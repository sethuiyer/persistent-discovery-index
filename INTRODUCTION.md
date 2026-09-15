# INTRODUCTION.md — orientation for an agent working in this repository

You are an agent that has just landed in this repo. This file tells you what it
is, what governs every change you make, where to look, and which mistakes have
already been made so you don't repeat them.

Read this file, then `SPINE.md` §0 (the ledger). You will rarely need anything else
to start.

---

## 1. What this is, in one paragraph

PDI (Persistent Discovery Index) is an observability library for AI agents. It
ingests agent traces, builds a **resolution tower** over behaviour — a refining
chain of behavioural quotients — and keeps **two ledgers** at every level: `n_j`,
the number of distinctions the presentation makes, and `L_j`, the number that
survive. The difference is the cost of discovery, localised to the resolution where
it appears. Everything is stdlib-only, MIT, and self-checking.

## 2. THE ONE RULE

**Every claim carries a warrant, and no claim is stronger than its warrant.**

This is not a style preference. It is the design rule the whole repository was
built around, and a change that violates it is a bug even if all tests pass.

Concretely, when you write or change anything:

- A number that could be a rate must say whether it **is** a rate
  (`D_shallow`, `stopped_at`, convergence status).
- A negative result states its **search bounds**. Write *"none among the 216
  tested"*, never *"none exists"* — unless you have a proof.
- A quantity that depends on the presentation must **say so**. `Δ` is
  presentation-dependent, `D` is cofinal-invariant. Both are true and both matter.
- Labels carry their hypotheses. `"lower bound IF the tail stays monotone"`, not
  `"lower bound"`. See §17.
- The status vocabulary in `SPINE.md` is fixed:
  `proved` / `computed` / `negative` / `open` / `conjecture` / `standard` / `cited`.

> If you find yourself wanting to say "obviously" or "clearly", stop. Either it is
> proved, in which case cite the proof, or it is not.

## 3. Where to look — routing table

| Your question | Read |
|---|---|
| What is claimed, and how strongly? | `SPINE.md` §0 ledger (the index) |
| What is the whole mathematical chain? | `SPINE.md` §1–§11 |
| Where did a reference come from? | `SPINE.md` §12 |
| Is quantity X canonical? | `SPINE.md` §16 (canonicity is **absent**, quarantined) |
| Why is search irreversible? | `SPINE.md` §18 (proved) |
| Who is this for / how is it sold? | `PRODUCT_README.md` (strategy, not warrant) |
| How do I pitch it to non-tech / sales? | `PRODUCT_BREAKDOWN.md` (battlecard, ROI, non-tech) |
| How do I use it? | `README.md` |
| What does a real trace look like? | `fixtures/` |

### The code, by layer

```
LEAF MODULES (stdlib only — safe to change, nothing depends on your edits
              except by contract)

  pdi.py                the index, ledgers, exponents, statuses
  quotient_tower.py     the refinement law + TowerViolation
  transport.py          the stateful min-conflicts searcher
  adapters.py           trace dataclasses, pi-session loader
  sudoku.py             the worked stress case
  survival_commutation.py   two survival operators, deliberately standalone

MIDDLE

  agent_profiler.py     <-- pdi            profile, asymptotic layer, statuses
  ingest.py             <-- adapters       7 trace-format loaders
  stable_quotient.py    <-- transport      partition refinement to T-stability
  both_structures.py    <-- pdi            what the ledger cannot distinguish
  one_question.py       <-- pdi            is n_j a survival quantity (no)
  proof_awareness.py    <-- agent_profiler the warrant audit
  invariance_first.py   <-- pdi, quotient_tower
  collision_mechanism.py <-- transport     O2: the collision characterisation
  o2_theorem.py         <-- transport      O2: the proof
  invertibility.py      <-- stable_quotient, transport   Q1/Q2 attacks

ENTRY POINTS (demos, run but not imported)

  demo.py  demo_agents.py  demo_tower.py  demo_sudoku.py
  pdi_profile.py  diagnose_agents.py
```

Nothing in this repo has a third-party dependency. If you add one, you have broken
the zero-dependency property the README and CI both assert.

## 4. How to verify — and what "green" means

```bash
for f in test_*.py toys.py; do python3 "$f" || echo "FAIL $f"; done
python3 test_repo_consistency.py     # docs vs code vs each other
```

21 suites, all exit nonzero on failure. CI runs them on Python 3.10 and 3.12.

**Green means the claims in the ledger are still backed.** It does not mean the
code is correct in any broader sense — most of this repo has no external oracle.

If you add a suite, `test_repo_consistency.py` will notice if you forget to update
a count in the docs. It fails loudly. That is deliberate.

## 5. Load-bearing invariants — do not break these

1. **The refinement law.** `Q_{j+1}(x) = Q_{j+1}(y) ⟹ Q_j(x) = Q_j(y)`.
   Enforced by `QuotientTower.validate` / `validate_pairs`, which raise
   `TowerViolation`. Never weaken this to a warning.
2. **`n_j` is exactly `|H/∼_j|`.** It is a count, not an estimate.
3. **`L_j` is non-decreasing at a fixed horizon.** There is a test.
4. **`pdi.py` imports nothing project-local.** It is the base of the graph.
5. **No bare bound labels.** `"exact"`, `"lower bound"`, `"upper bound"`,
   `"unknown"` are all forbidden strings — they claim more than a finite prefix can
   support (§17). There is a test.
6. **`n_j` is survival-free.** It must stay independent of any success predicate.
   If you make it depend on `live`, you have broken §14.
7. **The ledger in `SPINE.md` is the source of truth** for claim status. If you
   change a claim's strength, change its row.

## 6. Traps that have actually bitten

These are real, each cost time, and each is a place where the obvious reading of
the code is wrong.

**`live=False` does not mean "dead".** In `PDI.insert`, `live` is an *explicit
override*. The default rule is *reaches the horizon*. To use outcome-based
survival, call `finalize_explicit()`.

**`recompute_statuses()` overwrites `mark_live()`.** It reclassifies everything by
the horizon rule. If you interleave them, you will silently lose your explicit
marks. Use one mode or the other.

**Coaccessibility makes whole chains live.** A node with any live descendant is
live. So if you insert all `2^H` traces, `L_j == n_j` always, and a test that
"varies the success predicate" varies nothing. To get `L_j < n_j` you need a branch
with **no** live descendant.

**`Searcher.run` resets the tabu list at the start of every call.** `run_state`
carries it. This makes the transport a composition of *memoryless legs*, which is
the whole basis of §18. It also means one-step behaviour is identical across tabu
lengths — that invariance is the proof's outline, not a coincidence.

**A finite-window sup is not a limsup.** `limsup = inf_m sup_{j≥m} s_j`, so no
finite prefix determines it. Never print a finite sup as a rate.

**`_looks_like_a_run` gates whole-object JSON parsing.** If you add a format,
add its container key to that set or pretty-printed files silently yield **zero
runs with no error**.

**Numbers in prose drift.** This has happened four times (suite count twice, loop
count, LOC). Do not hand-maintain a count. `test_repo_consistency.py` checks it.

**Empirical negatives are provisional.** `SPINE.md` row 8.1 said "0 injective among
216, empirical" for several versions. It is now **proved** (§18). Before accepting
an empirical negative, ask what the mechanism would have to be.

## 7. How to add a claim

1. **Establish it.** Prove it, compute it exhaustively, or verify it over a stated
   range. "I ran it and it looked right" is not a warrant.
2. **Label it** in the `SPINE.md` ledger with one of the fixed statuses, and write
   the section.
3. **Test it.** A file that prints PASS/FAIL but never calls `sys.exit(1)` cannot
   fail anything. Every suite exits nonzero.
4. **If it is a negative,** state the bounds in the claim itself.
5. **Run `test_repo_consistency.py`** and fix whatever it flags.

If a claim turns out to be wrong, **correct it in place and say so in the commit
message.** Every version of this repo that fixed an overclaim left the correction
visible. That is the house style, not an accident.

## 8. Already settled — do not redo

| Claim | Status |
|---|---|
| The tower law, the two ledgers, `Δ = S − D` | §1–§3 |
| Transport exists but is state drift, not monodromy | §8 |
| The stable quotient exists and is computable | §5 |
| `T` on the recurrent core is a permutation | §6 |
| The two survival operators commute on the quotient axis | §13 |
| `Ω` is **identically zero** on PDI's own axis → **not** a PDI quantity | §13.4 |
| `n_j` is survival-free; `Δ` moves while survival is fixed | §14 |
| The ledger does **not** determine the structure (non-isomorphic trees, equal ledgers) | §15 |
| Canonicity is **absent**; the dependence is quarantined, not eliminated | §16 |
| No finite prefix bounds a limsup; bound labels carry hypotheses | §17 |
| **No injective transport loop exists** — irreversibility is structural | §18 |
| The Ihara/Bass zeta family is blind on the §15 pair and sharp on the recurrent core | §19 |

## 9. Open — where the work is

| | Status |
|---|---|
| **O1 — canonical fibre.** Is the stable quotient presentation-independent? | **open**, known to vary; this *is* the Lindenbaum–Tarski gap |
| **O3 — sufficient augmentation.** Does any finite augmentation give a reversible lift? | **open**; §18 says it must separate states *at the attractor* |
| **§10 conjecture.** A functor from tower live/transient to transport recurrent/transient | **conjecture** |
| **Controlled corpus.** Repeated tasks per agent | the blocker for every empirical claim |
| **Twisted zeta.** Does `∏(1−χ(P)u^{ℓ(P)})^{-1}` separate what bare zeta cannot? | **closed, negative** — needs a non-length-determined `χ`, i.e. a non-trivial `π₁→U(1)`; PDI's transport has none (§19.6) |
| **Monodromy on the core.** Is `γ ↦ T_γ|_R` a homomorphism `π₁ → Sym(R)`? | **closed, negative** — it is a monoid homomorphism, not a group representation: `R` is loop-dependent (O1) and the inverse axiom fails (§18); see §19.7 |
| ~~`invertibility.py` has no test~~ | **closed (v0.21.0)** — `test_invertibility.py` pins Q1 (0 of 216, exact grid) and the §8.2 Q2 numbers |

## 10. Two things about the repository's character

**Negative results are outputs, not failures.** `UNRESOLVED`, presentation-
dependence, non-injective ledgers, "these trees share a ledger but aren't
isomorphic" — each is a *successful* result. The system prevented a stronger
statement than the evidence allowed. Do not "fix" these by weakening them into
something more comfortable.

**Do not make a claim narrower either.** Both over- and under-claiming have been
corrected here. If a result is proved, state it proved.
