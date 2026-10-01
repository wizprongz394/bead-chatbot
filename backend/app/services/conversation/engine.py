import re

from app.services.conversation.state import get_or_create, save
from app.services.conversation.intents import classify
from app.services.conversation.constraints import extract_into_state
from app.services.conversation.questions import select_next_question, summary
from app.services.retrieval.vector_store import search as vsearch, rerank
from app.services.retrieval.product_search import search_products
from app.services.retrieval.answer import compose_qa_answer, compose_refusal


def _format_product_cards(products):
    lines = []
    for p in products[:5]:
        lines.append(
            "  - " + str(p.get("item_number", "?")) + "\n"
            + "    Type: " + str(p.get("pin_type", "-")) + "\n"
            + "    Material: " + str(p.get("material", "-")) + "\n"
            + "    Length: " + str(p.get("length_in", "-"))
            + " | Dia: " + str(p.get("diameter_in", "-"))
        )
    return "\n".join(lines)


def _format_requirement_summary(problem):
    return "Requirement Summary\n" + summary(problem)


def _has_meaningful_constraints(problem):
    """True if at least one filterable constraint is present."""
    return any([
        problem.material,
        problem.pin_type,
        problem.end_type,
        problem.item_number,
        problem.length_in_min,
        problem.length_in_max,
        problem.diameter_in_min,
        problem.diameter_in_max,
    ])


def handle_turn(session_id, message):
    state = get_or_create(session_id)
    state.bump()

    text = (message or "").strip()
    if not text:
        return _response(state, "I didn't catch that. Could you rephrase?", [])

    intent = classify(text)
    state.current_intent = intent
    extract_into_state(text, state.active_problem)

    # ---------- off-topic ----------
    if intent == "off_topic":
        return _response(state, compose_refusal("off_topic"), [])

    # ---------- escalate ----------
    if intent == "escalate":
        save(state)
        return _response(
            state,
            "I'll route this to the appropriate Bead team. "
            "Here's the requirement context I'll pass along:\n\n"
            + _format_requirement_summary(state.active_problem),
            [],
            actions=[{"type": "escalate"}],
        )

    # ---------- RFI ----------
    if intent == "rfi":
        save(state)
        return _response(
            state,
            "For a commercial request like this, I'd recommend submitting an RFI. "
            "Here's the requirement context I've captured so far:\n\n"
            + _format_requirement_summary(state.active_problem)
            + "\n\nYou can submit this to Bead via the contact page.",
            [],
            actions=[{"type": "rfi_prefill"}],
        )

    # ---------- Q&A ----------
    if intent == "qa":
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            qvec = model.encode([text], convert_to_numpy=True)[0].tolist()
            raw = vsearch(qvec, top_k=8)
            evidence = rerank(text, raw, top_k=4)
            evidence = [e for e in evidence if e["_rerank_score"] > 0.35]
        except Exception:
            evidence = []
        if not evidence:
            return _response(state, compose_refusal("related"), [])
        result = compose_qa_answer(text, evidence, use_llm=True)
        return _response(state, result["answer"], result["evidence"])

    # ---------- Compare ----------
    if intent == "compare":
        item_nums = re.findall(r"\b([A-Z]\d{3}-\d{3,4}[A-Z]{0,3})\b", text.upper())
        if len(item_nums) >= 2:
            matched = []
            all_p = search_products(state.active_problem, limit=1000)
            for p in all_p:
                if p["item_number"] in item_nums:
                    matched.append(p)
            if len(matched) >= 2:
                lines = ["Comparison:"]
                for p in matched:
                    lines.append(
                        "  " + p["item_number"]
                        + " - " + str(p.get("pin_type", "-"))
                        + ", " + str(p.get("material", "-"))
                        + ", L=" + str(p.get("length_in", "-"))
                        + ", D=" + str(p.get("diameter_in", "-"))
                    )
                return _response(state, "\n".join(lines), [])
        return _response(
            state,
            "I can compare Bead products if you give me two item numbers. "
            "For example: 'compare W018-584AC and W020-521AC'.",
            [],
        )

    # ---------- Default: discover ----------
    # Only search products if we have something meaningful to filter by.
    if _has_meaningful_constraints(state.active_problem):
        products = search_products(state.active_problem, limit=5)
        if products:
            save(state)
            heading = (
                "I found " + str(len(products))
                + " product(s) matching your requirements:"
            )
            body = _format_product_cards(products)
            next_q = select_next_question(state.active_problem, state.questions_asked)
            tail = ""
            if next_q:
                tail = "\n\nTo narrow this down: " + next_q["prompt"]
                state.questions_asked.append(next_q["field"])
            full = heading + "\n" + body + tail
            return _response(state, full, [], products=products)

    # No meaningful constraints OR no matches: ask a clarifying question.
    next_q = select_next_question(state.active_problem, state.questions_asked)
    if next_q:
        state.questions_asked.append(next_q["field"])
        save(state)
        return _response(state, next_q["prompt"], [])

    # We have constraints, but nothing matched and no more questions to ask.
    save(state)
    return _response(
        state,
        "I've captured these requirements but couldn't find an exact match in the "
        "available Bead catalog:\n\n"
        + _format_requirement_summary(state.active_problem)
        + "\n\nI can route this to Bead's team for confirmation.",
        [],
        actions=[{"type": "rfi_prefill"}],
    )


def _response(state, reply, evidence, products=None, actions=None):
    return {
        "session_id": state.session_id,
        "reply": reply,
        "intent": state.current_intent,
        "state": state.to_dict(),
        "evidence": evidence or [],
        "products": products or [],
        "actions": actions or [],
    }
