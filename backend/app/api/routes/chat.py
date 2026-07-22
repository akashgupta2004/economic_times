from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_anything_service import query_multimodal_rag

router = APIRouter()

class ChatRequest(BaseModel):
    messages: list[dict]
    user_id: str

class ChatResponse(BaseModel):
    answer: str
    confidence: str
    citations: list[dict]

@router.post("/", response_model=ChatResponse)
async def chat_with_copilot(request: ChatRequest):
    try:
        from app.services.agent_service import chat_with_agent
        # Query the Agent (which can use tools like query_machine_logs and search_knowledge_graph)
        answer = await chat_with_agent(request.messages)
        
        return ChatResponse(
            answer=str(answer),
            confidence="High",  # Can be derived from RAG-Anything if supported
            citations=[]
        )
    except Exception as e:
        import traceback
        with open("traceback.log", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))
