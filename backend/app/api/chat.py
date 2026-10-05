"""Chat API. Thin HTTP wrapper around app.services.conversation.engine."""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.conversation.engine import handle_turn
from app.services.conversation.state import (
    ConversationState, get_or_create, all_sessions, _SESSIONS,
)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    state: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: Optional[str]
    state: dict
    evidence: list
    products: list
    actions: list
    suggestions: list = []


def _rehydrate_state(session_id: Optional[str], state_dict: Optional[dict]):
    """
    Rebuild a ConversationState from a client-sent dict.
    This is the stateless-server pattern: the client holds state across turns,
    the server rebuilds it on each request.
    """
    sid = session_id or str(uuid.uuid4())
    state = ConversationState(session_id=sid)

    if state_dict:
        ap = state_dict.get("active_problem") or {}
        for field_name, c in ap.items():
            if c and c.get("value") is not None:
                state.active_problem.set(
                    field_name,
                    c["value"],
                    source=c.get("source", "user_stated"),
                )
        state.questions_asked = state_dict.get("questions_asked") or []
        state.turn_count = state_dict.get("turn_count") or 0
        state.previous_problems = state_dict.get("previous_problems") or []

    _SESSIONS[sid] = state
    return state


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    # Client-held state: rebuild session on the fly
    if req.state is not None or req.session_id:
        _rehydrate_state(req.session_id, req.state)

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
