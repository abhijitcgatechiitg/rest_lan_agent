"""
LangChain @tool wrappers for Smart Bistro user tools.

DESIGN NOTE
-----------
All underlying logic lives in user_tools/ and is NEVER modified here.
These wrappers serve two purposes:
  1. Expose selected tools to Claude via bind_tools() for LLM-driven decisions.
  2. Provide a consistent typed interface for graph nodes that call tools
     programmatically via .invoke({...}).

LLM-callable (simple inputs Claude can generate):
  fetch_menu_tool   — no required args; Claude calls this to show the menu
  parse_order_tool  — just the raw user text; Claude calls this to parse orders

Node-callable (complex inputs; nodes call these programmatically):
  update_cart_tool  — needs current cart + ops; nodes assemble these from state
  place_order_tool  — needs full cart; called only from order_node
  save_history_tool — called immediately after place_order_tool
"""

from typing import List, Optional
from langchain_core.tools import tool

from user_tools.fetch_menu import fetch_menu
from user_tools.parse_order_line import parse_order_line
from user_tools.update_cart import update_cart
from user_tools.place_order import place_order, save_order_history


@tool
def fetch_menu_tool(categories: Optional[List[str]] = None) -> dict:
    """
    Fetch the Smart Bistro restaurant menu.

    Optionally filter by category names:
    'Original Meals', 'Kids Meals', 'Waffle Fries', 'Drinks'.

    Returns menu_version, currency, and items with
    item_id, name, price, description, calories, and options.
    """
    return fetch_menu(categories)


@tool
def parse_order_tool(text: str) -> dict:
    """
    Parse a natural language food order into structured cart operations.

    Input is the raw user utterance, e.g.:
    '2 Classic Crispy Sandwich Meal and 1 Sweet Tea Large'
    'remove Waffle Fries Medium'
    'set lemonade to 3'

    Returns:
      parsed   — list of {op, item_id, qty, options}
      warnings — list of unrecognized item strings
    """
    menu_data = fetch_menu()
    return parse_order_line(text, menu_data["items"])


@tool
def update_cart_tool(cart: List[dict], currency: str, ops: List[dict]) -> dict:
    """
    Apply add / remove / set_qty operations to the current cart.

    Each op: {op, item_id, qty, name, unit_price, options}
    Returns updated cart list and subtotal.
    """
    return update_cart(cart, currency, ops)


@tool
def place_order_tool(cart: List[dict], user_id: str, currency: str) -> dict:
    """
    Place a confirmed order from the current cart.

    Returns order_id, eta_minutes, total, currency.
    """
    return place_order(cart, user_id, currency=currency)


@tool
def save_history_tool(
    user_id: str,
    order_id: str,
    cart: List[dict],
    total: float,
    currency: str,
    timestamp: str,
) -> dict:
    """
    Persist order details to order history after a successful placement.
    Returns {ok: true} on success.
    """
    return save_order_history(user_id, order_id, cart, total, currency, timestamp)


# ── Tool sets ─────────────────────────────────────────────────────────────────

# Bound to Claude in chat_node — simple inputs only.
LLM_TOOLS = [fetch_menu_tool, parse_order_tool]

# Available to all graph nodes for programmatic calls.
ALL_TOOLS = [
    fetch_menu_tool,
    parse_order_tool,
    update_cart_tool,
    place_order_tool,
    save_history_tool,
]
