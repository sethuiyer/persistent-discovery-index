#!/usr/bin/env python3
"""
test_ingest_more.py — self-checking suite for the CrewAI / AutoGen / OTel loaders

The loaders are written to PUBLISHED SCHEMAS, not to a live capture. These tests
therefore check two different things:

  1. SCHEMA CONFORMANCE -- the loader reads what the spec says is there.
  2. EDGE PRESERVATION  -- the axiom's third clause. A loader that collapses
     repeated calls, drops arguments, or mis-pairs a result with its call has
     thrown away the edges, whatever its schema conformance.

(2) is the one that matters, and it caught a real AutoGen bug: pairing results by
tool_call_id alone mis-attributes errors, because v0.2 puts the call on the
assistant message and the id (if any) on the function message.

Run: python3 test_ingest_more.py     (exit 0 on success)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from ingest import (AUTOGEN, CREWAI, OTEL, detect_format, load_any, load_autogen,
                    load_crewai, load_otel_genai, to_canonical, write_canonical)
from ingest import CANONICAL, load_canonical

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_detection() -> None:
    print("detection")
    check("otel fixture detects as otel",
          detect_format(f"{FIX}/otel_genai.json") == OTEL,
          detect_format(f"{FIX}/otel_genai.json"))
    check("autogen fixture detects as autogen",
          detect_format(f"{FIX}/autogen_chat.jsonl") == AUTOGEN,
          detect_format(f"{FIX}/autogen_chat.jsonl"))
    check("crewai fixture detects as crewai",
          detect_format(f"{FIX}/crewai_output.json") == CREWAI,
          detect_format(f"{FIX}/crewai_output.json"))


def test_otel() -> None:
    print("OTel GenAI")
    runs = load_otel_genai(f"{FIX}/otel_genai.json")
    check("two traces -> two runs", len(runs) == 2, str(len(runs)))
    if len(runs) != 2:
        return
    a, b = runs
    check("trace with a failed tool is an error", a.outcome == "error", a.outcome)
    check("clean trace is a stop", b.outcome == "stop", b.outcome)
    check("model read from gen_ai.request.model", a.model == "model-x", a.model)
    check("project read from service.name", a.project == "demo-agent", a.project)
    check("tool spans are found (nested under agent/chat)",
          [s.tool for s in a.steps] == ["search", "read"], str([s.tool for s in a.steps]))
    check("EDGES: arguments decoded to dicts",
          a.steps[0].args == {"query": "alpha"} and a.steps[1].args == {"path": "/tmp/x"},
          str([s.args for s in a.steps]))
    check("EDGES: error attributed to the failing call only",
          a.steps[1].error is not None and a.steps[0].error is None,
          f"{a.steps[0].error} / {a.steps[1].error}")
    check("EDGES: repeated identical calls are NOT collapsed",
          [s.tool for s in b.steps] == ["search", "search"], str([s.tool for s in b.steps]))
    check("EDGES: both repeats keep their args",
          len(b.steps) == 2 and all(s.args == {"query": "beta"} for s in b.steps))
    check("EDGES: repeats are distinct objects, not one shared step",
          b.steps[0] is not b.steps[1])


def test_autogen() -> None:
    print("AutoGen")
    runs = load_autogen(f"{FIX}/autogen_chat.jsonl")
    check("two histories -> two runs", len(runs) == 2, str(len(runs)))
    if len(runs) != 2:
        return
    v2, v4 = runs
    check("v0.2 stop_reason read from the TOP level", v2.outcome == "error",
          f"outcome={v2.outcome}")
    check("v0.4 TaskResult stop_reason read", v4.outcome == "stop", v4.outcome)
    check("PAIRING: v0.2 error attributed to `read`, not `search`",
          v2.steps[0].error is None and v2.steps[1].error is not None,
          f"search={v2.steps[0].error} read={v2.steps[1].error}")
    check("v0.2 args decoded", v2.steps[0].args == {"query": "gamma"}, str(v2.steps[0].args))
    check("v0.4 typed events -> steps", [s.tool for s in v4.steps] == ["search", "write"],
          str([s.tool for s in v4.steps]))
    check("v0.4 typed-event args decoded",
          v4.steps[1].args == {"path": "/tmp/z", "body": "hi"}, str(v4.steps[1].args))
    check("v0.4 no false errors", all(s.error is None for s in v4.steps))


def test_crewai() -> None:
    print("CrewAI")
    runs = load_crewai(f"{FIX}/crewai_output.json")
    check("one crew -> one run", len(runs) == 1, str(len(runs)))
    if not runs:
        return
    r = runs[0]
    check("task tool calls become steps in order",
          [s.tool for s in r.steps] == ["search", "fetch", "write"], str([s.tool for s in r.steps]))
    check("EDGES: tool_input preserved",
          r.steps[0].args == {"query": "epsilon"} and r.steps[2].args == {"path": "/tmp/out.md", "body": "s"},
          str([s.args for s in r.steps]))
    check("crew name becomes project", r.project == "demo-crew", r.project)


def test_round_trip_through_canonical() -> None:
    print("round-trip: every format -> canonical -> back")
    for name in ("otel_genai.json", "autogen_chat.jsonl", "crewai_output.json"):
        src = f"{FIX}/{name}"
        runs = load_any(src)
        fd, tmp = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            write_canonical(runs, tmp)
            back = load_canonical(tmp)
            same_tools = [[s.tool for s in r.steps] for r in runs] == \
                         [[s.tool for s in r.steps] for r in back]
            same_args = [[s.args for s in r.steps] for r in runs] == \
                        [[s.args for s in r.steps] for r in back]
            same_out = [r.outcome for r in runs] == [r.outcome for r in back]
            check(f"{name}: steps survive the round-trip", same_tools)
            check(f"{name}: EDGES (args) survive the round-trip", same_args)
            check(f"{name}: outcomes survive the round-trip", same_out)
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    print("=" * 70)
    print("test_ingest_more")
    print("=" * 70)
    test_detection()
    test_otel()
    test_autogen()
    test_crewai()
    test_round_trip_through_canonical()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
