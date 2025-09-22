import os
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

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
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "{content}")
    ])
    chain = prompt | llm
    res = chain.invoke({"content": content})
    return res.content if hasattr(res, "content") else str(res)