# Use case 02 — Production token-waste APM

> Show finance the share of spend that went to dead ends — and the resolution level
> where the waste begins.
>
> **Buyer:** FinOps lead / engineering director
> **Data path:** live spans (OpenTelemetry GenAI) → `ingest.py` → `pdi_profile.py` / `dashboard.py`
> **Status:** **illustrative** numbers from a simulated corpus; live ingestion is
> **schema-conformant but not yet validated on a live capture**.

## The pain

The monthly model bill is up 40% while active users grew 10%. Engineering shows span
logs; nobody can separate *productive reasoning* from *useless trial-and-error*,
because every trace viewer counts both the same way.

## What PDI measures

| Signal | FinOps reading |
|---|---|
| transient mass `n_j − L_j` | behaviour that did not lead anywhere persistent |
| yield `L_j / n_j` | reasoning signal-to-noise, by resolution |
| STOP level `j*` | where to stop paying for finer behaviour |
| success/cost detail covariation | which refinements carry **cost** as well as outcome (`multiresolution.py`) |

## Illustrative sketch

From `simulate_corpus.py` (**constructed, not a customer result**), 300 runs × 5 tasks:

```
agent             success   tool calls/run
disciplined          97%         3.00
wanderer             89%        12.75     <- 4.25x
```

At 100k runs and $0.05/run that is **$5,000 vs $21,250** — an illustrative
**$16,250/month** that a pass-rate dashboard does not show. Real numbers require a
customer corpus; **do not quote the simulated figure as a finding**.

## Proof status

- **Discharged:** the two ledgers, yield and inflation are computed and tested.
- **Not discharged:** any *measured* percentage of recoverable spend, and the causal
  claim that removing the transient behaviour preserves success. The success/cost
  covariation is **predictive, not causal** (`O4_SCOPE.md` §9.5).
- **Ingestion caveat:** the OTel GenAI loader is written to the published spec but
  has **not** been run against a live capture (`README.md`, roadmap).

## Pilot (30–90 days)

1. Point `ingest.py` at a 2-week span export; validate field coverage first.
2. Report: share of tool calls in transient classes, by resolution, with the horizon.
3. Choose **one** investigation — a retry, a retrieval, or a routing change — and
   measure cost **and** quality on matched, held-out tasks.

## Risks / failure modes

- **Reporting a simulated number as a real one.** The single most likely failure.
- **Counting ≠ expenditure**: repeating an identical failed run raises cost without
  changing class counts. The report must show both.
- **Missing labels**: without an independent success signal, `L` reduces to the
  agent's own stop reason (`O4_SCOPE.md` §1).
