import os
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from google import genai
from google.genai import types
from dotenv import load_dotenv
import config

# Load environment variables
load_dotenv()

# Define the state of the agent
class AgentState(TypedDict):
    messages: List[str]
    answer: str
    grounding_metadata: dict

# Initialize Gemini Client
# Use Vertex AI configuration from config.py
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(config.GOOGLE_APPLICATION_CREDENTIALS)
client = genai.Client(
    vertexai=True,
    project=config.PROJECT_ID,
    location=config.LOCATION
)

# Define the tool
grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

def call_gemini(state: AgentState):
    """
    Node that calls Gemini with the Google Search tool enabled.
    """
    messages = state['messages']
    last_message = messages[-1] if messages else ""
    
    # Configure the generation request
    generation_config = types.GenerateContentConfig(
        tools=[grounding_tool]
    )
    
    try:
        response = client.models.generate_content(
            model=config.GENERATION_MODEL_ID, # Use configured model
            contents=last_message,
            config=generation_config,
        )
        
        answer = response.text
        grounding_metadata = {}
        
        # Extract grounding metadata if available
        if response.candidates and response.candidates[0].grounding_metadata:
            # We need to convert the object to a dict to be serializable if needed, 
            # or just pass the object if the state allows. 
            # For simplicity in the API response later, let's extract key parts.
            gm = response.candidates[0].grounding_metadata
            
            # Helper to convert objects to dicts (simplified)
            grounding_metadata = {
                "web_search_queries": gm.web_search_queries,
                "search_entry_point": gm.search_entry_point.rendered_content if gm.search_entry_point else None,
                # We might need more processing here for chunks and supports
                # but let's keep it raw-ish for now or process it in the app.py
            }
            # Note: The actual object structure might be complex to serialize directly.
            # We will store the raw response object in a way we can extract from later 
            # or just the text and let the app handle the rest? 
            # Let's actually try to return the raw response object's relevant parts.
            
            # For the purpose of this agent, let's store the raw grounding metadata object 
            # if possible, or a dict representation.
            # The API response needs to be JSON serializable.
            
            # Let's reconstruct the citation logic here or in the app. 
            # For now, let's just pass the text.
            pass

        return {
            "answer": answer,
            "grounding_metadata": response.candidates[0].grounding_metadata
        }
        
    except Exception as e:
        return {
            "answer": f"Error calling Gemini: {str(e)}",
            "grounding_metadata": {}
        }

# Define the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("gemini_search", call_gemini)

# Set entry point
workflow.set_entry_point("gemini_search")

# Add edges
workflow.add_edge("gemini_search", END)

# Compile the graph
agent_app = workflow.compile()
