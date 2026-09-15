#!/usr/bin/env python3
"""
demo_agents.py — PDI as an agent reasoning profiler, on a real search problem.

Setup: an N x N grid, start top-left, goal bottom-right. The task is to find
EVERY shortest path from start to goal. Because the task fixes the solution set,
every complete strategy discovers the SAME persistent structure -- so any
difference in S and Delta is purely algorithmic.

A family of strategies is profiled, parameterised by how much wandering the
heuristic permits (slack = how much further from the goal a step may go than the
remaining budget allows). slack = 0 is an admissible heuristic; larger slack is
looser guidance; `unpruned` has none.

Same task. Same persistent structure. Different discovery cost.

Run: python3 demo_agents.py
"""
from __future__ import annotations

from typing import Iterator

from agent_profiler import AgentProfiler, compare, format_profile

N = 6
START = (0, 0)
GOAL = (N - 1, N - 1)
D_LEN = 2 * (N - 1)          # shortest-path length (right/down only)
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def in_grid(c) -> bool:
    return 0 <= c[0] < N and 0 <= c[1] < N


def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _enum(bounded: bool, slack: int | None) -> list:
    """Enumerate paths up to D_LEN steps.

    bounded=True  : monotone only (right/down)          -> only shortest paths
    slack is None : no heuristic                       -> maximum wandering
    slack = k     : allow a step that is up to k further from the goal than the
                    remaining budget permits            -> k=0 is admissible
    """
    runs: list = []

    def rec(cell, path, visited):
        runs.append((tuple(path), cell == GOAL and len(path) - 1 == D_LEN))
        if len(path) - 1 == D_LEN:
            return
        for dr, dc in NEIGHBOURS:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not in_grid(nxt) or nxt in visited:
                continue
            if bounded and not (dr == 1 or dc == 1):
                continue                      # monotone steps only
            if slack is not None:
                remaining = D_LEN - (len(path) - 1) - 1
                if manhattan(nxt, GOAL) > remaining + slack:
                    continue
            rec(nxt, path + [nxt], visited | {nxt})

    rec(START, [START], {START})
    return runs


# --------------------------------------------------------------------------
# strategies: every one of them discovers all shortest paths
# --------------------------------------------------------------------------
def strategy_shortest_only():
    return _enum(bounded=True, slack=None)


def strategy_admissible():
    return _enum(bounded=False, slack=0)


def strategy_slack1():
    return _enum(bounded=False, slack=1)


def strategy_slack2():
    return _enum(bounded=False, slack=2)


def strategy_unpruned():
    return _enum(bounded=False, slack=None)


STRATEGIES = {
    "shortest_only": strategy_shortest_only,
    "admissible": strategy_admissible,
    "slack_1": strategy_slack1,
    "slack_2": strategy_slack2,
    "unpruned": strategy_unpruned,
}


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 74)
    print(f"grid {N}x{N}  start={START}  goal={GOAL}  shortest length={D_LEN}")
    print("task: find EVERY shortest path  ->  solution set is fixed by the task")
    print("=" * 74)

    agents = {}
    for name, fn in STRATEGIES.items():
        p = AgentProfiler()
        for path, ok in fn():
            p.add_run(path, ok)
        agents[name] = p

    for name in ("shortest_only", "unpruned"):
        print(format_profile(name, agents[name].profile()))

    print(compare(agents))

    print("\n" + "=" * 74)
    print("reading")
    print("=" * 74)
    print("""
  D      fixed by the task: every strategy found all shortest paths, so the
         persistent ledgers are identical.
  S      what the strategy actually walked through.
  Delta  transient scaffolding that bought no persistent structure.
  STOP   first resolution where persistent yield collapses -- finer than that
         the agent is generating exploration, not knowledge.

  Run the same table over prompt variants, planners, beam widths, temperatures
  or tool policies and it becomes a measurement rather than an opinion.""")
