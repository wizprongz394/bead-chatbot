import json
with open("app/data/products.json", "r", encoding="utf-8") as f:
    products = json.load(f)
sample = products[0]
print("Fields on first product:", list(sample.keys()))
print()
print("Has source_url:", "source_url" in sample)
if "source_url" in sample:
    print("URL:", sample["source_url"])
