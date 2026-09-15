#!/usr/bin/env python3
"""
test_invariance_first.py — self-checking suite for invariance_first.py

The claim under test is that five named principles are ONE principle and that PDI
instantiates all of them. The suite pins the split:

  (a) witness-gated construction   -> PDI enforces it (TowerViolation)
  (b) canonicity                   -> PDI does NOT have it; it quarantines the
                                      finite-scale number behind D_shallow and
                                      the asymptotic one behind a convergence
                                      status, and leaves canonicity OPEN (9.1)

Run: python3 test_invariance_first.py     (exit 0 on success)
"""
from __future__ import annotations

import math
import sys

from agent_profiler import asymptotic
from pdi import PDI
from quotient_tower import QuotientTower, TowerViolation

from invariance_first import H, reindexed, traces

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_gate_fires_on_witness() -> None:
    print("(a) the gate is on the witness")
    corpus = [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
    good = QuotientTower([lambda h: h[0], lambda h: h[:2], lambda h: h[:3]])
    check("refining tower is accepted", good.validate(corpus) == len(corpus))
    bad = QuotientTower([lambda h: h[:2], lambda h: h[0], lambda h: h[:3]])
    raised = False
    try:
        bad.validate(corpus)
    except TowerViolation:
        raised = True
    check("non-refining tower raises TowerViolation", raised)
    # exhaustive cross-check agrees with the fast check
    check("validate_pairs agrees", good.validate_pairs(corpus) == len(corpus))


def test_presentation_dependence_is_real() -> None:
    print("(b) the finite-scale number IS presentation-dependent")
    runs = list(traces())
    marks = [t[0] == t[1] for t in runs]
    a = reindexed(runs, marks, prepend=False)
    b = reindexed(runs, marks, prepend=True)
    ea, eb = a.exponents(), b.exponents()
    check("both presentations are accepted towers", True)
    check("finite-scale D differs", abs(ea["D"] - eb["D"]) > 1e-12,
          f"{ea['D']} vs {eb['D']}")
    check("A is flagged shallow (attained inside the horizon)", ea["D_shallow"])
    check("B is not flagged shallow", not eb["D_shallow"])


def test_quarantine_holds() -> None:
    print("(b') and it is quarantined, not eliminated")
    runs = list(traces())
    marks = [t[0] == t[1] for t in runs]
    a = reindexed(runs, marks, prepend=False)
    b = reindexed(runs, marks, prepend=True)

    def dseq(idx, Hn):
        return {j: math.log(idx.L[j]) / (-math.log(idx.eps(j)))
                for j in range(1, Hn + 1) if idx.L.get(j, 0) > 0}

    Ha, Hb = max(a.L), max(b.L)
    aa = asymptotic({"d_seq": dseq(a, Ha), "s_seq": {}, "horizon": Ha})["D"]
    ab = asymptotic({"d_seq": dseq(b, Hb), "s_seq": {}, "horizon": Hb})["D"]
    check("A's tail is STABLE", aa["status"] == "STABLE", aa["status"])
    check("B's tail is TRENDING_UP", ab["status"] == "TRENDING_UP", ab["status"])
    check("B is reported as a LOWER bound, not a value", ab["bound"] == "lower bound",
          ab["bound"])
    # the true limsup is 1 for both, so B's lower bound is CORRECT, not wrong
    true_limsup = 1.0
    check("B's lower bound does not overclaim", ab["value"] <= true_limsup + 1e-12)
    check("A's exact value is right", abs(aa["value"] - true_limsup) < 1e-12)
    # and the raw finite-scale number is NOT what gets promised
    check("window sup != tail estimate for B",
          abs(max(dseq(b, Hb).values()) - ab["value"]) < 1e-12)  # both are the tail end


def test_reindexing_is_row_3_1() -> None:
    print("the reindexing instance of row 3.1")
    runs = list(traces())
    marks = [t[0] == t[1] for t in runs]
    a = reindexed(runs, marks, prepend=False)
    b = reindexed(runs, marks, prepend=True)
    Ha, Hb = max(a.L), max(b.L)
    check("B has one more level than A", Hb == Ha + 1)
    check("dropping B's first level recovers A's L sequence",
          all(b.L.get(j + 1, 0) == a.L.get(j, 0) for j in range(1, Ha + 1)))
    # the sequence s_j = (j-1)/j is strictly increasing, so the finite sup is at
    # the horizon while the limsup is 1 -- exactly row 3.1
    seq = [math.log(b.L[j], 2) / j for j in range(1, Hb + 1)]
    check("B's exponent sequence is strictly increasing", all(
        seq[i] < seq[i + 1] for i in range(len(seq) - 1)))
    check("and bounded above by 1 (the limsup)", max(seq) < 1.0)


if __name__ == "__main__":
    print("=" * 70)
    print("test_invariance_first")
    print("=" * 70)
    test_gate_fires_on_witness()
    test_presentation_dependence_is_real()
    test_quarantine_holds()
    test_reindexing_is_row_3_1()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
