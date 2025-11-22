import os
import vertexai
from vertexai.generative_models import GenerativeModel
import config

class GeminiClient:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(config.GOOGLE_APPLICATION_CREDENTIALS)
        vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
        self.model = GenerativeModel(config.GENERATION_MODEL_ID)

    def generate_content(self, prompt: str) -> str:
        """Generates content using Gemini model."""
        response = self.model.generate_content(prompt)
        return response.text
