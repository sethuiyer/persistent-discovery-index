#!/usr/bin/env python3
"""
test_o4b_cost.py — synthetic audit of the cost-variation statistic.

No PDI data, no agent runs. Checks that the implementation matches the frozen
prose (O4B_PREDECLARATION_PILOT2.md §3) and that no pathological consequence was
overlooked. Exact arithmetic (Fraction) where the claim is exact.

Fixtures: zero variance (abstain), currency scaling, unequal repetitions (equal
task weighting), unresolved residual, singleton refinement, within-task centring
invariance, and nesting validation.

Run: python3 test_o4b_cost.py     (exit 0 on success)
"""
from __future__ import annotations

import sys
from fractions import Fraction as F

from multiresolution import RefinementViolation
from o4b_cost import best_level, variance_shares

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


# 4 runs, 2 tasks x 2; behavioural classes (NOT by task, so the algebra is exercised)
TASKS4 = ["t1", "t1", "t2", "t2"]
COSTS4 = [F(1), F(3), F(10), F(14)]
LEVELS4 = [[0, 0, 0, 0],       # root (trivial)
           [0, 0, 0, 1],       # L1: {0,1,2} vs {3}
           [0, 1, 1, 2]]       # L2: {0} {1,2} {3}   (not discrete)


def test_fixture_algebra() -> None:
    print("base fixture: energies, residual, shares, total")
    r = variance_shares(COSTS4, TASKS4, LEVELS4)
    print(f"    E={r['E']} residual={r['residual']} total={r['total']} shares={r['shares']}")
    check("E_0 == 4/3", r["E"][0] == F(4, 3), str(r["E"][0]))
    check("E_1 == 1/24", r["E"][1] == F(1, 24), str(r["E"][1]))
    check("residual == 9/8", r["residual"] == F(9, 8), str(r["residual"]))
    check("total == within-task weighted variance 5/2", r["total"] == F(5, 2), str(r["total"]))
    check("total == sum(E) + residual", r["total"] == sum(r["E"]) + r["residual"])
    check("shares sum to 1 - residual share (< 1)", sum(r["shares"]) < 1
          and sum(r["shares"]) + r["residual"] / r["total"] == 1)


def test_zero_variance_abstains() -> None:
    print("zero variance -> share undefined -> ABSTAIN (never 0)")
    r = variance_shares([F(5), F(5), F(5), F(5)], TASKS4, LEVELS4)
    check("abstains", r["abstain"] is True)
    check("shares are None, not zeros", r["shares"] is None)
    check("reason names zero variance", "zero" in r["reason"], r["reason"])
    check("best_level abstains", best_level(r, 0.0) is None)


def test_currency_scaling() -> None:
    print("currency rescaling: shares invariant, energies scale by k^2")
    base = variance_shares(COSTS4, TASKS4, LEVELS4)
    k = 4
    scaled = variance_shares([k * c for c in COSTS4], TASKS4, LEVELS4)
    check("shares unchanged", base["shares"] == scaled["shares"],
          f"{base['shares']} vs {scaled['shares']}")
    check("E scales by k^2", scaled["E"] == [k * k * e for e in base["E"]])
    check("residual scales by k^2", scaled["residual"] == k * k * base["residual"])
    check("total scales by k^2", scaled["total"] == k * k * base["total"])


def test_unequal_repetitions() -> None:
    print("unequal repetitions: equal-task weighting; a 1-run task is excluded")
    tasks = ["t1", "t1", "t2", "t2", "t2", "t2", "t3"]
    costs = [F(1), F(3)] + [F(0)] * 4 + [F(7)]
    root = [0] * 7
    singles = list(range(7))            # finest resolves everything -> residual 0
    r = variance_shares(costs, tasks, [root, singles], r_min=2)
    # equal task weighting: 0.5 * var(t1)=1  +  0.5 * var(t2)=0
    check("total uses EQUAL TASK weighting (1/2, not run-weighted 1/3)",
          r["total"] == F(1, 2), str(r["total"]))
    check("t3 (one priced run) is excluded and counted",
          r["tasks_excluded"] == {"t3": 1}, str(r["tasks_excluded"]))
    check("two tasks, six runs eligible",
          r["tasks_eligible"] == 2 and r["runs_eligible"] == 6)


def test_unresolved_residual() -> None:
    print("unresolved residual: a coarse finest level leaves residual in the total")
    coarse = [[0, 0, 0, 0], [0, 0, 0, 0]]       # no refinement at all: nothing resolved
    r = variance_shares(COSTS4, TASKS4, coarse)
    check("residual > 0 when the finest partition resolves nothing", r["residual"] > 0, str(r["residual"]))
    check("total == sum(E) + residual", r["total"] == sum(r["E"]) + r["residual"])
    check("everything is unresolved: residual == total", r["residual"] == r["total"])
    check("no share is claimed", sum(r["shares"]) == 0)
    # a merging (non-trivial but coarse) refinement resolves only part of it
    partial = variance_shares(COSTS4, TASKS4, [[0, 0, 0, 0], [0, 0, 0, 0], [0, 1, 0, 1]])
    check("partial refinement leaves a positive residual share",
          0 < partial["residual"] / partial["total"] < 1)


def test_singleton_refinement_inadmissible() -> None:
    print("singleton refinement is inadmissible and never selected")
    discrete = [[0, 0, 0, 0], [0, 1, 2, 3]]        # L1 is discrete
    r = variance_shares(COSTS4, TASKS4, discrete)
    check("discrete level marked inadmissible", r["level_admissible"][1] is False)
    check("its distinct-task support is 0 (every block is one run)", r["support"][1] == 0.0,
          str(r["support"][1]))
    check("best_level will not select it even at s_min = 0",
          best_level(r, 0.0) is None, str(best_level(r, 0.0)))
    # and the 4-run fixture's supported, non-discrete L1 IS selectable
    ok = variance_shares(COSTS4, TASKS4, LEVELS4)
    check("a supported level remains selectable under s_min",
          best_level(ok, F(1, 2)) == 0, str(best_level(ok, F(1, 2))))


def test_unknown_is_not_signal() -> None:
    print("unknown rows are removed from the SELECTION cohort, not just masked")
    # two tasks, each with two known-cost-0 runs and one unknown-cost-9 run.
    # The known observations have ZERO cost variation, so selection must abstain.
    tasks = ["t1", "t1", "t1", "t2", "t2", "t2"]
    costs = [F(0), F(0), F(9), F(0), F(0), F(9)]
    levels = [[0] * 6, [0, 0, "unknown", 0, 0, "unknown"]]
    r = variance_shares(costs, tasks, levels)
    print(f"    selection: abstain={r['abstain']} reason={r['reason']!r} "
          f"excluded_mass={r['unknown_excluded_mass']}")
    print(f"    descriptive full-cohort total={r['full']['total']} "
          f"E_unknown={r['full']['E_unknown']}")
    check("selection abstains: the known runs have no variation", r["abstain"] is True,
          str(r.get("shares")))
    check("reason names zero variance", "zero" in r["reason"], r["reason"])
    check("excluded mass is reported", r["unknown_excluded_mass"] > 0)
    check("the descriptive full-cohort report still shows energy",
          r["full"]["total"] > 0, str(r["full"]["total"]))

    # and changing an unknown run's cost must NOT move the selection numbers
    tasks2 = ["t1", "t1", "t1", "t2", "t2", "t2"]
    lv2 = [[0] * 6, [0, 1, "unknown", 0, 1, "unknown"]]
    a = variance_shares([F(0), F(2), F(9), F(0), F(2), F(9)], tasks2, lv2)
    b = variance_shares([F(0), F(2), F(1000), F(0), F(2), F(1)], tasks2, lv2)
    check("selection shares are invariant to unknown-run costs",
          a["shares"] == b["shares"], f"{a['shares']} vs {b['shares']}")
    check("selection energy invariant too", a["E"] == b["E"])
    check("the descriptive report DOES change with unknown-run costs",
          a["full"]["total"] != b["full"]["total"])
    check("unknown mass is reported in the descriptive report",
          sum(a["full"]["E_unknown"]) > 0)


def test_support_counts_distinct_tasks() -> None:
    print("support counts DISTINCT TASKS per block, not runs")
    # a level that simply separates the two tasks: every block holds one task only
    by_task = [[0, 0, 0, 0], [0, 0, 1, 1]]
    r = variance_shares(COSTS4, TASKS4, by_task)
    check("task-separating level has zero cross-task support", r["support"][1] == 0.0,
          str(r["support"][1]))
    check("and is therefore inadmissible", r["level_admissible"][1] is False)
    check("best_level abstains (no admissible refinement)",
          best_level(r, 0.0) is None, str(best_level(r, 0.0)))
    # several runs of ONE task in a block still do not establish support
    tasks = ["t1"] * 4 + ["t2", "t2"]
    costs = [F(1), F(3), F(5), F(7), F(0), F(0)]
    lv = [[0] * 6, [0, 0, 0, 0, 1, 1]]      # block0 = four t1 runs, block1 = two t2 runs
    r2 = variance_shares(costs, tasks, lv)
    check("four runs of one task do not create a supported block",
          r2["support"][1] == 0.0, str(r2["support"][1]))


def test_support_uses_task_weighting() -> None:
    print("support uses the equal-task measure mu, not a fraction of raw runs")
    tasks = ["t1"] * 4 + ["t2"] * 2 + ["t3"] * 2
    costs = [F(1), F(2), F(3), F(4), F(0), F(0), F(5), F(5)]
    lv = [[0] * 8, [0, 0, 0, 0, 0, 0, 1, 1]]     # block0 = t1+t2 (supported), block1 = t3
    r = variance_shares(costs, tasks, lv, r_min=2)
    check("support is the task-weighted 2/3", r["support"][1] == F(2, 3), str(r["support"][1]))
    check("NOT the raw-run fraction 3/4", r["support"][1] != F(3, 4))
    check("level has enough blocks and support -> admissible", r["level_admissible"][1] is True)


def test_within_task_centring_invariance() -> None:
    print("within-task centring removes per-task offsets")
    base = variance_shares(COSTS4, TASKS4, LEVELS4)
    shifted = variance_shares([c + off for c, off in
                               zip(COSTS4, [100, 100, 200, 200])], TASKS4, LEVELS4)
    check("shares unchanged by per-task constant offsets",
          base["shares"] == shifted["shares"],
          f"{base['shares']} vs {shifted['shares']}")
    check("energies unchanged too", base["E"] == shifted["E"])


def test_nesting_is_enforced() -> None:
    print("nesting is enforced at construction")
    bad = [[0, 0, 0, 0], [0, 0, 1, 1], [0, 1, 0, 1]]   # block {0,2} straddles L1
    try:
        variance_shares(COSTS4, TASKS4, bad)
        check("non-nested levels raise RefinementViolation", False, "no error raised")
    except RefinementViolation:
        check("non-nested levels raise RefinementViolation", True)


if __name__ == "__main__":
    print("=" * 70)
    print("test_o4b_cost — audit of the cost-variation statistic")
    print("=" * 70)
    test_fixture_algebra()
    test_zero_variance_abstains()
    test_unknown_is_not_signal()
    test_currency_scaling()
    test_unequal_repetitions()
    test_unresolved_residual()
    test_singleton_refinement_inadmissible()
    test_support_counts_distinct_tasks()
    test_support_uses_task_weighting()
    test_within_task_centring_invariance()
    test_nesting_is_enforced()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
