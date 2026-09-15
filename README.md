# Persistent Discovery Index (PDI)

**A microscope for agent behaviour. It shows where useful discovery ends and
unnecessary exploration begins — and at which behavioural resolution it happens.**

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
- **Multi-framework ingest** (`ingest.py`): canonical, pi, OpenAI, LangSmith, with
  autodetection, directory walking, and canonical round-trip export.
- **One-command profiler** (`pdi_profile.py`) for anyone's traces.
- `LIVE` / `TRANSIENT` / `UNKNOWN` node state with coaccessibility propagation;
  two live rules (horizon-reaching, or explicit).
- Adaptive STOP on physical resolution, discounted by the observed persistent yield.
- Node-level caching with hierarchical reuse.
- **Two output layers**: finite-scale diagnostics (exact) and asymptotic
  diagnostics (status-bearing).
- **Six self-checking suites**, including closed-form toy validation and the
  refinement law verified over a full real corpus.

## Roadmap

- **A controlled task corpus** — repeated tasks per agent. The blocker for real
  conclusions, not the software.
- **More ingest adapters** — CrewAI, AutoGen, OpenTelemetry GenAI spans. Each is one
  loader returning `list[Run]`.
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
