# Version: 2026-10-06T10:05:41.693022
"""FastAPI app entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router

app = FastAPI(
    title="Bead Electronics Assistant",
    version="0.1.0",
    description="Conversational product discovery + technical assistance for Bead Electronics.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
def root():
    return {"service": "bead-assistant", "status": "ok", "docs": "/docs"}
