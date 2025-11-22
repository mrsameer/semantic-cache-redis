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
    response = gemini.generate_content(question)
    end_time = time.time()
    
    # Store in cache
    cache.store(question, response)
    
    return {
        "answer": response,
        "latency": end_time - start_time,
        "source": "CACHE_MISS",
        "similarity": "N/A"
    }

@app.get("/cache")
async def get_cache():
    entries = cache.get_all_entries()
    return {"entries": entries}

@app.delete("/cache")
async def clear_cache():
    cache.clear_cache()
    return {"message": "Cache cleared"}
