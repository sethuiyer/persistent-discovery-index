#!/usr/bin/env python3
"""
quotient_tower.py — behavioural resolution towers.

In PDI <= v0.2.0 the level index j was path length: level j held length-j
prefixes. That is a trie, and n_j was "number of distinct length-j prefixes".

Here the level index means what the theory says it means:

    j = behavioural resolution

Level j is a partition of histories into behavioural classes,

    Q_j : H -> classes_j,        X_j = H / ~_j,

and the tower is required to be a genuine refinement tower:

    REFINEMENT LAW
        Q_{j+1}(h) = Q_{j+1}(h')   =>   Q_j(h) = Q_j(h')

Finer classes refine coarser ones; they never contradict them. Given the law,
each level-(j+1) class has a unique level-j parent, so the classes still form a
tree -- but n_j is now exactly |H / ~_j|, the number of behavioural classes at
resolution j, and no longer counts prefixes.

With a tower, the ledger reads:

    n_j = |H / ~_j|                        behavioural classes at resolution j
    L_j = number of resolution-j classes containing a persistent history

which is the construction the invariant was always stated over.
"""
from __future__ import annotations

from typing import Any, Callable, Hashable, Iterable, Sequence


class TowerViolation(ValueError):
    """The refinement law is violated: a finer class straddles two coarser ones."""


class QuotientTower:
    """A refining sequence of behavioural quotient maps.

    levels[0] is the coarsest. Each level is a callable history -> hashable class.
    """

    def __init__(
        self,
        levels: Sequence[Callable[[Any], Hashable]],
        eps: Callable[[int], float] | None = None,
    ) -> None:
        if not levels:
            raise ValueError("a tower needs at least one level")
        self.levels = list(levels)
        self.eps_fn = eps if eps is not None else (lambda j: 2.0 ** -j)

    # ------------------------------------------------------------------ shape
    def depth(self) -> int:
        return len(self.levels)

    def eps(self, j: int) -> float:
        return self.eps_fn(j)

    def signature(self, h: Any) -> tuple:
        """(Q_1(h), ..., Q_K(h)) — the class chain of one history."""
        return tuple(level(h) for level in self.levels)

    # ------------------------------------------------------------- validation
    def validate(self, histories: Iterable[Any]) -> int:
        """Check the refinement law on a corpus. Returns the number of histories
        checked; raises TowerViolation on the first conflict.

        The check is exact: for each level j we record the coarser prefix that a
        level-j class has been seen with. If the same level-j class ever appears
        with a different coarser prefix, the tower is not a refinement tower.
        """
        seen: list[dict] = [{} for _ in self.levels]   # seen[j][cls] = coarser prefix
        n = 0
        for h in histories:
            sig = self.signature(h)
            for j in range(1, len(sig)):
                coarser = sig[:j]
                prev = seen[j].setdefault(sig[j], coarser)
                if prev != coarser:
                    raise TowerViolation(
                        f"level {j + 1} class {sig[j]!r} has two coarser prefixes: "
                        f"{prev!r} and {coarser!r}"
                    )
            n += 1
        return n

    def validate_pairs(self, histories: Sequence[Any]) -> int:
        """Exhaustive O(|H|^2) version, kept for small corpora and for testing
        the fast check. Slow by construction."""
        H = list(histories)
        sigs = [self.signature(h) for h in H]
        for i in range(len(H)):
            for k in range(i + 1, len(H)):
                for j in range(1, len(sigs[i])):
                    if sigs[i][j] == sigs[k][j] and sigs[i][:j] != sigs[k][:j]:
                        raise TowerViolation(
                            f"histories {i},{k} share level-{j+1} class but differ coarser"
                        )
        return len(H)


def prefix_tower(label: Callable[[Any], Hashable]) -> "_PrefixTower":
    """The v0.2.0 behaviour: level j is the length-j labelled prefix. Provided so
    the old indexing is expressible as a (degenerate) tower, and so existing
    results stay reproducible."""
    return _PrefixTower(label)


class _PrefixTower:
    """Level j = first j labelled symbols. Level count is set by the longest
    history seen, so this deliberately duck-types QuotientTower rather than
    subclassing it."""

    def __init__(self, label: Callable[[Any], Hashable]) -> None:
        self.label = label

    def eps(self, j: int) -> float:
        return 2.0 ** -j

    def signature(self, h: Sequence[Any]) -> tuple:
        # accept either a bare step sequence or a Run/Turn carrying .steps, so
        # callers do not have to remember which the tower wants
        steps = getattr(h, "steps", h)
        return tuple(self.label(x) for x in steps)

    def validate(self, histories: Iterable[Any]) -> int:
        n = 0
        for _ in histories:
            n += 1
        return n
