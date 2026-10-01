# Bead Electronics - Product Assistant

Conversational AI assistant for Bead Electronics. Helps engineers, buyers, and visitors move from a vague requirement to a specific Bead product, a technical answer, or a structured RFI.

## What it does

- Product discovery in natural language: "I need a square tandem pin for a medical device, material C51000"
- Progressive constraint capture: targeted follow-up questions, conversation state
- Grounded technical Q&A: retrieves from Bead's own content, cites sources, never invents facts
- RFI routing: recognizes commercial intent, produces a structured requirement summary
- Refusal safety: when it can't verify, it says so and routes to a human

## Architecture

    Frontend (port 5173)  -->  Backend FastAPI (port 8000)  -->  Data layer
    static HTML/JS/CSS          conversation engine               products.json
                                retrieval + rerank                content_chunks
                                product search                    embeddings.npz
                                Ollama LLM provider

The LLM is the conversational layer. The retrieval system is the evidence layer. Deterministic application logic is the control layer. The LLM never decides facts.

## Quick start

Backend:

    cd backend
    pip install -r requirements.txt
    python -m app.knowledge.run_ingest
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Frontend (second terminal):

    cd frontend
    python -m http.server 5173

Then open http://localhost:5173

## Requirements

- Python 3.11+
- Ollama with qwen2.5-coder:7b (optional - falls back to deterministic mode if unavailable)
- ~2 GB disk for Python deps (torch, transformers)

## Data sources

Crawled from Bead's public site, respecting robots.txt:

- catalog.beadelectronics.com - product catalog (291 products)
- beadelectronics.com/blog - technical blog posts
- www.beadelectronics.com - product, application, company pages

## Status

Day 1 complete - full end-to-end vertical slice working.
See DATA_FEASIBILITY.md for what Bead's site provides.
