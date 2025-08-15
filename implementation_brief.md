# Long Article Writer - Implementation Project Brief

## Executive Summary
Implementation of a sophisticated web application for generating high-quality, research-backed long-form articles using local knowledge bases and LLMs. The system combines vector search, agentic workflows, and streaming interfaces to create a comprehensive content generation platform.

## Project Scope & Objectives

### Primary Objectives
1. **Knowledge-First Content Generation**: Prioritize local knowledge base research over web search
2. **Structured Writing Workflow**: Guide users through research → outline → draft → refine → export
3. **Transparent AI Process**: Streaming UX with visible citations and source attribution
4. **Local-First Privacy**: Keep documents and processing local with optional remote providers

### Success Metrics
- Generate 3000+ word articles with 90% local knowledge base coverage
- Outline generation within 10 seconds using local LLM
- Draft streaming starts within 5 seconds
- Support 100MB+ document collections without performance degradation

## Technical Architecture

### Infrastructure Stack
```
Frontend: React 18 + TypeScript + shadcn/ui + Vite
Backend: Python 3.11 + FastAPI + Uvicorn
Database: MySQL 8.0 (settings, metadata, job tracking)
Vector Store: Milvus (document embeddings and retrieval)
LLM: Ollama (local models) + optional remote providers
Search: Configurable web search providers
Deployment: Docker Compose for local development
Monitoring: Sentry (frontend + backend)
```

### Key Components

#### 1. Knowledge Base Management System
- **Document Ingestion Pipeline**: PDF/MD/TXT parsing → chunking → embedding → Milvus storage
- **Collection Management**: Logical grouping of documents for retrieval contexts
- **Metadata Tracking**: File hashes, timestamps, ingestion status, source attribution

#### 2. Agentic Article Generation
- **Research Agent**: Local retrieval + web search fallback with confidence thresholds
- **Outline Agent**: Structure generation based on retrieved knowledge
- **Draft Agent**: Section-by-section content generation with streaming
- **Refinement Agent**: Targeted improvements based on user feedback

#### 3. Streaming Chat Interface
- **Real-time Communication**: Server-Sent Events for token streaming
- **Interactive Workflow**: Progressive disclosure of outline → draft → refinement
- **Source Attribution**: Inline citations with knowledge base vs web distinction

## Implementation Strategy

### Phase 1: Foundation (M0-M1)
**Duration**: 1-2 weeks
**Priority**: Critical Infrastructure

#### M0: Project Scaffolding
- [ ] Docker Compose setup (MySQL, Milvus, Ollama)
- [ ] FastAPI backend with basic project structure
- [ ] React frontend with Vite and shadcn/ui
- [ ] Sentry integration for error monitoring
- [ ] Database schema creation and migrations

#### M1: Knowledge Base Core
- [ ] Collection CRUD operations
- [ ] File upload handling (multipart)
- [ ] Document parsing pipeline (PDF, MD, TXT)
- [ ] Chunking strategy implementation
- [ ] Milvus embedding and storage
- [ ] Basic retrieval testing

### Phase 2: Core Features (M2-M3)
**Duration**: 2-3 weeks
**Priority**: Essential User Workflows

#### M2: Writing Workspace
- [ ] Chat interface with streaming responses
- [ ] Collection selection sidebar
- [ ] Topic input and outline generation
- [ ] Basic message history and state management
- [ ] Progress indicators and loading states

#### M3: Article Generation
- [ ] Outline generation with local knowledge retrieval
- [ ] Draft generation with section streaming
- [ ] Citation system and source attribution
- [ ] Refinement workflow for targeted improvements
- [ ] Draft persistence and version tracking

### Phase 3: Configuration & Export (M4-M5)
**Duration**: 1-2 weeks
**Priority**: Production Readiness

#### M4: Settings Management
- [ ] LLM provider configuration (Ollama + remote)
- [ ] Embedding model selection
- [ ] Web search provider setup
- [ ] Secret encryption and storage
- [ ] Settings persistence and validation

#### M5: Export & Finalization
- [ ] Markdown export with front-matter
- [ ] File download links in chat interface
- [ ] Article metadata and archiving
- [ ] Final integration testing
- [ ] Documentation and deployment guides

## Technical Implementation Details

### Data Models

#### Core Tables
```sql
-- Settings management
CREATE TABLE settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    provider VARCHAR(50) NOT NULL,
    key_alias VARCHAR(100) NOT NULL,
    encrypted_secret TEXT,
    model_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Knowledge base collections
CREATE TABLE kb_collections (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document metadata
CREATE TABLE kb_documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    collection_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    sha256 VARCHAR(64),
    status ENUM('uploaded', 'processing', 'completed', 'failed'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id)
);

-- Document chunks for tracking
CREATE TABLE kb_chunks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    document_id INT NOT NULL,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES kb_documents(id)
);

-- Generated articles
CREATE TABLE articles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255),
    topic VARCHAR(255) NOT NULL,
    collection_id INT,
    markdown_path VARCHAR(500),
    status ENUM('drafting', 'completed', 'exported'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES kb_collections(id)
);

-- Background job tracking
CREATE TABLE jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type VARCHAR(50) NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed'),
    payload_json TEXT,
    result_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### API Endpoints

#### Settings Management
```python
POST /api/settings          # Upsert provider settings
GET /api/settings           # Retrieve current settings
DELETE /api/settings/{id}   # Remove provider configuration
```

#### Knowledge Base
```python
POST /api/kb/collections              # Create collection
GET /api/kb/collections               # List collections
DELETE /api/kb/collections/{id}       # Delete collection

POST /api/kb/{collection_id}/upload   # Upload documents
GET /api/kb/{collection_id}/documents # List documents
DELETE /api/kb/documents/{id}         # Remove document
```

#### Article Generation
```python
POST /api/write/outline    # Generate outline from topic + collection
POST /api/write/draft      # Generate draft from outline
POST /api/write/refine     # Refine specific sections
POST /api/write/export     # Export article as markdown
```

### Frontend Architecture

#### Component Structure
```
src/
├── components/
│   ├── ui/              # shadcn/ui components
│   ├── settings/        # Settings management
│   ├── knowledge-base/  # Collection and document management
│   ├── chat/           # Streaming chat interface
│   └── export/         # Article export and download
├── hooks/
│   ├── useChat.ts      # Chat state and streaming
│   ├── useSettings.ts  # Settings management
│   └── useKnowledgeBase.ts # KB operations
├── services/
│   ├── api.ts          # API client
│   ├── streaming.ts    # SSE handling
│   └── storage.ts      # Local storage utils
└── types/              # TypeScript interfaces
```

#### Key Features
- **Streaming Chat**: Real-time token display with source attribution
- **Progressive Workflow**: Guided outline → draft → refinement process
- **Collection Sidebar**: Easy switching between knowledge contexts
- **Export Integration**: In-chat download links and article management

## Risk Assessment & Mitigation

### Technical Risks
1. **Local LLM Performance**: Mitigation via remote provider fallback
2. **Vector Search Quality**: Configurable similarity thresholds and hybrid search
3. **Document Processing Errors**: Robust error handling and user feedback
4. **Memory Usage**: Streaming responses and chunk-based processing

### Implementation Risks
1. **Complexity Scope**: Phased delivery with MVP focus
2. **Integration Challenges**: Early prototype with all components
3. **Performance Bottlenecks**: Monitoring and optimization in each phase

## Success Criteria

### Functional Requirements
- [ ] Upload and process 100+ document collections
- [ ] Generate outlined articles with local knowledge priority
- [ ] Stream draft generation with <5s startup time
- [ ] Export publication-ready markdown with citations
- [ ] Refine articles with targeted section improvements

### Quality Requirements
- [ ] <10s outline generation on local hardware
- [ ] 90%+ uptime for local services
- [ ] Encrypted secret storage
- [ ] Comprehensive error handling and user feedback
- [ ] Clean, intuitive user interface

## Next Steps

1. **Environment Setup**: Initialize development environment with Docker Compose
2. **Backend Foundation**: Implement FastAPI structure and database models
3. **Frontend Scaffold**: Create React application with basic routing
4. **Integration Testing**: Verify component communication early
5. **Iterative Development**: Follow milestone-based delivery approach

---

**Project Timeline**: 4-6 weeks for MVP completion
**Team Requirements**: Full-stack developer with Python/React experience
**Infrastructure**: Local development environment with Docker support