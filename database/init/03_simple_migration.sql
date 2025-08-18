-- Simple migration script that adds missing tables and columns
-- This script ignores errors if tables/columns already exist

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
    
    -- Base model timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_collection_id (collection_id),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='Upload job tracking for batch document processing';

-- Create folder_nodes table
CREATE TABLE IF NOT EXISTS folder_nodes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    collection_id INT NOT NULL,
    upload_job_id INT NULL,
    
    -- Hierarchy structure
    name VARCHAR(255) NOT NULL COMMENT 'Folder name',
    full_path VARCHAR(500) NOT NULL COMMENT 'Complete path from root',
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
    
    -- Base model timestamps
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