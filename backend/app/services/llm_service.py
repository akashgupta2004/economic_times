from litellm import completion
from app.config import settings
import json

class LLMService:
    def __init__(self):
        self.model = settings.LLM_MODEL

    def generate_response(self, messages: list[dict], temperature: float = 0.2) -> str:
        """
        Generic API-agnostic LLM completion via litellm.
        Uses settings.LLM_MODEL which can be "gemini/gemini-pro", "groq/llama3-70b-8192", etc.
        """
        response = completion(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    def extract_entities(self, text: str) -> dict:
        """
        Extracts entities for the Knowledge Graph.
        Returns a dictionary of relationships.
        """
        prompt = f"""
        Extract the following industrial entities from the text:
        - Equipment Tags (e.g. PMP-101A)
        - Process Parameters (e.g. 300 PSI)
        - Personnel
        
        Return the result as a JSON array of RDF triplets: [ {{"subject": "...", "predicate": "...", "object": "..."}} ]
        
        Text: {text}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response_text = self.generate_response(messages)
        
        try:
            # Very basic parsing, in production use structured outputs / function calling
            # find JSON block
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(response_text[start:end])
            return []
        except Exception as e:
            print(f"Failed to parse entities: {e}")
            return []

llm_service = LLMService()
