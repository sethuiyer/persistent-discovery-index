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
| 8.1 | No injective transport loop exists in this family | **PROVED** (§18) — was empirical |
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
| 16.1 | PDI enforces witness-gated construction (`TowerViolation`, convergence status, `S_shallow`) | **verified** (§16.1) |
| 16.2 | PDI does **not** have canonicity; the finite-scale number is presentation-dependent and only quarantined | **computed, negative** (§16.2) |
| 16.3 | The five named “invariance-first” principles are **three** claims of different logical shape | **analysis** (§16.3) |
| 17.1 | Every warrant PDI states is dischargeable, except the asymptotic `bound` | **audited** (§17.1) |
| 17.2 | No finite prefix determines a limsup, so all three `bound` labels are falsifiable | **proved + exhibited** (§17.2) |
| 17.3 | The `bound` labels now carry their hypothesis | **fixed** (§17.3) |
| 19.1 | The Ihara/Bass zeta family does not separate the §15.2 pair: both `Z=1`, both Bass det `=1−u²` | **computed, negative** (§19.1) |
| 19.2 | Bass determinant of a forest `= (1−u²)^{#components}` — shape-blind | **computed** (§19.2) |
| 19.3 | Zeta separates `C3⊔C3` from `C6` (same degrees, same `(V,E)`) — sharp on cycles | **computed** (§19.3) |
| 19.4 | The twisted zeta is void on the current construction: `χ` is length-determined, and the transport has no non-trivial `π₁ → U(1)` | **computed, negative** (§19.6) |
| 19.5 | `γ ↦ T_γ|_R` is a monoid homomorphism but NOT a group representation: `R` is loop-dependent (O1), and the inverse axiom fails (§18) | **computed, negative** (§19.7) |

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

**N1. No injective loop.** Over 216 loops (`n = 10`, varying schedule, `tabu`,
`steps`), the induced map on the stable quotient was injective **0 times**.
Quotient sizes ranged 4–33. The collapse is therefore not an artefact of a badly
chosen schedule. **This is now a theorem, not an empirical negative** (§18): a
global optimum has `n` preimages under a single step, every leg is therefore
non-injective, and non-injectivity composes. The 216-loop search was answering a
question that a per-leg check settles outright.

**N2. Augmenting with tabu memory does not restore invertibility.** Transporting
`(x, tabu)` instead of `x`, the augmented map is still many-to-one, and the induced
map on the augmented stable quotient is still non-injective (6–22 blocks, with
2{,}284–18{,}652 collisions remaining — 2{,}284–2{,}292 over the 2{,}304-state
augmented space at tabu length 1, 18{,}632–18{,}652 over the 18{,}688-state space at
tabu length 2). The
memory projection was *a* source of collapse; removing it was not sufficient.
*Still empirical, but no longer unexplained*: Lemma A (§18.2) says `a` is an argmin
at `z^{e_a}` for **every** `a` when `z` is a global optimum, so the
collapse happens at the attractor — exactly where an augmented state has nothing
left to separate. Carrying the memory removes one source of collapse, not the
source. Suite: `test_invertibility.py`.

**N3. Branches and basins are the wrong fibre.** Neither the partition by nearest
optimum (2 blocks) nor by greedy-descent basin (94 blocks) is `T`-stable. The
correct fibre had to be constructed (§5), not guessed.

---

## 9. Open problems

**O1. Canonical fibre.** The stable quotient is loop-specific: different
`(tabu, steps)` yield 4, 12, 24, 40 blocks. Whether there is a schedule-independent
fibre within a suitable class of loops is open.

**O2. Injective transport.** ~~N1 is empirical. Either exhibit an injective loop,
or prove that the induced map on the stable quotient of this family is necessarily
non-injective.~~ **RESOLVED — the second branch, proved** in §18 (v0.18.0). The
obstruction is a *single step*: a global optimum has `n` preimages, so every leg is
non-injective and non-injectivity composes.

**O3. Sufficient augmentation.** N2 rules out tabu memory as sufficient. Whether
*some* finite augmentation makes the dynamics invertible is open — it is the same
question as whether the process has a reversible lift. §18 sharpens it: the
collapse is forced at the **global optima**, so any augmentation that works must
separate states the landscape pulls together *at the attractor*. Augmenting by
history alone does not, because the history is itself pushed to the attractor.

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

---

## 16. One principle, or three?

> *The invariance-first principle: build equivalence classes only modulo provable
> indistinguishability. Lindenbaum–Tarski, Hennessy–Milner, explicit coercion,
> "no experiment without protocol", and "make illegal states unrepresentable" are
> the same principle, and PDI instantiates all of them.*

Tested rather than agreed with, in `invariance_first.py`; suite
`test_invariance_first.py`. **They are not one principle.** They are three, with
different logical shapes, and PDI's standing on each is different:

| | shape | sources | PDI |
|---|---|---|---|
| **(a)** witness-gated construction | an axiom you enforce | Lindenbaum–Tarski **form**, explicit coercion, Minsky | **strong** |
| **(b)** canonicity | a property you hope for | Lindenbaum–Tarski **guarantee** | **absent** — row 9.1 open |
| **(c)** agreement of two equivalences | a theorem you prove or refute | Hennessy–Milner | **conditional** — §13 |

### 16.1 (a) The gate fires on the *witness*

`QuotientTower.validate` raises `TowerViolation` on a non-refining tower and
accepts a refining one. The check is on the *corpus* — the refinement law (1.1) —
not on the output. You cannot build the object without the proof. The same shape
appears three more times in the repo:

- `exponents()` carries `S_shallow`/`D_shallow`, so a value attained *inside* the
  horizon is not printed as a rate;
- `agent_profiler.asymptotic` carries a convergence status
  (`STABLE / TRENDING_UP / TRENDING_DOWN / UNRESOLVED / NONE`) and a bound
  (`exact / lower bound / upper bound`) rather than a bare number;
- `stopped_at` accompanies the exponents for the same reason.

This is the shape shared by Lindenbaum–Tarski's construction, the explicit-coercion
rule in Coq/Lean/Idris, and "make illegal states unrepresentable."

### 16.2 (b) Canonicity is absent, and the dependence is quarantined

The tower is an **input** (`pdi.py`: `tower: Optional[Any] = None`), not derived
from a provability relation. So the Lindenbaum–Tarski *guarantee* — that the
quotient is determined by the behaviour — is not available. Row 2.3 proves only
**cofinal** invariance; row 9.1 leaves canonicity **open** and records it as
**known to vary**.

Same traces, same success marks, resolution index shifted by one prepended symbol.
Both towers pass the gate.

| `j` | `L_j` (A) | `log₂L_j/j` | `L_j` (B) | `log₂L_j/j` |
|---|---|---|---|---|
| 1 | 2 | 1.00000 | 1 | 0.00000 |
| 2 | 4 | 1.00000 | 2 | 0.50000 |
| ⋮ | ⋮ | ⋮ | ⋮ | ⋮ |
| 8 | 256 | 1.00000 | 128 | 0.87500 |
| 9 | | | 256 | 0.88889 |

Finite-scale layer: `D_A = 1.000000` (`D_shallow=True`), `D_B = 0.888889`
(`D_shallow=False`). **Presentation-dependent: yes.**

Asymptotic layer: `A = 1.000000 STABLE exact`, `B = 0.888889 TRENDING_UP
lower bound`. The true limsup is `1` for both — dropping B's first level recovers
A — so B's bound is *correct* and A's estimate is *correct*.

**This is row 3.1 firing on a presentation shift.** The finite-window sup is not
the limsup; the asymptotic layer with its convergence status is the repo's
response to that. The cofinal-invariant object survives; the finite-scale number
does not, and is labelled.

> PDI does not **eliminate** presentation-dependence. It **quarantines** it. The
> principle instantiated here is not *"the quantity is invariant."* It is
> **"you may not assert an invariance you do not have — the representation must
> carry the status."** That is the explicit-coercion rule: the claim is not
> forbidden, it must come with its witness.

### 16.3 (c) Agreement is conditional

Hennessy–Milner is an *agreement theorem* between two independently defined
equivalences — bisimilarity (structural) and modal indistinguishability
(observational). PDI's one instance of this shape is §13: `Ω = 0` exactly when the
refinement axis is `T`-invariant, and `Ω ≠ 0` on the inclusion axis. So PDI has
one instance and one counterexample, which is what a theorem of this shape
licenses.

### 16.4 The honest form of the claim

PDI **enforces (a) everywhere it can** — `TowerViolation` on the refinement law, a
convergence status on every asymptotic number, `S_shallow`/`D_shallow` so a
non-rate is never printed as a rate.

PDI **does not have (b)**, and says so in row 9.1 instead of asserting it. **That
row is the principle applied to the ledger itself** — the deepest instantiation in
the repo is not an object that satisfies the principle but a ledger entry that
records its absence.

PDI has **one instance of (c)**, and one counterexample.

---

## 17. Warrant audit — "proof-aware observability system"

> *So this is a proof-aware observability system.*

A proof-aware system states warrants, and every warrant it states is
**dischargeable** — either enforced at construction, or a fact about the data in
hand. The audit asks exactly that of every warrant PDI states. Built in
`proof_awareness.py`; suite `test_proof_awareness.py`.

### 17.1 The audit

| warrant | claim it makes | how it is backed | verdict |
|---|---|---|---|
| `TowerViolation` | refinement law (1.1) holds on the corpus | enforced at construction | **discharged** |
| `S_shallow` / `D_shallow` | the sup was attained *inside* the horizon | fact about the observation | **discharged** |
| convergence status | the shape of the observed tail | fact about the observation | **discharged** |
| `bound` | a bound on the **unobserved** tail | claim about data not in hand | **NOT DISCHARGED** |

Everything holds except the last. The status field is honest by construction; the
`bound` field was a claim about a tail that had not been observed.

### 17.2 No finite prefix bounds a limsup

Since `limsup = inf_m sup_{j≥m} s_j`, any observation is consistent with
continuations whose limsup lies anywhere in `[0, M₁]`. All three labels are
therefore falsifiable, and each is falsified by exhibiting the continuation:

| status | observed tail | reported value | continuation | true limsup | violated |
|---|---|---|---|---|---|
| `TRENDING_UP` | `0.1 0.2 0.3 0.4` | `0.400000` | `1/j` | `0.002506` | **yes** |
| `TRENDING_DOWN` | `0.4 0.3 0.2 0.1` | `0.400000` | `9, 9, …` | `9.000000` | **yes** |
| `STABLE` | `0.5 ×4` | `0.500000` | `9, 9, …` | `9.000000` | **yes** |

This is not a coding error. It is a theorem: **the observation does not determine
the extension**, which is why `limsup([1, 1/2, …, 1/49]) = 1/49` while the same
prefix extended with zeros has limsup `0`.

### 17.3 The fix: the labels carry their hypothesis

```
'exact'        ->  'window-exact (tail flat so far)'
'lower bound'  ->  'lower bound IF the tail stays monotone'
'upper bound'  ->  'upper bound IF the tail stays monotone'
'unknown'      ->  'no bound claimed'
```

This is the same move as `S_shallow`: **do not forbid the number, attach the
condition under which it means what it says.** The estimate is still reported —
it is useful — but it no longer uses the grammar of a proof for something that is
a heuristic.

### 17.4 Verdict

PDI is a **warrant-carrying observability system**, and it is proof-aware in every
place where a proof obligation *can* be discharged at construction. The asymptotic
`bound` was the single point where the grammar outran the warrant. It is now
labelled rather than asserted, which closes the gap the label "proof-aware"
opened.

---

## 18. O2 resolved — irreversibility is structural

> *O2 should now be: find the collision mechanism.*

**Result.** In this family, **no transport loop is injective**, and the obstruction
is a *single step*. Built in `o2_theorem.py` and `collision_mechanism.py`; suites
`test_o2_theorem.py` and `test_collision_mechanism.py`. This closes the negative
branch of O2, and retires the last empirical negative in the ledger (§8.1).

### 18.1 Setup

The transport is a **composition of memoryless legs**. `Searcher.run(x, lam, steps)`
resets the tabu list at the *start of every call*, and the loop driver calls it once
per leg:

$$T = f_k \circ \cdots \circ f_1, \qquad f_i = \mathrm{run}(\cdot,\lambda_i,\text{steps})$$

The atomic step flips exactly one bit,

$$g(x) = x \oplus e_{v(x)}, \qquad
v(x) = \operatorname*{argmin}_v \bigl(\delta(x,v),\; |v-\lambda(n-1)|\bigr)$$

where `best_flip` minimises `δ` **without** requiring `δ < 0` — a min-conflicts
step, not gradient descent.

### 18.2 The three steps

**Composition lemma.** `T` injective ⟹ `f₁` injective. If `f₁(x) = f₁(y)` then
`T(x) = T(y)`; injectivity forces `x = y`. So *a non-injective first leg kills every
schedule built on it*, and the loop search was the wrong search.

**Lemma A (the optimum pulls its own perturbations back).** Let `z` be a **global**
optimum. For all `a, b`,

$$\delta(z^{e_a}, b) \;=\; E(z^{e_a e_b}) - E(z^{e_a}) \;\ge\; E(z) - E(z^{e_a})
\;=\; \delta(z^{e_a}, a)$$

because `E(z)` is the global minimum. So `a` is **always** an argmin at `z^{e_a}`:
undoing a perturbation of an optimum is never worse than any alternative.
Verified on **8096/8096** triples.

**Lemma B + Theorem.** Let `A_a = argmin_b δ(z^{e_a}, b) = {b : z^{e_a e_b} optimal}`
and `d₂(z) = #{optimA z' ≠ z : d_H(z,z') = 2}`. Then `a ∈ A_a`, and `|A_a| > 1` only
for bits `a` involved in a 2-bit relation to another optimum — at most `2 d₂(z)` such
bits. Every remaining bit wins its tie-break outright, so

$$\boxed{\;\bigl|g^{-1}(z)\bigr| \;=\; |S(z)| \;=\;
\bigl|\{a : v(z^{e_a}) = a\}\bigr| \;\ge\; n - 2\,d_2(z)\;}$$

Verified on **400/400** (instance, λ, optimum) cases, with the bound **tight**
(slack `0` observed at `n = 8`, `d₂ = 0`).

**Corollary.** For `n ≥ 2 d₂(z) + 2`, `|g^{-1}(z)| ≥ 2`: the one-step map is
**not injective**.

### 18.3 The chain

`run(·, λ, steps)` has `g` as its **first** step, because the tabu list is empty
there. Hence `run = h ∘ g`, and `h ∘ g` is non-injective whenever `g` is. Combined
with the composition lemma:

> **No schedule of these legs is injective.** Not for any length, not for any
> choice of `λ`, not for any tabu length.

This also explains an observation the census produced but did not predict: the
one-step image size is **identical across tabu lengths** (`2…8` all give `96` of
`256`). The first step is tabu-free, so the tabu length cannot affect it.

### 18.4 The mechanism

`|S(z)|` is monotone in energy *in aggregate* and maximal at the optima:

| `E(z)` | 0 (opt) | 2 | 3 | 4 | 5 | 6 | … | 11 | 12 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean `\|S(z)\|` | **8.000** | 8.000 | 5.500 | 3.000 | 3.500 | 1.739 | … | 0.000 | 0.000 | 0.000 |

Concordance `> 0.9` but **not** `1.0` — the ordering is *concentrated*, not
pointwise (§17 discipline: the claim is stated no more strongly than the data).

> The map collapses hardest exactly where the search is trying to go. **You cannot
> have a contraction without a collision.**

### 18.5 What this settles

The many-to-one collapse is **not** an implementation accident, and **not** a
failure of the loop search. It is forced by the energy landscape having a global
optimum. The conjecture's premise is now proved for this family:

$$F = \underbrace{\text{transient trees}}_{\text{information lost at the attractor}}
\;\longrightarrow\;
\underbrace{R}_{\text{recurrent core}}_{\text{invertibility survives here}}$$

and `R` is therefore **not** merely where invertibility happened to be recovered.
It is the **maximal place where invertibility can survive**.

### 18.6 Residual hypothesis, stated plainly

The theorem is proved for this search family (min-conflicts with argmin-`δ` flips).
The corollary needs `n ≥ 2 d₂(z) + 2` — satisfied with room to spare by every
instance tested (`n ≥ 8`, `d₂ ≤ 1`), but it *is* a condition, and instances with
many optima clustered at Hamming distance 2 from each other are the boundary case.

---

## 19. Zeta functions and the §15 witness — a negative

> *The ledger is blind to the edges. Use an edge-sensitive invariant: the Ihara
> zeta.*

§15.2 exhibits two traces with identical ledgers `(n_j, L_j)` and non-isomorphic
discovery structure. The proposal is to separate them with the Ihara zeta

$$Z_G(u) = \prod_{[P]} (1 - u^{\ell(P)})^{-1},$$

over primitive non-backtracking closed cycles, via the Ihara–Bass closed form

$$Z_G(u)^{-1} = (1-u^2)^{|E|-|V|} \det\!\left(I - uA + u^2(D-I)\right).$$

Built and computed in `zeta_separation.py`; suite `test_ihara_separation.py`.

### 19.1 The answer is no, and it is structural

**The §15.2 pair is a tree.** A tree has no non-backtracking closed walk at all,
so the Euler product is empty and

$$Z_A(u) = Z_B(u) = 1, \qquad \det(I-uA+u^2(D-I)) = 1 - u^2 \ \text{ for both.}$$

Verified in the suite: `#prime cycles = 0` for both, `Z^{-1} = 1` for both, Bass
determinant `= 1-u^2` for both — **no separation, on the very witness §15 uses.**

The mechanism, stated plainly: **zeta listens to edges only through cycles.**
"Edges" and "cycles" are not the same information. §15's witness has edges and no
cycles, so an invariant that reads cycles reads nothing.

### 19.2 The Bass determinant of a forest is shape-blind

Computed over every forest tested (paths, stars, both tries, and one- and
two-component forests):

$$\det\!\left(I-uA+u^2(D-I)\right) = (1-u^2)^{c}, \qquad c = \#\text{components}.$$

On the acyclic part the Bass determinant is a function of the **number of
components alone** — it carries *no* tree-shape information. This is a computed
law over the tested range, not a proof; the range is `zeta_separation.FORESTS`.

### 19.3 Where zeta belongs — the recurrent core

Zeta is not vacuous; it is *aimed at the wrong part of the spine*. Positive
control, in the suite: `C3 ⊔ C3` and `C6` have the same degree sequence (all 2)
and the same `(|V|,|E|) = (6,6)`, and

$$Z_{C_3\sqcup C_3}(u)^{-1} = (1-u^3)^4 \;\neq\; (1-u^6)^2 = Z_{C_6}(u)^{-1}.$$

Zeta separates them. It is **blind to acyclic structure and sharp on cyclic
structure.** By §6 the recurrent core `R` is the union of cycles and the transient
remainder `F\setminus R` is trees, so

$$Z \text{ is non-trivial exactly on } R, \text{ and provably empty on } F\setminus R.$$

The ledger and the zeta family are therefore **complements, not rivals**:

| invariant | sees | blind to |
|---|---|---|
| ledger `(n_j, L_j)` | levels | arrangement (§15.2) |
| zeta `Z_G(u)` | cycles | acyclic structure (§19.1) |
| twisted zeta `Z_{G,χ}` | cycles **plus edge gains** | needs a gain PDI does not have (§19.6) |
| characteristic polynomial | some shape | complete? no — cospectral trees exist |
| AHU canonical form | rooted-tree shape, completely | — |

What separates §15.2 today is the last row (already used in §15.2), and the char
poly for this pair. Not a zeta.

### 19.4 A caution about the analogy

Ihara's standard reduction strips degree-1 vertices to reach the **2-core**; §6
splits a functional graph into a **recurrent core** and transient trees. These are
different constructions on different objects — a graph leaf-pruning versus the
union of cycles of a map `T`. The word "core" is shared; the construction is not.
Treat the resemblance as an analogy to test, not an identification — the same
caution §12 applies to "persistent".

### 19.5 The twisted zeta — the same answer, one level up

A twisted product

$$Z_{G,\chi}(u) = \prod_{[P]} \left(1 - \chi(P)\,u^{\ell(P)}\right)^{-1}$$

has content **iff `χ` does not factor through the cycle length.** If `χ(P) =
f(\ell(P))` then the product is a function of the prime-cycle length multiset
$(m_\ell)$, which `Z_G` already determines — so it separates nothing new. This
is a proof, not an estimate.

The criterion is therefore operational: **`χ` must not be constant on prime
cycles of the same length.** Computed in `zeta_separation.py` panel 5 on
`C3 ⊔ C3`, with a `{±1}` edge gain that inverts one triangle:

| object | `Z^{-1}` |
|---|---|
| bare | `(1-u³)⁴` |
| length-`χ`, `f(3)=+1` | `(1-u³)⁴` |
| length-`χ`, `f(3)=-1` | `(1+u³)⁴` |
| **edge gain**, mixed | `(1-u³)²(1+u³)²` |

`χ` takes two values on length-3 cycles, and the mixed product is outside the
reach of any constant-per-length `χ` — so a gain *is* read, and a length-character
is not. Pinned in `test_ihara_separation.py`.

**PDI has no such gain.** Two readings of `χ`, both void:

1. **`χ` from §7.** It is built on `C_L ↪ F_p^×`, i.e. through the cycle
   *order*, hence through `ℓ(P)`. And `prime_holonomy.character()` is called
   exactly once in the whole repo, on a hand-made residual (`h = 2³`) — never on
   a trajectory. So it is length-determined, and the criterion fails.
2. **`χ(P)` = transport holonomy around `P`.** On `R`, `T|_R` is a permutation
   (§6.2): traversing a cycle returns *exactly*, so `χ(P) = id`. Across loops it
   is not even a homomorphism — `test_transport.py` asserts `rev ≠ inv` and
   `sq ≠ sq`. Not a representation, so no character exists.

### 19.6 What this settles, and the routing law

The twisted zeta is **not an independent fourth arrow.** It is §8 in new clothes:
it needs a non-trivial representation `π₁ → U(1)`, i.e. a genuine monodromy, and
§8 found state drift instead. It inherits that negative — and inherits §18,
because the failure of reversibility is the same irreversibility.

The durable result of §19 is a **routing law**, not an invariant:

$$\text{transient arrangement} \to \text{edge/tree invariants (AHU, zeta deaf)}
\qquad
\text{recurrent arrangement} \to \text{cycle invariants (}Z_G\text{, deaf to trees)}$$

Every projection needs its own blind-spot statement, and "keep the edges" does
not mean every edge-derived invariant preserves what the ledger lost: projecting
`G → {primitive cycles}` deliberately destroys the forest.

### 19.7 Core monodromy — answered, and the strand closes

The §19.7 open edge was:

> **Does `γ ↦ T_γ|_R` define a homomorphism `π₁(presentation space) → Sym(R)`?**

Built in `core_monodromy.py`; suite `test_core_monodromy.py`. Over `n=10`,
`tabu ∈ {2,3}`, `steps=8`, and the six schedules listed in `core_monodromy.LOOPS`:

1. **Composition holds.** `T_{γ₁γ₂} = T_{γ₂} ∘ T_{γ₁}` exactly, on every state.
   The assignment is a **monoid homomorphism** from the free monoid of schedules.
   That half is earned.
2. **The target `R` is not well-defined — this is O1.** `|R|` takes the values
   `6, 8, 10, 12, 16` across the six loops, with different cycle structures, and
   the intersection of all six cores is **2 states out of 1024**. There is no
   single `R` for `π₁` to act on, so the map is not even *well-typed*. The
   recurrent core inherits precisely the presentation-dependence O1 records for
   the stable quotient.
3. **The inverse axiom fails — this is §18.** `T_{γ^{-1}} ∘ T_γ ≠ id` on the
   core, and `T_{γ^{-1}}` does not even map `core(γ)` into itself.
4. **On the common quotient** stable under all six loops at once — a genuine
   quotient, `332` blocks of `1024` at `tabu=2` and `369` at `tabu=3` — **every**
   induced map is non-injective, and the cores still differ per loop.

**Verdict (computed, negative).** `γ ↦ T_γ|_R` is a monoid homomorphism that is
not a group representation: no loop-independent `R` (O1), and no inverse where it
is typed (§18). Hence no character on `π₁` — so there is nothing for a twisted
zeta to twist by. This is the same conclusion as §19.5–19.6, reached from the
transport side rather than the zeta side.

The zeta strand therefore closes on the repository's **central open problem**, not
on a local defect: transport monodromy needs a *canonical* core, and canonicity is
exactly what O1 says PDI does not have. The remaining honest statement is the
routing law of §19.6 plus one open question, unchanged and now sharply localised:

> **O1 is the whole obstruction.** Any future transport/character/phase
> programme — twisted zeta, Berry phase, holonomy — is blocked until the stable
> fibre is presentation-independent. §19 adds no new open problem; it removes a
> candidate and points the arrow back at O1.
