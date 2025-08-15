## Product Requirements Document (PRD)

### Product: Long Article Writer
### Version: 0.1 (Initial)
### Owner: TBD
### Last Updated: TBD

## 1. Overview
The Long Article Writer is a web application that generates in‑depth articles on a given topic. It prioritizes research from a local knowledge base and falls back to web research if needed. It guides users through outline creation, drafting, and iterative refinement, producing a final markdown article.

## 2. Goals and Non‑Goals
### Goals
- Produce high‑quality, well‑researched long‑form articles with minimal manual effort.
- Prefer local knowledge base content; only use web research when the topic is not sufficiently covered locally.
- Provide a structured workflow: research → outline → draft → refine → export.
- Offer a chat‑like, streaming UX for transparency and control.

### Non‑Goals (v0.1)
- Multi‑tenant SaaS, billing, and role‑based access control.
- Real‑time multi‑user collaboration.
- Complex editorial workflows (review/approve chains).
- Advanced CMS features beyond markdown export.

## 3. Target Users and Personas
### Personas
- Content Strategist: Needs fast, research‑grounded drafts to scale content production.
- Technical Writer: Needs accurate sourcing and the ability to control knowledge collections.
- Solo Creator: Wants a simple tool to generate and refine long‑form posts.

## 4. User Stories (MVP)
- As a user, I can configure LLM and embedding providers so that generation and retrieval work reliably.
- As a user, I can create and manage knowledge base collections and upload documents to them.
- As a user, I can select a collection and input a topic to receive an outline based on local sources.
- As a user, I can get a draft article with inline citations where possible and see it stream into the UI.
- As a user, I can refine the draft via follow‑up prompts and regenerate sections.
- As a user, I can export the final article as markdown and access it via a link in the UI.

## 5. Scope (MVP)
### In Scope
- Settings for LLM providers, embedding models, and web search providers.
- Knowledge base management: collections, file upload, ingestion, chunking, embedding to Milvus.
- Chat‑based writing workspace with streaming responses, sidebar for collection selection, topic input, and action buttons.
- Outline generation, draft generation, and refinement cycles.
- Markdown export of final article and accessible link in the UI.

### Out of Scope (MVP)
- Authentication (assume single local user) unless explicitly added later.
- WYSIWYG rich‑text editing; focus on markdown.
- Advanced plagiarism detection or SEO scoring (basic compliance only).

## 6. Functional Requirements
### 6.1 Settings Page
- Configure LLM providers (local Ollama, optional remote) and model names.
- Configure embedding model used for Milvus ingestion.
- Configure web search providers and keys.
- Persist settings in MySQL; mask and encrypt secrets at rest.

### 6.2 Knowledge Base Management
- Create/delete collections.
- Upload documents (PDF, Markdown, Text; others optional) into a selected collection.
- Ingestion pipeline: file parsing → chunking → embedding → upsert to Milvus with metadata (collection, source, hash, timestamp).
- View documents per collection; re‑ingest updated files.

### 6.3 Writing Workspace (Chat)
- Sidebar to select active knowledge base collection.
- Topic input and “Generate Outline” action.
- Streaming chat messages (SSE or websockets) while the model reasons/generates.
- Buttons: Generate Outline, Generate Draft, Refine Draft, Export.
- Display sources/citations when content comes from knowledge base or web research.
- Final output saved as markdown; provide a link to view/download.

### 6.4 Research Policy
- Attempt retrieval from local knowledge base first (configurable top‑k and score threshold).
- If retrieval confidence below threshold, perform web search and fetch relevant pages.
- Maintain provenance: tag which sections were informed by local vs web sources.

## 7. Non‑Functional Requirements
- Latency: Initial outline within 10s on a modern laptop with local LLM; draft streaming start < 5s.
- Reliability: Failed web calls or embeddings should surface actionable errors with retry.
- Privacy: All uploaded documents stay local unless the user opts into remote models/search.
- Security: Secrets encrypted at rest; never log API keys; CORS locked to app origin.
- Observability: Sentry for errors and performance spans; structured logs.
- Export: Deterministic markdown with front‑matter (title, date, sources).

## 8. System Architecture (High Level)
- Frontend: React + shadcn/ui components; streaming chat UI.
- Backend: Python FastAPI on Uvicorn; orchestrates agentic workflow using OpenAI’s agentic framework (per context7 MCP server guidance).
- Database: MySQL (local Docker instance) for settings, document metadata, job tracking, and article records.
- Vector Store: Milvus for embeddings and retrieval.
- LLMs: Local models via Ollama (primary). Optional remote provider via settings.
- Web Search: Pluggable providers configured in settings.
- Deployment: Docker for local dev and packaging.
- Monitoring: Sentry SDK integrated in frontend and backend.

## 9. Data Model (Initial)
- users (optional for single‑user; keep table for future multi‑user)
- settings (provider, key alias, encrypted secret, model name, created_at, updated_at)
- kb_collections (id, name, description, created_at)
- kb_documents (id, collection_id, filename, mime_type, size_bytes, sha256, status, created_at)
- kb_chunks (id, document_id, chunk_index, text, created_at)
- articles (id, title, topic, collection_id, markdown_path, status, created_at, updated_at)
- jobs (id, type, status, payload_json, result_json, created_at, updated_at)
Note: Embeddings are stored in Milvus with references back to kb_chunks.id and collection ids.

## 10. Key API Endpoints (MVP)
- POST /api/settings: upsert settings; GET /api/settings
- POST /api/kb/collections: create; GET /api/kb/collections; DELETE /api/kb/collections/{id}
- POST /api/kb/{collectionId}/upload: multipart upload; triggers ingestion job
- GET /api/kb/{collectionId}/documents: list
- POST /api/write/outline: { topic, collectionId } → streaming outline
- POST /api/write/draft: { outlineId or outline text, collectionId } → streaming draft
- POST /api/write/refine: { articleId, instructions } → streaming updates
- POST /api/write/export: { articleId } → returns markdown file path/link

## 11. Core Workflows
### 11.1 Ingestion
1) User uploads files to a collection.
2) Backend parses, chunks, embeds, and writes vectors to Milvus with metadata.
3) Status updates visible in UI; errors logged to Sentry.

### 11.2 Article Creation
1) User selects collection, enters a topic, clicks Generate Outline.
2) Backend: retrieve from Milvus → if weak, web search → synthesize outline with citations.
3) User approves outline; clicks Generate Draft.
4) Backend drafts sections sequentially, streaming tokens.
5) User refines via chat prompts; model edits specific sections.
6) User exports; backend writes markdown to disk and records path in MySQL.

## 12. Acceptance Criteria
- Settings persisted and reloaded across sessions; secrets masked in UI.
- Users can create/delete collections and upload at least 100MB across files without crashes.
- Ingestion shows progress and completes with vectors visible via simple recall test.
- Outline generation works with local KB only; falls back to web search when KB is insufficient.
- Draft generation streams to UI with visible tokens and shows source attributions.
- Refinement updates only targeted sections while preserving citations where valid.
- Export produces a downloadable markdown with front‑matter and a link in the chat.

## 13. Risks and Mitigations
- Local LLM quality may be insufficient: allow switching to remote providers.
- Embedding mismatch across models: pin default embedding model and store its name in metadata.
- Web search variability: support multiple providers and cache fetched pages.
- Large files and parsing errors: limit per‑file size, offer clear error messages, and support retry.

## 14. Milestones (Suggested)
- M0: Scaffolding (Dockerized FastAPI + React; Sentry wired; MySQL/Milvus/Ollama compose).
- M1: Knowledge Base (collections, upload, ingestion pipeline to Milvus).
- M2: Writing Workspace (chat UI, streaming, select collection, outline gen).
- M3: Draft + Refinement (draft generation, targeted refine flows, citations).
- M4: Settings (LLM, embeddings, web search; encrypted secrets).
- M5: Export (markdown file generation and link display).

## 15. Open Questions
- Which web search provider(s) will we support first (SerpAPI, Bing, Tavily, custom)?
- Minimum local LLM(s) via Ollama to target for quality vs performance?
- Document types to prioritize beyond PDF/MD/TXT?
- Do we need authentication for v0.1 or is single‑user sufficient?
- Where to store uploaded files and generated markdown (local disk path convention)?
- Threshold and top‑k defaults for retrieval and fallback policy?

## 16. Definitions
- Collection: Logical grouping of documents used for retrieval.
- Ingestion: Parse, chunk, embed, and index documents into Milvus.
- Streaming: Token‑by‑token or chunked partial responses rendered live in the UI.