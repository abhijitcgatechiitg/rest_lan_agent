import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime
from agent.state import AgentState
from agent.assistant import phrase
from user_tools.fetch_menu import fetch_menu
from user_tools.parse_order_line import parse_order_line
from user_tools.update_cart import update_cart
from user_tools.place_order import place_order, save_order_history

load_dotenv()
CURRENCY = os.getenv("CURRENCY", "INR")
SYSTEM_PROMPT = open("agent/system_prompt_restaurant.txt", encoding="utf-8").read()

def md_cart(cart, subtotal, currency):
    lines = ["\n🧺 **Your Cart**"]
    for it in cart:
        lines.append(f"- {it['name']} × {it['qty']} — ₹{it['qty'] * it['unit_price']}")
    lines.append(f"**Subtotal: ₹{subtotal}**")
    return "\n".join(lines)

def new_state() -> AgentState:
    return {
        "user_id": "web-user",
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

st.set_page_config(page_title="Smart Bistro 🍽️", page_icon="🍕", layout="centered")
st.title("Smart Bistro 🍽️")
st.markdown("Talk to your food assistant. Try: `2 coke and 1 garlic bread`, `show cart`, or `checkout`.")

if "state" not in st.session_state:
    st.session_state.state = new_state()

user_input = st.chat_input("What's your order?")
if user_input:
    state = st.session_state.state
    state["last_user_message"] = user_input

    menu_data = fetch_menu()
    items = menu_data["items"]
    state["menu_version"] = menu_data["menu_version"]
    state["currency"] = menu_data["currency"]

    parsed = parse_order_line(user_input, items)
    if parsed["parsed"]:
        ops = []
        for p in parsed["parsed"]:
            m = next((i for i in items if i["item_id"] == p["item_id"]), None)
            if m:
                ops.append({
                    "op": "add", "item_id": m["item_id"], "qty": p["qty"],
                    "name": m["name"], "unit_price": m["price"], "options": {}
                })
        res = update_cart(state["cart"], CURRENCY, ops)
        state["cart"] = res["cart"]
        state["subtotal"] = res["subtotal"]
        reply = md_cart(state["cart"], state["subtotal"], CURRENCY)
    elif user_input.lower() in {"show cart", "cart"}:
        reply = md_cart(state["cart"], state["subtotal"], CURRENCY)
    elif user_input.lower() in {"checkout", "done", "confirm"} and state["cart"]:
        placed = place_order(state["cart"], state["user_id"])
        save_order_history(state["user_id"], placed["order_id"], state["cart"], placed["total"], placed["currency"], datetime.utcnow().isoformat())
        reply = f"✅ Order Confirmed!\n\n**Order ID**: {placed['order_id']}\n**ETA**: {placed['eta_minutes']} mins\n**Total**: ₹{placed['total']}"
        state["cart"] = []
        state["subtotal"] = 0.0
        st.success(f"Order {placed['order_id']} placed successfully!")
    else:
        reply = "Try something like `2 coke and 1 garlic bread`, `show cart`, or `checkout`."

    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        st.markdown(phrase(SYSTEM_PROMPT, reply))