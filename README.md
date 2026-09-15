# Persistent Discovery Index (PDI)

**Persistent Discovery Index is a multiresolution data structure that separates what
a system discovers persistently from the transient exploration structure generated
while discovering it.**

It maintains two deliberately separate information channels at every resolution level:

| ledger | symbol | meaning |
|---|---|---|
| **persistent** | `L_j` | what survived to the observation horizon |
| **exploration** | `n_j` | what was explored getting there |

> ### Same geometry. Different discovery cost.

## The invariant

The separation is not a design preference. It is a theorem:

```
D     = limsup_j log L_j / (-log eps_j)   intrinsic, cofinal-invariant
S     = limsup_j log n_j / (-log eps_j)   presentation-dependent
Delta = S - D                             discovery overhead, presentation-dependent
```

`L` is a **covering count** — it answers a question about the boundary, so it is a
function of *physical resolution* and cannot be moved by reindexing the tower. That
is **cofinal invariance of the physical-scale live dimension**, and it is proved:
using `eps_j` instead of the level index removes the arbitrary depth
parametrisation that makes raw level-indexed quantities gauge-dependent.

`n` is not a covering count. Dead-end nodes cover nothing, so `n_j` is only a
shell-indexed sequence, and a cofinal restriction may sample a different subshell of
it.

`Delta = S - D >= 0` because `L_j <= n_j` for every `j`. Two consequences follow
directly:

- **The gap is not canonicity-open.** `Delta` is *refuted* as a cofinal invariant by
  an explicit realizable counterexample: `L_j = 2^j` with `n_j = 4^j` on odd shells
  and `2^j` on even shells gives `Delta = 1` for `P` and `Delta = 0` for `P' = P_{2j}`
  — same boundary, same `D`, different overhead.
- **`Delta` is invariant when both exponents converge** (regular variation), because
  a limit is subsequence-invariant.

The distinction is classical elsewhere — coaccessible vs all states in automata,
essential vs transient in sofic shifts, where entropy is a function of the essential
part only (Lind–Marcus). PDI is the data structure that keeps both.

## Demonstrated

Two agents reach an **identical** persistent ledger. Only the exploration ledger
differs:

| | `D` | `S` | `Delta` |
|---|---:|---:|---:|
| Agent A (clean discovery) | 1.000000 | 1.000000 | 0.000000 |
| Agent B (heavy transient branching) | **1.000000** | 1.720628 | **0.720628** |

```
identical persistent ledgers L_j : True
same D                           : True
different S                      : True
different Delta                  : True
```

**Same geometry. Different discovery cost.** `D` is held fixed while `Delta` varies,
so the comparison is well-defined by construction rather than by convention.

And the counterexample bites on a real tree — even-only reindexing leaves `D` alone
and moves `Delta`:

```
Agent B   full presentation : D=1.000000  Delta=0.720628
          reindexed (even)  : D=1.000000  Delta=0.681244
          -> D invariant: True    Delta invariant: False
```

## Behavioural resolution towers (v0.3.0)

Up to v0.2.0 the level index was **path length**: level *j* held length-*j* prefixes,
and `n_j` counted them. That is a trie.

v0.3.0 changes what resolution *means*. The level index is now a **behavioural
resolution**, and the levels form a genuine refinement tower of quotient maps
`Q_j : H → X_j = H / ~_j`:

```python
tower = QuotientTower([
    lambda h: reached_goal(h),                    # Q1  two classes
    lambda h: (reached_goal(h), steps(h)),        # Q2  + step count
    lambda h: (reached_goal(h), multiset(h)),     # Q3  + move multiset
    lambda h: (reached_goal(h), move_seq(h)),     # Q4  + move sequence
    lambda h: (reached_goal(h), tuple(h)),        # Q5  + full path
])

idx = PDI(tower=tower)
idx.fit(runs)              # validates the refinement law, then inserts
```

The required **refinement law** is checked, not assumed:

```
Q_{j+1}(h) = Q_{j+1}(h')   =>   Q_j(h) = Q_j(h')
```

`QuotientTower.validate()` raises `TowerViolation` on the first finer class that
straddles two coarser ones, and `validate_pairs()` does the exhaustive
`O(|H|²)` version for small corpora. With the law enforced, each level-(j+1) class
has a unique level-*j* parent, so the classes still form a tree — but now

```
n_j = |H / ~_j|        exactly the behavioural class count
L_j = number of resolution-j classes containing a persistent history
```

which is the construction the invariant was always stated over. Verified: for every
level, the PDI's `n_j` equals `|H / ~_j|` computed independently from the corpus.

### The sharper diagnostic

With behavioural levels, an absolute yield threshold is a poor guide at coarse
resolutions. The informative quantity is **class inflation against a reference**:

```
class inflation relative to 'shortest_only'   (n_j / n_j_reference)
agent             Q1      Q2      Q3      Q4      Q5
shortest_only  1.00x   1.00x   1.00x   1.00x   1.00x
slack_2        1.00x   1.09x   2.44x   3.49x   3.49x
unpruned       1.00x   1.09x   5.89x   7.35x   7.35x

distinction onset: at resolution 3 (Q3 + move multiset), 'slack_2' first exceeds 2x
```

That is the v0.3.0 product, and it is a strictly stronger statement than v0.2.0
could make: **the profiler names the behavioural resolution at which a strategy
starts manufacturing distinctions that do not contribute to successful behaviour.**

```bash
python3 demo_tower.py      # the behavioural tower, laws and tables above
python3 test_tower.py      # 11 self-checks incl. rejection of invalid towers
```

## Real agent traces (v0.4.0)

`adapters.py` reads the **actual session transcripts** written by the pi agent
harness — JSONL event streams with `toolCall` blocks and matching `toolResult`
records — and reconstructs runs. A *run* is one user turn: the ordered tool calls
between one user message and the next, with the terminal `stopReason` of the last
assistant message as the outcome.

Nothing here is synthetic:

```
real traces from ~/.pi/agent/sessions
  turns     : 1456
  tool calls: 14422   errors: 830 (5.8%)
  terminal success (stopReason=='stop'): 1204/1456 (82.7%)
  models    : 10
```

The tower is explicit and structurally nested, so the refinement law holds by
construction rather than by luck:

```
Q1  terminal outcome
Q2  + tool-family multiset
Q3  + tool-family sequence
Q4  + per-step error classes
Q5  + normalised argument classes
Q6  + full normalised trace
```

```bash
python3 diagnose_agents.py navokoj          # per-model, one project
python3 diagnose_agents.py --all            # every project
python3 diagnose_agents.py --all --matched  # only prompts >=2 models actually ran
```

On the `navokoj` project, four models ran enough turns to profile:

```
agent                                              D         S     Delta    waste
MiniMax-M3                                  2.863960  3.142701  0.278741     8.9%
deepseek-flash                              2.377444  2.543731  0.166288     6.5%
z-ai/glm-5.3                                1.850220  2.160964  0.310744    14.4%
huihui-ai/Huihui-Qwen3.8-27B-abliterated    1.953445  2.084963  0.131517     6.3%

persistent structure differs across agents: D in [1.850220, 2.863960]
-> agents did not all find the same structure; compare with care
```

### What this pass actually established

**The adapter works and the tool diagnoses real agents.** 14,422 real tool calls
reconstructed, the refinement law verified over the whole corpus, the yield and
inflation tables produced from live data.

**But personal session logs are not a controlled corpus, and the tool says so.**
`D` differs across models because they were doing different work, so the
per-model comparison is *descriptive*, not experimental. The profiler prints that
warning itself rather than hiding it:

> `agents did not all find the same structure; compare with care`

`--matched` restricts to opening prompts that at least two models actually ran,
which controls for the task. On this corpus that leaves **27 of 1104 turns across
7 shared prompts** — enough to demonstrate the mechanism, far too little to draw
conclusions. That is the honest state of the evidence, and it defines the
prerequisite for the next experiment:

> **A task corpus with repeated tasks per agent.** The profiler is ready; the
> corpus is what is missing. Session logs accumulate whatever work happened to
> occur, which is exactly the confound the `--matched` flag exists to remove.

## Use case: agent reasoning profiler

`agent_profiler.py` turns the distinction into a measurement. Give it agent runs —
a path of abstracted states plus whether the run succeeded — and it reports, per
resolution level:

```
level       eps      full     live    yield
    6   0.01562        60       32   53.33%
    8   0.00391       350      112   32.00%
   10   0.00098      1774      252   14.21%
   11   0.00049      3624      252    6.95%
D = 0.850919   S = 1.079279   Delta = 0.228360
```

Because the task fixes the persistent structure and the algorithm supplies the
transient exploration, the same table is an **algorithm comparison**:

```
agent                   D         S     Delta    waste  STOP at
shortest_only    0.850919  0.850919  0.000000     0.0%        -
admissible       0.850919  0.850919  0.000000     0.0%        -
slack_1          0.850919  0.850919  0.000000     0.0%        -
slack_2          0.850919  1.010933  0.160013    15.8%        -
unpruned         0.850919  1.079279  0.228360    21.2%       11
```

Five strategies, one task (find every shortest path on a 6x6 grid), identical
persistent structure `D`, and a clean ordering of discovery overhead. **Presentation
dependence is not a defect here** — it is precisely what makes `Delta` comparable
across algorithms. The task supplies the geometry; the algorithm supplies the waste.

The `STOP at` column is the profiler's other product. Persistent yield collapsing
toward zero says: *finer than this, the strategy is generating exploration, not
knowledge.* Point the same table at ReAct vs beam search vs MCTS, or at prompt,
temperature and tool-policy variants, and it is a measurement rather than an
opinion — the output of the earlier invariant, applied to real agent logs.

```bash
python3 demo_agents.py     # the benchmark table above
python3 test_profiler.py   # 15 self-checks on the profiler
```

## Evaluation requirement: horizons must span the transient-growth subsequence

The non-invariance of `Delta` is real but can be **invisible at short horizons** —
and this repository's own tests are the example.

| horizon | spike lands on | even-only reindexing | `Delta` test |
|---|---|---|---|
| `H = 8` | level 7 (odd) | `Delta` 0.720628 -> 0.681244 | correctly **fails** |
| `H = 7` | level 6 (even) | `Delta` unchanged | **passes spuriously** |

At `H = 7` the transient-growth spike sits on an even level, so reindexing to even
levels happens to agree and a test asserting non-invariance passes for the wrong
reason.

**This is an evaluation requirement, not a caveat about PDI.** A single finite window
that misses the transient-growth subsequence will report `Delta` as though it were an
invariant. Any claim of the form *"agent X explores less than agent Y"* must therefore
either state the horizon, or be backed by a **growth-rate estimate** rather than a
point measurement. `D` is unaffected — an intrinsic quantity survives a badly chosen
window; a presentation-dependent one does not. That is the theorem appearing in
evaluation design.

## Design rules

1. **Never collapse the two ledgers into one counter.** They measure different things.
2. **`LIVE` is horizon-relative.** At a fixed horizon it is monotone under additive
   insertion and `L_j <= L_{j+1}` (the map `live(j) -> live(j+1)` selecting a
   horizon-reaching child is injective). When the horizon grows, previously-live nodes
   can be demoted — `TRANSIENT` means "dead given the data so far", never final.
3. **`UNKNOWN` is a theorem, not a fallback.** Deciding live-vs-dead is the
   stabilisation problem and is undecidable in general. A streaming index cannot
   promise stable classification.
4. **STOP is decided on physical resolution, not tree depth.** Depth is an
   implementation coordinate.

## Run

```bash
python3 demo.py        # two agents, same persistent ledger, different cost
python3 test_pdi.py    # 15 self-checks, all of the above asserted
```

## API

```python
from pdi import PDI, Status

idx = PDI(label=lambda action: action[0])   # behavioural quotient at resolution 0
idx.insert(trace)                           # descend by physical resolution
idx.recompute_statuses()                    # LIVE / TRANSIENT / UNKNOWN

idx.ledgers()             # (n_j, L_j)  -- two channels, never merged
idx.exponents()           # {'D', 'S', 'delta', 'horizon'}
idx.live_non_decreasing() # invariant check
idx.refine_worthwhile(j, gain, cost)        # R4: physical-resolution STOP
idx.lookup_or_refine(query, equivalent)     # hierarchical reuse; refine on miss
```

Nodes carry a `payload`, so the index doubles as a hierarchical semantic cache:
reuse at the coarsest resolution that is still equivalent, refine only on a miss.
This is where [FUTCache](https://github.com/sethuiyer/FUTCache) plugs in — FUTCache
asks *"is this state close to something already computed?"*; the PDI adds *"at what
resolution does it become meaningfully novel, and does that novelty persist?"*

## What is implemented

- Separate `n_j` / `L_j` ledgers, maintained independently at every level.
- **Behavioural resolution towers** (`quotient_tower.py`): `QuotientTower` with
  `validate()` / `validate_pairs()` enforcing the refinement law, plus
  `prefix_tower()` which expresses the v0.2.0 path-length indexing as a degenerate
  tower so earlier results stay reproducible.
- **Real trace adapter** (`adapters.py`): reads pi session JSONL transcripts,
  reconstructs turns with tool calls paired to results and errors attributed,
  and supplies the six-level tool tower. Verified on 14,422 real tool calls.
- `LIVE` / `TRANSIENT` / `UNKNOWN` node state with coaccessibility propagation
  (`mark_live`) and an authoritative batch classifier (`recompute_statuses`).
  Two live rules: horizon-reaching, or explicit (`insert(..., live=True)`).
- Adaptive STOP keyed on physical resolution, discounted by the observed persistent
  yield ratio `L_j / n_j`.
- Node-level caching with hierarchical reuse (`lookup_or_refine`).
- **Agent reasoning profiler** (`agent_profiler.py`): consumes agent runs, reports the
  per-resolution yield table, `D`, `S`, `Delta`, the STOP level, the
  `inflation_table()` distinction-onset diagnostic, and `compare()` for the
  cross-strategy benchmark.
- **`diagnose_agents.py`**: end-to-end diagnosis of real sessions, grouped by model,
  with `--matched` to control for the task.
- Invariant checks (`live_non_decreasing`) and **65 passing self-checks** across
  `test_pdi.py`, `test_profiler.py`, `test_tower.py` and `test_adapter.py`,
  including cofinal invariance of `D`, non-invariance of `Delta`, `n_j = |H / ~_j|`,
  rejection of invalid towers, and the refinement law over the full real corpus.

The substrate is a labelled trie, with the behavioural quotient applied by the label
map. The behavioural abstraction — resolution as a first-class coordinate, and the
persistent/transient split — is what the structure *is*; the substrate is an
implementation choice.

## Roadmap

- **A controlled task corpus** — the blocker for real conclusions. Repeated tasks per
  agent, so `--matched` has something to match on.
- **Persistence-based garbage collection** — eviction driven by the `L`/`n` split
  (retain, compress, summarise, prune) instead of recency alone.
- **Learned towers** — derive the behavioural levels from data while still enforcing
  the refinement law. Deliberately sequenced after the controlled corpus, so that a
  result can be attributed to the tower rather than to the learning algorithm.

## References

- `concepts/cofinal-invariance` — gauge-dependence of raw exponents, Cauchy–Hadamard, `Delta` non-invariance
- `concepts/regular-growth-identification` — full vs live counts; why `q_c = 1-2^{-dim_B}` is conditional
- `concepts/resolution-stop` — the quotient → completion → observer triple
- Lind & Marcus, *An Introduction to Symbolic Dynamics and Coding* — entropy from the essential part
