#!/usr/bin/env python3
"""Self-checks for the agent profiler. Run: python3 test_profiler.py"""
from agent_profiler import AgentProfiler
from demo_agents import STRATEGIES, D_LEN

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


print("agent profiler self-checks")

profs = {}
for name, fn in STRATEGIES.items():
    p = AgentProfiler()
    for path, ok in fn():
        p.add_run(path, ok)
    profs[name] = p.profile()

# 1. every strategy discovers all shortest paths -> identical persistent ledger
Ds = [pr["D"] for pr in profs.values()]
check("all strategies reach the same D", max(Ds) - min(Ds) < 1e-12)
check("D > 0 (task has real persistent structure)", Ds[0] > 0)
check("every strategy found every solution",
      all(pr["successes"] == profs["shortest_only"]["successes"] for pr in profs.values()))

# 2. identical live counts, different full counts
lv = {k: [r["L"] for r in pr["rows"]] for k, pr in profs.items()}
fv = {k: [r["n"] for r in pr["rows"]] for k, pr in profs.items()}
check("identical live counts L_j across strategies", len({tuple(v) for v in lv.values()}) == 1)
check("distinct full counts n_j across strategies", len({tuple(v) for v in fv.values()}) > 1)

# 3. overhead ordering: no guidance costs more
d = {k: pr["delta"] for k, pr in profs.items()}
check("shortest_only overhead == 0", abs(d["shortest_only"]) < 1e-12)
check("admissible overhead == 0", abs(d["admissible"]) < 1e-12)
check("slack_1 overhead == 0", abs(d["slack_1"]) < 1e-12)
check("slack_2 overhead > 0", d["slack_2"] > 1e-12)
check("unpruned overhead > slack_2 overhead", d["unpruned"] > d["slack_2"])
check("Delta >= 0 everywhere", all(v >= -1e-12 for v in d.values()))

# 4. stop-level detection fires only for wasteful strategies
stops = {}
for name, fn in STRATEGIES.items():
    p = AgentProfiler()
    for path, ok in fn():
        p.add_run(path, ok)
    stops[name] = p.stop_level(0.10)
check("shortest_only: no STOP needed (yield never collapses)", stops["shortest_only"] is None)
check("unpruned: STOP is detected", stops["unpruned"] is not None)
# NB: on this small task the yield only collapses at the finest observed level
# (level 11 of 11), so STOP lands there rather than early. A deeper task shows
# the early STOP the profiler is for.
check("unpruned STOP lies in the observed range",
      stops["unpruned"] is not None and 1 < stops["unpruned"] <= D_LEN + 1)

# 5. yield table is well-formed
for name, pr in profs.items():
    ok = all(0.0 <= r["yield"] <= 1.0 for r in pr["rows"])
    if not ok:
        FAILS.append(f"yield out of range for {name}")
check("all yields in [0,1]", not any("yield out of range" in f for f in FAILS))

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
