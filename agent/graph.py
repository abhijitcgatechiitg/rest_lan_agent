"""
LangGraph StateGraph for Smart Bistro.

Graph shape
-----------
                    START
                      │
              route_intent()   ← conditional edge (rule-based router)
          ┌─────┬──────┼──────┬──────┐
          ▼     ▼      ▼      ▼      ▼
       menu_  cart_ confirm_ order_ chat_
       node   node   node    node   node
          └─────┴──────┼──────┴──────┘
                       ▼
                      END

Checkpointing
-------------
MemorySaver persists the full AgentState per thread_id.
Each conversation gets a unique thread_id; state is automatically
loaded on subsequent invocations using the same thread_id.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.nodes import (
    route_intent,
    menu_node,
    cart_node,
    confirm_node,
    order_node,
    chat_node,
)


def build_graph() -> StateGraph:
    """Build and compile the Smart Bistro StateGraph."""
    builder = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("menu_node",    menu_node)
    builder.add_node("cart_node",    cart_node)
    builder.add_node("confirm_node", confirm_node)
    builder.add_node("order_node",   order_node)
    builder.add_node("chat_node",    chat_node)

    # ── Entry point: START → route_intent → one of the five nodes ─────────────
    builder.add_conditional_edges(
        START,
        route_intent,
        {
            "menu_node":    "menu_node",
            "cart_node":    "cart_node",
            "confirm_node": "confirm_node",
            "order_node":   "order_node",
            "chat_node":    "chat_node",
        },
    )

    # ── All nodes finish at END (single-turn response, no internal loops) ─────
    builder.add_edge("menu_node",    END)
    builder.add_edge("cart_node",    END)
    builder.add_edge("confirm_node", END)
    builder.add_edge("order_node",   END)
    builder.add_edge("chat_node",    END)

    # ── Compile with in-memory checkpointer ───────────────────────────────────
    # MemorySaver stores the full AgentState per thread_id.
    # Production: swap for SqliteSaver / RedisSaver.
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Module-level singleton — imported by runner.py, streamlit_app.py, main.py
graph = build_graph()
