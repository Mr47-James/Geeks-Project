#!/usr/bin/env python3
"""
Complete database migration script to fix all missing tables and columns
"""
from flask import Flask
from index import init_db, db
from models.music import User, Role, Artist, Track, UserPreference, UserActivity, UserBookmark
from sqlalchemy import text, inspect
from werkzeug.security import generate_password_hash

def fix_database():
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            print("🔍 Checking database structure...")
            
            # Get all existing tables
            existing_tables = inspector.get_table_names()
            print(f"Existing tables: {existing_tables}")
            
            # Required tables and their expected columns
            required_tables = {
                'users': ['id', 'username', 'email', 'password_hash', 'role', 'region', 'created_at', 'updated_at'],
                'artists': ['id', 'name', 'bio', 'genre', 'country', 'created_at'],
                'tracks': ['id', 'title', 'album', 'genre', 'duration', 'release_year', 'file_path', 'file_size', 'bitrate', 'sample_rate', 'created_at', 'updated_at', 'artist_id', 'play_count', 'like_count', 'dislike_count'],
                'user_preferences': ['id', 'user_id', 'track_id', 'preference', 'created_at'],
                'user_activities': ['id', 'user_id', 'track_id', 'activity_type', 'duration_listened', 'timestamp'],
                'user_bookmarks': ['id', 'user_id', 'track_id', 'created_at']
            }
            
            # Check each required table
            for table_name, expected_columns in required_tables.items():
                if table_name not in existing_tables:
                    print(f"❌ Table '{table_name}' is missing")
                else:
                    # Check columns in existing table
                    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                    missing_columns = set(expected_columns) - set(existing_columns)
                    if missing_columns:
                        print(f"❌ Table '{table_name}' missing columns: {missing_columns}")
                    else:
                        print(f"✅ Table '{table_name}' has all required columns")
            
            print("\n🔧 Recreating all tables to ensure correct structure...")
            
            # Drop all tables and recreate them
            db.drop_all()
            db.create_all()
            
            print("✅ All tables recreated successfully!")
            
            # Verify the new structure
            print("\n🔍 Verifying new table structure...")
            inspector = inspect(db.engine)
            for table_name in required_tables.keys():
                if inspector.has_table(table_name):
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    print(f"✅ {table_name}: {columns}")
                else:
                    print(f"❌ {table_name}: NOT FOUND")
            
            # Create demo users
            print("\n👥 Creating demo users...")
            
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('techpass'),
                role=Role.TECHNICIAN,
                region='North America'
            )
            
            # Create regular user
            regular_user = User(
                username='user',
                email='user@example.com',
                password_hash=generate_password_hash('consumerpass'),
                role=Role.CONSUMER,
                region='North America'
            )
            
            db.session.add(admin_user)
            db.session.add(regular_user)
            
            # Create sample data if needed
            if Artist.query.count() == 0:
                print("🎵 Creating sample music data...")
                
                # Create sample artists
                artist1 = Artist(name='The Beatles', genre='Rock', country='UK')
                artist2 = Artist(name='Miles Davis', genre='Jazz', country='USA')
                artist3 = Artist(name='Daft Punk', genre='Electronic', country='France')
                
                db.session.add(artist1)
                db.session.add(artist2)
                db.session.add(artist3)
                db.session.flush()  # Get IDs
                
                # Create sample tracks
                tracks = [
                    Track(title='Hey Jude', album='The Beatles 1967-1970', genre='Rock', duration=431, artist_id=artist1.id, play_count=1500, like_count=120),
                    Track(title='Let It Be', album='Let It Be', genre='Rock', duration=243, artist_id=artist1.id, play_count=1200, like_count=95),
                    Track(title='Kind of Blue', album='Kind of Blue', genre='Jazz', duration=540, artist_id=artist2.id, play_count=800, like_count=75),
                    Track(title='One More Time', album='Discovery', genre='Electronic', duration=320, artist_id=artist3.id, play_count=2000, like_count=180),
                    Track(title='Get Lucky', album='Random Access Memories', genre='Electronic', duration=367, artist_id=artist3.id, play_count=1800, like_count=150),
                ]
                
                for track in tracks:
                    db.session.add(track)
            
            db.session.commit()
            
            print("✅ Demo users created:")
            print("   - admin@example.com / techpass (TECHNICIAN)")
            print("   - user@example.com / consumerpass (CONSUMER)")
            print("✅ Sample music data created!")
            print("\n🎉 Database setup completed successfully!")
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    fix_database()