from dataclasses import dataclass, field
import pymupdf4llm
import os
from typing import List

@dataclass
class ContentChunk:
    text: str
    page_number: int
    chunk_type: str = "text"
    metadata: dict = field(default_factory=dict)

def parse_and_chunk(file_path: str) -> List[ContentChunk]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    pages = pymupdf4llm.to_markdown(file_path, page_chunks=True)
    chunks = []
    
    for page in pages:
        text = page.get("text", "")
        metadata = page.get("metadata", {})
        page_num = metadata.get("page", 1)
        
        # Split into smaller chunks if the text is very long
        if len(text) > 2000:
            paragraphs = text.split("\n\n")
            current_chunk_text = ""
            for p in paragraphs:
                if len(current_chunk_text) + len(p) > 2000 and current_chunk_text:
                    chunks.append(ContentChunk(
                        text=current_chunk_text.strip(),
                        page_number=page_num,
                        metadata=metadata.copy()
                    ))
                    current_chunk_text = p + "\n\n"
                else:
                    current_chunk_text += p + "\n\n"
            
            if current_chunk_text.strip():
                chunks.append(ContentChunk(
                    text=current_chunk_text.strip(),
                    page_number=page_num,
                    metadata=metadata.copy()
                ))
        else:
            if text.strip():
                chunks.append(ContentChunk(
                    text=text.strip(),
                    page_number=page_num,
                    metadata=metadata.copy()
                ))
            
    return chunks
