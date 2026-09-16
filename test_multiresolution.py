#!/usr/bin/env python3
"""
test_multiresolution.py — the O4a acceptance contract (seven fixtures), plus the
identities they rest on. Exact arithmetic (Fraction) wherever the claim is exact.

Fixtures (O4_SCOPE.md §3.3):
  1 constant-label   1b identity & root condition   2 unequal-weight
  3 planted-level    4 unresolved-residual          5 permutation-null
  6 xor-interaction  7 refinement-trap
plus pruning price (§9.4), aggregation (§9.5), and label coverage (§4).

This suite discharges **O4a only** (synthetic correctness) — specifically the
*algebra*: valid nested projections and exact identities. It does NOT discharge
feature provenance: the module consumes partitions supplied by the caller, and
nothing here checks that the features used to build them exclude the evaluator
outcome (O4_SCOPE.md §4). It says nothing about O4b (real-data usefulness).

Run: python3 test_multiresolution.py     (exit 0 on success)
"""
from __future__ import annotations

import itertools
import sys
from fractions import Fraction as F

from multiresolution import (PartitionTower, RefinementViolation, analyse,
                             band_energy, coverage, decomposition, energies,
                             labelled_cohort, normalize_weights, parent_energies,
                             permutation_null, pruning_error, variance)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


# ---- shared fixtures -------------------------------------------------------
def tower6() -> PartitionTower:
    """N=6: 1 -> 2 -> 4 -> 6 blocks. n_j = [1,2,4,6], d_j = [1,2,2]."""
    return PartitionTower([[0] * 6, [0, 0, 0, 1, 1, 1],
                           [0, 0, 1, 2, 2, 3], [0, 1, 2, 3, 4, 5]])


def tower8() -> PartitionTower:
    """N=8: 1 -> 2 -> 4 -> 8 blocks. n_j = [1,2,4,8], d_j = [1,2,4]."""
    return PartitionTower([[0] * 8, [0, 0, 0, 0, 1, 1, 1, 1],
                           [0, 0, 1, 1, 2, 2, 3, 3], list(range(8))])


U6 = [F(1, 6)] * 6
U8 = [F(1, 8)] * 8


def test_identity_and_root() -> None:
    print("1b. exact accounting, and the root condition")
    p = [1, 0, 1, 1, 0, 0]
    d = decomposition(p, tower6(), U6)
    check("Var = sum E_j + residual", d["E_total"] + d["residual"] == d["variance"],
          f"{d['E_total']}+{d['residual']} vs {d['variance']}")
    check("trivial root: ||p - P_0 p||^2 == Var",
          d["root_energy"] == d["variance"], f"{d['root_energy']} vs {d['variance']}")

    non_trivial = PartitionTower([[0, 0, 0, 1, 1, 1], [0, 0, 1, 2, 2, 3],
                                  [0, 1, 2, 3, 4, 5]], require_trivial_root=False)
    dn = decomposition(p, non_trivial, U6)
    check("non-trivial root: telescoping still sums to ||p - P_0 p||^2",
          dn["E_total"] + dn["residual"] == dn["root_energy"])
    check("non-trivial root: ||p - P_0 p||^2 <= Var (never greater)",
          dn["root_energy"] <= dn["variance"])
    check("non-trivial root with differing block means: strictly < Var",
          dn["root_energy"] < dn["variance"])

    # equality is attainable with a non-trivial root when every root block has the
    # same mean: XOR, partitioned by A, gives mean 1/2 in both root blocks.
    equal_means = PartitionTower([[0, 0, 1, 1], [0, 1, 2, 3]], require_trivial_root=False)
    q = [0, 1, 1, 0]
    dq = decomposition(q, equal_means, [F(1, 4)] * 4)
    check("non-trivial root, equal block means: ||p - P_0 p||^2 == Var",
          dq["root_energy"] == dq["variance"])


def test_constant_label() -> None:
    print("1. constant-label")
    for c in (0, 1):
        d = decomposition([c] * 6, tower6(), U6)
        check(f"p == {c}: every E_j == 0", all(e == 0 for e in d["E"]), str(d["E"]))
        check(f"p == {c}: residual == 0", d["residual"] == 0)
        check(f"p == {c}: Var == 0", d["variance"] == 0)


def test_unequal_weight() -> None:
    print("2. unequal-weight")
    mu = normalize_weights([F(3), F(1), F(1), F(1), F(1), F(1)])
    p = [1, 0, 1, 1, 0, 1]
    t = tower6()
    E = energies(p, t, mu)
    d = decomposition(p, t, mu)
    check("weights normalise to one", sum(mu) == 1)
    check("Var = sum E_j + residual (non-uniform mu)",
          d["E_total"] + d["residual"] == d["variance"])
    for j in range(t.depth() - 1):
        pe = sum(parent_energies(p, t, j, mu).values())
        check(f"E_{j} == sum of parent-local energies", E[j] == pe, f"{E[j]} vs {pe}")


def test_planted_level() -> None:
    print("3. planted-level")
    p = [1, 1, 0, 0, 1, 1, 0, 0]       # differs within L2 blocks, constant within L1 blocks
    E = energies(p, tower8(), U8)
    check("E_0 == 0 (no signal at the first refinement)", E[0] == 0, str(E))
    check("E_1 > 0 (signal localised at level 1)", E[1] > 0, str(E))
    check("E_2 == 0 (nothing left at the finest refinement)", E[2] == 0, str(E))
    check("E_1 == 1/4", E[1] == F(1, 4), str(E[1]))


def test_unresolved_residual() -> None:
    print("4. unresolved-residual")
    coarse = PartitionTower([[0] * 8, [0, 0, 0, 0, 1, 1, 1, 1],
                             [0, 0, 1, 1, 2, 2, 3, 3]])       # finest = 4 blocks, not discrete
    p = [1, 0, 0, 0, 1, 1, 0, 0]
    d = decomposition(p, coarse, U8)
    check("residual > 0 when the finest partition does not determine p",
          d["residual"] > 0, str(d["residual"]))
    check("identity still exact", d["E_total"] + d["residual"] == d["variance"])


def test_permutation_null() -> None:
    print("5. permutation-null (exact test target)")
    t = tower6()
    N = 6
    for S in (2, 3):                    # any success fraction, not only 1/2
        sums = [F(0)] * len(t.dims())
        cnt = 0
        for ones in itertools.combinations(range(N), S):
            lab = [1 if i in ones else 0 for i in range(N)]
            for j, e in enumerate(energies(lab, t, U6)):
                sums[j] += e
            cnt += 1
        p_bar = F(S, N)
        for j, dj in enumerate(t.dims()):
            emp = sums[j] / cnt
            formula = permutation_null(p_bar, dj, N)
            check(f"S={S} d_{j}: empirical mean == p_bar(1-p_bar)/(N-1)*d_j",
                  emp == formula, f"{emp} vs {formula}")
    try:
        permutation_null(F(1, 2), 1, 1)
        check("N <= 1 is rejected", False, "no error raised")
    except ValueError:
        check("N <= 1 is rejected", True)


def test_xor_interaction() -> None:
    print("6. xor-interaction (attribution depends on order)")
    p = [0, 1, 1, 0]                    # A xor B over (0,0),(0,1),(1,0),(1,1)
    mu = [F(1, 4)] * 4
    by_ab = [0, 1, 2, 3]
    order_ab = PartitionTower([[0] * 4, [0, 0, 1, 1], by_ab])   # A then B
    order_ba = PartitionTower([[0] * 4, [0, 1, 0, 1], by_ab])   # B then A
    for name, t in (("A then B", order_ab), ("B then A", order_ba)):
        E = energies(p, t, mu)
        check(f"{name}: first-revealed feature carries zero energy", E[0] == 0, str(E))
        check(f"{name}: second feature carries all of it", E[1] == variance(p, mu), str(E))


def test_refinement_trap() -> None:
    print("7. refinement-trap: non-nested partitions are rejected at construction")
    try:
        PartitionTower([[0, 0, 0, 0], [0, 0, 1, 1], [0, 1, 0, 1]])
        check("straddling partition raises RefinementViolation", False, "no error raised")
    except RefinementViolation:
        check("straddling partition raises RefinementViolation", True)
    try:
        PartitionTower([[0, 0, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]])
        check("nested partition constructs", True)
    except RefinementViolation:
        check("nested partition constructs", False)


def test_pruning_price() -> None:
    print("9.4 pruning price")
    p = [1, 0, 1, 1, 0, 1]
    t = tower6()
    d = decomposition(p, t, U6)
    for A in ([], [0], [1], [0, 1]):
        got = pruning_error(p, t, U6, A)
        want = d["residual"] + sum(d["E"][j] for j in range(len(d["E"])) if j not in A)
        check(f"A={A}: ||p - p_hat_A||^2 == residual + sum_(j not in A) E_j",
              got == want, f"{got} vs {want}")


def test_aggregation() -> None:
    print("9.5 aggregation is additive")
    p = [1, 0, 1, 1, 0, 1]
    t = tower6()
    E = energies(p, t, U6)
    for a, b in ((0, 1), (1, 2), (0, 2), (0, 3)):
        check(f"||(P_{b} - P_{a})p||^2 == sum E_[{a}:{b}]",
              band_energy(p, t, U6, a, b) == sum(E[a:b]))


def test_coverage_and_unknown() -> None:
    print("label coverage; unknown is not failure")
    labels = [1, 0, None, 1, None]
    cov = coverage(labels)
    check("coverage counts labelled and unknown separately",
          (cov["n"], cov["labelled"], cov["unknown"]) == (5, 3, 2), str(cov))
    check("coverage fraction", abs(cov["coverage"] - 0.6) < 1e-12, str(cov["coverage"]))
    check("labelled_cohort excludes unknown", labelled_cohort(labels) == [0, 1, 3])
    t = PartitionTower([[0] * 5, [0, 0, 0, 1, 1], [0, 1, 2, 3, 4]])
    res = analyse(labels, t, [F(1, 5)] * 5)
    check("analyse uses only the labelled cohort", res["cohort"] == [0, 1, 3], str(res["cohort"]))
    check("analyse reports coverage", res["coverage"] == cov)


if __name__ == "__main__":
    print("=" * 70)
    print("test_multiresolution")
    print("=" * 70)
    test_identity_and_root()
    test_constant_label()
    test_unequal_weight()
    test_planted_level()
    test_unresolved_residual()
    test_permutation_null()
    test_xor_interaction()
    test_refinement_trap()
    test_pruning_price()
    test_aggregation()
    test_coverage_and_unknown()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
