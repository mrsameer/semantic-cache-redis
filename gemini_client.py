import os
from google import genai
from google.genai import types
import config

class GeminiClient:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(config.GOOGLE_APPLICATION_CREDENTIALS)
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LOCATION
        )
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())

    def generate_content(self, prompt: str) -> str:
        """Generates content using Gemini model."""
        response = self.client.models.generate_content(
            model=config.GENERATION_MODEL_ID,
            contents=prompt
        )
        return response.text

    def generate_content_stream(self, prompt: str, use_grounding: bool = False):
        """Streams generated content tokens from Gemini."""
        generation_config = None
        if use_grounding:
            generation_config = types.GenerateContentConfig(
                tools=[self.grounding_tool]
            )

        return self.client.models.generate_content_stream(
            model=config.GENERATION_MODEL_ID,
            contents=prompt,
            config=generation_config,
        )
