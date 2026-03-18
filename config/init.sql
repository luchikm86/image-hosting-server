CREATE TABLE IF NOT EXISTS images (
    id            SERIAL PRIMARY KEY,
    filename      TEXT    NOT NULL,
    original_name TEXT    NOT NULL,
    size          INTEGER NOT NULL,
    upload_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_type     TEXT    NOT NULL
);