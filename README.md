# Persistent Discovery Index (PDI)

<p align="center"><img src="logo2.png" alt="Persistent Discovery Index" width="240"></p>

**A microscope for agent behaviour. It shows where useful discovery ends and
unnecessary exploration begins — and at which behavioural resolution it happens.**

> **Video deep dive — the math behind PDI, and why modern agent benchmarks
> lie:** [The Hidden Cost of AI Discovery](https://www.youtube.com/watch?v=tkPmvU6x_bc)

Two people try to find the exit from a maze. A tries 20 paths. B tries 2,000 and
finds the same exit.

Normal evaluation says: *both succeeded.* PDI says: *same result, wildly different
discovery cost — and here is the level of behavioural detail at which B's search
went noisy.*

```text
explored        1,000 behaviours
persistent        100 of them led somewhere useful
transient         900 did not

most tools throw the 900 away.
PDI keeps them, because they are what tells you about the agent —
even though they tell you almost nothing about the solution.
```

## Two numbers, never merged

| ledger | symbol | meaning |
|---|---|---|
| **exploration** | `n_j` | everything the agent tried, at resolution `j` |
| **persistent** | `L_j` | what actually led somewhere useful |

Every structure that exists today conflates these. DFA minimisation trims the
transient. Sofic-shift analysis keeps the essential part. Bisimulation discards
non-bisimilar branches. Caches drop the misses.

**PDI keeps both**, because the ratio between them is the measurement.

## Run it on your agent in five minutes

```bash
python3 pdi_profile.py traces/                    # autodetect format
python3 pdi_profile.py run.jsonl --format openai  # force a format
python3 pdi_profile.py traces/ --group-by model   # compare agents
python3 pdi_profile.py --demo                     # synthetic, no data needed
```

No configuration, no framework dependency, no service. Point it at JSONL.

## One ingest layer, many frameworks

PDI does not care which framework produced a trace. It needs three things per run:
the ordered tool calls, their arguments, and the terminal outcome. Everything else
is decoration.

| format | source | detection |
|---|---|---|
| `pi` | pi agent session JSONL | `type: session/message` events |
| `openai` | OpenAI-style chat with `tool_calls` | `messages` array or `role` keys |
| `langsmith` | LangSmith / LangGraph run exports | `run_type` / `trace_id` |
| `canonical` | anything you write | `steps` array |

`ingest.detect_format()` sniffs the file; `load_any()` dispatches. Add a framework
by writing one loader that returns `list[Run]`.

### The canonical format — the whole contract

One JSON object per line:

```json
{"model": "my-agent", "project": "repo", "prompt": "fix the failing test",
 "outcome": "stop",
 "steps": [{"tool": "read",  "args": {"path": "a.py"}, "error": null},
           {"tool": "edit",  "args": {"path": "a.py"}, "error": null},
           {"tool": "bash",  "args": {"command": "pytest"}, "error": null}]}
```

`outcome` is the terminal state: `"stop"` means the run finished on its own terms
and counts as a success. Anything else (`error`, `aborted`, `length`, `toolUse`)
does not. Map your framework's success notion onto `"stop"`.

`pdi_profile.py --dump-canonical out.jsonl` writes this back out, so PDI is also a
normaliser: **any agent trace in, one behavioural-run representation out.**

## The zoom levels

An agent's behaviour looks different depending on how closely you look:

```text
Trace A:  search → read → answer
Trace B:  search → read → search → answer
```

At `Q1` they are identical. At `Q3` they are not. That is what the tower encodes:

```text
Q1  terminal outcome              did it succeed?
Q2  + tool-family multiset        what kinds of tools
Q3  + tool-family sequence        in what order
Q4  + per-step error classes      where it failed
Q5  + normalised argument classes what it pointed them at
Q6  + full normalised trace       exactly what happened
```

Each level explicitly contains the previous one, so the **refinement law**

```
Q_{j+1}(h) = Q_{j+1}(h')   =>   Q_j(h) = Q_j(h')
```

holds by construction — and is *checked*, not assumed (`QuotientTower.validate()`
raises `TowerViolation`). With a tower, `n_j = |H / ~_j|` **exactly**: the number
of behavioural classes at resolution `j`.

## The diagnostic

```text
             FULL     LIVE
Q1              2        2
Q2             12       10
Q3            200       40
Q4          1,500       55
Q5         10,000       60
```

Useful behavioural diversity barely grows: `10 → 40 → 55 → 60`.
Total behaviour explodes: `12 → 200 → 1,500 → 10,000`.

**After Q3 this agent is manufacturing complexity rather than discovering useful
new behaviour** — and Q3 has a meaning (`+ tool sequence`), so you learn *where*
it went noisy, not just that it did.

The tool reports that as **class inflation against a reference**:

```text
class inflation relative to 'reference'   (n_j / n_j_reference)
agent                  Q1          Q2          Q3          Q4          Q5          Q6
reference           1.00x       1.00x       1.00x       1.00x       1.00x       1.00x
candidate           1.00x       1.09x       5.89x       7.35x       7.35x       7.35x

distinction onset: at resolution 3 (Q3 + tool sequence)
```

Level 1 is terminal outcome, so an onset there just means success rates differ.
PDI reports a separate **behavioural onset** that ignores that level.

## Same geometry, different discovery cost

Five strategies, one task (find every shortest path on a 6×6 grid):

```
agent                   D         S     Delta    waste  STOP at
shortest_only    0.850919  0.850919  0.000000     0.0%        -
admissible       0.850919  0.850919  0.000000     0.0%        -
slack_1          0.850919  0.850919  0.000000     0.0%        -
slack_2          0.850919  1.010933  0.160013    15.8%        -
unpruned         0.850919  1.079279  0.228360    21.2%       11
```

Identical persistent structure, one clean ordering of discovery overhead. The task
supplies the geometry; the algorithm supplies the waste. **Presentation dependence
of `Delta` is the point** — it is what makes it comparable across algorithms.

## Worked example: Sudoku

Sudoku is the purest case in this repo: **the solution is unique**, so the
persistent ledger is one thin path per puzzle and everything else the solver does
is transient. Every number below is a statement about waste. Three strategies, the
same two puzzles:

```
strategy            total nodes   backtracks
first/asc                23,232       23,231
first/random              3,992        3,991
mrv/asc                     169           63      <- 137x less than first/asc
```

**Where the nodes are** — share of all visits, by depth band:

```
strategy            total        d1-10      d11-20      d21-30      d31-40      d41-53
first/asc          23,232         5.8%        8.6%       76.2%        9.2%        0.2%
first/random        3,992        15.7%       10.0%       60.7%       12.5%        1.2%
mrv/asc               169        16.2%       16.8%       28.1%       24.0%       15.0%
```

**76.2% of `first/asc`'s entire search sits in depths 21–30.** That band is where
it stops deducing and starts guessing. MRV never enters that regime — its visits
are spread evenly across the whole depth range, because it never has a cell with
many candidates to guess from.

**Inflation against MRV, at selected depths:**

```
strategy              d1      d10      d15      d20      d25      d27      d30
first/asc          3.00x  142.00x   40.00x  260.00x  492.75x  627.00x   89.40x
first/random       1.50x   56.33x    8.50x   49.67x   72.00x   74.20x   17.40x
mrv/asc            1.00x    1.00x    1.00x    1.00x    1.00x    1.00x    1.00x
```

At depth 27 the naive solver is generating **627×** the search structure of MRV for
the same two solutions. `test_sudoku.py` also verifies that PDI's `n_j` equals the
solver's own per-depth node counts **exactly** at every depth, so the profile is
not an artefact of the profiling.

### And the honest caveat, which this example makes unavoidable

`D` and `S` both take their sup at **depth 1** here. They are reporting how many
values were tried in the *first cell* — not how large the search became. They happen
to order the strategies correctly, by correlation with shallow branching, but they
do not measure the thing anyone cares about. The per-depth profile and the totals
do.

**This is the open question in its most concrete form yet: at this scale the
asymptotic summaries are the wrong instrument and the finite-scale diagnostics are
the right one.** Run it yourself:

```bash
python3 demo_sudoku.py       # the tables above
python3 test_sudoku.py       # 20 checks, incl. PDI n_j == solver node counts
```

## Does discovery have holonomy? (a negative result)

PDI proved that `Delta` is **presentation**-dependent. That is path dependence in
the weak sense — *which* presentation. Holonomy needs the stronger thing:
dependence on the **route**, so that a closed loop in parameter space returns the
external parameter but not the internal state.

Three requirements, and the Sudoku probe settled two of them:

| requirement | meaning | status |
|---|---|---|
| **degeneracy** | more than one optimum, so "which branch" is a real question | ✅ exists |
| **walls** | a parameter family where behaviour changes | ✅ exists (λ ∈ 0.5–0.75) |
| **history** | a stateful process, `x_{t+1} = F(x_t, λ_t)` | ❌ absent from a memoryless solver |

A memoryless solver has `x = f(λ)`, so **every closed schedule returns `f(λ₀)` by
construction** — cross ten walls, still no residual. `transport.py` supplies the
missing third ingredient.

**Setup.** Max-Cut on n=12 with exactly **two** optimal cuts (found by enumeration
over all 4096 configurations), a deterministic min-conflicts search with a **tabu
list** as memory and a λ-controlled tie-break as the presentation, and the loop
`λ: 0.10 → 0.50 → 0.90 → 0.10`.

### What happened

**Non-identity transport exists.** The loop applied to representatives sometimes
maps `A → B` and `B → A` — the state genuinely does not return.

**But it is not a monodromy**, and this is decisive:

```
  tabu steps           perm  bij    id  rev=inv  sq=sq  ord  branch-determined?
     2    16       A->B B->A  True False    False  False    2  NO A:{A,B} B:{A,B}
     3    16       A->B B->A  True False    False  False    2  NO A:{A,B} B:{A,B}
     4     8       A->B B->A  True False    False  False    2  NO A:{A,B} B:{A,B}
     5     8       A->B B->A  True False     True   True    2  NO A:{A,B} B:{A,B}
```

Every configuration fails **branch-determination**: the image set for branch A is
`{A, B}` and so is the image set for branch B. Two states sitting in the same
branch get transported to *different* branches, so there is no map on branches to
speak of — no permutation, no order.

**Refining the fibre does not repair it.** Grouping starting states by their
greedy-descent **basin** (94 distinct basins) still leaves the loop undetermined:

```
  tabu=3 steps=16: basins=94  determined=61  ambiguous=33  largest image=2
  tabu=4 steps=8 : basins=94  determined=58  ambiguous=36  largest image=2
  tabu=5 steps=32: basins=94  determined=58  ambiguous=36  largest image=2
```

Roughly a third of basins have an ambiguous image. A bundle needs a fibre on which
the transport is a map; neither candidate works here.

### Verdict

> **Non-identity transport exists. It is state drift, not monodromy.** There is no
> map on branches (or on basins), so there is no permutation, no order, and nothing
> for a Berry phase to be a phase *of*.

Which is a useful thing to have ruled out, and `test_transport.py` asserts the
negative — **13 checks that should FAIL if someone later builds a genuine branch
map.** That is the falsifiable signature to watch for.

### On BAHA

BAHA's own `docs/technical/QUANTUM.md` says moving between branches is *"analogous
to parallel transport"*, and the mechanism is enumerate → score → jump. There is no
base space, no connection, no loop and no residual. Grepping the repo, `holonomy`
appears in the title, a pybind docstring and the dashboard footer — nowhere in the
algorithm.

What *is* real there and unused: Lambert W has a genuine branch point at
`z = −1/e` with a non-trivial monodromy permuting `W_0 ↔ W_{−1}`. BAHA uses the
*existence* of two branches as two candidate basins; it never performs the loop.

BAHA's actual relevance to this experiment is different: it is **stateful**, and
stateful discovery is exactly the ingredient a transport needs to be non-trivial.
Not the source of the holonomy — the source of the memory.

```bash
python3 transport.py        # the table above
python3 test_transport.py   # 13 checks asserting the negative result
```

## Constructing the fibre: the transport-stable quotient (v0.8.0)

v0.7.0 left a precise gap: **no fibre on which the transport is a map.** Two states
in the same branch, or the same basin, were sent to different fibres.

The fix is not to keep guessing fibres. It is to **construct** the coarsest one
that works.

> A partition `π` is **T-stable** if `T` is well defined on its blocks:
> `x ~ y  ⟹  T(x) ~ T(y)`.

The refinement key of a state is `(block(x), block(T(x)))`. Split blocks whose
members disagree on that key, repeat to fixpoint. That is ordinary partition
refinement — the same operation as DFA minimisation and bisimulation quotienting.

Crucially this runs over the **full state space** (2^n states), so the quotient is
exact rather than sampled:

```
n=12, 24 edges, 2 optima, 4096 states

  tabu steps  refinement profile                stable  largest  bijective  cycles
     2     4   2 -> 4 -> 4                          4     1731     False    2 x [1]
     2     8   2 -> 4 -> 8 -> 16 -> 24 -> 24       24      740     False    4 x [1,1,2,4]
     3     4   2 -> 4 -> 4                          4     1725     False    2 x [1]
     3     8   2 -> 4 -> 8 -> 12 -> 12             12     1510     False    2 x [1,1]
     4     8   2 -> ... -> 40                      40      548     False    ...
```

### The positive result: the fibre exists

The branch partition (2 blocks) is **not** stable. Refinement terminates at
**4–40 blocks** — not the discrete 4096. So there is a genuine quotient onto which
the transport descends: **a 100–1000× compression of the state space onto a space
where the loop is a well-defined function.** `block_map()` asserts stability and
would raise if it failed.

### The remaining obstruction, now exact

The induced map on the quotient is **many-to-one**. It is a function but not a
permutation — and a monodromy must be a permutation. What it actually is, is a
**functional graph**: sometimes idempotent (all fixed points), sometimes carrying
cycles of length 2 and 4.

| | v0.7.0 | v0.8.0 |
|---|---|---|
| fibre | none found | **exists** — 4–40 blocks |
| transport on the fibre | not a map | **a well-defined function** |
| monodromy | impossible | needs **invertibility** — still missing |

So the gap has moved and become singular:

> **What is missing is exactly injectivity.** `T` is not one-to-one on the
> quotient, so there is no permutation, no order, and nothing for a Berry phase to
> be a phase of — but there *is* finite cyclic dynamics on a genuine quotient.

That is a sharp, attackable target rather than a philosophical one: **find a loop
whose induced map is injective on its stable quotient.** If one exists, the
quotient becomes a permutation group, and the Berry-phase question finally has an
object to be about.

### One caveat

The stable quotient depends on the loop: different `(tabu, steps)` give 4, 12, 24,
40 blocks. That is expected — different transports have different maps — but it
means the fibre is **loop-specific**, not canonical. A canonical fibre would need
an argument that the stable quotient is independent of the schedule within some
class, which is not established.

```bash
python3 stable_quotient.py        # the table above
python3 test_stable_quotient.py   # 18 checks: fibre exists, map is not a permutation
```

## Prime fields: where invertibility is free, and where it isn't (v0.9.0)

The proposal: use `F_p^×` with `T_a(x) = a·x mod p`. Since `p` is prime, every
`a ≠ 0` is invertible, so `T_a ∈ Sym(F)` **for free**. A loop with edge labels
`a₁…a_k` has residual `h = Π aᵢ mod p`, of order dividing `p−1`; and since `F_p^×`
is cyclic, `φ(h) = exp(2πik/(p−1))` is a genuine character into `U(1)`.

### The algebra is correct

Verified for `p = 5, 7, 11, 13`: `x → ax` is a bijection for every `a ≠ 0`;
multiplication composes; every multiplicative order divides `p−1`; the character
has modulus 1. And the concrete claims hold exactly — `p = 5`, `×2` is the
4-cycle `1 → 2 → 4 → 3 → 1`, and `×4` is an involution.

### But as a fix for the v0.8.0 obstruction it is circular

`T_a` is invertible **because it was defined as a group action**. And a loop
residual `h = Π aᵢ` is a property of **labels we chose**, so `h ≠ 1` carries no
information about any search. It is a model of the target, not a construction of
it.

### What *is* earned: the recurrent core

A functional graph always splits into a **recurrent core** (its cycles) and the
transient trees feeding it. `T` restricted to a cycle is a permutation *by
definition* — invertibility that is not posited. And that is exactly the structure
v0.8.0 found:

```
  n=12 tabu=2 steps=8
    stable quotient         : 24 blocks
    recurrent core          : 8 nodes in 4 cycle(s), lengths=[1, 1, 2, 4]
    transient (irreversible) : 16 blocks feed the core
    T is a permutation on the core : True
    embeds in F_p^x (L | p-1)      : {1: [3,5,7], 2: [3,5,7], 4: [5,13,17]}

  n=10 tabu=3 steps=8
    stable quotient         : 18 blocks
    recurrent core          : 2 nodes in 2 cycle(s), lengths=[1, 1]
    transient (irreversible) : 16 blocks feed the core
```

The observed cycle lengths divide `p−1` for small primes, so **the character
`φ: Z/L → U(1)` genuinely exists for the structure that was found**, rather than
for one we chose.

### The honest statement, narrower than "primes give invertibility for free"

> Invertibility is recovered **on the recurrent core** of the real transport, and
> that core embeds into `F_p^×`, so the phase is a real character of a real finite
> group. The trees feeding the core remain many-to-one, and **they are most of the
> state space** — no prime field repairs that.

The chain is now:

```
memory → non-identity transport → stable fibre → invertible core →
cyclic group → character into U(1)
```

with the last step **earned on the recurrent part only**, and the irreversible
remainder stated rather than hidden.

```bash
python3 prime_holonomy.py         # the laboratory, and the bridge to it
python3 test_prime_holonomy.py    # 39 checks: algebra correct, core earned, obstruction survives
```

## The commuting square — and why it is the wrong question *for this axis* (v0.12.0)

Two operators delete what does not survive. `S_res` deletes what fails
**refinement**; `S_dyn` deletes what fails **iteration**. Their square has two
routes and a defect:

$$A = \mathcal S_{\rm dyn}\mathcal S_{\rm res}(X), \qquad
B = \mathcal S_{\rm res}\mathcal S_{\rm dyn}(X), \qquad
\Omega = \operatorname{defect}(A,B).$$

The answer depends **entirely on which kind of refinement axis is used**, and the
two axes are not the same thing:

| axis | structure | `Ω` |
|---|---|---|
| **quotient** (PDI's own, §1) | surjective, `T`-invariant bonding maps | **0** — provably |
| **inclusion** (TDA filtration) | injective, *not* required to be `T`-invariant | **≠ 0** |

### `Ω = 0` on the quotient axis, degenerately

Both arms are "intersect with a fixed set", so they commute by associativity of
intersection. And a finite tower of quotients of one finite set has **inverse limit
= its finest level**, so `S_res` discards nothing. Checked over **1,204,224**
`(T, tower)` systems at `n ≤ 4`: zero mismatches, `T` descending through the
bonding maps every time.

### `Ω ≠ 0` on the inclusion axis, exactly characterised

$$\Omega \neq 0 \quad\Longleftrightarrow\quad
\exists\, x\in F \text{ periodic with } T^n(x)\notin F \text{ for some } n$$

Held as an **iff** over all 3,754 `(T,F)` pairs at `n ≤ 4` (1,274 failures, 33.9 %)
— and there were **zero** failures among the 1,139 pairs where `F` happened to be
`T`-invariant. **`T`-invariance is exactly the hypothesis that forces commutation.**

Smallest witness, `n = 2`: `X = {0,1}`, `T` the swap, `F = {0}`.

```
  A = core(T, F)      = {}      refine first  -> cycle dies
  B = core(T, X) & F  = {0}     iterate first -> survives the clip
```

### What this settles

- **`Ω` is not a PDI quantity.** On PDI's own axis it is *identically zero*.
  Searching for `Ω ≠ 0` over the quotient tower could only ever have returned
  nothing — now a theorem, not a guess.
- **`Ω` is real, but it belongs to the hybrid setting** — persistence of a Conley
  index across a filtration — not to PDI's tower.

What survives on PDI's axis is not a defect to measure but a **construction**:
`R_∞ = lim← R_j` together with descent of the dynamics through the bonding maps,
which held in every case tested. The square is not the obstruction to building it.

```bash
python3 survival_commutation.py        # all four parts
python3 test_survival_commutation.py   # 19 checks: commutes on one axis, fails on the other
```

## One question, or two? (v0.13.0)

> *"Does it go away, or does it come back?" — everything else is a change of
> language for that question.*

Tested rather than agreed with (`one_question.py`). The test is behavioural: **a
quantity that moves while the survival predicate is held fixed is not a
translation of the question.**

Most of the list does reduce. The persistent boundary, `D`, the functional-graph
split (cycle vs tree), `T|R` vs `T` off `R`, `C_L`/`F_p^×`, `χ → U(1)`,
`π(R_{j+1}) ⊆ R_j`, and `Ω` are all the same operator read in different
coordinates. Two things are not:

**1. "Comes back" is two predicates, and PDI ships both.**

```
horizon  (recompute_statuses) : LIVE iff the node reaches level H   structural
explicit (finalize_explicit)  : LIVE iff on a successful trajectory  outcome
```

Same tree, both readings, `n_j` identical, and the level-1 live *sets* are
`{(1,)}` and `{(0,)}` — **disjoint**. The counts agree there (both 1), so a scalar
ledger hides what the set makes visible. The question isn't well-posed until
"comes back" is pinned to a rule.

**2. `n_j` is survival-free, and `Δ` moves while survival is fixed.**

```
                    j=1  j=2  j=3  j=4
  n_j  marker dead    3    5    9   16      <- does not move
  n_j  marker live    3    5    9   16
  L_j  marker dead    2    4    8   16      <- moves
  L_j  marker live    3    5    9   16
```

And two systems with identical `L_j` and identical `D` differ in `S` and `Δ`:

```
  A:  D = 1.0        S = 1.0        Delta = 0.0
  B:  D = 1.0        S = 1.720628   Delta = 0.720628
```

`Δ` is not a function of the survival predicate. It is `S − D` — a survival-free
growth rate minus a survival growth rate. This is *also* why `D` is
cofinal-invariant and `Δ` is not: the survival side is intrinsic, the cost side
isn't.

### The sharpened thesis

The dichotomy is not the original move. **It is the standard move.** Conley,
persistence, bisimulation minimisation, dead-code elimination — every field that
deletes what does not survive is applying it.

> PDI's original move is the **pairing**: a survival-free cost and a survival
> count **at the same resolution**, so the waste becomes a function of `j` and
> can be **located** (`j*`) and **rated** (`D`, `S`, `Δ`) instead of merely
> totalled.
>
> **Deleting gives a boolean. Pairing gives a curve. The curve is the instrument;
> where it turns is the result.**

```bash
python3 one_question.py        # parts 1, 1b, 2 -- all computed
python3 test_one_question.py   # 16 checks
```

## Keeping both — and keeping the edges (v0.14.0)

> *Keep the transient and the recurrent structure alike, because the distinction
> between what disappears and what returns is itself information.*

A distinction is information only if it is **not recoverable from either half**.
Two negative results force it (`both_structures.py`).

### 1. The core does not determine the transients

Same 3-cycle `0 → 1 → 2 → 0`, same transient count (2), different arrangement:

```
  T1   transient edges 3->0, 4->0      profile {1: 2}
  T2   transient edges 3->4->0         profile {1: 1, 2: 1}
```

### 2. The counts do not determine the structure

```
  A traces: (a,b) (a,c) (d,e) (d,f)    a has 2 children, d has 2
  B traces: (a,b) (a,c) (a,d) (e,f)    a has 3 children, e has 1

  n_j  A = [2, 4]   B = [2, 4]         identical
  L_j  A = [2, 4]   B = [2, 4]         identical

  canonical form  A = ((()())(()()))
                  B = ((()()())(()))     NOT isomorphic
```

Every scalar PDI reports is a **level-size profile**, and a level-size profile
cannot see the difference. **The information is in the edges.**

### What this corrects

v0.13.0 said the original move is the pairing of a survival-free cost with a
survival count at the same resolution. That stands — it's why `n_j` is
survival-free. But a pairing of two level-size profiles is still a *summary*: it
says **how much** is transient at each resolution, never **how the transients are
arranged**.

> **Keep both, and keep the edges** — because the distinction is information
> precisely where the counts are blind.

The limitation is of the *summary*, not the structure: PDI stores the trie, so
the edges are retained. The ledger is a projection of it, and that projection is
not injective.

```bash
python3 both_structures.py        # two negative results
python3 test_both_structures.py   # 13 checks, incl. non-isomorphism by AHU
```

## Ingest: three more frameworks (v0.15.0)

`FORMATS` now has seven loaders. The three new ones, with honest confidence levels:

| format | written to | confidence |
|---|---|---|
| `otel` | the published **OpenTelemetry GenAI semantic conventions** (`gen_ai.operation.name`, `gen_ai.tool.name`, `gen_ai.tool.call.arguments`, `gen_ai.request.model`, `error.type`) | highest — it is a spec |
| `autogen` | the documented message schema, **both** shapes it has shipped: v0.2 `function_call` dicts and v0.4 `ToolCallRequestEvent` / `ToolCallExecutionEvent` | medium |
| `crewai` | an **inferred** schema — CrewAI publishes no stable trace format | lowest |

**None of the three was validated against a live capture.** The fixtures in
`fixtures/` are constructed to those schemas. So the tests establish *schema
conformance* and *edge preservation*, not field-testedness. OTel is the one to
trust, because it is the one written to a spec — and since most frameworks are
converging on it, it is also the one that eventually subsumes the other two.

### Edge preservation is the load-bearing test

The axiom says keep the **edges** — how the cost was incurred. A loader that
collapses repeated calls, drops arguments, or mis-pairs a result with its call has
thrown them away regardless of schema conformance. So the suite tests that, and it
caught a real bug:

```python
# AutoGen v0.2 puts function_call on the ASSISTANT message but the id (if any) on
# the FUNCTION message. Keying pending calls by tool_call_id alone therefore
# mis-attributes results -- including errors -- to the wrong step.
```

```
  before:  search          read  ERR=Error: gone      <- wrong call
  after :  search   ERR=  read  ERR=Error: gone      <- correct
```

The loader now pairs by id when present, else by tool **name** to the oldest
unpaired call, else FIFO. Pinned by `test_ingest_more.py`.

Two more checks that exist specifically because of the edges:

```
  EDGES: repeated identical calls are NOT collapsed   (two `search` calls with
                                                       identical args stay two steps)
  EDGES: args survive  format -> canonical -> back    (round-trip per format)
```

```bash
python3 ingest.py                 # demo
python3 test_ingest.py            # original four formats
python3 test_ingest_more.py       # otel / autogen / crewai, incl. edge preservation
```

## One principle, or three? (v0.16.0)

> *Lindenbaum–Tarski, Hennessy–Milner, explicit coercion, "no experiment without
> protocol", and "make illegal states unrepresentable" are one principle, and PDI
> instantiates all of them.*

Tested rather than agreed with (`invariance_first.py`). **They are three**, with
different logical shapes, and PDI's standing differs on each:

| | shape | sources | PDI |
|---|---|---|---|
| **(a)** witness-gated construction | axiom you enforce | LT **form**, explicit coercion, Minsky | **strong** |
| **(b)** canonicity | property you hope for | LT **guarantee** | **absent** — row 9.1 open |
| **(c)** agreement of two equivalences | theorem you prove or refute | Hennessy–Milner | **conditional** — §13 |

### (a) The gate fires on the witness, not the result

`TowerViolation` on the refinement law. `S_shallow`/`D_shallow` so a value attained
*inside* the horizon isn't printed as a rate. A convergence status on every
asymptotic number:

```
STABLE / TRENDING_UP / TRENDING_DOWN / UNRESOLVED / NONE
  + bound: exact / lower bound / upper bound
```

### (b) Canonicity is absent — and the dependence is *quarantined*

The tower is an **input** (`tower=None`), not derived. So the LT guarantee isn't
available: row 2.3 proves only **cofinal** invariance, row 9.1 leaves **canonicity
open, known to vary**.

Same traces, same marks, index shifted by one prepended symbol. Both pass the gate.

```
     j   L_j (A)  log2L/j     L_j (B)  log2L/j
     1         2  1.00000           1  0.00000
     8       256  1.00000         128  0.87500
     9                             256  0.88889

  finite-scale :  A D=1.000000 D_shallow=True
                  B D=0.888889 D_shallow=False     <- presentation-dependent

  asymptotic   :  A  1.000000  STABLE       exact
                  B  0.888889  TRENDING_UP  lower bound
```

The true limsup is **1 for both** — dropping B's first level recovers A. So B's
lower bound is *correct*, A's exact value is *correct*, and the asymptotic layer
never claims a number it can't support. This is row 3.1 (*the finite-window sup is
not the limsup*) firing on a presentation shift.

> PDI does not **eliminate** presentation-dependence. It **quarantines** it.
>
> The principle here is not *"the quantity is invariant."* It is **"you may not
> assert an invariance you do not have — the representation must carry the
> status."**

That's the explicit-coercion rule: the claim isn't forbidden, it must come with
its witness.

### (c) Agreement is conditional

`Ω = 0` exactly when the refinement axis is `T`-invariant (v0.12.0). One instance,
one counterexample — which is what a theorem of this shape licenses.

### The honest form

**PDI enforces (a) everywhere it can. It does not have (b), and says so in row 9.1
rather than asserting it.** That row is the principle applied to the ledger itself:
the deepest instantiation in the repo isn't an object that satisfies the principle
— it's a ledger entry that records its absence.

```bash
python3 invariance_first.py        # gate, reindexing, and what the layers do
python3 test_invariance_first.py   # 18 checks
```

## Proof-aware? An audit of the warrants (v0.17.0)

> *So this is a proof-aware observability system.*

A proof-aware system states warrants, and **every warrant it states is
dischargeable** — enforced at construction, or a fact about the data in hand.
Audited in `proof_awareness.py`:

| warrant | claim | backing | verdict |
|---|---|---|---|
| `TowerViolation` | refinement law holds on the corpus | enforced at construction | **discharged** |
| `S_shallow` / `D_shallow` | the sup was attained *inside* the horizon | fact about the observation | **discharged** |
| convergence status | shape of the observed tail | fact about the observation | **discharged** |
| `bound` | a bound on the **unobserved** tail | claim about data not in hand | **NOT DISCHARGED** |

### The one place the grammar outran the warrant

`limsup = inf_m sup_{j≥m} s_j`, so **no finite prefix determines a limsup**. Any
observation is consistent with continuations having limsup anywhere in `[0, M₁]`.
All three `bound` labels were falsifiable, and here they are falsified:

```
  status          observed tail        reported   continuation   true limsup
  TRENDING_UP     0.1 0.2 0.3 0.4      0.400000   1/j            0.002506   VIOLATED
  TRENDING_DOWN   0.4 0.3 0.2 0.1      0.400000   9,9,9,...      9.000000   VIOLATED
  STABLE          0.5 0.5 0.5 0.5      0.500000   9,9,9,...      9.000000   VIOLATED
```

Not a coding error — a theorem. It's why `limsup([1, 1/2, …, 1/49]) = 1/49` while
the *same prefix* extended with zeros has limsup `0`.

### The fix: labels carry their hypothesis

```
  'exact'        ->  'window-exact (tail flat so far)'
  'lower bound'  ->  'lower bound IF the tail stays monotone'
  'upper bound'  ->  'upper bound IF the tail stays monotone'
  'unknown'      ->  'no bound claimed'
```

Same move as `S_shallow`: **don't forbid the number, attach the condition under
which it means what it says.** The estimate is still reported — it's useful — it
just no longer borrows the grammar of a proof.

```bash
python3 proof_awareness.py        # the audit and the three falsifications
python3 test_proof_awareness.py   # 20 checks
```

## O2 resolved: irreversibility is structural (v0.18.0)

O2 asked: **exhibit an injective transport loop, or prove non-injectivity is
necessary.** It's the second. And the obstruction is a *single step*.

### The transport is a composition of memoryless legs

`Searcher.run` resets the tabu list at the **start of every call**, and the loop
driver calls it once per leg:

```
T = f_k o ... o f_1          f_i = run(., lam_i, steps)
g(x) = x XOR e_{v(x)}        v(x) = argmin_v ( delta(x,v), |v - lam(n-1)| )
```

### Three steps to the theorem

**Composition lemma.** `T` injective ⟹ `f_1` injective. So a non-injective first
leg kills every schedule built on it — *the loop search was the wrong search.*

**Lemma A.** At a **global** optimum `z`, for all `a, b`:

```
delta(z^e_a, b) = E(z^e_a^e_b) - E(z^e_a)  >=  E(z) - E(z^e_a) = delta(z^e_a, a)
```

because `E(z)` is the global minimum. **Undoing a perturbation of an optimum is
never worse than any alternative.** Verified **8096/8096**.

**Theorem.** With `d2(z)` = # other optima at Hamming distance 2 from `z`:

```
|g^-1(z)| = |{ a : v(z^e_a) = a }|  >=  n - 2*d2(z)
```

Verified **400/400**, and **tight** — slack `0` at `n=8, d2=0`. For
`n >= 2*d2(z) + 2` the one-step map is **not injective**.

### The chain closes

`run(·, λ, steps)` has `g` as its **first** step — the tabu list is empty there —
so `run = h ∘ g` and inherits non-injectivity. Therefore:

> **No schedule is injective.** Not for any length, any λ, any tabu length.

That also explains a fact the census produced but didn't predict: one-step image
size is **identical across tabu lengths** — `{2:96, 3:96, 4:96, 5:96, 6:96, 8:96}`
of 256. The first step is tabu-free, so tabu length can't touch it.

### The mechanism

```
  E(z)          0(opt)     2      3      4      5      6    ...   11    12    14
  mean |S(z)|   8.000   8.000  5.500  3.000  3.500  1.739   ...  0.000 0.000 0.000
```

Concordance `> 0.9` but **not** `1.0` — *concentrated*, not pointwise. Stated no
more strongly than the data.

> The map collapses hardest exactly where the search is trying to go.
> **You cannot have a contraction without a collision.**

### What it settles

The many-to-one collapse is not an implementation accident and not a failed loop
search. It's forced by the landscape having a global optimum. So:

```
F = transient trees  ->  R = recurrent core
    (info lost at the attractor)   (invertibility survives here)
```

`R` is **not** merely where invertibility happened to be recovered — it is the
**maximal place where invertibility can survive.**

Row **8.1** moves from `empirical negative, not a proof` to **PROVED**. It was the
last empirical negative in the ledger.

```bash
python3 collision_mechanism.py     # the collision characterisation and the swap
python3 o2_theorem.py              # lemmas, theorem, chain, mechanism
python3 test_o2_theorem.py         # 16 checks across many instances
```

## The invariant underneath

`D` is a property of the task; `S` is a property of the algorithm; `Delta` is the
overhead:

```
D     = limsup_j log L_j / (-log eps_j)   intrinsic, cofinal-invariant  (proved)
S     = limsup_j log n_j / (-log eps_j)   presentation-dependent
Delta = S - D  >= 0                       presentation-dependent
```

`L` is a **covering count** — it answers a question about the boundary, so it is a
function of *physical resolution* and cannot be moved by reindexing the tower.
`n` is not a covering count: dead ends cover nothing. Hence `D` survives cofinal
reindexing and `Delta` does not (refuted by explicit realizable counterexample:
`L_j = 2^j` with `n_j` exponential on odd shells gives `Delta = 1` for `P` and
`Delta = 0` for `P' = P_{2j}`).

The distinction is classical elsewhere — coaccessible vs all states in automata,
essential vs transient in sofic shifts, where entropy is a function of the
essential part only (Lind–Marcus). PDI is the data structure that keeps both.

### Two layers, because one estimator cannot serve both

**Finite-scale — exact on the observed corpus:** yield `L_j/n_j`, inflation
`n_j/n_j^ref`, distinction onset `j*`. No asymptotic claim.

**Asymptotic — reported only with a convergence status.** The finite analogue of
`limsup` is the moving tail `M_m = sup_{j≥m} s_j`, so the estimate is the max over
the last `k` observed levels, plus its trend. No regression fitting.

| status | meaning |
|---|---|
| `STABLE` | tail flat; the value is the estimate |
| `TRENDING_UP` | still rising; the value is a **lower bound** |
| `TRENDING_DOWN` | still decaying; the value is an **upper bound** |
| `UNRESOLVED` | not monotone at this horizon |
| `NONE` | no persistent classes |

```text
asymptotic layer
  S: 0.342783  TRENDING_DOWN (upper bound)   window sup was 4.983613
  D: 0.000000  STABLE        (exact)         window sup was 0.000000
```

This replaced a real defect: `sup_{j≤H}` is not `limsup`, and for sub-geometric
growth the two diverge badly. The toy suite caught it. `UNRESOLVED` is a legitimate
result on a short tower, not a failure.

## Real traces

The adapter was developed against a private corpus of the author's own agent
sessions. Only the aggregate shape is reproduced, with no transcripts, prompts,
commands, paths or model identifiers:

```text
runs       : >1100
tool calls : >14000   errors: ~6%
succeeded  : ~80%
formats    : pi
```

Grouping by model on that corpus produces a **descriptive**, not experimental,
comparison — the agents were doing different work, and the profiler says so:

```
persistent structure differs across agents: D in [1.85, 2.86]
-> agents did not all find the same structure; compare with care
```

`--matched` restricts to opening prompts that at least two agents actually ran,
which controls for the task. On that corpus it leaves a handful of turns — enough
to demonstrate the mechanism, far too little to conclude. **The profiler is ready;
a controlled task corpus is what is missing.**

## Toy validation

`toys.py` checks the instrument against **closed forms** — each toy has an
analytically known `n_j` and `L_j`, hence known `D`, `S`, `Delta`:

| toy | construction | `n_j` | `L_j` | `D` | `S` | `Delta` | status |
|---|---|---|---|---|---|---|---|
| T1 | every leaf succeeds | `2^j` | `2^j` | 1 | 1 | 0 | STABLE/STABLE |
| T2 | one leaf succeeds | `2^j` | `1` | 0 | 1 | 1 | STABLE/STABLE |
| T3 | half the leaves succeed | `2^j` | `2^{j-1}` | `(d-1)/d` | 1 | `1/d` | STABLE/UP |
| T4 | nothing succeeds | `2^j` | `0` | 0 | 1 | 1 | STABLE/NONE |
| T5 | spine + dead-end fan | `1+w(j-1)` | `1` | 0 | `S` | `S` | DOWN/STABLE |
| T6 | behavioural tower | `2,2,6` | `1,1,3` | `log2(3)/3` | 1 | `1-log2(3)/3` | UNRESOLVED/UP |

Exact agreement, refinement law validated on all six. T5 also demonstrated the
estimator defect:

```
       w     d  window sup   tail est         status
    1000     6    4.983613   3.655502  TRENDING_DOWN
    1000    12    4.983613   1.440663  TRENDING_DOWN
    1000    24    4.983613   0.680371  TRENDING_DOWN
    1000    48    4.983613   0.342783  TRENDING_DOWN
```

Window sup frozen at a shallow shell regardless of depth; the tail decays toward
the true value 0 and says it is an upper bound while it does.

## Evaluation requirement

Short horizons can hide `Delta`'s non-invariance, and this repo's own tests are the
example: at `H = 8` the transient spike lands on an odd level and the
non-invariance test correctly fails; at `H = 7` it lands even, reindexing agrees,
and the test **passes spuriously**.

A single finite window that misses the transient-growth subsequence will report
`Delta` as though it were an invariant. Any claim of the form *"agent X explores
less than Y"* must state the horizon or be backed by a growth-rate estimate.
`D` is unaffected. **This is a requirement on measurement, not a caveat about PDI.**

## What is implemented

- Separate `n_j` / `L_j` ledgers, maintained independently at every level.
- **Behavioural resolution towers** (`quotient_tower.py`) with the refinement law
  enforced by `validate()` / `validate_pairs()`.
- **Multi-framework ingest** (`ingest.py`): canonical, pi, OpenAI, LangSmith, plus
  OpenTelemetry GenAI spans, AutoGen, and CrewAI — seven loaders with
  autodetection, directory walking, and canonical round-trip export.
- **One-command profiler** (`pdi_profile.py`) for anyone's traces.
- `LIVE` / `TRANSIENT` / `UNKNOWN` node state with coaccessibility propagation;
  two live rules (horizon-reaching, or explicit).
- Adaptive STOP on physical resolution, discounted by the observed persistent yield.
- Node-level caching with hierarchical reuse.
- **Two output layers**: finite-scale diagnostics (exact) and asymptotic
  diagnostics (status-bearing).
- **A negative result about zeta invariants** (`zeta_separation.py`): the
  Ihara/Bass family does not separate the §15 pair (a tree has no cycles) and is
  sharp on the recurrent core — it is a complement to the ledger, not a rival.
- **Core monodromy — closed, negative** (`core_monodromy.py`): `γ ↦ T_γ|_R` is a
  monoid homomorphism but not a group representation — the core is
  loop-dependent (O1) and the inverse axiom fails (§18).
- **Twenty-two self-checking suites**, including closed-form toy validation, the
  refinement law verified over a full real corpus, and edge-preservation checks
  on every ingest format.

## Roadmap

- **A controlled task corpus** — repeated tasks per agent. The blocker for real
  conclusions, not the software.
- ~~**More ingest adapters** — CrewAI, AutoGen, OpenTelemetry GenAI spans.~~ Done in
  v0.15.0. The remaining gap is not code: none of the three has been run against a
  **live capture**, only against fixtures built to the published schemas.
- **Persistence-based GC** — eviction driven by the `L`/`n` split.
- **Learned towers** — derive the behavioural levels from data, while still
  enforcing the refinement law. Sequenced after the controlled corpus so a result
  can be attributed to the tower rather than to the learning algorithm.

## References

- `concepts/cofinal-invariance` — gauge-dependence of raw exponents, `Delta` non-invariance
- `concepts/regular-growth-identification` — full vs live counts
- `concepts/resolution-stop` — the quotient → completion → observer triple
- Lind & Marcus, *An Introduction to Symbolic Dynamics and Coding* — entropy from the essential part

> **Give away the instrument. Sell the laboratory.**

## The spine

**[`SPINE.md`](SPINE.md)** — the whole chain in mathematics, with every claim
labelled **proved / computed / negative / open**. If you read one file in this
repository, read that one. It states plainly which results are earned, which are
empirical, and which are conjecture:

```
memory -> non-identity transport -> stable fibre ->
                 recurrent invertible core -> C_L -> U(1)
```

The invertible step is earned **on the recurrent core only**; the transient
remainder is stated rather than hidden; and the persistent/transient pattern that
recurs at two different levels is flagged as a **conjecture**, not a theorem.

**§12 records the provenance.** Every layer has an established literature
underneath it — the behavioural-equivalence spectrum (van Glabbeek), partition
refinement (Kanellakis–Smolka; Glück–Möller–Sintzoff), stability of persistence
diagrams (Cohen-Steiner–Edelsbrunner–Harer), monodromy without curvature
(Duistermaat), and Hodge zero-mode holonomy for parameter-dependent TDA
(arXiv:2605.28326). **PDI did not invent these; it assembles them and keeps the
accounting.** The section also states two things it does *not* claim: PDI's
"persistent" is survival, not topological persistence; and no new refinement
algorithm is proposed.


---

## The mathematics of PDI

The whole chain, in one narrative: why the tower is forced, why the two
ledgers cannot be merged, and exactly which claims are proved, computed, or
open. Claim-by-claim status is the ledger in [`SPINE.md`](SPINE.md) §0.

*Prefer to watch? The author's walkthrough of this narrative —
[The Hidden Cost of AI Discovery](https://www.youtube.com/watch?v=tkPmvU6x_bc) —
covers the same chain, ending on why benchmark scores hide the discovery cost.*

*Two ledgers, a tower, and the mathematics of what a finite observation licenses*

### Two runners and a bad metric

Two agents are given the same puzzle. The first tries twenty approaches and finds the answer. The second
tries two thousand and finds the same answer. Our dashboards say: both succeeded, success rate 1.0,
nothing to discuss. The difference — a hundredfold difference in how much work was needed to discover
the same structure — is invisible, because we collapsed the whole trajectory into a terminal bit.

This is the problem the Persistent Discovery Index (PDI) is built around, and the interesting part is
not that we can count steps. Counting is easy. The interesting part is that the quantity you want to
measure, discovery cost, is not a property of the answer. It is a property of the search, and search has
structure that changes with the resolution at which you look at it. So before we can measure anything,
we need a mathematical object that keeps both the structure found and the structure wasted, at every
resolution, without conflating them.

That object turns out to be a refining tower of quotients, and almost everything else in this software
is a consequence of taking the tower seriously.

### The tower

Let H be a set of histories — finite sequences of abstracted states, one per agent run. For each level j
= 1, …, J let Qⱼ : H → Xⱼ be a surjection onto a finite set of behaviour classes, where the levels
refine:

$$Q_{j+1}(x) = Q_{j+1}(y) \implies Q_j(x) = Q_j(y). \tag{1}$$

Equation (1) is the whole skeleton. It says that if two histories are indistinguishable at the finer
resolution j+1, they were already indistinguishable at the coarser resolution j. Equivalently, Qⱼ
factors through Qⱼ₊₁. The classes form a tree: level j's classes are unions of level (j+1)'s.

This is not a novel construction. It is the linear-time/branching-time spectrum of van Glabbeek, the
bisimulation quotients of Kanellakis and Smolka, the refinement orderings of process algebra. What PDI
does with it is the next section. But it is worth pausing on why (1) is the right axiom and not merely a
convenient one.

Without (1), the Xⱼ are just an unrelated list of feature spaces. You could compute a number at each
level and plot them, but the numbers would not be comparable, because there is no statement relating
what two adjacent levels are talking about. The refinement law is what makes the levels a tower — a
single object observed at many scales — rather than a bag of independent measurements. In code this is
enforced, not assumed: QuotientTower.validate raises TowerViolation if a pair of histories violates (1).
You cannot build the object without the proof.

### Two ledgers

Fix a distinguished subset P ⊆ H of histories that reach a successful outcome. Define

$$n_j = |X_j|, \qquad L_j = |Q_j(P)|. \tag{2}$$

nⱼ counts every distinction the presentation makes at resolution j. Lⱼ counts how many of those
distinctions are inhabited by successful histories — what survived.

Two observations. First, nⱼ = |H/ ∼ⱼ| exactly: it is a class count, not an estimate. Second, Lⱼ is
non-decreasing in j at fixed horizon, because the refining maps are surjective and P is fixed.

The design decision — the one that matters — is to keep both numbers and never merge them. Most systems
that deal with transient structure delete it. DFA minimisation trims unreachable states; symbolic
dynamics keeps only the essential part; bisimulation discards non-bisimilar branches; a cache evicts
misses. Each of these is the same move: intersect with the set of things that survive. PDI's claim is
that the gap between what was explored and what survived is itself the measurement, and you cannot see a
gap if you have already thrown away one side of it.

There is a subtlety here that costs people time. nⱼ is a survival-free quantity: it is determined by the
node set, not by the success predicate. You can verify this by fixing the histories and flipping the
success marks; nⱼ does not move. This means nⱼ is not a translation of "what survives" into another
language. It is an independent coordinate. The tower has two axes, and they are genuinely two.

### Exponents

Now we do what one always does with a growing sequence: rate it. Let εⱼ be the physical resolution at
level j, decreasing to zero, and define

$$D = \limsup_j \frac{\log L_j}{-\log \varepsilon_j}, \qquad S = \limsup_j \frac{\log n_j}{-\log \varepsilon_j}, \qquad \Delta = S - D. \tag{3}$$

Call them persistent complexity, exploration complexity, and discovery overhead. The claim that D means
something intrinsic rests on a covering argument. Build the discovery tree from the histories, put the
visual metric d = 2⁻ʳ on its boundary ∂ T, where r is the level. Level-j cylinders cover the boundary,
and distinct level-j cylinders are separated by 2 · 2⁻ʲ, so no ball of diameter 2⁻ʲ meets two of them.
Hence the minimal covering number is exactly the live count:

$$N(\partial T,\, 2^{-j}) = L_j, \qquad \dim_B(\partial T) = \limsup_j \frac{\log L_j}{-\log \varepsilon_j}. \tag{4}$$

So D is a box dimension. It is a covering count, a function of physical scale. And that is exactly why
it is cofinal-invariant: two towers that are cofinal in resolution and share a boundary compute the same
box dimension, because they are covering the same set at the same scales. Reindexing the tower does not
change D.

S has no such interpretation, and this is not a defect of the definition but a fact about what it
counts. Dead ends cover nothing. There is no set whose covering number is nⱼ, because the transient
branches do not survive to be covered. So S is intrinsically a shell-indexed sequence with no scale-free
meaning, and Δ = S - D inherits that. It is not cofinal-invariant. Concretely, take Lⱼ = 2ʲ and nⱼ = 4ʲ
on odd shells, 2ʲ on even shells. Then Δ = 1 for one indexing and Δ = 0 for the cofinal subsequence of
even shells, while D is unchanged.

This is the interpretive core of the instrument. D is a property of the task — how much structure there
is to find. Δ is a property of the algorithm — how much of its walk was wasted. Δ is a legitimate
algorithm comparison precisely when the task is held fixed, and is meaningless otherwise.

### The honest problem: a window is not a limit

Everything above concerns limsups over infinitely many scales. On real data you have finitely many
levels, and you compute a maximum over what you observed. These are different statistics, and the
difference is not noise.

Consider nⱼ = 1 + w(j-1). The ratio log nⱼ / j decays to zero, so the true S = 0. But the
observed-window maximum is log₂(1+w)/2, attained at j = 2, and it does not decrease no matter how deep
you go. The window statistic is not a noisy estimate of S; it is a different statistic that happens to
agree when growth is geometric.

The response is structural, not cosmetic. The instrument reports two layers. The finite-scale layer is
exact on the observed corpus: yield Lⱼ/nⱼ, class counts, and the onset $j^\*$, the first level at which
yield falls below a threshold. None of that involves asymptotics. The asymptotic layer reports the
moving tail Mₘ = sup[j≥m] sⱼ together with a convergence status: STABLE, TRENDING_UP, TRENDING_DOWN,
UNRESOLVED, or NONE.

The status matters more than the number, because of a small theorem. Since limsup = inf[m] Mₘ, no finite
prefix determines the limit: any observation is consistent with continuations whose limsup lies anywhere
from 0 to the prefix supremum. This is why every bound label in the system carries its hypothesis —
"lower bound if the tail stays monotone" — rather than asserting a bound outright. The number is not
forbidden; it is required to state the condition under which it means what it says. I will return to
this idea at the end, because it is the software's real thesis.

### Transport: from labels to loops

Now change the question. Instead of asking how much structure a search discovered, ask whether a closed
loop of presentations moves the persistent structure.

We need a stateful process. Let F be a finite state space and consider xₜ₊₁ = run(xₜ, λₜ, steps), where
λₜ is a presentation parameter and run is a deterministic local search with memory. For a closed loop γ
: λ₀ → λ₁ → ⋯ → λ₀, define the transport

$$T_\gamma : F \to F, \qquad T_\gamma(x) = \text{state after traversing } \gamma. \tag{5}$$

The memory requirement is not decorative. A memoryless solver has x = f(λ), so every closed loop returns
f(λ₀) and T_γ = id by construction. There is no transport question to ask. The memory — a tabu list, in
our implementation — is what makes "which branch are we on" a question with a nontrivial answer.

But now T_γ need not be well-defined on any meaningful partition. Two states "near the same optimum" can
be sent to different places. The fix is to construct the coarsest partition on which T is a map. Call π
T-stable if

$$x \sim_\pi y \implies T(x) \sim_\pi T(y). \tag{6}$$

Starting from any partition, iterate the refinement key

$$\kappa(x) = \bigl(\text{block}(x),\; \text{block}(T(x))\bigr) \tag{7}$$

to a fixpoint. Refinement is monotone and bounded by the discrete partition on a finite set, so it
terminates; at the fixpoint (6) holds by construction, and coarseness follows because any T-stable
refinement of the initial partition must separate states on which κ differs. This is ordinary partition
refinement — DFA minimisation, bisimulation quotienting — applied to a transport map instead of a
transition relation, and it compresses hard: from 4096 states down to 4–40 blocks, depending on tabu
length and step count.

### The recurrent core, and invertibility that is earned

Every finite map decomposes its functional graph into a recurrent core R — the union of its cycles — and
transient trees feeding into it. On R, the map is a permutation, by definition.

This is the first place in the whole construction where invertibility is not posited but earned. A cycle
is a permutation because a cycle is a permutation. Nothing was assumed. And it is exactly where the
structure lives: in one computation, a 24-block quotient split into 16 transient blocks and 8 recurrent
ones, with cycle lengths (1,1,2,4).

It is worth saying what this is not. One can build invertibility for free by working over a prime field:
let F = Fₚ^× and Tₐ(x) = ax mod p. Every nonzero a is invertible, so every Tₐ is a permutation, and a
loop with edge labels a₁, …, aₖ has residual h = ∏ aᵢ of finite order dividing p-1. Since Fₚ^× is
cyclic, h = gᵏ for a generator g, and

$$\varphi(g^k) = \exp\!\left(\frac{2\pi i k}{p-1}\right) \tag{8}$$

is a genuine character into U(1). All of that is correct, and all of it is circular as an answer to our
problem. Tₐ is invertible because we defined it as a group action. The residual h is a property of
labels we chose, not of any search. It models the target; it does not produce it. The earned statement
is narrower: the recurrent core of the real transport is invertible, and when its cycle lengths divide
p-1 — as 4 divides 4 and 12, as 2 divides 2, 4, 6 — the character exists for the structure we actually
found.

### Irreversibility is structural

The transport is many-to-one, and for a while that was an empirical observation: zero injective loops
among 216 tested. It is now a theorem, and the proof is short enough to give in full, because the
mechanism is the point.

Write the search state as x ∈ {0,1}ⁿ, let E be the number of uncut edges, and let the atomic step be a
min-conflicts flip

$$g(x) = x \oplus e_{v(x)}, \qquad v(x) = \operatorname*{argmin}_v \bigl(\delta(x,v),\; |v - \lambda(n-1)|\bigr), \tag{9}$$

where δ(x,v) = E(x ⊕ eᵥ) - E(x) and the comparison is lexicographic. Note that g minimises δ without
requiring it to be negative. It is a min-conflicts step, not gradient descent.

Lemma. Let z be a global optimum. Then for all a, b,

$$\delta(z^{e_a}, b) = E(z^{e_a e_b}) - E(z^{e_a}) \;\ge\; E(z) - E(z^{e_a}) \;=\; \delta(z^{e_a}, a), \tag{10}$$

because E(z) is the global minimum. So a is always an argmin at z^(eₐ) — undoing a perturbation of an
optimum is never worse than any alternative. Verified on 8096/8096 triples.

Theorem. Let S(z) = {a : v(z^(eₐ)) = a} and d₂(z) = #{z' optimal, z' ≠ z : d_H(z,z') = 2}. Then

$$|g^{-1}(z)| = |S(z)| \ge n - 2\,d_2(z). \tag{11}$$

The count is clean: a ∈ argmin[b] δ(z^(eₐ), b) always, and the argmin is a singleton except when some
other optimum sits at Hamming distance two from z using bit a; at most 2 d₂(z) bits can be so involved,
so at least n - 2d₂(z) bits win their tie-break outright.

Corollary. For n ≥ 2d₂(z) + 2, |g⁻¹(z)| ≥ 2: the one-step map is not injective.

The last step is a composition lemma. If T = fₖ ∘ ⋯ ∘ f₁ is injective then f₁ is injective, since f₁(x)
= f₁(y) ⇒ T(x) = T(y). And run( · , λ, steps) has g as its first step, because the tabu list is empty
there. Therefore every leg is non-injective, and non-injectivity composes: no schedule of these legs is
injective. It also explains a fact the census produced without predicting: the one-step image size is
identical across tabu lengths, because the first step is tabu-free.

The moral is not that the search is bad. It is that the map collapses hardest exactly where the search
is trying to go. You cannot have a contraction without a collision. And the recurrent core is therefore
not merely where invertibility happens to survive — it is the maximal place where it can.

### A square that almost commutes

Deleting things has an order, and the order matters. Let Sᵣₑₛ delete what does not survive refinement
(take the inverse limit), and S_dyn delete what does not survive iteration (take the recurrent core).
The defect is Ω = defect(A, B) where A = S_dyn Sᵣₑₛ and B = Sᵣₑₛ S_dyn.

On PDI's own axis — a tower of quotients of one finite set with surjective, T-invariant bonding maps —
the square commutes, Ω = 0, and it does so degenerately: both arms are "intersect with a fixed set," and
a finite tower of quotients has inverse limit equal to its finest level, so nothing is discarded by
Sᵣₑₛ. Over 1,204,224 systems at n ≤ 4, zero mismatches. This is a negative result about a candidate
invariant: Ω has no content as a PDI quantity.

On the other axis — a filtration that is not T-invariant, as in topological data analysis — Ω is
genuinely nonzero, with an exact characterisation: Ω ≠ 0 if and only if some periodic point of the
system lies in the filter while its orbit leaves it. Verified as an iff over all 3,754 pairs at n ≤ 4,
with zero failures among the 1,139 whose filter is T-invariant. The minimal witness is two states: X =
{0,1}, T the swap, F = {0}. Refine first and the cycle dies; iterate first and it survives the clip. The
dividing line is precisely T-invariance of the refinement axis.

### What the ledger cannot see

Here the construction turns on itself. Two tries built from four traces each:

$$A = \texttt{((()())(()())),} \qquad B = \texttt{((()()())(()))}. \tag{12}$$

These are different rooted trees — a has two children of degree two on the left, three and one on the
right. But nⱼ = (2,4) and Lⱼ = (2,4) for both. Every scalar PDI reports is a level-size profile, and a
level-size profile is a projection. This one is not injective. The information lives in the edges.

This is a good place to be honest about what a "summary" is. It is tempting to read a two-ledger result
as capturing the structure. It captures how much is transient at each resolution; it never captures how
the transients are arranged. The data structure retains the trie, so the edges are there to be queried —
but the headline numbers are lossy, and the loss is not recoverable from them.

That raises an obvious question: is there a compact invariant that does better — something that is
sensitive to edges without storing the whole graph? This is a natural place to reach for a zeta
function. The Ihara zeta of a graph is

$$Z_G(u) = \prod_{[P]} \left(1 - u^{\ell(P)}\right)^{-1} \tag{13}$$

over primitive non-backtracking closed cycles, with the Ihara–Bass closed form

$$Z_G(u)^{-1} = (1-u^2)^{|E|-|V|} \det\!\left(I - uA + u^2(D-I)\right). \tag{14}$$

It is a beautiful object, and it fails at the very witness that motivated it, for a structural reason.
The pair in (12) is a tree. A tree has no non-backtracking closed walk, so the product is empty and Z =
1 for both; the determinant is 1 - u² for both. The zeta family is identically blind here, because zeta
listens to edges only through cycles, and edges are not cycles. Computed across every forest tested, the
determinant is

$$\det\!\left(I - uA + u^2(D-I)\right) = (1-u^2)^{\#\text{components}}, \tag{15}$$

a function of the component count alone. Zero shape information.

That is not a failure of zeta; it is a location. On graphs with cycles it is sharp: C₃ ⊔ C₃ and C₆ share
a degree sequence and (|V|, |E|) = (6,6), yet Z⁻¹ = (1-u³)⁴ versus (1-u⁶)². So the routing law is:

$$\text{transient arrangement} \to \text{edge/tree invariants (AHU)}, \qquad \text{recurrent arrangement} \to \text{cycle invariants } (Z_G). \tag{16}$$

Keeping the edges does not mean every edge-derived invariant preserves what the ledger lost. Projecting
G → {primitive cycles} deliberately destroys the forest.

### The last strand, and why it closes on the central problem

The natural next hope is to decorate cycles with transport data. On the recurrent core, a closed cycle P
could carry a holonomy χ(P) ∈ U(1), and one forms the twisted product

$$Z_{G,\chi}(u) = \prod_{[P]}\left(1 - \chi(P) u^{\ell(P)}\right)^{-1}. \tag{17}$$

This has content if and only if χ does not factor through the cycle length: if χ(P) = f(ℓ(P)), the
product is a function of the length multiset, which Z_G already determines. Operational form: χ must
take two values on prime cycles of the same length.

PDI has no such gain. The character of (8) is built on C_L, hence through the cycle order. The other
reading — χ(P) as the holonomy of the transport itself — runs into the sharpest question in the
construction:

$$\rho : \pi_1(\text{presentation space}) \to \mathrm{Sym}(R), \qquad \rho([\gamma]) = T_\gamma|_R. \tag{18}$$

Is ρ a representation? We ran it. Composition holds exactly, on every state and hence on R: T_(γ₁γ₂) =
T_(γ₂) ∘ T_(γ₁), because the transport is literally built as a composition of legs. So ρ is a monoid
homomorphism. But the inverse axiom fails on R — T_(γ⁻¹) ∘ T_γ ≠ id on core(γ), and T_(γ⁻¹) does not
even preserve it — and this persists on the core, so it is not contamination from transient trees.
Worse, the codomain is not well-defined: |R| takes values 6, 8, 10, 12, 16 across six loops, and the
intersection of all six cores is two states out of 1024. There is no single R for π₁ to act on.

So there is no character on π₁, and the twisted zeta has nothing to twist by. The strand closes — and it
closes not on a defect of the attempt but on the repository's central open problem, O1: is the stable
quotient presentation-independent? Transport monodromy needs a canonical core. Canonicity is exactly
what we do not have.

### Coda: the discipline is the mathematics

Notice what happened across those last four sections. A seductive idea arrived (zeta separates what the
ledger cannot), a witness killed it, a positive control kept the negative from being vacuous, the domain
was located, a decorated version was proposed, and its premise — an earned gain — was shown absent. Each
step produced a statement with a stated warrant, and several of the outputs were negative: a projection
is not injective, an invariant is identically zero, a family is blind, a homomorphism is not a
representation.

That is the actual mathematical content of this system, and it is why the code carries its own ledger.
Every claim is labelled proved, computed, negative, open, or conjecture; negatives state their search
bounds ("none among the 216 tested," never "none exists"); and quantities that depend on the
presentation say so. This is not modesty. It is a theorem about finite observation — no finite prefix
determines a limsup — applied to the software's own output.

The open problems are few and sharp. O1 asks whether a presentation-independent fibre exists; everything
about phases and monodromy is blocked behind it. O3 asks whether any finite augmentation makes the
dynamics invertible, and the collision theorem says any such augmentation must separate states at the
attractor. And a pattern — that survival, to a horizon or under iteration, is the condition under which
canonical structure exists — is recorded as a conjecture, because the two decompositions are of
different objects and no common construction has been exhibited.

The instrument compresses a search into a curve of waste, locates where the waste begins, and is
explicit about which of its numbers are allowed to say what. That last property is not decoration on top
of the mathematics. It is the mathematics.
