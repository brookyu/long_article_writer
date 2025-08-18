-- Add missing upload_jobs table and update kb_documents with new columns
-- Migration script for upload job functionality

-- Create upload_jobs table
CREATE TABLE IF NOT EXISTS upload_jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    collection_id INT NOT NULL,
    job_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Progress tracking
    total_files INT DEFAULT 0,
    processed_files INT DEFAULT 0,
    successful_files INT DEFAULT 0,
    failed_files INT DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    -- Job metadata
    upload_path VARCHAR(500) NULL COMMENT 'Original upload path',
    folder_structure JSON NULL COMMENT 'Folder hierarchy',
    file_list JSON NULL COMMENT 'List of files to process',
    error_log JSON NULL COMMENT 'Detailed error information',
    
    -- Configuration
    max_file_size_mb INT DEFAULT 10,
    preserve_structure BOOLEAN DEFAULT TRUE,
    skip_unsupported BOOLEAN DEFAULT TRUE,
    
    -- Timestamps from BaseModel
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_collection_id (collection_id),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='Upload job tracking for batch document processing';

-- Add missing columns to kb_documents table (ignore errors if columns exist)
SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN relative_path VARCHAR(500) COMMENT \'Path within uploaded folder structure\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'relative_path'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column relative_path already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN parent_folder VARCHAR(255) COMMENT \'Parent folder name\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'parent_folder'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column parent_folder already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN folder_depth INT DEFAULT 0 COMMENT \'Depth level in folder hierarchy\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'folder_depth'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column folder_depth already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN folder_path VARCHAR(1000) COMMENT \'Full folder path from root\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'folder_path'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column folder_path already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN upload_job_id INT NULL COMMENT \'Associated upload job\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'upload_job_id'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column upload_job_id already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN folder_metadata JSON COMMENT \'Folder structure and metadata\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'folder_metadata'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column folder_metadata already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN document_tags JSON COMMENT \'Auto-generated tags based on folder location\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'document_tags'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column document_tags already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD COLUMN content_category VARCHAR(100) COMMENT \'Category inferred from folder structure\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND COLUMN_NAME = 'content_category'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column content_category already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create folder_nodes table for hierarchical folder management
CREATE TABLE IF NOT EXISTS folder_nodes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    collection_id INT NOT NULL,
    upload_job_id INT NULL,
    
    -- Hierarchy structure
    name VARCHAR(255) NOT NULL COMMENT 'Folder name',
    full_path VARCHAR(1000) NOT NULL COMMENT 'Complete path from root',
    parent_id INT NULL COMMENT 'Parent folder',
    depth INT DEFAULT 0 COMMENT 'Depth level in hierarchy',
    
    -- Content statistics
    document_count INT DEFAULT 0 COMMENT 'Number of documents in this folder',
    total_documents INT DEFAULT 0 COMMENT 'Total documents including subfolders',
    total_size_bytes BIGINT DEFAULT 0 COMMENT 'Total size of all documents',
    
    -- Metadata
    folder_metadata JSON COMMENT 'Additional folder metadata',
    auto_tags JSON COMMENT 'Auto-generated tags based on content',
    content_summary TEXT COMMENT 'AI-generated summary of folder contents',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Timestamps from BaseModel
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id) ON DELETE CASCADE,
    FOREIGN KEY (upload_job_id) REFERENCES upload_jobs(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_id) REFERENCES folder_nodes(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_collection_path (collection_id, full_path),
    INDEX idx_collection_id (collection_id),
    INDEX idx_parent_id (parent_id),
    INDEX idx_full_path (full_path)
) ENGINE=InnoDB COMMENT='Hierarchical folder structure for document organization';

-- Add foreign key constraint for upload_job_id (after upload_jobs table is created)
SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_documents ADD CONSTRAINT fk_documents_upload_job FOREIGN KEY (upload_job_id) REFERENCES upload_jobs(id) ON DELETE SET NULL;') INTO @sql
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_documents' AND CONSTRAINT_NAME = 'fk_documents_upload_job'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Foreign key fk_documents_upload_job already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update kb_collections to add relationship back-references
SET @sql = NULL;
SELECT CONCAT('ALTER TABLE kb_collections ADD COLUMN total_upload_jobs INT DEFAULT 0 COMMENT \'Total number of upload jobs\';') INTO @sql
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kb_collections' AND COLUMN_NAME = 'total_upload_jobs'
HAVING COUNT(*) = 0;
PREPARE stmt FROM COALESCE(@sql, 'SELECT "Column total_upload_jobs already exists" AS message');
EXECUTE stmt;
DEALLOCATE PREPARE stmt;