#!/usr/bin/env python3
"""
test_one_question.py — self-checking suite for one_question.py

What is under test:
  (1) n_j is invariant under the survival predicate  -> n_j is survival-FREE
  (2) PDI implements two survival predicates (horizon, explicit) and they can
      select DISJOINT branches of the same tree
  (3) Delta moves while L_j and D are held fixed     -> Delta is not survival

(1) and (3) are what makes the thesis "everything is one question" too strong,
and (2) is what makes even the question itself ambiguous until pinned.

Run: python3 test_one_question.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from pdi import PDI
from one_question import H, build_explicit, build_horizon, live_profiles

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_nj_is_survival_free() -> None:
    print("n_j invariance under the survival predicate")
    dead = build_explicit(mark_live=False)
    alive = build_explicit(mark_live=True)

    check("the two systems have the SAME n_j",
          all(dead.n[j] == alive.n[j] for j in range(1, H + 1)))
    check("the two systems have DIFFERENT L_j",
          any(dead.L[j] != alive.L[j] for j in range(1, H + 1)))
    # the point of the test: the survival ledger moved, the cost ledger did not
    check("L moved while n did not (>0 gap opened at some level)",
          any(alive.L[j] - dead.L[j] > 0 for j in range(1, H + 1)))
    check("n_j is strictly positive everywhere (not vacuous)",
          all(dead.n[j] > 0 for j in range(1, H + 1)))
    check("dead system has a real gap n_j > L_j",
          any(dead.n[j] > dead.L[j] for j in range(1, H + 1)))


def test_two_predicates_disagree() -> None:
    print('the two readings of "comes back"')
    h = PDI(); h.insert((0, 0, 0), live=True); h.insert((1,) * H); h.recompute_statuses()
    e = PDI(); e.insert((0, 0, 0), live=True); e.insert((1,) * H); e.finalize_explicit()

    check("same node set under both readings",
          all(h.n[j] == e.n[j] for j in range(1, H + 1)))
    check("level-1 live SETS differ",
          live_profiles(h, 1) != live_profiles(e, 1),
          f"{live_profiles(h,1)} vs {live_profiles(e,1)}")
    check("they are in fact disjoint at level 1",
          not (set(live_profiles(h, 1)) & set(live_profiles(e, 1))))
    check("counts agree at level 1 (a scalar ledger hides it)",
          h.L.get(1, 0) == e.L.get(1, 0))
    check("counts eventually diverge",
          any(h.L.get(j, 0) != e.L.get(j, 0) for j in range(1, H + 1)))


def test_delta_is_not_survival() -> None:
    print("Delta under fixed survival")
    a, b = build_horizon(), build_horizon(pad=True)
    exa, exb = a.exponents(), b.exponents()

    check("identical L_j", all(a.L.get(j, 0) == b.L.get(j, 0) for j in range(H + 1)))
    check("identical D", abs(exa["D"] - exb["D"]) < 1e-12,
          f"{exa['D']} vs {exb['D']}")
    check("different n_j", any(a.n.get(j, 0) != b.n.get(j, 0) for j in range(1, H + 1)))
    check("different S", abs(exa["S"] - exb["S"]) > 1e-9)
    check("different Delta", abs(exa["delta"] - exb["delta"]) > 1e-9,
          f"{exa['delta']} vs {exb['delta']}")
    check("Delta >= 0 for both", exa["delta"] >= -1e-12 and exb["delta"] >= -1e-12)


if __name__ == "__main__":
    print("=" * 68)
    print("test_one_question")
    print("=" * 68)
    test_nj_is_survival_free()
    test_two_predicates_disagree()
    test_delta_is_not_survival()
    print("=" * 68)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
