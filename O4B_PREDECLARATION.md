# O4B_PREDECLARATION.md

**Status: FROZEN BEFORE BASELINE RESULTS.**

**Study class: PILOT.** This is a diagnostic pilot. No result from it is a
commercial headline. Turning it into one requires a design and a power analysis
that this document does not assume.

This file fixes the *structure* of the O4b experiment — question, endpoint,
selection rule, accepted outcomes — **before** any baseline PDI number is
inspected. The intervention itself is **not** predeclared, because the claim is
that PDI says *where* to intervene. What is predeclared is the **rule that
selects** it.

Nothing here is a result. O4b remains **OPEN**.

---

## 1. Freeze stages and immutability

| stage | what is fixed | when |
|---|---|---|
| **Stage 1 (this commit)** | question, unit, endpoints, selection rule, accepted outcomes, coverage rules | now, before any run |
| **Stage 2** | corpus, verifier, task list, `δ`, `τ_min`, `K`, seed, CI method (every `[FIX BEFORE RUN]` field) | by a commit **before the first baseline run** |
| **Stage 3** | the selected intervention (from the discovery split only) | by a commit **before any held-out execution** |

**Amendment protocol.** After any baseline PDI profile has been inspected, this
file may not be changed in any way that affects endpoints, the selection rule, the
margins, or the splits. A change before that point must be a separate commit
stating the reason. The **fingerprint** of the freeze is the git commit that made
the change; every run log must cite it.

---

## 2. Question

> Can a **PDI-localized intervention** reduce **measured agent cost** while
> preserving **independently verified task success**?

Both halves are required. A cost reduction with degraded verified success is not a
positive result (see outcome **B**).

---

## 3. Corpus

`[FIX BEFORE RUN]` — not yet selected. Requirements, fixed now:

- **M deterministic tasks** in one workspace, each with an external verification
  that does not consult the agent's trajectory. `M = [FIX BEFORE RUN]`.
- **One fixed agent + one fixed configuration.** A **single** agent/configuration
  is sufficient for the first experiment. Multiple agents are
  replication/generalisation and are **out of scope** here.
- **Real cost or tokens captured per run.** If neither is available for a task,
  the task is excluded *and counted* (§8).
- The agent's own terminal state is **never** used as verified success.

## 4. Verifier

`[FIX BEFORE RUN]` — the exact command / method.

- Returns **PASS / FAIL / UNKNOWN**.
- Implemented through [`evaluators.py`](evaluators.py); **no verifier reads
  `turn.outcome`** or any other field produced by the agent.
- `UNKNOWN` is preserved as `unknown`, never coerced to `failure` or `success`.

## 5. Experimental unit

**Task × run.** Each task is run multiple times if cost is stochastic; the
resampling unit for all inference is the **task (task cluster)**, fixed before
analysis (§7).

## 6. Splits

- A **discovery split** and a **held-out split** over tasks, defined and frozen at
  Stage 2.
- **No held-out PDI profile and no held-out verified outcome may be inspected
  while selecting the intervention.** The selection rule (§9) operates on the
  discovery split only.
- A task appears on exactly one side.

## 7. Primary endpoint

**Δ cost per task** (intervention − baseline) on the **held-out** tasks, claimed
**only if** verified success is non-inferior.

**Non-inferiority margin `δ`: `[FIX BEFORE RUN]`.** Success is non-inferior if the
task-clustered confidence interval for (intervention − baseline) verified-success
rate lies entirely above `−δ`. The CI method is fixed before the run.

Secondary endpoints (reported, not primary): tokens, tool calls, PDI discovery
overhead, `j*`, and wall-clock time **only if** trustworthy. If wall-clock is
confounded by machine load, it is reported as unusable rather than adjusted.

## 8. Coverage (reported, never silently dropped)

- missing cost / missing tokens;
- missing verified labels, and `UNKNOWN` outcomes;
- tasks excluded, with the reason;
- any verifier or execution failure.

A primary claim is **not** made if coverage prevents it (outcome **D**).

## 9. Localization selection rule — FROZEN

Applies to the **discovery split only**.

1. For each discovery task `t`, run PDI on its baseline traces, with live status
   supplied by the **independent** verifier.
2. For each behavioural resolution `j`, compute the transient share
   `τ_j(t) = (n_j − L_j) / n_j` (skip levels with `n_j = 0`).
3. **Actionable levels** are declared in the corpus manifest at Stage 2: a level
   `j` is actionable only if the manifest maps it to an editable knob (e.g.
   tool-family policy, tool-ordering instruction, argument-targeting
   instruction). The mapping is fixed before any run.
4. Aggregate `τ_j` = **median** over discovery tasks whose baseline has at least
   one non-`UNKNOWN` label.
5. Select the actionable level `L*` maximising `τ_j`, subject to
   `τ_{L*} ≥ τ_min` and `τ_j(t) > 0` in at least `K` discovery tasks, with
   `τ_min` and `K` fixed before the run.
6. Tie-break: lowest level index (coarser first), then lexicographic level name.
7. **If no level satisfies (5): outcome C.** Stop.

The intervention is then the minimal change to the knob mapped to `L*`, as given
by the manifest's mapping template. It is written and committed (§1, Stage 3)
**before** any held-out execution.

## 10. Held-out test

Baseline and intervention are run under **matched conditions** on the held-out
tasks. The independent verifier supplies `verified_outcome` for every run. The
agent's terminal state is recorded but **never** used as verified success.

## 11. Resampling unit

**Task / task cluster**, fixed before analysis. Runs within a task are not
independent samples. Bootstrap or permutation over **tasks**, not runs.

## 12. Accepted outcomes

Every ending below is a **valid completion**. There is **no post-hoc
reclassification** of B, C or D as success, and no language that implies one.

| | outcome | meaning |
|---|---|---|
| **A** | **REMOVABLE WASTE** | intervention reduces cost while satisfying the predeclared non-inferiority criterion |
| **B** | **NECESSARY BEHAVIOUR** | targeted behaviour decreases, but verified performance violates non-inferiority |
| **C** | **NO STABLE ACTIONABLE SIGNAL** | PDI produces no localization satisfying the selection rule (§9.5) |
| **D** | **INCONCLUSIVE** | coverage, sample size, verifier failure, execution failure or variance prevents the primary claim |

## 13. Prohibited inferences

- No claim of causality beyond the predeclared intervention and matched held-out
  comparison.
- No generalisation from one agent/configuration to other agents.
- No commercial savings figure from this pilot, in any document.
- `UNKNOWN` is never folded into `failure` or `success`.
- Terminal state is never reported as task success.

## 14. Frozen now vs to-be-fixed

| frozen in this document (Stage 1) | `[FIX BEFORE RUN]` (Stage 2) |
|---|---|
| the question and its two halves | corpus / workspace |
| the experimental unit (Task × run) | task list and `M` |
| the endpoint structure and CI requirement | verifier command |
| the selection rule (§9, steps 1–7) | `δ`, `τ_min`, `K` |
| the split discipline and no-peeking rule | seed and CI method |
| the actionable-level requirement | the level→knob mapping |
| accepted outcomes A/B/C/D | — |
| coverage and prohibited-inference rules | — |
