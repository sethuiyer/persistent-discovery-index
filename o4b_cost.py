#!/usr/bin/env python3
"""
o4b_cost.py — the outcome-independent COST-VARIATION statistic (pilot 2, §3).

Localises where observed **cost variation** is resolved by behavioural refinement.
It is NOT a waste, saving, or causal measure: high cost may be necessary work.

Contract (O4B_PREDECLARATION_PILOT2.md §3 + O4B_PILOT2_TOWER.md):

  * equal weight per task, divided equally among that task's eligible runs;
  * cost centred WITHIN task using the same weights — this measures RUN-TO-RUN cost
    variation, so a behaviour that is consistently expensive on every repetition of
    every task can vanish from this signal (stated limitation, not a bug);
  * detail energies E_j = ||D_j c||^2 on a caller-supplied nested partition tower;
  * residual ||c - P_J c||^2 carried in the total;
  * unit-free shares s_j = E_j / (sum_j E_j + residual);
  * zero denominator -> share UNDEFINED -> the selector ABSTAINS (never 0);
  * a level is INADMISSIBLE unless it has >= min_blocks blocks AND its **support**
    passes: support = fraction of eligible runs sitting in blocks that contain runs
    from >= k_tasks DISTINCT TASKS. Several runs from one task do not establish
    generalisation, so a level that merely separates tasks is inadmissible;
  * a task with fewer than r_min priced runs is excluded.

The observable is passed separately: partitions must be over BEHAVIOURAL features
and must never include cost, tokens, or any deterministic encoding of them.

Stdlib only.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence

from multiresolution import PartitionTower, detail, residual, weighted_norm2

R_MIN_DEFAULT = 2
K_TASKS_DEFAULT = 2
SUPPORT_FRAC_DEFAULT = 0.5
MIN_BLOCKS_DEFAULT = 2


def variance_shares(costs: Sequence[Optional[float]],
                    tasks: Sequence,
                    levels: Sequence[Sequence],
                    r_min: int = R_MIN_DEFAULT,
                    k_tasks: int = K_TASKS_DEFAULT,
                    support_frac: float = SUPPORT_FRAC_DEFAULT,
                    min_blocks: int = MIN_BLOCKS_DEFAULT,
                    unknown_label: str = "unknown",
                    u_max: float = 0.5) -> dict:
    """Cost-variation shares over a nested partition tower.

    `costs[i]`     per-run cost (None = run not priced)
    `tasks[i]`     task/cluster id of run i
    `levels[j][i]` class id of run i at level j (levels[0] trivial; each refines prev)
    Any class equal to `unknown_label` marks that run's level as UNDETERMINED. A
    refinement whose contrast touches an unknown class is excluded from SELECTION:
    shares are computed from the KNOWN energy only, while the unknown-dependent mass
    is reported separately and a refinement with unknown mass > `u_max` is
    inadmissible. A parser failure can therefore never become behavioural signal.
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
                "level_admissible": None, "support": None, "n_blocks": None,
                "mean_class_size": None}

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
    sub_tasks = [tasks[i] for i in idx]
    tower = PartitionTower(sub_levels)                      # validates nesting + trivial root
    sub_mu = [mu[i] for i in idx]
    sub_c = [c[i] for i in idx]

    depth = len(sub_levels)
    m = len(idx)
    E, E_known, E_unknown = [], [], []
    for j in range(depth - 1):
        D = detail(sub_c, tower, j, sub_mu)
        e = weighted_norm2(D, sub_mu)
        known = [sub_levels[j][pos] != unknown_label
                 and sub_levels[j + 1][pos] != unknown_label for pos in range(m)]
        ek = sum(sub_mu[pos] * D[pos] * D[pos] for pos in range(m) if known[pos])
        E.append(e)
        E_known.append(ek)
        E_unknown.append(e - ek)          # contrast touches an unknown class
    res = residual(sub_c, tower, sub_mu)
    total = sum(E) + res

    support, n_blocks, mean_size, admissible = [], [], [], []
    total_mass = sum(sub_mu)                 # == 1 by construction
    for j in range(len(sub_levels)):
        mass: dict = {}
        taskset: dict = {}
        for pos, cls in enumerate(sub_levels[j]):
            mass[cls] = mass.get(cls, 0) + sub_mu[pos]
            taskset.setdefault(cls, set()).add(sub_tasks[pos])
        nb = len(mass)
        # support is the DECLARED equal-task measure mu of runs in supported blocks,
        # NOT a fraction of raw runs (which would let high-repetition tasks dominate).
        supported_mass = sum(mass[c] for c in mass if len(taskset[c]) >= k_tasks)
        n_blocks.append(nb)
        support.append(supported_mass / total_mass)
        mean_size.append(m / nb if nb else 0.0)
        admissible.append(nb >= min_blocks and support[-1] >= support_frac)

    base = {"E": E, "E_known": E_known, "E_unknown": E_unknown, "residual": res,
            "total": total, "tasks_eligible": n_tasks, "runs_eligible": m,
            "tasks_excluded": excluded, "support": support, "n_blocks": n_blocks,
            "mean_class_size": mean_size, "level_admissible": admissible}
    if total <= 0:
        base.update(abstain=True, reason="zero observed within-task variance",
                    shares=None, unknown_mass=None, total_unknown_mass=None)
        return base
    # SELECTION uses the known share only; unknown-dependent mass is reported, not used.
    base["shares"] = [ek / total for ek in E_known]
    base["unknown_mass"] = [eu / total for eu in E_unknown]
    base["total_unknown_mass"] = sum(E_unknown) / total
    base["level_admissible"] = [
        admissible[L] if L == 0 else (admissible[L] and base["unknown_mass"][L - 1] <= u_max)
        for L in range(depth)]
    base.update(abstain=False, reason="")
    return base


def best_level(result: dict, s_min: float) -> Optional[int]:
    """The admissible refinement with the largest share, or None (-> abstain / C).

    `shares[j]` is the variance resolved by adding level `j+1`, so ADMISSIBILITY is
    read from level `j+1`: a discrete or task-separating refinement is never
    selected. Ties break to the coarser refinement.
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
