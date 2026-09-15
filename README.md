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
