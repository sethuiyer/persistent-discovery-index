# The PDI Spine

A mathematical summary of what has been established, computed, ruled out, and left
open. Everything below is either proved here, proved in another module and cited,
or explicitly labelled otherwise. **Nothing in this document is claimed beyond its
stated status.**

---

## 0. Status ledger

| # | Claim | Status |
|---|---|---|
| 2.1 | Gauge law: `dim_{d^β} = β⁻¹ dim_d` | **proved** (standard metric scaling) |
| 2.2 | `dim_B(∂T) = limsup_j log L_j / (−log ε_j)` | **proved** (§2.2) |
| 2.3 | Cofinal invariance of the persistent exponent `D` | **proved** (§2.3) |
| 2.4 | `Δ = S − D` is not cofinal-invariant | **proved by counterexample** (§2.4) |
| 2.5 | `L_j` non-decreasing at fixed horizon | **proved** (injectivity) |
| 3.1 | The finite-window sup is not the limsup | **proved by counterexample** (§3) |
| 4.1 | Transport is a total deterministic map on the state space | **proved** (construction) |
| 5.1 | The coarsest `T`-stable refinement exists and is computable | **proved** (§5) |
| 6.1 | Functional-graph decomposition into recurrent core + trees | **standard** |
| 6.2 | `T` restricted to the recurrent core is a permutation | **proved** (immediate from 6.1) |
| 7.1 | `C_L ↪ F_p^×` when `L \| p−1`; character `φ: C_L → U(1)` | **standard** |
| — | Particular quotient sizes, cycle lengths, collision counts | **computed**, instance-dependent |
| 8.1 | No injective loop among 216 tested | **empirical negative**, not a proof |
| 8.2 | Augmenting with tabu memory does not restore injectivity | **empirical negative** |
| 8.3 | No `T`-stable quotient obtained from the branch or basin partition directly | **proved by counterexample** |
| 9.1 | The stable fibre is loop-independent (canonical) | **open** — known to vary |
| 9.2 | The persistent/transient pattern recurs at two levels | **conjecture** (§10) |
| 12 | Provenance: every layer has a verified literature underneath | **cited** (§12) |
| 13.1 | The survival square commutes on the quotient axis (T-invariant refinement) | **proved + verified** (§13.1) |
| 13.2 | It fails on the inclusion axis, iff some periodic point of `X` lies in the filter but leaves it | **proved + verified as an iff** (§13.2) |
| 13.3 | T-invariance of the refinement axis is exactly what forces commutation | **proved** (§13.2) |
| 13.4 | `Ω` has no content as a PDI quantity (identically zero on its own axis) | **negative** (§13.4) |
| 14.1 | `n_j` is invariant under the survival predicate — it is survival-free | **proved + verified** (§14.3) |
| 14.2 | PDI implements **two** survival predicates (horizon, explicit) which can select disjoint branches | **verified** (§14.2) |
| 14.3 | `Δ` moves while `L_j` and `D` are held fixed | **proved + verified** (§14.4) |
| 14.4 | The one-question reduction holds for one column only | **conclusion, narrower than claimed** (§14.5) |
| 15.1 | The recurrent core does not determine the transient structure | **proved by counterexample** (§15.1) |
| 15.2 | The ledger counts do not determine the structure (`n_j`, `L_j` identical; trees non-isomorphic) | **proved by counterexample** (§15.2) |
| 15.3 | The ledger is a lossy projection; the distinction lives in the edges | **conclusion** (§15.3) |

---

## 1. The tower and the two ledgers

Let `H` be a set of histories, and let

$$Q_j : H \to X_j, \qquad X_j = H/{\sim_j}, \qquad j = 1,\dots,J$$

be a refining tower of behavioural quotients, i.e. for all `j`

$$Q_{j+1}(x) = Q_{j+1}(y) \;\Longrightarrow\; Q_j(x) = Q_j(y). \tag{1.1}$$

Let `ε_j` be the physical resolution at level `j`, decreasing in `j`. Fix a
distinguished subset `P ⊆ H` of *persistent* histories (those reaching a
successful outcome). Define the two ledgers

$$n_j \;=\; |X_j|, \qquad L_j \;=\; |Q_j(P)|. \tag{1.2}$$

`n_j` counts everything distinguished at resolution `j`; `L_j` counts what survived.
Equation (1.1) is enforced in code (`QuotientTower.validate`) and is what makes the
levels a tower rather than a list of arbitrary feature functions.

With a tower, `n_j = |H/∼_j|` **exactly** — verified level by level against an
independent class count.

---

## 2. The invariant

### 2.1 Gauge law

For `β > 0`, balls of `d`-radius `ε` are `d^β`-balls of radius `ε^{1/β}`, so
`N_{d^β}(ε) = N_d(ε^{1/β})` and

$$\dim_{d^\beta} = \frac{1}{\beta}\dim_d. \tag{2.1}$$

This is why a level-indexed visual metric is gauge-dependent: reindexing the tower
changes `β`.

### 2.2 The persistent exponent is the live covering growth

**Proposition.** With the visual metric `d = 2^{−r}` on the boundary of the
discovery tree,

$$\dim_B(\partial T) \;=\; \limsup_j \frac{\log L_j}{-\log \varepsilon_j}. \tag{2.2}$$

*Proof.* Level-`j` cylinders cover `∂T`, and distinct level-`j` cylinders are at
distance `≥ 2·2^{−j}`, so no set of diameter `≤ 2^{−j}` meets two of them. Hence
`N(∂T, 2^{−j}) = L_j` exactly, and `N` is constant on each dyadic band. The box
dimension is therefore the dyadic covering growth of `L_j`. ∎

The mechanism matters: `L_j` is a **covering count**, a function of physical scale.
`n_j` is not — dead ends cover nothing — so `n_j` has no intrinsic scale-function
interpretation and only exists as a shell-indexed sequence.

### 2.3 Cofinal invariance of `D`

**Definition.** Define

$$D \;=\; \limsup_j \frac{\log L_j}{-\log\varepsilon_j},
\qquad
S \;=\; \limsup_j \frac{\log n_j}{-\log\varepsilon_j},
\qquad
\Delta \;=\; S - D. \tag{2.3}$$

**Proposition.** Let `P, P'` be towers on the same space with `ε_j → 0`, cofinal
in resolution and with the same boundary. Then `D_P = D_{P'}`.

*Proof.* By (2.2), `D` is the upper box dimension of the boundary in the metric
built from the mesh sequence of the *base space*, which the towers share. Cofinality
supplies the same physical scales up to constants, so the covering functions agree
asymptotically. ∎

**Caveat, and it matters.** This is a statement about the *asymptotic* quantity.
The finite-window estimator of §3 computes `max` over the observed levels and does
**not** inherit the invariance automatically — a `limsup` over a cofinal
subsequence can be smaller than the `limsup` over all levels. The invariance is a
property of `D` itself, not of the number the implementation prints, and §3 exists
because of exactly that gap.

### 2.4 `Δ` is not invariant

**Proposition.** `Δ` is not cofinal-invariant.

*Proof (counterexample).* Take `L_j = 2^j` with `n_j = 4^j` on odd shells and `2^j`
on even shells — realizable, since `L_j` is non-decreasing is the only constraint
beyond `L_j ≤ n_j`. Then `Δ = 1` for `P` and `Δ = 0` for `P' = P_{2j}`, while
`D` is unchanged. ∎

**Corollary.** `Δ ≥ 0` always, with equality iff `limsup log n_j/(−log ε_j) =
limsup log L_j/(−log ε_j)` — i.e. iff dead ends do not asymptotically dominate.

---

## 3. Estimation, and what the exponents do not mean

The definitions in (2.3) are `limsup`s over infinitely many scales. On finite data
one computes the **sup over the observed window**, and these differ:

**Proposition.** For `n_j = 1 + w(j−1)` the ratio `log n_j / j` decays to `0`, so the
true `S = 0`; yet the window sup reports `log₂(1+w)/2`, attained at `j = 2`,
independent of depth. The window statistic is not a noisy estimate of `S`; it is a
different statistic.

Consequences, implemented:

* the estimator is reported in **two layers** — finite-scale diagnostics (exact on
  the observed corpus: yield, inflation, distinction onset) and asymptotic
  diagnostics (the moving tail `M_m = sup_{j≥m} s_j`, with convergence status
  `STABLE / TRENDING_UP / TRENDING_DOWN / UNRESOLVED / NONE`);
* the layer distinction is not cosmetic: for `n_j = 1 + w(j−1)` the window sup is
  frozen at a shallow shell while the tail decays toward `0`.

---

## 4. Transport

Fix a finite state space `F` (the stable quotient, §5) and a closed loop in
presentation space

$$\gamma : \lambda_0 \to \lambda_1 \to \cdots \to \lambda_0,$$

driven by a **stateful** process `x_{t+1} = F(x_t, λ_t)`. A memoryless process has
`x = f(λ)`, so `T_γ = id` by construction and no transport question exists.

Define the transport map

$$T_\gamma : F \to F, \qquad T_\gamma(x) = \text{state after traversing } \gamma. \tag{4.1}$$

**Requirement (c), history.** `T_γ` is a bijection only if the process is
stateful. This is why the first Sudoku probe returned a trivial transport: the
searcher had no memory. Memory is the *precondition* of the whole construction.

---

## 5. The stable quotient

**Definition.** A partition `π` of `F` is `T`-stable if

$$x \sim_\pi y \;\Longrightarrow\; T(x) \sim_\pi T(y). \tag{5.1}$$

**Proposition (existence).** For any `T` and any initial partition `π₀`, the
coarsest `T`-stable refinement of `π₀` exists and is computable by iterating the
refinement key

$$\kappa(x) \;=\; \big(\text{block}(x),\; \text{block}(T(x))\big) \tag{5.2}$$

to a fixpoint.

*Proof.* Refinement is monotone and bounded by the discrete partition on a finite
set, so it terminates. The fixpoint satisfies (5.1): if `κ(x) = κ(y)` then
`block(T(x)) = block(T(y))`. Coarsest because every `T`-stable refinement of `π₀`
must separate states on which `κ` differs, so it refines the fixpoint. ∎

**Computed** (over the full state space, `n = 12`, 4096 states, Max-Cut with two
optima):

| `tabu` | `steps` | refinement profile | blocks | bijective |
|---|---|---|---|---|
| 2 | 4 | 2 → 4 → 4 | 4 | **no** |
| 2 | 8 | 2 → 4 → 8 → 16 → 24 → 24 | 24 | **no** |
| 3 | 8 | 2 → 4 → 8 → 12 → 12 | 12 | **no** |
| 4 | 8 | 2 → … → 40 | 40 | **no** |

The stable quotient exists and is small (a 100–1000× compression), but the induced
map `π → π` is **many-to-one** in every case tested.

---

## 6. The recurrent core

**Proposition (standard).** Every finite map `T : F → F` decomposes its functional
graph into a **recurrent core** `R ⊆ F` (the union of cycles) and transient trees
`F \ R`. On `R`, `T|_R` is a permutation.

This is the first place invertibility is **earned rather than assumed**: a cycle is
a permutation by definition, not by fiat.

Computed for the `n = 12, tabu = 2, steps = 8` case:

$$24 \;=\; \underbrace{16}_{\text{transient}} \;+\; \underbrace{8}_{\text{recurrent}}, \qquad
\text{cycle lengths} = (1,1,2,4).$$

So the recurrent part carries genuine cyclic actions `C_1, C_2, C_4`.

---

## 7. Characters

**Proposition (standard).** Let `C_L` be a cyclic group of order `L`. For any prime
`p` with `L | (p−1)`, there is an injective homomorphism `C_L ↪ F_p^×`; composing
with the discrete logarithm gives a character

$$\varphi : C_L \to U(1), \qquad \varphi(g^k) = \exp\!\left(\frac{2\pi i k}{p-1}\right). \tag{7.1}$$

**Status, stated precisely.** The character exists for the cycle lengths that were
**found** — `4 | 4, 12`, `2 | 2, 4, 6` — so (7.1) is a representation of a group the
transport produced, not of one posited in advance.

**What this is not.** Choosing `T_a(x) = ax mod p` as the transport makes
invertibility true *by construction*, and a residual `h = Π aᵢ` is a property of
labels chosen, not discovered. That is a model of the target, not a construction of
it. The earned statement is narrower: **the recurrent core of the real transport is
invertible, and `C_L ↪ F_p^×` gives it coordinates.**

---

## 8. Negative results

**N1. No injective loop among those tested.** Over 216 loops (`n = 10`, varying
schedule, `tabu`, `steps`), the induced map on the stable quotient was injective
**0 times**. Quotient sizes ranged 4–33. The collapse is therefore not an artefact
of a badly chosen schedule. *This is an empirical negative over a finite search, not
a proof that no injective loop exists.*

**N2. Augmenting with tabu memory does not restore invertibility.** Transporting
`(x, tabu)` instead of `x`, the augmented map is still many-to-one, and the induced
map on the augmented stable quotient is still non-injective (6–22 blocks, with
2{,}284–18{,}652 collisions remaining over an 18,688-state augmented space). The
memory projection was *a* source of collapse; removing it was not sufficient.

**N3. Branches and basins are the wrong fibre.** Neither the partition by nearest
optimum (2 blocks) nor by greedy-descent basin (94 blocks) is `T`-stable. The
correct fibre had to be constructed (§5), not guessed.

---

## 9. Open problems

**O1. Canonical fibre.** The stable quotient is loop-specific: different
`(tabu, steps)` yield 4, 12, 24, 40 blocks. Whether there is a schedule-independent
fibre within a suitable class of loops is open.

**O2. Injective transport.** N1 is empirical. Either exhibit an injective loop, or
prove that the induced map on the stable quotient of this family is necessarily
non-injective.

**O3. Sufficient augmentation.** N2 rules out tabu memory as sufficient. Whether
*some* finite augmentation makes the dynamics invertible is open — it is the same
question as whether the process has a reversible lift.

---

## 10. The recurring pattern (conjecture)

At two different levels the same decomposition appears, and in both cases the
persistent part is exactly where canonical structure lives:

| | persistent part | structure it carries | transient part |
|---|---|---|---|
| Tower (§2) | `L_j` — live classes | `D` is cofinal-invariant | `n_j − L_j`; `Δ` presentation-dependent |
| Transport (§6) | recurrent core `R` | `T\|_R` is invertible | `F \ R`; `T` many-to-one |

**Conjecture.** These are two instances of one phenomenon: *survival* — to a
horizon, or under iteration — is the condition under which a canonical invariant
exists, and non-surviving structure is exactly where presentation-dependence lives.

**Status: pattern, not theorem.** The two decompositions are of different objects
(quotient classes of histories; states of a finite dynamical system) and no common
construction is exhibited that produces both. What would upgrade it: a functor
carrying the tower's live/transient split to the transport's recurrent/transient
split, or a single definition of "survival" of which both are instances. Until
then the honest description is a structural resemblance that has held in every case
computed.

---

## 11. Summary of the spine

$$\text{memory} \;\to\; \text{non-identity transport} \;\to\; \text{stable fibre}
\;\to\; \textbf{recurrent invertible core} \;\to\; C_L \;\to\; U(1)$$

with the invertible step earned on the recurrent part only, the transient remainder
stated rather than hidden, and §10 flagged as conjecture.

---

## 12. Provenance — what each layer is built on

Every layer of the spine has an established literature underneath it. **PDI did not
invent these; it assembles them and keeps the accounting.** What is new here is the
two-ledger split (§1) and following the stack until the recurrent core appears
(§6). What is *not* claimed: a new refinement algorithm, a new persistence theory,
or topological persistence of any kind.

### Quotients and behavioural towers

- **R. J. van Glabbeek**, *The Linear Time – Branching Time Spectrum I*, in
  Handbook of Process Algebra, 2001, pp. 3–200.
  DOI [10.1016/B978-044482830-9/50019-9](https://doi.org/10.1016/B978-044482830-9/50019-9)
  — the spectrum of behavioural equivalences. PDI's `Q_j` tower is a refining family
  in exactly this sense, and equation (1.1) is the refinement ordering.

- **P. C. Kanellakis, S. A. Smolka**, *CCS expressions, finite state processes, and
  three problems of equivalence*, Information and Computation 90(1), 1990.
  DOI [10.1016/0890-5401(90)90025-D](https://doi.org/10.1016/0890-5401(90)90025-D)
  — partition refinement for bisimulation on finite processes. **This is the
  algorithm used in §5**, applied to a transport map rather than a transition
  relation.

- **R. Glück, B. Möller, M. Sintzoff**, *Model Refinement Using Bisimulation
  Quotients*, AMAST 2010, LNCS 6486, pp. 76–91.
  DOI [10.1007/978-3-642-17796-5_5](https://doi.org/10.1007/978-3-642-17796-5_5)
  — reduce a system to a bisimulation quotient, then refine to meet a property.
  The move in §5 — *refine `∼` until `x ∼ y ⟹ T(x) ∼ T(y)`* — is this operation.

### Persistence versus transient structure

- **D. Cohen-Steiner, H. Edelsbrunner, J. Harer**, *Stability of Persistence
  Diagrams*, Discrete & Computational Geometry 37(1), 2007.
  DOI [10.1007/s00454-006-1276-5](https://doi.org/10.1007/s00454-006-1276-5)
  — the stability theorem that makes "persistent" quantitative rather than
  metaphorical.

- **H. Edelsbrunner, J. Harer**, *Computational Topology: An Introduction*,
  American Mathematical Society, 2009.
  DOI [10.1090/mbk/069](https://doi.org/10.1090/mbk/069)

> **Stated to avoid a false equivalence.** PDI's "persistent" is **not**
> topological persistence. It means *survival* — of a quotient class to an
> observation horizon (§2), or of a state under iteration (§6). The word is shared;
> the construction is a different one.

### Growth rates and generating functions

- **T. Mayama**, *Finite-state enumeration of adjacency-constrained 132-avoiding
  permutations*, [arXiv:2605.23519](https://arxiv.org/abs/2605.23519) —
  finite-state decomposition yielding rational ordinary generating functions.

> **Characterisation corrected.** The tweet cited this for Cauchy–Hadamard. It does
> not use Cauchy–Hadamard. It is cited here for the property that actually matters:
> **a finite state decomposition forces rational generating-function growth**, which
> is the same structure PDI's finite quotient has, and the reason `n_j` growth is
> geometric when the quotient is finite.

Cauchy–Hadamard itself is textbook and needs no citation.

### Monodromy, holonomy, transport

- **J. J. Duistermaat**, *On global action-angle coordinates*, Communications on
  Pure and Applied Mathematics 33(6), 1980.
  DOI [10.1002/cpa.3160330602](https://doi.org/10.1002/cpa.3160330602)
  — the canonical example of **non-trivial monodromy with no curvature**: parallel
  transport around a loop fails to return. This is the object §4–§6 are a finite,
  discrete analogue of.

- **S. Kanno et al.**, *Gauge Geometry of Hodge Zero-Mode Transport in
  Parameter-Dependent Topological Data Analysis*,
  [arXiv:2605.28326](https://arxiv.org/abs/2605.28326) — represents homological
  features as zero modes of the combinatorial Hodge Laplacian and computes
  **curvature and holonomy as descriptors of local reorganisation and accumulated
  memory** in evolving topological structure. This is the closest existing work to
  the transport experiment of §4–§6, and it is recent.

### The fibre construction

The "refine until `T` is a map" move is the partition-refinement line above
(Kanellakis–Smolka; coalgebraic refinement). PDI's contribution is not the
algorithm but the **two ledgers** (§1) and the observation that, once the fibre is
constructed, the transport decomposes into an **invertible recurrent core** and an
irreversible remainder (§6) — which is where the group structure and the characters
of §7 live.

---

## 13. The commuting square — answered

Two ways to delete what does not survive. `S_res` deletes what does not survive
**refinement**; `S_dyn` deletes what does not survive **iteration**.

$$\mathcal S_{\rm res}(X) \;=\; \varprojlim_j X_j, \qquad
\mathcal S_{\rm dyn}(X) \;=\; \operatorname{core}(X,T) \;=\; \{x : \exists n\ge 1,\; T^n(x)=x\}$$

Both routes to the bottom-right of the square are computable:

$$A = \mathcal S_{\rm dyn}\mathcal S_{\rm res}(X), \qquad
B = \mathcal S_{\rm res}\mathcal S_{\rm dyn}(X), \qquad
\Omega = \operatorname{defect}(A,B).$$

The answer depends **entirely on which kind of refinement axis is used**, and the
two axes are genuinely different. Built and searched exhaustively in
`survival_commutation.py`; self-checking in `test_survival_commutation.py`.

### 13.1 The quotient axis — `Ω = 0`, degenerately

Levels are quotients of a common finite set, with surjective and `T`-invariant
bonding maps. This is PDI's actual structure (§1). Both routes collapse, for two
independent reasons:

- Both operators act on subsets of one set, so they commute by associativity of
  intersection — a square whose two arms are both "intersect with a fixed set"
  cannot fail.
- A finite tower of quotients of one finite set has **inverse limit = its finest
  level**. So `S_res` discards nothing and both routes reduce to the same core.

The one non-trivial step is a fibre argument: if a block is periodic at a coarse
level, then `T^k` maps its fibre into itself, and a self-map of a finite set has a
periodic point — hence the coarse core is the image of the fine core.

Computed over **1,204,224** `(T, tower)` systems at `n ≤ 4`: **zero** mismatches,
with `T` descending through the bonding maps in every single one.

### 13.2 The inclusion axis — `Ω ≠ 0`, with an exact characterisation

Here the filter `F` is an inclusion (a filtration, TDA-style) and is **not**
required to be `T`-invariant. Then

$$\boxed{\;\Omega \neq 0 \quad\Longleftrightarrow\quad
\exists\, x\in F \text{ periodic with } T^n(x)\notin F \text{ for some } n\;}$$

Verified as an **iff** over all 3,754 `(T,F)` pairs at `n ≤ 4`: 1,274 failures
(33.9 %), the iff holding in 3,754/3,754 cases, and **zero** failures among the
1,139 pairs where `F` happens to be `T`-invariant.

### 13.3 Minimal witness

`n = 2`. Let `X = {0,1}`, `T` be the swap (a 2-cycle), `F = {0}`.

$$A = \operatorname{core}(T,F) = \varnothing, \qquad
B = \operatorname{core}(T,X)\cap F = \{0\}, \qquad A \neq B.$$

Refine first and the cycle dies; iterate first and it survives the clip. Order of
observation genuinely matters — but only here.

### 13.4 What this settles, and what it costs

**T-invariance of the refinement axis is exactly the hypothesis that forces
commutation.** The quotient axis satisfies it by construction; a TDA filtration
does not.

- **Negative (about `Ω` as a PDI quantity).** On PDI's own axis `Ω` is
  *identically zero*. Building the square as a search for `Ω ≠ 0` over the
  quotient tower could only ever have returned nothing, and that is now a theorem
  rather than a guess. `Ω` is **not** a new PDI invariant.
- **Positive (about where `Ω` lives).** `Ω` is a genuine non-zero invariant of the
  *hybrid* setting — persistence of a Conley index across a filtration. It belongs
  to that literature, not to PDI's tower.

What survives on PDI's axis is therefore not a defect to measure but a
**construction**: the inverse limit of the recurrent cores

$$R_\infty = \varprojlim_j R_j$$

together with descent of the dynamics, `π_{j+1,j} T_{j+1} = T_j π_{j+1,j}`, which
held in every case tested. §13.1 confirms that the square is not the obstruction to
building it.

---

## 14. The motherboard question — and its residue

> *"Does it go away, or does it come back?" — everything else is a change of
> language for that question.*

Tested rather than agreed with, in `one_question.py`; suite
`test_one_question.py`. The test is behavioural: **a quantity that moves while the
survival predicate is held fixed is not a translation of the question.**

### 14.1 The table

| item | reduces to the dichotomy? |
|---|---|
| persistent boundary vs interior | **yes** — what survives refinement |
| `D` | **yes** — the rate of what comes back |
| functional graph (cycle vs tree feeding a cycle) | **yes** |
| `T\|R` vs `T` off `R` (permutation vs many-to-one) | **yes** |
| `C_L`, `F_p^×` | **yes**, downstream — structure *on* what returns |
| `χ: C_L → U(1)` | **yes**, downstream — the phase of what returns |
| `π(R_{j+1}) ⊆ R_j` | **yes** — does a return survive a change of resolution |
| `Ω` | **yes** — the failure of the previous line (§13) |
| `n_j` | **no** — there is no success mark in it |
| `S`, `Δ` | **no** — `S − D` needs a survival-free cost |
| `j*` (onset) | **no** — a location needs both columns |

### 14.2 The question is not yet one question: "comes back" is two predicates

PDI ships two, and they are not the same thing:

- **horizon rule** (`recompute_statuses`) — LIVE ⟺ the node has a descendant at
  level `H`. *Structural.*
- **explicit rule** (`finalize_explicit`) — LIVE ⟺ the node lies on a chain
  declared successful. *Outcome.*

Same tree, both readings, `n_j` identical, and the level-1 live sets are
`{(1,)}` versus `{(0,)}` — **disjoint**. The *counts* agree at that level (both
1), so a scalar ledger hides what the set makes visible; the counts diverge from
level 4 onward.

So the motherboard question is well-posed only once "comes back" is pinned to a
rule. That is not a philosophical caveat — it is a code path.

### 14.3 `n_j` is survival-free

Fixed node set; only the success marks varied:

| `j` | 1 | 2 | 3 | 4 | … |
|---|---|---|---|---|---|
| `n_j` (marker branch dead) | 3 | 5 | 9 | 16 | … |
| `n_j` (marker branch live) | 3 | 5 | 9 | 16 | … |
| `L_j` (marker branch dead) | 2 | 4 | 8 | 16 | … |
| `L_j` (marker branch live) | 3 | 5 | 9 | 16 | … |

`n_j` does not move. It is decided by the **node set**, not by any survival
predicate. The dichotomy cannot produce it — there is nothing for it to be a
translation *of*.

### 14.4 `Δ` moves while survival is fixed

Two systems with identical `L_j` and identical `D`:

$$A:\; D=1.0,\; S=1.0,\; \Delta=0.0
\qquad
B:\; D=1.0,\; S=1.720628,\; \Delta=0.720628$$

`Δ` is therefore not a function of the survival predicate. It is `S − D`: a
survival-free growth rate minus a survival growth rate. This is also why `D` is
cofinal-invariant (2.3) while `Δ` is not (2.4) — the survival side is intrinsic,
the cost side is not.

### 14.5 The sharpened thesis

The dichotomy is not the original move. It is the **standard** move. Conley
invariant sets, topological persistence, bisimulation minimisation, dead-code
elimination: every field that deletes what does not survive is applying it.

> **PDI's original move is the pairing**: a survival-free cost and a survival
> count **at the same resolution**, so that the waste becomes a function of `j`
> and can be **located** (onset `j*`) and **rated** (`D`, `S`, `Δ`) instead of
> merely totalled.
>
> Deleting gives a boolean. Pairing gives a curve. The curve is the instrument;
> where it turns is the result.

This is **narrower** than "everything is one question", and it is the version the
code supports: `n_j` is invariant under the success marks (§14.3), `Δ` moves while
survival is held fixed (§14.4), and the survival predicate itself is not unique
(§14.2).

---

## 15. Keeping both — and keeping the edges

> *Keep the transient and the recurrent structure alike, because the distinction
> between what disappears and what returns is itself information.*

A distinction is information only if it is not recoverable from either half. Two
negative results force the claim. Built in `both_structures.py`; suite
`test_both_structures.py`.

### 15.1 The recurrent core does not determine the transients

Two maps on five states with the **same** 3-cycle `0 → 1 → 2 → 0`:

| | transient edges | profile (depth → nodes) |
|---|---|---|
| `T1` | `3 → 0`, `4 → 0` | `{1: 2}` |
| `T2` | `3 → 4 → 0` | `{1: 1, 2: 1}` |

Same core, same transient **count** (2), different **arrangement**. Neither the
core nor the count recovers the shape.

### 15.2 The ledger counts do not determine the structure

Two tries built from four traces each:

| | traces | level-1 out-degrees |
|---|---|---|
| `A` | `(a,b) (a,c) (d,e) (d,f)` | `a` has 2, `d` has 2 |
| `B` | `(a,b) (a,c) (a,d) (e,f)` | `a` has 3, `e` has 1 |

$$n_j = (2,4), \quad L_j = (2,4) \qquad \text{for both.}$$

Their canonical (AHU) rooted-tree forms are

$$A = \texttt{((()())(()()))}, \qquad B = \texttt{((()()())(()))}$$

which are **not equal**, so the trees are not isomorphic. Every scalar PDI
reports is a level-size profile, and a level-size profile cannot see the
difference. **The information is in the edges.**

### 15.3 What this corrects, and what it does not

§14.4 said the original move is the **pairing** of a survival-free cost with a
survival count at the same resolution. That stands — it is why `n_j` is
survival-free (§14.3).

But a pairing of two level-size profiles is still a **summary**. It says *how
much* is transient at each resolution and never *how the transients are
arranged*. So §14.4 is the statement of what makes the ledger possible; §15 is
the statement of what the ledger leaves out.

The limitation is of the **summary**, not of the structure: PDI stores the trie
(nodes and children), so the edges are retained. The ledger is a projection of
it, and §15.2 shows that projection is not injective.

### 15.4 The statement

> **Keep both, and keep the edges** — because the distinction is information
> precisely where the counts are blind.

The transport work is the reproduction of §15.1: the recurrent core is a
permutation on its cycles (**earned**, §6.2) while the trees feeding it stay
many-to-one (§8). Those are the two halves. PDI's value is that it reports both,
instead of discarding the second the moment the first is found.
