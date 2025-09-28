"""
Database initialization and seeding utilities
"""
from flask import Flask
from werkzeug.security import generate_password_hash

from index import init_db, db
from models.music import Artist, Track, UserPreference, User, Role


def _create_user(*, username: str, email: str, password: str, role: Role) -> User:
    """Utility to create a user with an email username."""
    return User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
    )

def create_sample_data():
    """Create sample data for testing"""
    
    # Create sample artists
    artists_data = [
        {
            'name': 'The Beatles',
            'bio': 'English rock band formed in Liverpool in 1960, widely regarded as the most influential band of all time.',
            'genre': 'Rock',
            'country': 'United Kingdom'
        },
        {
            'name': 'Miles Davis',
            'bio': 'American trumpeter, bandleader, and composer, one of the most influential and acclaimed figures in jazz.',
            'genre': 'Jazz',
            'country': 'United States'
        },
        {
            'name': 'Ludwig van Beethoven',
            'bio': 'German composer and pianist, crucial figure in the transition between Classical and Romantic eras.',
            'genre': 'Classical',
            'country': 'Germany'
        },
        {
            'name': 'Bob Dylan',
            'bio': 'American singer-songwriter, widely regarded as one of the greatest songwriters of all time.',
            'genre': 'Folk Rock',
            'country': 'United States'
        },
        {
            'name': 'Daft Punk',
            'bio': 'French electronic music duo formed in 1993, known for their innovative use of electronic instruments.',
            'genre': 'Electronic',
            'country': 'France'
        }
    ]
    
    artists = []
    for artist_data in artists_data:
        artist = Artist(**artist_data)
        db.session.add(artist)
        artists.append(artist)
    
    db.session.flush()  # Flush to get IDs
    
    # Create sample tracks
    tracks_data = [
        # The Beatles
        {'title': 'Hey Jude', 'album': 'Hey Jude', 'genre': 'Rock', 'duration': 431, 'release_year': 1968, 'artist_id': artists[0].id},
        {'title': 'Let It Be', 'album': 'Let It Be', 'genre': 'Rock', 'duration': 243, 'release_year': 1970, 'artist_id': artists[0].id},
        {'title': 'Yesterday', 'album': 'Help!', 'genre': 'Pop', 'duration': 125, 'release_year': 1965, 'artist_id': artists[0].id},
        {'title': 'Come Together', 'album': 'Abbey Road', 'genre': 'Rock', 'duration': 259, 'release_year': 1969, 'artist_id': artists[0].id},
        
        # Miles Davis
        {'title': 'So What', 'album': 'Kind of Blue', 'genre': 'Jazz', 'duration': 562, 'release_year': 1959, 'artist_id': artists[1].id},
        {'title': 'All Blues', 'album': 'Kind of Blue', 'genre': 'Jazz', 'duration': 691, 'release_year': 1959, 'artist_id': artists[1].id},
        {'title': 'Bitches Brew', 'album': 'Bitches Brew', 'genre': 'Jazz Fusion', 'duration': 1620, 'release_year': 1970, 'artist_id': artists[1].id},
        
        # Beethoven
        {'title': 'Symphony No. 9 in D minor, Op. 125', 'album': 'Symphony No. 9', 'genre': 'Classical', 'duration': 4200, 'release_year': 1824, 'artist_id': artists[2].id},
        {'title': 'Moonlight Sonata', 'album': 'Piano Sonata No. 14', 'genre': 'Classical', 'duration': 900, 'release_year': 1801, 'artist_id': artists[2].id},
        {'title': 'Für Elise', 'album': 'Bagatelle No. 25', 'genre': 'Classical', 'duration': 210, 'release_year': 1810, 'artist_id': artists[2].id},
        
        # Bob Dylan
        {'title': 'Like a Rolling Stone', 'album': 'Highway 61 Revisited', 'genre': 'Folk Rock', 'duration': 369, 'release_year': 1965, 'artist_id': artists[3].id},
        {'title': 'Blowin\' in the Wind', 'album': 'The Freewheelin\' Bob Dylan', 'genre': 'Folk', 'duration': 168, 'release_year': 1963, 'artist_id': artists[3].id},
        {'title': 'The Times They Are a-Changin\'', 'album': 'The Times They Are a-Changin\'', 'genre': 'Folk', 'duration': 194, 'release_year': 1964, 'artist_id': artists[3].id},
        
        # Daft Punk
        {'title': 'One More Time', 'album': 'Discovery', 'genre': 'Electronic', 'duration': 320, 'release_year': 2001, 'artist_id': artists[4].id},
        {'title': 'Get Lucky', 'album': 'Random Access Memories', 'genre': 'Electronic', 'duration': 367, 'release_year': 2013, 'artist_id': artists[4].id},
        {'title': 'Around the World', 'album': 'Homework', 'genre': 'Electronic', 'duration': 428, 'release_year': 1997, 'artist_id': artists[4].id},
    ]
    
    tracks = []
    for track_data in tracks_data:
        track = Track(**track_data)
        # Add some random play counts and likes for demo
        import random
        track.play_count = random.randint(0, 1000)
        track.like_count = random.randint(0, 100)
        track.dislike_count = random.randint(0, 20)
        db.session.add(track)
        tracks.append(track)

    # Create sample users
    if User.query.count() == 0:
        demo_users = [
            _create_user(username="admin", email="admin@example.com", password="techpass", role=Role.TECHNICIAN),
            _create_user(username="user", email="user@example.com", password="consumerpass", role=Role.CONSUMER),
        ]

        for user in demo_users:
            db.session.add(user)
    
    db.session.commit()
    print(f"Created {len(artists)} artists, {len(tracks)} tracks, and {User.query.count()} users")

def init_database(app):
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if data already exists
        if Artist.query.count() == 0:
            print("Creating sample data...")
            create_sample_data()
            print("Sample data created successfully!")
        else:
            print("Database already contains data.")

        if User.query.count() == 0:
            demo_users = [
                _create_user(username="admin", email="admin@example.com", password="techpass", role=Role.TECHNICIAN),
                _create_user(username="user", email="user@example.com", password="consumerpass", role=Role.CONSUMER),
            ]

            for user in demo_users:
                db.session.add(user)
            db.session.commit()
            print("Seeded demo users.")

if __name__ == '__main__':
    # Create Flask app for standalone execution
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:password@localhost/GeeksINS"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database
    init_db(app)
    init_database(app)