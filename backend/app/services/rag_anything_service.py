import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
import asyncio
from functools import partial
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc, logger
from raganything import RAGAnything, RAGAnythingConfig
from dotenv import load_dotenv
from app.config import settings
from lightrag.llm.hf import hf_embed
from transformers import AutoTokenizer, AutoModel
import torch

load_dotenv()


def _get_rag_anything():

    parser = settings.PARSER_MODE if settings.PARSER_MODE in ["mineru", "docling", "paddleocr"] else "docling"

    config = RAGAnythingConfig(
        working_dir="./rag_storage",
        parser=parser,
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )

    from lightrag.llm.openai import openai_complete_if_cache

    llm_model = settings.RAG_LLM_MODEL
    vision_model = settings.VISION_MODEL

    # Text generation model wrapper using OpenAI
    async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        if kwargs.pop("keyword_extraction", None) or "response_format" in kwargs:
            kwargs["response_format"] = {"type": "json_object"}
        return await openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=settings.OPENAI_API_KEY,
            **kwargs,
        )

    # Vision model wrapper using OpenAI
    async def vision_model_func(prompt, system_prompt=None, history_messages=[], image_data=None, messages=None, **kwargs):
        kwargs.pop("response_format", None)
        kwargs.pop("keyword_extraction", None)

        if messages:
            return await openai_complete_if_cache(
                vision_model, "", system_prompt=None, history_messages=[],
                messages=messages, api_key=settings.OPENAI_API_KEY, **kwargs,
            )
        elif image_data:
            return await openai_complete_if_cache(
                vision_model, "", system_prompt=None, history_messages=[],
                messages=[msg for msg in [
                    {"role": "system", "content": system_prompt} if system_prompt else None,
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                        ],
                    } if image_data else {"role": "user", "content": prompt},
                ] if msg is not None],
                api_key=settings.OPENAI_API_KEY, **kwargs,
            )
        else:
            return await llm_model_func(prompt, system_prompt, history_messages, **kwargs)

    # Embedding wrapper using Qwen3 local embedding model
    print("Loading Qwen3-Embedding-0.6B...")
    embed_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
    embed_model_obj = AutoModel.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)

    embedding_func = EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=2048,
        func=partial(
            hf_embed,
            tokenizer=embed_tokenizer,
            embed_model=embed_model_obj,
        ),
    )


    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
        lightrag_kwargs={"graph_storage": "Neo4JStorage"}
    )
    return rag

# Singleton instance
rag_app = None

def get_rag_app():
    global rag_app
    if rag_app is None:
        rag_app = _get_rag_anything()
    return rag_app

async def process_document(file_path: str):
    app = get_rag_app()
    # Process the document completely using dual-graph multimodal parsing
    await app.process_document_complete(
        file_path=file_path, output_dir="./rag_storage/output", parse_method="auto"
    )

async def query_multimodal_rag(query_text: str):
    from lightrag import QueryParam
    app = get_rag_app()
    # Ensure LightRAG storages (Neo4j) are connected before querying
    await app._ensure_lightrag_initialized()
    # Hybrid query searches the visual and text graphs simultaneously
    result = await app.aquery(
        query_text,
        mode="hybrid",
        top_k=15,
        max_entity_tokens=3000,
        max_relation_tokens=3000,
        max_total_tokens=8000
    )
    return result
