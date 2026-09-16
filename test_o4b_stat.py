#!/usr/bin/env python3
"""
test_o4b_stat.py — statistic-only sanity audit (O4B_PREDECLARATION.md §7).

Checks that the IMPLEMENTATION agrees with the frozen prose and that the decision
rule has no pathological consequence we failed to notice. Uses synthetic vectors
only: no PDI profiles, no agent runs, no data. The ruler is audited before
anything is measured.

Run: python3 test_o4b_stat.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from o4b_stat import (MIN_ELIGIBLE, bootstrap_mean_percentile, classify,
                      cost_reduction, non_inferiority, paired_differences,
                      task_cost_mean, task_success_score)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def row(label, d, expect=None):
    D, lo, holds = non_inferiority(d)
    note = "" if expect is None else f"  [expected NI={expect}]"
    print(f"    {label:<26} D={D:+.4f}  D*_5={lo:+.4f}  NI={holds}{note}")
    return D, lo, holds


def c_row(label, deltas, expect=None):
    Dl, hi, red = cost_reduction(deltas)
    note = "" if expect is None else f"  [expected reduced={expect}]"
    print(f"    {label:<26} Delta={Dl:+.4f}  Delta*_95={hi:+.4f}  reduced={red}{note}")
    return Dl, hi, red


def test_success_scoring() -> None:
    print("success score: UNKNOWN is coverage, not a denominator")
    check("2 success / 0 failure -> 1.0", task_success_score(["success", "success"]) == 1.0)
    check("success+unknown -> 1.0", task_success_score(["success", "unknown"]) == 1.0)
    check("all unknown -> ineligible (None)", task_success_score(["unknown", "unknown"]) is None)
    check("1 success 1 failure -> 0.5", task_success_score(["success", "failure"]) == 0.5)


def test_success_cases() -> None:
    print("non-inferiority on synthetic task vectors (8 tasks)")
    _, loA, niA = row("A  all d_t = 0", [0.0] * 8, expect=True)
    _, loB, niB = row("B  all d_t = +0.5", [0.5] * 8, expect=True)
    _, loC, niC = row("C  all d_t = -0.5", [-0.5] * 8, expect=False)
    row("D  7x0, 1x-0.5", [0.0] * 7 + [-0.5])
    row("E  6x0, 2x-0.5", [0.0] * 6 + [-0.5, -0.5])
    row("F  mixture", [-0.5, -0.5, -0.5, 0.0, 0.0, 0.0, 0.5, 0.5])
    check("A: all-zero is non-inferior (lower bound is 0)", niA and loA == 0.0)
    check("B: uniform improvement is non-inferior", niB and loB == 0.5)
    check("C: uniform -0.5 violates NI", (not niC) and abs(loC + 0.5) < 1e-12)
    print("    D/E/F are inspection rows: no threshold was tuned to them.")


def test_classify() -> None:
    print("classification (D for low eligibility, B for degraded success, A for both)")
    check("n_both=5 -> D", classify(5, True, True) == "D")
    check("n_both=6, NI fails -> B", classify(6, False, True) == "B")
    check("n_both=6, NI holds, cost up -> D", classify(6, True, False) == "D")
    check("n_both=6, NI holds, cost down -> A", classify(6, True, True) == "A")
    check("MIN_ELIGIBLE is 6", MIN_ELIGIBLE == 6)


def test_cost() -> None:
    print("cost rule on synthetic task vectors")
    _, _, redAll = c_row("all Delta_t < 0", [-0.1] * 8, expect=True)
    _, hiZero, redZero = c_row("all Delta_t = 0", [0.0] * 8, expect=False)
    c_row("one giant saving + increases", [-5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    c_row("mixed", [-0.4, -0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4])
    check("all-negative is a cost reduction", redAll)
    check("all-zero is NOT a cost reduction (upper bound is not < 0)",
          (not redZero) and hiZero == 0.0)
    check("a missing run cost makes the task ineligible", task_cost_mean([0.1, None]) is None)
    check("all runs priced -> eligible", task_cost_mean([0.1, 0.3]) == 0.2)


def test_paired_and_deterministic() -> None:
    print("pairing and determinism")
    d = paired_differences([1.0, None, 0.5], [0.5, 0.5, 0.5])
    check("ineligible tasks are dropped from the pair set", d == [0.5, 0.0], str(d))
    check("same seed -> same bound",
          bootstrap_mean_percentile([-0.5, 0.0, 0.5], 0.05)
          == bootstrap_mean_percentile([-0.5, 0.0, 0.5], 0.05))
    check("different seed may differ (sanity, not a claim)",
          bootstrap_mean_percentile([-0.4, -0.2, 0.0, 0.2], 0.05, seed=1)
          == bootstrap_mean_percentile([-0.4, -0.2, 0.0, 0.2], 0.05, seed=1))


if __name__ == "__main__":
    print("=" * 70)
    print("test_o4b_stat — audit of the frozen decision statistic")
    print("=" * 70)
    test_success_scoring()
    test_success_cases()
    test_classify()
    test_cost()
    test_paired_and_deterministic()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
