import re
from typing import Dict, List

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

def _qty_from_text_segment(seg: str) -> int:
    seg = seg.strip().lower()
    m = re.search(r"(\d+)", seg)
    if m:
        return max(1, int(m.group(1)))
    for word, num in NUMBER_WORDS.items():
        if word in seg:
            return num
    return 1

def find_by_name_or_id(name_or_id: str, menu_items: List[Dict]) -> str | None:
    key = name_or_id.strip().lower()
    for it in menu_items:
        if it["item_id"].lower() == key:
            return it["item_id"]
    for it in menu_items:
        if key in it["name"].lower():
            return it["item_id"]
    return None

def parse_order_line(text: str, menu_items: List[Dict]) -> Dict:
    t = (text or "").strip()
    if not t:
        return {"parsed": [], "warnings": ["Empty input"]}
    segments = re.split(r",|\band\b", t, flags=re.IGNORECASE)
    parsed = []
    warnings = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        matched_id = find_by_name_or_id(seg, menu_items)
        if matched_id:
            qty = _qty_from_text_segment(seg)
            parsed.append({"item_id": matched_id, "qty": qty, "options": {}})
        else:
            warnings.append(f"Unrecognized item in: '{seg}'")
    return {"parsed": parsed, "warnings": warnings}