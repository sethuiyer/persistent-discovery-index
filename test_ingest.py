#!/usr/bin/env python3
"""Self-checks for the multi-format ingest layer. Run: python3 test_ingest.py

Every format is exercised on a synthetic fixture, so the checks are reproducible
without depending on anyone's private traces.
"""
from __future__ import annotations

import json
import os
import tempfile

from ingest import (CANONICAL, LANGSMITH, OPENAI, PI, detect_format, load_any,
                    load_canonical, load_langsmith, load_openai, load_paths,
                    to_canonical, write_canonical)

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def w(path, objs):
    with open(path, "w") as f:
        for o in objs:
            f.write(json.dumps(o) + "\n")


print("ingest self-checks")

with tempfile.TemporaryDirectory() as d:
    # ---------------- canonical ----------------
    cp = os.path.join(d, "canonical.jsonl")
    w(cp, [{"model": "m", "project": "p", "prompt": "t", "outcome": "stop",
            "steps": [{"tool": "read", "args": {"path": "a.py"}},
                      {"tool": "edit", "args": {"path": "a.py"}}]},
           {"model": "m", "project": "p", "prompt": "t2", "outcome": "error",
            "steps": [{"tool": "bash", "args": {"command": "x"}, "error": "boom"}]}])
    check("canonical detected", detect_format(cp) == CANONICAL)
    rs = load_canonical(cp)
    check("canonical: two runs", len(rs) == 2)
    check("canonical: steps parsed", [s.tool for s in rs[0].steps] == ["read", "edit"])
    check("canonical: error attributed", rs[1].steps[0].error == "boom")
    check("canonical: outcome respected", rs[0].succeeded and not rs[1].succeeded)

    # ---------------- openai ----------------
    op = os.path.join(d, "openai.jsonl")
    w(op, [{"messages": [
        {"role": "user", "content": "fix it"},
        {"role": "assistant", "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "read_file", "arguments": json.dumps({"path": "a.py"})}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "ok"},
        {"role": "assistant", "tool_calls": [
            {"id": "c2", "type": "function",
             "function": {"name": "apply_patch", "arguments": json.dumps({"path": "a.py"})}}]},
        {"role": "tool", "tool_call_id": "c2", "content": "Error: patch failed"},
        {"role": "assistant", "content": "done"}]}])
    check("openai detected", detect_format(op) == OPENAI)
    rs = load_openai(op)
    check("openai: one run", len(rs) == 1)
    check("openai: two tool steps", [s.tool for s in rs[0].steps] == ["read_file", "apply_patch"])
    check("openai: arguments string parsed", rs[0].steps[0].args.get("path") == "a.py")
    check("openai: error heuristic fires", rs[0].steps[1].error is not None)
    check("openai: final text -> success", rs[0].succeeded)

    # ---------------- langsmith ----------------
    lp = os.path.join(d, "langsmith.jsonl")
    objs = []
    for k, (nm, rt) in enumerate([("planner", "chain"), ("search", "tool"), ("write", "tool")]):
        objs.append({"id": f"r{k}", "trace_id": "t1", "name": nm, "run_type": rt,
                     "inputs": {"q": k}, "error": None,
                     "start_time": f"2026-01-01T00:00:0{k}Z"})
    w(lp, objs)
    check("langsmith detected", detect_format(lp) == LANGSMITH)
    rs = load_langsmith(lp)
    check("langsmith: one trace -> one run", len(rs) == 1)
    check("langsmith: tool/chain steps ordered",
          [s.tool for s in rs[0].steps] == ["planner", "search", "write"])
    check("langsmith: no error -> stop", rs[0].outcome == "stop")

    # ---------------- pi (shape only; full parser is tested in test_adapter) ------
    pp = os.path.join(d, "pi.jsonl")
    w(pp, [{"type": "session", "cwd": "/x/proj"},
           {"type": "model_change", "modelId": "mm"},
           {"type": "message", "message": {
               "role": "user", "content": [{"type": "text", "text": "go"}]}},
           {"type": "message", "message": {
               "role": "assistant", "stopReason": "toolUse", "content": [
                   {"type": "toolCall", "id": "c1", "name": "bash",
                    "arguments": {"command": "ls"}}]}},
           {"type": "message", "message": {
               "role": "toolResult", "toolCallId": "c1", "toolName": "bash",
               "isError": False, "content": [{"type": "text", "text": "ok"}]}},
           {"type": "message", "message": {"role": "assistant", "stopReason": "stop",
                                           "content": [{"type": "text", "text": "d"}]}}])
    check("pi detected", detect_format(pp) == PI)
    check("pi loads through load_any", len(load_any(pp)) == 1)

    # ---------------- round trip ----------------
    rs = load_any(cp)
    rt = os.path.join(d, "roundtrip.jsonl")
    n = write_canonical(rs, rt)
    check("canonical round trip writes all runs", n == len(rs))
    rs2 = load_any(rt)
    check("round trip preserves tool sequences",
          [s.tool for s in rs[0].steps] == [s.tool for s in rs2[0].steps])
    check("round trip preserves outcomes", [r.outcome for r in rs] == [r.outcome for r in rs2])
    check("round trip keeps errors",
          rs2[1].steps[0].error == rs[1].steps[0].error)

    # ---------------- directory walk + mixed formats ----------------
    allruns = load_paths([d])
    check("directory walk finds every format", len(allruns) >= 5)

    # ---------------- malformed input is skipped, not fatal ----------------
    bad = os.path.join(d, "bad.jsonl")
    open(bad, "w").write("not json\n{\"steps\": []}\n")
    check("malformed lines skipped", load_any(bad) == [])

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
