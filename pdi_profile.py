#!/usr/bin/env python3
"""
pdi_profile.py — run the instrument on your own agent traces, in one command.

    python3 pdi_profile.py traces/                    # autodetect the format
    python3 pdi_profile.py run.jsonl --format openai
    python3 pdi_profile.py traces/ --group-by model
    python3 pdi_profile.py --demo                     # synthetic, no data needed

Answers one question:

    Where does useful discovery end and unnecessary exploration begin,
    and at which behavioural resolution?

No configuration. No framework dependency. Point it at JSONL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

from adapters import TOOL_LEVEL_NAMES, tool_tower
from agent_profiler import AgentProfiler, compare, format_profile, inflation_table
from ingest import (FORMATS, CapabilityError, detect_format, load_any, load_paths,
                    require_capabilities, write_canonical)
from pdi import PDI
from quotient_tower import prefix_tower


# --------------------------------------------------------------------------
def ingest(paths, fmt):
    runs = []
    for p in paths:
        if not os.path.exists(p):
            print(f"  ! not found: {p}")
            continue
        runs.extend(load_paths([p], fmt))
    return runs


def source_formats(paths, fmt):
    """The set of source formats present, for the capability gate."""
    fmts = Counter()
    for p in paths:
        if os.path.isfile(p):
            fmts[fmt or detect_format(p)] += 1
        elif os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in fs:
                    if f.endswith((".jsonl", ".json", ".db")):
                        fmts[fmt or detect_format(os.path.join(root, f))] += 1
    return set(fmts)


def summarize(runs, paths, fmt):
    fmts = Counter()
    for p in paths:
        if os.path.isfile(p):
            fmts[fmt or detect_format(p)] += 1
        elif os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in fs:
                    if f.endswith((".jsonl", ".json", ".db")):
                        fmts[fmt or detect_format(os.path.join(root, f))] += 1
    steps = sum(len(r.steps) for r in runs)
    errs = sum(1 for r in runs for s in r.steps if s.error)
    succ = sum(1 for r in runs if r.succeeded)
    tools = Counter(s.tool for r in runs for s in r.steps)
    lines = [f"  runs      : {len(runs)}",
             f"  tool calls: {steps}   errors: {errs} ({errs/max(steps,1)*100:.1f}%)",
             f"  succeeded : {succ}/{len(runs)} ({succ/max(len(runs),1)*100:.1f}%)",
             f"  formats   : {dict(fmts)}",
             f"  top tools : {', '.join(f'{t}({c})' for t, c in tools.most_common(6))}"]
    return "\n".join(lines)


def build_tower(name):
    if name == "tool":
        return tool_tower(), TOOL_LEVEL_NAMES
    if name == "prefix":
        return prefix_tower(lambda x: x), None
    raise SystemExit(f"unknown tower {name!r} (use tool|prefix)")


def demo_runs():
    """Two synthetic agents on the same task: one disciplined, one wasteful.
    Lets the tool be exercised with no data at all."""
    from adapters import Step, Turn
    import random
    rng = random.Random(0)
    out = []
    for i in range(40):
        steps = [Step("read", {"path": f"f{i}.py"}), Step("edit", {"path": f"f{i}.py"})]
        out.append(Turn(steps=steps + [Step("bash", {"command": "pytest"})],
                        outcome="stop", model="disciplined", project="demo",
                        prompt=f"fix f{i}"))
    for i in range(40):
        steps = [Step("read", {"path": f"f{i}.py"})]
        for _ in range(rng.randint(3, 25)):
            steps.append(Step("bash", {"command": f"grep -n x f{i}.py"},
                              error=None if rng.random() > .3 else "no match"))
        steps += [Step("edit", {"path": f"f{i}.py"}), Step("bash", {"command": "pytest"})]
        out.append(Turn(steps=steps, outcome="stop" if rng.random() > .25 else "error",
                        model="wasteful", project="demo", prompt=f"fix f{i}"))
    return out


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="PDI — agent behaviour profiler")
    ap.add_argument("paths", nargs="*", help="trace files or directories")
    ap.add_argument("--format", choices=list(FORMATS), default=None,
                    help="force a trace format (default: autodetect)")
    ap.add_argument("--group-by", choices=["model", "project", "file", "none"],
                    default="model")
    ap.add_argument("--tower", choices=["tool", "prefix"], default="tool")
    ap.add_argument("--min", type=int, default=5, help="min runs per group")
    ap.add_argument("--dump-canonical", metavar="OUT.jsonl",
                    help="write the normalised runs and exit")
    ap.add_argument("--demo", action="store_true", help="use synthetic runs")
    a = ap.parse_args(argv)

    print("=" * 78)
    print("PDI — where useful discovery ends and unnecessary exploration begins")
    print("=" * 78)

    if a.demo or not a.paths:
        runs = demo_runs()
        print("\n  source: synthetic demo (--demo)")
    else:
        runs = ingest(a.paths, a.format)
        print("\n" + summarize(runs, a.paths, a.format))

    if not runs:
        print("\n  nothing to profile.")
        return 1

    if a.dump_canonical:
        n = write_canonical(runs, a.dump_canonical)
        print(f"\n  wrote {n} normalised runs to {a.dump_canonical}")
        return 0

    tower, names = build_tower(a.tower)

    # Input warrants: an analysis may not claim more than ingestion recovered.
    if a.group_by != "none" and not (a.demo or not a.paths):
        try:
            require_capabilities(source_formats(a.paths, a.format), "agent_comparison")
        except CapabilityError as e:
            print("\n" + str(e))
            return 2

    if a.group_by == "none":
        groups = {"all runs": runs}
    else:
        key = {"model": lambda r: r.model, "project": lambda r: r.project,
               "file": lambda r: r.session}[a.group_by]
        groups = defaultdict(list)
        for r in runs:
            groups[key(r)].append(r)

    keep = {k: v for k, v in groups.items() if len(v) >= a.min}
    if len(keep) < 1:
        print(f"\n  no group has >= {a.min} runs; try --min 1")
        return 1

    agents = {}
    for name, rs in keep.items():
        p = AgentProfiler(index=PDI(tower=tower))
        for r in rs:
            p.add_run(r, r.succeeded)
        agents[name] = p

    if len(keep) == 1:
        only = next(iter(keep))
        print(format_profile(only, agents[only].profile()))
    else:
        for name in keep:
            print(format_profile(name, agents[name].profile()))
        print(compare(agents))
        S = {m: agents[m].profile()["S"] for m in keep}
        ref = min(S, key=S.get)
        print(inflation_table(agents, reference=ref,
                              level_names=[f"Q{i}" for i in
                                           range(1, (3 if names is None else len(names)) + 1)]
                              if names else None))
        if names:
            print("    " + "   ".join(f"Q{i}={n.split(None,1)[1]}"
                                      for i, n in enumerate(names, 1)))
        print(f"\n  reference for inflation = {ref} (lowest window S).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
