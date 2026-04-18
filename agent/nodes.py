"""
LangGraph node functions and intent router for Smart Bistro.

Each node:
  - Accepts AgentState, returns a dict of fields to update (partial update).
  - 'messages' uses the add_messages reducer — it appends, never overwrites.

route_intent:
  - Not a node; used as a LangGraph conditional edge function.
  - Returns the name of the next node as a string.
"""

import os
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, SystemMessage

from agent.state import AgentState
from agent.tools import (
    fetch_menu_tool,
    parse_order_tool,
    update_cart_tool,
    place_order_tool,
    save_history_tool,
    LLM_TOOLS,
)
from user_tools.fetch_menu import fetch_menu
from user_tools.parse_order_line import parse_order_line

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt_restaurant.txt").read_text(encoding="utf-8")
_CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£"}
_CAT_ICONS = {"Original Meals": "🍗", "Kids Meals": "🧒", "Waffle Fries": "🍟", "Drinks": "🥤"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(amount: float, currency: str) -> str:
    sym = _CURRENCY_SYMBOLS.get((currency or "").upper(), "$")
    return f"{sym}{amount:.2f}"


def _build_llm():
    """Returns a ChatAnthropic instance, or None when USE_LLM=false."""
    if os.getenv("USE_LLM", "false").lower() != "true":
        return None
    model = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
    return ChatAnthropic(model=model, temperature=0.3)


# ── Intent Router (conditional edge — not a state node) ───────────────────────

def route_intent(state: AgentState) -> str:
    """
    Maps current state → next node name.
    Rule-based first (fast, deterministic); parse-attempt fallback.
    """
    msg = (state.get("last_user_message") or "").strip().lower()
    stage = state.get("stage", "greet")

    # ── Awaiting yes/no after checkout prompt ─────────────────────────────────
    if stage == "awaiting_confirmation":
        if msg in {"yes", "y", "confirm", "ok", "sure", "place order"}:
            return "order_node"
        if msg in {"no", "n", "cancel", "nevermind", "stop"}:
            return "confirm_node"   # show cart again, no confirmation prompt
        return "chat_node"          # ambiguous — Claude clarifies

    # ── Explicit commands ─────────────────────────────────────────────────────
    if msg in {"show menu", "menu"}:
        return "menu_node"
    if msg in {"show cart", "cart"}:
        return "confirm_node"
    if msg in {"checkout", "done", "confirm", "place order"}:
        return "confirm_node"       # shows cart + asks for confirmation

    # ── Rule-based parse attempt ──────────────────────────────────────────────
    raw = state.get("last_user_message", "")
    result = parse_order_line(raw, fetch_menu()["items"])
    if result["parsed"]:
        return "cart_node"

    # ── Everything else → Claude ──────────────────────────────────────────────
    return "chat_node"


# ── Nodes ─────────────────────────────────────────────────────────────────────

def menu_node(state: AgentState) -> dict:
    """Fetch and format the full menu as a chat reply."""
    menu_data = fetch_menu_tool.invoke({})
    items = menu_data["items"]
    currency = menu_data["currency"]

    cats: dict = {}
    for it in items:
        cats.setdefault(it["category"], []).append(it)

    lines = ["📖 **Smart Bistro Menu**\n"]
    for cat_name, cat_items in cats.items():
        icon = _CAT_ICONS.get(cat_name, "🍽️")
        lines.append(f"**{icon} {cat_name}**")
        for it in cat_items:
            cal = f"  _{it['calories']} cal_" if it.get("calories") else ""
            lines.append(f"  • {it['name']} — {_fmt(float(it['price']), currency)}{cal}")
        lines.append("")
    lines.append("What would you like to order?")
    reply = "\n".join(lines)

    return {
        "last_ai_message": reply,
        "messages": [AIMessage(content=reply)],
        "stage": "menu",
        "menu_version": menu_data["menu_version"],
        "currency": currency,
    }


def cart_node(state: AgentState) -> dict:
    """Parse order text, enrich ops with menu prices, update cart."""
    raw = state.get("last_user_message", "")
    currency = state.get("currency", "USD")

    parsed_result = parse_order_tool.invoke({"text": raw})
    parsed = parsed_result["parsed"]
    warnings = parsed_result["warnings"]

    if not parsed:
        if warnings:
            joined = "\n".join(f"- {w}" for w in warnings)
            reply = f"⚠️ I couldn't find those items:\n{joined}\n\nCheck the menu or try the full item name."
        else:
            reply = "I didn't catch that order. Try `1 Classic Crispy Sandwich Meal` or check the menu."
        return {"last_ai_message": reply, "messages": [AIMessage(content=reply)]}

    # Enrich parsed items with live prices from menu
    items = fetch_menu()["items"]
    ops = []
    for p in parsed:
        m = next((i for i in items if i["item_id"] == p["item_id"]), None)
        if m:
            ops.append({
                "op": p.get("op", "add"),
                "item_id": m["item_id"],
                "qty": p.get("qty", 1),
                "name": m["name"],
                "unit_price": m["price"],
                "options": p.get("options", {}),
            })

    result = update_cart_tool.invoke({
        "cart": state.get("cart", []),
        "currency": currency,
        "ops": ops,
    })
    new_cart = result["cart"]
    new_subtotal = result["subtotal"]

    lines = ["🧺 **Cart Updated!**"]
    for it in new_cart:
        lines.append(f"- **{it['name']}** × {it['qty']} — {_fmt(it['qty'] * it['unit_price'], currency)}")
    lines.append(f"\n**Subtotal: {_fmt(new_subtotal, currency)}**")
    lines.append("\nType `checkout` when ready!")

    if warnings:
        joined = "\n".join(f"- {w}" for w in warnings)
        reply = f"⚠️ Some items not found:\n{joined}\n\n" + "\n".join(lines)
    else:
        reply = "\n".join(lines)

    return {
        "cart": new_cart,
        "subtotal": new_subtotal,
        "last_ai_message": reply,
        "messages": [AIMessage(content=reply)],
        "stage": "cart",
    }


def confirm_node(state: AgentState) -> dict:
    """Show cart summary. If arriving from a checkout command, ask for yes/no."""
    cart = state.get("cart", [])
    subtotal = state.get("subtotal", 0.0)
    currency = state.get("currency", "USD")

    if not cart:
        reply = "Your cart is empty! Add some items from the menu first."
        return {
            "last_ai_message": reply,
            "messages": [AIMessage(content=reply)],
            "stage": "cart",
        }

    lines = ["🧺 **Your Cart**"]
    for it in cart:
        lines.append(f"- **{it['name']}** × {it['qty']} — {_fmt(it['qty'] * it['unit_price'], currency)}")
    lines.append(f"\n**Total: {_fmt(subtotal, currency)}**")

    cmd = (state.get("last_user_message") or "").strip().lower()
    if cmd in {"checkout", "done", "confirm", "place order"}:
        lines.append("\n✅ Ready to place your order? Type **yes** to confirm or **no** to keep editing.")
        new_stage = "awaiting_confirmation"
    else:
        lines.append("\nType `checkout` to place your order, or keep adding items!")
        new_stage = "confirm"

    reply = "\n".join(lines)
    return {
        "last_ai_message": reply,
        "messages": [AIMessage(content=reply)],
        "stage": new_stage,
    }


def order_node(state: AgentState) -> dict:
    """Place the confirmed order and persist to history."""
    cart = state.get("cart", [])
    user_id = state.get("user_id", "web-user")
    currency = state.get("currency", "USD")

    if not cart:
        reply = "Your cart is empty — nothing to place!"
        return {"last_ai_message": reply, "messages": [AIMessage(content=reply)]}

    placed = place_order_tool.invoke({
        "cart": cart, "user_id": user_id, "currency": currency,
    })
    save_history_tool.invoke({
        "user_id": user_id,
        "order_id": placed["order_id"],
        "cart": cart,
        "total": placed["total"],
        "currency": placed["currency"],
        "timestamp": datetime.utcnow().isoformat(),
    })

    reply = (
        f"✅ **Order Confirmed!**\n\n"
        f"**Order ID:** `{placed['order_id']}`\n"
        f"**ETA:** {placed['eta_minutes']} mins\n"
        f"**Total:** {_fmt(placed['total'], placed['currency'])}\n\n"
        "Thank you for choosing Smart Bistro! 🍗"
    )
    return {
        "cart": [],
        "subtotal": 0.0,
        "order_id": placed["order_id"],
        "last_ai_message": reply,
        "messages": [AIMessage(content=reply)],
        "stage": "placed",
    }


def chat_node(state: AgentState) -> dict:
    """
    Claude handles off-topic queries, FAQ, and anything the router didn't classify.
    Passes full conversation history so Claude has context across turns.
    Gracefully degrades to a hint when USE_LLM=false.
    """
    llm = _build_llm()
    if llm is None:
        reply = (
            "I'm running in rule-based mode. Try:\n"
            "- `1 Classic Crispy Sandwich Meal`\n"
            "- `show menu` · `show cart` · `checkout`"
        )
        return {"last_ai_message": reply, "messages": [AIMessage(content=reply)]}

    history = list(state.get("messages", []))
    response = llm.invoke([SystemMessage(content=_SYSTEM_PROMPT)] + history)
    reply = response.content if hasattr(response, "content") else str(response)

    return {
        "last_ai_message": reply,
        "messages": [AIMessage(content=reply)],
    }
