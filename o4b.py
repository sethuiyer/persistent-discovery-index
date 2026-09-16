#!/usr/bin/env python3
"""
o4b.py — the O4b evaluation harness: protocol, not results.

O4b asks whether PDI's diagnoses reduce cost at **preserved task quality**. That is
an experiment on real, independently evaluated, matched-task data
(`O4_SCOPE.md` §5). This module only enforces the conditions under which such an
experiment is admissible. **It computes no usefulness claim.**

It checks:
  * every considered run carries an independent success label and its provenance;
  * `unknown` is excluded from the labelled cohort, never folded into failure;
  * label coverage is reported, not assumed;
  * a comparison is **matched**: candidate agents share tasks;
  * a deterministic **task-cluster** split keeps every task on one side only;
  * the evaluator's identity/version is frozen across a comparison.

Everything here is a precondition. A passing report is a licence to run the
experiment, not evidence for it. If a report says the protocol holds, O4b is still
open.

Stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable, Optional, Sequence

LABELS = ("success", "failure")


class ProtocolError(ValueError):
    """A precondition for the O4b experiment is not met."""


# --------------------------------------------------------------------------
# cohort and coverage — unknown is not failure
# --------------------------------------------------------------------------
def labelled(runs: Sequence[Any]) -> list:
    """Runs with a verified success/failure label. `unknown` is excluded."""
    return [r for r in runs if getattr(r, "verified_outcome", None) in LABELS]


def coverage_report(runs: Sequence[Any]) -> dict:
    n = len(runs)
    succ = sum(1 for r in runs if getattr(r, "verified_outcome", None) == "success")
    fail = sum(1 for r in runs if getattr(r, "verified_outcome", None) == "failure")
    unk = sum(1 for r in runs if getattr(r, "verified_outcome", None) == "unknown")
    unevaluated = n - succ - fail - unk
    return {"n": n, "success": succ, "failure": fail, "unknown": unk,
            "unevaluated": unevaluated, "labelled": succ + fail,
            "coverage": ((succ + fail) / n) if n else 0.0}


# --------------------------------------------------------------------------
# the evaluator must be frozen
# --------------------------------------------------------------------------
def evaluators(runs: Sequence[Any]) -> set:
    return {str(r.evaluator) for r in labelled(runs) if getattr(r, "evaluator", None)}


def require_single_evaluator(runs: Sequence[Any]) -> str:
    evs = evaluators(runs)
    if len(evs) == 0:
        raise ProtocolError("no labelled run carries evaluator provenance")
    if len(evs) > 1:
        raise ProtocolError(
            f"more than one evaluator across the comparison: {sorted(evs)}; "
            "freeze evaluator identity/version before comparing")
    return next(iter(evs))


# --------------------------------------------------------------------------
# matching — agents must share tasks
# --------------------------------------------------------------------------
def task_of(run: Any) -> str:
    return getattr(run, "prompt", "") or ""


def agent_of(run: Any) -> str:
    return getattr(run, "model", "unknown")


def matched_tasks(runs: Sequence[Any]) -> dict[str, set]:
    """task -> set of agents that ran it (on the labelled cohort)."""
    out: dict[str, set] = {}
    for r in labelled(runs):
        out.setdefault(task_of(r), set()).add(agent_of(r))
    return out


def require_matched(runs: Sequence[Any], min_agents: int = 2, min_tasks: int = 1) -> dict[str, set]:
    """Every comparison needs tasks run by more than one agent (O4_SCOPE §5)."""
    table = matched_tasks(runs)
    shared = {t: a for t, a in table.items() if len(a) >= min_agents}
    if len(shared) < min_tasks:
        raise ProtocolError(
            f"no matched tasks: {len(shared)} task(s) run by >= {min_agents} agents "
            f"(need >= {min_tasks}); matched tasks are required for agent comparison")
    return shared


# --------------------------------------------------------------------------
# deterministic, task-cluster split — a task is on exactly one side
# --------------------------------------------------------------------------
def task_split(runs: Sequence[Any], heldout_frac: float = 0.5,
               seed: int = 0) -> tuple[list, list]:
    """Split by TASK, not by run, so no task appears in both sides."""
    import random
    pool = list(runs)
    tasks = sorted({task_of(r) for r in pool})
    rng = random.Random(seed)
    rng.shuffle(tasks)
    k = max(1, int(round(len(tasks) * heldout_frac))) if tasks else 0
    hold = set(tasks[:k])
    train = [r for r in pool if task_of(r) not in hold]
    held = [r for r in pool if task_of(r) in hold]
    return train, held


def require_disjoint(train: Sequence[Any], held: Sequence[Any]) -> None:
    overlap = {task_of(r) for r in train} & {task_of(r) for r in held}
    if overlap:
        raise ProtocolError(f"task appears in both splits: {sorted(overlap)}")


# --------------------------------------------------------------------------
def report(runs: Sequence[Any], fmt: Optional[str] = None) -> dict:
    """Preconditions only. No usefulness claim is computed or implied here."""
    from ingest import capabilities_of
    cov = coverage_report(runs)
    out: dict = {"coverage": cov, "status": "preconditions only; O4b NOT evaluated",
                 "usefulness": None}
    if fmt:
        out["capabilities"] = capabilities_of(fmt)
    try:
        out["evaluator"] = require_single_evaluator(runs)
    except ProtocolError as e:
        out["evaluator"] = None
        out["protocol_error"] = str(e)
        return out
    try:
        shared = require_matched(runs)
        out["matched_tasks"] = len(shared)
        train, held = task_split(labelled(runs))
        require_disjoint(train, held)
        out["split"] = {"train_runs": len(train), "heldout_runs": len(held),
                        "train_tasks": len({task_of(r) for r in train}),
                        "heldout_tasks": len({task_of(r) for r in held})}
    except ProtocolError as e:
        out["protocol_error"] = str(e)
    return out


def main() -> None:
    from ingest import CapabilityError, detect_format, load_any, require_capabilities
    if len(sys.argv) < 2:
        print("usage: python3 o4b.py <labelled-traces>")
        raise SystemExit(2)
    path = sys.argv[1]
    fmt = detect_format(path) if os.path.isfile(path) else None
    # Executable input warrant: refuse the experiment if the capture cannot
    # warrant it (O4_SCOPE.md §5).
    if fmt:
        try:
            require_capabilities([fmt], "o4b_cost")
        except CapabilityError as e:
            print(f"\n[input: {fmt}]")
            print(str(e))
            print("\nO4b remains OPEN. This capture cannot warrant the cost claim.")
            raise SystemExit(2)
    runs = load_any(path)
    print(json.dumps(report(runs, fmt), indent=2))
    print("\nNOTE: this report verifies the protocol only. O4b (cost reduction at "
          "preserved quality) is NOT evaluated and remains open.")


if __name__ == "__main__":
    main()
