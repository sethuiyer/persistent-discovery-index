#!/usr/bin/env python3
"""
prime_holonomy.py — the F_p^x laboratory, and the honest bridge to it.

PART A — the laboratory.

Over a prime field, multiplicative transport is invertible BY CONSTRUCTION:

    F = F_p^x = {1..p-1},   T_a(x) = a*x mod p,   a != 0

p prime => every nonzero a is invertible => T_a in Sym(F), for free. A loop with
edge labels a_1..a_k has residual h = prod a_i mod p, with finite order dividing
p-1. Since F_p^x is cyclic, h = g^k for a generator g and

    phi(gamma) = exp(2*pi*i*k/(p-1))

is a genuine character of a finite group into U(1). All of that is correct.

PART B — the honest part, which is the whole point.

Invertibility in Part A is POSITED, not earned. T_a is a group action because we
DEFINED it as one. That does not confer invertibility on a discovery process; it
replaces the process with a group action. "Primes give invertibility for free" is
true only in the sense that we assumed a group.

The obstruction from v0.8.0 is that the ACTUAL transport is many-to-one. If the
residual h = prod a_i is a free choice of labels, then h != 1 is trivially
achievable and carries no information about any search.

So the only version of this that is earned is:

    the RECURRENT CORE of the real transport is already invertible.

A cycle of a functional graph IS a cyclic group action -- T restricted to a cycle
is a permutation by definition, of order = the cycle length. That is real, it is
not posited, and it is exactly what the v0.8.0 experiment observed (cycles of
length 1, 2 and 4). Part B extracts that core from the real transport and asks
whether it embeds into F_p^x -- i.e. whether the observed order divides p-1, so
that the character phi exists for the structure we FOUND rather than one we chose.

The trees feeding the cycles are the irreversible part. No prime field fixes them.

Run: python3 prime_holonomy.py
"""
from __future__ import annotations

import math
from collections import Counter

from stable_quotient import (block_map, branch_labels, build_transport,
                             coarsest_stable, functional_graph)
from transport import Searcher, find_instance


# --------------------------------------------------------------------------
# PART A — the laboratory (correct, but invertibility is assumed)
# --------------------------------------------------------------------------
def mult_order(a: int, p: int) -> int:
    o, v = 1, a % p
    while v != 1:
        v = (v * a) % p
        o += 1
    return o


def verify_field(p: int) -> dict:
    F = list(range(1, p))
    bijective = all(len({(a * x) % p for x in F}) == p - 1 for a in F)
    compose_ok = all(((a * b) % p) * x % p == a * (b * x) % p
                     for a in F for b in F for x in F)
    res_ok = all(math.prod(labels) % p == math.prod(labels) % p for labels in [[1]])
    # residual of a loop is the product of its labels
    loops = [[2, 3], [2, 2, 2], [3, 4], [1, 1]]
    residuals = {tuple(l): math.prod(l) % p for l in loops}
    return {"p": p, "bijective": bijective, "compose_ok": compose_ok,
            "residuals": residuals,
            "orders": {a: mult_order(a, p) for a in F}}


def character(p: int, h: int) -> complex:
    """phi(h) = exp(2*pi*i*k/(p-1)) where h = g^k. Well defined since F_p^x cyclic."""
    if h % p == 0:
        raise ValueError("h must be nonzero")
    for k in range(p - 1):
        g = _generator(p)
        if pow(g, k, p) == h % p:
            return complex(math.cos(2 * math.pi * k / (p - 1)),
                           math.sin(2 * math.pi * k / (p - 1)))
    raise ValueError("no discrete log found")


def _generator(p: int) -> int:
    for g in range(2, p):
        if mult_order(g, p) == p - 1:
            return g
    return 1


# --------------------------------------------------------------------------
# PART B — the bridge: the recurrent core of the REAL transport
# --------------------------------------------------------------------------
def recurrent_core(bm: dict) -> dict:
    """Split the induced map into its recurrent core (cycles) and the trees.

    T restricted to a cycle is a permutation -- invertibility that is EARNED, not
    assumed. The trees are the irreversible part.
    """
    fg = functional_graph(bm)
    cycle_nodes = {b for c in fg["cycles"] for b in c}
    # a cycle node's image stays on its cycle; everything else is transient
    forward = {b for b in bm if bm.get(b) in cycle_nodes and b not in cycle_nodes}
    perm = all(len({bm[b] for b in c}) == len(c) and all(bm[b] in c for b in c)
               for c in fg["cycles"])
    return {"cycles": fg["cycles"], "cycle_lengths": fg["cycle_lengths"],
            "n_cycle_nodes": len(cycle_nodes), "n_blocks": len(bm),
            "n_transient": len(bm) - len(cycle_nodes),
            "feeds_cycle": len(forward),
            "is_permutation_on_core": perm}


def bridge(n: int, schedule, tabu_len: int, steps: int) -> dict:
    base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
    edges, opt = find_instance(n, base, want=2)
    s = Searcher(n, edges, tabu_len=tabu_len)
    T = build_transport(s, schedule, steps, n)
    part, _ = coarsest_stable(branch_labels(opt, n), T)
    bm = block_map(part, T)
    core = recurrent_core(bm)

    # does each observed cycle length divide p-1 for some small prime?
    embeddable = {}
    for L in set(core["cycle_lengths"]):
        primes = [p for p in (3, 5, 7, 11, 13, 17, 19, 23)
                  if p > L and (p - 1) % L == 0]
        embeddable[L] = primes[:3]
    core["embeddable"] = embeddable
    return core


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 86)
    print("PART A — the F_p^x laboratory (invertibility POSITED, not earned)")
    print("=" * 86)
    for p in (5, 7, 11, 13):
        v = verify_field(p)
        g = _generator(p)
        cyc = [pow(g, k, p) for k in range(p - 1)]
        print(f"\n  p={p}:  bijective={v['bijective']}  compose={v['compose_ok']}  "
              f"generator={g}  cyclic order: {' -> '.join(map(str, cyc + [cyc[0]]))}")
        print(f"        loop residuals (product of labels mod p): "
              f"{ { '+'.join(map(str,k)): val for k, val in v['residuals'].items() } }")
        print(f"        orders: {v['orders']}")
        h = pow(2, 3, p)
        if h != 1:
            ph = character(p, h)
            print(f"        character phi(h={h}) = {ph.real:+.4f}{ph.imag:+.4f}i   "
                  f"(a genuine U(1) character)")

    print()
    print("=" * 86)
    print("PART B — the EARNED part: recurrent core of the real transport")
    print("=" * 86)
    print("  A cycle of a functional graph IS a cyclic group action. T restricted to")
    print("  a cycle is a permutation by definition. That invertibility is not posited.")
    for n in (10, 12):
        for tabu_len, steps in ((2, 8), (3, 8), (4, 8)):
            core = bridge(n, [0.10, 0.50, 0.90, 0.10], tabu_len, steps)
            print(f"\n  n={n} tabu={tabu_len} steps={steps}")
            print(f"    stable quotient      : {core['n_blocks']} blocks")
            print(f"    recurrent core       : {core['n_cycle_nodes']} nodes in "
                  f"{len(core['cycles'])} cycle(s), lengths={core['cycle_lengths']}")
            print(f"    transient (irreversible): {core['n_transient']} blocks feed the core")
            print(f"    T is a permutation on the core : {core['is_permutation_on_core']}")
            print(f"    embeds in F_p^x (L | p-1)      : {core['embeddable']}")

    print()
    print("=" * 86)
    print("verdict")
    print("=" * 86)
    print("""
  PART A is correct and clean, and it is also CIRCULAR as an answer to the
  obstruction: T_a(x) = a*x is invertible because we defined a group action.
  It models the target; it does not produce it. A loop residual h = prod a_i is a
  property of labels we chose, so "h != 1" tells you nothing about any search.

  PART B is the part that is earned. The real transport's recurrent core IS
  invertible, because a cycle is one by definition -- and this is exactly the
  structure v0.8.0 observed (cycles of length 1, 2, 4). Those lengths divide p-1
  for small primes, so a character phi into U(1) genuinely exists FOR THE
  STRUCTURE THAT WAS FOUND.

  So the honest statement is narrower than "primes give invertibility for free":

      invertibility is recovered ON THE RECURRENT CORE of the transport,
      and THAT core embeds into F_p^x, so the phase is a real character of a
      real finite group.

  What no prime field repairs is the rest: the trees feeding the core remain
  many-to-one, and they are most of the state space.
""")
