"""
Lightweight document ingestion pipeline.
Orchestrates: PDF parsing -> Entity extraction -> KG insertion.
Uses only 1 LLM API call per document (for enrichment).
"""
import os
import logging
from typing import Optional

from app.config import settings
from app.services.lightweight_parser import parse_and_chunk
from app.services.kg_extractor import (
    extract_entities_local,
    extract_relations_local,
    enrich_with_llm,
    insert_into_neo4j,
)

logger = logging.getLogger(__name__)


async def ingest_document_lightweight(file_path: str) -> dict:
    """
    Full lightweight ingestion pipeline for a PDF document.
    
    Pipeline:
        1. Parse PDF with pymupdf4llm (CPU-only)
        2. Extract entities with GLiNER
        3. Extract relations with heuristics
        4. Enrich with a single LLM call (1 API call)
        5. Insert into Neo4j
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        Dict with pipeline statistics.
    """
    logger.info(f"Starting lightweight ingestion for: {file_path}")
    
    result = {
        "file": os.path.basename(file_path),
        "status": "success",
        "steps": {}
    }
    
    # Step 1: Parse the PDF
    try:
        chunks = parse_and_chunk(file_path)
        
        # Calculate number of unique pages from chunks
        pages = set(getattr(c, "page_number", 0) for c in chunks)
        num_pages = len(pages)
        
        result["steps"]["parsing"] = {
            "pages": num_pages,
            "chunks": len(chunks),
        }
        logger.info(
            f"Step 1 complete: {num_pages} pages, {len(chunks)} chunks"
        )
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        result["status"] = "failed"
        result["error"] = f"PDF parsing failed: {str(e)}"
        return result
    
    # Step 2: Extract entities locally (zero API calls)
    entities = extract_entities_local(chunks)
    result["steps"]["entity_extraction"] = {
        "entities_found": len(entities),
        "types": {}
    }
    for entity in entities:
        t = entity.entity_type
        result["steps"]["entity_extraction"]["types"][t] = \
            result["steps"]["entity_extraction"]["types"].get(t, 0) + 1
    logger.info(f"Step 2 complete: {len(entities)} entities extracted locally")
    
    # Step 3: Extract relations locally (zero API calls)
    relations = extract_relations_local(chunks, entities)
    result["steps"]["relation_extraction"] = {
        "relations_found": len(relations)
    }
    logger.info(f"Step 3 complete: {len(relations)} relations extracted locally")
    
    # Step 4: Enrich with LLM (exactly 1 API call)
    try:
        summary_text = "\n".join(
            chunk.text for chunk in chunks 
            if chunk.chunk_type in ("text", "heading")
        )[:2000]  # Cap at 2000 chars for the LLM
        
        entities, relations = await enrich_with_llm(entities, relations, summary_text)
        result["steps"]["llm_enrichment"] = {
            "total_entities": len(entities),
            "total_relations": len(relations),
            "api_calls": 1
        }
        logger.info(f"Step 4 complete: LLM enrichment done (1 API call)")
    except Exception as e:
        logger.warning(f"LLM enrichment failed (non-fatal, continuing): {e}")
        result["steps"]["llm_enrichment"] = {"status": "skipped", "reason": str(e)}
    
    # Step 5: Insert into Neo4j
    try:
        neo4j_stats = await insert_into_neo4j(entities, relations, document_title=os.path.basename(file_path))
        result["steps"]["neo4j_insertion"] = neo4j_stats
        logger.info(
            f"Step 5 complete: {neo4j_stats['entities_created']} entities, "
            f"{neo4j_stats['relations_created']} relations inserted into Neo4j"
        )
    except Exception as e:
        logger.error(f"Neo4j insertion failed: {e}")
        result["steps"]["neo4j_insertion"] = {"status": "failed", "error": str(e)}
    
    # Final summary
    result["summary"] = (
        f"Ingested '{os.path.basename(file_path)}': "
        f"{num_pages} pages, {len(entities)} entities, "
        f"{len(relations)} relations. Used 1 LLM API call."
    )
    logger.info(f"Pipeline complete: {result['summary']}")
    
    return result
