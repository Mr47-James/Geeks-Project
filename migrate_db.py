#!/usr/bin/env python3
"""
Database migration script to add missing columns to users table
"""
from flask import Flask
from index import init_db, db
from models.music import User, Role
from sqlalchemy import text, inspect

def migrate_database():
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        try:
            # Check current table structure using inspector
            inspector = inspect(db.engine)
            
            # Check if users table exists
            if not inspector.has_table('users'):
                print("Users table doesn't exist. Creating all tables...")
                db.create_all()
                print("✅ All tables created successfully!")
                return
            
            # Get existing columns
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            print(f"Existing columns in users table: {existing_columns}")
            
            # Add missing columns if they don't exist
            columns_to_add = [
                ("email", "VARCHAR(120) UNIQUE"),
                ("password_hash", "VARCHAR(255)"),
                ("role", "VARCHAR(20) DEFAULT 'consumer'"),
                ("region", "VARCHAR(100)"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            # Use connection.execute() instead of engine.execute()
            with db.engine.connect() as connection:
                for column_name, column_def in columns_to_add:
                    if column_name not in existing_columns:
                        try:
                            sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_def};"
                            print(f"Adding column: {sql}")
                            connection.execute(text(sql))
                            connection.commit()
                            print(f"✅ Added column: {column_name}")
                        except Exception as e:
                            print(f"❌ Error adding column {column_name}: {e}")
                            connection.rollback()
                    else:
                        print(f"✅ Column {column_name} already exists")
            
            print("✅ Database migration completed successfully!")
            
            # Create demo users if none exist
            if User.query.count() == 0:
                print("Creating demo users...")
                from werkzeug.security import generate_password_hash
                
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
                db.session.commit()
                print("✅ Demo users created:")
                print("   - admin@example.com / techpass (TECHNICIAN)")
                print("   - user@example.com / consumerpass (CONSUMER)")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_database()