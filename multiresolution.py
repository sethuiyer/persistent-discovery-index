#!/usr/bin/env python3
"""
multiresolution.py — weighted detail analysis of a success label over a
behavioural refinement tower.

Finite-resolution and exact. For one fixed, normalised measure `mu`, nested
partitions `P_0` (trivial) .. `P_J`, and a binary label `p`:

    Var_mu(p) = sum_{j=0}^{J-1} ||D_j p||_mu^2 + ||p - P_J p||_mu^2,   D_j = P_{j+1} - P_j

No infinite corpus, scaling exponent or convergence assumption is used — which is
what suits the finite traces PDI actually receives.

Two things this module does NOT do, and says so:

  * It does not call the result causal. `E_j > 0` means the refinement at level j
    adds predictive information *conditional on earlier levels*, not that the
    behaviour caused the outcome (feature order changes attribution; see XOR).
  * It does not present the permutation null as a significance test. The formula

        E_perm[E_j] = p_bar(1-p_bar)/(N-1) * d_j        (N > 1)

    for a uniform permutation of the *observed labels preserving their count* is
    an EXACT synthetic test target. Displayed on real data it is a reference level
    to report alongside raw energy, not a threshold.

Nesting is enforced at construction: a finer block may not straddle two coarser
blocks. Without nesting `D_j` is not an orthogonal projection and the null
carries `tr[(P_{j+1}-P_j)^2]` rather than `n_{j+1} - n_j`.

Stdlib only.
"""
from __future__ import annotations

from typing import Any, Hashable, Sequence


class RefinementViolation(ValueError):
    """A finer block spans two coarser blocks: the partitions are not nested."""


class PartitionTower:
    """Nested partitions of a finite index set.

    `levels[0]` is the coarsest. Each level is a sequence of block ids, one per
    item. A trivial root (one block) is required by default, because the
    accounting identity is a statement about `Var_mu(p)` only when `P_0 p` is the
    global mean.
    """

    def __init__(self, levels: Sequence[Sequence[Hashable]],
                 require_trivial_root: bool = True) -> None:
        if not levels:
            raise ValueError("a tower needs at least one level")
        self.levels = [tuple(L) for L in levels]
        n = len(self.levels[0])
        if any(len(L) != n for L in self.levels):
            raise ValueError("every level must partition the same index set")
        if require_trivial_root and len(set(self.levels[0])) != 1:
            raise ValueError(
                "root partition must be trivial so that P_0 p = mean_mu(p); "
                "pass require_trivial_root=False to inspect a non-trivial root")
        self.require_trivial_root = require_trivial_root
        self._validate_nesting()
        self._n = [len(set(L)) for L in self.levels]

    def _validate_nesting(self) -> None:
        for j in range(len(self.levels) - 1):
            parent: dict = {}
            for child, par in zip(self.levels[j + 1], self.levels[j]):
                prev = parent.setdefault(child, par)
                if prev != par:
                    raise RefinementViolation(
                        f"level {j + 1} block {child!r} straddles coarser blocks "
                        f"{prev!r} and {par!r}: partitions are not nested")

    def depth(self) -> int:
        return len(self.levels)

    def size(self) -> int:
        return len(self.levels[0])

    def n_levels(self) -> list[int]:
        return list(self._n)

    def dims(self) -> list[int]:
        """d_j = n_{j+1} - n_j: the dimension added by each refinement."""
        return [self._n[j + 1] - self._n[j] for j in range(len(self._n) - 1)]

    def restrict(self, idx: Sequence[int]) -> "PartitionTower":
        """Sub-tower on a subset of indices, order preserved (nesting survives)."""
        return PartitionTower([[self.levels[j][i] for i in idx] for j in range(self.depth())],
                              require_trivial_root=self.require_trivial_root)


# --------------------------------------------------------------------------
# weighted operators — arithmetic-agnostic (ints, Fraction, float)
# --------------------------------------------------------------------------
def normalize_weights(w: Sequence[Any]) -> list:
    s = sum(w)
    if s == 0:
        raise ValueError("weights sum to zero")
    return [x / s for x in w]


def weighted_mean(v: Sequence[Any], mu: Sequence[Any]):
    return sum(x * w for x, w in zip(v, mu))


def _block_means(v: Sequence[Any], blocks: Sequence[Hashable], mu: Sequence[Any]):
    tot: dict = {}
    mass: dict = {}
    for x, b, w in zip(v, blocks, mu):
        tot[b] = tot.get(b, 0) + w * x
        mass[b] = mass.get(b, 0) + w
    return {b: tot[b] / mass[b] for b in mass}, mass


def conditional_expectation(v: Sequence[Any], blocks: Sequence[Hashable],
                            mu: Sequence[Any]) -> list:
    """P_j v: the mu-weighted conditional expectation over the given partition."""
    means, _ = _block_means(v, blocks, mu)
    return [means[b] for b in blocks]


def weighted_norm2(v: Sequence[Any], mu: Sequence[Any]):
    return sum(w * x * x for x, w in zip(v, mu))


def detail(v: Sequence[Any], tower: PartitionTower, j: int, mu: Sequence[Any]) -> list:
    """D_j v = P_{j+1} v - P_j v."""
    a = conditional_expectation(v, tower.levels[j], mu)
    b = conditional_expectation(v, tower.levels[j + 1], mu)
    return [y - x for x, y in zip(a, b)]


def energies(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any]) -> list:
    """E_j = ||D_j v||_mu^2 at every refinement."""
    return [weighted_norm2(detail(v, tower, j, mu), mu)
            for j in range(tower.depth() - 1)]


def parent_energies(v: Sequence[Any], tower: PartitionTower, j: int,
                    mu: Sequence[Any]) -> dict:
    """E_{j,C} = sum_{B subset C} mu(B) (mean_B - mean_C)^2, per coarser block C.

    Summing these over C reproduces E_j independently of the norm-of-detail path.
    """
    means_c, mass_c = _block_means(v, tower.levels[j], mu)
    means_b, mass_b = _block_means(v, tower.levels[j + 1], mu)
    child_parent = {}
    for B, C in zip(tower.levels[j + 1], tower.levels[j]):
        child_parent[B] = C
    out = {c: 0 for c in mass_c}
    for B, C in child_parent.items():          # once per child block, not per item
        out[C] = out[C] + mass_b[B] * (means_b[B] - means_c[C]) ** 2
    return out


def residual(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any]):
    """||v - P_J v||_mu^2: variation the finest partition does not resolve."""
    pj = conditional_expectation(v, tower.levels[-1], mu)
    return weighted_norm2([x - y for x, y in zip(v, pj)], mu)


def root_energy(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any]):
    """||v - P_0 v||_mu^2. Equals Var_mu(v) iff the root is trivial."""
    p0 = conditional_expectation(v, tower.levels[0], mu)
    return weighted_norm2([x - y for x, y in zip(v, p0)], mu)


def variance(v: Sequence[Any], mu: Sequence[Any]):
    m = weighted_mean(v, mu)
    return weighted_norm2([x - m for x in v], mu)


def band_energy(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any],
                a: int, b: int):
    """||(P_b - P_a) v||_mu^2 = sum_{j=a}^{b-1} E_j."""
    pa = conditional_expectation(v, tower.levels[a], mu)
    pb = conditional_expectation(v, tower.levels[b], mu)
    return weighted_norm2([y - x for x, y in zip(pa, pb)], mu)


def reconstruct(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any],
                A: Sequence[int]) -> list:
    """p_hat_A = P_0 v + sum_{j in A} D_j v."""
    out = conditional_expectation(v, tower.levels[0], mu)
    for j in A:
        d = detail(v, tower, j, mu)
        out = [x + y for x, y in zip(out, d)]
    return out


def pruning_error(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any],
                  A: Sequence[int]):
    """||v - p_hat_A||_mu^2 = ||v - P_J v||_mu^2 + sum_{j not in A} E_j."""
    return weighted_norm2([x - y for x, y in zip(v, reconstruct(v, tower, mu, A))], mu)


def detail_inner(u: Sequence[Any], w: Sequence[Any], tower: PartitionTower, j: int,
                 mu: Sequence[Any]):
    du, dw = detail(u, tower, j, mu), detail(w, tower, j, mu)
    return sum(a * b * m for a, b, m in zip(du, dw, mu))


def covariation(u: Sequence[Any], w: Sequence[Any], tower: PartitionTower,
                mu: Sequence[Any]):
    """sum_j <D_j u, D_j w>_mu — e.g. the success/cost detail interaction."""
    return sum(detail_inner(u, w, tower, j, mu) for j in range(tower.depth() - 1))


def permutation_null(p_bar, d_j, N: int):
    """E_perm[E_j] = p_bar(1-p_bar)/(N-1) * d_j, for N > 1. An exact test target."""
    if N <= 1:
        raise ValueError("the permutation null needs N > 1")
    return p_bar * (1 - p_bar) / (N - 1) * d_j


def decomposition(v: Sequence[Any], tower: PartitionTower, mu: Sequence[Any]) -> dict:
    E = energies(v, tower, mu)
    return {"E": E, "E_total": sum(E), "residual": residual(v, tower, mu),
            "root_energy": root_energy(v, tower, mu), "variance": variance(v, mu)}


# --------------------------------------------------------------------------
# labelled cohort and coverage — unknown is NOT failure
# --------------------------------------------------------------------------
def labelled_cohort(labels: Sequence[Any]) -> list[int]:
    """Indices with a known label; `None` is `unknown` and is excluded."""
    return [i for i, x in enumerate(labels) if x is not None]


def coverage(labels: Sequence[Any]) -> dict:
    n = len(labels)
    k = len(labelled_cohort(labels))
    return {"n": n, "labelled": k, "unknown": n - k,
            "coverage": (k / n) if n else 0.0}


def analyse(labels: Sequence[Any], tower: PartitionTower, mu: Sequence[Any],
            cohort: Sequence[int] | None = None) -> dict:
    """Supervised detail energies on an explicitly declared labelled cohort.

    `unknown` labels are excluded, never folded into `failure`; coverage is
    reported separately.
    """
    if cohort is None:
        cohort = labelled_cohort(labels)
    p = [labels[i] for i in cohort]
    m = normalize_weights([mu[i] for i in cohort])
    sub = tower.restrict(cohort)
    d = decomposition(p, sub, m)
    n_ = len(p)
    p_bar = weighted_mean(p, m)
    return {"cohort": list(cohort), "p": p, "tower": sub, "mu": m,
            "n_levels": sub.n_levels(), "dims": sub.dims(),
            "E": d["E"], "residual": d["residual"], "variance": d["variance"],
            "root_energy": d["root_energy"],
            "null": [permutation_null(p_bar, dj, n_) for dj in sub.dims()],
            "coverage": coverage(labels)}


# --------------------------------------------------------------------------
def main() -> None:
    from fractions import Fraction as F
    N = 8
    tower = PartitionTower([[0] * N,
                            [0, 0, 0, 0, 1, 1, 1, 1],
                            [0, 0, 1, 1, 2, 2, 3, 3],
                            list(range(N))])
    mu = [F(1, N)] * N
    p = [1, 1, 0, 0, 1, 1, 0, 0]
    d = decomposition(p, tower, mu)
    print("n_j:", tower.n_levels(), " d_j:", tower.dims())
    print("E_j:", d["E"], " residual:", d["residual"], " Var:", d["variance"])
    print("identity:", d["E_total"] + d["residual"] == d["variance"])
    print("null (reference level):", [permutation_null(F(1, 2), dj, N) for dj in tower.dims()])


if __name__ == "__main__":
    main()
