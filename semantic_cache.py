import json
import time
import os
import numpy as np
import redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from google import genai
from google.genai import types
import config

class SemanticCache:
    def __init__(self):
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(config.GOOGLE_APPLICATION_CREDENTIALS)
        
        # Initialize Google GenAI Client
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LOCATION
        )
        
        # Initialize Redis
        self.redis_client = redis.Redis.from_url(config.REDIS_URL)
        self._create_index()

    def _create_index(self):
        """Creates the Redis search index if it doesn't exist."""
        try:
            self.redis_client.ft(config.INDEX_NAME).info()
            print(f"Index '{config.INDEX_NAME}' already exists.")
        except redis.exceptions.ResponseError:
            print(f"Creating index '{config.INDEX_NAME}'...")
            schema = (
                TextField("query"),
                TextField("response"),
                VectorField(
                    "embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": config.VECTOR_DIMENSION,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            definition = IndexDefinition(prefix=["cache:"], index_type=IndexType.HASH)
            self.redis_client.ft(config.INDEX_NAME).create_index(schema, definition=definition)

    def get_embedding(self, text: str) -> list[float]:
        """Generates embedding for the given text using Google GenAI SDK."""
        
        # Configure embedding request
        # Use SEMANTIC_SIMILARITY task type as recommended for retrieval/similarity
        embed_config = types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY"
        )
        
        response = self.client.models.embed_content(
            model=config.EMBEDDING_MODEL_ID,
            contents=text,
            config=embed_config
        )
        
        # Extract embedding values
        embedding_values = response.embeddings[0].values
        embedding_vector = np.array(embedding_values, dtype=np.float32)
        
        # Explicitly normalize the embedding (L2 norm)
        norm = np.linalg.norm(embedding_vector)
        if norm > 0:
            embedding_vector = embedding_vector / norm
            
        return embedding_vector.tolist()

    def search(self, query_text: str, threshold: float = config.SIMILARITY_THRESHOLD):
        """Searches for a semantically similar query in the cache."""
        query_embedding = self.get_embedding(query_text)
        
        # Prepare the query
        # KNNSearch: Return top 1 result
        # We use standard RediSearch query syntax for vector search
        # The query is: "*=>[KNN 1 @embedding $vec_param AS score]"
        base_query = f"*=>[KNN 1 @embedding $vec_param AS score]"
        query = (
            Query(base_query)
            .return_fields("response", "score", "query")
            .sort_by("score")
            .dialect(2)
        )
        
        params = {"vec_param": np.array(query_embedding, dtype=np.float32).tobytes()}
        
        results = self.redis_client.ft(config.INDEX_NAME).search(query, query_params=params)
        
        if results.docs:
            doc = results.docs[0]
            # Redis returns distance (1 - cosine_similarity) for COSINE metric? 
            # Wait, RediSearch COSINE distance is 1 - cosine_similarity.
            # So if distance is small, similarity is high.
            # Similarity = 1 - distance.
            # We want Similarity >= Threshold.
            # So (1 - distance) >= Threshold  =>  distance <= 1 - Threshold.
            
            distance = float(doc.score)
            similarity = 1 - distance
            
            print(f"Found cache candidate. Distance: {distance}, Similarity: {similarity}")
            
            if similarity >= threshold:
                return doc.response
        
        return None

    def store(self, query_text: str, response_text: str):
        """Stores the query and response in the cache with embedding."""
        embedding = self.get_embedding(query_text)
        key = f"cache:{int(time.time())}"
        
        mapping = {
            "query": query_text,
            "response": response_text,
            "embedding": np.array(embedding, dtype=np.float32).tobytes(),
        }
        
        # Use pipeline to set hash and expire
        pipe = self.redis_client.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, config.CACHE_TTL_SECONDS)
        pipe.execute()
        print(f"Stored in cache: {query_text}")

    def check(self, query_text: str):
        """High-level method to check cache."""
        return self.search(query_text)

    def get_all_entries(self):
        """Retrieves all cached entries for the dashboard."""
        keys = self.redis_client.keys("cache:*")
        entries = []
        for key in keys:
            data = self.redis_client.hgetall(key)
            if data:
                # Decode bytes to strings
                entry = {
                    "key": key.decode("utf-8"),
                    "query": data.get(b"query", b"").decode("utf-8"),
                    "response": data.get(b"response", b"").decode("utf-8"),
                    # We don't need the embedding for display
                }
                entries.append(entry)
        return entries

    def clear_cache(self):
        """Clears all cached entries."""
        keys = self.redis_client.keys("cache:*")
        if keys:
            self.redis_client.delete(*keys)
            print(f"Cleared {len(keys)} cache entries.")
