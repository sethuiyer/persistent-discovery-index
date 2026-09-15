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
