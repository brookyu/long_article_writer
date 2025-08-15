# Long Article Writer

AI-powered long-form article generation with knowledge base integration.

## Features

- 📚 **Knowledge-First Research**: Prioritize local knowledge bases over web search
- ✍️ **Structured Writing Workflow**: Research → Outline → Draft → Refine → Export
- 🔄 **Streaming Interface**: Real-time article generation with transparent process
- 🏠 **Local-First Privacy**: Keep documents and processing local with optional remote providers
- 📄 **Citation System**: Automatic source attribution and reference tracking

## Architecture

- **Frontend**: React 18 + TypeScript + shadcn/ui + Tailwind CSS
- **Backend**: Python FastAPI + SQLAlchemy + Uvicorn
- **Database**: MySQL 8.0 (metadata) + Milvus (vector storage)
- **LLM**: Ollama (local models) with remote provider fallback
- **Deployment**: Docker Compose for local development

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 8GB+ RAM (for local LLMs)
- 10GB+ disk space

### 1. Clone and Setup

```bash
git clone <your-repo>
cd long_article_writer

# Copy environment configuration
cp env.example .env

# Edit .env file with your preferences (optional)
nano .env
```

### 2. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### 3. Initialize Ollama Models

```bash
# Pull required models (this may take 10-15 minutes)
docker exec law_ollama ollama pull llama3.1:8b
docker exec law_ollama ollama pull nomic-embed-text

# Verify models are available
docker exec law_ollama ollama list
```

### 4. Access Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run locally (with Docker services running)
export DATABASE_URL="mysql://law_user:law_password@localhost:3306/long_article_writer"
export MILVUS_HOST="localhost"
export OLLAMA_HOST="localhost"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage

### 1. Settings Configuration

Configure your LLM providers, embedding models, and web search APIs in the Settings page.

### 2. Knowledge Base Management

1. Create a new collection
2. Upload documents (PDF, Markdown, Text)
3. Wait for ingestion to complete

### 3. Article Generation

1. Select a knowledge base collection
2. Enter your article topic
3. Generate outline → Review → Generate draft
4. Refine sections as needed
5. Export final markdown

## Services

### Core Infrastructure

- **MySQL** (port 3306): Application data and metadata
- **Milvus** (port 19530): Vector embeddings and similarity search
- **Ollama** (port 11434): Local LLM serving
- **Backend** (port 8000): FastAPI application
- **Frontend** (port 3000): React application

### Optional Services

- **Minio** (port 9000): Milvus object storage
- **etcd** (port 2379): Milvus coordination

## API Endpoints

### Health & Settings
- `GET /health` - Basic health check
- `GET /api/health/detailed` - Detailed health with dependencies
- `GET /api/settings` - List provider configurations
- `POST /api/settings` - Create/update provider settings

### Knowledge Base (Coming Soon)
- `POST /api/kb/collections` - Create collection
- `GET /api/kb/collections` - List collections
- `POST /api/kb/{collection_id}/upload` - Upload documents
- `GET /api/kb/{collection_id}/documents` - List documents

### Article Generation (Coming Soon)
- `POST /api/write/outline` - Generate outline
- `POST /api/write/draft` - Generate draft
- `POST /api/write/refine` - Refine sections
- `POST /api/write/export` - Export markdown

## Troubleshooting

### Common Issues

**Ollama Models Not Loading**
```bash
# Check Ollama status
docker logs law_ollama

# Manually pull models
docker exec -it law_ollama ollama pull llama3.1:8b
```

**Database Connection Issues**
```bash
# Check MySQL status
docker logs law_mysql

# Verify database exists
docker exec -it law_mysql mysql -u law_user -p long_article_writer
```

**Milvus Connection Issues**
```bash
# Check all Milvus services
docker logs milvus-standalone
docker logs milvus-etcd
docker logs milvus-minio
```

### Performance Tuning

**For Better LLM Performance:**
- Increase Docker memory allocation to 12GB+
- Use smaller models (llama3.1:8b → phi3:mini)
- Enable GPU acceleration if available

**For Large Document Collections:**
- Increase MySQL connection pool size
- Adjust Milvus memory settings
- Use SSD storage for better I/O

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [ ] ✅ **M0**: Infrastructure setup
- [ ] **M1**: Knowledge base management
- [ ] **M2**: Writing workspace with streaming
- [ ] **M3**: Article generation and refinement
- [ ] **M4**: Settings and configuration
- [ ] **M5**: Export and finalization