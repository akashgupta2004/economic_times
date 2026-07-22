import os
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import chat, webhook, dashboard, ingest
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Industrial Copilot and Knowledge Graph Pipeline",
    version="1.0.0"
)

# Allow CORS for frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
