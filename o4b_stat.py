#!/usr/bin/env python3
"""
o4b_stat.py — the frozen O4b decision statistic (O4B_PREDECLARATION.md §7).

This is the RULER. It implements exactly the predeclared procedure; the defaults
are the predeclared values. It must not be tuned to produce desired answers: any
change to the method or the defaults after a baseline profile has been inspected
breaks the seal.

Paired and task-level, by construction:
  * the resampling unit is the TASK/CLUSTER, never a run;
  * baseline and intervention are paired per task (d_t), never bootstrapped
    independently.

Stdlib only.
"""
from __future__ import annotations

import random
from typing import Optional, Sequence

SEED = 20260916
N_RESAMPLES = 10000
DELTA = 0.10          # non-inferiority margin
Q_NI = 0.05           # 5th percentile  -> one-sided 95% lower bound
Q_COST = 0.95         # 95th percentile -> one-sided 95% upper bound
MIN_ELIGIBLE = 6      # n_both < 6 -> INCONCLUSIVE


# --------------------------------------------------------------------------
# per-task scores
# --------------------------------------------------------------------------
def task_success_score(labels: Sequence[str]) -> Optional[float]:
    """s_{t,c} = #success / (#success + #failure). UNKNOWN is not in the denominator.

    Returns None when the task/condition has no non-UNKNOWN run (not eligible).
    """
    s = sum(1 for x in labels if x == "success")
    f = sum(1 for x in labels if x == "failure")
    total = s + f
    return (s / total) if total else None


def task_cost_mean(costs: Sequence[Optional[float]]) -> Optional[float]:
    """C̄_{t,c} = mean of run costs. None if ANY run cost is missing (task ineligible)."""
    if not costs or any(c is None for c in costs):
        return None
    return sum(costs) / len(costs)


def paired_differences(intervention: Sequence[Optional[float]],
                       baseline: Sequence[Optional[float]]) -> list:
    """Paired d_t for tasks eligible in BOTH conditions (both non-None)."""
    return [i - b for i, b in zip(intervention, baseline)
            if i is not None and b is not None]


# --------------------------------------------------------------------------
# the bootstrap (task-level, paired input vectors)
# --------------------------------------------------------------------------
def bootstrap_mean_percentile(x: Sequence[float], q: float,
                              seed: int = SEED, n: int = N_RESAMPLES) -> Optional[float]:
    """q-th percentile of the bootstrap distribution of mean(x), resampling TASKS."""
    m = len(x)
    if m == 0:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        tot = 0.0
        for _ in range(m):
            tot += x[rng.randrange(m)]
        means.append(tot / m)
    means.sort()
    idx = min(n - 1, max(0, int(round(q * (n - 1)))))
    return means[idx]


def non_inferiority(d: Sequence[float], delta: float = DELTA,
                    seed: int = SEED, n: int = N_RESAMPLES) -> tuple:
    """Return (D, lower_bound, holds). Holds iff the 5th percentile >= -delta."""
    if not d:
        return None, None, False
    lo = bootstrap_mean_percentile(d, Q_NI, seed, n)
    return sum(d) / len(d), lo, (lo >= -delta)


def cost_reduction(deltas: Sequence[float], seed: int = SEED, n: int = N_RESAMPLES) -> tuple:
    """Return (Delta, upper_bound, reduced). Reduced iff the 95th percentile < 0."""
    if not deltas:
        return None, None, False
    hi = bootstrap_mean_percentile(deltas, Q_COST, seed, n)
    return sum(deltas) / len(deltas), hi, (hi < 0)


def classify(n_both: int, ni_holds: bool, cost_reduced: bool) -> str:
    """A / B / D per the predeclaration. C is decided before the held-out stage."""
    if n_both < MIN_ELIGIBLE:
        return "D"
    if not ni_holds:
        return "B"
    return "A" if cost_reduced else "D"
