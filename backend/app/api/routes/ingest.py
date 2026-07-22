from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
import logging

from app.config import settings
from neo4j import GraphDatabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/graph")
async def get_graph():
    uri = settings.NEO4J_URI
    user = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 300")
            nodes = {}
            links = []

            for record in result:
                n = record["n"]
                m = record["m"]
                r = record["r"]

                # Check for id property if element_id is unavailable
                n_id = getattr(n, "element_id", getattr(n, "id", str(hash(n))))
                m_id = getattr(m, "element_id", getattr(m, "id", str(hash(m))))

                if n_id not in nodes:
                    nodes[n_id] = {
                        "id": n_id,
                        "label": list(n.labels)[0] if n.labels else "Node",
                        "properties": dict(n)
                    }
                if m_id not in nodes:
                    nodes[m_id] = {
                        "id": m_id,
                        "label": list(m.labels)[0] if m.labels else "Node",
                        "properties": dict(m)
                    }

                links.append({
                    "source": n_id,
                    "target": m_id,
                    "label": r.type
                })

        driver.close()
        return {"nodes": list(nodes.values()), "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def ingest_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF, etc.) into the Knowledge Graph.
    Uses lightweight pipeline (pdfplumber + local extraction) or MinerU
    depending on PARSER_MODE in .env.
    """
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    import uuid
    from app.services.db_service import add_job
    job_id = f"JOB-{str(uuid.uuid4())[:8].upper()}"

    try:
        if settings.PARSER_MODE == "lightweight":
            # Use the new lightweight CPU-only pipeline
            from app.services.ingest_pipeline import ingest_document_lightweight
            result = await ingest_document_lightweight(file_path)
            logger.info(f"Lightweight ingestion result: {result.get('summary', 'done')}")
        else:
            # Fallback to RAGAnything (MinerU/Docling/etc)
            from app.services.rag_anything_service import process_document
            await process_document(file_path)

        add_job(job_id, file.filename, "Completed")
    except Exception as e:
        add_job(job_id, file.filename, "Failed")
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Document processed successfully", "file_name": file.filename}


@router.post("/upload_sqlite")
async def upload_sqlite(file: UploadFile = File(...)):
    sqlite_dir = "./sqlite_uploads"
    os.makedirs(sqlite_dir, exist_ok=True)

    if not (file.filename.endswith(".sqlite") or file.filename.endswith(".db")):
        raise HTTPException(status_code=400, detail="File must be a .sqlite or .db file")

    file_path = os.path.join(sqlite_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    import uuid
    from app.services.db_service import add_job
    job_id = f"JOB-{str(uuid.uuid4())[:8].upper()}"

    try:
        add_job(job_id, file.filename, "Completed")
    except Exception as e:
        add_job(job_id, file.filename, "Failed")
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "SQLite database uploaded successfully", "file_name": file.filename}
