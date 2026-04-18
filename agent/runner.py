"""
Thin adapter between the compiled LangGraph and the UI layers.

Both streamlit_app.py and main.py call run_turn() — they never touch
the graph, nodes, or state directly.

Usage
-----
    from agent.runner import run_turn

    # Each call returns (reply_string, full_state_dict)
    reply, state = run_turn(thread_id, user_input)
    reply, state = run_turn(thread_id, user_input, user_id="cli-user")

Thread identity
---------------
thread_id is the key MemorySaver uses to persist state between turns.
Pass the same thread_id across turns to continue a conversation.
Generate a new thread_id (e.g. str(uuid4())) to start fresh.
"""

from langchain_core.messages import HumanMessage

from agent.graph import graph

# Fields required for the very first turn of a new thread.
# On subsequent turns these are loaded from the MemorySaver checkpoint.
_INIT_STATE = {
    "cart": [],
    "subtotal": 0.0,
    "currency": "USD",
    "stage": "greet",
    "menu_version": "",
    "last_ai_message": "",
    "suggested_items": [],
    "order_id": None,
    "history_enabled": True,
    "debug_trace": [],
    "interrupt_context": {},
}


def run_turn(
    thread_id: str,
    user_input: str,
    user_id: str = "web-user",
) -> tuple[str, dict]:
    """
    Process one user turn through the LangGraph.

    Args:
        thread_id:  Unique conversation key for MemorySaver.
        user_input: Raw text typed by the user.
        user_id:    Written into order history. Defaults to 'web-user'.

    Returns:
        (reply, state)
        reply — the assistant's message string, ready to display.
        state — the full AgentState dict after this turn.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Detect first turn: no checkpoint exists yet for this thread_id.
    existing = graph.get_state(config)
    is_new_thread = not existing.values

    input_dict: dict = {
        "last_user_message": user_input,
        "messages": [HumanMessage(content=user_input)],
    }
    if is_new_thread:
        input_dict.update({**_INIT_STATE, "user_id": user_id})

    try:
        result = graph.invoke(input_dict, config=config)
    except Exception as exc:
        reply = f"⚠️ Something went wrong: {exc}"
        return reply, {}

    reply = result.get("last_ai_message", "")
    return reply, result
