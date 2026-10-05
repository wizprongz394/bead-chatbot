from app.services.conversation.engine import _find_product, _handle_alternatives
from app.services.conversation.state import get_or_create

# Direct test of _find_product
base = _find_product("W018-584AC")
print("_find_product returns:", type(base).__name__)
print("Has keys:", list(base.keys())[:5] if base else None)
print()

# Direct test of _handle_alternatives
state = get_or_create()
result = _handle_alternatives(state, "show me alternatives to W018-584AC")
print("Result keys:", list(result.keys()))
print("Products count:", len(result.get("products", [])))
print("First 3 products:")
for p in result.get("products", [])[:3]:
    print("  ", p.get("item_number"), p.get("pin_type"), p.get("material"))
print()
print("Reply preview:")
print(result.get("reply", "")[:300])
