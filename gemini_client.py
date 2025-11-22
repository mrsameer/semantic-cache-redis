import os
from google import genai
import config

class GeminiClient:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(config.GOOGLE_APPLICATION_CREDENTIALS)
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LOCATION
        )

    def generate_content(self, prompt: str) -> str:
        """Generates content using Gemini model."""
        response = self.client.models.generate_content(
            model=config.GENERATION_MODEL_ID,
            contents=prompt
        )
        return response.text
