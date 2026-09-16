# O4B_PREDECLARATION_PILOT2.md — DRAFT, NOT FROZEN

**Status: DRAFT. No baseline runs. Nothing here is frozen.**
Pilot 1 closed as **C** ([`O4B_PILOT1_RESULT.md`](O4B_PILOT1_RESULT.md)).
Design context: [`O4B_PILOT2_DESIGN.md`](O4B_PILOT2_DESIGN.md).
Ruler: [`o4b_stat.py`](o4b_stat.py), reused for the success/cost endpoints.

Unresolved decisions are marked **`[CHOICE]`** or **`[FIX BEFORE RUN]`** and are
listed together in §10. They must all be settled and frozen before the first
baseline run.

---

## 1. Question — the value-add test

> Does **PDI localisation** reduce cost at non-inferior verified success **more
> than ordinary success-and-cost guidance**?

A P-vs-baseline improvement **alone is not sufficient**. The added-value claim
requires P to beat H, or to succeed where H abstains, on identical held-out tasks
(§6).

## 2. Difficulty — mechanical, fixed before any outcome

- Task families are defined by a **mechanical rule over the mutation, not by agent
  behaviour**: e.g. `(operator × module-size band × number of interacting
  functions)`. **`[CHOICE]`** the exact axes.
- A **difficulty ladder** spanning a range, declared before any run.
  **`[CHOICE]`** the bands and target per-band counts.
- Task identities and the discovery/held-out split are **sealed before running**.
- **Explicitly forbidden:** choosing a task because some agent failed it.
- **Mandatory:** every run persists its full trace; a run without a persisted
  trace is recorded as ineligible (coverage), never silently used.

## 3. Waste signal — cost variation, NOT proven waste

The diagnostic must be computable **when every run succeeds** (pilot 1's failure
mode). It is **cost variation**:

- Observable `c(h)`: per-run cost from `usage` (square-integrable on a finite cohort).
- Fixed partition tower `Q1…Q6` (order fixed), detail `D_j = P_{j+1} − P_j`.
- `E_j = ‖D_j c‖²_μ`, and the **unit-free share**
  `s_j = E_j / (Σ_j E_j + ‖c − P_J c‖²_μ) ∈ [0, 1]`.
- **Task adjustment:** centre cost **within task** (subtract the per-task mean)
  before projecting, so cross-task difficulty is not the signal.
- **Weighting:** **`[CHOICE]`** per-run uniform (current default) vs per-task.
- **Feature order:** the tower order is fixed; cost attribution is
  order-dependent (the XOR caveat) and that dependence is stated, not hidden.
- **Admissibility:** features exclude the evaluator result and deterministic
  encodings of it; cost is the observable, not a label.

> **`s_j` locates where cost variance is expressed in behaviour. It is not waste,
> not a saving, and not a cause.** High cost may be necessary work, or a harder
> task, or an inefficient policy.

## 4. Mathematical guardrail (cost is not a binary label)

- The binary bound `Σ E_j ≤ Var_μ(p) ≤ 1/4` applies to a `{0,1}` label **only**.
- For real-valued cost, the projection identity
  `Var_μ(c) = Σ_j E_j + ‖c − P_J c‖²_μ` holds whenever `c ∈ L²(μ)`, but there is
  **no `1/4` bound**, and `E_j` is in **squared-cost units** whose magnitude
  depends on the cost scale.
- Therefore **selection uses the unit-free share `s_j`**. Raw `E_j` may be
  reported but must state units and normalization. The warrant is explicitly the
  fraction of observed cost variance attributable to refinement `j` — nothing
  causal.

## 5. Selectors P and H — identical inputs, identical budget

Both receive **the same discovery data, the same candidate levels/behaviours, and
the same manifest-permitted intervention templates**, and both are allowed at most
`N_cand` candidate attempts **`[FIX BEFORE RUN]`**.

- **P (PDI):** select actionable `L*` maximising the **median over discovery tasks
  of `s_j`**, subject to `s_{L*} ≥ s_min` **`[FIX BEFORE RUN]`** and presence
  (`s_j(t) > 0`) in `≥ K` discovery tasks **`[FIX BEFORE RUN]`**.
- **H (ordinary guidance):** **`[CHOICE]`** e.g. the actionable level with the
  largest **raw** tool-count share of total, or the largest raw cost contribution.
  H must be a plausible heuristic, **not a straw man**.
- **Tie-breaking:** coarser level index first, then lexicographic name (same for both).
- **Abstention:** if a selector finds nothing admissible, it records **C** and does
  not descend to another level.

## 6. Evaluation — baseline, P, H on identical held-out tasks

- Arms: **baseline** (no intervention), **P-selected**, **H-selected**.
- **Matched budgets:** same tasks, same `R` runs/task/arm, same model and agent
  config, same intervention class and size, independent verification for all arms.
- **Primary:** `(P − baseline)` cost at non-inferior verified success, using the
  frozen statistic in [`o4b_stat.py`](o4b_stat.py) unchanged (`D*₅ ≥ −δ`,
  `Δ*₉₅ < 0`, `n_both < 6 → D`).
- **Added value:** the `(P − H)` contrast on the same endpoint, reported whatever
  it shows. If P and H are indistinguishable, **PDI has not demonstrated added
  value on this corpus** — a valid result.
- Held-out tasks stay sealed until **both** interventions are committed.

## 7. Artifacts and missing-data handling (pre-specified)

Per run, recorded: `task_id`, `arm`, `run_index`, **full trace path**, steps,
terminal outcome, `verified_outcome` + evaluator provenance, cost, tokens, model,
commit, corpus fingerprint.

Missing-data rules, declared before execution:
- missing **cost** → task cost-ineligible (counted);
- missing **trace** → run ineligible (counted), never used for profiling;
- **UNKNOWN** → excluded from the success denominator, counted;
- no silent drops; **no reruns**; every scheduled run recorded, including crashes,
  timeouts and failures.

## 8. Outcomes (A/B/C/D, reused)

- **A** — P reduces cost at non-inferior verified success **and** P beats H.
- **B** — non-inferiority violated.
- **C** — no level passes P's rule (or H abstains); reported as C, never reframed.
- **D** — coverage / power / verifier / execution failure.
The **P-vs-H contrast is reported** in every outcome, including B and D.

## 9. Non-negotiables

- **Cost variation ≠ waste**, and neither is a commercial savings claim.
- No task selected because this agent failed it.
- No held-out inspection before both interventions are committed.
- No post-hoc reclassification of B/C/D as success.
- If P's localiser yields nothing, that is **C**.

## 10. Unresolved — must be settled before the first run

| # | item | mark |
|---|---|---|
| 1 | difficulty axes (mechanical task-family rule) | `[CHOICE]` |
| 2 | difficulty ladder bands and counts | `[CHOICE]` |
| 3 | weighting `μ`: per-run vs per-task | `[CHOICE]` |
| 4 | H's ordinary guidance rule | `[CHOICE]` |
| 5 | candidate budget `N_cand` | `[FIX BEFORE RUN]` |
| 6 | `s_min` threshold | `[FIX BEFORE RUN]` |
| 7 | `K` (tasks a level must appear in) | `[FIX BEFORE RUN]` |
| 8 | `R`, `δ`, split seed, model/config | `[FIX BEFORE RUN]` |
| 9 | corpus construction (modules, operators, kill rules) | `[FIX BEFORE RUN]` |
| 10 | implementation of the cost-variation share in code + its own audit | `[FIX BEFORE RUN]` |
