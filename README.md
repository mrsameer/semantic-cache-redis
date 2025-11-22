# 🧠 Semantic Cache with Redis & Gemini Vertex AI

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Redis](https://img.shields.io/badge/redis-stack-red)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![Vertex AI](https://img.shields.io/badge/Vertex%20AI-Gemini-4285F4)

A production-ready **Semantic Caching** system built with **Redis Stack** (Vector Search) and **Google Gemini Vertex AI**. This project demonstrates how to significantly reduce LLM costs and latency by caching responses based on *semantic meaning* rather than exact text matching.

Includes a premium, dark-themed **Web Interface** to visualize cache hits, misses, and similarity scores in real-time.

---

## ✨ Key Features

- **🚀 Semantic Caching**: Uses vector embeddings to understand the *intent* of a query.
    - *Example*: "Tell me the capital of France" matches "What is the capital of France?"
- **🕒 Time-Aware Caching (TASC)**: Resolves relative time expressions to absolute dates.
    - *Example*: "Weather today" (Nov 22) and "Weather yesterday" (Nov 21) are distinct cache entries.
    - Uses `dateparser` to normalize queries like "today", "yesterday", "last Friday" to ISO dates.
    - Supports composite queries: "Rainfall today and yesterday".
- **🔍 Metadata Filtering**: Strict date filtering prevents false positives.
    - *Example*: "Weather today" won't hit "Weather yesterday" even if semantically similar.
    - Uses Redis TagField for exact date matching.
- **🎯 Hybrid Search (BM25 + Vector)**: Combines lexical and semantic search for precision.
    - *Example*: "Rainfall of Hyderabad" won't match "Rainfall of Andhra" despite high semantic similarity.
    - Configurable balance via `HYBRID_ALPHA` (default: 0.7 = 70% vector, 30% BM25).
- **⚡ High Performance**:
    - **Cache Hit**: ~0.2s (Redis Vector Search)
    - **Cache Miss**: ~1.5s+ (LLM Generation)
- **🧠 Advanced AI Models**:
    - **Embeddings**: `text-embedding-004` (768 dimensions) for semantic understanding.
    - **Generation**: `gemini-1.5-flash-001` for fast, accurate responses.
- **🎨 Premium Web UI**:
    - Real-time latency visualization.
    - Visual indicators for Cache Hits (Green) vs Misses (Blue).
    - Dashboard to inspect and manage cached entries.
- **🛠️ Production Ready**:
    - Dockerized Redis Stack.
    - Environment-based configuration (`.env`).
    - FastAPI backend with REST endpoints.


---

## 🏗️ Architecture

```mermaid
graph TD
    User["User / Web UI"] -->|Query| API["FastAPI Backend"]
    API -->|"1. Check Cache"| Cache["Semantic Cache (Redis)"]
    Cache -->|"Vector Search"| Redis[("Redis Stack")]
    
    Redis -- "Hit (Similarity > 0.9)" --> API
    Redis -- Miss --> LLM["Gemini Vertex AI"]
    
    LLM -->|"Generate Response"| API
    API -->|"Store Result"| Redis
    API -->|Response| User
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+**
- **Docker** (for Redis Stack)
- **Google Cloud Project** with Vertex AI API enabled.
- **Service Account Key** (`gemini-api-key.json`) with Vertex AI User permissions.

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/semantic-cache-redis.git
cd semantic-cache-redis
```

### 2. Start Redis Stack

Run Redis with RediSearch and RedisJSON modules using Docker:

```bash
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

### 3. Environment Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configuration

Create a `.env` file in the root directory:

```ini
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=gemini-api-key.json
PROJECT_ID=your-project-id
LOCATION=us-central1

# Models
EMBEDDING_MODEL_ID=text-embedding-004
GENERATION_MODEL_ID=gemini-1.5-flash-001

# Cache Settings
SIMILARITY_THRESHOLD=0.9
CACHE_TTL_SECONDS=3600
VECTOR_DIMENSION=768
INDEX_NAME=semantic_cache_idx

# Hybrid Search (BM25 + Vector)
HYBRID_ENABLED=true
HYBRID_ALPHA=0.7  # 0.7 = 70% vector, 30% BM25
```

> **Note**: Ensure `VECTOR_DIMENSION` matches your embedding model (768 for `text-embedding-004`).

---

## 📚 Advanced Features

### Time-Aware Caching

The system automatically normalizes temporal expressions in queries:

```python
# Example queries that get normalized:
"Weather today"           -> "Weather 2025-11-22"
"Rainfall yesterday"      -> "Rainfall 2025-11-21"
"Temperature last Friday" -> "Temperature 2025-11-15"
"Weather today and yesterday" -> Stored with tags: 2025-11-22, 2025-11-21
```

### Hybrid Search

Hybrid search combines BM25 (keyword matching) with vector similarity to reduce false positives:

- **Pure Vector**: "Rainfall of Hyderabad" matches "Rainfall of Andhra" (0.95 similarity)
- **Hybrid**: Same query results in **MISS** (BM25 detects different keywords)

Tune the balance with `HYBRID_ALPHA`:
- `1.0` = Pure vector (semantic only)
- `0.7` = Default (70% semantic, 30% keyword)
- `0.5` = Balanced
- `0.0` = Pure BM25 (keyword only)

---

## 🖥️ Usage

### Running the Web Interface

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Open your browser and navigate to:
👉 **http://localhost:8000/static/index.html**

### Using the UI

1.  **Ask a Question**: Type a query like "What is the capital of France?".
    - *Result*: **Cache MISS** (Blue badge). The system calls Gemini.
2.  **Ask Again**: Type the same question or a variation like "Tell me the capital city of France".
    - *Result*: **Cache HIT** (Green badge). The system finds the semantic match in Redis.
3.  **Check Dashboard**: Scroll down to see stored cache entries.

### API Endpoints

- `POST /ask`: Submit a query.
- `POST /agent/ask`: Ask the LangGraph agent (with Google Search).
- `GET /cache`: Retrieve all cached entries.
- `DELETE /cache`: Clear the cache.

---

## 🧪 Verification Script

You can also run the CLI demonstration script:

```bash
python main.py
```

This script runs a sequence of test queries to demonstrate exact matches, semantic matches, and cache misses, printing the latency for each.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
