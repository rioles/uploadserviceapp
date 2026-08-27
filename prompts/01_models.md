# Role
You are a Django and PostgreSQL expert specializing in database modeling.

# Context
I am working on a Django 5.2 project named VideoStream.

Database: Aurora PostgreSQL
Django App: videos (already created)
Settings: videostream/settings/base.py
Auth: Keycloak via JWT — no django.contrib.auth.User
user_id is a UUID extracted from the JWT token, not a foreign key to a local users table.

# Task
Create the videos/models.py file containing three Django models: Video, VideoChunk, and VideoFormat, matching exactly the following SQL tables.

## Target SQL Tables
```sql
CREATE TABLE videos (
    id            UUID PRIMARY KEY,
    upload_id     TEXT NOT NULL,
    user_id       UUID NOT NULL,
    title         TEXT,
    description   TEXT,
    total_chunks  INTEGER NOT NULL,
    size_bytes    BIGINT,
    duration_s    INTEGER,
    status        TEXT DEFAULT 'processing',
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE video_chunks (
    id          UUID PRIMARY KEY,
    video_id    UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    s3_key      TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    UNIQUE (video_id, chunk_index)
);

CREATE TABLE video_formats (
    id           UUID PRIMARY KEY,
    video_id     UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    resolution   TEXT NOT NULL,
    s3_key       TEXT NOT NULL,
    codec        TEXT DEFAULT 'h264',
    bitrate_kbps INTEGER,
    ready        BOOLEAN DEFAULT false,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_videos_user_id   ON videos(user_id);
CREATE INDEX idx_chunks_video_id  ON video_chunks(video_id, chunk_index);
CREATE INDEX idx_chunks_s3_key    ON video_chunks(s3_key);
CREATE INDEX idx_formats_video_id ON video_formats(video_id);
CREATE INDEX idx_formats_s3_key   ON video_formats(s3_key);
