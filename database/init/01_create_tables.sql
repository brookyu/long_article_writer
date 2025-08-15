-- Long Article Writer Database Schema
-- Created: $(date)

-- Settings management for LLM providers, embedding models, web search
CREATE TABLE IF NOT EXISTS settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    provider VARCHAR(50) NOT NULL COMMENT 'Provider type: ollama, openai, anthropic, serpapi, etc.',
    key_alias VARCHAR(100) NOT NULL COMMENT 'Human-readable name for this configuration',
    encrypted_secret TEXT COMMENT 'Encrypted API key or secret',
    model_name VARCHAR(100) COMMENT 'Specific model name to use',
    config_json JSON COMMENT 'Additional provider-specific configuration',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether this configuration is currently active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_provider_alias (provider, key_alias),
    INDEX idx_provider (provider),
    INDEX idx_active (is_active)
) ENGINE=InnoDB COMMENT='Provider configurations and API keys';

-- Knowledge base collections for document organization
CREATE TABLE IF NOT EXISTS kb_collections (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    embedding_model VARCHAR(100) COMMENT 'Model used for embeddings in this collection',
    total_documents INT DEFAULT 0,
    total_chunks INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_collection_name (name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='Collections of documents for knowledge retrieval';

-- Document metadata and status tracking
CREATE TABLE IF NOT EXISTS kb_documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    collection_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    sha256 VARCHAR(64) NOT NULL COMMENT 'File hash for deduplication',
    file_path VARCHAR(500) COMMENT 'Local storage path',
    status ENUM('uploaded', 'processing', 'completed', 'failed') DEFAULT 'uploaded',
    error_message TEXT COMMENT 'Error details if processing failed',
    chunk_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id) ON DELETE CASCADE,
    UNIQUE KEY unique_collection_hash (collection_id, sha256),
    INDEX idx_collection_id (collection_id),
    INDEX idx_status (status),
    INDEX idx_sha256 (sha256)
) ENGINE=InnoDB COMMENT='Document metadata and ingestion status';

-- Document chunks for reference and debugging
CREATE TABLE IF NOT EXISTS kb_chunks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    document_id INT NOT NULL,
    chunk_index INT NOT NULL COMMENT 'Order within the document',
    text TEXT NOT NULL,
    char_count INT GENERATED ALWAYS AS (CHAR_LENGTH(text)) STORED,
    milvus_id VARCHAR(100) COMMENT 'Reference to Milvus vector ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (document_id) REFERENCES kb_documents(id) ON DELETE CASCADE,
    UNIQUE KEY unique_document_chunk (document_id, chunk_index),
    INDEX idx_document_id (document_id),
    INDEX idx_milvus_id (milvus_id)
) ENGINE=InnoDB COMMENT='Text chunks for tracking and reference';

-- Generated articles and their metadata
CREATE TABLE IF NOT EXISTS articles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255),
    topic VARCHAR(255) NOT NULL,
    collection_id INT COMMENT 'Primary knowledge base used',
    outline_json JSON COMMENT 'Generated outline structure',
    content_markdown TEXT COMMENT 'Current article content',
    markdown_path VARCHAR(500) COMMENT 'Path to exported markdown file',
    status ENUM('outlining', 'drafting', 'refining', 'completed', 'exported') DEFAULT 'outlining',
    word_count INT DEFAULT 0,
    source_count INT DEFAULT 0 COMMENT 'Number of sources cited',
    local_source_ratio DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Ratio of local vs web sources',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id) ON DELETE SET NULL,
    INDEX idx_collection_id (collection_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FULLTEXT idx_title_topic (title, topic)
) ENGINE=InnoDB COMMENT='Generated articles and their progress';

-- Background job tracking for async operations
CREATE TABLE IF NOT EXISTS jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type VARCHAR(50) NOT NULL COMMENT 'Job type: ingestion, outline, draft, refine, export',
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    payload_json JSON COMMENT 'Job input parameters',
    result_json JSON COMMENT 'Job output results',
    progress INT DEFAULT 0 COMMENT 'Progress percentage 0-100',
    error_message TEXT COMMENT 'Error details if job failed',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='Background job queue and status tracking';

-- Article sources for citation tracking
CREATE TABLE IF NOT EXISTS article_sources (
    id INT PRIMARY KEY AUTO_INCREMENT,
    article_id INT NOT NULL,
    source_type ENUM('local', 'web') NOT NULL,
    source_title VARCHAR(255),
    source_url VARCHAR(500) COMMENT 'URL for web sources',
    document_id INT COMMENT 'Reference to kb_documents for local sources',
    chunk_ids JSON COMMENT 'Array of chunk IDs that contributed',
    confidence_score DECIMAL(4,3) COMMENT 'Retrieval confidence score',
    citation_text TEXT COMMENT 'How this source was cited in the article',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES kb_documents(id) ON DELETE SET NULL,
    INDEX idx_article_id (article_id),
    INDEX idx_source_type (source_type),
    INDEX idx_document_id (document_id)
) ENGINE=InnoDB COMMENT='Source attribution and citation tracking';

-- Create a view for collection statistics
CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    c.id,
    c.name,
    c.description,
    c.embedding_model,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(DISTINCT ch.id) as chunk_count,
    COALESCE(SUM(d.size_bytes), 0) as total_size_bytes,
    COUNT(CASE WHEN d.status = 'completed' THEN 1 END) as completed_documents,
    COUNT(CASE WHEN d.status = 'failed' THEN 1 END) as failed_documents,
    c.created_at,
    c.updated_at
FROM kb_collections c
LEFT JOIN kb_documents d ON c.id = d.collection_id
LEFT JOIN kb_chunks ch ON d.id = ch.document_id
GROUP BY c.id, c.name, c.description, c.embedding_model, c.created_at, c.updated_at;

-- Insert default settings for local development
INSERT IGNORE INTO settings (provider, key_alias, model_name, is_active) VALUES
('ollama', 'Local Llama3.1', 'llama3.1:8b', TRUE),
('ollama', 'Local Embedding', 'nomic-embed-text', TRUE);

-- Create default collection for testing
INSERT IGNORE INTO kb_collections (name, description, embedding_model) VALUES
('Default Collection', 'Default knowledge base for initial testing', 'nomic-embed-text');