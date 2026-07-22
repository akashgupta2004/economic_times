from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.services.llm_service import llm_service
from app.services.neo4j_service import neo4j_service

router = APIRouter()

class RAGFlowWebhookPayload(BaseModel):
    document_id: str
    chunk_id: str
    text_content: str

def process_chunk_for_kg(text_content: str):
    """
    Background task to extract entities from chunk and upsert to Neo4j.
    """
    triplets = llm_service.extract_entities(text_content)
    if triplets:
        neo4j_service.upsert_triplets(triplets)

@router.post("/ragflow")
async def handle_ragflow_webhook(payload: RAGFlowWebhookPayload, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to receive parsed chunks from RAGFlow and trigger KG extraction in the background.
    """
    background_tasks.add_task(process_chunk_for_kg, payload.text_content)
    return {"status": "processing accepted"}
