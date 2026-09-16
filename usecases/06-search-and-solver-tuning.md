# Use case 06 — Search & solver tuning beyond agents

> The same instrument applies to *any* search: compare solvers, planners, or
> optimizers by **where they stop deducing and start guessing** — with hard,
> reproducible evidence today.
>
> **Buyer:** industrial / optimization / R&D engineering
> **Data path:** solver node/pruning traces → the per-depth profile (`demo_sudoku.py` is the worked case)
> **Status:** **computed** — this is the one use case with a frozen, exact result already in the repo.

## The pain

Two solvers return the *same* answer, so the scoreboard says "tie". One explored
23,232 nodes; the other 169. The difference is invisible to accuracy, and it is the
entire cost of the search.

## What PDI measures

| Signal | Optimization reading |
|---|---|
| `n_j` vs `L_j` per depth | exploration vs what led to a solution |
| inflation vs a reference | how much extra structure one solver manufactures |
| per-depth waste share | the *band* where it stops deducing |
| PDI `n_j` == solver node counts | the profile is **not an artefact** (verified exactly) |

## Evidence (computed — not illustrative)

Two Sudoku puzzles, three strategies, the same two solutions (`demo_sudoku.py`):

```
strategy            total nodes   backtracks
first/asc                23,232       23,231
first/random              3,992        3,991
mrv/asc                     169          63     <- 137x fewer

first/asc share of visits by depth band:
  d1-10 5.8%   d11-20 8.6%   d21-30 76.2%   d31-40 9.2%   d41-53 0.2%
```

**76.2% of the naive search sits in one depth band** — where it stops deducing and
starts guessing. At depth 27 the naive solver generates **627×** MRV's structure for
the same solution. `test_sudoku.py` checks that PDI's `n_j` equals the solver's own
per-depth node counts **exactly**.

## Proof status

- **Discharged:** the per-depth profile, the inflation table, and the exact match to
  solver node counts (20 checks).
- **Honest limitation:** on this example the *asymptotic* summaries `D` and `S` both
  take their sup at depth 1 — they order the strategies correctly but measure
  first-cell branching, not search size. **The per-depth profile is the instrument
  here**, and the software says so itself (`README.md`, "Evaluation requirement").

## Pilot (30–90 days)

1. Instrument a solver to emit node counts per depth (or per parameter setting).
2. Run the existing pipeline; read the depth band holding the waste.
3. Change one heuristic; confirm the band shrinks **without** changing solution quality.

## Risks / failure modes

- **Over-reading `D`/`S`** when the waste is at depth, not at the root (this example).
- **Comparing across problem sizes** — `Δ` is valid only at fixed task.
- **Misreading the reference**: inflation is relative to a chosen baseline solver.
