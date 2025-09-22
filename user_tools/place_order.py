from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "order_history.json"

def place_order(cart: List[Dict], user_id: str, notes: str = "") -> Dict:
    total = sum(it["qty"] * it["unit_price"] for it in cart)
    eta = 30
    order_id = f"ORD-{int(datetime.utcnow().timestamp())}"
    return {"order_id": order_id, "eta_minutes": eta, "total": total, "currency": "INR"}

def save_order_history(user_id: str, order_id: str, cart: List[Dict], total: float, currency: str, timestamp: str) -> Dict:
    record = {
        "user_id": user_id,
        "order_id": order_id,
        "timestamp": timestamp,
        "total": total,
        "currency": currency,
        "items": [x["item_id"] for x in cart]
    }
    try:
        if HISTORY_PATH.exists():
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        else:
            data = []
    except Exception:
        data = []
    data.append(record)
    HISTORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True}