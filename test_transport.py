#!/usr/bin/env python3
"""Self-checks for the transport experiment. Run: python3 test_transport.py

This is a NEGATIVE result, so the tests assert the negative: that the loop is
not a well-defined map on branches, and that refining the fibre to greedy-descent
basins does not repair it. If someone later builds a genuine monodromy, these
tests should FAIL -- which is the point.
"""
from __future__ import annotations

from transport import (Searcher, Transport, all_optima, compose, energy,
                       find_instance, inverse, order_of)

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


N = 12
BASE = [(i, (i + 1) % N) for i in range(N)] + [(i, (i + 4) % N) for i in range(N)]
EDGES, OPT = find_instance(N, BASE, want=2)
LAMS = [0.10, 0.50, 0.90, 0.10]

print("transport self-checks")

# 1. the problem is genuinely degenerate
check("exactly two optima", len(OPT) == 2)
check("the two optima are complements",
      all(a != b for a, b in zip(OPT[0], OPT[1])))
check("both optima have the same energy", energy(OPT[0], EDGES) == energy(OPT[1], EDGES))
check("enumeration agrees with direct evaluation",
      all(energy(o, EDGES) <= energy(tuple((m >> i) & 1 for i in range(N)), EDGES)
          for m in range(1 << N) for o in [OPT[0]]))

# 2. the searcher is deterministic -- required for the inverse test to mean anything
s = Searcher(N, EDGES, tabu_len=3)
x0 = OPT[0]
check("searcher is deterministic",
      s.run(x0, 0.5, 8) == s.run(x0, 0.5, 8))
check("settle is deterministic", s.settle(x0) == s.settle(x0))

# 3. non-identity transport exists at the level of representatives
T = Transport(Searcher(N, EDGES, tabu_len=3), OPT, steps_per_leg=16)
fwd = T.permutation(LAMS)
check("representative transport is bijective", len(set(fwd.values())) == len(fwd))
check("representative transport can be NON-identity", fwd != {b: b for b in fwd})

# 4. THE decisive negative result: the loop is not determined by the branch
images, _ = T.branch_determined(LAMS)
check("branch images are NOT single-valued (state drift, not monodromy)",
      any(len(v) > 1 for v in images.values()))

# 5. refining the fibre to greedy basins does not repair it
d = T.fibre_determined(LAMS)
check("there are many basins", d["n_basins"] > 10)
check("basin fibre is ALSO not determined", d["n_ambiguous"] > 0)

# 6. the algebraic flags that would signal a monodromy are not stable
flags = []
for tabu_len in (2, 3, 4, 5):
    for steps in (4, 8, 16, 32):
        TT = Transport(Searcher(N, EDGES, tabu_len=tabu_len), OPT, steps_per_leg=steps)
        p = TT.permutation(LAMS)
        r = TT.permutation([LAMS[0], LAMS[2], LAMS[1], LAMS[0]])
        flags.append((r == inverse(p), TT.permutation(TT.power(LAMS, 2)) == compose(p, p)))
check("rev=inv is not uniformly true", any(not f[0] for f in flags))
check("sq=sq is not uniformly true", any(not f[1] for f in flags))

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
print()
print("Meaning: non-identity transport exists, but it is STATE DRIFT, not a")
print("monodromy. If a future change makes these tests fail, that is the")
print("interesting event -- it would mean a genuine branch map appeared.")
raise SystemExit(1 if FAILS else 0)
