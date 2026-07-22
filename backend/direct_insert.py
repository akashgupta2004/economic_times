import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
import asyncio
from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from app.config import settings
from functools import partial
from lightrag.llm.hf import hf_embed
from transformers import AutoTokenizer, AutoModel

async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    if kwargs.pop("keyword_extraction", None) or "response_format" in kwargs:
        kwargs["response_format"] = {"type": "json_object"}
    return await openai_complete_if_cache(
        settings.RAG_LLM_MODEL, prompt, system_prompt=system_prompt,
        history_messages=history_messages, api_key=settings.OPENAI_API_KEY, **kwargs
    )

async def main():
    print("Loading local embeddings...")
    embed_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
    embed_model_obj = AutoModel.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
    
    embedding_func = EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=2048,
        func=partial(hf_embed, tokenizer=embed_tokenizer, embed_model=embed_model_obj)
    )
    
    print("Initializing LightRAG...")
    rag = LightRAG(
        working_dir="./rag_storage",
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        graph_storage="Neo4JStorage"
    )
    
    await rag.initialize_storages()
    
    print("Reading Pump_B_Guide.txt...")
    with open("temp_uploads/Pump_B_Guide.txt", "r", encoding="utf-8") as f:
        content = f.read()
        
    print("Inserting into Vector DB and Neo4j...")
    await rag.ainsert([content])
    print("Injection complete! The text is now fully mapped.")

if __name__ == "__main__":
    asyncio.run(main())
