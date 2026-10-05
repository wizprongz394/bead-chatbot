from app.services.retrieval.product_search import _load_products
catalog = _load_products()
base = None
for p in catalog:
    if p.get("item_number") == "W018-584AC":
        base = p
        break

print("Base found:", base is not None)
if base:
    print("Base pin_type:", base.get("pin_type"))
    print("Base material:", base.get("material"))
    print()
    same_type = [p for p in catalog if p.get("pin_type") == base.get("pin_type")]
    same_type_mat = [p for p in same_type if p.get("material") == base.get("material")]
    print("Products with same pin_type:", len(same_type))
    print("Products with same pin_type AND material:", len(same_type_mat))
    print()
    print("First 10 with same pin_type:")
    for p in same_type[:10]:
        print("  " + str(p.get("item_number")) + "  " + str(p.get("material")) + "  L=" + str(p.get("length_in")))
