from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Industrial Copilot Backend"

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # OpenAI Settings (primary LLM provider)
    OPENAI_API_KEY: str = ""

    # Model Selection
    LLM_MODEL: str = "gpt-4o-mini"  # Used by agent_service (litellm format)
    RAG_LLM_MODEL: str = "gpt-4o-mini"    # Used by RAG/LightRAG (bare model name)
    VISION_MODEL: str = "gpt-4o-mini"

    # Parser Mode: "lightweight" (pdfplumber, CPU), "docling" (CPU), or "mineru" (GPU)
    PARSER_MODE: str = "docling"

    # Embeddings
    EMBEDDINGS_MODEL: str = "all-MiniLM-L6-v2"
    HF_HUB_DISABLE_SYMLINKS_WARNING: str = "1"

    class Config:
        env_file = ".env"


settings = Settings()
