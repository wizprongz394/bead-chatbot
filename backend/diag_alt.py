from app.services.retrieval.product_search import _load_products

catalog = _load_products()
print("Total products:", len(catalog))

base = None
for p in catalog:
    if p.get("item_number") == "W018-584AC":
        base = p
        break

if not base:
    print("ERROR: W018-584AC not found in catalog")
else:
    print()
    print("Base product W018-584AC:")
    print("  pin_type:", base.get("pin_type"))
    print("  material:", base.get("material"))
    print("  end_type:", base.get("end_type"))
    print()

    # Count family members
    same_type = [p for p in catalog if p.get("pin_type") == base.get("pin_type")]
    print("Products with SAME pin_type:", len(same_type))

    same_mat = [p for p in catalog if p.get("material") == base.get("material")]
    print("Products with SAME material:", len(same_mat))

    # Score distribution
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
        scored.append((s, p.get("item_number"), p.get("pin_type"), p.get("material")))

    print()
    print("Score distribution (non-self products):")
    from collections import Counter
    counts = Counter(s for s, *_ in scored)
    for s in sorted(counts.keys(), reverse=True):
        print(f"  score={s}: {counts[s]} products")

    print()
    print("Top 10 by score:")
    scored.sort(key=lambda t: -t[0])
    for s, num, pt, mat in scored[:10]:
        print(f"  {num}  score={s}  type={pt}  material={mat}")
