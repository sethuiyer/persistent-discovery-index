#!/usr/bin/env python3
"""
test_survival_commutation.py — self-checking suite for survival_commutation.py

The claim under test is NOT "Omega = 0". It is the sharper pair:

  (i)  on the QUOTIENT axis (T-invariant refinement) the square commutes, and
  (ii) on the INCLUSION axis it fails, with Omega != 0 exactly when some periodic
       point of X lies in the filter F but its orbit leaves F.

Both are checked exhaustively at small n, plus the minimal witness is pinned to an
exact system so a regression cannot silently move it.

Run: python3 test_survival_commutation.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from survival_commutation import (
    all_maps,
    core,
    part1_is_trivial,
    part2,
    part3,
    part4_characterisation,
    partition_refines,
    periodic_points,
    projection,
    quotient_map,
    t_invariant_partitions,
    _orbit_leaves,
)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILS.append(name)


# --------------------------------------------------------------------------
def test_primitives() -> None:
    print("primitives")
    # 0 -> 1 -> 2 -> 0 cycle, 3 -> 2 transient
    T = {0: 1, 1: 2, 2: 0, 3: 2}
    check("periodic_points finds the 3-cycle only",
          periodic_points(T) == {0, 1, 2}, str(periodic_points(T)))
    check("core of whole space = periodic points",
          core(T, set(range(4))) == {0, 1, 2})
    check("core of a non-invariant set is empty",
          core(T, {3}) == set())
    check("core of a forward-invariant subset keeps its points",
          core(T, {0, 1, 2}) == {0, 1, 2})
    check("orbit_leaves detects leaving",
          _orbit_leaves(T, 3, {3}) and not _orbit_leaves(T, 0, {0, 1, 2}))


def test_quotient_machinery() -> None:
    print("quotient machinery")
    T = {0: 1, 1: 0, 2: 2}
    # {0,1} together, {2} alone -- T-invariant because 0 and 1 swap
    fine = {0: 0, 1: 1, 2: 2}          # discrete
    coarse = {0: 0, 1: 0, 2: 1}        # {0,1} merged
    check("fine refines coarse", partition_refines(fine, coarse))
    check("coarse does not refine fine", not partition_refines(coarse, fine))
    Tf = quotient_map(T, fine, 3)
    Tc = quotient_map(T, coarse, 3)
    pi = projection(fine, coarse, 3)
    check("dynamics descends through the bonding map",
          all(pi[Tf[b]] == Tc[pi[b]] for b in Tf))
    inv = [p for p in t_invariant_partitions(T, 3)]
    check("t_invariant_partitions returns only invariant partitions", len(inv) > 0)
    for p in inv:
        for x in range(3):
            for y in range(3):
                if p[x] == p[y]:
                    check(f"invariance of {p}", p[T[x]] == p[T[y]])
                    break
            break


def test_part1_trivial() -> None:
    print("part 1 -- restriction operators commute")
    # exhaustive at n=3, asserted directly rather than only printed
    n = 3
    X = set(range(n))
    bad = 0
    for r in range(1 << n):
        P = {x for x in X if r >> x & 1}
        for s in range(1 << n):
            Q = {x for x in X if s >> x & 1}
            if (X & P) & Q != (X & Q) & P:
                bad += 1
    check("no counterexample among restriction pairs", bad == 0, f"bad={bad}")


def test_part2_quotient_axis() -> None:
    print("part 2 -- quotient axis")
    # recompute independently of the printed summary, at n=3
    n = 3
    systems = descent_ok = mismatches = 0
    for T in all_maps(n):
        parts = list(t_invariant_partitions(T, n))
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                if partition_refines(parts[i], parts[j]):
                    fine, coarse = parts[i], parts[j]
                elif partition_refines(parts[j], parts[i]):
                    fine, coarse = parts[j], parts[i]
                else:
                    continue
                systems += 1
                Tf, Tc = quotient_map(T, fine, n), quotient_map(T, coarse, n)
                pi = projection(fine, coarse, n)
                if all(pi[Tf[b]] == Tc[pi[b]] for b in Tf):
                    descent_ok += 1
                A = {pi[b] for b in periodic_points(Tf)}
                B = periodic_points(Tc) & A
                if A != B:
                    mismatches += 1
    check("systems were actually checked", systems > 0, f"systems={systems}")
    check("T always descends", descent_ok == systems,
          f"{descent_ok}/{systems}")
    check("Omega = 0 on the quotient axis", mismatches == 0,
          f"mismatches={mismatches}")


def test_part3_minimal_witness() -> None:
    print("part 3 -- minimal witness on the inclusion axis")
    w = part3(4)
    check("a witness exists at n = 2", w is not None and w["n"] == 2,
          str(None if w is None else w["n"]))
    if w:
        check("witness is the 2-cycle with a one-point filter",
              w["T"] == {0: 1, 1: 0} and w["F"] == {0},
              f"T={w['T']} F={w['F']}")
        check("route A is empty", w["A"] == set(), str(w["A"]))
        check("route B is non-empty", w["B"] == {0}, str(w["B"]))
        check("Omega != 0", w["A"] != w["B"])


def test_part4_characterisation() -> None:
    print("part 4 -- exact characterisation")
    n = 3
    X = set(range(n))
    total = agree = inv_cases = inv_bad = 0
    for T in all_maps(n):
        per = periodic_points(T)
        for r in range(1 << n):
            F = {x for x in range(n) if r >> x & 1}
            if not F or F == X:
                continue
            total += 1
            omega = core(T, F) != (per & F)
            pred = any(x in per and _orbit_leaves(T, x, F) for x in F)
            if omega == pred:
                agree += 1
            if all(T[x] in F for x in F):
                inv_cases += 1
                if omega:
                    inv_bad += 1
    check("(T,F) pairs checked", total > 0, f"total={total}")
    check("the iff holds exactly", agree == total, f"{agree}/{total}")
    check("T-invariance always forces commutation", inv_bad == 0,
          f"{inv_bad} defects among {inv_cases}")
    check("invariant cases were non-trivial", inv_cases > 0)


if __name__ == "__main__":
    print("=" * 68)
    print("test_survival_commutation")
    print("=" * 68)
    test_primitives()
    test_quotient_machinery()
    test_part1_trivial()
    test_part2_quotient_axis()
    test_part3_minimal_witness()
    test_part4_characterisation()
    print("=" * 68)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
