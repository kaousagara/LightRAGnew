# LightRAG on Replit

## Overview
LightRAG is a Simple and Fast Retrieval-Augmented Generation (RAG) system utilizing graph-based knowledge representation. It's a full-stack application designed for efficient document indexing, knowledge graph exploration, and advanced querying. The project aims to provide a robust solution for managing and querying complex information, with capabilities for multimodal document processing, secure access control, and dynamic relationship typing in its knowledge graph.

## User Preferences
The agent should prioritize iterative development and clear communication. Before making major architectural changes or introducing new external dependencies, the agent must ask for explicit approval. When implementing new features or making significant modifications, the agent should provide detailed explanations of the changes, their impact, and any configuration required. The agent should always ensure that the frontend build process is followed, placing outputs in `lightrag/api/webui/`. Destructive operations like merging or deleting entities in the graph should only be performed after explicit confirmation and with a clear understanding of the impact on data integrity.

## System Architecture

### UI/UX Decisions
The frontend is a React 19 application with TypeScript, built using Vite and Bun, and styled with Tailwind CSS. Graph visualization is handled by Sigma.js, offering multi-selection, temporary hiding, and admin-only node merging/deletion features. The UI supports multi-language display (English, Chinese, French, Arabic) and incorporates visual indicators for document sensitivity. Data fetching and caching are managed with TanStack React Query, and state management uses Zustand.

### Technical Implementations
- **Backend**: Python FastAPI server running on port 5000, integrating the LightRAG core for RAG operations. It provides endpoints for document indexing, graph exploration, and querying, including Ollama-compatible API endpoints.
- **Frontend**: Serves a dynamic web interface with components for graph visualization and document management. It includes custom RAG hooks (`useRAGStream`, `useCoTParser`, `useLaTeXValidator`) for enhanced functionality.
- **Knowledge Graph**: Uses dynamic relationship types in Neo4j (configurable) based on keyword priority and entity types, with synonym normalization. The default is JSON-based storage.
- **Multimodal Document Processing**: Automatically analyzes tables, equations, and images within documents using AI, enriching the knowledge graph with insights from these elements.
- **Security**: Implements Accreditation-Level Access Control, where documents and data are filtered based on user clearance levels and departmental tags. Role-Based Access Control is supported for graph modifications, requiring admin privileges for destructive operations.
- **Entity Merge Verification**: Prevents incorrect merging of same-named entities by assessing semantic and contextual similarity before combining them, ensuring data integrity.

### Feature Specifications
- Document upload and indexing.
- Knowledge graph exploration and RAG querying (local, global, hybrid, naive modes).
- Graph visualization with advanced interaction features.
- Multimodal document processing for tables, equations, and images.
- Ollama-compatible API.
- Accreditation-Level Access Control for secure data access.
- Role-Based Access Control for graph modifications.
- Entity Merge Verification for accurate knowledge graph management.

### System Design Choices
- **Full-stack architecture** with a Python backend and React frontend.
- **Microservice-oriented approach** with the LightRAG core integrated into FastAPI.
- **Production Storage Architecture** (configured by default):
  - **Neo4j** for knowledge graph storage with dynamic relationship types
  - **Milvus** for high-performance vector storage and similarity search
  - **Elasticsearch** for text chunk storage and hybrid search (BM25 + vector)
  - Alternative option: PostgreSQL all-in-one (for simplified deployments)
- **Environment variables** for flexible configuration of API keys, LLM/embedding providers, and security settings.
- **Optimized frontend performance** through asynchronous layout calculations, debounced inputs, and memoized components.
- **Deployment model** configured for VM environments to maintain state across sessions.

## Production Storage Configuration

The system is configured with a production-grade storage architecture using specialized services:

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                      LightRAG System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Elasticsearch│  │    Milvus    │  │    Neo4j     │      │
│  │              │  │              │  │              │      │
│  │ KV Storage   │  │   Vectors    │  │    Graph     │      │
│  │ Doc Status   │  │  Embeddings  │  │ Entities &   │      │
│  │ Text Chunks  │  │              │  │ Relations    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Storage Backends

**Elasticsearch** (`ElasticsearchKVStorage`, `ElasticsearchDocStatusStorage`)
- Stores document text chunks and metadata
- Enables hybrid search (BM25 + vector + RRF)
- Handles document status tracking
- Full-text search capabilities with powerful analyzers

**Milvus** (`MilvusVectorDBStorage`)
- Optimized for billion-scale vector search
- HNSW/IVF indexing for fast similarity search
- GPU acceleration support
- Horizontal scalability

**Neo4j** (`Neo4JStorage`)
- Native graph database for knowledge graph
- Dynamic relationship types based on entity semantics
- Cypher query language for complex traversals
- Optimized for relationship-heavy queries

### Required Secrets

Configure these in **Replit Secrets** (🔒):

**Elasticsearch:**
- `ELASTICSEARCH_CLOUD_ID` (ou `ELASTICSEARCH_URL`)
- `ELASTICSEARCH_API_KEY` (ou `ELASTICSEARCH_USERNAME` + `ELASTICSEARCH_PASSWORD`)

**Milvus:**
- `MILVUS_URI` (e.g., `https://xxx.zillizcloud.com:443`)
- `MILVUS_TOKEN` (pour Zilliz Cloud)
- `MILVUS_DB_NAME` (e.g., `lightrag`)

**Neo4j:**
- `NEO4J_URI` (e.g., `neo4j+s://xxx.databases.neo4j.io`)
- `NEO4J_USERNAME` (typically `neo4j`)
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE` (e.g., `neo4j`)

**Storage Backend Selection (already configured in env.example):**
- `LIGHTRAG_KV_STORAGE=ElasticsearchKVStorage`
- `LIGHTRAG_DOC_STATUS_STORAGE=ElasticsearchDocStatusStorage`
- `LIGHTRAG_GRAPH_STORAGE=Neo4JStorage`
- `LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage`

### Cloud Service Recommendations

For production deployment, use managed services:

1. **Elastic Cloud** (https://cloud.elastic.co/)
   - 14-day free trial
   - Managed Elasticsearch clusters
   - Built-in security and monitoring

2. **Neo4j Aura** (https://neo4j.com/cloud/aura/)
   - Free tier available
   - Fully managed Neo4j instances
   - Automatic backups and scaling

3. **Zilliz Cloud** (https://zilliz.com/)
   - Managed Milvus service
   - Free tier available
   - Enterprise-grade performance

### Performance Characteristics

- **Documents**: Billions of documents
- **Vectors**: Billions of vectors with optimized indexing
- **Graph**: Millions of entities and relations
- **Queries**: Ultra-fast similarity search and graph traversals

### Alternative: PostgreSQL (Simplified Deployment)

For smaller deployments or when external services are not desired:

**PostgreSQL All-in-One:**
- `LIGHTRAG_KV_STORAGE=PGKVStorage`
- `LIGHTRAG_GRAPH_STORAGE=PGGraphStorage`
- `LIGHTRAG_VECTOR_STORAGE=PGVectorStorage`
- Available natively in Replit
- Good for up to 100k documents

See `STORAGE_SETUP.md` for PostgreSQL configuration.

### Setup Guide

See `STORAGE_SETUP.md` for detailed instructions including:
- Cloud service setup and provisioning
- Environment variable configuration
- Docker Compose for self-hosted deployment
- Migration from JSON/PostgreSQL storage
- Troubleshooting common issues

## External Dependencies
- **OpenAI**: Used for LLM operations (gpt-4o-mini) and embeddings (text-embedding-3-small). Requires `OPENAI_API_KEY` or `LLM_BINDING_API_KEY` and `EMBEDDING_BINDING_API_KEY`.
- **Ollama**: Provides compatibility for chat applications.
- **Neo4j**: Optional graph database for advanced knowledge graph storage with dynamic relationship types.
- **PostgreSQL**: Optional relational database for vector/graph/KV storage.
- **Redis**: Optional for caching.
- **Milvus/Qdrant**: Optional vector databases for vector storage.
- **Sigma.js**: JavaScript library for graph visualization in the frontend.
- **TanStack React Query**: Frontend library for data fetching, caching, and synchronization.
- **Zustand**: Frontend library for state management.