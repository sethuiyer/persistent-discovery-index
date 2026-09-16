#!/usr/bin/env python3
"""
evaluators.py — independent outcome evaluation, NOT outcome inference.

A loader recovers what the runtime observed (`Turn.terminal_outcome`). It must
never decide whether the *task* worked. An evaluator independently judges the
result against the world and attaches a label:

    verified_outcome = success | failure | unknown
    evaluator        = id / version / method   (the warrant for that label)

The witness is external to the trajectory: a command's exit status, a required
artifact, a file's contents, an exact answer. **No evaluator reads
`run.outcome`** — that route (`agent stopped` -> `task succeeded`) is closed by
construction, and there is a test for it.

`unknown` is a first-class result: when verification cannot be performed, the run
is labelled `unknown`, never `failure` and never `success`.

Stdlib only.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from typing import Any, Optional, Sequence

from adapters import Evaluator

METHOD = "external check, independent of the trajectory"


class EvaluationError(ValueError):
    """The evaluation could not be set up (bad configuration, not a task result)."""


# --------------------------------------------------------------------------
# evaluators -> (outcome, provenance)
# --------------------------------------------------------------------------
def command_exit(cmd: Any, cwd: Optional[str] = None,
                 timeout: int = 120) -> tuple[str, Evaluator]:
    """Run a command and judge by its exit status.

    exit 0 -> success; nonzero -> failure; could-not-run / timeout -> unknown.
    """
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=True,
                           shell=isinstance(cmd, str))
    except (OSError, subprocess.TimeoutExpired):
        return "unknown", Evaluator("command_exit", "1", f"{METHOD}; check did not run")
    ok = r.returncode == 0
    return ("success" if ok else "failure",
            Evaluator("command_exit", "1", f"{METHOD}; exit status {r.returncode}"))


def artifact(path: str, must_exist: bool = True) -> tuple[str, Evaluator]:
    """Judge by the presence/absence of a required artifact."""
    try:
        present = os.path.exists(path)
    except OSError:
        return "unknown", Evaluator("artifact", "1", f"{METHOD}; path not checkable")
    ok = present if must_exist else not present
    want = "exists" if must_exist else "absent"
    return ("success" if ok else "failure",
            Evaluator("artifact", "1", f"{METHOD}; required {want}: {path}"))


def file_contains(path: str, marker: str) -> tuple[str, Evaluator]:
    """Judge by whether a file contains a literal marker. A missing file fails."""
    if not os.path.exists(path):
        return "failure", Evaluator("file_contains", "1", f"{METHOD}; file missing: {path}")
    try:
        with open(path, errors="ignore") as f:
            found = marker in f.read()
    except OSError:
        return "unknown", Evaluator("file_contains", "1", f"{METHOD}; file not readable")
    return ("success" if found else "failure"), \
        Evaluator("file_contains", "1", f"{METHOD}; marker in {path}")


def exact_match(observed: Optional[str], expected: str,
                normalize: bool = True) -> tuple[str, Evaluator]:
    """Judge by exact (optionally whitespace-normalised) answer equality."""
    ev = Evaluator("exact_match", "1", f"{METHOD}; answer equality")
    if observed is None:
        return "unknown", Evaluator("exact_match", "1", f"{METHOD}; no observed value")
    a, b = observed, expected
    if normalize:
        a, b = " ".join(a.split()), " ".join(b.split())
    return ("success" if a == b else "failure"), ev


# --------------------------------------------------------------------------
# attaching a label to runs, via the canonical boundary
# --------------------------------------------------------------------------
def attach(runs: Sequence[Any], result: tuple[str, Evaluator]) -> list:
    """Return runs with `verified_outcome` / `evaluator` set from one evaluation.

    The run's own `outcome` (terminal state) is left untouched: terminal state and
    verified task outcome are different claims and must not overwrite each other.
    """
    outcome, ev = result
    if outcome not in ("success", "failure", "unknown"):
        raise EvaluationError(f"outcome must be success/failure/unknown, got {outcome!r}")
    return [replace(r, verified_outcome=outcome, evaluator=ev) for r in runs]
