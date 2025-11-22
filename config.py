import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# Google Cloud / Vertex AI Configuration
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "gemini-api-key.json")
PROJECT_ID = os.getenv("PROJECT_ID", "you project id")
LOCATION = os.getenv("LOCATION", "us-central1")

# Model Configuration
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "text-embedding-004")
GENERATION_MODEL_ID = os.getenv("GENERATION_MODEL_ID", "gemini-1.5-flash-001")

# Cache Configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.9))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 3600))
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 768))
INDEX_NAME = os.getenv("INDEX_NAME", "semantic_cache_idx")
