"""Main conversation turn handler. Orchestrates intent, constraints, questions, retrieval."""
import logging
import re

from app.services.conversation.state import get_or_create, save
from app.services.conversation.intents import classify
from app.services.conversation.constraints import extract_into_state, extract_item_number
from app.services.conversation.questions import select_next_question, summary
from app.services.retrieval.vector_store import search as vsearch, rerank
from app.services.retrieval.product_search import search_products, _load_products
from app.services.retrieval.answer import compose_qa_answer, compose_refusal

logger = logging.getLogger(__name__)


COMPARE_FIELDS = [
    ("item_number", "Item Number"),
    ("pin_type", "Pin Type"),
    ("material", "Material"),
    ("end_type", "End Type"),
    ("feature_type", "Feature Type"),
    ("length_in", "Length"),
    ("square_in", "Square"),
    ("diameter_in", "Diameter"),
]


def _format_product_cards(products):
    lines = []
    for p in products[:5]:
        lines.append(
            "  - " + str(p.get("item_number", "?"))
            + "  |  " + str(p.get("pin_type", "-"))
            + "  |  " + str(p.get("material", "-"))
            + "  |  L=" + str(p.get("length_in", "-"))
            + "  D=" + str(p.get("diameter_in", "-"))
        )
    return "\n".join(lines)


def _format_requirement_summary(problem):
    return "Requirement Summary\n" + summary(problem)


def _has_meaningful_constraints(problem):
    return any([
        problem.material, problem.pin_type, problem.end_type,
        problem.item_number, problem.length_in_min, problem.length_in_max,
        problem.diameter_in_min, problem.diameter_in_max,
    ])


def _find_product(item_number):
    catalog = _load_products()
    num_upper = item_number.upper()
    for p in catalog:
        if p.get("item_number", "").upper() == num_upper:
            return {k: v for k, v in p.items() if not k.startswith("_")}
    return None


def _relaxed_search(problem, limit=5):
    import copy
    drop_order = ["application", "product_family", "mounting", "end_type", "pin_type"]

    def try_search(drop_fields):
        p = copy.copy(problem)
        for field in drop_fields:
            setattr(p, field, None)
        return search_products(p, limit=limit)

    for i in range(1, len(drop_order) + 1):
        results = try_search(drop_order[:i])
        if results:
            return results
    return []


def _handle_compare(state, text):
    item_nums = re.findall(r"\b([A-Z]\d{3}-\d{3,4}[A-Z]{0,3})\b", text.upper())
    if len(item_nums) < 2:
        return _response(
            state,
            "I can compare two Bead products if you give me their item numbers. "
            "For example: 'compare W018-584AC and W020-431AC'.",
            [],
            suggestions=[
                "Compare W018-584AC and W020-431AC",
                "Compare W025-048AC and W025-051AC",
            ],
        )

    seen, unique = set(), []
    for n in item_nums:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    if len(unique) < 2:
        return _response(state, "I need two different item numbers to compare.", [])

    a_num, b_num = unique[0], unique[1]
    a, b = _find_product(a_num), _find_product(b_num)

    if a is None and b is None:
        return _response(state, "I couldn't find " + a_num + " or " + b_num + " in the Bead catalog.", [])
    if a is None:
        return _response(state, "I found " + b_num + " but not " + a_num + " in the Bead catalog.", [])
    if b is None:
        return _response(state, "I found " + a_num + " but not " + b_num + " in the Bead catalog.", [])

    rows = []
    differences = 0
    for key, label in COMPARE_FIELDS:
        av = a.get(key, "-") or "-"
        bv = b.get(key, "-") or "-"
        same = (av == bv)
        if not same:
            differences += 1
        rows.append({"field": key, "label": label, "a": av, "b": bv, "same": same})

    same_count = len(rows) - differences
    lines = [
        "Comparing " + a_num + " and " + b_num + ":",
        "",
        "  - " + str(same_count) + " field(s) match",
        "  - " + str(differences) + " field(s) differ",
    ]
    meaningful = [r for r in rows if not r["same"] and r["field"] != "item_number"]
    if meaningful:
        lines.append("")
        lines.append("Key differences:")
        for r in meaningful[:6]:
            lines.append(
                "  - " + r["label"] + ":  " + a_num + " = " + str(r["a"])
                + "   |   " + b_num + " = " + str(r["b"])
            )

    save(state)
    return _response(
        state,
        "\n".join(lines),
        [],
        products=[a, b],
        actions=[{"type": "comparison", "rows": rows, "a": a, "b": b}],
        suggestions=[
            "Show me alternatives to " + a_num,
            "Request a quote for " + a_num,
            "Compare " + a_num + " with another product",
        ],
    )


def _handle_alternatives(state, text):
    item_num = extract_item_number(text)
    base = None
    if item_num:
        base = _find_product(item_num)
    if base is None and state.active_problem.item_number is not None:
        base = _find_product(state.active_problem.item_number.value)
    if base is None:
        return _response(
            state,
            "Which product should I find alternatives for? Give me an item number like W018-584AC.",
            [],
            suggestions=["Alternatives to W018-584AC", "Alternatives to W020-431AC"],
        )

    catalog = _load_products()

    def score(p):
        if p.get("item_number") == base.get("item_number"):
            return -1
        s = 0
        if p.get("pin_type") and base.get("pin_type") and p["pin_type"] == base["pin_type"]:
            s += 10
        if p.get("material") and base.get("material") and p["material"] == base["material"]:
            s += 5
        if p.get("end_type") and base.get("end_type") and p["end_type"] == base["end_type"]:
            s += 2
        if p.get("square_in") and base.get("square_in") and p["square_in"] == base["square_in"]:
            s += 1
        if p.get("diameter_in") and base.get("diameter_in") and p["diameter_in"] == base["diameter_in"]:
            s += 1
        return s

    scored = []
    for p in catalog:
        s = score(p)
        if s < 0:
            continue
        scored.append((s, {k: v for k, v in p.items() if not k.startswith("_")}))

    scored.sort(key=lambda sp: (-sp[0], sp[1].get("item_number", "")))
    top = [p for _, p in scored[:5]]

    if not top:
        return _response(state, "I couldn't find alternatives to " + base["item_number"] + ".", [])

    reply = (
        "Here are products similar to " + base["item_number"] + " ("
        + str(base.get("pin_type", "?")) + ", " + str(base.get("material", "?"))
        + "):\n\n" + _format_product_cards(top)
        + "\n\nSimilarity is based on shared pin type, material, end type, and "
        "dimensional attributes. Please confirm the exact specifications with Bead "
        "before selection."
    )

    save(state)
    return _response(
        state, reply, [],
        products=top,
        suggestions=[
            "Compare " + base["item_number"] + " and " + top[0]["item_number"],
            "Show me products like " + top[0]["item_number"],
        ],
    )


SWITCH_PATTERNS = [
    r"\bactually\b.{0,30}\bforget\b",
    r"\bforget (that|it|the|this)\b",
    r"\bnew (question|requirement|request)\b",
    r"\bstart over\b",
    r"\bnever ?mind\b",
]


def _is_context_switch(text):
    t = text.lower()
    return any(re.search(p, t) for p in SWITCH_PATTERNS)


def handle_turn(session_id, message):
    state = get_or_create(session_id)
    state.bump()

    text = (message or "").strip()
    if not text:
        return _response(state, "I didn't catch that. Could you rephrase?", [])

    if _is_context_switch(text):
        if state.active_problem.known_fields():
            state.archive_and_reset("user initiated context switch")
        state._just_switched = True

    intent = classify(text)
    state.current_intent = intent

    if intent == "discover" and re.search(r"\b(similar|alternatives?|like)\b", text.lower()):
        return _handle_alternatives(state, text)

    extract_into_state(text, state.active_problem)

    if intent == "off_topic":
        return _response(state, compose_refusal("off_topic"), [])

    if intent == "escalate":
        save(state)
        return _response(
            state,
            "I'll route this to the appropriate Bead team.\n\n"
            + _format_requirement_summary(state.active_problem),
            [],
            actions=[{"type": "escalate"}],
        )

    if intent == "rfi":
        save(state)
        return _response(
            state,
            "For a commercial request like this, I'd recommend submitting an RFI.\n\n"
            + _format_requirement_summary(state.active_problem)
            + "\n\nYou can submit this to Bead via the contact page.",
            [],
            actions=[{"type": "rfi_prefill"}],
            suggestions=["Request a sample", "What is Bead's lead time?"],
        )

    if intent == "qa":
        # Surface real errors to logs. Only catch expected retrieval misses.
        try:
            from app.knowledge.embed import load_pretrained, embed_texts as _embed
            load_pretrained()
            qvec = _embed([text])[0]
            raw = vsearch(qvec, top_k=8)
            evidence = rerank(text, raw, top_k=4)
            evidence = [e for e in evidence if e["_rerank_score"] > 0.35]
            logger.info("QA retrieval: query=%r, top_k=%d, kept=%d", text, len(raw), len(evidence))
        except Exception as exc:
            logger.exception("QA retrieval failed: %s", exc)
            evidence = []

        if not evidence:
            return _response(state, compose_refusal("related"), [], suggestions=[
                "What is the swaging process?",
                "What materials does Bead work with?",
            ])
        result = compose_qa_answer(text, evidence, use_llm=True)
        return _response(state, result["answer"], result["evidence"])

    if intent == "compare":
        return _handle_compare(state, text)

    if _has_meaningful_constraints(state.active_problem):
        products = search_products(state.active_problem, limit=5)
        if products:
            save(state)
            heading = "I found " + str(len(products)) + " product(s) matching your requirements:"
            body = _format_product_cards(products)
            next_q = select_next_question(state.active_problem, state.questions_asked)
            tail = ""
            if next_q:
                tail = "\n\nTo narrow this down: " + next_q["prompt"]
                state.questions_asked.append(next_q["field"])

            product_suggestions = []
            if len(products) >= 2:
                product_suggestions.append(
                    "Compare " + products[0]["item_number"] + " and " + products[1]["item_number"]
                )
            product_suggestions.append("Show me alternatives to " + products[0]["item_number"])
            product_suggestions.append("Request a quote for " + products[0]["item_number"])

            return _response(state, heading + "\n" + body + tail, [],
                             products=products, suggestions=product_suggestions)

        relaxed = _relaxed_search(state.active_problem, limit=5)
        if relaxed:
            save(state)
            heading = (
                "No exact match with all constraints, but here are the closest "
                "products (with fewer filters applied):"
            )
            return _response(
                state,
                heading + "\n" + _format_product_cards(relaxed) + "\n\nYou can refine this or request an RFI.",
                [],
                products=relaxed,
                suggestions=[
                    "Show me alternatives to " + relaxed[0]["item_number"],
                    "Request a quote for " + relaxed[0]["item_number"],
                ],
            )

    next_q = select_next_question(state.active_problem, state.questions_asked)
    if next_q:
        state.questions_asked.append(next_q["field"])
        save(state)
        return _response(state, next_q["prompt"], [])

    save(state)
    return _response(
        state,
        "I've captured these requirements but couldn't find a match.\n\n"
        + _format_requirement_summary(state.active_problem),
        [],
        actions=[{"type": "rfi_prefill"}],
    )


def _response(state, reply, evidence, products=None, actions=None, suggestions=None):
    if getattr(state, "_just_switched", False):
        reply = "Got it - starting fresh.\n\n" + (reply or "")
        state._just_switched = False
    return {
        "session_id": state.session_id,
        "reply": reply,
        "intent": state.current_intent,
        "state": state.to_dict(),
        "evidence": evidence or [],
        "products": products or [],
        "actions": actions or [],
        "suggestions": suggestions or [],
    }
