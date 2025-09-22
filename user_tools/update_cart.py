from typing import Dict, List

def _index_by_id(cart: List[Dict], item_id: str) -> int:
    for i, it in enumerate(cart):
        if it["item_id"] == item_id:
            return i
    return -1

def update_cart(cart: List[Dict], currency: str, ops: List[Dict]) -> Dict:
    cart = [dict(x) for x in cart]
    for op in ops:
        kind = op.get("op")
        item_id = op.get("item_id")
        qty = int(op.get("qty", 1))
        name = op.get("name", item_id)
        price = float(op.get("unit_price", 0.0))
        idx = _index_by_id(cart, item_id)

        if kind == "add":
            if idx == -1:
                cart.append({
                    "item_id": item_id,
                    "name": name,
                    "qty": max(1, qty),
                    "unit_price": price,
                    "options": {}
                })
            else:
                cart[idx]["qty"] += qty
        elif kind == "set_qty" and idx != -1:
            if qty <= 0:
                cart.pop(idx)
            else:
                cart[idx]["qty"] = qty
        elif kind == "remove" and idx != -1:
            cart.pop(idx)
    subtotal = sum(it["qty"] * it["unit_price"] for it in cart)
    return {"cart": cart, "subtotal": subtotal, "currency": currency}