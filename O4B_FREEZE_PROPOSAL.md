# O4B_FREEZE_PROPOSAL.md — ONE consolidated proposal (DRAFT, NOT FROZEN)

**Status: UNFROZEN.** One review, then freeze and execute. This supersedes
[`O4B_PILOT2_DESIGN.md`](O4B_PILOT2_DESIGN.md) and
[`O4B_PILOT2_TOWER.md`](O4B_PILOT2_TOWER.md), which become historical.
Pilot 1 closed as **C** ([`O4B_PILOT1_RESULT.md`](O4B_PILOT1_RESULT.md)).
Ruler: [`o4b_stat.py`](o4b_stat.py). Cost statistic: [`o4b_cost.py`](o4b_cost.py).

## 1. Value-add question

> Does **PDI localisation** reduce cost at non-inferior verified success **more than
> ordinary success-and-cost guidance**? A P-vs-baseline win alone is insufficient;
> the claim needs the **(P − H)** contrast.

## 2. Difficulty — structural challenge bands

Axes (mechanical): **mutation count** (one / two composed), **dependency span** (one
function / declared call edge), **module size** (line bands, a **covariate**).

| band | construction | target per side |
|---|---|---|
| A | one defect, one function | 4 |
| B | one defect at a declared call edge | 4 |
| C | **two composed defects across a declared call edge** | 4 |

Band C requires: clean PASS; each mutation **alone** FAIL; combined FAIL; cancelling
pairs rejected. **Band C claims composition across an edge, not demonstrated
interaction.**

### 2.1 Module allocation (fixed before construction)

The 21 production modules with dedicated verifiers: `pdi, quotient_tower, adapters,
ingest, multiresolution, cofinal_mesh, transport, stable_quotient,
collision_mechanism, both_structures, one_question, invariance_first,
proof_awareness, prime_holonomy, survival_commutation, core_monodromy, o2_theorem,
invertibility, sudoku, agent_profiler, zeta_separation`.

- Sort, then shuffle with seed **`20260916`**: first **12 → discovery**, remaining
  **9 → held-out**. Sides are **cluster-disjoint**; a module's tasks all stay on its
  side.
- A module may host **at most 2 tasks**, in **distinct functions** (distinct call
  edges for band C).
- Targets are **4 per band per side (24 total)**.

### 2.2 Quota shortfall (declared)

Targets are targets, not entitlements. After exhausting a side's modules under the
rules, an unmet cell is **recorded as a shortfall**; that cell's count is reduced.
**Never** relax a construction rule, move a module across sides, or reuse a
function. If constructible **held-out < 6**, the pilot is reported as **D** without
held-out execution.

## 3. Diagnostic tower — parsing uncertainty is `unknown`

Small, cumulative. **Excluded as features:** unique paths, IDs, terminal/verified
outcomes, **cost, tokens, and any deterministic encoding of these**.

**Exact tool recognition** (`[FIX]` the sets): `SEARCH_TOOLS = {grep, glob, search,
find, websearch}`, `BASH_SEARCH_FIRST = {grep, rg, find, fd, ls, ag, ack}`;
`READ_TOOLS = {read, view_file, read_file}`, `BASH_READ_FIRST = {cat, head, tail,
sed, less, more, nl}`.

| level | categories | extraction |
|---|---|---|
| 0 | — | trivial root |
| 1 search mode | `none` / `targeted` / `broad` / **`unknown`** | `S` = search events. `broad` if `S ≥ 2` or any scope contains `*` / is `/` / empty. `targeted` if `S == 1` and not broad. `none` if `S == 0`. **`unknown` if any search event's args do not parse.** |
| 2 read scope | `none` / `bounded` / `whole-file-or-mixed` / **`unknown`** | `none` if no reads; `bounded` if every read declares a range (`offset/limit/start/end/line`); else `whole-file-or-mixed`. **`unknown` if any read args do not parse.** |
| 3 recovery | `none` / `retry` / `changed-action` / `unresolved` / **`unknown`** | `none` if no errors. Else first error and the **immediately following** step same run: same tool **and** identical `canonical_args` → `retry`; a different tool **or** different args → **`changed-action`**; **no following step → `unresolved`**. **`unknown` if the error or the next step does not parse.** |

**Parsing uncertainty is `unknown`, never a behavioural category** — otherwise
parser failures become apparent signal. `changed-action` asserts a *changed action*,
**not** a revised recovery strategy.

## 4. Cost-variation statistic (implemented, audited)

Equal weight **per task**, split across its eligible priced runs (measure `μ`);
cost **centred within task** with the same `μ`; `E_j = ‖D_j c‖²`; residual
`‖c − P_J c‖²`; shares `s_j = E_j / (Σ E_j + residual)`; **zero denominator →
abstain** (never 0); a task with `< R_min` priced runs is excluded and counted.

**Support uses `μ`** (not raw runs): a block is *supported* iff it holds runs from
`≥ k_tasks` distinct tasks; a level's support is the **μ-mass** of its supported
blocks; admissible iff `≥ min_blocks` blocks and support `≥ support_frac`.

**Stated limitation:** centring measures **run-to-run** variation, so a behaviour
consistently expensive on *every* repetition can vanish. The audit establishes
**algebraic correctness, not useful localisation.**

## 5. Selectors P and H — same candidates, same budget

Candidate refinements are the three tower levels; refinement `j` maps to the
feature at level `j+1` and to its template.

**P (PDI).** On discovery only: select the admissible refinement maximising the
median `s_j` across discovery tasks, subject to `s_{L*} ≥ s_min` and presence in
`≥ K` tasks. Abstains → **C**.

**H (ordinary guidance).** Rank the **same three refinements** by the **mean
allocated cost of the events that refinement targets** — refinement 1 → search
events, 2 → read events, 3 → error/recovery events — with the **same `μ`**.
Attribution is frozen: **an assistant message's `usage` is split equally across the
tool calls that message issued** (captures carry **no per-event cost**; labelled an
assumption). Candidates may overlap; each refinement is scored **independently**,
no double-counting correction. H abstains under its own threshold.

**Shared:** tie-break coarser-first; budget `N_cand`; abstention → **C**, never
descend.

### 5.1 Fixed intervention templates (identical for P and H)

| level | template |
|---|---|
| 1 search | "When searching, prefer a single targeted search with a specific pattern and a bounded directory; avoid wildcard or root-wide searches unless a targeted search has already failed." |
| 2 read | "When reading files, prefer a bounded range (offset/limit); read a whole file only when a bounded range is insufficient." |
| 3 recovery | "If a tool or command fails, change the approach rather than repeating the identical call." |

**Forbidden in every arm:** adding tools/MCP, changing the model, disclosing the
failing test or the defect location, task-specific step lists or retry recipes.

## 6. Evaluation

Arms **baseline / P-selected / H-selected** on **identical held-out tasks**,
matched budgets and runs, independent verification for all arms. Primary:
`(P − baseline)` cost at non-inferior verified success, via `o4b_stat.py`
(`D*₅ ≥ −δ`, `Δ*₉₅ < 0`, `n_both < 6 → D`). The **(P − H)** contrast is reported in
every outcome. Outcomes **A/B/C/D** as in pilot 1; C = abstention, D = inconclusive.

## 7. Artifacts and missing data

Per run: `task_id`, `arm`, `run_index`, **full trace path**, steps, terminal outcome,
`verified_outcome` + evaluator provenance, cost, tokens, model, commit, corpus
fingerprint. Missing **cost** → task cost-ineligible (counted); task with `< R_min`
priced runs → excluded (counted); missing **trace** → run ineligible (counted);
**UNKNOWN** → out of the success denominator, counted; **no silent drops, no
reruns**; every scheduled run recorded including crashes and timeouts.

## 8. All remaining parameters (proposed)

| # | parameter | proposed |
|---|---|---|
| 1 | `k_tasks` / `support_frac` / `min_blocks` | 2 / 0.5 / 2 |
| 2 | `R_min` | 2 |
| 3 | `s_min` | 0.10 |
| 4 | `K` (discovery tasks a level must appear in) | 3 |
| 5 | `N_cand` (per selector) | 1 |
| 6 | H abstention threshold | top refinement must exceed the runner-up by ≥ 10% |
| 7 | H overlapping-cost handling | score each refinement independently; no correction |
| 8 | `R` runs / task / arm | 2 |
| 9 | `δ` | 0.10 |
| 10 | split seed | 20260916 |
| 11 | model / agent | `pi --mode rpc`, `deepseek-flash` |
| 12 | module-size line bands (covariate) | ≤200 / 201–500 / >500 |
| 13 | module allocation | §2.1 (seeded 12 / 9) |
| 14 | tool sets | §3 |
| 15 | band targets | 4 per band per side; §2.2 on shortfall |

## 9. Non-negotiables

Cost variation ≠ waste ≠ savings. No task chosen because an agent failed it. No
held-out inspection before both interventions are committed. No post-hoc
reclassification of B/C/D. If P abstains → **C**.
