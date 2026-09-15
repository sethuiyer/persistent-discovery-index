#!/usr/bin/env python3
"""
demo.py — the operational content of the theorem.

Agent A and Agent B discover the SAME persistent structure (identical live set)
but B spends far more transient work getting there. The theorem says:

    D is the same for both        (intrinsic, cofinal-invariant)
    S differs                     (presentation)
    Delta = S - D differs         (presentation)

Same geometry. Different discovery cost. And the theorem guarantees the
comparison is well-defined: D is held fixed while Delta varies.
"""
from __future__ import annotations

import math
from pdi import PDI, Status

H = 8  # observation horizon


# --------------------------------------------------------------------------
# corpus construction
# --------------------------------------------------------------------------
def live_traces(H: int):
    """The persistent boundary: every binary trace of length H."""
    for mask in range(2 ** H):
        yield tuple((mask >> i) & 1 for i in range(H))


def distractors(prefix, k):
    """2^k immediately-terminating children -- transient exploration."""
    for d in range(2 ** k):
        yield tuple(prefix) + (("d", k, d),)


def build(agent: str) -> PDI:
    idx = PDI()
    for t in live_traces(H):
        idx.insert(t)
    if agent == "B":
        # at each live node at level k, spawn 2^k dead-end children
        for k in range(1, H - 1):   # keep distractors STRICTLY below the horizon
            for mask in range(2 ** k):
                prefix = tuple((mask >> i) & 1 for i in range(k))
                for t in distractors(prefix, k):
                    idx.insert(t)
    idx.recompute_statuses()
    return idx


# --------------------------------------------------------------------------
def report(name: str, idx: PDI):
    n, L = idx.ledgers()
    ex = idx.exponents()
    print(f"\n  {name}")
    print(f"    {'j':>3} {'n_j':>10} {'L_j':>9} {'live?':>6}")
    for j in range(1, idx.max_level + 1):
        live = idx.L.get(j, 0)
        ok = idx.L.get(j,0) <= idx.L.get(j+1,0) if j < idx.max_level else "-"
        print(f"    {j:>3} {n.get(j,0):>10} {live:>9} {str(ok):>6}")
    print(f"    D (persistent)  = {ex['D']:.6f}")
    print(f"    S (exploration) = {ex['S']:.6f}")
    print(f"    Delta           = {ex['delta']:.6f}")
    print(f"    L_j non-decreasing: {idx.live_non_decreasing()}")
    return ex


if __name__ == "__main__":
    print("=" * 74)
    print(f"PDI demo   |   horizon H={H}")
    print("=" * 74)

    A = build("A")
    B = build("B")
    exA = report("Agent A  (clean discovery)", A)
    exB = report("Agent B  (same boundary, heavy transient branching)", B)

    print("\n" + "=" * 74)
    print("Same geometry. Different discovery cost.")
    print("=" * 74)
    same_L = all(A.L.get(j, 0) == B.L.get(j, 0) for j in range(A.max_level + 1))
    print(f"  identical persistent ledgers L_j : {same_L}")
    print(f"  same D                           : {abs(exA['D']-exB['D']) < 1e-12}")
    print(f"  different S                      : {abs(exA['S']-exB['S']) > 1e-9}")
    print(f"  different Delta                  : {abs(exA['delta']-exB['delta']) > 1e-9}")
    print(f"  Delta_A = {exA['delta']:.6f}   Delta_B = {exB['delta']:.6f}")


    # ---------------------------------------------------------- reindexing
    print("\n" + "=" * 74)
    print("cofinal reindexing: D invariant, Delta NOT")
    print("=" * 74)

    def exps_at(idx, levels):
        def sup(counts, scale):
            v = [math.log(counts.get(j,0))/ (scale*j*math.log(2.0))
                 for j in levels if counts.get(j,0) > 0]
            return max(v) if v else 0.0
        S = sup(idx.n, 1); D = sup(idx.L, 1)
        return D, S, S - D

    for name, idx in (("A", A), ("B", B)):
        allv  = list(range(1, idx.max_level + 1))
        evenv = [j for j in allv if j % 2 == 0]          # P' = P_{2j}
        D1, S1, d1 = exps_at(idx, allv)
        D2, S2, d2 = exps_at(idx, evenv)
        print(f"  Agent {name}:")
        print(f"     full presentation : D={D1:.6f}  S={S1:.6f}  Delta={d1:.6f}")
        print(f"     reindexed (even)  : D={D2:.6f}  S={S2:.6f}  Delta={d2:.6f}")
        print(f"     -> D invariant: {abs(D1-D2)<1e-9}    Delta invariant: {abs(d1-d2)<1e-9}")

    # ---------------------------------------------------------------- STOP
    print("\n" + "=" * 74)
    print("STOP policy on physical resolution (R4)")
    print("=" * 74)
    for j in range(1, A.max_level + 1):
        ok = A.refine_worthwhile(j, gain=1.0, cost=0.35)
        n, L = A.n.get(j, 0), A.L.get(j, 0)
        print(f"  level {j}  eps={A.eps(j):.5f}  L/n={L}/{n}  refine_worthwhile={ok}")
    print("  (yield ratio L_j/n_j is what makes finer resolution worth its cost;")
    print("   agent B drives that ratio down without changing the boundary.)")

    # --------------------------------------------------------------- cache
    print("\n" + "=" * 74)
    print("hierarchical reuse (cache on nodes, refine only on miss)")
    print("=" * 74)
    A.root.payload = "ROOT"
    node = A.root
    for depth in range(1, 5):
        lab = 1
        node = node.children[lab] if lab in node.children else list(node.children.values())[0]
        node.payload = f"cached@{node.level}"
    payload, used = A.lookup_or_refine((1, 1, 1, 1, 1, 1, 1, 1), lambda a, b: a == b)
    print(f"  query hit at level {used}: payload={payload!r}   reuses={A.stats['reuses']}")
