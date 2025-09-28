-- Music Manager Database Seed Data
-- This file contains sample data for the Music Manager application

-- Create database (run this separately if needed)
-- CREATE DATABASE GeeksINS;

-- Sample Artists
INSERT INTO artists (name, bio, genre, country, created_at) VALUES
('The Beatles', 'English rock band formed in Liverpool in 1960, widely regarded as the most influential band of all time.', 'Rock', 'United Kingdom', NOW()),
('Miles Davis', 'American trumpeter, bandleader, and composer, one of the most influential and acclaimed figures in jazz.', 'Jazz', 'United States', NOW()),
('Ludwig van Beethoven', 'German composer and pianist, crucial figure in the transition between Classical and Romantic eras.', 'Classical', 'Germany', NOW()),
('Bob Dylan', 'American singer-songwriter, widely regarded as one of the greatest songwriters of all time.', 'Folk Rock', 'United States', NOW()),
('Daft Punk', 'French electronic music duo formed in 1993, known for their innovative use of electronic instruments.', 'Electronic', 'France', NOW());

-- Sample Tracks (assuming artist IDs 1-5 from above)
INSERT INTO tracks (title, album, genre, duration, release_year, artist_id, play_count, like_count, dislike_count, created_at, updated_at) VALUES
-- The Beatles (artist_id = 1)
('Hey Jude', 'Hey Jude', 'Rock', 431, 1968, 1, 850, 95, 5, NOW(), NOW()),
('Let It Be', 'Let It Be', 'Rock', 243, 1970, 1, 720, 88, 3, NOW(), NOW()),
('Yesterday', 'Help!', 'Pop', 125, 1965, 1, 650, 92, 2, NOW(), NOW()),
('Come Together', 'Abbey Road', 'Rock', 259, 1969, 1, 580, 85, 8, NOW(), NOW()),

-- Miles Davis (artist_id = 2)
('So What', 'Kind of Blue', 'Jazz', 562, 1959, 2, 420, 78, 4, NOW(), NOW()),
('All Blues', 'Kind of Blue', 'Jazz', 691, 1959, 2, 380, 72, 6, NOW(), NOW()),
('Bitches Brew', 'Bitches Brew', 'Jazz Fusion', 1620, 1970, 2, 290, 65, 12, NOW(), NOW()),

-- Beethoven (artist_id = 3)
('Symphony No. 9 in D minor, Op. 125', 'Symphony No. 9', 'Classical', 4200, 1824, 3, 950, 98, 1, NOW(), NOW()),
('Moonlight Sonata', 'Piano Sonata No. 14', 'Classical', 900, 1801, 3, 780, 89, 3, NOW(), NOW()),
('Für Elise', 'Bagatelle No. 25', 'Classical', 210, 1810, 3, 680, 91, 2, NOW(), NOW()),

-- Bob Dylan (artist_id = 4)
('Like a Rolling Stone', 'Highway 61 Revisited', 'Folk Rock', 369, 1965, 4, 620, 82, 7, NOW(), NOW()),
('Blowin'' in the Wind', 'The Freewheelin'' Bob Dylan', 'Folk', 168, 1963, 4, 540, 79, 5, NOW(), NOW()),
('The Times They Are a-Changin''', 'The Times They Are a-Changin''', 'Folk', 194, 1964, 4, 480, 75, 9, NOW(), NOW()),

-- Daft Punk (artist_id = 5)
('One More Time', 'Discovery', 'Electronic', 320, 2001, 5, 890, 94, 4, NOW(), NOW()),
('Get Lucky', 'Random Access Memories', 'Electronic', 367, 2013, 5, 1200, 99, 2, NOW(), NOW()),
('Around the World', 'Homework', 'Electronic', 428, 1997, 5, 670, 86, 6, NOW(), NOW());

-- Sample User Preferences (optional)
INSERT INTO user_preferences (track_id, preference, created_at) VALUES
(1, 'like', NOW()),
(2, 'like', NOW()),
(3, 'like', NOW()),
(8, 'like', NOW()),
(15, 'like', NOW()),
(7, 'dislike', NOW()),
(13, 'dislike', NOW());

-- Update sequences (PostgreSQL specific)
SELECT setval('artists_id_seq', (SELECT MAX(id) FROM artists));
SELECT setval('tracks_id_seq', (SELECT MAX(id) FROM tracks));
SELECT setval('user_preferences_id_seq', (SELECT MAX(id) FROM user_preferences));