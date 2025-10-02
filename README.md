# Atlantes Music Streaming Platform

A comprehensive music streaming web application built with Flask, featuring user authentication, track management, playlists, and machine learning-powered recommendations.

## Overview

Atlantes is a full-featured music streaming platform that allows users to upload, organize, and stream audio files. The application supports user roles (consumers and technicians), provides ML-based music recommendations, and includes features like playlists, bookmarks, and social interactions.

![Shot1](Screenshots/Screenshot%20from%202025-09-29%2000-42-19.png)
![Shot1](Screenshots/Screenshot%20from%202025-09-29%2000-42-20.png)
![Shot1](Screenshots/Screenshot%20from%202025-09-29%2000-42-27.png)
![Shot1](Screenshots/Screenshot%20from%202025-09-29%2000-42-31.png)



## Technologies Used

### Backend Framework
- **Flask**: Lightweight WSGI web application framework for Python. Handles routing, request/response processing, session management, and template rendering.
- **SQLAlchemy**: Python SQL toolkit and Object-Relational Mapping (ORM) library. Manages database operations, relationships, and migrations.
- **Flask-Bcrypt**: Flask extension for password hashing using bcrypt algorithm. Ensures secure password storage.

### Audio Processing
- **Mutagen**: Python module for handling audio metadata. Extracts information like title, artist, album, duration, bitrate, and sample rate from audio files (MP3, FLAC, WAV, AAC, M4A, OGG).
- **Werkzeug**: WSGI utility library for Python. Provides secure filename handling and file streaming capabilities.

### Data Processing & Machine Learning
- **Pandas**: Data manipulation and analysis library. Used for processing user activity data and generating insights.
- **NumPy**: Fundamental package for array computing. Supports numerical operations in ML algorithms.
- **Scikit-learn (implied)**: Machine learning library for building recommendation algorithms based on user preferences and activity patterns.

### Frontend Technologies
- **Jinja2**: Template engine for Python. Renders dynamic HTML templates with Flask.
- **HTMX**: JavaScript library for dynamic web applications. Enables AJAX requests and DOM updates without complex JavaScript frameworks.
- **Bootstrap**: CSS framework for responsive web design. Provides pre-built components and styling.
- **JavaScript**: Client-side scripting for interactive features like audio playback controls and dynamic form submissions.

### Database
- **SQLite/PostgreSQL**: Database engine for data persistence. Stores user accounts, tracks, artists, playlists, and activity logs.

### Additional Libraries
- **Collections.Counter**: Python utility for counting hashable objects. Used for genre distribution analysis.
- **UUID**: Generates unique identifiers for file uploads and sessions.
- **ZipFile**: Handles batch uploads of compressed audio archives.
- **Pathlib**: Object-oriented filesystem paths. Manages file system operations securely.
- **Datetime**: Date and time handling for timestamps and scheduling.

## Special Features

### Machine Learning Recommendations
The platform implements sophisticated ML algorithms for personalized music recommendations:

- **Collaborative Filtering**: Analyzes user preferences (likes/dislikes) and activity patterns to suggest similar tracks.
- **Content-Based Filtering**: Recommends tracks based on audio metadata (genre, artist, album) and user listening history.
- **Hybrid Approach**: Combines multiple recommendation strategies for improved accuracy.
- **Real-time Learning**: Updates recommendations based on user interactions (play, bookmark, like/dislike).
- **KNN Algorithm**: Uses K-Nearest Neighbors for finding similar users and tracks based on region and preferences.

### Audio Streaming
- **Direct File Streaming**: Serves audio files directly from the server with proper MIME types.
- **Range Requests**: Supports seeking and partial content delivery for efficient streaming.
- **Metadata Integration**: Displays track information during playback (title, artist, duration).
- **Cross-browser Compatibility**: Works across different browsers with fallback mechanisms.

### Batch Upload System
- **Multi-format Support**: Accepts individual files or ZIP archives containing multiple audio files.
- **Automatic Metadata Extraction**: Uses Mutagen to parse audio tags and populate track information.
- **Duplicate Prevention**: Checks for existing tracks and artists to avoid duplicates.
- **Progress Tracking**: Session-based upload state management for large batches.
- **File Validation**: Ensures only supported audio formats are processed.

### User Management & Roles
- **Role-Based Access Control**: Two user types - Consumers (regular users) and Technicians (administrators).
- **Secure Authentication**: Password hashing, session management, and CSRF protection.
- **Profile Management**: User settings, password changes, and account deletion.
- **Activity Tracking**: Logs user interactions for analytics and recommendations.

### Social Features
- **Playlists**: User-created collections of tracks with public/private visibility.
- **Bookmarks**: Save favorite tracks for quick access.
- **Like/Dislike System**: Rate tracks to improve recommendations.
- **User Activity Logging**: Track plays, views, and interactions for ML training.

### Analytics & Statistics
- **Track Analytics**: Play counts, like/dislike ratios, and popularity metrics.
- **Genre Distribution**: Visual breakdown of music library composition.
- **User Engagement**: Activity logs and preference analysis.
- **Performance Metrics**: File size, bitrate, and quality statistics.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- SQLite (default) or PostgreSQL (recommended for production)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd atlantes-music
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python -c "from index import init_db, db; from flask import Flask; app = Flask(__name__); init_db(app); app.app_context().push(); db.create_all()"
   ```

5. **Run database migrations (if any)**
   ```bash
   python migrate_user_activity_cascade.py
   ```

6. **Seed sample data (optional)**
   ```bash
   python -c "from flask import Flask; from index import init_db, db; from database.index import create_sample_data; app = Flask(__name__); init_db(app); app.app_context().push(); create_sample_data()"
   ```

7. **Start the application**
   ```bash
   python app.py
   ```

8. **Access the application**
   Open http://localhost:5000 in your browser

## Usage

### For Consumers (Regular Users)

1. **Registration & Login**
   - Create an account with username, email, and password
   - Login to access the platform

2. **Browsing Music**
   - View popular tracks and artists on the home page
   - Browse tracks by genre, artist, or search terms
   - View detailed track and artist information

3. **Audio Playback**
   - Click play buttons to stream audio
   - Use player controls for pause, seek, and volume
   - View track metadata during playback

4. **Personal Features**
   - Create and manage playlists
   - Bookmark favorite tracks
   - Like/dislike tracks to improve recommendations
   - View personalized recommendations

5. **Upload Music**
   - Upload individual audio files or ZIP archives
   - Automatic metadata extraction and organization
   - Manage your uploaded tracks

### For Technicians (Administrators)

1. **Content Management**
   - Upload and manage tracks in bulk
   - Edit track metadata and information
   - Delete tracks and manage artists

2. **User Management**
   - View user statistics and activity
   - Manage user accounts and permissions

3. **Analytics Dashboard**
   - View platform statistics and metrics
   - Monitor system performance and usage

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /signup` - User registration
- `GET /logout` - User logout

### Tracks
- `GET /tracks` - List all tracks (technician)
- `GET /tracks/<id>` - View track details
- `POST /tracks/<id>/edit` - Edit track (technician)
- `POST /tracks/<id>/delete` - Delete track (technician)
- `POST /tracks/<id>/like` - Like track
- `POST /tracks/<id>/dislike` - Dislike track

### Audio Streaming
- `GET /audio/<track_id>` - Stream audio file
- `GET /api/track/<track_id>/info` - Get track metadata for player

### User Management
- `GET /api/user/profile` - Get user profile
- `POST /api/user/profile` - Update user profile
- `POST /api/user/change-password` - Change password
- `POST /api/user/delete-account` - Delete account

### Playlists
- `POST /client/playlists/create` - Create playlist
- `GET /client/playlists/<id>` - View playlist
- `POST /client/playlists/<id>/add-track` - Add track to playlist
- `POST /client/playlists/<id>/remove-track` - Remove track from playlist

### Recommendations
- `GET /recommendations/<track_id>` - Get ML-based recommendations

### Upload
- `POST /upload/preview` - Preview batch upload
- `POST /upload/confirm` - Confirm and process upload

## Configuration

### Environment Variables
- `UPLOAD_FOLDER` - Directory for uploaded files (default: ./uploads)
- `MAX_CONTENT_LENGTH` - Maximum file size (default: 200MB)

### Database Configuration
Modify `index.py` to configure database connection:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music.db'  # or PostgreSQL URI
```

## Development

### Project Structure
```
atlantes-01/
├── app.py                 # Main application
├── index.py              # Database initialization
├── models/
│   └── music.py          # Database models
├── templates/            # Jinja2 templates
├── static/               # CSS, JS, images
├── uploads/              # User uploads
├── database/             # Sample data
└── migrations/           # Database migrations
```

### Running Tests
```bash
python -m pytest tests/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on the GitHub repository or contact the development team.

## Note

The Platform is unstable and still under developpment, use it with caution.
