#!/usr/bin/env python3
"""
demo_sudoku.py — PDI on a real search problem with a unique solution.

Sudoku is the purest case: the solution is a single thin path, so the persistent
ledger L_j is one node per puzzle per depth, and *everything else the solver does
is transient*. `D = 0` and `Delta = S` by construction. Every number is a
statement about waste.

Three strategies, the same two puzzles:

    first/asc     scan cells in order, try 1..9
    mrv/asc       fewest-candidates-first
    first/random  scan cells in order, random value order

Run: python3 demo_sudoku.py
"""
from __future__ import annotations

import math
import time

from agent_profiler import AgentProfiler, compare, format_profile, inflation_table
from pdi import PDI
from quotient_tower import prefix_tower
from sudoku import PUZZLES, STRATEGIES, run_records, solve

PUZZLE_SET = ("easy", "medium")
LABEL = lambda s: (s.args.get("cell"), s.args.get("value"))


def profile_strategy(name, kw, cap=300_000):
    """Collect PDI runs from both puzzles, and the cheap per-depth counts."""
    runs = []
    depth_counts = [0] * 82
    total = backtracks = 0
    t0 = time.time()
    for pname in PUZZLE_SET:
        tr = solve(PUZZLES[pname], cap=cap, **kw)
        for j, c in enumerate(tr.nodes_at_depth):
            depth_counts[j] += c
        total += tr.total_nodes
        backtracks += tr.backtracks
        rs, _ = run_records(PUZZLES[pname], label=name, **kw)
        runs.extend(rs)
    prof = AgentProfiler(index=PDI(tower=prefix_tower(LABEL)))
    for r in runs:
        prof.add_run(r, r.succeeded)
    return {"name": name, "runs": runs, "depth": depth_counts, "total": total,
            "backtracks": backtracks, "profile": prof.profile(),
            "secs": time.time() - t0, "agent": prof}


if __name__ == "__main__":
    print("=" * 78)
    print("PDI on Sudoku — where does the search start generating dead branches?")
    print("=" * 78)
    print(f"  puzzles: {', '.join(PUZZLE_SET)}   (each has a UNIQUE solution)")
    print("  L_j = 1 node per puzzle per depth  ->  D = 0, Delta = S")
    print("  so every number below is a statement about WASTE.")

    results = []
    for name, kw in STRATEGIES.items():
        results.append(profile_strategy(name, kw))

    # ---------------- the per-depth profile: where the bullshit starts ------
    print("\n" + "=" * 78)
    print("the search tree, by depth   (n_j = nodes visited at depth j)")
    print("=" * 78)
    peak = max(max(r["depth"]) for r in results)
    for r in results:
        print(f"\n  {r['name']}   total nodes = {r['total']:,}   "
              f"backtracks = {r['backtracks']:,}")
        for j in range(1, 82):
            n = r["depth"][j]
            if n:
                bar = "#" * max(1, int(50 * n / peak))
                mark = "  <- peak" if n == max(r["depth"]) else ""
                print(f"    d={j:>2} {n:>6} {bar}{mark}")

    # ---------------- PDI's own numbers ------------------------------------
    print("\n" + "=" * 78)
    print("PDI summary")
    print("=" * 78)
    for r in results:
        p = r["profile"]
        peak_j = max(range(1, 82), key=lambda j: r["depth"][j])
        first_fan = next((j for j in range(1, 82)
                          if r["depth"][j] > 4 * max(1, r["depth"][j - 1])
                          and r["depth"][j] > 50), None)
        print(f"\n  {r['name']}")
        print(f"    total nodes   : {r['total']:,}")
        print(f"    D={p['D']:.6f}  S={p['S']:.6f}  Delta={p['delta']:.6f}")
        print(f"    peak of n_j   : depth {peak_j} ({r['depth'][peak_j]:,} nodes)")
        print(f"    first blow-up : depth {first_fan} " if first_fan else
              "    first blow-up : none")
        print(f"    L_j at depth  : {p['rows'][0]['L'] if p['rows'] else 0} per puzzle")

    # ---------------- where the work actually accumulates -------------------
    print("\n" + "=" * 78)
    print("where the nodes are:  share of all visits, by depth band")
    print("=" * 78)
    bands = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 53)]
    print(f"  {'strategy':<15} {'total':>9} " +
          "".join(f"{f'd{a}-{b}':>12}" for a, b in bands))
    for r in results:
        tot = sum(r["depth"][j] for j in range(1, 82)) or 1
        cells = []
        for a, b in bands:
            share = sum(r["depth"][j] for j in range(a, b + 1)) / tot
            cells.append(f"{share*100:>11.1f}%")
        print(f"  {r['name']:<15} {r['total']:>9,} " + "".join(cells))

    print("\n  n_j at selected depths")
    depths = [1, 10, 15, 20, 25, 27, 30, 40, 53]
    print(f"  {'strategy':<15}" + "".join(f"{('d'+str(d)):>9}" for d in depths))
    for r in results:
        print(f"  {r['name']:<15}" + "".join(f"{r['depth'][d]:>9,}" for d in depths))

    print("\n  inflation vs the cheapest strategy, at selected depths")
    ref = min(results, key=lambda x: x["total"])
    print(f"  (reference = {ref['name']})")
    print(f"  {'strategy':<15}" + "".join(f"{('d'+str(d)):>9}" for d in depths))
    for r in results:
        cells = []
        for d in depths:
            base = ref["depth"][d]
            cells.append("        -" if not base else f"{r['depth'][d]/base:>8.2f}x")
        print(f"  {r['name']:<15}" + "".join(f"{c:>9}" for c in cells))

    print("\n" + "=" * 78)
    print("reading")
    print("=" * 78)
    print("""
  Sudoku has a unique solution, so the persistent ledger is one thin path per
  puzzle and EVERYTHING ELSE is transient. For the easy+medium pair, L_j = 2 at
  every depth. All the interesting structure is in n_j.

  Where the waste lives: first/asc puts most of its nodes in depth band 21-30,
  which is where it starts guessing instead of deducing. MRV never visits more
  than 5 nodes at any depth, because it never enters that regime.

  On the summary statistics. Both D and S take their sup at DEPTH 1 here -- they
  report how many values were tried in the first cell, not how large the search
  became. They order the strategies correctly by luck of correlation, but they do
  not measure the thing anyone cares about. The per-depth profile and the totals
  do. This is the 'practical scale' question in its most concrete form yet: the
  asymptotic summaries are the wrong instrument at this scale, and the
  finite-scale diagnostics are the right one.""")
