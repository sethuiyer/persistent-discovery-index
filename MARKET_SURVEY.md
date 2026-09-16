# MARKET_SURVEY.md — closest matches to PDI

> **Strategy, not a warrant.** This is a competitive survey, not a claim about PDI.
> Every external result quoted here is attributed to its source. If a statement
> conflicts with [`SPINE.md`](SPINE.md) about PDI itself, the ledger wins.

**Verified 2026-09-16** with TinyFish search/fetch against the papers and public
repositories below. I read the READMEs, the AgentSight abstract, and the ClawTrace /
Cost–Utility Alignment method and results sections — **not** every table or the full
source trees.

---

## 0. Method

Four questions asked of each tool: (1) does it analyse agent traces, (2) does it
connect behaviour to outcomes and cost, (3) does it locate inefficiency, (4) does it
test improvements? Sources: original papers, public repositories, official docs.

---

## 1. Study first: ClawTrace + CostCraft

**Repository:** <https://github.com/epsilla-cloud/clawtrace>
**Paper:** *ClawTrace: Cost-Aware Tracing for LLM Agent Skill Distillation*, arXiv
2604.23853 — <https://arxiv.org/html/2604.23853v1>

ClawTrace records agent execution and emits compact **TraceCards** (step costs, token
counts, expensive spans, suspected redundant calls). **CostCraft** turns those into
three kinds of instruction change:

- **Preserve** — keep useful behaviour.
- **Prune** — remove suspected unnecessary work, **including inside successful runs**.
- **Repair** — address failures using evaluator evidence.

That is the same loop PDI is moving toward: **trace → diagnosis → intervention →
evaluation.**

### What their experiments actually report (exact)

- *"prune rules transferred across benchmarks and cut median cost by 32%, while
  preserve rules, trained on benchmark-specific conventions, caused regressions on
  new task types."*
- On the primary SpreadsheetBench evaluation, **median cost rose**: reported cost
  uplifts of **+22%, +49%, +15%, +21%** across conditions on successful tasks.
- Removing prune patches **tripled the regression count (4 → 13)** with comparable
  median cost; stripping cost attribution **more than doubled** the median cost
  uplift on successful tasks (22% → 49%).
- **Single-seed** evaluation, by their own description.

### Why it matters

- It is a **concrete experimental comparator** whose results show that cost and
  quality must be assessed together. Their data show a **trade-off** (cost reductions
  alongside regressions). That is **not** automatically PDI's outcome **B**: assigning
  a category requires applying PDI's declared statistical rule to comparable data,
  which has not been done.
- Their mechanism proposes removals using **argument-similarity heuristics plus
  LLM-generated explanations**. They **do** execute held-out agents with the modified
  skills; what is absent is **isolated step-deletion evidence** — evidence that a
  *specific* step was unnecessary. **PDI has not run that experiment either**, and
  independent grading of a whole run does not by itself establish an individual
  step's causal contribution. Treat this as the intended distinction, not an
  established one.

---

## 2. Prior art that closes a claim: Cost–Utility Alignment

**Paper:** *Cost–Utility Alignment in LLM Agent Trajectories: Profiling, Attribution,
Diagnosis, Adaptation, and Evaluation*, arXiv 2608.26195 —
<https://arxiv.org/html/2608.26195v1>

This one is a positioning hit, not a tool match. It:

- *"treats resource consumption and task contribution as **dual ledgers over the same
  execution**"*, organised around five stages: cost profiling, utility attribution,
  misalignment diagnosis, targeted adaptation, evaluation;
- defines alignment as *"the absence of a feasible alternative achieving comparable
  utility at lower cost under matched constraints"* — which is PDI's O4b question,
  published;
- structures attribution as an **evidence ladder**: proxy signals → information
  dependency → **counterfactual intervention**.

**Consequence:** the **"two ledgers" framing is prior art.** PDI must not lead with
it. PDI's remaining distinctiveness is narrower: *refining quotients with total/live
class counts*, *weighted multiresolution energies with exact residual and
reconstruction identities*, and *evidence requirements on the inputs*. Their evidence
ladder — proxy signals → information dependency → **counterfactual intervention** —
is a **cited framework** PDI can adopt as warrant vocabulary for its own diagnoses,
and it composes with `verified_outcome`.

---

## 3. The rest of the field

| tool | actual overlap with PDI | main distinction |
|---|---|---|
| **[AgentFlow](https://github.com/ClemenceChee/AgentFlow)** | groups execution paths, discovers process graphs, identifies duration bottlenecks, checks conformance, feeds findings into runtime guards; no LLM calls in core analysis | closest to PDI's **deterministic behavioural analysis**; uses process graphs + path statistics |
| **[AgentSight](https://github.com/eunomia-bpf/agentsight)** | reads coding-agent sessions, profiles tokens, exposes repeated calls/retries, connects model activity with files and processes | strongest overlap with PDI's **cross-agent ingestion**; adds **system-level eBPF** capture PDI cannot match |
| **[PM4Py + COMPASS](https://ceur-ws.org/Vol-3996/paper-5.pdf)** | converts agent trajectories to event logs, compares successful/unsuccessful behaviour, discovers patterns, derives prompt guidelines | closest **process-mining precedent** (2025); **no cost metric** — optimises task success |
| **[LangSmith Insights](https://docs.langchain.com/langsmith/insights)** | groups traces into hierarchical categories with cost, latency, errors, evaluator scores | strong **commercial** overlap incl. multilevel detail; categorisation uses LLMs |
| **[context-profiler](https://github.com/yanpgwang/context-profiler)** | detects repeated content, repeated tool inputs, context hotspots; emits structured evidence and input-format confidence | closest narrowly-focused tool for the **rereading / context-overhead** case |
| **[GEPA](https://github.com/gepa-ai/gepa)** | reads traces + evaluation feedback, proposes targeted prompt/code changes, evaluates candidates | closest **optimisation engine**; PDI could feed it diagnostics |

---

## 4. What this changes for PDI

1. **Drop "two ledgers" as the headline.** It is published prior art (§2). Cite it.
2. **Strengthen the H comparator — or scope it honestly.** `O4B_FREEZE_PROPOSAL.md`
   currently defines H as "rank refinements by mean allocated cost of the targeted
   events." ClawTrace's Preserve/Prune/Repair is ordinary guidance *at the state of
   the art*. If P beats only a naive H, the result is uninformative.
3. **A possible methodological gap, stated as a hypothesis:** ClawTrace's removals
   rest on argument similarity plus LLM explanations, and what is missing from the
   literature is **isolated step-deletion evidence**. PDI's evaluator and runner
   could produce that — but it has not, and independent grading of a whole run does
   not establish a single step's causal contribution. Hypothesis, not result.
4. **Their data show the cost/quality trade-off is real**, which is *why* PDI's
   accepted-outcomes table exists. It does **not** license calling their result
   outcome B: that requires PDI's declared statistical rule applied to comparable
   data.
5. **Adopt the attribution ladder** (proxy → dependency → counterfactual) as the
   warrant vocabulary for PDI's own diagnoses.

## 5. Positioning conclusion

PDI belongs in **agent process mining / cost-aware trajectory analysis**. Its
defensible ground is **auditable multiresolution analysis that helps choose better
interventions** — the quotient tower, the multiresolution energies, and the evidence
requirements. It is **not** "we have two ledgers" and **not** "we find waste":
hierarchical grouping, trace retention, loop detection and cost diagnostics each
already have strong counterparts.

**The comparison to win:** whether that mathematical structure produces **better
decisions** than the simpler diagnostics — measured as cost reduction at
non-inferior verified success, against a ClawTrace-grade baseline, not a placeholder.

## 6. Caveats

- ClawTrace's evaluation is **single-seed**; treat its numbers as preliminary.
- §1–§3 rest on abstracts, READMEs and method/results sections, not full code review.
- External tools and papers move; re-verify before quoting in any customer-facing
  material.
