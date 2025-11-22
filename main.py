import time
import config
from semantic_cache import SemanticCache
from gemini_client import GeminiClient

def main():
    print("Initializing Semantic Cache and Gemini Client...")
    cache = SemanticCache()
    gemini = GeminiClient()
    
    def ask_question(question: str):
        print(f"\n--- Question: '{question}' ---")
        start_time = time.time()
        
        # 1. Check Cache
        cached_response = cache.check(question)
        
        if cached_response:
            end_time = time.time()
            print(f"Cache HIT! (Time: {end_time - start_time:.4f}s)")
            print(f"Response: {cached_response}")
            return
        
        print("Cache MISS. Querying Gemini...")
        
        # 2. Generate Response
        response = gemini.generate_content(question)
        end_time = time.time()
        print(f"Generated Response (Time: {end_time - start_time:.4f}s)")
        print(f"Response: {response}")
        
        # 3. Store in Cache
        cache.store(question, response)

    # Test Case 1: First query (Cache Miss)
    ask_question("What is the capital of France?")
    
    # Test Case 2: Exact same query (Cache Hit)
    ask_question("What is the capital of France?")
    
    # Test Case 3: Semantically similar query (Cache Hit)
    ask_question("Tell me the capital city of France")
    
    # Test Case 4: Different query (Cache Miss)
    ask_question("What is the capital of Germany?")

if __name__ == "__main__":
    main()
