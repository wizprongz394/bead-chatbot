"""Rule-based intent classifier."""
import re

INTENTS = ["discover", "qa", "compare", "rfi", "escalate", "off_topic"]

PATTERNS = {
    "compare": [
        r"\bcompare\b", r"\bversus\b", r"\bvs\.?\b",
        r"difference between", r"which one (is|would)",
    ],
    "rfi": [
        r"\b(rfq|rfi|quote|quotation|sample|samples|order)\b",
        r"\b\d{3,}\s*(pieces|units|pcs|parts)\b",
        r"\bvolume\b",
        r"how much (would|does|do)",
        r"\bpricing\b", r"\bprice\b",
    ],
    "escalate": [
        # explicit human-request phrases
        r"\bspeak to (a )?(human|person|someone|engineer|sales|rep|representative)\b",
        r"\btalk to (a )?(human|person|someone|engineer|sales|rep|representative)\b",
        r"\bcontact (a )?(human|person|someone|engineer|sales|rep|representative)\b",
        # direct contact intent
        r"\bi want to (contact|reach|talk to|speak to|get in touch)\b",
        r"\bi('?d| would) like to (contact|reach|talk to|speak to|get in touch)\b",
        r"\bhow (do|can) i (contact|reach|talk to|speak to|get in touch)\b",
        r"\b(contact|reach) (you|bead|sales|support|your team|us)\b",
        r"\bget in touch\b",
        r"\bhow to (contact|reach)\b",
        r"\bcustomer service\b",
        r"\b(a )?(human|real person|representative|rep)\b",
        r"\bemail (address|contact)\b",
        r"\bphone (number)?\b",
        r"\b(contact|support) (info|information)\b",
    ],
    "qa": [
        r"^(what|which|who|when|where|why|how|does|do|can|is|are|will|would)\b",
        r"\?$",
        r"\btell me about\b",
        r"\bexplain\b",
    ],
    "discover": [
        r"\bi (need|want|am looking for|'m looking for|require)\b",
        r"\bfind (me|a|an)\b",
        r"\bshow me\b",
        r"\blooking for\b",
        r"\bsearch(ing)? for\b",
        r"\bdo you (have|make|offer|sell|carry)\b",
        r"\bhelp me (find|choose|pick)\b",
    ],
    "off_topic": [
        r"\b(weather|stock price|revenue|politics|sports|recipe)\b",
        r"\b(your|the) (company'?s?|bead'?s) revenue\b",
        r"\bhow much (money|profit|revenue)\b",
    ],
}

BEAD_KEYWORDS = [
    "pin", "connector", "contact", "terminal", "material",
    "tandem", "hollow", "solid", "square", "round",
    "medical", "automotive", "hollow", "overmold", "pcb",
]


def classify(text):
    if not text or not text.strip():
        return "off_topic"
    lowered = text.lower().strip()

    # Off-topic first
    for pattern in PATTERNS["off_topic"]:
        if re.search(pattern, lowered):
            return "off_topic"

    # Escalate (contact/support) — checked before others to catch "I want to contact you"
    for pattern in PATTERNS["escalate"]:
        if re.search(pattern, lowered):
            return "escalate"

    # Then all other intents in pattern order
    for intent, regexes in PATTERNS.items():
        if intent == "off_topic":
            continue
        if intent == "escalate":
            continue  # already checked
        for pattern in regexes:
            if re.search(pattern, lowered):
                return intent

    # Safe default
    if any(w in lowered for w in BEAD_KEYWORDS):
        return "discover"

    return "discover"
