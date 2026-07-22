from fastapi import APIRouter
from app.services.db_service import get_recent_jobs, init_db
from app.services.neo4j_service import neo4j_service
import random
import time

router = APIRouter()

# Initialize DB on load
init_db()

@router.get("/stats")
async def get_dashboard_stats():
    # Get graph stats from Neo4j
    neo4j_stats = neo4j_service.get_stats()
    
    # We don't have a direct count of "Documents" ingested in RAGFlow without an API call,
    # so we'll mock that specific number or count from jobs.
    jobs = get_recent_jobs(limit=100)
    docs_ingested = len([j for j in jobs if j["status"] == "Completed"])
    
    # Mocking active queries for demonstration
    active_queries = random.randint(10, 50)
    
    return {
        "documents_ingested": docs_ingested,
        "kg_nodes": neo4j_stats["nodes"],
        "active_queries": active_queries
    }

@router.get("/jobs")
async def get_dashboard_jobs():
    jobs = get_recent_jobs(limit=5)
    return jobs

@router.post("/sync")
async def trigger_ragflow_sync():
    # In a real scenario, this would trigger RAGFlow API
    # For now, we simulate adding a job
    from app.services.db_service import add_job
    job_id = f"JOB-{random.randint(1000, 9999)}"
    add_job(job_id, "Manual_Sync_Triggered.pdf", "Processing")
    
    return {"status": "success", "message": f"Sync triggered successfully. Job ID: {job_id}"}
