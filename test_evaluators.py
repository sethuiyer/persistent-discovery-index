#!/usr/bin/env python3
"""
test_evaluators.py — independent outcome evaluation.

The load-bearing test is `test_separation`: a run whose terminal state is `stop`
must be able to receive `verified_outcome = failure`, and a run whose terminal
state is `error` must be able to receive `success`. If terminal state and verified
outcome can overwrite each other, `Stopped = success` has returned.

Run: python3 test_evaluators.py     (exit 0 on success)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from adapters import Evaluator, Step, Turn as Run
from evaluators import (EvaluationError, artifact, attach, command_exit, exact_match,
                        file_contains)
from ingest import to_canonical, load_canonical
from o4b import coverage_report

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def R(outcome="stop"):
    return Run(steps=[Step("bash", {"command": "ls"})], outcome=outcome, model="m",
               prompt="t", cost=0.01, tokens_input=10, tokens_output=5)


def test_command_exit() -> None:
    print("command_exit judges by exit status")
    check("exit 0 -> success", command_exit(["true"])[0] == "success")
    check("nonzero -> failure", command_exit(["false"])[0] == "failure")
    check("missing binary -> unknown, not failure", command_exit(["/no/such/bin"])[0] == "unknown")
    check("provenance records the exit status", "exit status" in str(command_exit(["true"])[1]))


def test_artifact() -> None:
    print("artifact judges by presence")
    fd, p = tempfile.mkstemp()
    os.close(fd)
    check("existing artifact required -> success", artifact(p)[0] == "success")
    check("missing artifact required -> failure", artifact(p + ".nope")[0] == "failure")
    check("absent-required when present -> failure", artifact(p, must_exist=False)[0] == "failure")
    check("absent-required when missing -> success", artifact(p + ".nope", must_exist=False)[0] == "success")


def test_file_contains() -> None:
    print("file_contains judges by content")
    fd, p = tempfile.mkstemp()
    open(p, "w").write("hello world")
    os.close(fd)
    check("marker present -> success", file_contains(p, "hello")[0] == "success")
    check("marker absent -> failure", file_contains(p, "goodbye")[0] == "failure")
    check("missing file -> failure (required artifact absent)", file_contains(p + ".x", "hello")[0] == "failure")


def test_exact_match() -> None:
    print("exact_match judges by answer equality")
    check("equal -> success", exact_match("42", "42")[0] == "success")
    check("different -> failure", exact_match("41", "42")[0] == "failure")
    check("whitespace normalised", exact_match("a  b", "a b")[0] == "success")
    check("no observed value -> unknown", exact_match(None, "42")[0] == "unknown")


def test_separation() -> None:
    print("terminal state and verified outcome are separate claims")
    stopped = attach([R("stop")], ("failure", Evaluator("x", "1", "forced")))[0]
    check("stopped run can be a verified FAILURE",
          stopped.outcome == "stop" and stopped.verified_outcome == "failure",
          f"{stopped.outcome}/{stopped.verified_outcome}")
    errored = attach([R("error")], ("success", Evaluator("x", "1", "forced")))[0]
    check("errored run can be a verified SUCCESS",
          errored.outcome == "error" and errored.verified_outcome == "success",
          f"{errored.outcome}/{errored.verified_outcome}")
    check("terminal_outcome is unchanged by evaluation", stopped.terminal_outcome == "stop")
    unk = attach([R("stop")], ("unknown", Evaluator("x", "1", "not verified")))[0]
    check("unknown is not a label", unk.labelled is False)
    check("unknown still carries provenance", unk.evaluator is not None)


def test_attach_preserves() -> None:
    print("attach preserves everything else")
    r = R("stop")
    g = attach([r], ("success", Evaluator("cmd", "1", "exit 0")))[0]
    check("steps preserved", [s.tool for s in g.steps] == ["bash"])
    check("cost/tokens preserved", (g.cost, g.tokens_input, g.tokens_output) == (0.01, 10, 5))
    check("provenance attached", str(g.evaluator) == "cmd@1 [exit 0]")
    try:
        attach([r], ("maybe", Evaluator("x")))
        check("bad outcome rejected", False, "no error raised")
    except EvaluationError:
        check("bad outcome rejected", True)


def test_canonical_round_trip() -> None:
    print("verified outcome survives the canonical boundary")
    g = attach([R("stop")], ("success", Evaluator("command_exit", "1", "exit 0")))[0]
    d = to_canonical(g)
    check("serialised label", d.get("verified_outcome") == "success", str(d))
    check("serialised provenance id", d.get("evaluator", {}).get("id") == "command_exit")
    check("serialised cost", d.get("cost") == 0.01, str(d.get("cost")))
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(d) + "\n")
    back = load_canonical(p)[0]
    check("round-trip label", back.verified_outcome == "success")
    check("round-trip cost", back.cost == 0.01)
    check("coverage counts the label", coverage_report([back])["labelled"] == 1)


def test_no_trajectory_reading() -> None:
    print("evaluators never read the trajectory")
    import inspect
    import evaluators
    for fn in (evaluators.command_exit, evaluators.artifact, evaluators.file_contains,
               evaluators.exact_match):
        src = inspect.getsource(fn)
        check(f"{fn.__name__} does not read .outcome", ".outcome" not in src)


if __name__ == "__main__":
    print("=" * 70)
    print("test_evaluators")
    print("=" * 70)
    test_command_exit()
    test_artifact()
    test_file_contains()
    test_exact_match()
    test_separation()
    test_attach_preserves()
    test_canonical_round_trip()
    test_no_trajectory_reading()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
