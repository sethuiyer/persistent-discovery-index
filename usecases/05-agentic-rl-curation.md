# Use case 05 — Agentic-RL data curation & reward signal

> Use *which behavioural distinctions predict success* to filter trajectories and
> shape rewards — with an explicit error budget for what you discard.
>
> **Buyer:** training / research team
> **Data path:** rollout traces + independent success labels → `multiresolution.py`
> **Status:** the **algebra is discharged (O4a)**; the utility for RL is an **open experiment**.

## The pain

Agent rollouts are full of wandering. Success rewards are sparse, and credit
assignment across a 30-step trajectory is guesswork. Teams filter by hand or by
crude heuristics (length, tool count) that ignore *where* the useful work was.

## What PDI measures

- `L_j` marks the **persistent** classes at each resolution — the behaviour on
  successful trajectories; `n_j − L_j` is the transient.
- The **detail energies** `E_j = ‖D_j p‖²` localise *which refinement* carries
  success information, conditional on earlier levels (`O4_SCOPE.md` §9).
- `p̂_A` and the **pruning price** give an error budget for keeping only selected
  levels: `‖p − p̂_A‖² = ‖p − P_J p‖² + Σ_{j∉A} E_j`.

## Illustrative sketch (computed, exact)

From `test_multiresolution.py` — small, but exact:

```
planted-level:  E = [0, 1/4, 0]      signal localised to one refinement
xor-interaction: first feature E=0, second E=1/4   (both orders)
permutation null: E_perm[E_j] = p_bar(1-p_bar)/(N-1) * d_j   (exact)
```

The **permutation null** is the guardrail: more refinement dimensions produce more
empirical energy *with no signal*, so a raw `E_j` must be read against it.

## Proof status

- **Discharged (O4a):** the identities, the null, planted-structure sensitivity, and
  the pruning price — verified in exact arithmetic.
- **Not discharged:** that filtering trajectories by persistent yield improves RL
  sample efficiency, or that the detail levels transfer across tasks. Both are
  experiments, not facts.
- **Caveat:** the module consumes **caller-supplied partitions**; it does not build
  diagnostic features or verify label independence (`O4_SCOPE.md` §3.2, §4).

## Pilot (30–90 days)

1. Label a rollout set with an **independent** evaluator (not the agent's stop reason).
2. Compute detail energies and the null; report which levels exceed the null.
3. Filter trajectories by persistent yield; compare RL sample efficiency against a
   length/tool-count baseline, on held-out tasks.

## Risks / failure modes

- **Predictive ≠ causal**: a level's energy means it adds conditional information,
  not that the behaviour *causes* success.
- **Compressing the representation ≠ removing the actions** (`O4_SCOPE.md` §9.4).
- **`unknown` is not failure**: exclude it from the cohort and report coverage.
