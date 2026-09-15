# Persistent Discovery Index (PDI)

A multiresolution quotient tree over histories, with **two deliberately separate
information channels**:

| ledger | symbol | meaning |
|---|---|---|
| persistent | `L_j` | what survived to the observation horizon |
| exploration | `n_j` | what was explored getting there |

This is not a design preference. It is enforced by a theorem:

```
D     = limsup_j log L_j / (-log eps_j)   intrinsic, cofinal-invariant
S     = limsup_j log n_j / (-log eps_j)   presentation-dependent
Delta = S - D                             discovery overhead, presentation-dependent
```

`L` is a **covering count** — it answers a question about the boundary, so it is a
function of physical scale and cannot be moved by reindexing the tower. `n` is
not a covering count: dead-end nodes cover nothing, so `n_j` is only a
shell-indexed sequence, and a cofinal restriction may sample a different subshell
of it. `Delta` mixes the two and inherits the shell sequence's dependence.

The distinction is classical elsewhere — coaccessible vs all states in automata,
essential vs transient in sofic shifts, where entropy is a function of the
essential part only (Lind–Marcus).

## ⚠️ Evaluation caveat: finite horizons can hide `Delta`

The non-invariance of `Delta = S - D` is real, but it can be **invisible at small
horizons** — and this repository's own demo is the example.

| horizon | spike lands on | even-only reindexing | `Delta` test |
|---|---|---|---|
| `H = 8` | level 7 (odd) | `Delta` 0.720628 -> 0.681244 | correctly **fails** |
| `H = 7` | level 6 (even) | `Delta` unchanged | **passes spuriously** |

At `H = 7` the transient-growth spike sits on an even level, so reindexing to even
levels happens to agree and a test asserting non-invariance passes for the wrong
reason. The effect only appears when the sampled horizon actually contains the
transient-growth subsequence.

**Consequence for benchmarking.** A single finite window that misses that
subsequence will report `Delta` as though it were an invariant. Any claim of the
form *"agent X explores less than agent Y"* must therefore either (a) state the
horizon, or (b) be backed by a **growth-rate estimate** rather than a point
measurement. `D` does not have this problem; `Delta` does.

This is not a defect of the implementation. It is the theorem showing up in
evaluation design: an intrinsic quantity (`D`) survives a bad window, a
presentation-dependent one (`Delta`) does not.

## Design rules

1. **Never collapse the two ledgers into one counter.** They measure different things.
2. **`LIVE` is horizon-relative.** At a fixed horizon it is monotone under additive
   insertion and `L_j <= L_{j+1}`. When the horizon grows, previously-live nodes can
   be demoted — so `TRANSIENT` is "dead given the data so far", never final.
3. **`UNKNOWN` is a theorem, not a fallback.** Deciding live-vs-dead is the
   stabilisation problem and is undecidable in general. A streaming index cannot
   promise stable classification.
4. **STOP is decided on physical resolution, not tree depth.** Depth is an
   implementation coordinate.

## Run

```bash
python3 demo.py
```

Output: two agents reaching an **identical** persistent ledger but with different
exploration cost, then the reindexing test.

```
Agent A  (clean discovery)      D=1.000000  S=1.000000  Delta=0.000000
Agent B  (heavy transient)      D=1.000000  S=1.720628  Delta=0.720628
  identical persistent ledgers L_j : True
  same D                           : True
  different Delta                  : True

cofinal reindexing (even levels only):
  Agent B  D=1.000000  S=1.681244  Delta=0.681244
  -> D invariant: True    Delta invariant: False
```

"Same geometry, different computational stupidity" — and the theorem guarantees
it is well-defined, because `D` is held fixed while `Delta` varies.

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

## Status and scope

**Research prototype, v0.1.0.** The claims are exactly the ones the demo and the
self-checks enforce — no more.

What is honest about the scope:

- The tree is a labelled trie with the behavioural quotient applied by the label
  map. Resolution-dependent quotient towers — refining the quotient *per level*,
  not just lengthening the prefix — are the next milestone and are **not**
  implemented. That step is what makes this more than a trie with accounting.
- `recompute_statuses()` is the authoritative batch classifier; `mark_live()` is
  the incremental version, sound at a fixed horizon. `TRANSIENT` is horizon-relative
  and revisable, never final.
- GC policy, persistence-based eviction, and retrieval quality are specified in
  the design and **not** implemented here.

**What the prototype does demonstrate:** that the two ledgers can be maintained
independently, that `L_j` stays non-decreasing, that `D` is unchanged by cofinal
reindexing while `Delta` is not, that adaptive resolution plus node caching gives a
working hierarchical reuse path, and that two agents reaching an identical
persistent ledger can differ measurably in discovery overhead.

## References

- `concepts/cofinal-invariance` — gauge-dependence of raw exponents, Cauchy–Hadamard, `Delta` non-invariance
- `concepts/regular-growth-identification` — full vs live counts; why `q_c = 1-2^{-dim_B}` is conditional
- `concepts/resolution-stop` — the frozen quotient → completion → observer triple
- Lind & Marcus, *An Introduction to Symbolic Dynamics and Coding* — entropy from the essential part
