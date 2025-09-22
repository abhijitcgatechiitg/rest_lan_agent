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

CURRENCY = os.getenv("CURRENCY", "INR")
SYSTEM_PROMPT = open("agent/system_prompt_restaurant.txt", encoding="utf-8").read()

def md_cart(cart, subtotal, currency):
    lines = ["\n🧺 Your Cart"]
    for it in cart:
        lines.append(f"- {it['name']} × {it['qty']} — ₹{it['qty'] * it['unit_price']}")
    lines.append(f"Subtotal: ₹{subtotal}")
    return "\n".join(lines)

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
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        state["last_user_message"] = user

        # Load menu
        menu_data = fetch_menu()
        items = menu_data["items"]
        state["menu_version"] = menu_data["menu_version"]
        state["currency"] = menu_data["currency"]

        # Parse user input
        parsed = parse_order_line(user, items)
        if parsed["parsed"]:
            ops = []
            for p in parsed["parsed"]:
                m = next((i for i in items if i["item_id"] == p["item_id"]), None)
                if m:
                    ops.append({
                        "op": "add",
                        "item_id": m["item_id"],
                        "qty": p["qty"],
                        "name": m["name"],
                        "unit_price": m["price"],
                        "options": {}
                    })
            res = update_cart(state["cart"], CURRENCY, ops)
            state["cart"] = res["cart"]
            state["subtotal"] = res["subtotal"]
            reply = md_cart(state["cart"], state["subtotal"], CURRENCY)
        elif user.lower() in {"show cart", "cart"}:
            reply = md_cart(state["cart"], state["subtotal"], CURRENCY)
        elif user.lower() in {"checkout", "done", "confirm"} and state["cart"]:
            placed = place_order(state["cart"], state["user_id"])
            save_order_history(state["user_id"], placed["order_id"], state["cart"], placed["total"], placed["currency"], datetime.utcnow().isoformat())
            reply = f"✅ Order Confirmed!\nOrder ID: {placed['order_id']}\nETA: {placed['eta_minutes']} mins\nTotal: ₹{placed['total']}"
            state["cart"] = []
            state["subtotal"] = 0.0
        else:
            reply = "Sorry, I didn't understand. Try '2 Margherita and 1 Coke' or 'show cart' or 'checkout'."

        print(phrase(SYSTEM_PROMPT, reply))