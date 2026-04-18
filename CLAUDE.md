# Smart Bistro — CLAUDE.md

## What This Project Is
A LangChain + Anthropic restaurant ordering agent ("Smart Bistro") serving as the empirical
test bed for an IEEE WOCC 2026 research paper on dual-validation workflows for enterprise AI
systems (paper #1571269278, accepted April 2026).

**Every feature serves two goals:**
1. A realistic, working demo app
2. Measurable, collectable metrics for the research paper

---

## How to Run

```bash
cd C:/Abhijit/01NobelResearchLab/rest_lan_agent
source .venv/Scripts/activate        # Windows
streamlit run streamlit_app.py       # Web UI
python main.py                       # CLI
```

---

## Architecture

| File | Role |
|---|---|
| `streamlit_app.py` | Web UI — two-column layout (menu left, chat right) |
| `main.py` | CLI entry point |
| `agent/assistant.py` | `phrase()` — optionally routes responses through Claude |
| `agent/state.py` | `AgentState` TypedDict — do not rename fields |
| `user_tools/parse_order_line.py` | **Rule-based NLU — intentionally no LLM** |
| `user_tools/update_cart.py` | Stateless cart operations |
| `user_tools/fetch_menu.py` | Reads `data/menu.json` |
| `user_tools/place_order.py` | Generates order ID, saves order history |
| `data/menu.json` | Smart Bistro menu v2 (Original Meals, Kids Meals, Waffle Fries, Drinks) |

---

## Key Constraints

- `parse_order_line.py` MUST stay rule-based (no LLM). It is the **deterministic validation
  subject** in the research paper — its predictability is the point.
- `phrase()` in `assistant.py` is the **LLM layer**. Keep these two concerns strictly separate.
- Do not change `menu.json` schema — item_id, name, price, options, is_available, category,
  description, calories are all required fields for v2.
- Experiment outputs go in `validation_results/` (gitignored — never commit).
- `.env` has the API key — never commit it (already gitignored).

---

## Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=...            # Claude API key
USE_LLM=true                     # Set false to skip Claude response phrasing
MODEL_NAME=claude-3-haiku-20240307
CURRENCY=USD
```

---

## Menu Structure (v2)

| Category | Item IDs | Description |
|---|---|---|
| Original Meals | OM01–OM08 | Meal = Waffle Fries + Drink included |
| Kids Meals | KM01–KM03 | Small side + drink included |
| Waffle Fries | WF01–WF02 | Medium / Large |
| Drinks | DK01–DK11 | Tea, Lemonade, Blend, Fountain, Coffee, OJ, Water |

---

## Planned Directories (Research Experiments)

```
tests/               # pytest deterministic test suite (to be built)
validation_results/  # LLM-as-judge output JSON (gitignored)
validation/          # Golden sets and judge scripts
```

---

## Research Paper Context

- **Paper:** "An Empirical Study of Version-Control and Validation Workflows for Enterprise AI Systems"
- **Venue:** IEEE WOCC 2026 — Accepted April 15, 2026
- **Key reviewer feedback:** Add real empirical metrics; rename title; expand LLM-judge section
- **Next:** Build `tests/` and `validation/` to collect empirical data for the camera-ready version

See `REQUIREMENTS.md` for the living feature roadmap.
