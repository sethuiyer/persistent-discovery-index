#!/usr/bin/env python3
"""
diagnose_agents.py — make PDI diagnose an actual agent.

Loads real pi session traces, groups turns by the model that produced them, and
asks the question the invariant was built to answer:

    Where does partition inflation begin for each agent?

    python3 diagnose_agents.py [project]        # default: navokoj
    python3 diagnose_agents.py --all            # every project, every model

The tower is explicit (Q1..Q6, see adapters.tool_tower): each level contains the
previous one, so the refinement law is structural and the levels are named
behavioural resolutions rather than arbitrary indices.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from adapters import (PI_SESSIONS, TOOL_LEVEL_NAMES, load_pi_runs, tool_tower)
from agent_profiler import AgentProfiler, compare, format_profile, inflation_table
from pdi import PDI


def summarize(turns) -> str:
    models = Counter(t.model for t in turns)
    tools = Counter(s.tool for t in turns for s in t.steps)
    errs = sum(1 for t in turns for s in t.steps if s.error)
    calls = sum(len(t.steps) for t in turns)
    succ = sum(1 for t in turns if t.succeeded)
    out = [
        f"  real traces from {PI_SESSIONS}",
        f"  turns   : {len(turns)}",
        f"  tool calls: {calls}   errors: {errs} ({errs/max(calls,1)*100:.1f}%)",
        f"  terminal success (stopReason=='stop'): {succ}/{len(turns)} "
        f"({succ/max(len(turns),1)*100:.1f}%)",
        f"  models  : {len(models)}",
    ]
    for m, c in models.most_common(8):
        out.append(f"      {m:<44} {c:>4} turns")
    return "\n".join(out)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    all_projects = "--all" in argv
    matched = "--matched" in argv
    project = args[0] if args else "navokoj"

    turns = load_pi_runs()
    if not turns:
        print("no pi session traces found; set PI_SESSIONS or run the agent first")
        return 1

    print("=" * 78)
    print("PDI — real agent diagnosis")
    print("=" * 78)
    print(summarize(turns))

    if not all_projects:
        turns = [t for t in turns if t.project == project]
        if not turns:
            print(f"\n  no turns in project {project!r}")
            return 1
        print(f"\n  filtered to project {project!r}: {len(turns)} turns")

    if matched:
        # keep only opening prompts that at least two models actually ran:
        # this controls for the task, which the raw grouping cannot.
        by_prompt = defaultdict(set)
        for t in turns:
            by_prompt[t.prompt].add(t.model)
        shared = {p for p, ms in by_prompt.items() if len(ms) > 1 and p}
        before = len(turns)
        turns = [t for t in turns if t.prompt in shared]
        print(f"\n  --matched: {len(shared)} shared prompts, "
              f"{len(turns)}/{before} turns retained")

    # ---- group by the agent that produced the turn -------------------------
    by_model = defaultdict(list)
    for t in turns:
        by_model[t.model].append(t)

    MIN_TURNS = 2 if matched else 20
    for i, a in enumerate(argv):
        if a == "--min" and i + 1 < len(argv):
            MIN_TURNS = int(argv[i + 1])
    keep = {m: ts for m, ts in by_model.items() if len(ts) >= MIN_TURNS}
    if len(keep) < 2:
        print(f"\n  need >=2 models with >={MIN_TURNS} turns; found {len(keep)}")
        for m, ts in sorted(by_model.items(), key=lambda kv: -len(kv[1])):
            print(f"      {m:<44} {len(ts):>4}")
        return 1

    tower = tool_tower()
    agents = {}
    for model, ts in keep.items():
        prof = AgentProfiler(index=PDI(tower=tower))
        for t in ts:
            prof.add_run(t, t.succeeded)
        agents[model] = prof

    print("\n" + "=" * 78)
    print("behavioural-resolution profiles")
    print("=" * 78)
    for model in keep:
        print(format_profile(model, agents[model].profile()))

    print(compare(agents))

    # reference = the model with the smallest S (least exploration)
    S = {m: agents[m].profile()["S"] for m in keep}
    ref = min(S, key=S.get)
    print(inflation_table(agents, reference=ref,
                          level_names=[f"Q{i}" for i in range(1, 7)]))
    print("\n    " + "   ".join(f"Q{i}={n.split(None,1)[1]}" for i, n in
                                enumerate(TOOL_LEVEL_NAMES, 1)))

    print("\n" + "=" * 78)
    print("reading")
    print("=" * 78)
    print(f"""
  reference = {ref} (lowest exploration exponent S).
  D    is the persistent (successful-turn) behavioural structure.
  S    is the full exploration structure this model actually generated.
  Delta is what it spent on turn shapes that never reached a stop outcome.
  The inflation row identifies the FIRST behavioural resolution at which a model
  manufactures distinctions the reference does not -- i.e. where its wasted
  reasoning begins, named in behavioural terms rather than "it used more tools".
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
