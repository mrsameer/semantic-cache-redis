import json
import time
import os
import numpy as np
import redis
from redis.commands.search.field import VectorField, TextField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from google import genai
from google.genai import types
import config
from temporal_utils import normalize_query_dates, extract_date_from_query

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
            # For development: Check if 'date' field exists in info, if not, drop and recreate
            # This is a simple heuristic for this task.
            info = self.redis_client.ft(config.INDEX_NAME).info()
            # attributes is a list of lists in some versions, or list of dicts. 
            # Let's just force drop for this task to ensure schema update.
            # In production, use a migration strategy.
            print("Dropping index to ensure schema update...")
            try:
                self.redis_client.ft(config.INDEX_NAME).dropindex()
            except Exception as e:
                print(f"Error dropping index: {e}")
                
        except redis.exceptions.ResponseError:
            pass
            
        print(f"Creating index '{config.INDEX_NAME}'...")
        schema = (
            TextField("query"),
            TextField("response"),
            TagField("date"), # Metadata for filtering
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

    def search(self, query_text: str):
        """Searches for a semantically similar query in the cache using hybrid search."""
        # Normalize the query to handle relative time (e.g., "today" -> "2023-10-27")
        normalized_query = normalize_query_dates(query_text)
        query_dates = extract_date_from_query(query_text)
        
        print(f"Original Query: '{query_text}' -> Normalized Query: '{normalized_query}'")
        if query_dates:
            print(f"Extracted Dates for Filtering: {query_dates}")
        
        # Generate embedding for vector search
        query_embedding = self.get_embedding(normalized_query)
        
        # Prepare date filter if dates exist
        date_filter = None
        if query_dates:
            date_filters = []
            for date_str in query_dates:
                escaped_date = date_str.replace("-", "\\-")
                date_filters.append(f"(@date:{{{escaped_date}}})")
            date_filter = " ".join(date_filters)
        
        if config.HYBRID_ENABLED:
            # Perform Hybrid Search (BM25 + Vector)
            return self._hybrid_search(query_text, normalized_query, query_embedding, date_filter)
        else:
            # Fallback to pure vector search
            return self._vector_search(query_embedding, date_filter)
    
    def _vector_search(self, query_embedding, date_filter=None):
        """Performs pure vector similarity search."""
        if date_filter:
            base_query = f"({date_filter})=>[KNN 5 @embedding $vec_param AS score]"
        else:
            base_query = f"*=>[KNN 5 @embedding $vec_param AS score]"
            
        query = (
            Query(base_query)
            .return_fields("response", "score", "query", "date")
            .sort_by("score")
            .dialect(2)
        )
        
        params = {"vec_param": np.array(query_embedding, dtype=np.float32).tobytes()}
        results = self.redis_client.ft(config.INDEX_NAME).search(query, query_params=params)
        
        if results.total > 0:
            best_result = results.docs[0]
            distance = float(best_result.score)
            similarity = 1 - distance
            
            if similarity >= config.SIMILARITY_THRESHOLD:
                print(f"Found cache candidate. Distance: {distance}, Similarity: {similarity}")
                return best_result.response
        
        return None
    
    def _hybrid_search(self, query_text, normalized_query, query_embedding, date_filter=None):
        """Performs hybrid search combining BM25 and vector similarity."""
        # 1. Perform BM25 text search using ORIGINAL query (not normalized)
        # This allows "today" to match "today" in stored queries
        bm25_results = self._bm25_search(query_text, date_filter)
        
        # 2. Perform Vector search
        vector_results = self._vector_search_raw(query_embedding, date_filter)
        
        # 3. Combine results with score fusion
        combined_scores = {}
        
        # Normalize and add BM25 scores
        if bm25_results:
            max_bm25_score = max(r['score'] for r in bm25_results) if bm25_results else 1.0
            for result in bm25_results:
                doc_id = result['doc_id']
                normalized_score = result['score'] / max_bm25_score if max_bm25_score > 0 else 0
                combined_scores[doc_id] = {
                    'bm25_score': normalized_score,
                    'vector_score': 0,
                    'response': result['response'],
                    'query': result['query']
                }
        
        # Add vector scores (already normalized as 1 - distance)
        if vector_results:
            for result in vector_results:
                doc_id = result['doc_id']
                if doc_id not in combined_scores:
                    combined_scores[doc_id] = {
                        'bm25_score': 0,
                        'vector_score': result['score'],
                        'response': result['response'],
                        'query': result['query']
                    }
                else:
                    combined_scores[doc_id]['vector_score'] = result['score']
        
        # 4. Calculate hybrid scores
        alpha = config.HYBRID_ALPHA
        for doc_id in combined_scores:
            scores = combined_scores[doc_id]
            hybrid_score = alpha * scores['vector_score'] + (1 - alpha) * scores['bm25_score']
            scores['hybrid_score'] = hybrid_score
        
        # 5. Get best result
        if combined_scores:
            best_doc_id = max(combined_scores, key=lambda x: combined_scores[x]['hybrid_score'])
            best_result = combined_scores[best_doc_id]
            
            print(f"Hybrid Search - BM25: {best_result['bm25_score']:.4f}, "
                  f"Vector: {best_result['vector_score']:.4f}, "
                  f"Hybrid: {best_result['hybrid_score']:.4f}")
            
            if best_result['hybrid_score'] >= config.SIMILARITY_THRESHOLD:
                return best_result['response']
        
        return None
    
    def _bm25_search(self, query_text, date_filter=None, top_k=5):
        """Performs BM25 text search on the query field."""
        # Escape special characters for Redis query
        escaped_query = query_text.replace("-", "\\-").replace(":", "\\:")
        
        if date_filter:
            base_query = f"({date_filter}) (@query:{escaped_query})"
        else:
            base_query = f"@query:{escaped_query}"
        
        try:
            query = (
                Query(base_query)
                .with_scores()  # Retrieve BM25 scores for hybrid weighting
                .return_fields("query", "response", "date")
                .scorer("BM25")
                .paging(0, top_k)
                .dialect(2)
            )
            
            results = self.redis_client.ft(config.INDEX_NAME).search(query)
            
            parsed_results = []
            for doc in results.docs:
                parsed_results.append({
                    'doc_id': doc.id,
                    'query': doc.query,
                    'response': doc.response,
                    'score': float(doc.score) if hasattr(doc, 'score') else 0.0
                })
            
            return parsed_results
        except Exception as e:
            print(f"BM25 search error: {e}")
            return []
    
    def _vector_search_raw(self, query_embedding, date_filter=None, top_k=5):
        """Performs vector search and returns raw results with scores."""
        if date_filter:
            base_query = f"({date_filter})=>[KNN {top_k} @embedding $vec_param AS score]"
        else:
            base_query = f"*=>[KNN {top_k} @embedding $vec_param AS score]"
            
        query = (
            Query(base_query)
            .return_fields("response", "score", "query", "date")
            .sort_by("score")
            .dialect(2)
        )
        
        params = {"vec_param": np.array(query_embedding, dtype=np.float32).tobytes()}
        
        try:
            results = self.redis_client.ft(config.INDEX_NAME).search(query, query_params=params)
            
            parsed_results = []
            for doc in results.docs:
                distance = float(doc.score)
                similarity = 1 - distance
                parsed_results.append({
                    'doc_id': doc.id,
                    'query': doc.query,
                    'response': doc.response,
                    'score': similarity
                })
            
            return parsed_results
        except Exception as e:
            print(f"Vector search error: {e}")
            return []



    def store(self, query_text: str, response_text: str):
        """Stores the query and response in the cache with embedding."""
        # Normalize the query to handle relative time
        normalized_query = normalize_query_dates(query_text)
        query_dates = extract_date_from_query(query_text)
        
        embedding = self.get_embedding(normalized_query)
        key = f"cache:{int(time.time())}"
        
        mapping = {
            "query": query_text,
            "response": response_text,
            "embedding": np.array(embedding, dtype=np.float32).tobytes(),
        }
        
        if query_dates:
            # Join dates with comma for TagField
            # TagField separates values by comma by default
            mapping["date"] = ",".join(query_dates)
        else:
            mapping["date"] = "GENERAL" # Tag for queries without specific date
        
        # Use pipeline to set hash and expire
        pipe = self.redis_client.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, config.CACHE_TTL_SECONDS)
        pipe.execute()
        print(f"Stored in cache: {query_text} (Date: {mapping['date']})")

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
