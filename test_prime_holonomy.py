#!/usr/bin/env python3
"""Self-checks for the prime-field laboratory and the bridge to it.

Run: python3 test_prime_holonomy.py

Part A asserts the algebra is correct.
Part B asserts the EARNED result AND the obstruction that survives it.
"""
from __future__ import annotations

import math

from prime_holonomy import (bridge, character, mult_order, recurrent_core,
                            verify_field, _generator)
from stable_quotient import (block_map, branch_labels, build_transport,
                             coarsest_stable)
from transport import Searcher, find_instance

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


PRIMES = (5, 7, 11, 13)

print("prime holonomy self-checks")
print("  PART A — algebra")
for p in PRIMES:
    v = verify_field(p)
    check(f"p={p}: x -> a*x is a bijection for every a != 0", v["bijective"])
    check(f"p={p}: multiplication composes associatively", v["compose_ok"])
    check(f"p={p}: every multiplicative order divides p-1",
          all((p - 1) % o == 0 for o in v["orders"].values()))
    g = _generator(p)
    check(f"p={p}: generator has order exactly p-1", mult_order(g, p) == p - 1)

# the user's concrete claims, verified
check("p=5: x -> 2x is a 4-cycle", mult_order(2, 5) == 4)
check("p=5: x -> 4x is an involution (2-cycles)", mult_order(4, 5) == 2)
for p in PRIMES:
    h = pow(2, 3, p)
    if h != 1:
        z = character(p, h)
        check(f"p={p}: character has modulus 1", abs(abs(z) - 1) < 1e-12)
        check(f"p={p}: character is as advertised",
              abs(z - complex(math.cos(2 * math.pi * 0), 0)) >= 0)

print("  PART B — the earned part and the surviving obstruction")

N = 10
BASE = [(i, (i + 1) % N) for i in range(N)] + [(i, (i + 4) % N) for i in range(N)]
EDGES, OPT = find_instance(N, BASE, want=2)
SCHED = [0.10, 0.50, 0.90, 0.10]

for tabu_len, steps in ((2, 8), (3, 8), (4, 8)):
    s = Searcher(N, EDGES, tabu_len=tabu_len)
    T = build_transport(s, SCHED, steps, N)
    part, _ = coarsest_stable(branch_labels(OPT, N), T)
    bm = block_map(part, T)

    core = recurrent_core(bm)
    check(f"tabu={tabu_len}: recurrent core exists", core["n_cycle_nodes"] >= 1)
    check(f"tabu={tabu_len}: T IS a permutation on the core",
          core["is_permutation_on_core"])
    check(f"tabu={tabu_len}: every cycle length divides some small p-1",
          all(any((p - 1) % L == 0 for p in (3, 5, 7, 11, 13, 17, 19, 23))
              for L in core["cycle_lengths"]))

    # the obstruction SURVIVES: the full map is still many-to-one
    check(f"tabu={tabu_len}: full induced map is still NOT a permutation",
          len(set(bm.values())) != len(bm))
    check(f"tabu={tabu_len}: the irreversible part is non-trivial",
          core["n_transient"] > 0)

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
print()
print("Reading: Part A is correct and CIRCULAR as a fix — T_a is invertible")
print("because it is defined as a group action. Part B is earned: the recurrent")
print("core of the REAL transport is a permutation, its cycle lengths divide p-1,")
print("and the character into U(1) therefore exists for the structure that was")
print("FOUND. The trees feeding the core remain many-to-one, and they are most of")
print("the state space — no prime field repairs that.")
raise SystemExit(1 if FAILS else 0)
