import json
from pathlib import Path
from typing import Dict, List, Optional

def fetch_menu(categories: Optional[List[str]] = None) -> Dict:
    DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "menu.json"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    cat_filter = {c.lower() for c in categories} if categories else None
    for cat in data.get("categories", []):
        if cat_filter and cat["name"].lower() not in cat_filter:
            continue
        for it in cat.get("items", []):
            it_copy = it.copy()
            it_copy["category"] = cat["name"]
            items.append(it_copy)
    return {
        "menu_version": data.get("version", "v1"),
        "currency": data.get("currency", "INR"),
        "items": items,
    }