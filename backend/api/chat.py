from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from agent.loop import run_agent, get_logs

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: Optional[list] = None


@router.post("/chat")
async def chat(req: ChatRequest):
    result = await run_agent(
        user_message=req.message,
        conversation_id=req.conversation_id,
        history=req.history or [],
    )
    return result


@router.get("/logs")
async def logs(conversation_id: Optional[str] = None):
    return get_logs(conversation_id)
