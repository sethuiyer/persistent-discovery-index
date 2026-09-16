#!/usr/bin/env python3
"""
test_ingest_cli.py — CLI agent stores: Claude Code, Codex, OpenCode, Antigravity.

Confidence is stated honestly and tested at the level it is claimed:

  * claude / codex / opencode — written to a LIVE CAPTURE on disk; these tests
    build schema-accurate fixtures and, when a live store is present, also load it.
  * antigravity — INFERRED. SQLite + protobuf blobs with no public schema; the
    loader recovers (call_id, tool, JSON args) by scanning length-delimited
    fields. Tested as a heuristic, not as a specification.

Run: python3 test_ingest_cli.py     (exit 0 on success)
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys
import tempfile

from ingest import (ANTIGRAVITY, CLAUDE, CODEX, OPENCODE, detect_format,
                    load_antigravity, load_claude, load_codex, load_opencode)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def tmp(suffix: str) -> str:
    fd, p = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return p


def write_lines(records) -> str:
    p = tmp(".jsonl")
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


# ---- protobuf helpers for the antigravity fixture -------------------------
def _vi(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | 0x80 if n else b)
        if not n:
            return bytes(out)


def _bf(fn: int, payload: bytes) -> bytes:
    return _vi((fn << 3) | 2) + _vi(len(payload)) + payload


# ---- fixtures -------------------------------------------------------------
def claude_lines():
    base = {"sessionId": "s1", "cwd": "/repo", "uuid": "u0", "parentUuid": None,
            "isSidechain": False, "version": "1"}
    return [
        {"operation": "enqueue", "sessionId": "s1", "timestamp": "t", "type": "queue-operation"},
        {**base, "type": "user", "message": {"role": "user", "content": "fix the failing test"}},
        {**base, "type": "assistant",
         "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "c1",
                                                       "name": "Bash", "input": {"command": "pytest"}}]}},
        {**base, "type": "user",
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1",
                                                  "is_error": True, "content": "1 failed"}]}},
        {**base, "type": "assistant", "message": {"role": "assistant",
                                                  "content": [{"type": "text", "text": "done"}]}},
        # meta messages are not turns
        {**base, "type": "user", "message": {"role": "user", "content": "<command-name>/model</command-name>"}},
        # a sidechain (subagent) record must be skipped
        {**base, "isSidechain": True, "type": "assistant",
         "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "c9",
                                                       "name": "Read", "input": {"file_path": "/x"}}]}},
        {**base, "type": "user", "message": {"role": "user", "content": "now explain it"}},
        {**base, "type": "assistant", "message": {"role": "assistant",
                                                  "content": [{"type": "text", "text": "explained"}]}},
    ]


def test_claude() -> None:
    print("claude (Claude Code transcript JSONL)")
    p = write_lines(claude_lines())
    check("detects as claude", detect_format(p) == CLAUDE, detect_format(p))
    runs = load_claude(p)
    check("two real turns (meta + sidechain excluded)", len(runs) == 2, f"got {len(runs)}")
    if len(runs) != 2:
        return
    a, b = runs
    check("run 1 has the Bash step", [s.tool for s in a.steps] == ["bash"], str([s.tool for s in a.steps]))
    check("tool error is attached to the step", a.steps[0].error is not None and "failed" in a.steps[0].error)
    check("its prompt is the real user text", a.prompt == "fix the failing test", a.prompt)
    check("run 1 ended with assistant text -> stop", a.outcome == "stop", a.outcome)
    check("run 2 is a zero-tool turn", b.steps == [] and b.prompt == "now explain it", str(b.steps))
    check("sidechain Read was skipped",
          all(s.tool != "read" for r in runs for s in r.steps))


def codex_lines():
    return [
        {"timestamp": "t", "ordinal": 0, "type": "session_meta",
         "payload": {"id": "x1", "cwd": "/repo", "model_provider": "openai"}},
        {"timestamp": "t", "ordinal": 1, "type": "response_item",
         "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "write the patch"}]}},
        {"timestamp": "t", "ordinal": 2, "type": "response_item",
         "payload": {"type": "custom_tool_call", "call_id": "k1", "name": "exec",
                     "input": "const r = await tools.exec_command({\"cmd\":\"pwd && ls\",\"workdir\":\"/repo\"});"}},
        {"timestamp": "t", "ordinal": 3, "type": "response_item",
         "payload": {"type": "custom_tool_call_output", "call_id": "k1",
                     "output": [{"type": "input_text", "text": "Script completed\nWall time 0.1"}]}},
    ]


def test_codex() -> None:
    print("codex (rollout JSONL)")
    p = write_lines(codex_lines())
    check("detects as codex", detect_format(p) == CODEX, detect_format(p))
    runs = load_codex(p)
    check("one run", len(runs) == 1, f"got {len(runs)}")
    if len(runs) != 1:
        return
    r = runs[0]
    check("one step named exec", [s.tool for s in r.steps] == ["exec"], str([s.tool for s in r.steps]))
    check("JS-wrapped JSON args were brace-extracted", r.steps[0].args.get("cmd") == "pwd && ls", str(r.steps[0].args))
    check("prompt captured", r.prompt == "write the patch", r.prompt)
    check("project from session_meta cwd", r.project == "/repo", r.project)


def build_opencode_db() -> str:
    p = tmp(".db")
    con = sqlite3.connect(p)
    con.execute("create table session (id text, model text)")
    con.execute("create table message (id text, data text)")
    con.execute("create table part (id text, message_id text, session_id text, time_created int, data text)")
    con.execute("insert into session values ('ses_1','claude-sonnet')")
    def part(i, mid, typ, **kw):
        con.execute("insert into part values (?,?,?,?,?)",
                    (f"p{i}", mid, "ses_1", i, json.dumps({"type": typ, **kw})))
    con.execute("insert into message values ('m1', ?)", (json.dumps({"role": "user"}),))
    con.execute("insert into message values ('m2', ?)", (json.dumps({"role": "assistant"}),))
    part(1, "m1", "text", text="fix the build")
    part(2, "m2", "tool", tool="bash", callID="c1",
         state={"input": {"command": "make"}, "status": "completed", "output": "ok"})
    part(3, "m2", "tool", tool="read", callID="c2",
         state={"input": {"file_path": "/x.py"}, "status": "error", "output": "ENOENT"})
    con.commit()
    con.close()
    return p


def test_opencode() -> None:
    print("opencode (SQLite part.data JSON)")
    p = build_opencode_db()
    check("detects as opencode", detect_format(p) == OPENCODE, detect_format(p))
    runs = load_opencode(p)
    check("one run", len(runs) == 1, f"got {len(runs)}")
    if len(runs) != 1:
        return
    r = runs[0]
    check("two tool steps", [s.tool for s in r.steps] == ["bash", "read"], str([s.tool for s in r.steps]))
    check("bash args preserved", r.steps[0].args.get("command") == "make", str(r.steps[0].args))
    check("errored tool carries its error", r.steps[1].error and "ENOENT" in r.steps[1].error)
    check("user prompt captured", r.prompt == "fix the build", r.prompt)


def build_antigravity_db() -> str:
    p = tmp(".db")
    con = sqlite3.connect(p)
    con.execute("create table steps (idx integer, step_type integer, step_payload blob)")
    sub = _bf(1, b"call_zzz") + _bf(2, b"run_command") + _bf(3, b'{"CommandLine":"echo hi"}')
    con.execute("insert into steps values (2, 132, ?)", (_bf(5, sub),))
    con.commit()
    con.close()
    return p


def test_antigravity() -> None:
    print("antigravity (SQLite + protobuf scan; INFERRED)")
    p = build_antigravity_db()
    check("detects as antigravity", detect_format(p) == ANTIGRAVITY, detect_format(p))
    runs = load_antigravity(p)
    check("one run (boundaries not recoverable)", len(runs) == 1, f"got {len(runs)}")
    if len(runs) != 1:
        return
    r = runs[0]
    check("tool call recovered from the blob", [s.tool for s in r.steps] == ["run_command"],
          str([s.tool for s in r.steps]))
    check("JSON args recovered", r.steps[0].args.get("CommandLine") == "echo hi", str(r.steps[0].args))


# ---- live captures (skip when absent) -------------------------------------
def test_live() -> None:
    print("live captures on disk (skipped when absent)")
    cdir = os.path.expanduser("~/.claude/projects")
    if os.path.isdir(cdir):
        f = None
        for q in glob.glob(f"{cdir}/*/*.jsonl"):
            if os.path.basename(q).startswith("agent-"):
                continue
            if '"tool_use"' in open(q, errors="ignore").read():
                f = q
                break
        if f:
            runs = load_claude(f)
            check("live claude session loads runs with steps",
                  len(runs) > 0 and sum(len(r.steps) for r in runs) > 0,
                  f"{len(runs)} runs")
        else:
            print("  SKIP  no claude session with tools")
    else:
        print("  SKIP  no ~/.claude")
    adir = os.path.expanduser("~/.gemini/antigravity-cli/conversations")
    dbs = glob.glob(f"{adir}/*.db") if os.path.isdir(adir) else []
    if dbs:
        runs = load_antigravity(dbs[-1])
        check("live antigravity db yields tool steps",
              runs and len(runs[0].steps) > 0, str(len(runs)))
    else:
        print("  SKIP  no antigravity db")


if __name__ == "__main__":
    print("=" * 70)
    print("test_ingest_cli")
    print("=" * 70)
    test_claude()
    test_codex()
    test_opencode()
    test_antigravity()
    test_live()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
