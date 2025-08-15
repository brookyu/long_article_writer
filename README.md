# 📝 Long Article Writer

An AI-powered article generation system that creates comprehensive, well-researched articles using your choice of LLM providers and knowledge base integration.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![React](https://img.shields.io/badge/react-18+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)

## ✨ Features

### 🤖 **AI-Powered Generation**
- **Real LLM Integration**: Uses Ollama for local AI generation (gpt-oss:20b, mixtral, etc.)
- **Configurable Models**: Switch between different LLM providers and models
- **Smart Progress Tracking**: Real-time generation status with model-specific feedback
- **Quality Output**: Structured markdown articles with proper formatting

### 📚 **Knowledge Base Management**
- **Document Collections**: Organize and manage your source documents
- **Vector Search**: Semantic search through your knowledge base
- **Citation Integration**: Articles reference relevant source materials
- **Multiple Formats**: Support for various document types

### ⚙️ **Flexible Configuration**
- **LLM Providers**: Ollama (local), OpenAI, Anthropic support
- **Embedding Models**: nomic-embed-text, OpenAI embeddings
- **Search Providers**: DuckDuckGo, SearXNG, Google, Bing
- **Connection Testing**: Verify all services before use

### 🎨 **Modern Interface**
- **React 18 Frontend**: Modern, responsive TypeScript interface
- **shadcn/ui Components**: Beautiful, accessible UI components
- **Real-time Updates**: Live progress tracking and notifications
- **Mobile-Friendly**: Works great on all device sizes

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- MySQL 8.0+
- Docker & Docker Compose
- [Ollama](https://ollama.ai/) (for local LLM)

### 1. Clone the Repository
```bash
git clone https://github.com/brookyu/long_article_writer.git
cd long_article_writer
```

### 2. Start Dependencies
```bash
# Start MySQL, Milvus, and Ollama
docker-compose up -d mysql milvus-standalone ollama

# Install Ollama models
ollama pull gpt-oss:20b
ollama pull nomic-embed-text
```

### 3. Setup Backend
```bash
cd backend
pip install -r requirements.txt

# Set up database
mysql -u root -p -e "CREATE DATABASE long_article_writer;"
```

### 4. Setup Frontend
```bash
cd frontend
npm install
```

### 5. Start All Servers
```bash
# Use the convenient startup script
./start-servers.sh
```

### 6. Access the Application
- **Frontend**: http://localhost:3005
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🛠️ Development

### Server Management
The project includes professional server management scripts:

```bash
# Start all servers
./start-servers.sh

# Check server status
./status.sh

# Stop all servers
./stop-servers.sh

# View logs
tail -f logs/backend.log
tail -f logs/frontend.log
```

### Project Structure
```
long_article_writer/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── schemas/        # Pydantic schemas
│   └── requirements.txt
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/         # Application pages
│   │   └── types/         # TypeScript types
│   └── package.json
├── database/              # Database initialization
├── docker-compose.yml     # Docker services
└── docs/                 # Documentation
```

## 🔧 Configuration

### Environment Variables
```bash
# Backend (.env)
DATABASE_URL=mysql://user:password@localhost:3306/long_article_writer
OLLAMA_HOST=localhost
OLLAMA_PORT=11434

# Optional
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### LLM Configuration
The application supports multiple LLM providers:

- **Ollama** (recommended for local development)
  - Models: gpt-oss:20b, mixtral:latest, llama2, etc.
  - Fast, private, and free
  
- **OpenAI**
  - Models: gpt-4, gpt-3.5-turbo
  - Requires API key
  
- **Anthropic**
  - Models: claude-3-sonnet, claude-2
  - Requires API key

## 📖 Usage

### 1. Configure Settings
- Navigate to **Settings** in the web interface
- Select your preferred LLM provider and model
- Test connections to ensure everything works
- Save your configuration

### 2. Create Knowledge Collections
- Go to **Collections** 
- Create a new collection for your documents
- Upload relevant documents (PDF, TXT, DOCX)
- Wait for processing and embedding generation

### 3. Generate Articles
- Select a collection
- Click **"Write Article"**
- Specify topic, style, length, and type
- Watch real-time generation progress
- Review and export completed articles

### 4. Manage Articles
- View all generated articles in the **Generated Articles** section
- Read full content with word counts
- Export to various formats
- Track generation history

## 🏗️ Architecture

### Backend (FastAPI)
- **RESTful API**: Clean, documented endpoints
- **Async Operations**: Non-blocking article generation
- **Database Integration**: SQLAlchemy with MySQL
- **Vector Search**: Milvus for semantic search
- **AI Integration**: Ollama, OpenAI, Anthropic support

### Frontend (React)
- **Modern Stack**: React 18 + TypeScript + Vite
- **UI Framework**: shadcn/ui for consistent design
- **State Management**: React hooks and context
- **Real-time Updates**: Server-sent events for progress
- **Responsive Design**: Works on all devices

### AI & Search
- **Local LLMs**: Ollama for privacy and speed
- **Vector Embeddings**: Semantic document search
- **Web Search**: Multiple provider support
- **Citation**: Automatic source referencing

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Servers won't start:**
```bash
# Check ports
lsof -i :8000 :3005

# Clean restart
./stop-servers.sh && ./start-servers.sh
```

**LLM not responding:**
```bash
# Check Ollama
ollama list
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

**Database connection errors:**
```bash
# Check MySQL
docker-compose ps mysql
mysql -u root -p -e "SHOW DATABASES;"
```

### Get Help
- 📖 [Documentation](./docs/)
- 🐛 [Issues](https://github.com/brookyu/long_article_writer/issues)
- 💬 [Discussions](https://github.com/brookyu/long_article_writer/discussions)

## 🚀 What's Next?

- [ ] Advanced citation management
- [ ] Multi-language support
- [ ] Article collaboration features
- [ ] Enhanced export formats
- [ ] Plugin system for custom LLMs
- [ ] Advanced analytics and insights

---

Built with ❤️ using FastAPI, React, and the power of local AI.

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