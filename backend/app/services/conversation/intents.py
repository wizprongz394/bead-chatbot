"""Rule-based intent classifier."""
import re

INTENTS = ["discover", "qa", "compare", "rfi", "escalate", "off_topic"]

PATTERNS = {
    "compare": [r"\bcompare\b", r"\bversus\b", r"\bvs\.?\b", r"difference between", r"which one (is|would)"],
    "rfi": [r"\b(rfq|rfi|quote|quotation|sample|samples|order)\b", r"\b\d{3,}\s*(pieces|units|pcs|parts)\b", r"\bvolume\b", r"how much (would|does|do)"],
    "escalate": [r"\bspeak to (a )?(human|person|someone|engineer|sales)\b", r"\btalk to (a )?(human|person|someone|engineer|sales)\b", r"\bcontact (a )?(human|person|someone|engineer|sales)\b"],
    "qa": [r"^(what|which|who|when|where|why|how|does|do|can|is|are|will|would)\b", r"\?$", r"\btell me about\b", r"\bexplain\b"],
    "discover": [r"\bi (need|want|am looking for|'m looking for|require)\b", r"\bfind (me|a|an)\b", r"\bshow me\b", r"\blooking for\b", r"\bsearch(ing)? for\b", r"\bdo you (have|make|offer|sell|carry)\b", r"\bhelp me (find|choose|pick)\b"],
    "off_topic": [r"\b(weather|stock price|revenue|politics|sports|recipe)\b", r"\b(your|the) (company'?s?|bead'?s) revenue\b", r"\bhow much (money|profit|revenue)\b"],
}


def classify(text):
    if not text or not text.strip():
        return "off_topic"
    lowered = text.lower().strip()

    # Explicit off-topic patterns must be checked FIRST to avoid
    # the "discover" default catching them via keyword overlap.
    for pattern in PATTERNS["off_topic"]:
        if re.search(pattern, lowered):
            return "off_topic"

    for intent, regexes in PATTERNS.items():
        if intent == "off_topic":
            continue
        for pattern in regexes:
            if re.search(pattern, lowered):
                return intent

    # Safe default: if it mentions a Bead product concept, treat as discover.
    if any(w in lowered for w in ["pin", "connector", "contact", "terminal",
                                  "material", "tandem", "hollow", "solid",
                                  "square", "round", "medical", "automotive"]):
        return "discover"

    # Truly unrecognized. Treat as discover so we can ask a follow-up.
    return "discover"
