-- Add file_list column to upload_jobs table if it doesn't exist
-- This column is needed to store the list of files for multiple file uploads

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE upload_jobs ADD COLUMN file_list JSON NULL;') INTO @sql
FROM information_schema.columns 
WHERE table_schema = 'long_article_writer' 
  AND table_name = 'upload_jobs' 
  AND column_name = 'file_list'
HAVING COUNT(*) = 0;

PREPARE stmt FROM COALESCE(@sql, 'SELECT "file_list column already exists" as message;');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;