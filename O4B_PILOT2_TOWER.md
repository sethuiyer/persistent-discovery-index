# O4B_PILOT2_TOWER.md — diagnostic tower proposal (DRAFT, NOT FROZEN)

> **Superseded** by [`O4B_FREEZE_PROPOSAL.md`](O4B_FREEZE_PROPOSAL.md); kept as history.

Companion to [`O4B_PREDECLARATION_PILOT2.md`](O4B_PREDECLARATION_PILOT2.md) §3.
The tower localises **cost variation**; it is not a waste measure. Levels are small
and cumulative. All categories are **proposed** until frozen.

**The statistic's synthetic audit establishes algebraic correctness. It does not
establish useful localisation.**

## 1. Levels and mechanical extraction rules

Features are extracted from trace events only. **Excluded absolutely:** unique
paths, IDs, outcomes (terminal or verified), cost, tokens, and any deterministic
encoding of these. `[FIX BEFORE RUN]` the declared tool sets.

| level | feature (categories) | extraction rule (mechanical) | missing-data handling |
|---|---|---|---|
| **0** | trivial root | one block | — |
| **1** | **search mode:** `none` / `targeted` / `broad` | search events = declared search tools (`grep, glob, search, find, websearch`) or a bash first-token in `{grep, rg, find, fd, ls, ag}`. Let `S` = count. `broad` if `S ≥ 2` **or** any search scope argument contains a wildcard (`*`) or an unbounded root (`/`, empty). `targeted` if `S == 1` and not broad. `none` if `S == 0`. | unparseable search args → **`broad`** (an unreadable scope is not evidence of targeting) |
| **2** | **read scope:** `none` / `bounded` / `whole-file-or-mixed` | read events = family `read`, or bash first-token in `{cat, head, tail, sed, less, more}`. A read is `bounded` iff its args declare a range (`offset/limit/start/end/line`) or the command uses `head`/`tail`/`sed` with a range; otherwise `whole`. `none` if no reads; `bounded` if all bounded; `whole-file-or-mixed` if any whole read or both kinds occur. | unparseable read args → **`whole`** (conservative) |
| **3** | **recovery:** `none` / `retry` / `revised approach` | error events = steps with non-null `error`. `none` if there are none. Otherwise take the **first** error and its **immediately following** step (same turn): `retry` if same tool **and** identical `canonical_args`; else `revised approach`; if there is no following step → `none`. | error field absent for all steps → `none`; unparseable following step → **`revised approach`** (conservative) |

Precedence and tie rules are fixed above (first error only; conservative mapping of
unparseable data). No level reads any label or the observable.

## 2. Feature → extraction rule → intervention candidate

Every candidate lives inside the frozen knob manifest (pilot-2 §5): a candidate
changes **agent policy**, never task information.

| level | extraction (recap) | intervention candidate class | forbidden |
|---|---|---|---|
| 1 | search mode (count + scope breadth) | **search-scoping guidance**: prefer one targeted search; avoid wildcard/root-wide patterns | disclosing where the defect is; adding search tools |
| 2 | read scope (range-bounded vs whole) | **read-scoping guidance**: prefer bounded ranges; avoid whole-file reads when a range suffices | naming the failing file/test; adding tools |
| 3 | recovery after the first error (retry vs revise) | **recovery-policy instruction**: on error, revise the approach rather than repeating an identical call | task-specific retry recipes; solution hints |

Both selectors P and H draw candidates from this same table, with the same budget.

## 3. Support bounds (distinct tasks, not runs)

**Support is counted in DISTINCT TASKS per block.** Several runs from one task do
**not** establish generalisation, so:

- a block is **supported** iff it contains runs from `≥ k_tasks` distinct tasks;
- a level's **support** = fraction of eligible runs sitting in supported blocks;
- a level is **admissible** iff it has `≥ min_blocks` blocks **and** its support
  `≥ support_frac`.

Proposed defaults, all `[FIX BEFORE RUN]`: `k_tasks = 2`, `support_frac = 0.5`,
`min_blocks = 2`. Consequences, both intended:

- a **discrete** level has support `0` → inadmissible;
- a level that merely **separates the tasks** also has support `0` → inadmissible.

Implemented in [`o4b_cost.py`](o4b_cost.py); pinned by `test_o4b_cost.py`.

## 4. Stated limitation — what centring hides

Within-task centring measures **run-to-run cost variation**. A behaviour that is
**consistently expensive on every repetition of every task** — the same overhead
present in all runs — is largely removed by centring and can **vanish from this
signal**. This is a deliberate property of the diagnostic (it isolates variation,
not level), and it means a well-supported share is evidence about *variation*,
never a complete account of cost.

## 5. Remaining numeric choices (settle in one review)

| # | choice | proposed default |
|---|---|---|
| 1 | `k_tasks` (distinct tasks per supported block) | 2 |
| 2 | `support_frac` | 0.5 |
| 3 | `min_blocks` | 2 |
| 4 | `R_min` (priced runs per task) | 2 |
| 5 | `s_min` (P's share threshold) | `[FIX BEFORE RUN]` |
| 6 | `K` (discovery tasks a level must appear in) | `[FIX BEFORE RUN]` |
| 7 | `N_cand` (candidate budget per selector) | `[FIX BEFORE RUN]` |
| 8 | H: overlapping-cost handling | `[FIX BEFORE RUN]` |
| 9 | H: abstention threshold | `[FIX BEFORE RUN]` |
| 10 | `R` runs/task/arm; `δ`; split seed; model | `[FIX BEFORE RUN]` |
| 11 | module-size line bands (covariate); module → side assignment | `[FIX BEFORE RUN]` |
| 12 | declared tool sets (§1) | `[FIX BEFORE RUN]` |
