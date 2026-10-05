"""Contextual follow-up suggestions. Optional helper for the engine."""


def suggest_followups(state, last_reply_type="generic"):
    """Return a list of 2-3 suggested next prompts based on state.

    This is a fallback helper; the engine computes most suggestions inline.
    """
    ap = state.active_problem
    suggestions = []

    if ap.item_number is not None and last_reply_type != "compare":
        suggestions.append("Compare " + str(ap.item_number.value) + " with another product")

    if ap.material is not None:
        suggestions.append("Show me products with different materials")

    if ap.pin_type is not None:
        suggestions.append("What are the applications for " + str(ap.pin_type.value) + " pins?")

    if len(suggestions) < 2:
        suggestions.append("What is the swaging process?")
        suggestions.append("What materials does Bead work with?")

    return suggestions[:3]
