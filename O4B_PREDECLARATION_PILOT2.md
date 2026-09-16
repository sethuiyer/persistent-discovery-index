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

## 2. Difficulty — STRUCTURAL CHALLENGE BANDS (not validated levels)

Three mechanical axes, applied to the mutation and the module only:

| axis | values | role |
|---|---|---|
| **mutation count** | one defect / two composed defects | challenge |
| **dependency span** | one function / crossing a declared call edge | challenge |
| **module size** | fixed source-line bands | **covariate, recorded — not difficulty** |

**"Interacting" is mechanical:** functions `f, g` in the same module such that `g`'s
body contains a `Call` to `f` (an AST call edge). No other sense of "interacting"
is admissible.

**Bands** (target 24 tasks, 8 per band):

| band | construction | discovery / held-out |
|---|---|---|
| **A** | one defect, one function | 4 / 4 |
| **B** | one defect affecting a cross-function contract (at a declared call edge) | 4 / 4 |
| **C** | two defects in interacting functions | 4 / 4 |

These are **structural challenge bands, not validated difficulty levels**: actual
difficulty is an experimental result (measured as baseline success), not an
assumption.

**Band C construction gate (all four required):**
1. clean tree PASS;
2. mutation 1 alone FAIL;
3. mutation 2 alone FAIL;
4. combined FAIL.
A pair whose defects **cancel** (combined PASS) is rejected, as is a pair with no
declared call edge between them.

**Cluster discipline.** The cluster is the **module**; clusters are **disjoint
across splits**, and every task of a module stays on that module's side. Module
size is recorded per task as a covariate.

**Quota honesty.** Only ~21 production modules currently have a dedicated verifier,
so 24 tasks require some modules to carry more than one task (same side). Every
unsuccessful construction attempt is recorded, and **rules are never relaxed to
fill a quota**; a shortfall is reported as a shortfall.

### 2.4 Gates before freezing

**Gate 1 — trace persistence: PASS.** The committed runner was exercised end to end
against a fake `pi` on PATH (no paid agent): fresh mutated tree → RPC until
`agent_settled` → usage → trace copied out of the workdir → verifier → workdir
cleaned. The recorded trace is readable after cleanup, its cost is captured, and a
second run writes a distinct trace. Evidence: `test_o4b_run.py`.

**Gate 2 — cost attribution: FAILS the naive form, so an assumption is required.**
In a real capture: usage is recorded **only on assistant messages** (335/335); **no
`toolCall` block carries its own cost** (0 of 388); `toolResult` messages carry
none; and **66 of 335** assistant messages issued **more than one** tool call. So
**per-event cost does not exist**, and even message-level cost is not 1:1 with
events. H cannot rank targeted events from total session cost. The assumption is
fixed in §5 and labelled as an assumption.

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
  task weighting** (equal per task, split across eligible runs).
  **Event attribution (frozen, and labelled an assumption):** an assistant
  message's `usage` is split **equally across the tool calls that message issued**;
  a message with no tool call attributes its cost to no event. This follows from
  Gate 2 — captures carry no per-event cost. **Overlapping-cost handling** (when
  candidate event sets overlap) and **H's own abstention threshold** remain
  **`[FIX BEFORE RUN]`**.
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
| 1 | module → side assignment and multi-task modules (only ~21 modules) | `[CHOICE]` |
| 2 | diagnostic tower level list | `[FIX BEFORE RUN]` |
| 3 | singleton/admissibility bound | `[FIX BEFORE RUN]` |
| 4 | `R_min` (minimum eligible repetitions) | `[FIX BEFORE RUN]` |
| 5 | H: overlapping-cost handling | `[FIX BEFORE RUN]` |
| 6 | H abstention threshold; P `s_min` and `K` | `[FIX BEFORE RUN]` |
| 7 | `N_cand`, `R`, `δ`, split seed, model/config | `[FIX BEFORE RUN]` |
| 8 | module-size line bands (covariate) | `[FIX BEFORE RUN]` |
| 9 | implementation of the cost-variation share **and its §4.1 audit** | `[FIX BEFORE RUN]` |
