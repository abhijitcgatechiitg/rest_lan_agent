import os
from dotenv import load_dotenv
from agent.state import AgentState
from agent.assistant import phrase
from user_tools.fetch_menu import fetch_menu
from user_tools.parse_order_line import parse_order_line
from user_tools.update_cart import update_cart
from user_tools.place_order import place_order, save_order_history
from datetime import datetime

load_dotenv()

CURRENCY = os.getenv("CURRENCY", "USD")
SYSTEM_PROMPT = open("agent/system_prompt_restaurant.txt", encoding="utf-8").read()


def currency_symbol(currency: str) -> str:
    return {
        "USD": "$",
        "INR": "₹",
        "EUR": "€",
        "GBP": "£",
    }.get((currency or "").upper(), "$")


def fmt_money(amount: float, currency: str) -> str:
    return f"{currency_symbol(currency)}{amount:.2f}"


def md_cart(cart, subtotal, currency):
    lines = ["\n🧺 Your Cart"]
    for it in cart:
        lines.append(f"- {it['name']} × {it['qty']} — {fmt_money(it['qty'] * it['unit_price'], currency)}")
    lines.append(f"Subtotal: {fmt_money(subtotal, currency)}")
    return "\n".join(lines)


def md_menu(items, currency):
    lines = ["\n📖 Menu"]
    for it in items:
        lines.append(f"- {it['name']} ({it['item_id']}) [{it['category']}] — {fmt_money(float(it['price']), currency)}")
    return "\n".join(lines)


def _ops_from_parsed(parsed_items, menu_items):
    ops = []
    for p in parsed_items:
        m = next((i for i in menu_items if i["item_id"] == p["item_id"]), None)
        if not m:
            continue
        ops.append({
            "op": p.get("op", "add"),
            "item_id": m["item_id"],
            "qty": p.get("qty", 1),
            "name": m["name"],
            "unit_price": m["price"],
            "options": p.get("options", {}),
        })
    return ops


def _warning_reply(warnings, items):
    menu_names = ", ".join(it["name"] for it in items[:5])
    joined = "\n".join(f"- {w}" for w in warnings)
    return f"⚠️ I could not find some items:\n{joined}\n\nTry menu items like: {menu_names}\nType 'show menu' to see everything."


def new_state() -> AgentState:
    return {
        "user_id": "cli-user",
        "stage": "greet",
        "cart": [],
        "subtotal": 0.0,
        "currency": CURRENCY,
        "menu_version": "",
        "last_user_message": "",
        "last_ai_message": "",
        "suggested_items": [],
        "order_id": None,
        "history_enabled": True,
        "debug_trace": [],
        "interrupt_context": {},
    }

if __name__ == "__main__":
    state = new_state()
    print("👋 Welcome to Smart Bistro!")
    while True:
        user = input("You: ").strip().lstrip("\ufeff")
        if user.lower() in {"quit", "exit"}:
            break
        state["last_user_message"] = user

        # Load menu
        menu_data = fetch_menu()
        items = menu_data["items"]
        state["menu_version"] = menu_data["menu_version"]
        state["currency"] = menu_data["currency"]
        active_currency = state["currency"]

        if user.lower() in {"show menu", "menu"}:
            reply = md_menu(items, active_currency)
        elif user.lower() in {"show cart", "cart"}:
            reply = md_cart(state["cart"], state["subtotal"], active_currency)
        elif user.lower() in {"checkout", "done", "confirm"}:
            if not state["cart"]:
                reply = "Your cart is empty. Add items first or type 'show menu'."
            else:
                placed = place_order(state["cart"], state["user_id"], currency=active_currency)
                save_order_history(
                    state["user_id"],
                    placed["order_id"],
                    state["cart"],
                    placed["total"],
                    placed["currency"],
                    datetime.utcnow().isoformat(),
                )
                reply = (
                    "✅ Order Confirmed!\n"
                    f"Order ID: {placed['order_id']}\n"
                    f"ETA: {placed['eta_minutes']} mins\n"
                    f"Total: {fmt_money(placed['total'], placed['currency'])}"
                )
                state["cart"] = []
                state["subtotal"] = 0.0
        # Parse user input
        else:
            parsed = parse_order_line(user, items)
            if parsed["parsed"]:
                ops = _ops_from_parsed(parsed["parsed"], items)
                res = update_cart(state["cart"], active_currency, ops)
                state["cart"] = res["cart"]
                state["subtotal"] = res["subtotal"]
                reply = md_cart(state["cart"], state["subtotal"], active_currency)
                if parsed["warnings"]:
                    reply = f"{_warning_reply(parsed['warnings'], items)}\n\n{reply}"
            elif parsed["warnings"]:
                reply = _warning_reply(parsed["warnings"], items)
            else:
                reply = "Try '2 Margherita and 1 Coke', 'remove coke', 'set coke to 2', 'show menu', 'show cart', or 'checkout'."

        print(phrase(SYSTEM_PROMPT, reply))
