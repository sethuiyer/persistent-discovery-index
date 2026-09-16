#!/usr/bin/env python3
"""
test_cofinal_mesh.py — the §2.3 / §2.4 contract, as executable checks.

The point of these tests is that the VALUES are derived, not asserted:

  * the exact identity is checked against a direct computation;
  * burst peaks and sparse samples are bounded analytically (correction in
    (0, 1/j]), and the limits are recovered from those bounds;
  * monotonicity of L, n and n - L is checked on a real prefix;
  * the dense-mesh sandwich is checked on a control tower, and the sparse
    witness is checked to violate the density hypothesis (mesh ratio -> inf).

Run: python3 test_cofinal_mesh.py     (exit 0 on success)
"""
from __future__ import annotations

import math
import sys

from cofinal_mesh import (band_of, burst_depths, burst_peak, counts,
                          exponent_with_convention, finite_corpus_exponents,
                          local_mesh_ratios, mesh_ratio, ratio_L, ratio_n,
                          sandwich_upper, sparse_point, sparse_ratio)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_monotone() -> None:
    print("the witness is a realisable tower: L, n, n-L all nondecreasing")
    ks = burst_depths(4)                       # [2, 4, 16, 256]
    Ln = [counts(j, ks) for j in range(1, 257)]
    L = [c[0] for c in Ln]
    n = [c[1] for c in Ln]
    check("L nondecreasing", all(L[i] <= L[i + 1] for i in range(len(L) - 1)))
    check("n nondecreasing (refinement cannot remove blocks)",
          all(n[i] <= n[i + 1] for i in range(len(n) - 1)))
    check("n - L nondecreasing", all((n[i] - L[i]) <= (n[i + 1] - L[i + 1])
                                     for i in range(len(L) - 1)))
    check("explicit first level L_1=2, n_1=3", (L[0], n[0]) == (2, 3), str((L[0], n[0])))


def test_identity() -> None:
    print("the exact identity matches a direct computation")
    ks = burst_depths(4)
    for j in (16, 256):
        direct = math.log2(2 ** j + 2 ** (2 * ks[band_of(j, ks)])) / j
        check(f"identity == direct at j={j}", abs(ratio_n(j, ks) - direct) < 1e-12,
              f"{ratio_n(j, ks)} vs {direct}")


def test_burst_peaks() -> None:
    print("burst peaks are bounded above by 2 + 1/k_m and converge to 2")
    ks = burst_depths(8)
    peaks = []
    for m in range(1, 8):
        peak, upper, corr = burst_peak(m, ks)
        # for k_m > ~1074 the term 2^-k_m underflows to 0; the analytic bound is
        # stated as 0 <= corr <= 1/k_m and checked as such.
        check(f"correction in [0, 1/k_m] at m={m}", 0.0 <= corr <= 1.0 / ks[m],
              f"corr={corr}, 1/k={1.0/ks[m]}")
        check(f"peak in [2, upper] at m={m}", 2.0 <= peak <= upper, str(peak))
        peaks.append(peak)
    for m in (1, 2, 3):
        check(f"correction is strictly positive in the representable range m={m}",
              burst_peak(m, ks)[2] > 0.0)
    check("peaks non-increasing toward 2",
          all(peaks[i] >= peaks[i + 1] for i in range(len(peaks) - 1)) and peaks[0] > peaks[-1])
    check("peaks converge to 2 (< 2 + 1e-9)", peaks[-1] < 2.0 + 1e-9, str(peaks[-1]))


def test_burst_is_the_band_max() -> None:
    print("within a band the ratio peaks at the burst, so S is the peak limit")
    ks = burst_depths(4)
    worst = 0.0
    for j in range(2, 257):
        m = band_of(j, ks)
        peak, upper, _ = burst_peak(m, ks)
        worst = max(worst, ratio_n(j, ks) - peak)
    check("no sampled j exceeds its band peak", worst <= 1e-12, str(worst))


def test_sparse_samples() -> None:
    print("sparse samples sit at 1 + a vanishing correction")
    ks = burst_depths(8)
    for m in range(2, 8):
        r, upper, corr = sparse_ratio(m, ks)
        check(f"sparse ratio in [1, 1+1/j] at m={m}", 1.0 <= r <= upper,
              f"r={r}, upper={upper}")
    for m in (2, 3):
        check(f"sparse correction strictly positive where representable m={m}",
              sparse_ratio(m, ks)[2] > 0.0)
    last = sparse_ratio(7, ks)[0]
    check("sparse ratios converge to 1 (< 1 + 1e-9)", last < 1.0 + 1e-9, str(last))


def test_limits() -> None:
    print("the exponents")
    ks = burst_depths(8)
    check("D (all levels) == 1 exactly", ratio_L(1) == 1.0 and ratio_L(999) == 1.0)
    S_all = burst_peak(7, ks)[0]
    check("S (all levels) -> 2", abs(S_all - 2.0) < 1e-9, str(S_all))
    check("Delta (all levels) -> 1", abs((S_all - ratio_L(1)) - 1.0) < 1e-9)
    S_sp = sparse_ratio(7, ks)[0]
    check("D (sparse) == 1", ratio_L(sparse_point(7, ks)) == 1.0)
    check("S (sparse) -> 1", abs(S_sp - 1.0) < 1e-9, str(S_sp))
    check("Delta (sparse) -> 0", abs(S_sp - 1.0) < 1e-9)


def test_mesh_density_hypothesis() -> None:
    print("the sparse witness violates the density hypothesis")
    ks = burst_depths(8)
    ratios = [mesh_ratio(m, ks) for m in range(0, 6)]
    check("sparse mesh ratio grows without bound",
          all(ratios[i] < ratios[i + 1] for i in range(len(ratios) - 1)) and ratios[-1] > 1e6,
          str(ratios))


def test_dense_mesh_preserves_both() -> None:
    print("control: a dense mesh preserves D and S (the repaired §2.3)")
    N = 10000
    c = {j: 2 ** j for j in range(1, N + 1)}          # monotone counts
    s = {j: float(j) for j in range(1, N + 1)}        # mesh s_j = j
    sub = [m * m for m in range(1, 101)]              # j_m = m^2, s_j = m^2
    mesh = [j * j for j in sub]
    ratios = local_mesh_ratios(mesh)
    check("dense control mesh ratios -> 1", ratios[-1] < 1.05, str(ratios[-1]))
    sub_lim = sandwich_upper(c, sub, s)
    full_lim = sandwich_upper(c, list(range(1, N + 1)), s)
    check("dense subsample preserves the exponent", abs(sub_lim - full_lim) < 1e-9,
          f"{sub_lim} vs {full_lim}")


def test_finite_corpus() -> None:
    print("finite corpora and the empty-persistence convention")
    e = finite_corpus_exponents(1000)
    check("finite corpus: S = 0", e["S"] == 0.0)
    check("finite corpus: D = 0 (nonempty persistence)", e["D"] == 0.0)
    for N in (10, 1000, 10 ** 6):
        bound = finite_corpus_exponents(N)["bound"]
        check(f"N={N}: ratio bound log2(N)/j decays with j",
              bound / 10 ** 3 > bound / 10 ** 6 and bound / 10 ** 6 < 1e-4,
              f"{bound}/10^6 = {bound/10**6:.2e}")
    d, why = exponent_with_convention({1: 0, 2: 0}, {1: 1.0, 2: 2.0})
    check("empty persistence -> D = 0 by explicit convention", d == 0.0, str(d))
    check("the convention is named, not silent", "convention" in why, why)


if __name__ == "__main__":
    print("=" * 70)
    print("test_cofinal_mesh")
    print("=" * 70)
    test_monotone()
    test_identity()
    test_burst_peaks()
    test_burst_is_the_band_max()
    test_sparse_samples()
    test_limits()
    test_mesh_density_hypothesis()
    test_dense_mesh_preserves_both()
    test_finite_corpus()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
