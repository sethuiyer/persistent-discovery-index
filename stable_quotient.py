#!/usr/bin/env python3
"""
stable_quotient.py — construct the transport-stable quotient.

v0.7.0 left a precise failure: the loop transport T is not well defined on
branches, nor on greedy-descent basins. Two states in the same fibre are sent to
different fibres, so there is no map, hence no monodromy, hence nothing for a
Berry phase to be a phase of.

The obvious next move is not to keep guessing fibres. It is to CONSTRUCT the
coarsest one that works.

    A partition pi is T-STABLE if T is well defined on its blocks, i.e. for all
    x ~ y in pi,  T(x) ~ T(y).

Equivalently: the refinement key of a state is (block(x), block(T(x))). Split
blocks whose members disagree on that key and repeat. The fixpoint is the
coarsest T-stable refinement of whatever partition you started from. This is
ordinary partition refinement -- DFA minimisation, bisimulation quotienting.

What that buys us:

  * starting from the BRANCH partition, the fixpoint answers the sharp question
    "what minimal extra information, beyond which optimum we are near, makes the
    transport a genuine map?"
  * the number of blocks at the fixpoint is a real number: 2 means branches were
    already enough, |S| means the transport is maximally state dependent and no
    quotient structure exists at all
  * on the fixpoint the induced map pi -> pi is a function by construction, so it
    finally makes sense to ask whether it is a permutation, and of what order

This works over the FULL state space (2^n states), so the quotient is exact
rather than sampled. n is kept small because the state space is the point.

Run: python3 stable_quotient.py
"""
from __future__ import annotations

from transport import Searcher, find_instance, fmt, inverse, compose, order_of


# --------------------------------------------------------------------------
# exact transport map over the whole state space
# --------------------------------------------------------------------------
def pack(bits) -> int:
    return sum(b << i for i, b in enumerate(bits))


def unpack(x: int, n: int) -> tuple:
    return tuple((x >> i) & 1 for i in range(n))


def build_transport(searcher: Searcher, schedule, steps: int, n: int):
    """T[x] for every state. Deterministic, memoised by construction."""
    T = [0] * (1 << n)
    for x in range(1 << n):
        y = unpack(x, n)
        for lam in schedule[1:]:
            y = searcher.run(y, lam, steps)
        T[x] = pack(y)
    return T


def branch_labels(optima, n: int):
    """Nearest optimum by Hamming distance, ties by index. Total on states."""
    opts = [pack(o) for o in optima]
    return [min(range(len(opts)),
                key=lambda i: (bin(x ^ opts[i]).count("1"), i))
            for x in range(1 << n)]


# --------------------------------------------------------------------------
# partition refinement
# --------------------------------------------------------------------------
def refine(part, T):
    """One T-stability refinement round. Returns (new_partition, n_blocks)."""
    ids: dict = {}
    new = [0] * len(part)
    for x in range(len(part)):
        key = (part[x], part[T[x]])
        b = ids.get(key)
        if b is None:
            b = len(ids)
            ids[key] = b
        new[x] = b
    return new, len(ids)


def coarsest_stable(part, T, cap: int = 64):
    """Iterate to the coarsest T-stable refinement of `part`."""
    profile = [len(set(part))]
    for _ in range(cap):
        part, k = refine(part, T)
        profile.append(k)
        # stable when no block split in the last round
        if k == profile[-2]:
            break
    return part, profile


def block_map(part, T):
    """The induced map on blocks. Well defined by stability -- assert it."""
    out = {}
    for x, b in enumerate(part):
        t = part[T[x]]
        if out.setdefault(b, t) != t:
            raise AssertionError(f"partition not T-stable at block {b}")
    return out


def functional_graph(bm):
    """Characterise the induced map: its cycles and whether it is idempotent.

    A monodromy is a PERMUTATION, so the cycle structure is the whole question.
    A map that collapses blocks (many-to-one) is a functional graph with trees
    feeding cycles, not a group element.
    """
    cycles, done = [], set()
    for start in bm:
        path, cur = [], start
        while cur not in done and cur not in path:
            path.append(cur)
            cur = bm[cur]
        if cur in path:
            cycles.append(path[path.index(cur):])
        done.update(path)
    idem = all(bm[bm[b]] == bm[b] for b in bm)
    return {"cycles": cycles, "n_cycles": len(cycles),
            "cycle_lengths": sorted(len(c) for c in cycles),
            "idempotent": idem}


# --------------------------------------------------------------------------
if __name__ == "__main__":
    for n in (10, 12):
        base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
        edges, opt = find_instance(n, base, want=2)
        print("=" * 84)
        print(f"transport-stable quotient   |   n={n}, {len(edges)} edges, "
              f"{len(opt)} optima, {1<<n} states")
        print("=" * 84)

        lam0, lam1, lam2 = 0.10, 0.50, 0.90
        gamma = [lam0, lam1, lam2, lam0]

        for tabu_len in (2, 3, 4):
            for steps in (4, 8):
                s = Searcher(n, edges, tabu_len=tabu_len)
                T = build_transport(s, gamma, steps, n)
                branch = branch_labels(opt, n)
                n_states = 1 << n

                part, profile = coarsest_stable(branch, T)
                k = len(set(part))
                bm = block_map(part, T)
                bij = len(set(bm.values())) == len(bm)
                o = order_of(bm) if bij else None
                fg = functional_graph(bm)

                sizes = {}
                for b in part:
                    sizes[b] = sizes.get(b, 0) + 1
                biggest = max(sizes.values())

                print(f"\n  tabu={tabu_len} steps={steps}")
                print(f"    branch partition      : 2 blocks")
                print(f"    refinement profile    : {' -> '.join(map(str, profile))}")
                print(f"    coarsest stable       : {k} blocks "
                      f"({'DISCRETE -- no quotient structure' if k == n_states else 'genuine quotient'})")
                print(f"    largest block         : {biggest} states")
                print(f"    induced map bijective : {bij}"
                      + (f"   order={o}" if bij else "   (many-to-one)"))
                print(f"    functional graph      : {fg['n_cycles']} cycle(s), "
                      f"lengths={fg['cycle_lengths']}, idempotent={fg['idempotent']}")
                print(f"    reduced from {n_states} states by "
                      f"{round(n_states / k, 2)}x")
