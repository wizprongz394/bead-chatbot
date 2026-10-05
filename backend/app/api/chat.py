"""Chat API. Thin HTTP wrapper around app.services.conversation.engine."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.conversation.engine import handle_turn
from app.services.conversation.state import get_or_create, all_sessions

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: Optional[str]
    state: dict
    evidence: list
    products: list
    actions: list
    suggestions: list = []


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    result = handle_turn(req.session_id, req.message)
    return result


@router.get("/session/{session_id}")
def get_session(session_id: str):
    sessions = all_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    return sessions[session_id].to_dict()


@router.post("/reset/{session_id}")
def reset_session(session_id: str):
    sessions = all_sessions()
    if session_id in sessions:
        del sessions[session_id]
    new_state = get_or_create()
    return {"new_session_id": new_state.session_id}


@router.get("/health")
def health():
    return {"status": "ok"}
