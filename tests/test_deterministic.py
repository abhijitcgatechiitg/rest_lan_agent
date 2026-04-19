"""
tests/test_deterministic.py
============================
Deterministic regression test suite for Smart Bistro — user_tools/ layer.

PURPOSE
-------
These tests validate the invariant behavior of the four deterministic
components (fetch_menu, parse_order_line, update_cart, place_order).
They serve as a backward-compatibility guard: any future feature addition
that alters the behavior of these functions will cause a test to fail before
it reaches production. In a team workflow this suite is triggered automatically
on every pull request as a CI gate.

Tests have NO dependency on the LLM layer, network calls, or UI.
All 12 tests are fully reproducible and deterministic.

MENU REFERENCE (data/menu.json v2)
-----------------------------------
  WF01  Waffle Fries Medium   $2.49
  WF02  Waffle Fries Large    $2.99
  OM01  Classic Crispy Sandwich Meal  $8.99
  DK01  Sweet Tea Medium      $2.25
  DK02  Sweet Tea Large       $2.65
  (+ 19 more items across Original Meals, Kids Meals, Drinks)

RUN
---
  cd C:/Abhijit/01NobelResearchLab/rest_lan_agent
  source .venv/Scripts/activate
  pytest tests/test_deterministic.py -v
"""
import json
import re
import sys
from pathlib import Path

# ── path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from user_tools.fetch_menu import fetch_menu
from user_tools.parse_order_line import parse_order_line
from user_tools.update_cart import update_cart
from user_tools.place_order import place_order, save_order_history

HISTORY_PATH = ROOT / "data" / "order_history.json"


def _menu_items():
    """Load live menu items — called fresh per test to match production behavior."""
    return fetch_menu()["items"]


# ════════════════════════════════════════════════════════════════════════════
# D-01 / D-02 — fetch_menu
# ════════════════════════════════════════════════════════════════════════════

def test_D01_full_menu_load():
    """D-01: fetch_menu returns all 24 items with version, currency, and required schema."""
    result = fetch_menu()

    assert result["menu_version"] == "v2"
    assert result["currency"] == "USD"
    assert len(result["items"]) == 24

    required_fields = {
        "item_id", "name", "price", "category",
        "description", "calories", "options", "is_available"
    }
    for item in result["items"]:
        missing = required_fields - item.keys()
        assert not missing, f"Item '{item.get('item_id')}' missing fields: {missing}"


def test_D02_category_filter_drinks():
    """D-02: fetch_menu filtered to 'Drinks' returns exactly 11 items, all in that category."""
    result = fetch_menu(categories=["Drinks"])

    assert len(result["items"]) == 11
    assert all(it["category"] == "Drinks" for it in result["items"])


# ════════════════════════════════════════════════════════════════════════════
# D-03 through D-07 — parse_order_line
# ════════════════════════════════════════════════════════════════════════════

def test_D03_parse_single_item_numeric_qty():
    """D-03: Single item with numeric quantity is parsed to correct item_id, qty, and op."""
    result = parse_order_line("2 Waffle Fries Medium", _menu_items())

    assert result["warnings"] == []
    assert len(result["parsed"]) == 1
    item = result["parsed"][0]
    assert item["item_id"] == "WF01"
    assert item["qty"] == 2
    assert item["op"] == "add"


def test_D04_parse_single_item_word_qty():
    """D-04: Word-form quantity ('one') is normalized to integer 1."""
    result = parse_order_line("one Sweet Tea Medium", _menu_items())

    assert result["warnings"] == []
    assert len(result["parsed"]) == 1
    item = result["parsed"][0]
    assert item["item_id"] == "DK01"
    assert item["qty"] == 1
    assert item["op"] == "add"


def test_D05_parse_multi_item_compound():
    """D-05: 'and'-joined multi-item input yields two correctly parsed items."""
    result = parse_order_line(
        "2 Classic Crispy Sandwich Meal and 1 Sweet Tea Large", _menu_items()
    )

    assert result["warnings"] == []
    assert len(result["parsed"]) == 2
    by_id = {p["item_id"]: p["qty"] for p in result["parsed"]}
    assert by_id.get("OM01") == 2, "Expected OM01 qty=2"
    assert by_id.get("DK02") == 1, "Expected DK02 qty=1"


def test_D06_parse_remove_operation():
    """D-06: 'remove' keyword sets op=remove on the matched item."""
    result = parse_order_line("remove Waffle Fries Medium", _menu_items())

    assert result["warnings"] == []
    assert len(result["parsed"]) == 1
    item = result["parsed"][0]
    assert item["op"] == "remove"
    assert item["item_id"] == "WF01"


def test_D07_parse_unknown_item_rejected():
    """D-07: Unrecognized item name produces a warning and an empty parsed list."""
    result = parse_order_line("1 Cheeseburger Deluxe", _menu_items())

    assert result["parsed"] == []
    assert len(result["warnings"]) >= 1
    assert "Unrecognized" in result["warnings"][0]


# ════════════════════════════════════════════════════════════════════════════
# D-08 through D-10 — update_cart
# ════════════════════════════════════════════════════════════════════════════

def test_D08_cart_add_to_empty():
    """D-08: Adding to an empty cart creates one line; subtotal equals qty × unit_price."""
    ops = [{"op": "add", "item_id": "WF01", "name": "Waffle Fries Medium",
            "qty": 2, "unit_price": 2.49}]
    result = update_cart([], "USD", ops)

    assert len(result["cart"]) == 1
    assert result["cart"][0]["item_id"] == "WF01"
    assert result["cart"][0]["qty"] == 2
    assert round(result["subtotal"], 2) == 4.98   # 2 × $2.49
    assert result["currency"] == "USD"


def test_D09_cart_qty_accumulation_no_duplicate_lines():
    """D-09: Adding the same item twice accumulates quantity on one line, not two."""
    existing_cart = [
        {"item_id": "WF01", "name": "Waffle Fries Medium",
         "qty": 1, "unit_price": 2.49, "options": {}}
    ]
    ops = [{"op": "add", "item_id": "WF01", "name": "Waffle Fries Medium",
            "qty": 1, "unit_price": 2.49}]
    result = update_cart(existing_cart, "USD", ops)

    assert len(result["cart"]) == 1, "Cart must have one line, not a duplicate"
    assert result["cart"][0]["qty"] == 2
    assert round(result["subtotal"], 2) == 4.98   # 2 × $2.49


def test_D10_cart_set_qty_zero_removes_item():
    """D-10: set_qty with qty=0 removes the item entirely and zeroes the subtotal."""
    existing_cart = [
        {"item_id": "WF01", "name": "Waffle Fries Medium",
         "qty": 2, "unit_price": 2.49, "options": {}}
    ]
    ops = [{"op": "set_qty", "item_id": "WF01", "qty": 0}]
    result = update_cart(existing_cart, "USD", ops)

    assert result["cart"] == []
    assert result["subtotal"] == 0.0


# ════════════════════════════════════════════════════════════════════════════
# D-11 / D-12 — place_order
# ════════════════════════════════════════════════════════════════════════════

def test_D11_place_order_schema_and_total():
    """D-11: place_order returns correct total (to 2 dp), fixed ETA=30, and ORD- prefixed ID."""
    cart = [
        {"item_id": "WF01", "name": "Waffle Fries Medium",
         "qty": 2, "unit_price": 2.49, "options": {}},
        {"item_id": "DK01", "name": "Sweet Tea Medium",
         "qty": 1, "unit_price": 2.25, "options": {}},
    ]
    result = place_order(cart, "web-user")

    # 2 × $2.49 + 1 × $2.25 = $4.98 + $2.25 = $7.23
    assert round(result["total"], 2) == 7.23
    assert result["eta_minutes"] == 30
    assert result["currency"] == "USD"
    assert re.match(r"^ORD-\d+$", result["order_id"]), \
        f"Unexpected order_id format: '{result['order_id']}'"


def test_D12_save_order_history_persists_record():
    """D-12: save_order_history appends a retrievable record to order_history.json."""
    cart = [
        {"item_id": "WF01", "name": "Waffle Fries Medium",
         "qty": 1, "unit_price": 2.49, "options": {}}
    ]
    order = place_order(cart, "test-user")

    save_order_history(
        user_id="test-user",
        order_id=order["order_id"],
        cart=cart,
        total=order["total"],
        currency=order["currency"],
        timestamp="2026-04-19T00:00:00",
    )

    records = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    match = [r for r in records if r["order_id"] == order["order_id"]]

    assert len(match) == 1, "Expected exactly one matching order record"
    assert match[0]["user_id"] == "test-user"
    assert round(match[0]["total"], 2) == 2.49   # 1 × $2.49

    # ── cleanup: remove the test record so history stays clean ──────────────
    cleaned = [r for r in records if r["order_id"] != order["order_id"]]
    HISTORY_PATH.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
