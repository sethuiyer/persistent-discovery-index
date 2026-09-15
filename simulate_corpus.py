#!/usr/bin/env python3
"""
simulate_corpus.py — Controlled multi-agent trace corpus generator.

Generates a controlled, repeated-task corpus across multiple agent architectures
to demonstrate how PDI metrics isolate algorithmic waste from task geometry.

Tasks:
  1. fix_token_auth           (Fix failing unit test in auth/token.py)
  2. payment_gateway_500      (Investigate 500 error in checkout/gateway.py)
  3. sqlalchemy_migration     (Refactor deprecated syntax in models/user.py)
  4. cve_security_patch       (Patch vulnerability in package dependencies)
  5. ratelimit_middleware     (Add token-bucket middleware in server.py)

Agent Archetypes:
  - agent-disciplined : Lean, direct, high-leverage tool calls (benchmark baseline)
  - agent-wanderer    : Achieves same outcomes but with wide exploratory search
  - agent-looping     : Error-prone, repeats tool calls, suffers from command failures

Emits canonical JSONL traces compatible with ingest.py, pdi_profile.py, and dashboard.py.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any, Dict, List

TASKS = [
    {
        "id": "fix_token_auth",
        "prompt": "Fix failing unit test in auth/token.py: signature verification expired",
        "primary_file": "auth/token.py",
        "test_cmd": "pytest tests/test_auth.py",
        "related_files": ["auth/config.py", "auth/keys.pem", "tests/test_auth.py"],
    },
    {
        "id": "payment_gateway_500",
        "prompt": "Investigate 500 Internal Server Error in checkout/gateway.py during Stripe webhook",
        "primary_file": "checkout/gateway.py",
        "test_cmd": "pytest tests/test_checkout.py",
        "related_files": ["checkout/models.py", "checkout/stripe_client.py", "logs/app.log"],
    },
    {
        "id": "sqlalchemy_migration",
        "prompt": "Refactor deprecated Query.get() syntax to Session.get() in models/user.py",
        "primary_file": "models/user.py",
        "test_cmd": "pytest tests/test_models.py",
        "related_files": ["models/base.py", "models/session.py", "alembic/versions/001.py"],
    },
    {
        "id": "cve_security_patch",
        "prompt": "Patch high-severity CVE-2026-4401 in dependencies by updating cryptography package",
        "primary_file": "requirements.txt",
        "test_cmd": "pip check && pytest tests/test_crypto.py",
        "related_files": ["setup.py", "pyproject.toml", "security/audit.log"],
    },
    {
        "id": "ratelimit_middleware",
        "prompt": "Add token-bucket rate-limiting middleware to API routes in server.py",
        "primary_file": "server.py",
        "test_cmd": "pytest tests/test_server.py",
        "related_files": ["middleware/limiter.py", "config/redis.py", "tests/test_server.py"],
    },
]


def gen_disciplined_run(task: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Disciplined agent: direct search, reads primary file, edits, verifies."""
    succeeded = rng.random() < 0.94
    steps = [
        {"tool": "read", "args": {"path": task["primary_file"]}, "error": None},
        {"tool": "edit", "args": {"path": task["primary_file"], "patch": "fix"}, "error": None},
        {"tool": "bash", "args": {"command": task["test_cmd"]}, "error": None if succeeded else "exit status 1: test assertion failed"},
    ]
    if not succeeded and rng.random() < 0.5:
        # Quick 1-step correction attempt
        steps.append({"tool": "edit", "args": {"path": task["primary_file"], "patch": "retry_fix"}, "error": None})
        steps.append({"tool": "bash", "args": {"command": task["test_cmd"]}, "error": None})
        succeeded = True

    return {
        "model": "agent-disciplined",
        "project": "bench_suite_v1",
        "prompt": task["prompt"],
        "outcome": "stop" if succeeded else "error",
        "steps": steps,
    }


def gen_wanderer_run(task: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Wanderer agent: achieves high success but explores many irrelevant files and extra commands."""
    succeeded = rng.random() < 0.88
    steps: List[Dict[str, Any]] = []

    # 1. Unfocused exploratory searches
    steps.append({"tool": "bash", "args": {"command": f"grep -rn '{task['id'].split('_')[0]}' ."}, "error": None})
    steps.append({"tool": "bash", "args": {"command": "find . -name '*.py' | head -n 30"}, "error": None})

    # 2. Reading related and unrelated files
    num_reads = rng.randint(2, 4)
    sampled_files = rng.sample(task["related_files"], min(len(task["related_files"]), num_reads))
    for f in sampled_files:
        steps.append({"tool": "read", "args": {"path": f}, "error": None})

    # 3. Reading primary file
    steps.append({"tool": "read", "args": {"path": task["primary_file"]}, "error": None})

    # 4. Speculative edits and intermittent testing
    for iteration in range(rng.randint(2, 4)):
        steps.append({"tool": "edit", "args": {"path": task["primary_file"], "attempt": iteration}, "error": None})
        steps.append({"tool": "bash", "args": {"command": task["test_cmd"]},
                      "error": None if (iteration == 2 and succeeded) else "exit status 1: failed"})

    if succeeded and (not steps[-1]["error"] is None):
        steps.append({"tool": "edit", "args": {"path": task["primary_file"], "final": True}, "error": None})
        steps.append({"tool": "bash", "args": {"command": task["test_cmd"]}, "error": None})

    return {
        "model": "agent-wanderer",
        "project": "bench_suite_v1",
        "prompt": task["prompt"],
        "outcome": "stop" if succeeded else "error",
        "steps": steps,
    }


def gen_looping_run(task: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Looping agent: hits bash syntax errors, repeats identical searches, frequently aborts."""
    succeeded = rng.random() < 0.52
    steps: List[Dict[str, Any]] = []

    # Repetitive search commands with syntax or path errors
    steps.append({"tool": "bash", "args": {"command": "cat unexisting_log.txt"}, "error": "FileNotFoundError: [Errno 2] No such file"})
    steps.append({"tool": "bash", "args": {"command": f"grep -n 'TODO' {task['primary_file']}"}, "error": None})

    for _ in range(rng.randint(3, 6)):
        cmd = rng.choice([
            "ls -la /tmp",
            f"git diff {task['primary_file']}",
            "grep -r 'Exception' .",
            "pytest --maxfail=1",
        ])
        err = "exit status 1" if "pytest" in cmd and not succeeded else None
        steps.append({"tool": "bash", "args": {"command": cmd}, "error": err})

    steps.append({"tool": "read", "args": {"path": task["primary_file"]}, "error": None})
    steps.append({"tool": "edit", "args": {"path": task["primary_file"], "mode": "blind_patch"}, "error": None})
    steps.append({"tool": "bash", "args": {"command": task["test_cmd"]}, "error": None if succeeded else "exit status 1"})

    outcome = "stop" if succeeded else rng.choice(["error", "length", "aborted"])
    return {
        "model": "agent-looping",
        "project": "bench_suite_v1",
        "prompt": task["prompt"],
        "outcome": outcome,
        "steps": steps,
    }


def generate_corpus(runs_per_task: int = 25, seed: int = 42) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    all_runs: List[Dict[str, Any]] = []

    for task in TASKS:
        for _ in range(runs_per_task):
            all_runs.append(gen_disciplined_run(task, rng))
            all_runs.append(gen_wanderer_run(task, rng))
            all_runs.append(gen_looping_run(task, rng))

    rng.shuffle(all_runs)
    return all_runs


def main():
    parser = argparse.ArgumentParser(description="Generate simulated controlled agent corpus")
    parser.add_argument("--out", default="corpus/traces.jsonl", help="Output path for traces JSONL")
    parser.add_argument("--runs-per-task", type=int, default=20, help="Runs per task per agent archetype")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    runs = generate_corpus(runs_per_task=args.runs_per_task, seed=args.seed)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in runs:
            f.write(json.dumps(r) + "\n")

    print(f"Generated {len(runs)} runs across {len(TASKS)} tasks and 3 agent archetypes.")
    print(f"Saved to: {args.out}")

    # Breakdown
    models = {}
    for r in runs:
        m = r["model"]
        models.setdefault(m, {"count": 0, "success": 0, "steps": 0})
        models[m]["count"] += 1
        if r["outcome"] == "stop":
            models[m]["success"] += 1
        models[m]["steps"] += len(r["steps"])

    print("\nSummary Breakdown:")
    for m, s in sorted(models.items()):
        succ_rate = s["success"] / s["count"] * 100
        avg_steps = s["steps"] / s["count"]
        print(f"  {m:<18}: {s['count']} runs | {succ_rate:>5.1f}% success | {avg_steps:>5.2f} avg tool calls/run")


if __name__ == "__main__":
    main()
