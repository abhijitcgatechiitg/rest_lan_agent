"""
CLI entry point for Smart Bistro.

Each user message is processed through the LangGraph via run_turn().
The graph persists state (cart, stage, history) between turns using
MemorySaver keyed by session_id.
"""

import uuid
from dotenv import load_dotenv
from agent.runner import run_turn

load_dotenv()


if __name__ == "__main__":
    session_id = str(uuid.uuid4())
    print("👋 Welcome to Smart Bistro! (type 'quit' or 'exit' to leave)")
    print()

    while True:
        try:
            user = input("You: ").strip().lstrip("\ufeff")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user:
            continue
        if user.lower() in {"quit", "exit"}:
            print("Thanks for visiting Smart Bistro! See you next time. 🍗")
            break

        reply, _ = run_turn(session_id, user, user_id="cli-user")
        print(f"Bistro: {reply}\n")
