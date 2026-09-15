#!/usr/bin/env python3
"""Self-checks for the real-trace adapter. Run: python3 test_adapter.py

Uses a synthetic pi-format transcript so the checks are reproducible without
depending on anyone's private session logs. A real-data smoke test runs only if
~/.pi/agent/sessions exists and is non-empty.
"""
from __future__ import annotations

import json
import os
import tempfile

from adapters import (PI_SESSIONS, TOOL_LEVEL_NAMES, load_pi_runs, load_pi_session,
                      tool_tower, arg_class, normalize_args)
from quotient_tower import TowerViolation

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


FIXTURE = [
    {"type": "session", "cwd": "/x/navokoj", "id": "s1", "timestamp": 1, "version": "1"},
    {"type": "model_change", "modelId": "modelA", "provider": "p",
     "id": "m1", "parentId": None, "timestamp": 2},
    {"type": "message", "id": "u1", "parentId": None, "timestamp": 3,
     "message": {"role": "user", "content": [{"type": "text", "text": "deep research this repo"}]}},
    {"type": "message", "id": "a1", "parentId": "u1", "timestamp": 4,
     "message": {"role": "assistant", "stopReason": "toolUse", "content": [
         {"type": "toolCall", "id": "c1", "name": "bash", "arguments": {"command": "ls -la | wc -l"}}]}},
    {"type": "message", "id": "t1", "parentId": "a1", "timestamp": 5,
     "message": {"role": "toolResult", "toolCallId": "c1", "toolName": "bash",
                 "isError": False, "content": [{"type": "text", "text": "ok"}]}},
    {"type": "message", "id": "a2", "parentId": "t1", "timestamp": 6,
     "message": {"role": "assistant", "stopReason": "stop",
                 "content": [{"type": "text", "text": "done"}]}},
    {"type": "message", "id": "u2", "parentId": None, "timestamp": 7,
     "message": {"role": "user", "content": [{"type": "text", "text": "second task"}]}},
    {"type": "message", "id": "a3", "parentId": "u2", "timestamp": 8,
     "message": {"role": "assistant", "stopReason": "toolUse", "content": [
         {"type": "toolCall", "id": "c2", "name": "edit", "arguments": {"path": "a.py"}}]}},
    {"type": "message", "id": "t2", "parentId": "a3", "timestamp": 9,
     "message": {"role": "toolResult", "toolCallId": "c2", "toolName": "edit",
                 "isError": True, "content": [{"type": "text", "text": "no such file"}]}},
    {"type": "message", "id": "a4", "parentId": "t2", "timestamp": 10,
     "message": {"role": "assistant", "stopReason": "error", "content": []}},
]


print("real-trace adapter self-checks")

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "2026-01-01T00-00-00-000Z_abc123.jsonl")
    with open(p, "w") as f:
        for ev in FIXTURE:
            f.write(json.dumps(ev) + "\n")

    turns = load_pi_session(p)

    check("two turns reconstructed", len(turns) == 2)
    t1, t2 = turns

    # turn structure
    check("turn 1 has one step", len(t1.steps) == 1)
    check("tool name recovered", t1.steps[0].tool == "bash")
    check("tool arguments recovered", t1.steps[0].args.get("command") == "ls -la | wc -l")
    check("successful result paired to call", t1.steps[0].error is None)
    check("terminal outcome = stop", t1.outcome == "stop")
    check("turn 1 counts as succeeded", t1.succeeded)
    check("opening prompt captured", t1.prompt == "deep research this repo")
    check("model captured", t1.model == "modelA")
    check("project captured", t1.project == "navokoj")

    # turn 2: an errored tool result must be attributed to the right step
    check("turn 2 error attributed", t2.steps[0].error == "no such file")
    check("terminal outcome = error", t2.outcome == "error")
    check("turn 2 counts as failed", not t2.succeeded)
    check("second prompt captured", t2.prompt == "second task")

    # argument classification
    s = t1.steps[0]
    check("arg_class extracts the program", arg_class(s)[0] == "ls")
    check("arg_class sees the pipe", arg_class(s)[1] is True)
    check("normalize_args collapses whitespace", "  " not in normalize_args(s))

    # tower: the refinement law must hold, structurally
    tower = tool_tower()
    try:
        tower.validate(turns)
        check("tool tower satisfies the refinement law on real-shaped turns", True)
    except TowerViolation as e:
        check(f"tool tower satisfies the refinement law ({e})", False)

    # tower levels are explicitly nested -> law holds by construction
    sig1 = tower.signature(t1)
    check("tower has 6 behavioural levels", len(sig1) == 6)
    check("each level contains the previous (Q2 repeats Q1)",
          sig1[0] == t1.outcome and sig1[1][0] == t1.outcome)

# a real-data smoke test, only if the corpus is present
if os.path.isdir(PI_SESSIONS) and any(
        f.endswith(".jsonl") for _, _, fs in os.walk(PI_SESSIONS) for f in fs):
    real = load_pi_runs()
    check("real corpus loads", len(real) > 0)
    check("real turns have models", all(t.model for t in real))
    check("real turns have terminal outcomes", all(t.outcome for t in real))
    tower = tool_tower()
    try:
        tower.validate(real)
        check("refinement law holds on the full real corpus", True)
    except TowerViolation as e:
        check(f"refinement law holds on the full real corpus ({e})", False)
else:
    print("  [skip] real corpus not present")

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
