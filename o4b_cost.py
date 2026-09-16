#!/usr/bin/env python3
"""
o4b_cost.py — the outcome-independent COST-VARIATION statistic (pilot 2, §4).

Localises where observed **cost variation** is resolved by behavioural refinement.
It is NOT a waste, saving, or causal measure: high cost may be necessary work.

Contract (O4B_FREEZE_PROPOSAL.md §4 + O4B_PILOT2_TOWER.md):

  * equal weight per task, divided equally among that task's eligible runs;
  * cost centred WITHIN task using the same weights — this measures RUN-TO-RUN cost
    variation, so a behaviour consistently expensive on every repetition can vanish
    from this signal (stated limitation, not a bug);
  * detail energies E_j = ||D_j c||^2 on a caller-supplied nested partition tower;
  * residual ||c - P_J c||^2 carried in the total; unit-free shares s_j = E_j / total;
  * zero denominator -> share UNDEFINED -> the selector ABSTAINS (never 0);
  * a level is INADMISSIBLE unless it has >= min_blocks blocks AND its **support**
    passes: support = the DECLARED equal-task measure mu of runs in blocks holding
    runs from >= k_tasks DISTINCT TASKS. Several runs from one task do not establish
    generalisation.

UNKNOWN HANDLING (correctness, v-next). A class labelled `unknown` is undetermined.
Masking unknown rows out of an energy sum is NOT enough: those rows still enter the
parent means and the within-task centring, so they contaminate the "known" energy.
Therefore the SELECTION decomposition is computed on the **declared known cohort**:
centring, weights, and both projections are recomputed on the runs whose classes are
known at every level, and the excluded mu-mass is reported. The **full-cohort**
decomposition is returned separately as a descriptive report. A refinement is
inadmissible if the excluded mass exceeds `u_max`.

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
U_MAX_DEFAULT = 0.5


# --------------------------------------------------------------------------
# helpers, all operating on an explicit index set
# --------------------------------------------------------------------------
def _eligible_tasks(tasks, idx, r_min):
    by_task = defaultdict(list)
    for i in idx:
        by_task[tasks[i]].append(i)
    eligible = {t: v for t, v in by_task.items() if len(v) >= r_min}
    excluded = {t: len(v) for t, v in by_task.items() if len(v) < r_min}
    return eligible, excluded


def _weights(costs, eligible):
    n_tasks = len(eligible)
    sample = next(c for c in costs if c is not None)
    one = type(sample)(1)                       # exact arithmetic when costs are exact
    mu = {}
    for _t, run_idx in eligible.items():
        for i in run_idx:
            mu[i] = (one / n_tasks) / len(run_idx)
    return mu


def _centre(costs, eligible):
    c = {}
    for _t, run_idx in eligible.items():
        mean_t = sum(costs[i] for i in run_idx) / len(run_idx)
        for i in run_idx:
            c[i] = costs[i] - mean_t
    return c


def _decompose(sub_levels, sub_c, sub_mu, m):
    tower = PartitionTower(sub_levels)
    E = [weighted_norm2(detail(sub_c, tower, j, sub_mu), sub_mu)
         for j in range(tower.depth() - 1)]
    res = residual(sub_c, tower, sub_mu)
    return E, res


def _levels_support(sub_levels, sub_tasks, sub_mu, k_tasks, support_frac, min_blocks):
    support, n_blocks, mean_size, admissible = [], [], [], []
    total_mass = sum(sub_mu)
    m = len(sub_mu)
    for j in range(len(sub_levels)):
        mass: dict = {}
        taskset: dict = {}
        for pos, cls in enumerate(sub_levels[j]):
            mass[cls] = mass.get(cls, 0) + sub_mu[pos]
            taskset.setdefault(cls, set()).add(sub_tasks[pos])
        nb = len(mass)
        supported = sum(mass[cl] for cl in mass if len(taskset[cl]) >= k_tasks)
        n_blocks.append(nb)
        support.append(supported / total_mass)
        mean_size.append(m / nb if nb else 0.0)
        admissible.append(nb >= min_blocks and support[-1] >= support_frac)
    return support, n_blocks, mean_size, admissible


# --------------------------------------------------------------------------
def variance_shares(costs: Sequence[Optional[float]],
                    tasks: Sequence,
                    levels: Sequence[Sequence],
                    r_min: int = R_MIN_DEFAULT,
                    k_tasks: int = K_TASKS_DEFAULT,
                    support_frac: float = SUPPORT_FRAC_DEFAULT,
                    min_blocks: int = MIN_BLOCKS_DEFAULT,
                    unknown_label: str = "unknown",
                    u_max: float = U_MAX_DEFAULT) -> dict:
    n = len(costs)
    if len(tasks) != n or not levels or any(len(L) != n for L in levels):
        raise ValueError("costs, tasks and every level must be the same length")

    priced = [i for i in range(n) if costs[i] is not None]
    eligible_full, excluded_full = _eligible_tasks(tasks, priced, r_min)
    idx_full = sorted(i for v in eligible_full.values() for i in v)

    empty = {"abstain": True, "shares": None, "E": None, "residual": None, "total": None,
             "tasks_eligible": 0, "runs_eligible": 0, "tasks_excluded": excluded_full,
             "support": None, "n_blocks": None, "mean_class_size": None,
             "level_admissible": None, "unknown_excluded_mass": None, "full": None}

    if not idx_full:
        empty["reason"] = "no task has >= r_min priced runs"
        return empty

    # ---- descriptive full-cohort decomposition (includes unknown rows) --------
    mu_full = _weights(costs, eligible_full)
    c_full = _centre(costs, eligible_full)
    lv_full = [[levels[j][i] for i in idx_full] for j in range(len(levels))]
    tk_full = [tasks[i] for i in idx_full]
    full = _describe(lv_full, c_full, mu_full, idx_full, unknown_label)

    # ---- selection cohort: classes known at EVERY level -----------------------
    idx_known = [i for i in idx_full if all(levels[j][i] != unknown_label
                                            for j in range(len(levels)))]
    eligible_known, excluded_known = _eligible_tasks(tasks, idx_known, r_min)
    idx_known = sorted(i for v in eligible_known.values() for i in v)

    excluded_mass = 1 - sum(mu_full.get(i, 0) for i in idx_known)
    base = {"tasks_excluded": excluded_known or excluded_full,
            "unknown_excluded_mass": excluded_mass, "full": full}
    if not idx_known:
        base.update(empty)
        base["tasks_excluded"] = excluded_known
        base["reason"] = "no task has >= r_min KNOWN runs"
        base["full"] = full
        base["unknown_excluded_mass"] = excluded_mass
        return base

    mu = _weights(costs, eligible_known)
    c = _centre(costs, eligible_known)
    lv = [[levels[j][i] for i in idx_known] for j in range(len(levels))]
    tk = [tasks[i] for i in idx_known]
    sub_mu = [mu[i] for i in idx_known]
    sub_c = [c[i] for i in idx_known]

    E, res = _decompose(lv, sub_c, sub_mu, len(idx_known))
    total = sum(E) + res
    support, n_blocks, mean_size, admissible = _levels_support(
        lv, tk, sub_mu, k_tasks, support_frac, min_blocks)

    base.update({"tasks_eligible": len(eligible_known), "runs_eligible": len(idx_known),
                 "E": E, "residual": res, "total": total, "support": support,
                 "n_blocks": n_blocks, "mean_class_size": mean_size,
                 "level_admissible": admissible})
    if total <= 0:
        base.update(abstain=True, reason="zero observed within-task variance",
                    shares=None)
        return base
    base.update(abstain=False, reason="", shares=[e / total for e in E])
    base["level_admissible"] = [adm and excluded_mass <= u_max for adm in admissible]
    return base


def _describe(sub_levels, c, mu, idx, unknown_label):
    """Full-cohort decomposition, with unknown-dependent energy reported, not used."""
    sub_mu = [mu[i] for i in idx]
    sub_c = [c[i] for i in idx]
    E, res = _decompose(sub_levels, sub_c, sub_mu, len(idx))
    m = len(idx)
    E_known, E_unknown = [], []
    for j in range(len(sub_levels) - 1):
        D = detail(sub_c, PartitionTower(sub_levels), j, sub_mu)
        known = [sub_levels[j][p] != unknown_label
                 and sub_levels[j + 1][p] != unknown_label for p in range(m)]
        ek = sum(sub_mu[p] * D[p] * D[p] for p in range(m) if known[p])
        E_known.append(ek)
        E_unknown.append(E[j] - ek)
    total = sum(E) + res
    return {"E": E, "E_known": E_known, "E_unknown": E_unknown, "residual": res,
            "total": total}


def best_level(result: dict, s_min: float) -> Optional[int]:
    """The admissible refinement with the largest share, or None (-> abstain / C).

    `shares[j]` is the variance resolved by adding level `j+1`, so ADMISSIBILITY is
    read from level `j+1`. Ties break to the coarser refinement.
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
