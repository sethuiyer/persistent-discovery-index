# O4B_PILOT1_RESULT.md

**Status: CLOSED. Outcome: C — NO STABLE ACTIONABLE SIGNAL.**
Protocol: [`O4B_PREDECLARATION.md`](O4B_PREDECLARATION.md) (fingerprint `1887cdf`).
Corpus fingerprint: `586e1bee0cc12c50…` (superseding `517cbeda…` after the pi
`usage.cost` fix — same module split, see `180d256`).
Ruler: [`o4b_stat.py`](o4b_stat.py), unchanged.

## 1. What was executed

| | |
|---|---|
| discovery baseline runs | **24 / 24** scheduled and recorded (12 tasks × 2 runs) |
| `agent_settled` | 24 / 24 |
| regeneration hash matched the sealed corpus | 24 / 24 |
| verified outcomes | **success 24**, failure 0, unknown 0 |
| verifier UNKNOWN | 0 (verification coverage 100%) |
| cost present | **24 / 24** |
| total cost | **$0.0778** (mean $0.00324; min $0.00224; max $0.00512) |
| tokens | 292,136 in / 46,539 out |
| crashes / timeouts / invalid regenerations | 0 |

Held-out tasks: **not run.** Nothing was inspected on the held-out side.

## 2. Why the outcome is C

The frozen selection rule takes liveness from the independent verifier and uses
`τ_j(t) = (n_j − L_j) / n_j`. With **every** recorded baseline episode a verified
success, every represented class is live, so `L_j = n_j`, hence `τ_j = 0` at every
level and on every task. `τ_{L*} ≥ τ_min = 0.20` is therefore never satisfied, and
the rule requires **C** with no descent to another level.

## 3. Evidence limitation — recorded, not papered over

**The session traces were not persisted** by the runner version that produced these
24 runs, so the profile counts `n_j`, `L_j` were never computed. The outcomes and
costs are valid and are preserved verbatim, with a `WARNING`, in
`o4b_corpus/baseline_notraces.json`.

Therefore **C is established by implication from the declared liveness definition,
not by computed profile counts.** No rerun was performed: a rerun would create new
observations, could not recover the missing traces, and would not guarantee the
same 24/24 result. The implication is sufficient for the recorded cohort.

## 4. Two interpretations that must not be blurred

1. **Success does not imply the absence of waste.** A successful run can contain
   redundant searches, retries and unnecessary actions. The failure-linked liveness
   statistic cannot distinguish that overhead **when every class is live** — which
   is exactly the situation here.
2. **C does not establish corpus difficulty as the sole cause.** It establishes
   that **no actionable signal exists under this corpus and this instrument**. The
   corpus's 24/24 success is consistent with the outcome and plausibly contributes
   to it, but it is not proven to be the only cause, and this document does not
   claim it.

## 5. What was actually learned

- The **apparatus works end to end**: seeded defect injector → hash-checked
  regeneration → `pi --mode rpc` until `agent_settled` → verifier-protected
  grading → cost/tokens from real usage. Two harness defects (a false cost
  capability, and dropped pi costs) were found and fixed by the machinery itself.
- **Failure-linked liveness alone cannot localise inefficiency inside uniformly
  successful runs.** That is a property of the instrument as configured, and it
  shapes the next experiment.

## 6. No post-hoc reclassification

A/B/C/D were fixed before the baseline. C stands as C. Nothing in this result may
be narrated as a savings finding, and no held-out task was opened.
