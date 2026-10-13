ALTER TABLE users ALTER COLUMN google_sub DROP NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
UPDATE users SET display_name = COALESCE(display_name, 'Learner') WHERE display_name IS NULL;
