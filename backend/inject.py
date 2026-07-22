import asyncio
import json
import logging
from app.services.rag_anything_service import get_rag_app
from raganything.utils import separate_content, insert_text_content

logging.basicConfig(level=logging.INFO)

async def inject():
    print("Initializing RAG backend...")
    rag = get_rag_app()
    # Bypass the mineru check completely:
    from lightrag import LightRAG
    rag.lightrag = LightRAG(
        working_dir=rag.config.working_dir,
        llm_model_func=rag.llm_model_func,
        embedding_func=rag.embedding_func,
        **rag.lightrag_kwargs
    )
    await rag.lightrag.initialize_storages()
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()
    
    json_path = r"rag_storage\output\e361e58a-7483-44f5-bc62-a9080ae6ec72_3c79b975\e361e58a-7483-44f5-bc62-a9080ae6ec72\hybrid_auto\e361e58a-7483-44f5-bc62-a9080ae6ec72_content_list.json"
    print("Loading JSON...")
    with open(json_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
        
    print(f"Separating {len(content_list)} blocks...")
    text_content, _ = separate_content(content_list)
    doc_id = "doc-91cdb1dd238693f14d3dc1c6a8f7d0f9-retry"
    file_name = "e361e58a-7483-44f5-bc62-a9080ae6ec72.pdf"
    
    print(f"Text Content Length: {len(text_content)}")
    print("Starting Gemma 3 Graph Extraction... THIS WILL TAKE A WHILE!")
    print("Make sure Ollama is running and your terminal is visible.")
    
    await insert_text_content(
        rag.lightrag,
        input=text_content,
        file_paths=file_name,
        ids=doc_id,
    )
    print("Graph Extraction Complete!")

if __name__ == "__main__":
    asyncio.run(inject())
