import asyncio
from app.services.rag_anything_service import process_document

async def main():
    print("Ingesting Pump_B_Guide.txt using the official RAG pipeline...")
    await process_document("temp_uploads/Pump_B_Guide.html")
    print("Ingestion complete! The Vector DB and Knowledge Graph are fully synced.")

if __name__ == "__main__":
    asyncio.run(main())
