# Smart Bistro — Requirements

## Status Legend
- ✅ Done
- 🔄 In Progress
- 📋 Planned

---

## R1 — Smart Bistro Menu v2 ✅ (2026-04-18)
Realistic menu inspired by Chick-fil-A (original names, no copyright).
Sections: Original Meals, Kids Meals, Waffle Fries, Drinks.
Stored in `data/menu.json` (version v2).
Item fields: item_id, name, description, price, calories, options, is_available.

Items:
- **Original Meals** (OM01–OM08): Classic/Fiery Crispy Sandwiches, Golden Tenders 8/12pc, Crispy Strips 3/4pc — all include Waffle Fries + Drink
- **Kids Meals** (KM01–KM03): Crispy Bites, Grilled Bites, Mini Strips — includes small side + drink
- **Waffle Fries** (WF01–WF02): Medium ($2.49) / Large ($2.99)
- **Drinks** (DK01–DK11): Sweet Tea M/L, Fresh Lemonade M/L, Sunny Blend M/L, Fountain Drink M/L, Cold Brew Coffee, Orange Juice, Bottled Water

---

## R2 — Streamlit Two-Column Chat & Order UI ✅ (2026-04-18)
On launch, show:
- Greeting: "Hi! Welcome to Smart Bistro — I can help you in ordering food from the menu shown to the left."
- Left column (40%): Full menu with category headers, item descriptions, prices, calories
- Right column (60%): Chat history + Cart expander + Chat input
- Cart expander shows live cart with "Clear Cart" and "Place Order" buttons
- Chat history maintained across the session (all messages visible)
- `phrase()` LLM layer applied to all responses when USE_LLM=true

---

## R3 — Deterministic Test Suite 📋
Build `tests/` directory with pytest.

### Test files
- `tests/test_parse_order_line.py` — unit tests for NLU parsing
  - Standard order: "2 Classic Crispy Sandwich Meal and 1 Sweet Tea Large"
  - Remove: "remove Sweet Tea Large"
  - Set qty: "set Waffle Fries Medium to 3"
  - Unknown item: "1 Unicorn Burger" → warning generated
  - Edge cases: empty input, numbers as words ("two"), partial names

- `tests/test_update_cart.py` — unit tests for cart operations
  - Add to empty cart
  - Add duplicate item (qty accumulates)
  - Remove existing item
  - Set qty to 0 (removes item)
  - Subtotal calculation correctness

- `tests/test_fetch_menu.py` — unit tests for menu loading
  - All 4 categories load
  - Total item count = 24 (8+3+2+11)
  - Currency = USD
  - Version = v2

- `tests/test_integration.py` — end-to-end order flow
  - Full flow: parse → update_cart → place_order → save_order_history

### Metrics to collect (for paper)
- Pass rate % per test file
- Specific failure cases and error types
- Run time per suite

---

## R4 — LLM-as-Judge Validation Framework 📋
Build `validation/` directory.

### Files
- `validation/golden_sets.json` — predefined (input, expected_output) scenarios
- `validation/llm_judge.py` — invokes agent N=3 times per scenario, calls judge LLM
- `validation/run_validation.py` — orchestrates all scenarios, outputs results JSON

### Golden Set Scenarios (draft)
1. "Show me the menu" → full menu listing
2. "1 Classic Crispy Sandwich Meal" → cart with OM01, subtotal $8.99
3. "2 Waffle Fries Medium" → cart updated, qty=2, subtotal $4.98
4. "remove Waffle Fries Medium" → Waffle Fries removed
5. "checkout" (with items in cart) → order confirmation with Order ID, ETA, total
6. "1 Crispy Bites Kids Meal and 1 Orange Juice" → cart with KM01 + DK10
7. "set Sweet Tea Medium to 3" → qty updated correctly
8. "xyz unknown item" → graceful warning, no cart change

### Judge LLM scoring (per scenario, per run)
- **Accuracy** (0–10): Is the factual content correct (prices, item names, order ID)?
- **Completeness** (0–10): Does the response cover all required elements?
- **Consistency** (0–10): Is this run consistent with the other N runs?

Pass threshold: TBD during initial experiments (target ≥ 7.0 on all dimensions)

### Metrics to collect (for paper)
- Mean score per dimension per scenario
- Inter-run variance (consistency measure)
- Overall pass/fail rate
- Human vs. LLM judge agreement rate (human review of 20% sample)

---

## R5 — Research Paper Camera-Ready Updates 📋
Based on Review 1 feedback (received 2026-04-15):

1. **Rename title** — remove "Empirical Study"; use "A Framework for Version-Control and
   Dual-Validation Workflows for Enterprise AI Systems" or similar
2. **Add Section V: Experimental Results** — report metrics from R3 and R4
3. **Expand LLM-as-Judge section** — add: judge model used, prompt templates, threshold
   determination methodology, inter-run consistency analysis
4. **Condense Section II** — reduce basic Git/PR/OOP background; assume technical audience

---

## Notes
- All experiment outputs saved to `validation_results/` (gitignored)
- Paper deadline: per WOCC 2026 camera-ready instructions (check EDAS)
