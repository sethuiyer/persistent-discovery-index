#!/usr/bin/env python3
"""Self-checks for the behavioural quotient tower. Run: python3 test_tower.py"""
import math

from agent_profiler import AgentProfiler, inflation_table
from demo_agents import STRATEGIES
from demo_tower import TOWER, LEVEL_NAMES, reached_goal, moves_of, multiset_of_moves
from pdi import PDI
from quotient_tower import QuotientTower, TowerViolation, prefix_tower

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


print("quotient tower self-checks")

all_runs = {n: fn() for n, fn in STRATEGIES.items()}
histories = [h for runs in all_runs.values() for h, _ in runs]

# 1. the refinement law holds on the real corpus
try:
    TOWER.validate(histories)
    check("refinement law holds on the corpus (fast)", True)
except TowerViolation:
    check("refinement law holds on the corpus (fast)", False)

# 2. an INVALID tower is rejected -- a finer class straddling two coarser ones
bad = QuotientTower([
    lambda h: len(h) % 2,                       # Q1 uses parity of length
    lambda h: ("same", len(h)),                 # Q2: every class has ONE coarser parent? no
])
# (Q2 = ('same', n) refines parity only if every n has one parity -- it does.
#  So break it differently: Q2 groups two different parities together.)
bad = QuotientTower([
    lambda h: len(h) % 2,
    lambda h: "collapsed",                      # Q2 puts both parities in ONE class
])
try:
    bad.validate([(1, 2), (1, 2, 3)])
    check("invalid tower (finer class merges two coarser classes) is rejected", False)
except TowerViolation:
    check("invalid tower (finer class merges two coarser classes) is rejected", True)

# 3. n_j equals |H / ~_j| exactly, on the SAME corpus
runs_so = all_runs["shortest_only"]
hist_so = [h for h, _ in runs_so]
idx = PDI(tower=TOWER)
for h, good in runs_so:
    idx.insert(h, live=good)
idx.finalize_explicit()
ok, detail = True, []
for j in range(1, TOWER.depth() + 1):
    classes = {TOWER.signature(h)[:j] for h in hist_so}
    if idx.n.get(j, 0) != len(classes):
        ok = False
        detail.append(f"j={j}: pdi={idx.n.get(j,0)} classes={len(classes)}")
check("n_j == |H / ~_j| for every level", ok)
if detail:
    print("      " + "; ".join(detail))

# 4. same D across strategies under the behavioural tower; different Delta
def prof(name):
    p = AgentProfiler(index=PDI(tower=TOWER))
    for h, good in all_runs[name]:
        p.add_run(h, good)
    return p.profile()

pr = {n: prof(n) for n in STRATEGIES}
Ds = [p["D"] for p in pr.values()]
check("all strategies reach the same behavioural D", max(Ds) - min(Ds) < 1e-12)
check("Delta separates the strategies",
      pr["unpruned"]["delta"] > pr["shortest_only"]["delta"])
check("Delta >= 0", all(p["delta"] >= -1e-12 for p in pr.values()))
check("levels are behaviourally named, not path indices",
      TOWER.depth() == len(LEVEL_NAMES) == 5)
check("horizon is the tower depth, not the path length",
      all(p["horizon"] == 5 for p in pr.values()))

# 5. prefix_tower reproduces the v0.2.0 indexing as a degenerate tower
pt = prefix_tower(lambda x: x)
check("prefix_tower is a valid (degenerate) tower", pt.validate([(1, 2), (1, 3)]) == 2)

# 6. inflation table detects the distinction onset
agents = {n: AgentProfiler(index=PDI(tower=TOWER)) for n in STRATEGIES}
for n, runs in all_runs.items():
    for h, good in runs:
        agents[n].add_run(h, good)
tbl = inflation_table(agents, reference="shortest_only",
                      level_names=[f"Q{i}" for i in range(1, 6)])
check("inflation table reports a distinction onset", "distinction onset" in tbl)
check("inflation table shows unpruned above 2x", "7.35x" in tbl.replace(" ", ""))

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
