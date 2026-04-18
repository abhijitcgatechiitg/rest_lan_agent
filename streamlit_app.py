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
SYSTEM_PROMPT = open("agent/system_prompt_restaurant.txt", encoding="utf-8").read()

CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£"}

GREETING = (
    "Hi! Welcome to **Smart Bistro** 🍗\n\n"
    "I can help you in ordering food from the menu shown to the left.\n\n"
    "**Try saying:**\n"
    "- `1 Classic Crispy Sandwich Meal`\n"
    "- `2 Waffle Fries Medium and 1 Sweet Tea Large`\n"
    "- `1 Crispy Bites Kids Meal`\n"
    "- `show cart` — view your current order\n"
    "- `checkout` — place your order\n\n"
    "What can I get for you today?"
)


def fmt_money(amount: float, currency: str) -> str:
    sym = CURRENCY_SYMBOLS.get((currency or "").upper(), "$")
    return f"{sym}{amount:.2f}"


def new_state() -> AgentState:
    return {
        "user_id": "web-user",
        "stage": "greet",
        "cart": [],
        "subtotal": 0.0,
        "currency": "USD",
        "menu_version": "",
        "last_user_message": "",
        "last_ai_message": "",
        "suggested_items": [],
        "order_id": None,
        "history_enabled": True,
        "debug_trace": [],
        "interrupt_context": {},
    }


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
    sample = ", ".join(f"`{it['name']}`" for it in items[:3])
    joined = "\n".join(f"- {w}" for w in warnings)
    return (
        f"⚠️ I couldn't find some items:\n{joined}\n\n"
        f"Check the menu on the left, or try items like: {sample}"
    )


def _cart_md(cart, subtotal, currency):
    lines = ["🧺 **Cart Updated!**"]
    for it in cart:
        lines.append(f"- **{it['name']}** × {it['qty']} — {fmt_money(it['qty'] * it['unit_price'], currency)}")
    lines.append(f"\n**Subtotal: {fmt_money(subtotal, currency)}**")
    lines.append("\nType `checkout` when ready to place your order!")
    return "\n".join(lines)


def render_menu(items, currency):
    cats: dict = {}
    for it in items:
        cats.setdefault(it.get("category", "Other"), []).append(it)

    cat_icons = {
        "Original Meals": "🍗",
        "Kids Meals": "🧒",
        "Waffle Fries": "🍟",
        "Drinks": "🥤",
    }

    for cat_name, cat_items in cats.items():
        icon = cat_icons.get(cat_name, "🍽️")
        st.markdown(f"#### {icon} {cat_name}")
        cat_desc = cat_items[0].get("category_description", "")
        if cat_desc:
            st.caption(cat_desc)

        cards_html = ""
        for it in cat_items:
            cal = it.get("calories")
            cal_html = f'<span class="item-cal">· {cal} cal</span>' if cal else ""
            desc = it.get("description", "")
            options = it.get("options", {})
            opts_html = ""
            if options:
                parts = [f"{k}: {', '.join(v)}" for k, v in options.items()]
                opts_html = f'<div class="item-opts">Options — {"; ".join(parts)}</div>'

            cards_html += f"""
<div class="menu-item">
  <div class="item-row">
    <span class="item-name">{it['name']}</span>
    <span class="item-price">{fmt_money(float(it['price']), currency)}</span>
  </div>
  <div class="item-row" style="margin-top:1px">
    <span class="item-desc">{desc}</span>
    {cal_html}
  </div>
  {opts_html}
</div>"""

        st.markdown(cards_html, unsafe_allow_html=True)
        st.markdown("---")


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Smart Bistro", page_icon="🍗", layout="wide")

st.markdown("""
<style>
/* ── Global background & typography ─────────────────────── */
.stApp {
    background: linear-gradient(150deg, #e0f7f4 0%, #e8f8f5 45%, #f0fffe 100%);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}
[data-testid="stMainBlockContainer"] { padding-top: 1rem; }

/* ── Hero banner ─────────────────────────────────────────── */
.hero-banner {
    background: linear-gradient(135deg, #00695c 0%, #00897b 55%, #26a69a 100%);
    padding: 1.4rem 2rem 1.3rem;
    border-radius: 18px;
    margin-bottom: 1.2rem;
    box-shadow: 0 6px 24px rgba(0,105,92,0.25);
}
.hero-banner h1 {
    color: #ffffff !important;
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px;
    margin: 0 0 0.2rem 0;
}
.hero-banner p {
    color: rgba(255,255,255,0.88);
    font-size: 0.95rem;
    margin: 0;
}

/* ── Panel cards (columns) ───────────────────────────────── */
[data-testid="stColumn"] > div > div {
    background: rgba(255,255,255,0.78);
    border: 1.5px solid #b2dfdb;
    border-radius: 16px;
    padding: 1.1rem 1.3rem !important;
    box-shadow: 0 3px 14px rgba(0,137,123,0.09);
}

/* ── Section subheaders ──────────────────────────────────── */
h2, h3 {
    color: #00695c !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
}

/* ── Category headers (h4) ───────────────────────────────── */
h4 {
    color: #00796b !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 1.1rem 0 0.2rem 0 !important;
    padding-bottom: 4px;
    border-bottom: 2px solid #80cbc4;
}

/* ── Category subtitle ───────────────────────────────────── */
.stCaption { color: #607d8b !important; font-size: 0.82rem !important; }

/* ── Menu item cards ─────────────────────────────────────── */
.menu-item {
    display: flex;
    flex-direction: column;
    padding: 7px 10px 7px 12px;
    margin: 4px 0;
    border-radius: 9px;
    background: rgba(255,255,255,0.9);
    border-left: 3px solid #4db6ac;
    transition: background 0.18s;
}
.menu-item:hover { background: rgba(178,223,219,0.35); }
.item-row { display: flex; justify-content: space-between; align-items: center; }
.item-name { font-weight: 600; font-size: 0.93rem; color: #1c3d35; }
.item-price {
    font-weight: 700; font-size: 0.88rem; color: #00695c;
    background: #e0f2f1; padding: 2px 9px; border-radius: 20px;
    white-space: nowrap; margin-left: 8px;
}
.item-cal { font-size: 0.78rem; color: #90a4ae; margin-left: 5px; }
.item-desc { font-size: 0.80rem; color: #607d8b; margin-top: 2px; line-height: 1.35; }
.item-opts { font-size: 0.75rem; color: #80cbc4; margin-top: 2px; }

/* ── Horizontal rule ─────────────────────────────────────── */
hr { border-color: #b2dfdb !important; margin: 0.7rem 0 !important; }

/* ── Chat message bubbles ────────────────────────────────── */
[data-testid="stChatMessage"] {
    padding: 0.55rem 0.5rem !important;
    border-radius: 12px !important;
    margin-bottom: 0.25rem !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: rgba(224,242,241,0.5) !important;
}

/* ── Chat input bar ──────────────────────────────────────── */
[data-testid="stChatInputContainer"] {
    border: 2px solid #4db6ac !important;
    border-radius: 12px !important;
    background: #ffffff !important;
}
[data-testid="stChatInputContainer"]:focus-within {
    border-color: #00897b !important;
    box-shadow: 0 0 0 3px rgba(0,137,123,0.12) !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00897b, #00695c) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.42rem 1rem !important;
    transition: all 0.18s ease !important;
    box-shadow: 0 2px 6px rgba(0,105,92,0.2) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00695c, #004d40) !important;
    box-shadow: 0 5px 14px rgba(0,105,92,0.32) !important;
    transform: translateY(-1px) !important;
}

/* ── Cart expander ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1.5px solid #4db6ac !important;
    border-radius: 12px !important;
    background: rgba(224,242,241,0.3) !important;
    margin-top: 0.6rem !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #00695c !important;
    font-size: 0.93rem !important;
}

/* ── Inline code (prices / commands) ────────────────────── */
code {
    background: #e0f2f1 !important;
    color: #00695c !important;
    border-radius: 5px !important;
    padding: 1px 6px !important;
    font-size: 0.88em !important;
}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #e0f7f4; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #80cbc4; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4db6ac; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <h1>🍗 Smart Bistro</h1>
  <p>Fresh, hand-breaded, made for you &nbsp;·&nbsp; Open Daily 10:30 AM – 10:00 PM</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = new_state()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]

# ── Load menu ─────────────────────────────────────────────────────────────────
menu_data = fetch_menu()
items = menu_data["items"]
active_currency = menu_data["currency"]
st.session_state.state["currency"] = active_currency
st.session_state.state["menu_version"] = menu_data["menu_version"]

# ── Two-column layout ─────────────────────────────────────────────────────────
col_menu, col_chat = st.columns([4, 6], gap="large")

with col_menu:
    st.markdown("### 📋 Our Menu")
    render_menu(items, active_currency)

with col_chat:
    st.markdown("### 💬 Chat & Order")

    # Chat history (scrollable)
    with st.container(height=420):
        for msg in st.session_state.messages:
            avatar = "🍗" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # Cart summary
    state = st.session_state.state
    cart_label = f"🧺 Your Cart — {len(state['cart'])} item(s)"
    with st.expander(cart_label, expanded=bool(state["cart"])):
        if state["cart"]:
            for it in state["cart"]:
                st.markdown(
                    f"- **{it['name']}** × {it['qty']} — "
                    f"{fmt_money(it['qty'] * it['unit_price'], active_currency)}"
                )
            st.markdown(f"**Subtotal: {fmt_money(state['subtotal'], active_currency)}**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    state["cart"] = []
                    state["subtotal"] = 0.0
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Cart cleared! Ready to start fresh — what can I get for you?"
                    })
                    st.rerun()
            with c2:
                if st.button("✅ Place Order", use_container_width=True):
                    placed = place_order(state["cart"], state["user_id"], currency=active_currency)
                    save_order_history(
                        state["user_id"], placed["order_id"], state["cart"],
                        placed["total"], placed["currency"], datetime.utcnow().isoformat(),
                    )
                    reply = (
                        f"✅ **Order Confirmed!**\n\n"
                        f"**Order ID:** `{placed['order_id']}`\n"
                        f"**ETA:** {placed['eta_minutes']} mins\n"
                        f"**Total:** {fmt_money(placed['total'], placed['currency'])}\n\n"
                        "Thank you for choosing Smart Bistro! 🍗 Enjoy your meal!"
                    )
                    state["cart"] = []
                    state["subtotal"] = 0.0
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.rerun()
        else:
            st.markdown("*Your cart is empty — start ordering from the menu!*")

    # Chat input
    user_input = st.chat_input("What would you like to order?")
    if user_input:
        user_input = user_input.strip().lstrip("\ufeff")
        state["last_user_message"] = user_input
        st.session_state.messages.append({"role": "user", "content": user_input})

        cmd = user_input.lower()

        if cmd in {"show menu", "menu"}:
            reply = "The full menu is displayed on the left! Just tell me what you'd like."

        elif cmd in {"show cart", "cart"}:
            if state["cart"]:
                lines = ["🧺 **Your Cart**"]
                for it in state["cart"]:
                    lines.append(
                        f"- **{it['name']}** × {it['qty']} — "
                        f"{fmt_money(it['qty'] * it['unit_price'], active_currency)}"
                    )
                lines.append(f"\n**Subtotal: {fmt_money(state['subtotal'], active_currency)}**")
                lines.append("\nType `checkout` to place your order!")
                reply = "\n".join(lines)
            else:
                reply = "Your cart is empty. Check the menu on the left and add some items!"

        elif cmd in {"checkout", "done", "confirm", "place order"}:
            if state["cart"]:
                placed = place_order(state["cart"], state["user_id"], currency=active_currency)
                save_order_history(
                    state["user_id"], placed["order_id"], state["cart"],
                    placed["total"], placed["currency"], datetime.utcnow().isoformat(),
                )
                reply = (
                    f"✅ **Order Confirmed!**\n\n"
                    f"**Order ID:** `{placed['order_id']}`\n"
                    f"**ETA:** {placed['eta_minutes']} mins\n"
                    f"**Total:** {fmt_money(placed['total'], placed['currency'])}\n\n"
                    "Thank you for choosing Smart Bistro! 🍗 Enjoy your meal!"
                )
                state["cart"] = []
                state["subtotal"] = 0.0
            else:
                reply = "Your cart is empty. Add some items from the menu first!"

        else:
            parsed = parse_order_line(user_input, items)
            if parsed["parsed"]:
                ops = _ops_from_parsed(parsed["parsed"], items)
                res = update_cart(state["cart"], active_currency, ops)
                state["cart"] = res["cart"]
                state["subtotal"] = res["subtotal"]
                reply = _cart_md(state["cart"], state["subtotal"], active_currency)
                if parsed["warnings"]:
                    reply = _warning_reply(parsed["warnings"], items) + "\n\n" + reply
            elif parsed["warnings"]:
                reply = _warning_reply(parsed["warnings"], items)
            else:
                reply = (
                    "I didn't quite catch that. Try ordering by item name, for example:\n"
                    "- `1 Classic Crispy Sandwich Meal`\n"
                    "- `2 Waffle Fries Medium`\n"
                    "- `remove Sweet Tea Medium`\n\n"
                    "Or type `show cart` or `checkout`."
                )

        final_reply = phrase(SYSTEM_PROMPT, reply)
        st.session_state.messages.append({"role": "assistant", "content": final_reply})
        st.rerun()
