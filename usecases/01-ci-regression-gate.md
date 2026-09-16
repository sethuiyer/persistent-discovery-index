# Use case 01 — CI regression gate for agents

> Fail the pull request when a prompt or tool change makes the agent *wander*, even
> though the eval still says "pass".
>
> **Buyer:** developer / platform lead
> **Data path:** recorded eval tasks in CI (JSONL) → `pdi_profile.py` on two versions
> **Status:** the instrument is **computed and self-checking**; that it *predicts*
> production regressions **needs O4b**.

## The pain

A developer edits a system prompt, runs the 50-task eval, sees **90% pass**, and
merges. Three days later latency and cost are up, and nobody can say why. Pass rate
is a terminal bit: it cannot see that the agent now takes 13 tool calls where it
took 3 — because **both runs "succeeded."**

## What PDI measures

| Signal | Meaning for a gate |
|---|---|
| class inflation `n_j / n_j^ref` | how much more behaviour the candidate explores at resolution `j` |
| distinction onset `j*` | the level at which the candidate diverges (**behavioural**, ignores Q1 outcome) |
| `Δ = S − D` | discovery overhead; valid **only** when the task is held fixed |
| yield `L_j / n_j` | persistent share; collapsing yield is the wandering signature |

## Illustrative sketch

From the repository's own diagnostic example (a real computed table, not a customer
result):

```
class inflation vs reference
agent          Q1     Q2     Q3     Q4     Q5     Q6
reference    1.00x  1.00x  1.00x  1.00x  1.00x  1.00x
candidate    1.00x  1.09x  5.89x  7.35x  7.35x  7.35x

distinction onset: at resolution 3 (Q3 + tool sequence)
```

A gate could **block** when `j*` moves earlier, or when inflation at the first
behavioural level exceeds a frozen tolerance — and it can point the reviewer at the
level, not just the verdict.

## Proof status

- **Discharged:** the inflation table, `j*`, and the refinement law are computed and
  tested (`SPINE.md` §1–§2, `quotient_tower.py`).
- **Not discharged:** that `j*` inflation *predicts* a production regression at a
  useful precision/recall. That is O4b.
- **Removed on purpose:** the old "gate on `STABLE`" idea. `STABLE` describes a short
  observed tail; it is not statistical confidence (`SPINE.md` §17).

## Pilot (30–90 days)

1. Freeze a 50-task suite and a reference agent; record `n_j`/`L_j`.
2. Run each candidate change; gate at a tolerance (start loose, e.g. 2×).
3. **Measure the gate**: did it fire on changes that later hurt cost/latency, and
   stay quiet on benign ones? That is the precision/recall study.

## Risks / failure modes

- **False positives** from task mix. Mitigate with matched tasks per comparison.
- **`Δ` is presentation-dependent**: only comparable at **fixed task and tower**.
- **Horizon dependence**: a finite window can miss a transient growth subsequence
  (`SPINE.md` §3). State the horizon or use the asymptotic layer.
