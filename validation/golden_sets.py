"""
validation/golden_sets.py
==========================
Golden scenarios for LLM-as-judge evaluation (J-series).

Each scenario is a list of user turns. run_judge.py feeds them through
run_turn() to get the agent's responses, then passes those responses to
the judge LLM for scoring.

SCENARIO STRUCTURE
------------------
{
    "id":          "J-01"            # scenario ID for results JSON
    "name":        "..."             # human-readable label
    "turns":       ["msg1", ...]     # user inputs fed to the agent in order
    "eval_turn":   -1                # index of the turn whose response is judged
                                     # -1 means the last turn's response
    "dimensions":  ["Accuracy", ...]  # what the judge scores (0-10 each)
    "ground_truth": "..."            # facts the judge uses to verify accuracy
}
"""

GOLDEN_SCENARIOS = [
    {
        "id": "J-01",
        "name": "Menu Display Accuracy",
        "description": (
            "Agent is asked to show the menu. "
            "Judge verifies all 4 categories are present, items are listed "
            "with prices, and the format is clear."
        ),
        "turns": ["show menu"],
        "eval_turn": -1,
        "dimensions": ["Accuracy", "Completeness", "Format Clarity"],
        "ground_truth": (
            "The Smart Bistro menu v2 has exactly 4 categories: "
            "Original Meals (8 items, OM01-OM08), "
            "Kids Meals (3 items, KM01-KM03), "
            "Waffle Fries (2 items, WF01-WF02), "
            "Drinks (11 items, DK01-DK11). "
            "All items must appear with their names and USD prices. "
            "Example spot-checks: Waffle Fries Medium=$2.49, "
            "Classic Crispy Sandwich Meal=$8.99, Sweet Tea Medium=$2.25."
        ),
    },

    {
        "id": "J-02",
        "name": "Order Flow — Happy Path End-to-End",
        "description": (
            "Full 3-turn order: add items → checkout → confirm. "
            "Judge verifies the final order confirmation contains the correct "
            "total, an ORD- prefixed order ID, and a 30-minute ETA."
        ),
        "turns": [
            "2 Waffle Fries Medium and 1 Sweet Tea Medium",
            "checkout",
            "yes",
        ],
        "eval_turn": -1,
        "dimensions": ["Accuracy", "Completeness", "Consistency"],
        "ground_truth": (
            "The order contains: Waffle Fries Medium x2 @ $2.49 each = $4.98, "
            "Sweet Tea Medium x1 @ $2.25 = $2.25. "
            "Expected total = $7.23. "
            "The confirmation response must include: "
            "(1) an order ID matching the pattern ORD-<digits>, "
            "(2) total = $7.23, "
            "(3) ETA = 30 minutes. "
            "Any deviation in total or missing fields is an accuracy failure."
        ),
    },

    {
        "id": "J-03",
        "name": "Off-Topic FAQ — Dietary Question",
        "description": (
            "User asks a dietary FAQ not directly answered by the menu data. "
            "Judge evaluates whether the agent is helpful, stays in persona "
            "as a bistro assistant, and avoids hallucinating menu items."
        ),
        "turns": ["Do you have any gluten-free options?"],
        "eval_turn": -1,
        "dimensions": ["Helpfulness", "Persona Adherence", "Hallucination Avoidance"],
        "ground_truth": (
            "The Smart Bistro menu does not have an explicit gluten-free label "
            "on any item. A good response acknowledges the question helpfully, "
            "suggests items that may be lower in gluten risk (e.g. grilled options, "
            "drinks) or advises the customer to check with staff, and does NOT "
            "invent menu items or claim items are certified gluten-free. "
            "The agent should remain in its bistro assistant persona throughout."
        ),
    },
]
