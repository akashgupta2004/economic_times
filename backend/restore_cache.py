import asyncio
import json
import os
from app.services.rag_anything_service import get_rag_app
from lightrag.utils import compute_mdhash_id

def hash_file(file_path: str) -> str:
    import hashlib
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

async def restore_cache():
    print("Initializing RAG backend...")
    rag = get_rag_app()
    await rag._ensure_lightrag_initialized()
    
    file_path = r"temp_uploads\e361e58a-7483-44f5-bc62-a9080ae6ec72.pdf"
    json_path = r"rag_storage\output\e361e58a-7483-44f5-bc62-a9080ae6ec72_3c79b975\e361e58a-7483-44f5-bc62-a9080ae6ec72\hybrid_auto\e361e58a-7483-44f5-bc62-a9080ae6ec72_content_list.json"
    
    print("Loading saved MinerU JSON output...")
    with open(json_path, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
        
    print(f"Loaded {len(content_list)} blocks. Hashing file...")
    file_hash = hash_file(file_path)
    
    # Re-generate doc_id just to be perfectly identical to what it would be
    from raganything.utils import separate_content
    text_content, _ = separate_content(content_list)
    doc_id = compute_mdhash_id(text_content.strip(), prefix="doc-")
    
    print(f"File Hash: {file_hash}")
    print(f"Doc ID: {doc_id}")
    
    print("Restoring to parse_cache...")
    await rag.parse_cache.insert({
        file_hash: {
            "content_list": content_list,
            "doc_id": doc_id
        }
    })
    
    print("SUCCESS! Cache restored. You can now click Ingest in the browser safely.")

if __name__ == "__main__":
    asyncio.run(restore_cache())
