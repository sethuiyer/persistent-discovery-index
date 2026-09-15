#!/usr/bin/env python3
"""
agent_profiler.py — PDI as an agent reasoning profiler.

Question this answers:

    How much exploration did this agent perform to discover how much
    persistent behavioural structure?

Feed it agent runs. Each run is a path of abstracted states plus whether it
succeeded. The profiler builds a PDI over the runs and reports, per resolution
level:

    n_j    explored prefixes
    L_j    prefixes that lie on a successful run  (persistent)
    Y_j    L_j / n_j                             (persistent yield)

and the three numbers

    D     = limsup log L_j / (-log eps_j)   persistent complexity   (task)
    S     = limsup log n_j / (-log eps_j)   exploration complexity  (algorithm)
    Delta = S - D                            discovery overhead      (algorithm)

Because D is cofinal-invariant and Delta is not, the intended reading is:

    D      how much structure the task has
    S      how much structure this algorithm walked through
    Delta  how much of that walk was transient

That makes Delta a legitimate *algorithm* comparison even though it is not a
property of the task. The task supplies the geometry; the algorithm supplies the
overhead.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Callable, Hashable, Iterable, Optional, Sequence

from pdi import PDI, Status


class AgentProfiler:
    """Accumulate agent runs, then profile them."""

    def __init__(
        self,
        label: Optional[Callable[[Any], Hashable]] = None,
        eps: Optional[Callable[[int], float]] = None,
    ) -> None:
        self.pdi = PDI(label=label if label is not None else (lambda x: x), eps=eps)
        self.runs = 0
        self.successes = 0

    # ------------------------------------------------------------------ input
    def add_run(self, path: Sequence[Any], succeeded: bool) -> None:
        """Record one agent trajectory. `path` is the sequence of abstracted
        states visited; `succeeded` says whether it reached the goal.

        Explored prefixes always count toward n_j. Only prefixes on a successful
        run count toward L_j.
        """
        self.pdi.insert(path, live=succeeded)
        self.runs += 1
        self.successes += bool(succeeded)

    def add_runs(self, runs: Iterable[tuple[Sequence[Any], bool]]) -> "AgentProfiler":
        for path, ok in runs:
            self.add_run(path, ok)
        return self

    # --------------------------------------------------------------- profiling
    def profile(self) -> dict:
        self.pdi.finalize_explicit()
        n, L = self.pdi.ledgers()
        H = self.pdi.max_level

        def sup(counts: dict[int, int]) -> float:
            vals = [math.log(counts[j]) / (-math.log(self.pdi.eps(j)))
                    for j in range(1, H + 1) if counts.get(j, 0) > 0]
            return max(vals) if vals else 0.0

        S, D = sup(n), sup(L)

        rows = []
        for j in range(1, H + 1):
            nj, lj = n.get(j, 0), L.get(j, 0)
            rows.append({
                "level": j,
                "eps": self.pdi.eps(j),
                "n": nj,
                "L": lj,
                "yield": (lj / nj) if nj else 0.0,
            })

        return {
            "rows": rows,
            "D": D, "S": S, "delta": S - D,
            "runs": self.runs, "successes": self.successes,
            "horizon": H,
        }

    def stop_level(self, threshold: float = 0.10) -> Optional[int]:
        """First resolution at which persistent yield collapses below threshold.

        Everything finer than this level is mostly transient generation, so this
        is where an adaptive policy should stop refining.
        """
        rows = self.profile()["rows"]
        for r in rows:
            if r["yield"] < threshold:
                return r["level"]
        return None


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def format_profile(name: str, prof: dict, threshold: float = 0.10) -> str:
    out = [f"\n  {name}",
           f"    runs={prof['runs']}  successes={prof['successes']}",
           f"    {'level':>5} {'eps':>9} {'full':>9} {'live':>8} {'yield':>8}"]
    for r in prof["rows"]:
        out.append(f"    {r['level']:>5} {r['eps']:>9.5f} {r['n']:>9} {r['L']:>8} "
                   f"{r['yield']*100:>7.2f}%")
    out.append(f"    D (persistent)  = {prof['D']:.6f}")
    out.append(f"    S (exploration) = {prof['S']:.6f}")
    out.append(f"    Delta           = {prof['delta']:.6f}")
    return "\n".join(out)


def compare(agents: dict[str, AgentProfiler], threshold: float = 0.10) -> str:
    """Side-by-side benchmark table. This is the deliverable."""
    profs = {k: v.profile() for k, v in agents.items()}
    stops = {k: v.stop_level(threshold) for k, v in agents.items()}

    w = max(len(k) for k in agents) + 2
    out = ["", "=" * 74,
           "agent-efficiency benchmark  (same task, different strategies)",
           "=" * 74,
           f"  {'agent':<{w}} {'D':>9} {'S':>9} {'Delta':>9} {'waste':>8} {'STOP at':>8}"]
    for k, p in profs.items():
        waste = (p["delta"] / p["S"]) if p["S"] else 0.0
        stop = stops[k] if stops[k] is not None else "-"
        out.append(f"  {k:<{w}} {p['D']:>9.6f} {p['S']:>9.6f} {p['delta']:>9.6f} "
                   f"{waste*100:>7.1f}% {str(stop):>8}")

    Ds = [p["D"] for p in profs.values()]
    out.append("")
    if max(Ds) - min(Ds) < 1e-9:
        out.append(f"  all agents reached the SAME persistent structure  D = {Ds[0]:.6f}")
        out.append("  -> differences in S and Delta are algorithmic, not task-driven")
    else:
        out.append(f"  persistent structure differs across agents: D in "
                   f"[{min(Ds):.6f}, {max(Ds):.6f}]")
        out.append("  -> agents did not all find the same structure; compare with care")
    return "\n".join(out)
