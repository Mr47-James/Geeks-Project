from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()

def init_db(app: Flask):
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:password@localhost/musicdb"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return db
