# PDI — one page, four numbers

| # | claim | the number |
|---|---|---|
| 1 | same solutions, wildly different work | **23,232 nodes vs 169 nodes** |
| 2 | the waste is localised, not diffuse | **76.2% of the naive search sits in depths 21–30** |
| 3 | peak inflation against the informed strategy | **627× at depth 27** |
| 4 | it runs before you finish reading this | **65 ms, zero dependencies** |

> **We built a 65 ms zero-dependency profiler that tells you where your agent stops
> deducing and starts guessing.**

---

## What those numbers are

Two Sudoku puzzles, three strategies, the same two solutions. `first/asc` explores
23,232 nodes; `mrv/asc` explores 169. That is **137×**, and it is invisible to any
dashboard that reports success rate, because both succeed.

But the total is the boring part. The interesting part is *where* the work went:

```text
strategy            total nodes   backtracks
first/asc                23,232       23,231
first/random              3,992        3,991
mrv/asc                     169           63      <- 137x fewer
```

**76.2% of `first/asc`'s entire search sits in depths 21–30.** That band is where it
stops deducing and starts guessing. MRV never enters that regime — its visits are
spread evenly across the whole depth range, because it never has a cell with many
candidates to guess from. At depth 27 the naive solver is generating **627×** the
search structure of MRV for the same solutions.

The instrument does not just report a total. It reports the *shape* of the waste and
the resolution at which it starts.

## What it is, in two lines

Two ledgers, never merged:

| ledger | symbol | meaning |
|---|---|---|
| **exploration** | `n_j` | everything the agent tried, at behavioural resolution `j` |
| **persistent** | `L_j` | what actually led somewhere useful |

Every existing tool conflates these, or throws the first one away. DFA minimisation
trims the transient. So does bisimulation. So does every cache. **PDI keeps both**,
because the ratio between them is the measurement — and because the level at which
the ratio collapses is a fact about your agent you cannot recover after deleting it.

## Run it

```bash
git clone https://github.com/sethuiyer/persistent-discovery-index
cd persistent-discovery-index
python3 pdi_profile.py --demo            # 65 ms, no data needed
python3 pdi_profile.py your-traces/      # pi, OpenAI, LangSmith, OTel, AutoGen, CrewAI
python3 dashboard.py your-traces/        # self-contained offline HTML
```

No install. No API key. No service. No third-party dependency — stdlib only, MIT.
`git clone` and `python3` is the entire onboarding.

## What these numbers do **not** say

This is the part most tools leave out, so it is printed on the artefact:

- The numbers are **descriptive of the corpus in hand**. There is no reference
  distribution yet, so PDI will not tell you your agent is "bad" in absolute terms.
  It tells you where *this* agent's waste starts, relative to *another strategy on
  the same task*.
- `Δ` is **presentation-dependent** by construction. It is a legitimate algorithm
  comparison only when the task is held fixed. Comparing `Δ` across tasks is
  meaningless, and the tool says so.
- On the Sudoku example above, the asymptotic summaries `D` and `S` both take their
  supremum at depth 1 — they order the strategies correctly but measure first-cell
  branching, not search size. **The per-depth profile is the instrument here.** The
  software flags this itself rather than letting you over-read a number.
- Every claim in the mathematics carries an explicit status — `proved`, `computed`,
  `negative`, `open`, `conjecture` — in [`SPINE.md`](SPINE.md) §0. Negative results
  are outputs, not failures, and they state their search bounds.

> **Give away the instrument. Sell the laboratory.**

## Where to go next

| | |
|---|---|
| the instrument, in five minutes | [`README.md`](README.md) |
| every claim and its warrant | [`SPINE.md`](SPINE.md) — start at §0 |
| the whole mathematics, in one narrative | [`MATH.md`](MATH.md) |
| the whole chain, on video | [The Hidden Cost of AI Discovery](https://www.youtube.com/watch?v=tkPmvU6x_bc) |
| the whole chain, as a blog post | [The Persistent Discovery Index](https://gist.github.com/shunyabarlabs/ec39c0ad4ee105d283a914b7b0a99aed) |
| positioning and market hypothesis | [`PRODUCT_README.md`](PRODUCT_README.md) |
| the numbers behind this page | `python3 demo_sudoku.py`, `python3 test_sudoku.py` |

---

*This file is a pitch, not a warrant. Every number above is reproducible from the
repository; the claims they support are licensed in [`SPINE.md`](SPINE.md). If a
statement here conflicts with the ledger, the ledger wins.*
