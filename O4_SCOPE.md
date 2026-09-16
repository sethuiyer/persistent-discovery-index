# O4 — Construct and validate an outcome-independent diagnostic tower

**Status: open.** Two discharge conditions, stated separately in §5. This is a
**scope note, not a result**: it specifies what can be discharged before
independently evaluated data exists, and what cannot.

Related: [`SPINE.md`](SPINE.md) §9 (O4), §2.3–§2.5; [`INTRODUCTION.md`](INTRODUCTION.md) §9.

---

## 1. Why this is needed

The shipped descriptive tower puts the terminal outcome at its coarsest level:

```python
Q1 = lambda h: h.outcome                      # adapters.tool_tower
Turn.succeeded  :=  (self.outcome == "stop")  # adapters.Turn
```

So the success label `p` is measurable at `Π₁`. Because `Π_j` refines `Π₁`,
`P_j p = p` for every `j ≥ 1`, hence every success-detail operator
`D_j = P_{j+1} − P_j` annihilates `p`:

$$E_j = \lVert D_j p \rVert^2 = 0 \quad (j \ge 1), \qquad
\text{all signal lives in } E_0 = \operatorname{Var}_\mu(p).$$

The proposed multiresolution success signal is therefore not *wrong* on this
tower — it is **vacuous**. Fixing that requires a separate tower that does not
contain the label, and an outcome that is not the agent's own termination status.

**Q1–Q6 are not modified by O4.** They remain the label-bearing descriptive
tower, so historical counts stay comparable. The diagnostic tower is additional.

### Dependence on the success criterion

The label `p` is not intrinsic to a trace: it is supplied by an **evaluator**.
Changing the evaluator changes `p`, and therefore `L_j`, `D` and `Δ`, **even when
the corpus, the tower and the scales are held fixed**. This is a distinct axis
from tower *presentation* dependence (§2.3–§2.4): one is a choice of *what counts
as behaviour*, the other a choice of *what counts as success*. Comparisons must
freeze the evaluator's **identity, version and configuration**, exactly as they
freeze the tower version — otherwise a difference in `Δ` can be an artefact of the
label rather than of the agent.

---

## 2. The A / B split

| | Work | Depends on |
|---|---|---|
| **A — machinery** | label-free diagnostic tower + detail-energy computation | nothing; buildable and testable now |
| **B — signal** | independent verified outcome; matched-task validation | independently evaluated, matched-task corpus |

A can be discharged before B. **Discharging A is not evidence for B.**

---

## 3. A — machinery (buildable now)

### 3.1 The operator

Fix positive weights `μ`, a labelled cohort `C` (see §4), and `p` = verified
success on `C`. For the diagnostic partition `Π_j`, with `V_j` its block-constant
functions:

$$P_j f = \mathbb E_\mu[f \mid \Pi_j], \qquad D_j = P_{j+1} - P_j, \qquad
\dim W_j = n_{j+1} - n_j.$$

Retain, per parent `C`, its mass, child masses, success sums and cost sums. For a
child `B ⊂ C`, with `p̄` the `μ`-weighted mean:

$$E_{j,C} = \sum_{B \subset C} \mu(B)\,(\bar p_B - \bar p_C)^2, \qquad
E_j = \sum_C E_{j,C} = \lVert D_j p \rVert^2.$$

Nested conditional expectations are orthogonal projections, so the ranges of the
`D_j` are mutually orthogonal and

$$\lVert p - P_j p \rVert^2 - \lVert p - P_{j+1} p \rVert^2 = E_j \ \ge 0,$$

$$\sum_j E_j \le \operatorname{Var}_\mu(p) \le \tfrac14 \ \text{(binary } p\text{)},$$

with the residual `‖p − P_J p‖²` reported when the finest partition does not
determine `p`. Weights are **normalised once and applied identically at every
level**; no renormalisation per level. The choice of `μ` — **per-run or
per-task** — is **configurable and must be declared explicitly**; there is no
universally correct choice, and the two answer different questions.

Module: `multiresolution.py` (no third-party dependency).

### 3.2 The diagnostic tower

Features must be **outcome-independent** (§4). Nesting is enforced at construction
(`multiresolution.PartitionTower`, raising `RefinementViolation`).

**Not implemented by A.** `multiresolution.py` consumes partitions **supplied by
the caller**; it does not build features and does not check that they exclude the
success label or the evaluator result. Feature provenance (§4) is a **separate
warrant**, not discharged by the O4a fixtures.

### 3.3 Acceptance fixtures (A)

1. **constant-label** — `p ≡ c`. Every `E_j = 0` and the residual is 0; the
   instrument reports zero rather than manufacturing structure.
2. **unequal-weight** — non-uniform `μ`. Energies agree with a direct weighted
   least-squares computation to tolerance.
3. **planted-level** — a signal planted at a declared level `j*`; `E_{j*} > 0`
   and `E_j ≈ 0` for `j ≠ j*`.
4. **unresolved-residual** — the finest partition does not determine `p`;
   `‖p − P_J p‖² > 0` is reported, not silently dropped.
5. **permutation-null** — the **exact test target** (9.2): on `N > 1` equally
   weighted histories with the observed labels uniformly permuted (count
   preserved, any success fraction), the empirical mean of `E_j` equals
   `p̄(1−p̄)/(N−1)·d_j`. This is a test of the formula; the *displayed* baseline on
   real data is a reference level, not a significance test.
6. **xor-interaction** — `p = A ⊕ B` on independent fair bits: the first-revealed
   feature carries zero energy and the second carries all of it, in either order
   (9.5). Pins that attribution depends on feature order.
7. **refinement-trap** — a *non-nested* partition (blocks straddling coarser
   blocks) must be **rejected at construction** by `QuotientTower.validate`, not
   merely produce a failing identity. For non-nested projections the null carries
   `tr[(P_{j+1} − P_j)²]`; substituting `n_{j+1} − n_j` is what nesting buys, so
   the guard protects the very hypothesis (9.2) needs.

These establish **correctness** and **sensitivity to planted structure**. They do
not establish usefulness on real workloads (§5).

---

## 4. Features, labels, and the leakage rule

**Excluded from the diagnostic tower:** the success label, and any **deterministic
encoding of the evaluator result** (e.g. a field that is a function of
`verified_outcome`). Otherwise the `E_j` collapse as in §1.

**A tool error is not automatically leakage.** A tool error is an *intermediate
event*: a successful run can recover from errors. Only terminal-status fields
that the evaluator reads are excluded. Every feature records its **provenance**
(source field, whether it is terminal-status or intermediate), so admissibility is
auditable rather than asserted.

| class | example | admissible? |
|---|---|---|
| intermediate event | tool error, retry, tool family/order, arg classes | yes — must carry provenance |
| terminal status of the agent | `outcome`, `stopReason` | no — encodes the label |
| evaluator result / encodings | `verified_outcome`, derived pass/fail flags | no |

**Schema (implemented v0.33.0; population validation later).** `Terminal_outcome`
is `Turn.outcome` (observational runtime state). The canonical record also carries
the independent label and its provenance:

| field | meaning |
|---|---|
| `terminal_outcome` | what the agent did (the existing `outcome`, kept) |
| `verified_outcome` | `success` \| `failure` \| `unknown` |
| `evaluator` | id, version, method (provenance of the label) |

Implemented in `adapters.Evaluator` / `adapters.Turn`, produced by
[`evaluators.py`](evaluators.py) — command exit status, artifact presence, file
content, exact answer — and carried by `ingest.to_canonical`. Cost/tokens
(`cost`, `tokens_input`, `tokens_output`) travel the same way. **No evaluator
reads `Turn.outcome`**: the `agent stopped -> task succeeded` route is closed by
construction, with a test in [`test_evaluators.py`](test_evaluators.py).

### Unknown is not failure

`unknown` is a third value, not a synonym for `failure`. Supervised energies are
computed **only on an explicitly declared labelled cohort** (`success` /
`failure`), never folding `unknown` in. **Label coverage** (share of the corpus
that is labelled, and the `unknown` fraction) is reported as a separate number.

---

## 5. Discharge conditions

O4 is discharged in two independent stages, and they are recorded separately:

- **O4a — synthetic correctness: DISCHARGED (v0.29.0)** by
  `test_multiresolution.py`. The finite accounting identity (9.1), the pruning
  price (9.3), the aggregation law (9.5), the permutation-null baseline (9.2) and
  the XOR interaction fixture all hold; the machinery is correct and sensitive to
  planted structure. **Warrant scope:** this discharges the **algebra** — valid
  nested projections and exact identities — **not feature provenance.** The module
  consumes caller-supplied partitions; it does not build the diagnostic features
  and cannot establish that they exclude the evaluator outcome (§4). That is a
  separate warrant.
- **O4b — real-data usefulness: OPEN.** The diagnoses reduce cost at preserved
  task quality. Requires an **independently evaluated, matched-task corpus**.
  **Not inferable from O4a**, and nothing in this note demonstrates it.

For O4b, **matched tasks are specifically required for agent comparisons**: agents
that ran different work are not comparable. The protocol freezes features, tower
version, **evaluator identity/version/configuration** and weights before
evaluation, assesses on held-out tasks, and reports sampling stability by
**task-cluster resampling**. Rare singleton classes can produce perfect in-sample
separation with no generalisable information; a negative cost–success covariance
is an **experiment to run**, not a causal finding.

**Input warrants gate the experiment.** Every loader declares what its records
support (`ingest.CAPABILITIES`); `require_capabilities(fmts, "o4b_cost")` refuses
the analysis on a capture that cannot warrant it, rather than running it on
best-effort data. O4b needs `verified_outcome` and `cost` at `supported`: no native
store provides both, but a **canonical** trace can — labels from an independent
evaluator ([`evaluators.py`](evaluators.py)), cost/tokens carried through from the
store. So the gate refuses every native store and admits a canonical trace that
actually carries the fields; presence is then reported as coverage.

---

## 6. Non-goals

- No change to `Q1`–`Q6` or to any historical descriptive count.
- No injectivity claim for comparison keys (see `test_ingest_integrity.py`).
- No population claim from synthetic labels; no causal claim from observational
  association.
- No claim that a negative `cost`–`success` covariance means deleting a branch
  improves anything.
- Compressing the **diagnostic representation** (§9.4) is not a licence to remove
  agent actions: the pruning price (9.3) is predictive, not causal.
- Energy at a level is not causation (§9.5); the null **reference level** is not a
  significance test (§9.3) — though the formula it is computed from is an exact
  synthetic test target.

## 7. Open questions

- Label source and evaluator identity for a real corpus — noting that the
  evaluator is itself a **presentation** the exponents are sensitive to (§1,
  dependence on the success criterion).
- Handling `unknown` beyond exclusion (masking and probabilistic weights are both
  unattractive; exclusion is the conservative default).
- Choice of `μ` (**per-run vs per-task**): configurable and explicit, with no
  universally correct default; its effect on `E_j` comparability must be stated.

## 8. Consistency coverage

As of v0.29.0 `multiresolution.py` exists and `O4_SCOPE.md` is in the `DOCS` set of
`test_repo_consistency.py`, so the `.py` paths named here are checked against
disk. The longer-term improvement is unchanged: the checker should distinguish
**planned** modules from **implemented** ones, so a scope note can enter coverage
*before* its code exists, not only after.

## 9. Wavelet extension — adaptive compression with an error budget

Trees admit a Haar-style construction and conditional expectation is orthogonal
projection; PDI already supplies the partitions and observables. The connection
is finite and testable — no infinite corpus, scaling exponent or convergence
assumption is needed, which suits the finite traces PDI actually receives. See the
tree-wavelet construction and the conditional-expectation foundations.\[1,2\]

**9.1 Exact accounting.** With a trivial root `P_0` — so that `P_0 p = p̄`, the
global `μ`-mean — one fixed, normalized `μ` used at *every* level, and nested
`P_0 … P_J`,

$$\operatorname{Var}_\mu(p) = \sum_{j=0}^{J-1}\|D_j p\|_\mu^2 + \|p - P_J p\|_\mu^2. \tag{9.1}$$

Variation resolved at each refinement, plus unresolved variation. Exact at finite
resolution. The root condition is load-bearing: the telescoping of `P_0 … P_J`
starts at `‖p − P_0 p‖² ≤ Var_μ(p)`, with equality **iff** `P_0 p = p̄` — i.e. iff
every root block has the same `μ`-mean. A trivial root always qualifies; a
non-trivial root can also qualify (balanced blocks), and otherwise the identity is
a statement about `‖p − P_0 p‖²`, not `Var_μ(p)`.

**9.2 Total energy is a bad objective.** If the finest partition is discrete then
`P_J p = p` and `Σ_j E_j = p̄(1−p̄)` — identical for every such tower at a fixed
success rate, *including a tower built from meaningless episode identifiers*. So
the useful question is **how compactly, and how reproducibly on unseen tasks,
behavioural distinctions explain outcomes.** Zero energy also does not mean no
useful work: a partition containing only successful runs has zero success energy.

**9.3 Null baseline — report it.** Fix a tower independently of the labels. For
`N > 1` equally weighted histories and a **uniform permutation of the observed
labels that preserves their count** — any success fraction, not necessarily ½ —
the refinement adds `d_j = n_{j+1} − n_j` dimensions and

$$\mathbb E_{\mathrm{perm}}[E_j] = \frac{p̄(1-p̄)}{N-1}\, d_j. \tag{9.2}$$

The detail projection has rank `d_j`, annihilates constants, and the permutation
covariance is isotropic on the mean-zero subspace. **(9.2) assumes nesting.** For
arbitrary partition projections the null carries
`tr[(P_{j+1} − P_j)²]`, and replacing that by `n_{j+1} − n_j` is valid only when
the projections are nested — equivalently when `rank D_j = trace D_j = d_j`. An
implementation must **reject non-nested partitions**, not merely report a
failing identity.

Verified by exact enumeration over the `C(6,3) = 20` count-preserving labelings of
an `N = 6` tower. More detail dimensions produce more empirical energy **with no
behavioural signal**. Two readings, kept sharp:

- the **formula (9.2) is an exact synthetic test target** — fixture 5 checks it;
- the **reference level displayed on real data is not a significance test** — it
  is a mean under the null to report alongside raw energy.

Unequal weights and task-dependent structure need their own null model.

**9.4 Pruning with an error budget.** For a selected set `A` of detail levels,
`p̂_A = P_0 p + Σ_{j∈A} D_j p`, and orthogonality gives

$$\|p - \hat p_A\|_\mu^2 = \|p - P_J p\|_\mu^2 + \sum_{j \notin A} E_j. \tag{9.3}$$

Discarding distinctions has an exact predictive price, so a smaller description
can be chosen against an **error budget**: pick the pruning on training data and
measure the predictive loss on **held-out** tasks. This compresses the
**diagnostic representation**; it does not establish that the corresponding agent
actions can safely be removed.

**9.5 Aggregation, and attribution depends on order.** Merging adjacent stages is
additive, `‖(P_b − P_a)p‖² = Σ_{j=a}^{b-1} E_j`, so inserting intermediate levels
redistributes energy while preserving the total between fixed endpoints. But
attribution depends on feature order: for `p = A ⊕ B` on independent fair bits,
the first-revealed feature carries **zero** energy and the second carries all of
it (verified exactly, both orders). So *"energy appeared at the retry level"*
means **retries add predictive information conditional on the earlier features**
— it does not mean retries caused the outcome.

**Product reading.** A compact, held-out-validated behavioural explanation of
success *and* measured cost — chosen against an explicit error budget — is the
testable benefit, not a smaller raw energy.

*References.* \[1\] Gavish, Nadler, Coifman, *Multiscale wavelets on trees*
(<https://www.math.ucdavis.edu/~saito/data/acha.read.s11/gavish-nadler-coifman-wavelets_trees.pdf>).
\[2\] Conditional-expectation projections
(<https://www.stat.cmu.edu/~arinaldo/Teaching/36710-36752/Lecture_Notes/lec_notes_9.pdf>).
