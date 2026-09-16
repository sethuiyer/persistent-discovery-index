#!/usr/bin/env python3
"""
o4b_cost.py — the outcome-independent COST-VARIATION statistic (pilot 2, §3).

Localises where observed **cost variation** is resolved by behavioural refinement.
It is NOT a waste, saving, or causal measure: high cost may be necessary work.

Contract (O4B_PREDECLARATION_PILOT2.md §3, all of it load-bearing):

  * equal weight per task, divided equally among that task's eligible runs;
  * cost centred WITHIN task using the same weights;
  * detail energies E_j = ||D_j c||^2 on a caller-supplied nested partition tower;
  * residual ||c - P_J c||^2 carried in the total;
  * unit-free shares s_j = E_j / (sum_j E_j + residual);
  * zero denominator -> share UNDEFINED -> the selector ABSTAINS (never 0);
  * a level whose mean class size is below a threshold is INADMISSIBLE -- a
    singleton refinement resolves every observed difference without generalising;
  * a task with fewer than r_min eligible runs is excluded (with one run,
    within-task centring removes all variation).

No feature is read from the observable: the caller supplies partitions over
BEHAVIOURAL features, and `cost` is passed separately.

Stdlib only.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence

from multiresolution import (PartitionTower, detail, residual, weighted_norm2)

R_MIN_DEFAULT = 2
MIN_MEAN_CLASS_SIZE_DEFAULT = 2.0


def variance_shares(costs: Sequence[Optional[float]],
                    tasks: Sequence,
                    levels: Sequence[Sequence],
                    r_min: int = R_MIN_DEFAULT,
                    min_mean_class_size: float = MIN_MEAN_CLASS_SIZE_DEFAULT) -> dict:
    """Cost-variation shares over a nested partition tower.

    `costs[i]`        per-run cost (None = run not priced)
    `tasks[i]`        task/cluster id of run i
    `levels[j][i]`    class id of run i at level j (levels[0] must be trivial,
                      and each level must refine the previous)
    """
    n = len(costs)
    if len(tasks) != n or not levels or any(len(L) != n for L in levels):
        raise ValueError("costs, tasks and every level must be the same length")

    present = [i for i in range(n) if costs[i] is not None]
    by_task: dict = defaultdict(list)
    for i in present:
        by_task[tasks[i]].append(i)
    eligible = {t: idx for t, idx in by_task.items() if len(idx) >= r_min}
    excluded = {t: len(idx) for t, idx in by_task.items() if len(idx) < r_min}
    idx = sorted(i for t in eligible for i in eligible[t])

    if not idx:
        return {"abstain": True, "reason": "no task has >= r_min priced runs",
                "shares": None, "E": None, "residual": None, "total": None,
                "tasks_eligible": 0, "runs_eligible": 0, "tasks_excluded": excluded,
                "level_admissible": None, "mean_class_size": None}

    n_tasks = len(eligible)
    sample = next(c for c in costs if c is not None)
    one = type(sample)(1)            # keep exact arithmetic when costs are exact
    mu = [one * 0] * n
    for t, run_idx in eligible.items():                     # equal per task, split within
        for i in run_idx:
            mu[i] = (one / n_tasks) / len(run_idx)

    c = [None] * n
    for t, run_idx in eligible.items():                     # centre WITHIN task
        mean_t = sum(costs[i] for i in run_idx) / len(run_idx)
        for i in run_idx:
            c[i] = costs[i] - mean_t

    sub_levels = [[levels[j][i] for i in idx] for j in range(len(levels))]
    tower = PartitionTower(sub_levels)                      # validates nesting + trivial root
    sub_mu = [mu[i] for i in idx]
    sub_c = [c[i] for i in idx]

    E = [weighted_norm2(detail(sub_c, tower, j, sub_mu), sub_mu)
         for j in range(tower.depth() - 1)]
    res = residual(sub_c, tower, sub_mu)
    total = sum(E) + res

    mean_size, admissible = [], []
    for j in range(len(sub_levels)):
        classes = len(set(sub_levels[j]))
        size = (len(idx) / classes) if classes else 0.0
        mean_size.append(size)
        admissible.append(size >= min_mean_class_size)

    base = {"E": E, "residual": res, "total": total,
            "tasks_eligible": n_tasks, "runs_eligible": len(idx),
            "tasks_excluded": excluded, "mean_class_size": mean_size,
            "level_admissible": admissible}
    if total <= 0:
        base.update(abstain=True, reason="zero observed within-task variance", shares=None)
        return base
    base.update(abstain=False, reason="", shares=[e / total for e in E])
    return base


def best_level(result: dict, s_min: float) -> Optional[int]:
    """The admissible refinement with the largest share, or None (-> abstain / C).

    `shares[j]` is the variance resolved by adding level `j+1`, so ADMISSIBILITY is
    read from level `j+1`: a discrete refinement is never selected. Ties break to
    the coarser refinement.
    """
    if not result or result.get("abstain") or not result.get("shares"):
        return None
    depth = len(result["level_admissible"])
    best, best_s = None, None
    for j, s in enumerate(result["shares"]):
        finer = j + 1
        if finer >= depth or not result["level_admissible"][finer]:
            continue
        if s >= s_min and (best_s is None or s > best_s):
            best, best_s = j, s
    return best
