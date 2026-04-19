"""
validation/run_judge.py
========================
LLM-as-Judge evaluation runner — J-series probabilistic validation.

HOW IT WORKS
------------
1. For each golden scenario in golden_sets.py, the agent (Claude 3 Haiku)
   is run N times through run_turn() to collect N independent responses.
2. Each response is sent to the judge LLM (Claude 3.5 Haiku) with the
   judge_prompt.txt instructions and the scenario's ground truth.
3. The judge returns a JSON score (0-10) for each evaluation dimension.
4. Results are saved to validation_results/judge_results_<timestamp>.json
5. A summary table is printed to the terminal.

MODEL ROLES
-----------
  Agent : claude-3-haiku-20240307   (reads MODEL_NAME from .env)
  Judge : claude-haiku-4-5-20251001  (hardcoded — stronger evaluator)

PASS THRESHOLD
--------------
  Mean score >= 7.0 per dimension   (standard LLM-as-judge threshold)
  Inter-run std dev < 1.5           (consistency requirement)

RUN
---
  cd C:/Abhijit/01NobelResearchLab/rest_lan_agent
  source .venv/Scripts/activate
  python validation/run_judge.py

  Optional flags:
    --runs  N     number of agent runs per scenario (default 3)
    --scenario J-01   run only one scenario
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from uuid import uuid4

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import anthropic
from agent.runner import run_turn
from validation.golden_sets import GOLDEN_SCENARIOS

# ── constants ─────────────────────────────────────────────────────────────────
JUDGE_MODEL  = "claude-haiku-4-5-20251001"
AGENT_MODEL  = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
PASS_MEAN    = 7.0
PASS_STD_MAX = 1.5
RESULTS_DIR  = ROOT / "validation_results"
JUDGE_PROMPT = (Path(__file__).parent / "judge_prompt.txt").read_text(encoding="utf-8")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── helpers ───────────────────────────────────────────────────────────────────

def run_scenario_once(scenario: dict) -> str:
    """
    Drive the agent through all turns of a scenario.
    Returns the agent's response for the eval_turn.
    """
    thread_id = str(uuid4())
    responses = []
    for turn_text in scenario["turns"]:
        reply, _ = run_turn(thread_id, turn_text)
        responses.append(reply)
        time.sleep(0.3)  # small pause between turns

    eval_idx = scenario.get("eval_turn", -1)
    return responses[eval_idx]


def call_judge(scenario: dict, agent_response: str) -> dict:
    """
    Send the agent_response to the judge LLM.
    Returns parsed JSON: {"scores": {...}, "rationale": {...}}
    """
    user_message = (
        f"SCENARIO: {scenario['name']}\n"
        f"DESCRIPTION: {scenario['description']}\n\n"
        f"GROUND TRUTH:\n{scenario['ground_truth']}\n\n"
        f"USER INPUT: {scenario['turns'][scenario.get('eval_turn', -1)]}\n\n"
        f"AGENT RESPONSE:\n{agent_response}\n\n"
        f"DIMENSIONS TO SCORE: {', '.join(scenario['dimensions'])}"
    )

    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=512,
        messages=[
            {"role": "user", "content": JUDGE_PROMPT + "\n\n" + user_message}
        ],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if judge wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"scores": {}, "rationale": {}, "parse_error": raw}


def aggregate(run_results: list[dict], dimensions: list[str]) -> dict:
    """
    Given N judge results for one scenario, compute mean and stdev per dimension.
    Returns: {dim: {"scores": [..], "mean": x, "std": x, "pass": bool}}
    """
    agg = {}
    for dim in dimensions:
        scores = [r["scores"].get(dim) for r in run_results if r["scores"].get(dim) is not None]
        if not scores:
            agg[dim] = {"scores": [], "mean": None, "std": None, "pass": False}
            continue
        m = round(mean(scores), 2)
        s = round(stdev(scores), 2) if len(scores) > 1 else 0.0
        agg[dim] = {
            "scores": scores,
            "mean": m,
            "std": s,
            "pass": m >= PASS_MEAN and s <= PASS_STD_MAX,
        }
    return agg


def print_summary(all_results: list[dict]) -> None:
    sep = "-" * 72
    print(f"\n{'='*72}")
    print(f"  LLM-AS-JUDGE RESULTS  |  Agent: {AGENT_MODEL}  |  Judge: {JUDGE_MODEL}")
    print(f"{'='*72}")
    total_dims = 0
    passed_dims = 0
    for sc in all_results:
        print(f"\n  {sc['scenario_id']} — {sc['scenario_name']}")
        print(sep)
        print(f"  {'Dimension':<30} {'Scores':<20} {'Mean':>6}  {'Std':>5}  {'Pass?':>6}")
        print(sep)
        for dim, data in sc["aggregated"].items():
            total_dims += 1
            scores_str = str(data["scores"])
            pass_str = "PASS" if data["pass"] else "FAIL"
            if data["pass"]:
                passed_dims += 1
            print(f"  {dim:<30} {scores_str:<20} {str(data['mean']):>6}  {str(data['std']):>5}  {pass_str:>6}")
        print(sep)
    print(f"\n  OVERALL: {passed_dims}/{total_dims} dimensions passed")
    print(f"  Pass threshold: mean >= {PASS_MEAN}, std <= {PASS_STD_MAX}")
    print(f"{'='*72}\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LLM-as-Judge runner for Smart Bistro")
    parser.add_argument("--runs",     type=int, default=3,  help="Agent runs per scenario (default 3)")
    parser.add_argument("--scenario", type=str, default=None, help="Run only this scenario ID e.g. J-01")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    scenarios = GOLDEN_SCENARIOS
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            print(f"ERROR: Scenario '{args.scenario}' not found.")
            sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    all_results = []

    for scenario in scenarios:
        print(f"\nRunning {scenario['id']} — {scenario['name']} ({args.runs} runs)...")
        run_results = []

        for run_idx in range(1, args.runs + 1):
            print(f"  Run {run_idx}/{args.runs}: calling agent...", end=" ", flush=True)
            agent_response = run_scenario_once(scenario)
            print("calling judge...", end=" ", flush=True)
            judge_result = call_judge(scenario, agent_response)
            run_results.append({
                "run": run_idx,
                "agent_response": agent_response,
                "judge_raw": judge_result,
                "scores": judge_result.get("scores", {}),
                "rationale": judge_result.get("rationale", {}),
            })
            print("done.")
            time.sleep(1.0)  # rate-limit buffer between judge calls

        aggregated = aggregate(run_results, scenario["dimensions"])

        all_results.append({
            "scenario_id":   scenario["id"],
            "scenario_name": scenario["name"],
            "dimensions":    scenario["dimensions"],
            "runs":          run_results,
            "aggregated":    aggregated,
        })

    # ── save JSON ─────────────────────────────────────────────────────────────
    output = {
        "metadata": {
            "timestamp":   timestamp,
            "agent_model": AGENT_MODEL,
            "judge_model": JUDGE_MODEL,
            "runs_per_scenario": args.runs,
            "pass_threshold_mean": PASS_MEAN,
            "pass_threshold_std":  PASS_STD_MAX,
        },
        "results": all_results,
    }
    out_path = RESULTS_DIR / f"judge_results_{timestamp}.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {out_path.relative_to(ROOT)}")

    print_summary(all_results)


if __name__ == "__main__":
    main()
