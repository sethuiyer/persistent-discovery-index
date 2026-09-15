#!/usr/bin/env python3
"""Self-checks for the Sudoku demo. Run: python3 test_sudoku.py"""
from __future__ import annotations

from agent_profiler import AgentProfiler
from pdi import PDI
from quotient_tower import prefix_tower
from sudoku import PUZZLES, STRATEGIES, parse, run_records, solve

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


KNOWN = {  # known solutions for two of the fixtures
    "easy": "534678912672195348198342567859761423426853791713924856961537284287419635345286179",
    "medium": "462831957795426183381795426173984265659312748248567319926178534834259671517643892",
}


def board_of(trace):
    return "".join(str(v) for _, v in sorted(trace.solution_path, key=lambda x: x[0]))


print("sudoku self-checks")

# 1. the solver is correct
for pname, want in KNOWN.items():
    tr = solve(PUZZLES[pname], cap=300_000)
    check(f"{pname}: solved", tr.solved)
    check(f"{pname}: assignments cover the empty cells",
          len(tr.solution_path) == sum(1 for v in parse(PUZZLES[pname]) if not v))

# 2. validity: the solved board has no row/col/box conflict
def valid(board: str) -> bool:
    n = [int(c) for c in board]
    for k in range(9):
        row = n[k * 9:(k + 1) * 9]
        col = [n[k + 9 * i] for i in range(9)]
        box = [n[(k // 3) * 27 + (k % 3) * 3 + (i // 3) * 9 + i % 3] for i in range(9)]
        for grp in (row, col, box):
            if sorted(grp) != list(range(1, 10)):
                return False
    return True


for pname, want in KNOWN.items():
    tr = solve(PUZZLES[pname], cap=300_000)
    b = parse(PUZZLES[pname])          # start from the GIVEN cells, the solver
    for i, v in tr.solution_path:      # only fills the empties
        b[i] = v
    got = "".join(map(str, b))
    check(f"{pname}: solution is a valid grid", valid(got))
    check(f"{pname}: solution matches the known answer", got == want)

# 3. trace bookkeeping
for pname in ("easy", "medium"):
    tr = solve(PUZZLES[pname], cap=300_000)
    check(f"{pname}: nodes_at_depth sums to total_nodes",
          sum(tr.nodes_at_depth) == tr.total_nodes)
    check(f"{pname}: every visited depth has a count",
          all(tr.nodes_at_depth[j] > 0 for j in
              range(1, len(tr.solution_path) + 1)))

# 4. strategies genuinely differ
tot = {n: solve(PUZZLES["medium"], cap=300_000, **kw).total_nodes
       for n, kw in STRATEGIES.items()}
check("mrv explores far less than first/asc on medium", tot["mrv/asc"] * 20 < tot["first/asc"])
check("random value order is between them", tot["first/asc"] > tot["first/random"] > tot["mrv/asc"])

# 5. PDI's n_j must equal the solver's own per-depth node counts
pname, sname = "medium", "first/asc"
kw = STRATEGIES[sname]
tr = solve(PUZZLES[pname], cap=300_000, **kw)
runs, _ = run_records(PUZZLES[pname], label=sname, **kw)
prof = AgentProfiler(index=PDI(tower=prefix_tower(
    lambda s: (s.args.get("cell"), s.args.get("value")))))
for r in runs:
    prof.add_run(r, r.succeeded)
p = prof.profile()
got = {row["level"]: row["n"] for row in p["rows"]}
exp = {j: c for j, c in enumerate(tr.nodes_at_depth) if c and j > 0}
check("PDI n_j == solver nodes_at_depth at every depth", got == exp)
if got != exp:
    diff = {j: (got.get(j), exp.get(j)) for j in set(got) | set(exp) if got.get(j) != exp.get(j)}
    print(f"      mismatch: {diff}")

# 6. a unique solution => exactly one persistent node per depth
check("L_j == 1 at every depth for a single unique-solution puzzle",
      all(row["L"] == 1 for row in p["rows"]))

# 7. the prefix tower accepts both a Run and a bare step sequence
t = prefix_tower(lambda s: (s.args.get("cell"), s.args.get("value")))
check("prefix_tower accepts a Run object", len(t.signature(runs[0])) == len(runs[0].steps))
check("prefix_tower accepts a bare sequence", t.signature(runs[0].steps) == t.signature(runs[0]))

# 8. mrv solves 'hard' where naive does not
check("mrv solves the hard fixture", solve(PUZZLES["hard"], cap=300_000,
                                           **STRATEGIES["mrv/asc"]).solved)
check("first/asc does not solve the hard fixture within cap",
      not solve(PUZZLES["hard"], cap=300_000, **STRATEGIES["first/asc"]).solved)

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
