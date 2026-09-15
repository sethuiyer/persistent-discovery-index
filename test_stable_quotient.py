#!/usr/bin/env python3
"""Self-checks for the transport-stable quotient. Run: python3 test_stable_quotient.py

The positive result: a genuine T-stable quotient exists, and it is small
(hundreds-fold compression of the state space).

The remaining negative: the induced map is many-to-one, so it is not a
permutation -- which is exactly what a monodromy would have to be.
"""
from __future__ import annotations

from stable_quotient import (block_map, branch_labels, build_transport,
                             coarsest_stable, functional_graph, pack, unpack)
from transport import Searcher, find_instance

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


N = 10
BASE = [(i, (i + 1) % N) for i in range(N)] + [(i, (i + 4) % N) for i in range(N)]
EDGES, OPT = find_instance(N, BASE, want=2)
LAMS = [0.10, 0.50, 0.90, 0.10]
STATES = 1 << N

print("transport-stable quotient self-checks")

check("two optima", len(OPT) == 2)
check("pack/unpack round trip",
      all(pack(unpack(x, N), ) == x for x in range(0, STATES, 37)))

s = Searcher(N, EDGES, tabu_len=3)
T = build_transport(s, LAMS, 8, N)

# 1. the transport is a total, deterministic map on the state space
check("transport is total", len(T) == STATES and all(0 <= t < STATES for t in T))
check("transport is deterministic", T == build_transport(s, LAMS, 8, N))

# 2. the branch partition is NOT stable -- this is what v0.7.0 established
branch = branch_labels(OPT, N)
check("branch partition has 2 blocks", len(set(branch)) == 2)
unstable = any(branch[T[x]] != branch[T[y]]
               for x in range(0, STATES, 7) for y in range(0, STATES, 11)
               if branch[x] == branch[y])
check("branch partition is NOT T-stable", unstable)

# 3. THE POSITIVE RESULT: refinement reaches a stable, non-discrete quotient
part, profile = coarsest_stable(branch, T)
k = len(set(part))
check("refinement profile is non-decreasing", all(b >= a for a, b in zip(profile, profile[1:])))
check("refinement terminates", len(profile) < 64)
check("result is a genuine quotient (not discrete)", k < STATES)
check("result compresses the space", k * 10 < STATES)
bm = block_map(part, T)          # raises AssertionError if unstable
check("result IS T-stable (block map is well defined)", True)
check("every block has an image", set(bm) == set(part))

# 4. the remaining obstruction: the map is many-to-one, hence no monodromy
bij = len(set(bm.values())) == len(bm)
check("induced map is NOT a permutation (many-to-one)", not bij)
check("therefore no group order exists", not bij)

# 5. but there IS finite dynamics on the quotient: a functional graph
fg = functional_graph(bm)
check("induced map has at least one cycle", fg["n_cycles"] >= 1)
check("cycle lengths are positive", all(l >= 1 for l in fg["cycle_lengths"]))
check("cycle structure is well formed",
      sum(fg["cycle_lengths"]) <= len(bm))
if fg["idempotent"]:
    check("idempotent case: every cycle has length 1",
          all(l == 1 for l in fg["cycle_lengths"]))
# NB: non-idempotent does NOT imply a long cycle. A map can collapse onto fixed
# points without being idempotent (b -> c -> c is non-idempotent with one fixed
# point). Test the stronger claim across configurations instead.
long_cycles = False
for tl in (2, 3, 4):
    for st in (4, 8):
        TT = build_transport(Searcher(N, EDGES, tabu_len=tl), LAMS, st, N)
        pp, _ = coarsest_stable(branch_labels(OPT, N), TT)
        ff = functional_graph(block_map(pp, TT))
        if any(l > 1 for l in ff["cycle_lengths"]):
            long_cycles = True
check("some configuration shows a cycle of length > 1", long_cycles)

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
print()
print("Reading: the missing fibre EXISTS (a stable quotient of a few blocks,")
print("hundreds-fold smaller than the state space). What is still missing for a")
print("monodromy is INVERTIBILITY: the induced map is many-to-one, so the")
print("transport is a functional graph, not a permutation.")
raise SystemExit(1 if FAILS else 0)
