#!/usr/bin/env python3
"""
cofinal_mesh.py — what §2.3 can and cannot claim.

v0.27.0's §2.3 asserted that "cofinal in resolution" was enough to preserve the
persistent exponent `D`. It is not. Cofinality is a statement about the SET of
levels; it says nothing about their *spacing*. The missing hypothesis is that
the subsampled mesh is asymptotically dense in log-scale. Writing

    s_m = -log eps_m          (so s_m -> inf)

the sufficient condition is

    s_{m+1} / s_m  ->  1.

Under that hypothesis a monotone sandwich preserves BOTH exponents `D` and `S`,
and therefore `Delta = S - D`. Without it, `D` can survive while `S` and `Delta`
do not — which is the correct content of §2.4, once §2.4's witness is made a
genuine quotient tower.

Nothing here is estimated. The counterexample uses the exact identity

    log2 n_j / j = max(j, 2 k_m)/j + log2(1 + 2^{-|j - 2 k_m|}) / j

so the double-exponential tower is never materialised.

Witness (monotone in L, n, and n - L):
    k_m = 2^(2^m),  k_0 = 2,  k_{m+1} = k_m^2
    for k_m <= j < k_{m+1}:   L_j = 2^j,   n_j = 2^j + 2^(2 k_m)
    explicit first level:     L_1 = 2,     n_1 = 3

    all levels     : D = 1, S = 2, Delta = 1
    sparse j=k_m-1 : D = 1, S = 1, Delta = 0     (mesh not dense)

Run: python3 cofinal_mesh.py
"""
from __future__ import annotations

import math


# --------------------------------------------------------------------------
# the witness
# --------------------------------------------------------------------------
def burst_depths(M: int) -> list[int]:
    """k_m = 2^(2^m), starting at k_0 = 2. k_{m+1} = k_m^2."""
    ks, k = [], 2
    for _ in range(M):
        ks.append(k)
        k *= k
    return ks


def band_of(j: int, ks: list[int]) -> int:
    """Index m with k_m <= j < k_{m+1} (for j >= k_0)."""
    m = 0
    while m + 1 < len(ks) and j >= ks[m + 1]:
        m += 1
    return m


def counts(j: int, ks: list[int]) -> tuple[int, int]:
    """(L_j, n_j). j = 1 is set explicitly; the band formula says nothing about it."""
    if j == 1:
        return 2, 3
    m = band_of(j, ks)
    return 2 ** j, 2 ** j + 2 ** (2 * ks[m])


def ratio_L(j: int) -> float:
    """log2 L_j / j. L_j = 2^j at every level, including j = 1."""
    return 1.0


def ratio_n(j: int, ks: list[int]) -> float:
    """log2 n_j / j, via the exact identity (no big integers).

    The correction uses log1p: log2(1 + 2^-d) must not be computed as
    log2(1.0 + 2^-d), which rounds the correction to 0 for d > 53. log1p prevents
    that cancellation, but 2^-d itself can still UNDERFLOW for large d, so the
    computed correction can be a numerical 0 where the analytic one is positive.
    The analytic bounds (burst_peak / sparse_ratio) remain authoritative: a
    numerical zero is not a claim that the correction is exactly zero.
    """
    if j == 1:
        return math.log2(3.0) / 1.0
    b = 2 * ks[band_of(j, ks)]
    corr = math.log1p(2.0 ** (-abs(j - b))) / math.log(2.0)
    return max(j, b) / j + corr / j


def burst_peak(m: int, ks: list[int]) -> tuple[float, float, float]:
    """(peak, upper, correction) of log2 n_j / j at the burst j = k_m.

    Exact:  2 + log2(1 + 2^-k_m)/k_m,  correction in (0, 1/k_m].
    """
    km = ks[m]
    corr = math.log1p(2.0 ** (-km)) / math.log(2.0) / km
    return 2.0 + corr, 2.0 + 1.0 / km, corr


def sparse_point(m: int, ks: list[int]) -> int:
    """j = k_m - 1 — just *before* a burst, in the previous band."""
    return ks[m] - 1


def sparse_ratio(m: int, ks: list[int]) -> tuple[float, float, float]:
    """(ratio, upper, correction) at j = k_m - 1.

    The correction is returned directly rather than as ratio - 1: for large m it
    is far below the ulp of 1.0, so `ratio - 1.0` rounds to 0 while the
    correction itself is still a positive, representable number.
    """
    j = sparse_point(m, ks)
    b = 2 * ks[band_of(j, ks)]
    corr = math.log1p(2.0 ** (-abs(j - b))) / math.log(2.0) / j
    return 1.0 + corr, 1.0 + 1.0 / j, corr


def mesh_ratio(m: int, ks: list[int]) -> float:
    """s_{j_{m+1}} / s_{j_m} for the sparse point sequence j_m = k_m - 1.

    -> infinity, so the subsample is NOT asymptotically dense.
    """
    return (ks[m + 1] - 1) / (ks[m] - 1)


# --------------------------------------------------------------------------
# the positive theorem: a dense mesh preserves both exponents
# --------------------------------------------------------------------------
def local_mesh_ratios(s: list[float]) -> list[float]:
    """s_{m+1}/s_m over a subsampled scale sequence."""
    return [s[i + 1] / s[i] for i in range(len(s) - 1)]


def sandwich_upper(counts_map: dict[int, float], subsample: list[int], s: dict[int, float]) -> float:
    """sup over the subsample of log2 c / s  -- the bound that squeezes the full
    tower when the mesh is dense."""
    return max(math.log2(counts_map[j]) / s[j] for j in subsample if counts_map.get(j, 0) > 0)


# --------------------------------------------------------------------------
# finite corpora and the empty-persistence convention
# --------------------------------------------------------------------------
def finite_corpus_exponents(N: int) -> dict:
    """A corpus with at most N histories has n_j, L_j <= N at every level, so
    with s_j = j both ratios are <= log2(N)/j -> 0. The asymptotic exponents are
    identically zero; any positive printed value is a finite-window statistic."""
    return {"S": 0.0, "D": 0.0, "D_empty_persistence": 0.0, "bound": math.log2(N)}


def exponent_with_convention(counts: dict[int, float], s: dict[int, float]) -> tuple[float, str]:
    """sup of log2 c_j / s_j, with the empty-persistence convention made explicit:
    if every count is zero the ratio is undefined (log 0) and is defined here as 0.
    Matches pdi.PDI.exponents, which skips c == 0."""
    live = [j for j, c in counts.items() if c > 0]
    if not live:
        return 0.0, "empty-persistence convention: log 0 undefined -> 0"
    return max(math.log2(counts[j]) / s[j] for j in live), "computed"


# --------------------------------------------------------------------------
def main() -> None:
    ks = burst_depths(7)
    print("cofinal_mesh — dense mesh preserves D and S; sparse does not")
    print(f"k_m: {ks}")
    print()
    print(f"{'m':>2} {'k_m':>22} {'burst peak':>12} {'sparse ratio':>13} {'mesh ratio':>12}")
    for m in range(len(ks) - 1):
        peak, _, _ = burst_peak(m, ks)
        sr, _, _ = sparse_ratio(m + 1, ks)
        print(f"{m:>2} {ks[m]:>22} {peak:>12.6f} {sr:>13.6f} {mesh_ratio(m, ks):>12.1f}")

    print()
    print("all levels     : D=1  S=2  Delta=1")
    print("sparse j=k_m-1 : D=1  S->1  Delta->0")
    print()
    for N in (10, 1000, 10 ** 6):
        e = finite_corpus_exponents(N)
        print(f"finite corpus N={N:<8}: S={e['S']}  D={e['D']}  (|ratio| <= {e['bound']:.1f}/j -> 0)")
    d, why = exponent_with_convention({1: 0, 2: 0}, {1: 1, 2: 2})
    print(f"empty persistence: D={d}  [{why}]")


if __name__ == "__main__":
    main()
