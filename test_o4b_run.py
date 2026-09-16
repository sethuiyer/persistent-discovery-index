#!/usr/bin/env python3
"""
test_o4b_run.py — gate: the committed runner persists a readable trace end to end.

Runs `o4b_run.run_one` against a FAKE `pi` on PATH (no paid agent, no network). It
checks the full path: fresh mutated tree -> RPC until agent_settled -> session
usage -> TRACE COPIED OUT -> verifier -> workdir cleaned. The point is that a
recorded trace must outlive the workdir and still be readable.

Run: python3 test_o4b_run.py     (exit 0 on success)
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o4b_run                                                    # noqa: E402
from adapters import load_pi_session                              # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


FAKE_PI = '''#!/usr/bin/env python3
import sys, os, json
args = sys.argv[1:]
sdir = None
for i, a in enumerate(args):
    if a == "--session-dir" and i + 1 < len(args):
        sdir = args[i + 1]
sys.stdin.readline()
os.makedirs(sdir, exist_ok=True)
with open(os.path.join(sdir, "fake.jsonl"), "w") as f:
    f.write(json.dumps({"type": "session", "cwd": os.getcwd()}) + "\\n")
    f.write(json.dumps({"type": "message", "message": {
        "role": "user", "content": [{"type": "text", "text": "x"}]}}) + "\\n")
    f.write(json.dumps({"type": "message", "message": {
        "role": "assistant", "stopReason": "stop",
        "content": [{"type": "toolCall", "id": "c1", "name": "bash",
                     "arguments": {"command": "true"}},
                    {"type": "text", "text": "done"}],
        "usage": {"input": 20, "output": 3, "cost": {"total": 0.05}}}}) + "\\n")
print(json.dumps({"type": "agent_settled"}), flush=True)
'''


def main() -> int:
    bindir = tempfile.mkdtemp(prefix="fakepi_")
    pi = os.path.join(bindir, "pi")
    with open(pi, "w") as f:
        f.write(FAKE_PI)
    os.chmod(pi, 0o755)
    os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")

    # keep the test out of the repo's run store
    o4b_run.RUNS = tempfile.mkdtemp(prefix="o4b_runs_")

    corpus = o4b_run.load_corpus()
    disc = [t for t in corpus["tasks"] if t["split"] == "discovery"]
    task = disc[0]
    pristine = tempfile.mkdtemp(prefix="o4b_pristine_")
    o4b_run.agent_snapshot(pristine)

    before = set(glob.glob("/tmp/o4b_run_*"))
    rec = o4b_run.run_one(task, 1, pristine, "pi", "deepseek-flash", 30)
    after = set(glob.glob("/tmp/o4b_run_*"))

    trace = os.path.join(o4b_run.HERE, rec["trace"]) if rec.get("trace") else None
    turns = load_pi_session(trace) if trace and os.path.exists(trace) else []
    print("record:", {k: rec.get(k) for k in
                      ("status", "regeneration_ok", "agent_status", "verified_outcome",
                       "cost", "tokens_input", "trace")})
    check("run status ok", rec["status"] == "ok", rec.get("error", ""))
    check("regeneration matched the sealed corpus", rec["regeneration_ok"])
    check("agent reached agent_settled", str(rec["agent_status"]) == "settled")
    check("trace was copied out of the workdir", bool(trace) and os.path.exists(trace),
          str(rec.get("trace")))
    check("trace is readable after cleanup", len(turns) >= 1, f"turns={len(turns)}")
    check("cost captured from the session", rec["cost"] == 0.05, str(rec["cost"]))
    check("tokens captured from the session", (rec["tokens_input"], rec["tokens_output"]) == (20, 3))
    check("verifier outcome recorded", rec["verified_outcome"] in ("success", "failure", "unknown"))
    check("workdir was cleaned", after == before, f"{sorted(after - before)}")

    # a second run writes a distinct trace
    rec2 = o4b_run.run_one(task, 2, pristine, "pi", "deepseek-flash", 30)
    check("second run has its own trace file",
          rec2.get("trace") and rec2["trace"] != rec.get("trace"),
          f"{rec.get('trace')} vs {rec2.get('trace')}")

    shutil.rmtree(bindir, ignore_errors=True)
    shutil.rmtree(pristine, ignore_errors=True)
    print("=" * 70)
    print("ALL PASS" if not FAILS else f"FAILED: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
