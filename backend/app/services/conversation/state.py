"""Conversation state. Supports context switching. Constraints carry provenance."""
from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime, timezone


@dataclass
class Constraint:
    value: any
    source: str = "user_stated"
    confidence: str = "high"

    def to_dict(self):
        return {"value": self.value, "source": self.source, "confidence": self.confidence}


@dataclass
class ProblemState:
    product_family: Optional[Constraint] = None
    application: Optional[Constraint] = None
    mounting: Optional[Constraint] = None
    pin_type: Optional[Constraint] = None
    material: Optional[Constraint] = None
    end_type: Optional[Constraint] = None
    length_in_min: Optional[Constraint] = None
    length_in_max: Optional[Constraint] = None
    square_in_min: Optional[Constraint] = None
    square_in_max: Optional[Constraint] = None
    diameter_in_min: Optional[Constraint] = None
    diameter_in_max: Optional[Constraint] = None
    item_number: Optional[Constraint] = None
    volume: Optional[Constraint] = None
    freeform_notes: list = field(default_factory=list)

    def set(self, field_name, value, source="user_stated", confidence="high"):
        existing = getattr(self, field_name, None)
        if existing is not None and existing.source == "user_stated" and source != "user_stated":
            return
        setattr(self, field_name, Constraint(value=value, source=source, confidence=confidence))

    def known_fields(self):
        return [f for f in self.__dataclass_fields__ if f != "freeform_notes" and getattr(self, f) is not None]

    def to_dict(self):
        out = {}
        for f in self.__dataclass_fields__:
            if f == "freeform_notes":
                out[f] = getattr(self, f)
            else:
                v = getattr(self, f)
                out[f] = v.to_dict() if v else None
        return out


@dataclass
class ConversationState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active_problem: ProblemState = field(default_factory=ProblemState)
    previous_problems: list = field(default_factory=list)
    current_intent: Optional[str] = None
    questions_asked: list = field(default_factory=list)
    turn_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _just_switched: bool = False

    def archive_and_reset(self, reason):
        if self.active_problem.known_fields():
            self.previous_problems.append({
                "problem": self.active_problem.to_dict(),
                "closed_reason": reason,
                "closed_at": datetime.now(timezone.utc).isoformat(),
            })
        self.active_problem = ProblemState()
        self.questions_asked = []

    def bump(self):
        self.turn_count += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "active_problem": self.active_problem.to_dict(),
            "previous_problems": self.previous_problems,
            "current_intent": self.current_intent,
            "questions_asked": self.questions_asked,
            "turn_count": self.turn_count,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


_SESSIONS = {}


def get_or_create(session_id=None):
    if session_id and session_id in _SESSIONS:
        return _SESSIONS[session_id]
    state = ConversationState()
    _SESSIONS[state.session_id] = state
    return state


def save(state):
    _SESSIONS[state.session_id] = state


def all_sessions():
    return _SESSIONS
