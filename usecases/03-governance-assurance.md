# Use case 03 — Governance & assurance reports

> A signed, reproducible statement of **what a metric measures and what it hides** —
> for the people who have to answer when the board asks if the numbers are real.
>
> **Buyer:** CISO / risk officer / AI governance lead
> **Data path:** any trace corpus + the warrant layer and the 25 self-checking suites
> **Status:** the discipline is **implemented and tested**; the "signed report"
> product is a thin wrapper around it.

## The pain

Agent evaluation is full of confident, un-auditable scores. A vendor says "95%
reliable"; a regulator or board asks what that number assumes, and no one can
answer. The failure is not a bad metric — it is a metric **claiming more than its
evidence**.

## What PDI measures (and displays)

| Mechanism | Governance value |
|---|---|
| status vocabulary `proved / computed / negative / open / conjecture` | every claim is labelled with its strength |
| convergence status `STABLE / TRENDING_UP / …` | whether a reported rate is a rate or a snapshot |
| `D_shallow` / `S_shallow` | flags a value attained *inside* the horizon (not a rate) |
| bound labels carrying hypotheses | "lower bound **IF** the tail stays monotone" |
| zero dependencies + deterministic output | the report is reproducible off a commit |

## Illustrative sketch

From `proof_awareness.py` — the system **falsifies its own bound labels**, which is
the point:

```
status          observed tail     reported    continuation   true limsup
TRENDING_UP     0.1 0.2 0.3 0.4   0.400000    1/j            0.002506   VIOLATED
STABLE          0.5 0.5 0.5 0.5   0.500000    9,9,9,...      9.000000   VIOLATED
```

A governance report that ships this behaviour is *demonstrably* not overclaiming.

## Proof status

- **Discharged:** the discipline is implemented and enforced by 25 suites; the
  ledger (`SPINE.md` §0) is the source of truth for claim status.
- **Not discharged:** that a buyer will pay for calibration. That is the market bet
  in [`../CEO.md`](../CEO.md).
- **Scope honesty:** PDI's "persistent" is **survival, not topological persistence**
  (`SPINE.md` §12); the report must say so.

## Pilot (30–90 days)

1. Take one existing agent eval and re-express it as a warrant-bearing report.
2. Show the statuses, the horizon, and the shallow-attainment flags.
3. Offer a **signed, versioned** artefact per release: corpus hash, tower version,
   evaluator identity, coverage.

## Risks / failure modes

- **Honesty as a liability** with buyers who want a single confident number.
- **Liability of an audit claim**: "assured" must be scoped to *what* was checked.
- **Operational drift**: the discipline only holds if the checker keeps running;
  the consistency suite is not optional.
