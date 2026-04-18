from typing import TypedDict, Literal, List, Dict, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CartLine(TypedDict):
    item_id: str
    name: str
    qty: int
    unit_price: float
    options: Dict[str, str]


class AgentState(TypedDict, total=False):
    # ── Conversation history (managed by LangGraph add_messages reducer) ──────
    # Each turn appends HumanMessage + AIMessage — never overwritten.
    messages: Annotated[List[BaseMessage], add_messages]

    # ── Session identity & flow stage ─────────────────────────────────────────
    user_id: Optional[str]
    stage: Literal[
        "greet",
        "menu",
        "cart",
        "confirm",           # cart shown, waiting for checkout command
        "awaiting_confirmation",  # checkout triggered, waiting for yes/no
        "placed",
        "idle",
    ]

    # ── Cart ──────────────────────────────────────────────────────────────────
    cart: List[CartLine]
    subtotal: float
    currency: str

    # ── Menu metadata ─────────────────────────────────────────────────────────
    menu_version: str

    # ── Last turn snapshots (used by nodes for quick access) ──────────────────
    last_user_message: str
    last_ai_message: str

    # ── Misc ──────────────────────────────────────────────────────────────────
    suggested_items: List[str]
    order_id: Optional[str]
    history_enabled: bool
    debug_trace: List[str]
    interrupt_context: Dict[str, str]
