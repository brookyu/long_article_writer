-- Add updated_at column to kb_chunks table
-- This column is needed for SQLAlchemy BaseModel compatibility

-- Simple approach: Add column if it doesn't exist (ignore error if it does)
ALTER TABLE kb_chunks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
