import re
from typing import Dict, List, Optional

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}


def _normalize_segment_for_match(seg: str) -> str:
    seg = seg.lower()
    seg = re.sub(r"\b(add|remove|delete|set|update|change|to|qty|quantity)\b", " ", seg)
    seg = re.sub(r"\b(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\b", " ", seg)
    seg = re.sub(r"[^\w\s-]", " ", seg)
    seg = re.sub(r"\s+", " ", seg).strip()
    return seg


def _qty_from_text_segment(seg: str) -> int:
    seg = seg.strip().lower()
    m = re.search(r"(\d+)", seg)
    if m:
        return max(1, int(m.group(1)))
    for word, num in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", seg):
            return num
    return 1


def find_by_name_or_id(name_or_id: str, menu_items: List[Dict]) -> Optional[str]:
    key = name_or_id.strip().lower()
    if not key:
        return None
    for it in menu_items:
        if it["item_id"].lower() == key:
            return it["item_id"]
    for it in menu_items:
        if key in it["name"].lower():
            return it["item_id"]
    return None


def _detect_op(seg: str) -> str:
    s = seg.lower()
    if re.search(r"\b(remove|delete)\b", s):
        return "remove"
    if re.search(r"\b(set|update|change)\b", s):
        return "set_qty"
    return "add"


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
        op = _detect_op(seg)
        matched_id = find_by_name_or_id(seg, menu_items)
        if not matched_id:
            matched_id = find_by_name_or_id(_normalize_segment_for_match(seg), menu_items)
        if matched_id:
            qty = _qty_from_text_segment(seg)
            parsed.append({"op": op, "item_id": matched_id, "qty": qty, "options": {}})
        else:
            warnings.append(f"Unrecognized item in: '{seg}'")
    return {"parsed": parsed, "warnings": warnings}
