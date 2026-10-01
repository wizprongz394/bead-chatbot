"""Question selection. Priority-ordered. Max 4 questions."""
from app.services.conversation.state import ProblemState

QUESTION_PRIORITY = [
    ("product_family", "What type of pin are you looking for - solid wire, hollow, end-to-end (Tandem Pin), or a pin assembly?"),
    ("application", "What is the application or industry? (e.g., medical, automotive, industrial, PCB)"),
    ("mounting", "Do you need through-hole, surface-mount, or press-fit mounting?"),
    ("pin_type", "Is the pin shape square, round, or something else?"),
    ("material", "Do you have a material preference, or should I show all available materials?"),
]

MAX_QUESTIONS = 4
STOP_THRESHOLD = 3


def _is_filled(problem, field_name):
    return getattr(problem, field_name, None) is not None


def _filled_count(problem):
    return sum(1 for f, _ in QUESTION_PRIORITY if _is_filled(problem, f))


def select_next_question(problem, asked):
    if len(asked) >= MAX_QUESTIONS:
        return None
    if _filled_count(problem) >= STOP_THRESHOLD:
        return None
    for field_name, prompt in QUESTION_PRIORITY:
        if field_name in asked:
            continue
        if not _is_filled(problem, field_name):
            return {"field": field_name, "prompt": prompt}
    return None


def summary(problem):
    labels = {
        "product_family": "Product family", "application": "Application",
        "mounting": "Mounting", "pin_type": "Pin shape", "material": "Material",
        "end_type": "End type", "item_number": "Item number", "volume": "Estimated volume",
        "length_in_min": "Length (min)", "length_in_max": "Length (max)",
        "diameter_in_min": "Diameter (min)", "diameter_in_max": "Diameter (max)",
    }
    lines = []
    for field_name, label in labels.items():
        c = getattr(problem, field_name, None)
        if c is None:
            continue
        marker = ""
        if c.source != "user_stated":
            marker = "  (" + c.source + " - please confirm)"
        lines.append("  - " + label + ": " + str(c.value) + marker)
    return "\n".join(lines) if lines else "  (nothing captured yet)"
