"""Compose grounded answers from retrieval evidence. Never invents facts."""
from app.services.llm.factory import get_provider


REFUSAL_UNSUPPORTED = (
    "I couldn't verify that from Bead Electronics' available technical information. "
    "I can help route this to the appropriate Bead team instead."
)
REFUSAL_OFF_TOPIC = (
    "That's outside what I can help with here. I'm focused on Bead Electronics "
    "contact pins, connector applications, and technical specifications. "
    "Is there something in that area I can help with?"
)
REFUSAL_RELATED_OUT_OF_SCOPE = (
    "I don't have that specific information in the Bead resources I can access, "
    "but I can capture your requirement and route it to a Bead engineer who can confirm it."
)
REFUSAL_AMBIGUOUS = (
    "I want to make sure I answer the right question - are you asking about a "
    "specific part, or about Bead's general capabilities?"
)


def _trim_to_first_paragraphs(text, max_chars=400):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = []
    skip_prefixes = (
        "Request a Quote", "Capabilities", "Solid Pin Configurator",
        "800.", "QUICK LINKS", "Build Your Pins", "All Categories",
        "Products", "Applications", "Markets", "Resources", "Company",
    )
    for ln in lines:
        if any(ln.startswith(p) for p in skip_prefixes):
            continue
        if len(ln) < 25 and ln.isupper():
            continue
        if len(ln) < 3:
            continue
        # Skip a leading line that starts mid-sentence (lowercase first letter)
        if not cleaned and ln and ln[0].islower():
            continue
        cleaned.append(ln)
        if sum(len(x) for x in cleaned) >= max_chars:
            break
    if not cleaned and lines:
        return lines[0][:max_chars]
    return "\n".join(cleaned)


def _format_citations(evidence):
    seen = set()
    lines = []
    for e in evidence:
        url = e.get("source_url")
        title = e.get("source_title", url)
        if url in seen:
            continue
        seen.add(url)
        lines.append("  - " + str(title) + "\n    " + str(url))
    return "\n".join(lines) if lines else "  (no sources)"


def compose_qa_answer(question, evidence, use_llm=True):
    if not evidence:
        return {"answer": REFUSAL_UNSUPPORTED, "citations": "", "evidence": [], "refused": True}

    citations = _format_citations(evidence)

    if not use_llm:
        top = evidence[0]
        trimmed = _trim_to_first_paragraphs(top["text"])
        answer = "Here's what I found on this topic:\n\n" + trimmed
        return {"answer": answer, "citations": citations, "evidence": evidence, "refused": False}

    provider = get_provider()
    context_blocks = []
    for i, e in enumerate(evidence, 1):
        context_blocks.append("[Source " + str(i) + "] " + str(e.get("source_title")) + "\n" + e["text"])
    context = "\n\n---\n\n".join(context_blocks)

    system = (
        "You are a technical assistant for Bead Electronics, a custom contact pin manufacturer. "
        "Answer ONLY using the provided sources. Do not invent specifications, part numbers, "
        "pricing, or availability. If the sources do not answer the question, say so plainly. "
        "Keep the answer under 150 words and cite sources by number like [Source 1]. "
        "Do not add a Sources list at the end - the UI already shows them."
    )
    user = "Question: " + question + "\n\nSources:\n" + context + "\n\nAnswer:"

    try:
        answer = provider.complete(system=system, user=user, temperature=0.2, max_tokens=400)
    except Exception:
        answer = ""

    if not answer.strip() or len(answer.strip()) < 20:
        top = evidence[0]
        trimmed = _trim_to_first_paragraphs(top["text"])
        answer = "Here's what I found on this topic:\n\n" + trimmed
    else:
        answer = answer.strip()

    return {"answer": answer, "citations": citations, "evidence": evidence, "refused": False}


def compose_refusal(kind="unsupported"):
    if kind == "off_topic":
        return REFUSAL_OFF_TOPIC
    if kind == "related":
        return REFUSAL_RELATED_OUT_OF_SCOPE
    if kind == "ambiguous":
        return REFUSAL_AMBIGUOUS
    return REFUSAL_UNSUPPORTED
