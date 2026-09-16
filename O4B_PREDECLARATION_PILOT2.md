# O4B_PREDECLARATION_PILOT2.md — DRAFT, NOT FROZEN

**Status: DRAFT. No baseline runs. Nothing here is frozen.**
Pilot 1 closed as **C** ([`O4B_PILOT1_RESULT.md`](O4B_PILOT1_RESULT.md)).
Design context: [`O4B_PILOT2_DESIGN.md`](O4B_PILOT2_DESIGN.md).
Ruler for the success/cost endpoints: [`o4b_stat.py`](o4b_stat.py) (unchanged).

Sections marked **RESOLVED (draft)** are settled as contracts but still unfrozen.
Remaining unresolved choices are **`[CHOICE]`** / **`[FIX BEFORE RUN]`** and are
listed in §10.

---

## 1. Question — the value-add test

> Does **PDI localisation** reduce cost at non-inferior verified success **more
> than ordinary success-and-cost guidance**?

A P-vs-baseline improvement **alone is insufficient**. Added value requires P to
beat H, or to succeed where H abstains, on identical held-out tasks (§6).

## 2. Difficulty — mechanical, fixed before any outcome

- Task families defined by a **mechanical rule over the mutation, not agent
  behaviour**: `(operator × module-size band × interacting-function count)`.
  **`[CHOICE]`** the axes.
- A **difficulty ladder** spanning a range, declared before any run. **`[CHOICE]`**
  bands and counts.
- Task identities and split **sealed before running**.
- **Forbidden:** selecting a task because some agent failed it.
- **Mandatory:** every run persists its full trace; a run without a persisted trace
  is ineligible (coverage), never silently used.

## 3. RESOLVED (draft) — the diagnostic tower, and cost variation

### 3.1 A separate diagnostic tower (Q1–Q6 stay descriptive)

`Q1–Q6` contain the terminal outcome and increasingly specific trace keys. Using
them to localise cost would let cost grouping collapse into **outcome grouping**,
and the finest level could **memorise singletons**. So:

- `Q1–Q6` remain **descriptive only**; they are **not** used for cost localisation.
- Cost is projected on a **separate diagnostic tower** whose levels are declared,
  **admissible behavioural features**, fixed before the run. **`[FIX BEFORE RUN]`**
  the level list (coarse → fine).
- **Admissible features:** behavioural properties of the trace — tool family, tool
  sequence, error classes, argument classes.
- **Inadmissible as features:** **cost, tokens, and any deterministic encoding of
  them**; the terminal outcome; the verified outcome and its encodings. The tower
  must not be able to read the quantity it is explaining.
- **Singleton rule:** a level whose partition is (near-)discrete is inadmissible
  for selection — a singleton partition can resolve every observed cost difference
  without generalising. **`[FIX BEFORE RUN]`** the admissibility bound (e.g.
  minimum mean class size, or maximum class count).

### 3.2 The observable and the weights

- Observable `c(h)`: per-run cost from `usage`.
- **Weighting: equal weight per task, divided equally among that task's eligible
  runs.** This targets the **average task** and stops tasks with more retained runs
  from dominating.
- **Task adjustment:** centre cost **within task**, using **the same weights**,
  before projecting — so cross-task difficulty is not the signal.

### 3.3 The share

With the diagnostic partition tower and `D_j = P_{j+1} − P_j`:

```
E_j    = || D_j c ||²_μ
total  = Σ_j E_j + || c − P_J c ||²_μ          (weighted within-task cost variance)
s_j    = E_j / total                            (unit-free)
```

`s_j` is the **observed variance resolved by refinement `j`**. Feature order is
fixed by the tower, and cost attribution is order-dependent (the XOR caveat),
stated rather than hidden.

- **Minimum eligible repetitions.** A task with fewer than `R_min` eligible runs is
  excluded. With a single run, within-task centring removes **all** within-task
  variation, so the share is undefined. **`[FIX BEFORE RUN]`** `R_min`.
- **Zero denominator.** If `total = 0` there is no observed cost variation; the
  share is **undefined and the selector abstains** — it is never silently assigned
  `0`.

> **`s_j` is not waste, not a saving, and not a cause.** High cost may be necessary
> work, a harder task, or an inefficient policy. `s_j` localises where observed
> cost variance is *resolved by behavioural refinement*.

## 4. RESOLVED (draft) — mathematical guardrail (cost is not a binary label)

- The binary bound `Σ E_j ≤ Var_μ(p) ≤ 1/4` applies to a `{0,1}` label **only**.
- For real-valued cost, `Var_μ(c) = Σ_j E_j + ||c − P_J c||²_μ` holds when
  `c ∈ L²(μ)`, but there is **no `1/4` bound**, and `E_j` is in **squared-cost
  units** that scale with the currency unit. Shares `s_j` are invariant under
  currency rescaling; raw `E_j` is not, and must state units and normalization.
- The warrant is the **fraction of observed cost variance resolved by refinement
  `j`** — nothing causal.

### 4.1 Required statistic audit (before it touches data)

The cost-variation statistic ships with its own synthetic audit, as `o4b_stat.py`
did. Fixtures, at minimum:

| fixture | expected behaviour |
|---|---|
| zero variance (all costs equal) | `total = 0` → share **undefined → abstain** |
| currency rescaling (`c → k·c`) | shares **unchanged**; raw `E_j` scales by `k²` |
| unequal repetitions per task | task weighting dominates run count; a 1-run task is excluded |
| unresolved residual (`P_J c ≠ c`) | residual carried in `total`; share ≤ 1 |
| singleton refinement | resolved as inadmissible → cannot be selected |

## 5. RESOLVED (draft) — selectors P and H

Both receive **the same discovery data, the same candidate levels and the same
manifest-permitted intervention templates**, with the same budget
`N_cand` **`[FIX BEFORE RUN]`**, the same tie-breaking, and **separately declared
abstention thresholds** (their scores mean different things).

- **P (PDI):** select actionable `L*` maximising the **median over discovery tasks
  of `s_j`**, subject to `s_{L*} ≥ s_min` **`[FIX BEFORE RUN]`** and presence in
  `≥ K` discovery tasks **`[FIX BEFORE RUN]`**. Abstains if `total = 0` (§3.3).
- **H (ordinary guidance):** rank the **same candidate interventions** by the
  **mean measured cost of the events each candidate targets**, using the **same
  task weighting** (equal per task, split across eligible runs). Two things are
  frozen with H: **event attribution** (how a run's cost is assigned to the events
  a candidate targets) and **overlapping-cost handling** (when candidate event
  sets overlap). **`[FIX BEFORE RUN]`** both, plus H's own abstention threshold.
- **Tie-breaking (both):** coarser level first, then lexicographic name.
- **Abstention (both):** record **C**; never descend to another level.

## 6. Evaluation — baseline, P, H on identical held-out tasks

- Arms: **baseline**, **P-selected**, **H-selected**.
- **Matched budgets:** same tasks, same `R` runs/task/arm, same model and agent
  config, same intervention class and size, independent verification for all arms.
- **Primary:** `(P − baseline)` cost at non-inferior verified success, using
  `o4b_stat.py` unchanged (`D*₅ ≥ −δ`, `Δ*₉₅ < 0`, `n_both < 6 → D`).
- **Added value:** the `(P − H)` contrast on the same endpoint, reported in every
  outcome. If P and H are indistinguishable, **PDI has not demonstrated added value
  on this corpus** — a valid result.
- Held-out stays sealed until **both** interventions are committed.

## 7. Artifacts and missing-data handling (pre-specified)

Per run: `task_id`, `arm`, `run_index`, **full trace path**, steps, terminal
outcome, `verified_outcome` + evaluator provenance, cost, tokens, model, commit,
corpus fingerprint.

- missing **cost** → task cost-ineligible (counted);
- task with fewer than `R_min` eligible runs → task excluded (counted);
- missing **trace** → run ineligible (counted), never profiled;
- **UNKNOWN** → excluded from the success denominator, counted;
- no silent drops; **no reruns**; every scheduled run recorded including crashes.

## 8. Outcomes (A/B/C/D)

- **A** — P reduces cost at non-inferior verified success **and** P beats H.
- **B** — non-inferiority violated.
- **C** — P abstains / no level passes (or H abstains); reported as C, never reframed.
- **D** — coverage / power / verifier / execution failure.
The **P-vs-H contrast is reported** in every outcome, including B and D.

## 9. Non-negotiables

- **Cost variation ≠ waste**, and never a commercial savings claim.
- No task selected because this agent failed it.
- No held-out inspection before both interventions are committed.
- No post-hoc reclassification of B/C/D as success.
- If P's localiser yields nothing → **C**.

## 10. Unresolved — settle before the first run

| # | item | mark |
|---|---|---|
| 1 | difficulty axes (mechanical task-family rule) | `[CHOICE]` |
| 2 | difficulty ladder bands and counts | `[CHOICE]` |
| 3 | diagnostic tower level list | `[FIX BEFORE RUN]` |
| 4 | singleton/admissibility bound | `[FIX BEFORE RUN]` |
| 5 | `R_min` (minimum eligible repetitions) | `[FIX BEFORE RUN]` |
| 6 | H: event-attribution rule | `[FIX BEFORE RUN]` |
| 7 | H: overlapping-cost handling | `[FIX BEFORE RUN]` |
| 8 | H abstention threshold; P `s_min` and `K` | `[FIX BEFORE RUN]` |
| 9 | `N_cand`, `R`, `δ`, split seed, model/config | `[FIX BEFORE RUN]` |
| 10 | corpus construction (modules, operators, kill rules) | `[FIX BEFORE RUN]` |
| 11 | implementation of the cost-variation share **and its §4.1 audit** | `[FIX BEFORE RUN]` |
