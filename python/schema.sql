-- Create the data_records table if it doesn't exist
CREATE TABLE IF NOT EXISTS data_records (
    id SERIAL PRIMARY KEY,
    data JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
); 