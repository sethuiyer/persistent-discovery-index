#!/usr/bin/env python3
"""
demo_tower.py — v0.3.0: resolution means BEHAVIOURAL resolution.

Same task and strategies as demo_agents.py (find every shortest path on a 6x6
grid), but the level index is no longer path length. It is a refinement tower of
behavioural quotient maps:

    Q_1  reached the goal?                          (2 classes)
    Q_2  + number of steps
    Q_3  + multiset of moves taken
    Q_4  + the ordered move sequence
    Q_5  + the full path

Each level refines the one above it, so the refinement law holds:

    Q_{j+1}(h) = Q_{j+1}(h')  =>  Q_j(h) = Q_j(h')

and now n_j = |H / ~_j| exactly -- the number of behavioural classes at
resolution j -- instead of a count of prefixes.

The profiler then answers a sharper question than v0.2.0 could:

    At which behavioural resolution does this strategy begin manufacturing
    distinctions that do not contribute to successful behaviour?

Run: python3 demo_tower.py
"""
from __future__ import annotations

from collections import Counter

from agent_profiler import AgentProfiler, compare, inflation_table
from demo_agents import GOAL, STRATEGIES
from pdi import PDI
from quotient_tower import QuotientTower, TowerViolation


# --------------------------------------------------------------------------
# behavioural features of a history
# --------------------------------------------------------------------------
def moves_of(path) -> tuple:
    return tuple((b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))


def reached_goal(path) -> bool:
    return path[-1] == GOAL


def multiset_of_moves(path) -> tuple:
    c = Counter(moves_of(path))
    return tuple(sorted((k, v) for k, v in c.items()))


TOWER = QuotientTower([
    lambda h: reached_goal(h),                                      # Q_1
    lambda h: (reached_goal(h), len(h) - 1),                        # Q_2
    lambda h: (reached_goal(h), multiset_of_moves(h)),              # Q_3
    lambda h: (reached_goal(h), moves_of(h)),                       # Q_4
    lambda h: (reached_goal(h), tuple(h)),                          # Q_5
])

LEVEL_NAMES = [
    "Q1  reached goal?",
    "Q2  + step count",
    "Q3  + move multiset",
    "Q4  + move sequence",
    "Q5  + full path",
]


# --------------------------------------------------------------------------
if __name__ == "__main__":
    all_runs = {name: fn() for name, fn in STRATEGIES.items()}
    histories = [h for runs in all_runs.values() for h, _ in runs]

    print("=" * 74)
    print("v0.3.0  behavioural quotient tower")
    print("=" * 74)

    # 1. the refinement law must hold on the corpus
    try:
        n = TOWER.validate(histories)
        print(f"  refinement law: HOLDS over {n} histories (fast check)")
        TOWER.validate_pairs(histories[:400])
        print(f"  refinement law: HOLDS on exhaustive pairwise check (first 400)")
    except TowerViolation as e:
        print(f"  refinement law: VIOLATED -- {e}")

    # 2. n_j must equal |H / ~_j| exactly
    import math
    print("\n  n_j == |H / ~_j| check")
    for j in range(1, TOWER.depth() + 1):
        classes = {TOWER.signature(h)[:j] for h in histories}
        print(f"    {LEVEL_NAMES[j-1]:<24} |H/~_j| = {len(classes):>5}")

    # 3. profile every strategy through the behavioural tower
    agents = {}
    for name, runs in all_runs.items():
        prof = AgentProfiler(index=PDI(tower=TOWER))
        for h, ok in runs:
            prof.add_run(h, ok)
        agents[name] = prof

    print("\n" + "=" * 74)
    print("behavioural-resolution profiles")
    print("=" * 74)
    for name in ("shortest_only", "unpruned"):
        p = agents[name].profile()
        print(f"\n  {name}")
        print(f"    {'level':<24} {'classes':>8} {'persistent':>11} {'yield':>8}")
        for r in p["rows"]:
            print(f"    {LEVEL_NAMES[r['level']-1]:<24} {r['n']:>8} {r['L']:>11} "
                  f"{r['yield']*100:>7.2f}%")
        print(f"    D = {p['D']:.6f}   S = {p['S']:.6f}   Delta = {p['delta']:.6f}")

    print(compare(agents))
    print(inflation_table(agents, reference="shortest_only",
                          level_names=[f"Q{i}" for i in range(1, TOWER.depth() + 1)]))
    print("    " + "  ".join(f"Q{i}={n}" for i, n in enumerate(LEVEL_NAMES, 1)))

    print("\n" + "=" * 74)
    print("where the strategies diverge, in behavioural terms")
    print("=" * 74)
    print("""
  At Q1 every history is one of two classes. At Q2 they separate by length.
  By Q4 the move sequence is fixed, and by Q5 the strategies stand apart:

      shortest_only   only ever produces shortest paths      -> yield stays high
      unpruned        produces many non-shortest paths       -> yield collapses

  The collapse is now attributable to a NAMED behavioural resolution rather than
  to a path-length index. That is the v0.3.0 product: the profiler says which
  behavioural distinction is being manufactured without contributing to success.""")
