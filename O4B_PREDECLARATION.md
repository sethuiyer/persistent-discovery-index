# O4B_PREDECLARATION.md

**Status: FROZEN BEFORE BASELINE RESULTS.**
**Stage 2 (corpus, verifier, statistic, parameters): FROZEN.**
**Study class: PILOT.** No result here is a commercial headline; that would require
a design and power analysis this document does not assume.

This file fixes the experiment **before** any baseline PDI number is inspected. The
*intervention* is not predeclared — the claim is that PDI says *where* to intervene.
What is predeclared is the **rule that selects it**, and the constraints on what
selecting it entitles us to change.

O4b remains **OPEN**. Nothing here is a result.

---

## 1. Freeze stages and immutability

| stage | what | status |
|---|---|---|
| **Stage 1** | question, unit, endpoints, selection rule, accepted outcomes, coverage rules | **frozen (v0.33.1)** |
| **Stage 2** | corpus, verifier, `M`, `R`, statistic, `δ`, `τ_min`, `K`, seed, splits, knob manifest | **frozen (this commit)** |
| **Stage 3** | the selected intervention | frozen before any held-out execution |

After **any** baseline PDI profile has been inspected, this file may not change in
any way that affects endpoints, the selection rule, margins, or splits. The freeze
fingerprint is the git commit; run logs must cite it.

## 2. Question

> Can a **PDI-localized intervention** reduce **measured agent cost** while
> preserving **independently verified task success**?

Both halves are required.

## 3. Corpus — FROZEN

- **Workspace: this repository** (`persistent-discovery-index`): deterministic
  suites, natural clusters (one per module), cheap resets, a verifier independent
  of the agent's trajectory. Self-hosting is accepted; **overclaiming from
  self-hosting is prohibited (§13)**.
- **M = 20** tasks from the seeded defect injector (§3a).
- **Agent: `pi` headless** (`pi -p --session-dir …`), **one fixed configuration:
  model `deepseek-flash`**, identical in both conditions.
- **R = 2** runs per task per condition. Maximum planned: `20 × 2 × 2 = 80` runs,
  spent in stages (§11), never all up front.
- **Cost/tokens** from pi's per-message `usage` (surfaced by `load_pi_session`).
- The agent's terminal state is **never** used as verified success.

### 3a. Task eligibility — checked before any PDI number is inspected

Each candidate task must demonstrate:

```text
clean frozen repo      -> verifier PASS
seeded mutation        -> verifier FAIL
(agent works the task)
independent verifier   -> PASS / FAIL / UNKNOWN
```

A task is **eligible only if the mutation deterministically flips PASS→FAIL** on
the clean tree. Ineligible tasks are excluded **and counted**. A task's cluster is
the module the mutation touches.

**No leakage**: the agent sees only the task specification it would naturally
receive. Nothing may disclose the mutated location, the failing assertion, or the
solution. The injector, the split, and the mutation seed are fixed by commit before
the baseline runs.

## 4. Verifier — FROZEN

- `python3 <the mutated module's test suite>` → exit 0 PASS, nonzero FAIL, cannot
  run UNKNOWN. Cross-cutting mutations use `python3 test_repo_consistency.py`.
- Implemented as `evaluators.command_exit`; it reads **no field the agent produced**.
- `UNKNOWN` is preserved, never coerced to FAIL or PASS.

## 5. Experimental unit

**Task × run.** Inference resamples **tasks** (§7), never runs.

## 6. Splits — FROZEN

- **12 discovery / 8 held-out**, assigned by **task cluster (module)**, seed
  **`20260916`**.
- Held-out task identities are generated deterministically and then **SEALED**: no
  held-out PDI profile, no held-out verified outcome, and no held-out failure may
  be inspected while selecting the intervention or tuning the injector.
- A held-out task found invalid for a preregistered eligibility reason (§3a) is
  reported as an **exclusion (coverage)**, not silently replaced.

## 7. Primary endpoint and the non-inferiority statistic — FROZEN

Held-out tasks `H` (target `|H| = 8`), clustered by module. For task `t` and
condition `c ∈ {B, I}` there are `R = 2` runs, each labelled by the verifier
`success` / `failure` / `unknown`.

**Success score.** `s_{t,c} = (#success) / (#success + #failure)` over that task's
runs. A task is **success-eligible** only if **both** conditions have ≥ 1
non-`UNKNOWN` run.

**Success estimand.** `d_t = s_{t,I} − s_{t,B}` (paired, by task), `D = mean_t d_t`
over success-eligible tasks.

**Non-inferiority.** Bootstrap **tasks with replacement, 10,000 resamples, seed
`20260916`**, percentile method. Let `D*₅` be the 5th percentile of the bootstrap
distribution of `D`. Then

> **Non-inferiority holds iff `D*₅ ≥ −δ`, with `δ = 0.10`.**

**Cost.** `C̄_{t,c}` = **mean** of run costs for that task/condition; a task is
**cost-eligible** only if **every** run in **both** conditions has non-null cost.
`Δ_t = C̄_{t,I} − C̄_{t,B}`, `Δ = mean_t Δ_t` over cost-eligible tasks; `Δ*₉₅` is
the 95th bootstrap percentile.

> **Cost reduction is established iff `Δ*₉₅ < 0`.**

Both bootstraps resample the **paired task-level quantities** — never individual
runs, and never baseline and intervention independently. `d_t` and `Δ_t` are
computed per task first; the bootstrap vectors are the lists of those per-task
values.

The primary claim uses tasks eligible for **both**; if the eligible sets differ,
both are reported. `n_both = |eligible for both|`.

**Secondary (reported, not primary):** tokens, tool calls, PDI discovery overhead,
`j*`, per-task direction consistency, wall-clock **only if** trustworthy (else
reported unusable).

**Small-`n` caveat.** `n = 8` is a pilot. The interval is fragile, and no
commercial claim may be built on it.

## 8. Coverage (reported, never silently dropped)

missing cost / tokens; missing verified labels; `UNKNOWN` outcomes; tasks excluded
and why; verifier or execution failure. A primary claim is not made if coverage
prevents it (**D**).

## 9. Localization selection rule — FROZEN

Applies to the **discovery split only**.

1. Run PDI on each discovery task's baseline traces, with live status from the
   **independent** verifier.
2. Per level `j`: transient share `τ_j(t) = (n_j − L_j) / n_j` (skip `n_j = 0`).
3. **Actionable levels** are those in the knob manifest (§9a). Q1 and Q6 are not
   actionable.
4. Aggregate `τ_j` = **median** over discovery tasks with ≥ 1 non-`UNKNOWN` label.
5. Select the actionable level `L*` maximising `τ_j`, subject to
   **`τ_{L*} ≥ τ_min = 0.20`** and `τ_j(t) > 0` in **≥ K = 5** discovery tasks.
6. Tie-break: lowest level index (coarser first), then lexicographic name.
7. **If no level satisfies (5): outcome C. Stop.** No descending to Q6.

### 9a. Knob manifest — what selecting a level entitles you to change

| level | allowed intervention class | forbidden |
|---|---|---|
| **Q2** tool multiset | tool-policy instruction | adding tools/MCP, changing model |
| **Q3** tool sequence | ordering instruction (read → edit → verify) | task-specific step lists |
| **Q4** error classes | recovery-policy instruction | task-specific retry scripts |
| **Q5** argument classes | search/read **scoping** guidance | disclosing the failing test or solution locations |
| **Q1 / Q6** | not actionable | — |

The intervention must change **agent policy**, never add **task information**.

## 10. Held-out test

Baseline and intervention run under **matched conditions** on the held-out tasks.
The verifier supplies every `verified_outcome`. Terminal state is recorded, never
used as success.

## 11. Spending order — FROZEN

1. generate corpus, validate §3a eligibility (no agent runs against held-out);
2. freeze the 12/8 split and fingerprint;
3. **discovery baseline only** (`12 × 1 × 2 = 24` runs);
4. apply §9 — level `L*` or **C**;
5. commit exactly one manifest-permitted intervention (Stage 3) **before** any
   held-out execution;
6. **only then** open held-out (`8 × 2 × 2 = 32` runs).

## 12. Accepted outcomes — no post-hoc reclassification

| | outcome | condition |
|---|---|---|
| **A** | **REMOVABLE WASTE** | `D*₅ ≥ −δ` **and** `Δ*₉₅ < 0` |
| **B** | **NECESSARY BEHAVIOUR** | `D*₅ < −δ` (verified success degraded), regardless of cost |
| **C** | **NO STABLE ACTIONABLE SIGNAL** | no level satisfies §9.5 — decided before held-out |
| **D** | **INCONCLUSIVE** | `n_both < 6`, or coverage/label failure, or non-inferior but cost reduction not established |

B, C and D are **valid completions** and may not be narrated as success.

## 13. Prohibited inferences

- No causality beyond the predeclared intervention and matched held-out comparison.
- No generalisation from one agent/configuration (`deepseek-flash`) to others.
- No commercial savings figure from this pilot, in any document.
- No "self-hosted so it must generalise" claim.
- `UNKNOWN` never folded into `failure` or `success`.
- Terminal state never reported as task success.

## 14. Frozen vs to-be-fixed

| frozen (Stage 2, this commit) | remaining |
|---|---|
| battlefield = this repository | generated task identities (committed at §11.2) |
| `M=20`, `R=2`, model `deepseek-flash` | the 12/8 concrete assignment (committed at §11.2) |
| verifier command and method | — |
| `δ=0.10` **with** the §7 statistic | — |
| seed `20260916`, `τ_min=0.20`, `K=5` | — |
| selection rule §9 and knob manifest §9a | — |
| spending order §11 and outcomes §12 | — |
