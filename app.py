import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from semantic_cache import SemanticCache
from gemini_client import GeminiClient

app = FastAPI()

# Initialize services
cache = SemanticCache()
gemini = GeminiClient()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def read_index():
    return JSONResponse(content={"message": "Go to /static/index.html to view the UI"})

@app.post("/ask")
async def ask_question(request: QueryRequest):
    question = request.question
    start_time = time.time()
    
    # Check Cache
    # We need to modify cache.check to return similarity if possible, 
    # but for now we'll just check if it returns a response.
    # To get similarity, we might need to use search directly or modify check.
    # Let's use search directly here to get more info if we modify semantic_cache.py later,
    # but for now semantic_cache.search returns just the response string.
    # We will infer HIT/MISS based on result.
    
    cached_response = cache.check(question)
    
    if cached_response:
        end_time = time.time()
        return {
            "answer": cached_response,
            "latency": end_time - start_time,
            "source": "CACHE_HIT",
            "similarity": "High (Threshold Met)" # We can improve this later
        }
    
    # Cache Miss
    # Use the LangGraph agent for generation
    initial_state = {"messages": [question]}
    result = agent_app.invoke(initial_state)
    response_text = result.get("answer", "No answer generated.")
    grounding_metadata = result.get("grounding_metadata", {})
    
    end_time = time.time()
    
    # Store in cache (storing only text for now)
    cache.store(question, response_text)
    
    # Process metadata for response
    processed_metadata = {}
    if grounding_metadata:
        try:
            if hasattr(grounding_metadata, 'web_search_queries'):
                processed_metadata['web_search_queries'] = grounding_metadata.web_search_queries
            if hasattr(grounding_metadata, 'grounding_chunks'):
                chunks = []
                for chunk in grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web'):
                        chunks.append({"uri": chunk.web.uri, "title": chunk.web.title})
                processed_metadata['grounding_chunks'] = chunks
        except Exception:
            pass

    return {
        "answer": response_text,
        "latency": end_time - start_time,
        "source": "CACHE_MISS",
        "similarity": "N/A",
        "grounding_metadata": processed_metadata
    }

@app.get("/cache")
async def get_cache():
    entries = cache.get_all_entries()
    return {"entries": entries}

@app.delete("/cache")
async def clear_cache():
    cache.clear_cache()
    return {"message": "Cache cleared"}

# Agent Integration
from agent_graph import agent_app

@app.post("/agent/ask")
async def ask_agent(request: QueryRequest):
    question = request.question
    
    # Invoke the agent
    # The state expects 'messages' as a list of strings
    initial_state = {"messages": [question]}
    result = agent_app.invoke(initial_state)
    
    answer = result.get("answer", "No answer generated.")
    grounding_metadata = result.get("grounding_metadata", {})
    
    # Process grounding metadata for JSON response
    # We need to be careful with the object types from the SDK
    processed_metadata = {}
    if grounding_metadata:
        try:
            # Extract search queries
            if hasattr(grounding_metadata, 'web_search_queries'):
                processed_metadata['web_search_queries'] = grounding_metadata.web_search_queries
            
            # Extract chunks
            if hasattr(grounding_metadata, 'grounding_chunks'):
                chunks = []
                for chunk in grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web'):
                        chunks.append({
                            "uri": chunk.web.uri,
                            "title": chunk.web.title
                        })
                processed_metadata['grounding_chunks'] = chunks
            
            # Extract supports
            if hasattr(grounding_metadata, 'grounding_supports'):
                supports = []
                for support in grounding_metadata.grounding_supports:
                    support_dict = {}
                    if hasattr(support, 'segment'):
                        support_dict['segment'] = {
                            "text": support.segment.text,
                            "start_index": support.segment.start_index,
                            "end_index": support.segment.end_index
                        }
                    if hasattr(support, 'grounding_chunk_indices'):
                        support_dict['grounding_chunk_indices'] = support.grounding_chunk_indices
                    supports.append(support_dict)
                processed_metadata['grounding_supports'] = supports
                
            # Extract search entry point (HTML)
            if hasattr(grounding_metadata, 'search_entry_point') and grounding_metadata.search_entry_point:
                 processed_metadata['search_entry_point'] = grounding_metadata.search_entry_point.rendered_content
                 
        except Exception as e:
            print(f"Error processing metadata: {e}")
            processed_metadata = {"error": "Failed to process grounding metadata"}

    return {
        "answer": answer,
        "grounding_metadata": processed_metadata
    }
