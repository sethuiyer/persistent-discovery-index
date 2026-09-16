# Use case 04 — Model & scaffold selection

> Choose between models, prompts, or agent scaffolds on **matched tasks**, reporting
> discovery overhead instead of a single pass rate.
>
> **Buyer:** ML platform team / AI procurement / vendor due diligence
> **Data path:** the same task suite run across candidates → `pdi_profile.py --group-by model` / `--matched`
> **Status:** the **method is implemented**; a valid comparison **requires a controlled, matched-task corpus** (the repo's known blocker).

## The pain

"Model A scores 85%, Model B scores 84%." That comparison hides that A took 3× the
tool calls and 4× the tokens to get there — and, more subtly, that the two models
**ran different tasks**, so the scores were never comparable.

## What PDI measures

| Signal | Selection reading |
|---|---|
| `D` (persistent complexity) | the structure of the **task**; should be ~equal across candidates that solved the same work |
| `Δ = S − D` | the **algorithm's** overhead at fixed task |
| `j*` | where a candidate starts to diverge behaviourally |
| `--matched` | restricts to opening prompts **at least two agents actually ran** |

The profiler itself refuses the invalid comparison: when persistent structure
differs it prints

```
persistent structure differs across agents: D in [1.85, 2.86]
-> agents did not all find the same structure; compare with care
```

## Proof status

- **Discharged:** `D`, `Δ`, `j*`, and the `--matched` control are implemented and tested.
- **Not discharged:** that `Δ` ranks candidates by a useful downstream criterion.
  `Δ` is **presentation-dependent** — valid only at fixed task and tower.
- **Honest limitation:** on the private corpus `--matched` leaves only a handful of
  turns — "enough to demonstrate the mechanism, far too little to conclude."

## Illustrative sketch

Same two Sudoku strategies, same puzzles (`demo_sudoku.py`): identical persistent
structure, `Δ` cleanly ordered from `0.0` (informed) to `0.228` (unpruned). That is
the shape a selection report should have: **equal structure, ranked overhead.**

## Pilot (30–90 days)

1. Build a task suite where **every candidate runs every task** (matched by design).
2. Report per-candidate `D`, `Δ`, `j*`, and success — never `Δ` across tasks.
3. For vendor diligence, require the *vendor's* corpus be frozen and matched.

## Risks / failure modes

- **Task confounding** — the single biggest error; unmatched `Δ` is meaningless.
- **Small matched samples** producing confident-looking but unstable rankings.
- **Presentation dependence**: changing the tower changes `Δ`, not `D`.
