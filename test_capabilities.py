#!/usr/bin/env python3
"""
test_capabilities.py — input warrants: what each loader's records actually support.

Parsing N steps is not the same as warranting a comparison. These tests check
that (a) the four capability states are distinct and ordered, (b) every loader
declares a complete matrix, (c) analyses are REFUSED when the input does not
warrant them, and (d) no CLI loader fabricates a terminal outcome (`Stopped =
success` must not reappear under another name).

Run: python3 test_capabilities.py     (exit 0 on success)
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile

from ingest import (ANTIGRAVITY, CAP_RANK, CAPABILITIES, CLAUDE, CODEX, FORMATS,
                    INFERRED, OPENCODE, PI, SEMANTICS, SUPPORTED, UNAVAILABLE, UNKNOWN,
                    CapabilityError, capability_table, capabilities_of,
                    load_antigravity, load_codex, reconcile_capabilities,
                    require_capabilities)

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def refused(fmts, analysis) -> str:
    try:
        require_capabilities(fmts, analysis)
        return ""
    except CapabilityError as e:
        return str(e)


def test_states() -> None:
    print("the four states are distinct and ordered")
    check("supported is strongest", CAP_RANK[SUPPORTED] > CAP_RANK[INFERRED] > CAP_RANK[UNKNOWN] > CAP_RANK[UNAVAILABLE])
    check("unknown and unavailable are different claims", UNKNOWN != UNAVAILABLE
          and CAP_RANK[UNKNOWN] != CAP_RANK[UNAVAILABLE])


def test_matrix_complete() -> None:
    print("every loader declares a complete matrix")
    check("every format has capabilities", set(CAPABILITIES) == set(FORMATS),
          str(set(FORMATS) - set(CAPABILITIES)))
    for f in FORMATS:
        c = capabilities_of(f)
        check(f"{f}: all semantics present", set(c) == set(SEMANTICS), str(set(SEMANTICS) - set(c)))
    check("table renders every format", all(f in capability_table() for f in FORMATS))


def test_values_are_what_we_built() -> None:
    print("values match what each loader actually populates")
    oc = capabilities_of(OPENCODE)
    check("opencode carries cost + tokens", oc["cost"] == SUPPORTED and oc["tokens"] == SUPPORTED)
    check("only pi, opencode and canonical claim cost",
          {f for f in FORMATS if capabilities_of(f)["cost"] == SUPPORTED} == {PI, OPENCODE, "canonical"})
    check("pi carries real usage cost + tokens",
          capabilities_of(PI)["cost"] == SUPPORTED and capabilities_of(PI)["tokens"] == SUPPORTED)
    check("canonical carries cost/tokens as a passthrough",
          capabilities_of("canonical")["cost"] == SUPPORTED
          and capabilities_of("canonical")["tokens"] == SUPPORTED)
    check("terminal_outcome and verified_outcome are separate dimensions",
          "terminal_outcome" in SEMANTICS and "verified_outcome" in SEMANTICS)
    check("canonical terminal_outcome supported",
          capabilities_of("canonical")["terminal_outcome"] == SUPPORTED)
    check("claude terminal_outcome inferred (derived from the transcript)",
          capabilities_of(CLAUDE)["terminal_outcome"] == INFERRED)
    check("codex/opencode terminal_outcome unknown (field exists, mapping unvalidated)",
          capabilities_of(CODEX)["terminal_outcome"] == UNKNOWN
          and capabilities_of(OPENCODE)["terminal_outcome"] == UNKNOWN)
    check("antigravity terminal_outcome unavailable",
          capabilities_of(ANTIGRAVITY)["terminal_outcome"] == UNAVAILABLE)
    check("no CLI loader claims verified_outcome",
          all(capabilities_of(f)["verified_outcome"] != SUPPORTED
              for f in (CLAUDE, CODEX, OPENCODE, ANTIGRAVITY)))
    check("canonical passes verified_outcome through", capabilities_of("canonical")["verified_outcome"] == SUPPORTED)
    check("antigravity steps are inferred, not supported", capabilities_of(ANTIGRAVITY)["steps"] == INFERRED)
    check("antigravity run boundaries unavailable",
          capabilities_of(ANTIGRAVITY)["run_boundaries"] == UNAVAILABLE)
    check("codex tool errors are inferred (heuristic)", capabilities_of(CODEX)["tool_errors"] == INFERRED)


def test_antigravity_refused_for_run_level() -> None:
    print("antigravity is refused for run-level claims")
    check("steps-only exploration is allowed", require_capabilities([ANTIGRAVITY], "steps_only")
          == capabilities_of(ANTIGRAVITY))
    msg = refused([ANTIGRAVITY], "run_profile")
    check("run_profile is refused", bool(msg))
    check("message shows the refusal and the requirement", "Analysis refused" in msg
          and "Requires:" in msg and "Input:" in msg, msg)
    check("message names the missing run-level warrant", "run_boundaries" in msg)
    check("message states no run-level claim is warranted", "No run-level claim" in msg, msg)
    check("agent_comparison is also refused", bool(refused([ANTIGRAVITY], "agent_comparison")))


def test_supported_formats_pass() -> None:
    print("live-capture formats pass the analyses they warrant")
    check("claude: run_profile allowed", bool(require_capabilities([CLAUDE], "run_profile")))
    check("claude: agent_comparison allowed", bool(require_capabilities([CLAUDE], "agent_comparison")))
    check("opencode: agent_comparison allowed", bool(require_capabilities([OPENCODE], "agent_comparison")))


def test_o4b_gate() -> None:
    print("O4b gate: canonical can warrant it once it carries labels + cost")
    for f in FORMATS:
        if f == "canonical":
            check("canonical: o4b_cost allowed (passthrough of labels + cost)",
                  bool(require_capabilities([f], "o4b_cost")))
        else:
            check(f"{f}: o4b_cost refused", bool(refused([f], "o4b_cost")))
    msg = refused([OPENCODE], "o4b_cost")
    check("opencode refusal names verified_outcome (it has cost, not labels)",
          "verified_outcome" in msg, msg)
    msg2 = refused([CLAUDE], "o4b_cost")
    check("claude refusal names verified_outcome and cost",
          "verified_outcome" in msg2 and "cost" in msg2, msg2)


def test_reconcile_is_the_meet() -> None:
    print("mixing formats takes the weakest state per semantic")
    mix = reconcile_capabilities([CLAUDE, ANTIGRAVITY])
    check("steps become inferred", mix["steps"] == INFERRED, mix["steps"])
    check("run_boundaries become unavailable", mix["run_boundaries"] == UNAVAILABLE)
    check("string input is accepted as one format",
          require_capabilities(CLAUDE, "run_profile")["steps"] == SUPPORTED)


# ---- no fabricated terminal outcome ---------------------------------------
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


def _antigravity_db() -> str:
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(p)
    con.execute("create table steps (idx integer, step_type integer, step_payload blob)")
    sub = _bf(1, b"call_zzz") + _bf(2, b"run_command") + _bf(3, b'{"CommandLine":"echo hi"}')
    con.execute("insert into steps values (2, 132, ?)", (_bf(5, sub),))
    con.commit()
    con.close()
    return p


def _codex_jsonl() -> str:
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"type": "session_meta", "payload": {"id": "x", "cwd": "/r"}}) + "\n")
        f.write(json.dumps({"type": "response_item",
                            "payload": {"type": "message", "role": "user",
                                        "content": [{"type": "input_text", "text": "hi"}]}}) + "\n")
        f.write(json.dumps({"type": "response_item",
                            "payload": {"type": "custom_tool_call", "call_id": "k",
                                        "name": "exec", "input": 'tools.exec_command({"cmd":"ls"})'}}) + "\n")
    return p


def test_no_fabricated_success() -> None:
    print("no CLI loader resurrects Stopped = success")
    for name, runs in (("codex", load_codex(_codex_jsonl())),
                       ("antigravity", load_antigravity(_antigravity_db()))):
        check(f"{name}: outcome is not 'stop'",
              all(r.outcome != "stop" for r in runs), str([r.outcome for r in runs]))
        check(f"{name}: no run reports succeeded", not any(r.succeeded for r in runs))


def test_live_refusal_demo() -> None:
    print("live: the profiler refuses an antigravity capture")
    import glob
    dbs = glob.glob(os.path.expanduser("~/.gemini/antigravity-cli/conversations/*.db"))
    if not dbs:
        print("  SKIP  no antigravity db")
        return
    r = subprocess.run([sys.executable, os.path.join(HERE, "pdi_profile.py"),
                        dbs[-1], "--group-by", "model", "--min", "1"],
                       capture_output=True, text=True)
    check("exit code is 2 (refused)", r.returncode == 2, str(r.returncode))
    check("stderr/stdout carries the refusal", "Analysis refused" in (r.stdout + r.stderr))


if __name__ == "__main__":
    print("=" * 70)
    print("test_capabilities")
    print("=" * 70)
    test_states()
    test_matrix_complete()
    test_values_are_what_we_built()
    test_antigravity_refused_for_run_level()
    test_supported_formats_pass()
    test_o4b_gate()
    test_reconcile_is_the_meet()
    test_no_fabricated_success()
    test_live_refusal_demo()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
