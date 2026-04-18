import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

def build_llm():
    use_llm = os.getenv("USE_LLM", "false").lower() == "true"
    if not use_llm:
        return None
    model = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
    return ChatAnthropic(model=model, temperature=0.3)

def phrase(system: str, content: str) -> str:
    llm = build_llm()
    if llm is None:
        return content  # fallback if Claude is disabled
    # Use explicit message objects to avoid prompt-template parsing of braces
    # present in system prompt text (e.g., tool signatures with {} and []).
    res = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=content),
    ])
    return res.content if hasattr(res, "content") else str(res)
