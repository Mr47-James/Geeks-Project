#!/usr/bin/env python3
"""
Database migration script to add CASCADE delete to user_activities.user_id foreign key
"""
from flask import Flask
from index import init_db, db
from sqlalchemy import text, inspect

def migrate_user_activity_cascade():
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        try:
            # Check current table structure using inspector
            inspector = inspect(db.engine)

            # Check if user_activities table exists
            if not inspector.has_table('user_activities'):
                print("user_activities table doesn't exist. Creating all tables...")
                db.create_all()
                print("✅ All tables created successfully!")
                return

            print("Checking user_activities table foreign key constraints...")

            # Get existing foreign keys
            foreign_keys = inspector.get_foreign_keys('user_activities')
            print(f"Existing foreign keys in user_activities: {foreign_keys}")

            # Check if user_id foreign key has CASCADE
            user_fk = None
            for fk in foreign_keys:
                if 'user_id' in fk.get('constrained_columns', []):
                    user_fk = fk
                    break

            if user_fk:
                options = user_fk.get('options', {})
                if options.get('ondelete') == 'CASCADE':
                    print("✅ user_id foreign key already has CASCADE delete")
                    return
                else:
                    print("❌ user_id foreign key exists but no CASCADE delete. Need to drop and recreate.")

                    # Drop existing foreign key
                    fk_name = user_fk.get('name')
                    if fk_name:
                        with db.engine.connect() as connection:
                            try:
                                drop_sql = f"ALTER TABLE user_activities DROP CONSTRAINT {fk_name};"
                                print(f"Dropping constraint: {drop_sql}")
                                connection.execute(text(drop_sql))
                                connection.commit()
                                print("✅ Dropped existing foreign key constraint")
                            except Exception as e:
                                print(f"❌ Error dropping constraint: {e}")
                                connection.rollback()
                                return

            # Add new foreign key with CASCADE
            with db.engine.connect() as connection:
                try:
                    add_sql = """
                    ALTER TABLE user_activities
                    ADD CONSTRAINT fk_user_activities_user_id
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
                    """
                    print(f"Adding CASCADE foreign key: {add_sql}")
                    connection.execute(text(add_sql))
                    connection.commit()
                    print("✅ Added CASCADE foreign key to user_activities.user_id")
                except Exception as e:
                    print(f"❌ Error adding CASCADE foreign key: {e}")
                    connection.rollback()

            print("✅ Database migration completed successfully!")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_user_activity_cascade()
