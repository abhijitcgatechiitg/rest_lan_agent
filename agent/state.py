from typing import TypedDict, Literal, List, Dict, Optional

class CartLine(TypedDict):
    item_id: str
    name: str
    qty: int
    unit_price: float
    options: Dict[str, str]

class AgentState(TypedDict, total=False):
    user_id: Optional[str]
    stage: Literal["greet", "menu", "cart", "confirm", "placed", "idle"]
    cart: List[CartLine]
    subtotal: float
    currency: str
    menu_version: str
    last_user_message: str
    last_ai_message: str
    suggested_items: List[str]
    order_id: Optional[str]
    history_enabled: bool
    debug_trace: List[str]
    interrupt_context: Dict[str, str]