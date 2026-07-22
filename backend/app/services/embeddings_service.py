from langchain_community.embeddings import HuggingFaceEmbeddings
from app.config import settings

class EmbeddingsService:
    def __init__(self):
        # We initialize local embeddings using the model specified in settings
        # By default this will download the model weights to the local cache
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDINGS_MODEL)

    def embed_query(self, text: str) -> list[float]:
        return self.embeddings.embed_query(text)
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embeddings.embed_documents(texts)

embeddings_service = EmbeddingsService()
