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

## What v0.1.0 implements

- Separate `n_j` / `L_j` ledgers, maintained independently at every level.
- `LIVE` / `TRANSIENT` / `UNKNOWN` node state with coaccessibility propagation
  (`mark_live`) and an authoritative batch classifier (`recompute_statuses`).
- Adaptive STOP keyed on physical resolution, discounted by the observed persistent
  yield ratio `L_j / n_j`.
- Node-level caching with hierarchical reuse (`lookup_or_refine`).
- Invariant checks (`live_non_decreasing`) and **15 passing self-checks**, including
  cofinal invariance of `D`, non-invariance of `Delta`, and the two-agent result.

The substrate is a labelled trie, with the behavioural quotient applied by the label
map. The behavioural abstraction — resolution as a first-class coordinate, and the
persistent/transient split — is what the structure *is*; the substrate is an
implementation choice.

## Roadmap

- **Resolution-dependent quotient towers** — refine the quotient *per level* rather
  than only lengthening the prefix. This is the next implementation milestone.
- **Persistence-based garbage collection** — eviction driven by the `L`/`n` split
  (retain, compress, summarise, prune) instead of recency alone.
- **Retrieval-quality evaluation** — end-to-end indexing and query benchmarks.

## References

- `concepts/cofinal-invariance` — gauge-dependence of raw exponents, Cauchy–Hadamard, `Delta` non-invariance
- `concepts/regular-growth-identification` — full vs live counts; why `q_c = 1-2^{-dim_B}` is conditional
- `concepts/resolution-stop` — the quotient → completion → observer triple
- Lind & Marcus, *An Introduction to Symbolic Dynamics and Coding* — entropy from the essential part
