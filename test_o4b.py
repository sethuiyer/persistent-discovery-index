#!/usr/bin/env python3
"""
test_o4b.py — the O4b *protocol* contract: the preconditions, not the result.

These fixtures discharge nothing about usefulness. They check that the harness
(a) refuses ill-formed label data, (b) reports coverage separately, (c) requires a
frozen evaluator and matched tasks, and (d) splits by task cluster. A green run is
a licence to run the O4b experiment, not evidence for it.

Run: python3 test_o4b.py     (exit 0 on success)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from adapters import Evaluator, Step, Turn as Run
from ingest import load_canonical, to_canonical
from o4b import (ProtocolError, coverage_report, evaluators, labelled, matched_tasks,
                 report, require_matched, require_single_evaluator, task_split)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def R(agent: str, task: str, label=None, ev=None) -> Run:
    return Run(steps=[Step("read", {"path": "a.py"})], outcome="stop", model=agent,
               prompt=task, verified_outcome=label, evaluator=ev)


EV = Evaluator("judge", "1.0", "rubric")


def test_schema_validation() -> None:
    print("independent-label schema (make illegal states unrepresentable)")
    try:
        R("A", "t1", "maybe", EV)
        check("illegal verified_outcome is rejected", False, "no error raised")
    except ValueError:
        check("illegal verified_outcome is rejected", True)
    try:
        R("A", "t1", "success", None)
        check("label without evaluator provenance is rejected", False, "no error raised")
    except ValueError:
        check("label without evaluator provenance is rejected", True)
    check("unknown is not a label", R("A", "t1", "unknown", EV).labelled is False)
    check("success is a label", R("A", "t1", "success", EV).labelled is True)
    check("unevaluated is not a label", R("A", "t1", None, None).labelled is False)


def test_round_trip() -> None:
    print("canonical round-trip keeps the label and its provenance")
    r = R("A", "t1", "failure", Evaluator("judge", "2.0", "unit-tests"))
    d = to_canonical(r)
    check("verified_outcome serialised", d.get("verified_outcome") == "failure", str(d))
    check("evaluator serialised", d.get("evaluator", {}).get("id") == "judge", str(d.get("evaluator")))
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(d) + "\n")
    back = load_canonical(path)[0]
    check("round-trip label", back.verified_outcome == "failure")
    check("round-trip provenance", str(back.evaluator) == "judge@2.0 [unit-tests]",
          str(back.evaluator))
    check("unevaluated run omits the fields",
          "verified_outcome" not in to_canonical(R("A", "t1")))


def test_coverage() -> None:
    print("coverage is reported; unknown is not failure")
    runs = [R("A", "t1", "success", EV), R("A", "t1", "failure", EV),
            R("A", "t2", "unknown", EV), R("A", "t2", None, None)]
    cov = coverage_report(runs)
    check("success/failure/unknown/unevaluated counted separately",
          (cov["success"], cov["failure"], cov["unknown"], cov["unevaluated"]) == (1, 1, 1, 1),
          str(cov))
    check("labelled cohort excludes unknown and unevaluated", len(labelled(runs)) == 2)
    check("coverage fraction", cov["coverage"] == 0.5, str(cov["coverage"]))


def test_evaluator_freeze() -> None:
    print("the evaluator must be frozen across a comparison")
    one = [R("A", "t1", "success", EV), R("B", "t1", "failure", EV)]
    check("single evaluator accepted", require_single_evaluator(one) == "judge@1.0 [rubric]")
    check("evaluators() lists it once", evaluators(one) == {"judge@1.0 [rubric]"})
    two = one + [R("C", "t1", "success", Evaluator("other", "9", "human"))]
    try:
        require_single_evaluator(two)
        check("two evaluators rejected", False, "no error raised")
    except ProtocolError:
        check("two evaluators rejected", True)
    try:
        require_single_evaluator([R("A", "t1")])
        check("no evaluator at all rejected", False, "no error raised")
    except ProtocolError:
        check("no evaluator at all rejected", True)


def test_matching() -> None:
    print("a comparison requires matched tasks")
    runs = [R("A", "t1", "success", EV), R("B", "t1", "failure", EV),
            R("A", "t2", "success", EV)]
    table = matched_tasks(runs)
    check("task table maps tasks to agents", table["t1"] == {"A", "B"}, str(table))
    check("require_matched returns shared tasks", set(require_matched(runs)) == {"t1"})
    single = [R("A", "t1", "success", EV), R("A", "t2", "failure", EV)]
    try:
        require_matched(single)
        check("single-agent comparison rejected", False, "no error raised")
    except ProtocolError:
        check("single-agent comparison rejected", True)


def test_task_split() -> None:
    print("task-cluster split: deterministic, disjoint")
    runs = [R("A", f"t{i}", "success", EV) for i in range(6)]
    train, held = task_split(runs, heldout_frac=0.5, seed=0)
    tr_tasks = {r.prompt for r in train}
    he_tasks = {r.prompt for r in held}
    check("splits are disjoint by task", not (tr_tasks & he_tasks), f"{tr_tasks} vs {he_tasks}")
    check("every task is on exactly one side", tr_tasks | he_tasks == {f"t{i}" for i in range(6)})
    t2, h2 = task_split(runs, heldout_frac=0.5, seed=0)
    check("deterministic for a fixed seed", {r.prompt for r in t2} == tr_tasks
          and {r.prompt for r in h2} == he_tasks)
    check("held-out is non-empty", len(held) > 0 and len(train) > 0)


def test_report_makes_no_claim() -> None:
    print("the report verifies the protocol only")
    runs = [R("A", "t1", "success", EV), R("B", "t1", "failure", EV),
            R("A", "t2", "success", EV), R("B", "t2", "unknown", EV)]
    rep = report(runs)
    check("status says O4b is not evaluated", "NOT evaluated" in rep["status"], rep["status"])
    check("usefulness is explicitly None", rep["usefulness"] is None)
    check("evaluator recorded", rep["evaluator"] == "judge@1.0 [rubric]")
    check("matched task count reported", rep["matched_tasks"] == 1, str(rep.get("matched_tasks")))
    check("unknown label removes its task from the matched set (t2 loses B)",
          rep["matched_tasks"] == 1)
    full = [R("A", "t1", "success", EV), R("B", "t1", "failure", EV),
            R("A", "t2", "success", EV), R("B", "t2", "failure", EV)]
    check("labelling B on t2 restores the second matched task",
          report(full)["matched_tasks"] == 2)
    check("split reported", "split" in rep and rep["split"]["heldout_tasks"] >= 1, str(rep.get("split")))
    bad = report([R("A", "t1", "success", EV), R("A", "t2", "success", EV)])
    check("unmatched comparison surfaces a protocol error",
          "protocol_error" in bad and "matched" in bad["protocol_error"], str(bad))


if __name__ == "__main__":
    print("=" * 70)
    print("test_o4b")
    print("=" * 70)
    test_schema_validation()
    test_round_trip()
    test_coverage()
    test_evaluator_freeze()
    test_matching()
    test_task_split()
    test_report_makes_no_claim()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
