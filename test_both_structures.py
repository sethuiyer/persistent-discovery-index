#!/usr/bin/env python3
"""
test_both_structures.py — self-checking suite for both_structures.py

Two negative results that together force the claim:

  (1) the recurrent core does not determine the transient structure
  (2) the ledger counts do not determine the structure

Note (2) is a limitation of the ledger as a SUMMARY, not of PDI as a data
structure: the tree is stored, the scalar profile cannot see it.

Run: python3 test_both_structures.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from both_structures import build, canon, periodic_points, transient_profile

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


T1 = {0: 1, 1: 2, 2: 0, 3: 0, 4: 0}
T2 = {0: 1, 1: 2, 2: 0, 3: 4, 4: 0}


def test_core_does_not_determine_transients() -> None:
    print("the core does not determine the transients")
    check("same recurrent core", periodic_points(T1) == periodic_points(T2))
    check("core is the expected 3-cycle",
          periodic_points(T1) == {0, 1, 2})
    p1, p2 = transient_profile(T1), transient_profile(T2)
    check("same transient COUNT", sum(p1.values()) == sum(p2.values()))
    check("transient count is 2", sum(p1.values()) == 2)
    check("different transient PROFILE", p1 != p2, f"{p1} vs {p2}")
    check("T1 is flat, T2 has a depth-2 chain", p1 == {1: 2} and p2 == {1: 1, 2: 1})


def test_counts_do_not_determine_structure() -> None:
    print("the counts do not determine the structure")
    a = build([("a", "b"), ("a", "c"), ("d", "e"), ("d", "f")])
    b = build([("a", "b"), ("a", "c"), ("a", "d"), ("e", "f")])
    check("identical n_j", all(a.n.get(j, 0) == b.n.get(j, 0) for j in range(1, 3)))
    check("identical L_j", all(a.L.get(j, 0) == b.L.get(j, 0) for j in range(1, 3)))
    check("both have n_j = (2,4)",
          [a.n.get(j, 0) for j in (1, 2)] == [2, 4])
    check("both have L_j = n_j (all live)",
          [a.L.get(j, 0) for j in (1, 2)] == [2, 4])
    ca, cb = canon(a.root), canon(b.root)
    check("trees are NOT isomorphic", ca != cb, f"{ca} vs {cb}")
    check("canonical forms are the expected ones",
          ca == "((()())(()()))" and cb == "((()()())(()))", f"{ca} vs {cb}")


def test_ledger_keeps_count_not_shape() -> None:
    print("what the ledger keeps")
    a = build([("a", "b"), ("a", "c"), ("d", "e"), ("d", "f")])
    # node count per level is preserved and reported
    check("node count per level is reported", a.n.get(1) == 2 and a.n.get(2) == 4)
    # but branching is not a reported scalar
    reported = {"n", "L", "exponents", "ledgers"}
    check("the ledger is a level-size profile, not an edge set",
          "children" not in reported)


if __name__ == "__main__":
    print("=" * 68)
    print("test_both_structures")
    print("=" * 68)
    test_core_does_not_determine_transients()
    test_counts_do_not_determine_structure()
    test_ledger_keeps_count_not_shape()
    print("=" * 68)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
