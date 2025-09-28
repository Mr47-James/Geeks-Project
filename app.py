from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, desc, asc, func
from functools import wraps
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime
from io import BufferedReader
from pathlib import Path
from typing import Any, Dict, Iterable, List
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import numpy as np
import pandas as pd
from collections import Counter
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
try:
    from mutagen import File as MutagenFile
except ImportError:
    from mutagen._file import File as MutagenFile

# Import database initialization
from index import init_db, db
from models.music import Artist, Track, UserPreference, User, Role, UserActivity, UserBookmark, Playlist, PlaylistTrack

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production
bcrypt = Bcrypt(app)

# Logging configuration
logging.basicConfig(level=logging.INFO)  # Adjust level/handlers in production

# Upload configuration
UPLOAD_FOLDER = Path(os.environ.get('UPLOAD_FOLDER', Path.cwd() / 'uploads'))
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.aac', '.m4a', '.ogg'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB per file upper bound

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

STAGING_FOLDER = UPLOAD_FOLDER / 'staging'
STAGING_FOLDER.mkdir(parents=True, exist_ok=True)

MAX_FILES_PER_BATCH = 100
UPLOAD_BATCH_SESSION_KEY = 'pending_upload_batches'

# Regex for matching numeric strings (duration, bitrate, sample rate etc.)
_whitespace_collapse = re.compile(r"\s+")


def is_allowed_file(filename: str) -> bool:
    """Return True if filename extension is supported."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def normalize_string(value: str | None) -> str | None:
    """Trim and collapse whitespace for user-facing metadata strings."""
    if not value:
        return None
    collapsed = _whitespace_collapse.sub(' ', value).strip()
    return collapsed or None


def safe_filename(original_name: str) -> str:
    """Generate a unique, secure filename preserving the original extension."""
    stem = secure_filename(Path(original_name).stem) or 'track'
    extension = Path(original_name).suffix.lower()
    unique_suffix = uuid4().hex[:12]
    return f"{stem}-{unique_suffix}{extension}"


def ensure_session_batch() -> dict:
    """Ensure the session contains a dictionary to hold pending upload batches."""
    batch_state = session.get(UPLOAD_BATCH_SESSION_KEY)
    if not isinstance(batch_state, dict):
        batch_state = {}
        session[UPLOAD_BATCH_SESSION_KEY] = batch_state
    return batch_state


def extract_metadata(file_path: Path) -> dict[str, int | str | None]:
    """Use mutagen to derive common audio metadata, returning safe defaults."""
    metadata = {
        'duration': None,
        'bitrate': None,
        'sample_rate': None,
        'title': None,
        'album': None,
        'artist': None,
        'genre': None,
        'file_size': file_path.stat().st_size if file_path.exists() else None,
    }

    if not file_path.exists():
        return metadata

    try:
        mutagen_file = MutagenFile(file_path.as_posix())
        if mutagen_file is None:
            return metadata

        # Duration is available for most formats
        if getattr(mutagen_file.info, 'length', None):
            metadata['duration'] = int(mutagen_file.info.length)

        # Bitrate and sample rate vary by codec, guard each attribute
        if hasattr(mutagen_file.info, 'bitrate'):
            metadata['bitrate'] = int(getattr(mutagen_file.info, 'bitrate') or 0) or None

        if hasattr(mutagen_file.info, 'sample_rate'):
            metadata['sample_rate'] = int(getattr(mutagen_file.info, 'sample_rate') or 0) or None

        tags = mutagen_file.tags or {}

        def pick_first(*keys: str) -> str | None:
            for key in keys:
                value = tags.get(key)
                if isinstance(value, list) and value:
                    return str(value[0])
                if value:
                    return str(value)
            return None

        metadata['title'] = normalize_string(pick_first('TIT2', 'title'))
        metadata['album'] = normalize_string(pick_first('TALB', 'album'))
        metadata['artist'] = normalize_string(pick_first('TPE1', 'artist'))
        metadata['genre'] = normalize_string(pick_first('TCON', 'genre'))

    except Exception as exc:  # noqa: BLE001 guard against codec edge cases
        app.logger.warning('Metadata extraction failed for %s: %s', file_path.name, exc)

    return metadata


def _persist_file_from_storage(storage: FileStorage, destination: Path) -> Path:
    """
    Persist an uploaded file storage object to destination path.
    Guards against partial writes and ensures parent directories exist.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output_handle:
        _copy_stream(storage.stream, output_handle)
    return destination


def _copy_stream(source: Any, destination: Any, chunk_size: int = 65536) -> None:
    """Copy a stream in chunks to avoid loading entire file into memory."""
    while True:
        chunk = source.read(chunk_size)
        if not chunk:
            break
        destination.write(chunk)


def _extract_zip_to_temp(file_path: Path) -> List[Path]:
    """Extract zip archive into a temporary directory and return extracted file paths."""
    temp_dir = Path(tempfile.mkdtemp(prefix='batch-', dir=STAGING_FOLDER))
    extracted_files: List[Path] = []
    try:
        with ZipFile(file_path, 'r') as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_path = Path(member.filename)
                if member_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                safe_name = safe_filename(member_path.name)
                destination = temp_dir / safe_name
                with archive.open(member, 'r') as source, destination.open('wb') as target:
                    shutil.copyfileobj(source, target)
                extracted_files.append(destination)
    except BadZipFile as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError(f'Invalid zip archive: {file_path.name}') from exc
    return extracted_files


def _collect_audio_files(uploaded_items: Iterable[FileStorage]) -> List[Path]:
    """
    Persist uploaded files, handling zip archives by extracting their contents.
    Returns list of paths to audio files ready for metadata extraction.
    """
    audio_files: List[Path] = []
    for item in uploaded_items:
        filename = item.filename or ''
        suffix = Path(filename).suffix.lower()
        safe_name = safe_filename(filename)
        destination = UPLOAD_FOLDER / safe_name

        if suffix == '.zip':
            temp_zip_path = STAGING_FOLDER / safe_name
            _persist_file_from_storage(item, temp_zip_path)
            extracted = _extract_zip_to_temp(temp_zip_path)
            audio_files.extend(extracted)
            temp_zip_path.unlink(missing_ok=True)
            continue

        if suffix not in ALLOWED_EXTENSIONS:
            continue

        _persist_file_from_storage(item, destination)
        audio_files.append(destination)

    if len(audio_files) > MAX_FILES_PER_BATCH:
        for file_path in audio_files:
            if file_path.exists() and file_path.is_file():
                file_path.unlink(missing_ok=True)
        raise ValueError(f'Upload exceeds {MAX_FILES_PER_BATCH} audio files limit')

    return audio_files


def _match_or_prepare_artist(artist_name: str | None, batch_artists: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve artist by name or prepare a placeholder entry for confirmation."""
    if not artist_name:
        return {'status': 'missing', 'artist': None}

    normalized = normalize_string(artist_name)
    if not normalized:
        return {'status': 'missing', 'artist': None}

    existing = Artist.query.filter(func.lower(Artist.name) == normalized.lower()).first()
    if existing:
        return {'status': 'existing', 'artist': existing}

    key = normalized.lower()
    artist_entry = batch_artists.setdefault(key, {
        'name': normalized,
        'tracks': []
    })
    return {'status': 'pending', 'artist': artist_entry}


def _serialize_track_preview(track_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare track metadata for JSON serialization."""
    file_path = track_data.get('file_path')
    file_size = track_data.get('file_size')
    file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else None
    
    return {
        'title': track_data.get('title'),
        'album': track_data.get('album'),
        'genre': track_data.get('genre'),
        'duration': track_data.get('duration'),
        'bitrate': track_data.get('bitrate'),
        'sample_rate': track_data.get('sample_rate'),
        'file_size': file_size,
        'file_size_mb': file_size_mb,
        'file_path': file_path,
        'filename': Path(file_path).name if file_path else None,
        'artist_name': track_data.get('artist_name'),
        'artist_status': track_data.get('artist_status'),
        'artist_id': track_data.get('artist_id'),
        'release_year': track_data.get('release_year'),
    }


def _cleanup_staging(batch_payload: Dict[str, Any]) -> None:
    """Remove any temporary directories created for this batch."""
    temp_dirs = batch_payload.get('temp_dirs', []) if isinstance(batch_payload, dict) else []
    for folder in temp_dirs:
        shutil.rmtree(folder, ignore_errors=True)


def _prepare_batch_payload(audio_files: List[Path]) -> Dict[str, Any]:
    """Extract metadata and prepare a payload describing the uploaded batch."""
    batch_artists: Dict[str, Dict[str, Any]] = {}
    tracks_preview: List[Dict[str, Any]] = []
    temp_dirs: List[str] = []

    for file_path in audio_files:
        if str(file_path).startswith(STAGING_FOLDER.as_posix()):
            temp_dirs.append(file_path.parent.as_posix())

        metadata = extract_metadata(file_path)
        metadata['title'] = normalize_string(str(metadata.get('title')) if metadata.get('title') else None) or file_path.stem
        metadata['album'] = normalize_string(str(metadata.get('album')) if metadata.get('album') else None)
        metadata['genre'] = normalize_string(str(metadata.get('genre')) if metadata.get('genre') else None)
        metadata['artist'] = normalize_string(str(metadata.get('artist')) if metadata.get('artist') else None)

        artist_result = _match_or_prepare_artist(metadata.get('artist'), batch_artists)
        track_payload = {
            'title': metadata['title'],
            'album': metadata['album'],
            'genre': metadata['genre'],
            'duration': metadata['duration'],
            'bitrate': metadata['bitrate'],
            'sample_rate': metadata['sample_rate'],
            'file_size': metadata['file_size'],
            'file_path': file_path.as_posix(),
            'artist_status': artist_result['status'],
            'artist_name': metadata.get('artist'),
        }

        if artist_result['status'] == 'existing':
            track_payload['artist_id'] = artist_result['artist'].id
        elif artist_result['status'] == 'pending':
            artist_entry = artist_result['artist']
            artist_entry.setdefault('tracks', []).append(track_payload)

        tracks_preview.append(track_payload)

    batch_artists['_temp_dirs'] = temp_dirs
    return {
        'tracks': tracks_preview,
        'pending_artists': [value for key, value in batch_artists.items() if key != '_temp_dirs'],
        'temp_dirs': temp_dirs,
    }


def _store_batch_in_session(batch_payload: Dict[str, Any]) -> str:
    """Persist the batch payload in the user session and return its identifier."""
    batches = ensure_session_batch()
    batch_id = uuid4().hex
    batches[batch_id] = batch_payload
    session.modified = True
    return batch_id


def _pop_batch_from_session(batch_id: str) -> Dict[str, Any] | None:
    batches = ensure_session_batch()
    payload = batches.pop(batch_id, None)
    session.modified = True
    return payload


def _validate_tracks_ready(tracks: List[Dict[str, Any]]) -> List[str]:
    """Return a list of validation error messages for the provided tracks."""
    errors: List[str] = []
    for idx, track in enumerate(tracks, start=1):
        title = track.get('title')
        artist_name = track.get('artist_name')
        if not title:
            errors.append(f'Track #{idx} is missing a title.')
        if not artist_name and not track.get('artist_id'):
            errors.append(f'Track "{title or f"#{idx}"}" has no artist metadata.')
        # Ensure a file path for persistence
        if not track.get('file_path'):
            errors.append(f'Track "{title or f"#{idx}"}" is missing an audio file reference.')
    return errors


# Initialize database
init_db(app)


# Session helpers
class SessionKeys:
    USER_ID = "user_id"
    USERNAME = "username"
    ROLE = "role"
    LOGGED_IN = "logged_in"


def current_user() -> User | None:
    user_id = session.get(SessionKeys.USER_ID)
    if user_id is None:
        return None
    return User.query.get(user_id)


def is_logged_in() -> bool:
    return bool(session.get(SessionKeys.LOGGED_IN))


def current_role() -> str | None:
    role_value = session.get(SessionKeys.ROLE)
    return role_value


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific roles for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_logged_in():
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user_role = current_role()
            if user_role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('client_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def track_user_activity(track_id: int, activity_type: str, duration: int = 0):
    """Track user activity for ML recommendations"""
    user = current_user()
    if user:
        activity = UserActivity(
            user_id=user.id,
            track_id=track_id,
            activity_type=activity_type,
            duration_listened=duration
        )
        db.session.add(activity)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to track user activity: {e}')


# Create tables and seed data
with app.app_context():
    db.create_all()

    # Seed database with sample data if empty
    if Artist.query.count() == 0:
        from database.index import create_sample_data
        print("Creating sample data...")
        create_sample_data()
        print("Sample data created successfully!")

# Pagination settings
TRACKS_PER_PAGE = 10
ARTISTS_PER_PAGE = 10

@app.route('/')
def index():
    """Home page - accessible to everyone"""
    if is_logged_in():
        # Redirect authenticated users to their appropriate dashboard
        user_role = current_role()
        if user_role == 'consumer':
            return redirect(url_for('client_dashboard'))
        else:  # technician
            return redirect(url_for('admin_dashboard'))
    
    # Show public home page for non-authenticated users
    # Get some basic stats for public display
    total_tracks = Track.query.count()
    total_artists = Artist.query.count()
    popular_tracks = Track.query.order_by(desc(Track.play_count)).limit(6).all()
    
    return render_template('home.html',
                         total_tracks=total_tracks,
                         total_artists=total_artists,
                         popular_tracks=popular_tracks)


@app.route('/admin')
@login_required
@role_required('technician')
def admin_dashboard():
    """Admin/Technician Dashboard page"""
    # Get some basic stats for the dashboard
    total_tracks = Track.query.count()
    total_artists = Artist.query.count()
    recent_tracks = Track.query.order_by(desc(Track.created_at)).limit(5).all()
    popular_tracks = Track.query.order_by(desc(Track.play_count)).limit(5).all()

    # Placeholder integration summary for front-end hydration
    pending_integrations = {
        'message': 'External integrations pending. Drop tokens into the browser when ready.',
        'metricsReady': False,
        'connectivity': 'unknown'
    }

    return render_template('index.html',
                         total_tracks=total_tracks,
                         total_artists=total_artists,
                         recent_tracks=recent_tracks,
                         popular_tracks=popular_tracks,
                         pending_integrations=pending_integrations)

@app.route('/tracks')
@login_required
@role_required('technician')
def tracks():
    """List all tracks with search, filter, sort, and pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    genre_filter = request.args.get('genre', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    min_popularity = request.args.get('min_popularity', type=int)
    min_likes = request.args.get('min_likes', type=int)
    
    # Base query
    query = Track.query.join(Artist)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Track.title.ilike(f'%{search}%'),
                Track.album.ilike(f'%{search}%'),
                Artist.name.ilike(f'%{search}%')
            )
        )
    
    # Apply genre filter
    if genre_filter:
        query = query.filter(Track.genre == genre_filter)
    
    # Popularity filters
    if min_popularity is not None:
        query = query.filter(Track.play_count >= min_popularity)

    if min_likes is not None:
        query = query.filter(Track.like_count >= min_likes)
    
    # Apply sorting
    if sort_by == 'title':
        order_col = Track.title
    elif sort_by == 'artist':
        order_col = Artist.name
    elif sort_by == 'album':
        order_col = Track.album
    elif sort_by == 'genre':
        order_col = Track.genre
    elif sort_by == 'year':
        order_col = Track.release_year
    elif sort_by == 'duration':
        order_col = Track.duration
    elif sort_by == 'play_count':
        order_col = Track.play_count
    elif sort_by == 'likes':
        order_col = Track.like_count
    else:  # default to created_at
        order_col = Track.created_at
    
    if sort_order == 'asc':
        query = query.order_by(asc(order_col))
    else:
        query = query.order_by(desc(order_col))
    
    # Paginate results
    tracks_paginated = query.paginate(
        page=page, per_page=TRACKS_PER_PAGE, error_out=False
    )
    
    # Get unique genres for filter dropdown
    genres = db.session.query(Track.genre).distinct().filter(Track.genre.isnot(None)).all()
    genres = [g[0] for g in genres if g[0]]
    
    return render_template(
        'tracks.html',
        tracks=tracks_paginated,
        search=search,
        genre_filter=genre_filter,
        genres=genres,
        sort_by=sort_by,
        sort_order=sort_order,
        min_popularity=min_popularity,
        min_likes=min_likes,
    )

@app.route('/tracks/<int:track_id>')
def track_details(track_id):
    """View track details"""
    track = Track.query.get_or_404(track_id)
    
    # Get similar tracks (same genre or artist)
    similar_tracks = Track.query.filter(
        or_(
            Track.genre == track.genre,
            Track.artist_id == track.artist_id
        ),
        Track.id != track.id
    ).limit(5).all()
    
    return render_template('track_details.html', track=track, similar_tracks=similar_tracks)

@app.route('/tracks/create', methods=['GET'])
def create_track():
    """Redirect manual creation attempts to the upload workflow."""
    flash('Tracks are now created through the upload workflow. Please upload audio to continue.', 'info')
    return redirect(url_for('upload_tracks'))

@app.route('/tracks/<int:track_id>/edit', methods=['GET', 'POST'])
def edit_track(track_id):
    """Edit an existing track"""
    track = Track.query.get_or_404(track_id)
    
    if request.method == 'POST':
        # Update track data
        track.title = request.form.get('title')
        track.album = request.form.get('album')
        track.genre = request.form.get('genre')
        track.duration = request.form.get('duration', type=int)
        track.release_year = request.form.get('release_year', type=int)
        track.artist_id = request.form.get('artist_id', type=int)
        track.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash(f'Track "{track.title}" updated successfully!', 'success')
            return redirect(url_for('track_details', track_id=track.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating track: {str(e)}', 'error')
    
    # Get all artists for the dropdown
    artists = Artist.query.order_by(Artist.name).all()
    current_year = datetime.utcnow().year
    return render_template('edit_track.html', track=track, artists=artists, current_year=current_year)

@app.route('/tracks/<int:track_id>/delete', methods=['POST'])
def delete_track(track_id):
    """Delete a single track."""
    track = Track.query.get_or_404(track_id)
    track_title = track.title
    
    try:
        db.session.delete(track)
        db.session.commit()
        app.logger.info('Deleted track id=%s title="%s" via single deletion.', track_id, track_title)
        flash(f'Track "{track_title}" deleted successfully!', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        app.logger.exception('Failed to delete track id=%s: %s', track_id, exc)
        flash(f'Error deleting track: {str(exc)}', 'error')
    
    response = redirect(url_for('tracks'))
    response.headers['HX-Redirect'] = url_for('tracks')
    return response

@app.route('/tracks/<int:track_id>/like', methods=['POST'])
def like_track(track_id):
    """Like a track (for ML recommendations)"""
    track = Track.query.get_or_404(track_id)
    user = current_user()
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Please log in to like tracks'}), 401
    
    # Check if user already has a preference for this track
    existing_pref = UserPreference.query.filter_by(user_id=user.id, track_id=track_id).first()
    
    if existing_pref:
        if existing_pref.preference != 'like':
            # Update existing preference
            if existing_pref.preference == 'dislike':
                track.dislike_count = max(0, track.dislike_count - 1)
            existing_pref.preference = 'like'
            track.like_count += 1
        # If already liked, do nothing
    else:
        # Create new preference
        preference = UserPreference(user_id=user.id, track_id=track_id, preference='like')
        db.session.add(preference)
        track.like_count += 1
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'likes': track.like_count, 'dislikes': track.dislike_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/tracks/<int:track_id>/dislike', methods=['POST'])
def dislike_track(track_id):
    """Dislike a track (for ML recommendations)"""
    track = Track.query.get_or_404(track_id)
    user = current_user()
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Please log in to dislike tracks'}), 401
    
    # Check if user already has a preference for this track
    existing_pref = UserPreference.query.filter_by(user_id=user.id, track_id=track_id).first()
    
    if existing_pref:
        if existing_pref.preference != 'dislike':
            # Update existing preference
            if existing_pref.preference == 'like':
                track.like_count = max(0, track.like_count - 1)
            existing_pref.preference = 'dislike'
            track.dislike_count += 1
        # If already disliked, do nothing
    else:
        # Create new preference
        preference = UserPreference(user_id=user.id, track_id=track_id, preference='dislike')
        db.session.add(preference)
        track.dislike_count += 1
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'likes': track.like_count, 'dislikes': track.dislike_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/artists')
def artists():
    """List all artists with pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Base query
    query = Artist.query
    
    # Apply search filter
    if search:
        query = query.filter(Artist.name.ilike(f'%{search}%'))
    
    # Order by name
    query = query.order_by(Artist.name)
    
    # Paginate results
    artists_paginated = query.paginate(
        page=page, per_page=ARTISTS_PER_PAGE, error_out=False
    )
    
    return render_template(
        'artists.html',
        artists=artists_paginated,
        search=search,
    )


@app.route('/upload', methods=['GET'])
def upload_tracks():
    """Render the upload page."""
    return render_template('upload.html')


@app.route('/upload/preview', methods=['POST'])
def upload_preview():
    """Handle the initial upload, returning metadata preview and pending artists."""
    files: List[FileStorage] = request.files.getlist('files')
    if not files:
        flash('Please select at least one audio file or zip archive.', 'error')
        return redirect(url_for('upload_tracks'))

    try:
        audio_files = _collect_audio_files(files)
    except ValueError as error:
        flash(str(error), 'error')
        return redirect(url_for('upload_tracks'))

    if not audio_files:
        flash('No supported audio files detected.', 'error')
        return redirect(url_for('upload_tracks'))

    batch_payload = _prepare_batch_payload(audio_files)
    batch_payload['uploaded_at'] = datetime.utcnow().isoformat()
    batch_id = _store_batch_in_session(batch_payload)

    tracks_preview = [_serialize_track_preview(track) for track in batch_payload['tracks']]
    pending_artists = batch_payload['pending_artists']
    
    # Count matched artists (tracks with existing artist_id)
    matched_artists = []
    for track in batch_payload['tracks']:
        if track.get('artist_status') == 'existing' and track.get('artist_id'):
            artist_id = track.get('artist_id')
            if artist_id not in [a.id for a in matched_artists]:
                artist = Artist.query.get(artist_id)
                if artist:
                    matched_artists.append(artist)

    return render_template(
        'upload_review.html',
        batch_id=batch_id,
        tracks=tracks_preview,
        pending_artists=pending_artists,
        matched_artists=matched_artists,
        current_year=datetime.utcnow().year,
    )


@app.route('/upload/confirm', methods=['POST'])
def upload_confirm():
    """Persist staged tracks and any new artists after confirmation."""
    batch_id = request.form.get('batch_id')
    if not batch_id:
        flash('Missing batch identifier. Please upload files again.', 'error')
        return redirect(url_for('upload_tracks'))

    batch_payload = _pop_batch_from_session(batch_id)
    if not batch_payload:
        flash('Upload session expired. Please start a new upload.', 'error')
        return redirect(url_for('upload_tracks'))

    tracks = batch_payload.get('tracks', [])
    errors = _validate_tracks_ready(tracks)
    if errors:
        for message in errors:
            flash(message, 'error')
        return redirect(url_for('upload_tracks'))

    new_artists_data: List[Dict[str, Any]] = []
    if request.form.get('confirm_artists') == 'true':
        new_artists_data = batch_payload.get('pending_artists', [])

    created_artists: Dict[str, Artist] = {}
    total_saved_tracks = 0

    try:
        # Create new artists if confirmed
        for artist_data in new_artists_data:
            name = artist_data.get('name')
            if not name:
                continue
            existing = Artist.query.filter(func.lower(Artist.name) == name.lower()).first()
            if existing:
                created_artists[name.lower()] = existing
                continue
            artist = Artist(name=name)
            db.session.add(artist)
            db.session.flush()
            created_artists[name.lower()] = artist

        created_tracks: List[Track] = []
        for track_meta in tracks:
            artist_id = track_meta.get('artist_id')
            artist_name = track_meta.get('artist_name')
            if not artist_id and artist_name:
                artist_id = created_artists.get(artist_name.lower()).id if created_artists.get(artist_name.lower()) else None

            if not artist_id:
                continue

            new_track = Track(
                title=track_meta.get('title'),
                album=track_meta.get('album'),
                genre=track_meta.get('genre'),
                duration=track_meta.get('duration'),
                file_path=track_meta.get('file_path'),
                file_size=track_meta.get('file_size'),
                bitrate=track_meta.get('bitrate'),
                sample_rate=track_meta.get('sample_rate'),
                artist_id=artist_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.session.add(new_track)
            created_tracks.append(new_track)

        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        _cleanup_staging(batch_payload)
        flash(f'Failed to save uploaded tracks: {exc}', 'error')
        return redirect(url_for('upload_tracks'))

    _cleanup_staging(batch_payload)

    flash(f'Uploaded {len(tracks)} tracks successfully!', 'success')
    return redirect(url_for('tracks'))


@app.route('/artists/<int:artist_id>')
def artist_details(artist_id):
    """View artist details and their tracks"""
    artist = Artist.query.get_or_404(artist_id)
    tracks = Track.query.filter_by(artist_id=artist_id).order_by(desc(Track.created_at)).all()
    
    return render_template('artist_details.html', artist=artist, tracks=tracks)

@app.route('/artists/create', methods=['GET', 'POST'])
def create_artist():
    """Create a new artist"""
    if request.method == 'POST':
        name = request.form.get('name')
        bio = request.form.get('bio')
        genre = request.form.get('genre')
        country = request.form.get('country')
        
        if not name:
            flash('Artist name is required!', 'error')
            return redirect(url_for('create_artist'))
        
        artist = Artist(name=name, bio=bio, genre=genre, country=country)
        
        try:
            db.session.add(artist)
            db.session.commit()
            flash(f'Artist "{name}" created successfully!', 'success')
            return redirect(url_for('artists'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating artist: {str(e)}', 'error')
    
    return render_template('create_artist.html')

@app.route('/artists/<int:artist_id>/edit', methods=['GET', 'POST'])
def edit_artist(artist_id):
    """Edit an existing artist"""
    artist = Artist.query.get_or_404(artist_id)
    
    if request.method == 'POST':
        artist.name = request.form.get('name')
        artist.bio = request.form.get('bio')
        artist.genre = request.form.get('genre')
        artist.country = request.form.get('country')
        
        try:
            db.session.commit()
            flash(f'Artist "{artist.name}" updated successfully!', 'success')
            return redirect(url_for('artist_details', artist_id=artist.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating artist: {str(e)}', 'error')
    
    return render_template('edit_artist.html', artist=artist)

@app.route('/artists/<int:artist_id>/delete', methods=['POST'])
def delete_artist(artist_id):
    """Delete an artist and all their tracks"""
    artist = Artist.query.get_or_404(artist_id)
    artist_name = artist.name
    
    try:
        db.session.delete(artist)
        db.session.commit()
        flash(f'Artist "{artist_name}" and all their tracks deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting artist: {str(e)}', 'error')
    
    return redirect(url_for('artists'))

@app.route('/stats')
def stats():
    """Statistics and analytics page"""
    # Basic stats
    total_tracks = Track.query.count()
    total_artists = Artist.query.count()
    
    # Genre distribution
    genre_stats = db.session.query(Track.genre, db.func.count(Track.id)).filter(
        Track.genre.isnot(None)
    ).group_by(Track.genre).all()
    
    # Most popular tracks (by play count)
    popular_tracks = Track.query.order_by(desc(Track.play_count)).limit(10).all()
    
    # Most liked tracks
    liked_tracks = Track.query.order_by(desc(Track.like_count)).limit(10).all()
    
    # Artists with most tracks
    artist_track_counts = db.session.query(
        Artist.name, db.func.count(Track.id).label('track_count')
    ).join(Track).group_by(Artist.id, Artist.name).order_by(
        desc('track_count')
    ).limit(10).all()
    
    # Release year distribution
    year_stats = db.session.query(
        Track.release_year, db.func.count(Track.id)
    ).filter(Track.release_year.isnot(None)).group_by(
        Track.release_year
    ).order_by(Track.release_year).all()
    
    return render_template(
        'stats.html',
        total_tracks=total_tracks,
        total_artists=total_artists,
        genre_stats=genre_stats,
        popular_tracks=popular_tracks,
        liked_tracks=liked_tracks,
        artist_track_counts=artist_track_counts,
        year_stats=year_stats,
    )

@app.route('/api/integrations/status')
def integrations_status():
    """Mock integration status endpoint ready for token-based auth."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip()

    if not token:
        return jsonify({'message': 'Authorization token missing.', 'metricsReady': False}), 401

    # For now, accept any token and respond with a ready scaffold
    status_payload = {
        'message': 'Integration scaffold online. Supply real validation when external API wiring is complete.',
        'metricsReady': True,
        'connectivity': 'ok',
        'lastChecked': datetime.utcnow().isoformat() + 'Z'
    }

    return jsonify(status_payload)


@app.route('/api/metrics/snapshot')
def metrics_snapshot():
    """Returns a placeholder metrics snapshot for front-end hydration."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip()

    if not token:
        return jsonify({'message': 'Authorization token missing.'}), 401

    # Mock data to demonstrate layout; replace with real analytics later
    snapshot = {
        'metrics': [
            {'label': 'Plays (24h)', 'value': Track.query.with_entities(func.sum(Track.play_count)).scalar() or 0},
            {'label': 'Likes Total', 'value': Track.query.with_entities(func.sum(Track.like_count)).scalar() or 0},
            {'label': 'New Tracks (7d)', 'value': Track.query.filter(Track.created_at >= datetime.utcnow() - pd.Timedelta(days=7)).count()},
        ]
    }

    return jsonify(snapshot)


@app.route('/recommendations/<int:track_id>')
def get_recommendations(track_id):
    """Get ML-based recommendations for a track"""
    track = Track.query.get_or_404(track_id)
    
    # Simple recommendation algorithm based on:
    # 1. Same genre
    # 2. Same artist
    # 3. Similar popularity (play count)
    # 4. User preferences (liked tracks)
    
    recommendations = []
    
    # Get tracks from same genre
    genre_tracks = Track.query.filter(
        Track.genre == track.genre,
        Track.id != track.id
    ).order_by(desc(Track.like_count)).limit(3).all()
    recommendations.extend(genre_tracks)
    
    # Get tracks from same artist
    artist_tracks = Track.query.filter(
        Track.artist_id == track.artist_id,
        Track.id != track.id
    ).order_by(desc(Track.play_count)).limit(2).all()
    recommendations.extend(artist_tracks)
    
    # Get popular tracks (if we don't have enough recommendations)
    if len(recommendations) < 5:
        popular_tracks = Track.query.filter(
            Track.id != track.id,
            ~Track.id.in_([r.id for r in recommendations])
        ).order_by(desc(Track.like_count)).limit(5 - len(recommendations)).all()
        recommendations.extend(popular_tracks)
    
    # Remove duplicates and limit to 5
    seen_ids = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec.id not in seen_ids:
            unique_recommendations.append(rec)
            seen_ids.add(rec.id)
        if len(unique_recommendations) >= 5:
            break
    
    return jsonify([track.to_dict() for track in unique_recommendations])


# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - Gateway for role-based routing"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Set session variables
            session[SessionKeys.USER_ID] = user.id
            session[SessionKeys.USERNAME] = user.username
            session[SessionKeys.ROLE] = user.role.value
            session[SessionKeys.LOGGED_IN] = True
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Role-based routing
            if user.role == Role.CONSUMER:
                return redirect(url_for('client_dashboard'))
            else:  # TECHNICIAN role
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        region = request.form.get('region', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        if password and len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('signup.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=Role.CONSUMER,  # Default role for new users
            region=region
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating account. Please try again.', 'error')
    
    return render_template('signup.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Client-side routes (Consumer interface)
@app.route('/client')
@login_required
@role_required('consumer')
def client_dashboard():
    """Client dashboard - Consumer interface"""
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get user's favorite tracks (bookmarked)
    bookmarked_tracks = db.session.query(Track).join(UserBookmark).filter(
        UserBookmark.user_id == user.id
    ).order_by(desc(UserBookmark.created_at)).limit(10).all()
    
    # Get recently played tracks
    recent_activities = db.session.query(Track).join(UserActivity).filter(
        UserActivity.user_id == user.id,
        UserActivity.activity_type == 'play'
    ).order_by(desc(UserActivity.timestamp)).limit(10).all()
    
    # Get recommended tracks based on user preferences
    user_preferences = db.session.query(UserPreference).filter(
        UserPreference.user_id == user.id,
        UserPreference.preference == 'like'
    ).all()
    
    recommended_tracks = []
    if user_preferences:
        # Get genres from liked tracks
        liked_genres = db.session.query(Track.genre).join(UserPreference).filter(
            UserPreference.user_id == user.id,
            UserPreference.preference == 'like'
        ).distinct().all()
        
        if liked_genres:
            genres = [g[0] for g in liked_genres if g[0]]
            recommended_tracks = Track.query.filter(
                Track.genre.in_(genres)
            ).order_by(desc(Track.like_count)).limit(10).all()
    
    # Get popular tracks if no recommendations
    if not recommended_tracks:
        recommended_tracks = Track.query.order_by(desc(Track.play_count)).limit(10).all()
    
    return render_template('client_index.html',
                         bookmarked_tracks=bookmarked_tracks,
                         recent_tracks=recent_activities,
                         recommended_tracks=recommended_tracks,
                         user=user)


@app.route('/client/tracks')
@login_required
@role_required('consumer')
def client_tracks():
    """Client tracks page with search and filtering"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    genre_filter = request.args.get('genre', '')
    
    # Base query
    query = Track.query.join(Artist)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Track.title.ilike(f'%{search}%'),
                Track.album.ilike(f'%{search}%'),
                Artist.name.ilike(f'%{search}%')
            )
        )
    
    # Apply genre filter
    if genre_filter:
        query = query.filter(Track.genre == genre_filter)
    
    # Order by popularity
    query = query.order_by(desc(Track.play_count))
    
    # Paginate results
    tracks_paginated = query.paginate(
        page=page, per_page=TRACKS_PER_PAGE, error_out=False
    )
    
    # Get unique genres for filter dropdown
    genres = db.session.query(Track.genre).distinct().filter(Track.genre.isnot(None)).all()
    genres = [g[0] for g in genres if g[0]]
    
    return render_template('client_tracks.html',
                         tracks=tracks_paginated,
                         search=search,
                         genre_filter=genre_filter,
                         genres=genres)


@app.route('/client/artists')
@login_required
@role_required('consumer')
def client_artists():
    """Client artists page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Base query
    query = Artist.query
    
    # Apply search filter
    if search:
        query = query.filter(Artist.name.ilike(f'%{search}%'))
    
    # Order by name
    query = query.order_by(Artist.name)
    
    # Paginate results
    artists_paginated = query.paginate(
        page=page, per_page=ARTISTS_PER_PAGE, error_out=False
    )
    
    return render_template('client_artists.html',
                         artists=artists_paginated,
                         search=search)


@app.route('/client/track/<int:track_id>')
@login_required
@role_required('consumer')
def client_track_detail(track_id):
    """Client track detail page"""
    track = Track.query.get_or_404(track_id)
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Track user activity
    track_user_activity(track_id, 'view')
    
    # Check if user has bookmarked this track
    is_bookmarked = UserBookmark.query.filter_by(
        user_id=user.id, track_id=track_id
    ).first() is not None
    
    # Get user's preference for this track
    user_preference = UserPreference.query.filter_by(
        user_id=user.id, track_id=track_id
    ).first()
    
    # Get similar tracks
    similar_tracks = Track.query.filter(
        or_(
            Track.genre == track.genre,
            Track.artist_id == track.artist_id
        ),
        Track.id != track.id
    ).limit(5).all()
    
    return render_template('client_track_detail.html',
                         track=track,
                         is_bookmarked=is_bookmarked,
                         user_preference=user_preference,
                         similar_tracks=similar_tracks)


@app.route('/client/track/<int:track_id>/play', methods=['POST'])
@login_required
@role_required('consumer')
def client_play_track(track_id):
    """Track play activity"""
    track = Track.query.get_or_404(track_id)
    duration = request.json.get('duration', 0)
    
    # Update play count
    track.play_count += 1
    
    # Track user activity
    track_user_activity(track_id, 'play', duration)
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'play_count': track.play_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/track/<int:track_id>/bookmark', methods=['POST'])
@login_required
@role_required('consumer')
def client_bookmark_track(track_id):
    """Bookmark/unbookmark a track"""
    user = current_user()
    track = Track.query.get_or_404(track_id)
    
    existing_bookmark = UserBookmark.query.filter_by(
        user_id=user.id, track_id=track_id
    ).first()
    
    if existing_bookmark:
        # Remove bookmark
        db.session.delete(existing_bookmark)
        bookmarked = False
    else:
        # Add bookmark
        bookmark = UserBookmark(user_id=user.id, track_id=track_id)
        db.session.add(bookmark)
        bookmarked = True
        
        # Track activity
        track_user_activity(track_id, 'bookmark')
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'bookmarked': bookmarked})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/track/<int:track_id>/like', methods=['POST'])
@login_required
@role_required('consumer')
def client_like_track(track_id):
    """Like a track"""
    user = current_user()
    track = Track.query.get_or_404(track_id)
    
    existing_pref = UserPreference.query.filter_by(
        user_id=user.id, track_id=track_id
    ).first()
    
    if existing_pref:
        if existing_pref.preference != 'like':
            if existing_pref.preference == 'dislike':
                track.dislike_count = max(0, track.dislike_count - 1)
            existing_pref.preference = 'like'
            track.like_count += 1
    else:
        preference = UserPreference(
            user_id=user.id, track_id=track_id, preference='like'
        )
        db.session.add(preference)
        track.like_count += 1
    
    try:
        db.session.commit()
        return jsonify({
            'status': 'success',
            'likes': track.like_count,
            'dislikes': track.dislike_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/track/<int:track_id>/dislike', methods=['POST'])
@login_required
@role_required('consumer')
def client_dislike_track(track_id):
    """Dislike a track"""
    user = current_user()
    track = Track.query.get_or_404(track_id)
    
    existing_pref = UserPreference.query.filter_by(
        user_id=user.id, track_id=track_id
    ).first()
    
    if existing_pref:
        if existing_pref.preference != 'dislike':
            if existing_pref.preference == 'like':
                track.like_count = max(0, track.like_count - 1)
            existing_pref.preference = 'dislike'
            track.dislike_count += 1
    else:
        preference = UserPreference(
            user_id=user.id, track_id=track_id, preference='dislike'
        )
        db.session.add(preference)
        track.dislike_count += 1
    
    try:
        db.session.commit()
        return jsonify({
            'status': 'success',
            'likes': track.like_count,
            'dislikes': track.dislike_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/my-tracks')
@login_required
@role_required('consumer')
def client_my_tracks():
    """User's bookmarked tracks"""
    user = current_user()
    
    bookmarked_tracks = db.session.query(Track).join(UserBookmark).filter(
        UserBookmark.user_id == user.id
    ).order_by(desc(UserBookmark.created_at)).all()
    
    # Get user's playlists
    user_playlists = Playlist.query.filter_by(user_id=user.id).order_by(desc(Playlist.updated_at)).all()
    
    return render_template('client_mytracks.html',
                         bookmarked_tracks=bookmarked_tracks,
                         user_playlists=user_playlists)


# Playlist Routes
@app.route('/client/playlists/create', methods=['POST'])
@login_required
@role_required('consumer')
def create_playlist():
    """Create a new playlist"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Please log in to create playlists'}), 401
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    is_public = data.get('is_public', False)
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Playlist name is required'}), 400
    
    # Check if user already has a playlist with this name
    existing = Playlist.query.filter_by(user_id=user.id, name=name).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'You already have a playlist with this name'}), 400
    
    playlist = Playlist(
        name=name,
        description=description,
        user_id=user.id,
        is_public=is_public
    )
    
    try:
        db.session.add(playlist)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Playlist "{name}" created successfully!',
            'playlist': playlist.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/playlists/<int:playlist_id>')
@login_required
@role_required('consumer')
def view_playlist(playlist_id):
    """View playlist details"""
    user = current_user()
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns the playlist or if it's public
    if playlist.user_id != user.id and not playlist.is_public:
        flash('You do not have permission to view this playlist.', 'error')
        return redirect(url_for('client_my_tracks'))
    
    # Get playlist tracks with their position
    playlist_tracks = db.session.query(Track, PlaylistTrack.position, PlaylistTrack.added_at).join(
        PlaylistTrack, Track.id == PlaylistTrack.track_id
    ).filter(
        PlaylistTrack.playlist_id == playlist_id
    ).order_by(PlaylistTrack.position).all()
    
    return render_template('client_playlist_detail.html',
                         playlist=playlist,
                         playlist_tracks=playlist_tracks,
                         is_owner=playlist.user_id == user.id)


@app.route('/client/playlists/<int:playlist_id>/add-track', methods=['POST'])
@login_required
@role_required('consumer')
def add_track_to_playlist(playlist_id):
    """Add a track to a playlist"""
    user = current_user()
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns the playlist
    if playlist.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'You do not have permission to modify this playlist'}), 403
    
    data = request.get_json()
    track_id = data.get('track_id')
    
    if not track_id:
        return jsonify({'status': 'error', 'message': 'Track ID is required'}), 400
    
    track = Track.query.get_or_404(track_id)
    
    # Check if track is already in playlist
    existing = PlaylistTrack.query.filter_by(playlist_id=playlist_id, track_id=track_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Track is already in this playlist'}), 400
    
    # Get the next position
    max_position = db.session.query(func.max(PlaylistTrack.position)).filter_by(playlist_id=playlist_id).scalar() or 0
    
    playlist_track = PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track_id,
        position=max_position + 1
    )
    
    try:
        db.session.add(playlist_track)
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'"{track.title}" added to playlist "{playlist.name}"'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/playlists/<int:playlist_id>/remove-track', methods=['POST'])
@login_required
@role_required('consumer')
def remove_track_from_playlist(playlist_id):
    """Remove a track from a playlist"""
    user = current_user()
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns the playlist
    if playlist.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'You do not have permission to modify this playlist'}), 403
    
    data = request.get_json()
    track_id = data.get('track_id')
    
    if not track_id:
        return jsonify({'status': 'error', 'message': 'Track ID is required'}), 400
    
    playlist_track = PlaylistTrack.query.filter_by(playlist_id=playlist_id, track_id=track_id).first()
    if not playlist_track:
        return jsonify({'status': 'error', 'message': 'Track not found in playlist'}), 404
    
    try:
        db.session.delete(playlist_track)
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Track removed from playlist'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/playlists/<int:playlist_id>/delete', methods=['POST'])
@login_required
@role_required('consumer')
def delete_playlist(playlist_id):
    """Delete a playlist"""
    user = current_user()
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns the playlist
    if playlist.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'You do not have permission to delete this playlist'}), 403
    
    playlist_name = playlist.name
    
    try:
        db.session.delete(playlist)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Playlist "{playlist_name}" deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/client/playlists/<int:playlist_id>/edit', methods=['POST'])
@login_required
@role_required('consumer')
def edit_playlist(playlist_id):
    """Edit playlist details"""
    user = current_user()
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns the playlist
    if playlist.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'You do not have permission to edit this playlist'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    is_public = data.get('is_public', playlist.is_public)
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Playlist name is required'}), 400
    
    # Check if user already has another playlist with this name
    existing = Playlist.query.filter_by(user_id=user.id, name=name).filter(Playlist.id != playlist_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'You already have a playlist with this name'}), 400
    
    try:
        playlist.name = name
        playlist.description = description
        playlist.is_public = is_public
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Playlist "{name}" updated successfully',
            'playlist': playlist.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/playlists')
@login_required
@role_required('consumer')
def get_user_playlists():
    """Get user's playlists for API calls"""
    user = current_user()
    playlists = Playlist.query.filter_by(user_id=user.id).order_by(desc(Playlist.updated_at)).all()
    return jsonify([playlist.to_dict() for playlist in playlists])


# User Track Upload Routes
@app.route('/client/upload', methods=['GET'])
@login_required
@role_required('consumer')
def client_upload_tracks():
    """User track upload page"""
    return render_template('client_upload.html')


@app.route('/client/upload/process', methods=['POST'])
@login_required
@role_required('consumer')
def client_upload_process():
    """Process user track uploads"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Please log in to upload tracks'}), 401
    
    files = request.files.getlist('files')
    if not files or not files[0].filename:
        return jsonify({'status': 'error', 'message': 'Please select at least one audio file'}), 400
    
    uploaded_tracks = []
    errors = []
    
    for file in files:
        if not file.filename:
            continue
            
        # Check file type
        if not is_allowed_file(file.filename):
            errors.append(f'File "{file.filename}" is not a supported audio format')
            continue
        
        # Check file size (limit to 50MB per file for user uploads)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            errors.append(f'File "{file.filename}" is too large (max 50MB)')
            continue
        
        # Generate safe filename
        safe_name = safe_filename(file.filename)
        file_path = UPLOAD_FOLDER / safe_name
        
        try:
            # Save file
            _persist_file_from_storage(file, file_path)
            
            # Extract metadata
            metadata = extract_metadata(file_path)
            
            # Get form data for this file
            title = request.form.get(f'title_{file.filename}', '').strip()
            artist_name = request.form.get(f'artist_{file.filename}', '').strip()
            album = request.form.get(f'album_{file.filename}', '').strip()
            genre = request.form.get(f'genre_{file.filename}', '').strip()
            
            # Use metadata if form fields are empty
            if not title:
                title = metadata.get('title') or Path(file.filename).stem
            if not artist_name:
                artist_name = metadata.get('artist') or user.username
            if not album:
                album = metadata.get('album')
            if not genre:
                genre = metadata.get('genre')
            
            # Find or create artist
            artist = Artist.query.filter(func.lower(Artist.name) == artist_name.lower()).first()
            if not artist:
                artist = Artist(name=artist_name)
                db.session.add(artist)
                db.session.flush()
            
            # Create track
            track = Track(
                title=title,
                album=album,
                genre=genre,
                duration=metadata.get('duration'),
                file_path=file_path.as_posix(),
                file_size=metadata.get('file_size'),
                bitrate=metadata.get('bitrate'),
                sample_rate=metadata.get('sample_rate'),
                artist_id=artist.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.session.add(track)
            uploaded_tracks.append({
                'title': title,
                'artist': artist_name,
                'filename': file.filename
            })
            
        except Exception as e:
            errors.append(f'Error processing "{file.filename}": {str(e)}')
            # Clean up file if it was created
            if file_path.exists():
                file_path.unlink()
    
    try:
        db.session.commit()
        
        success_count = len(uploaded_tracks)
        error_count = len(errors)
        
        response_data = {
            'status': 'success' if success_count > 0 else 'error',
            'uploaded_count': success_count,
            'error_count': error_count,
            'uploaded_tracks': uploaded_tracks,
            'errors': errors
        }
        
        if success_count > 0:
            response_data['message'] = f'Successfully uploaded {success_count} track(s)'
            if error_count > 0:
                response_data['message'] += f' ({error_count} failed)'
        else:
            response_data['message'] = 'No tracks were uploaded'
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'uploaded_count': 0,
            'error_count': len(files),
            'errors': [f'Failed to save tracks to database: {str(e)}']
        }), 500


@app.route('/client/my-uploads')
@login_required
@role_required('consumer')
def client_my_uploads():
    """View user's uploaded tracks"""
    user = current_user()
    
    # Get tracks where the artist name matches the user's username
    # This is a simple way to identify user-uploaded tracks
    user_tracks = Track.query.join(Artist).filter(
        func.lower(Artist.name) == user.username.lower()
    ).order_by(desc(Track.created_at)).all()
    
    return render_template('client_my_uploads.html', user_tracks=user_tracks)


# Audio Streaming Routes
@app.route('/audio/<int:track_id>')
@login_required
def stream_audio(track_id):
    """Stream audio file for a track"""
    track = Track.query.get_or_404(track_id)
    
    # Check if file exists
    if not track.file_path or not Path(track.file_path).exists():
        return "Audio file not found", 404
    
    # For now, we'll serve the file directly
    # In production, you might want to add more security checks
    from flask import send_file
    try:
        return send_file(
            track.file_path,
            as_attachment=False,
            mimetype='audio/mpeg'  # Default to MP3, could be made dynamic
        )
    except Exception as e:
        app.logger.error(f'Error streaming audio for track {track_id}: {e}')
        return "Error streaming audio", 500


@app.route('/api/track/<int:track_id>/info')
@login_required
def get_track_info(track_id):
    """Get track information for the audio player"""
    track = Track.query.get_or_404(track_id)
    
    return jsonify({
        'id': track.id,
        'title': track.title,
        'artist': track.artist.name if track.artist else 'Unknown Artist',
        'album': track.album,
        'duration': track.duration,
        'genre': track.genre,
        'audio_url': url_for('stream_audio', track_id=track.id),
        'play_count': track.play_count,
        'like_count': track.like_count
    })


@app.route('/demo/player')
@login_required
def player_demo():
    """Audio player demo page"""
    return render_template('player_demo.html')


@app.route('/debug/audio/<int:track_id>')
@login_required
def debug_audio(track_id):
    """Debug audio file accessibility"""
    track = Track.query.get_or_404(track_id)
    
    debug_info = {
        'track_id': track.id,
        'title': track.title,
        'file_path': track.file_path,
        'file_exists': Path(track.file_path).exists() if track.file_path else False,
        'file_size': Path(track.file_path).stat().st_size if track.file_path and Path(track.file_path).exists() else None,
        'audio_url': url_for('stream_audio', track_id=track.id),
        'api_url': url_for('get_track_info', track_id=track.id)
    }
    
    return jsonify(debug_info)


# Control Panel API Routes
@app.route('/api/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile_api():
    """Get or update user profile"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    if request.method == 'GET':
        # Return user profile data
        return jsonify({
            'username': user.username,
            'email': user.email,
            'region': user.region,
            'bio': getattr(user, 'bio', ''),
            'avatar_url': getattr(user, 'avatar_url', None),
            'settings': {
                'two_factor_enabled': getattr(user, 'two_factor_enabled', False),
                'login_notifications': getattr(user, 'login_notifications', True),
                'email_recommendations': getattr(user, 'email_recommendations', True),
                'email_digest': getattr(user, 'email_digest', True),
                'email_security': getattr(user, 'email_security', True),
                'push_releases': getattr(user, 'push_releases', True),
                'push_playlists': getattr(user, 'push_playlists', False),
                'share_activity': getattr(user, 'share_activity', True),
                'data_collection': getattr(user, 'data_collection', True),
            }
        })
    
    elif request.method == 'POST':
        # Update user profile
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            region = request.form.get('region', '').strip()
            bio = request.form.get('bio', '').strip()
            
            # Validation
            if not username:
                return jsonify({'status': 'error', 'message': 'Username is required'}), 400
            
            if not email:
                return jsonify({'status': 'error', 'message': 'Email is required'}), 400
            
            # Check if username is taken by another user
            if username != user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    return jsonify({'status': 'error', 'message': 'Username is already taken'}), 400
            
            # Check if email is taken by another user
            if email != user.email:
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    return jsonify({'status': 'error', 'message': 'Email is already registered'}), 400
            
            # Update user data
            user.username = username
            user.email = email
            user.region = region
            
            # Add bio field if it doesn't exist (extend User model as needed)
            if hasattr(user, 'bio'):
                user.bio = bio
            
            # Update session if username changed
            if session.get(SessionKeys.USERNAME) != username:
                session[SessionKeys.USERNAME] = username
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Profile updated successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/user/settings', methods=['POST'])
@login_required
def update_user_settings():
    """Update user settings (toggles)"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    try:
        data = request.get_json()
        setting = data.get('setting')
        enabled = data.get('enabled', False)
        
        if not setting:
            return jsonify({'status': 'error', 'message': 'Setting name is required'}), 400
        
        # Map of allowed settings
        allowed_settings = {
            '2fa-toggle': 'two_factor_enabled',
            'login-notifications': 'login_notifications',
            'email-recommendations': 'email_recommendations',
            'email-digest': 'email_digest',
            'email-security': 'email_security',
            'push-releases': 'push_releases',
            'push-playlists': 'push_playlists',
            'share-activity': 'share_activity',
            'data-collection': 'data_collection',
        }
        
        if setting not in allowed_settings:
            return jsonify({'status': 'error', 'message': 'Invalid setting'}), 400
        
        # For now, we'll store settings in a simple way
        # In a real app, you might want a separate UserSettings table
        setting_attr = allowed_settings[setting]
        
        # Since our User model might not have these fields, we'll simulate success
        # In a real implementation, you'd extend the User model or create a UserSettings table
        
        return jsonify({
            'status': 'success',
            'message': f'Setting updated: {setting_attr} = {enabled}'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/user/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'status': 'error', 'message': 'Both current and new passwords are required'}), 400
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 400
        
        # Validate new password
        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters long'}), 400
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/user/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def revoke_session(session_id):
    """Revoke a specific user session"""
    # This is a mock implementation
    # In a real app, you'd have a UserSession table to track active sessions
    return jsonify({
        'status': 'success',
        'message': f'Session {session_id} revoked successfully'
    })


@app.route('/api/user/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """Revoke all other user sessions"""
    # This is a mock implementation
    # In a real app, you'd revoke all sessions except the current one
    return jsonify({
        'status': 'success',
        'message': 'All other sessions revoked successfully'
    })


@app.route('/api/user/payment-methods', methods=['GET', 'POST'])
@login_required
def payment_methods():
    """Get or add payment methods"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    if request.method == 'GET':
        # Mock payment methods data
        # In a real app, you'd fetch from a PaymentMethod table
        mock_methods = [
            {
                'id': 1,
                'brand': 'visa',
                'last4': '4242',
                'expiry': '12/25'
            }
        ]
        return jsonify(mock_methods)
    
    elif request.method == 'POST':
        # Mock adding payment method
        # In a real app, you'd integrate with a payment processor like Stripe
        card_number = request.form.get('card_number', '').replace(' ', '')
        expiry = request.form.get('expiry')
        cvv = request.form.get('cvv')
        cardholder_name = request.form.get('cardholder_name')
        
        if not all([card_number, expiry, cvv, cardholder_name]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
        
        # Basic validation
        if len(card_number) < 13 or len(card_number) > 19:
            return jsonify({'status': 'error', 'message': 'Invalid card number'}), 400
        
        return jsonify({
            'status': 'success',
            'message': 'Payment method added successfully'
        })


@app.route('/api/user/payment-methods/<int:method_id>', methods=['DELETE'])
@login_required
def remove_payment_method(method_id):
    """Remove a payment method"""
    # Mock implementation
    return jsonify({
        'status': 'success',
        'message': 'Payment method removed successfully'
    })


@app.route('/api/user/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account"""
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    try:
        confirmation = request.form.get('confirmation')
        password = request.form.get('password')
        
        if confirmation != 'DELETE':
            return jsonify({'status': 'error', 'message': 'Please type "DELETE" to confirm'}), 400
        
        if not check_password_hash(user.password_hash, password):
            return jsonify({'status': 'error', 'message': 'Incorrect password'}), 400
        
        # Delete user and related data
        # Delete user preferences
        UserPreference.query.filter_by(user_id=user.id).delete()
        
        # Delete user activities
        UserActivity.query.filter_by(user_id=user.id).delete()
        
        # Delete user bookmarks
        UserBookmark.query.filter_by(user_id=user.id).delete()
        
        # Delete user playlists and playlist tracks
        user_playlists = Playlist.query.filter_by(user_id=user.id).all()
        for playlist in user_playlists:
            PlaylistTrack.query.filter_by(playlist_id=playlist.id).delete()
        Playlist.query.filter_by(user_id=user.id).delete()
        
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        # Clear session
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)