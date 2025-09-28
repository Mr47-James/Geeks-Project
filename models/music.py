from datetime import datetime
from enum import Enum
from typing import Optional, Sequence, cast

from index import db


class Role(Enum):
    CONSUMER = "consumer"
    TECHNICIAN = "technician"


class Artist(db.Model):
    __tablename__ = 'artists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    genre = db.Column(db.String(50))
    country = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with tracks
    tracks = db.relationship('Track', backref='artist', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Artist {self.name}>'
    
    def to_dict(self):
        artist_tracks: Sequence['Track'] = cast(Sequence['Track'], getattr(self, 'tracks', ()) or ())
        return {
            'id': self.id,
            'name': self.name,
            'bio': self.bio,
            'genre': self.genre,
            'country': self.country,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'track_count': len(artist_tracks)
        }

class Track(db.Model):
    __tablename__ = 'tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200))
    genre = db.Column(db.String(50))
    duration = db.Column(db.Integer)  # in seconds
    release_year = db.Column(db.Integer)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)  # in bytes
    bitrate = db.Column(db.Integer)
    sample_rate = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to artist
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    
    # User interaction fields for ML recommendations
    play_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        artist_relation = getattr(self, 'artist', None)
        artist_name: Optional[str] = artist_relation.name if artist_relation else 'Unknown'
        return f'<Track {self.title} by {artist_name}>'
    
    def to_dict(self):
        artist_relation = getattr(self, 'artist', None)
        artist_name: Optional[str] = artist_relation.name if artist_relation else None
        return {
            'id': self.id,
            'title': self.title,
            'album': self.album,
            'genre': self.genre,
            'duration': self.duration,
            'duration_formatted': self.format_duration(),
            'release_year': self.release_year,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'artist_id': self.artist_id,
            'artist_name': artist_name,
            'play_count': self.play_count,
            'like_count': self.like_count,
            'dislike_count': self.dislike_count
        }
    
    def format_duration(self):
        """Format duration from seconds to MM:SS format"""
        if not self.duration:
            return "0:00"
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    preference = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='preferences')
    track = db.relationship(
        'Track',
        backref=db.backref('preferences', cascade='all, delete-orphan', passive_deletes=True)
    )
    
    def __repr__(self):
        return f'<UserPreference {self.preference} for track {self.track_id} by user {self.user_id}>'


class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    activity_type = db.Column(db.String(20), nullable=False)  # 'play', 'download', 'bookmark'
    duration_listened = db.Column(db.Integer, default=0)  # in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='activities')
    track = db.relationship('Track', backref='activities')
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type} for track {self.track_id} by user {self.user_id}>'


class UserBookmark(db.Model):
    __tablename__ = 'user_bookmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='bookmarks')
    track = db.relationship(
        'Track',
        backref=db.backref('bookmarks', cascade='all, delete-orphan', passive_deletes=True)
    )
    
    __table_args__ = (db.UniqueConstraint('user_id', 'track_id', name='unique_user_bookmark'),)
    
    def __repr__(self):
        return f'<UserBookmark track {self.track_id} by user {self.user_id}>'


class Playlist(db.Model):
    __tablename__ = 'playlists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='playlists')
    tracks = db.relationship('Track', secondary='playlist_tracks', backref='playlists')
    
    def __repr__(self):
        return f'<Playlist {self.name} by {self.user.username if self.user else "Unknown"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'is_public': self.is_public,
            'track_count': len(self.tracks),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlaylistTrack(db.Model):
    __tablename__ = 'playlist_tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    playlist = db.relationship(
        'Playlist',
        backref=db.backref('playlist_tracks', cascade='all, delete-orphan', passive_deletes=True)
    )
    track = db.relationship(
        'Track',
        backref=db.backref('playlist_tracks', cascade='all, delete-orphan', passive_deletes=True)
    )
    
    __table_args__ = (db.UniqueConstraint('playlist_id', 'track_id', name='unique_playlist_track'),)
    
    def __repr__(self):
        return f'<PlaylistTrack playlist={self.playlist_id} track={self.track_id} pos={self.position}>'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.CONSUMER, nullable=False)
    region = db.Column(db.String(100))  # For KNN ML recommendations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "region": self.region,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }