# PDI — Product Positioning

> **What this file is.** Strategy. Market hypotheses, customer guesses, and one
> recommended sequence.
>
> **What this file is not.** A warrant. Nothing here is proved, computed, or
> verified — unlike every claim in `SPINE.md`, which carries an explicit status.
> If a statement in this file turns out to be wrong, that is expected and
> costs nothing. If a statement in `SPINE.md` turns out to be wrong, that is a
> bug. **Do not cite this file as evidence for anything.**

Framework: CIRCLES (Lewis C. Lin, *Decode and Conquer* — widely used in Indian PM
interview loops, including Flipkart's; not a Flipkart framework).

---

## C — Comprehend the situation

**What exists.** A warrant-carrying observability library for AI agents. It reads
traces, builds a resolution tower over behaviour, keeps two ledgers (`n_j` cost vs
`L_j` survivors), and reports cost-of-discovery structure where the waste begins and
how strongly each number is supported.

| | |
|---|---|
| core modules | **2,956 lines** (`pdi.py`, `agent_profiler.py`, `quotient_tower.py`, `ingest.py`, `adapters.py`, `stable_quotient.py`, `transport.py`, `invertibility.py`, `prime_holonomy.py`, `sudoku.py`) |
| total Python | 9,589 lines |
| third-party dependencies | **zero** — stdlib only |
| ingest formats | **7** (canonical, pi, OpenAI, LangSmith, OTel GenAI, AutoGen, CrewAI) |
| self-checking suites | **24** |
| licence | MIT |

**What the market looks like.** Agent observability is crowded and commoditised:
LangSmith, Langfuse, Helicone, Braintrust, Phoenix. All answer *"what happened?"* and
*"what did it cost?"* None answer *"is this metric allowed to say that?"*

**The honest constraint.** Zero users. No `pip install`. No controlled corpus.
Everything in the sections below is a hypothesis until those three change.

---

## I — Identify the customer

Not "AI teams." Three specific people, in priority order:

1. **The eval engineer** who has to defend a number to a stakeholder. They currently
   ship `success_rate = 0.94`, get asked "is that good?", and have nothing to say.
2. **The platform lead** running CrewAI / AutoGen / LangGraph in production who
   cannot explain why agent B costs 25× agent A on the same task.
3. **The FinOps owner** who sees a token bill and no structure underneath it.

The **buyer** is (1) or (2). The **user** is whoever is on call when a trace is wrong.

---

## R — Report the customer's needs

In their words, not ours:

- *"Two agents both scored 100%. One burned 137× the tokens. My dashboard says
  they're identical."*
- *"I need to know **where** the waste starts, not that it exists."*
- *"When I show a number, I need to know what it's hiding."*
- *"If your tool silently mangles my trace, every chart downstream is confidently
  wrong."*

---

## C — Cut through prioritization

**The one thing to lead with: cost structure, not epistemology.**

Warrants are *why to trust us*. They are not *why to care*. Nobody wakes up wanting
a licensed claim. They wake up with a bill and a vague sense that something is
wasting money.

**Lead with 137×. Close with warrants.**

| Priority | Need | Backing |
|---|---|---|
| **P0** | Where does waste start? | `first/asc` search uses **23,232** nodes vs **169** for `mrv/asc` — **137×**. **76.2%** of the naive search sits in depth band 21–30. Onset `j*` localises it. |
| **P1** | Can I trust this number? | `STABLE` / `TRENDING_UP (lower bound)` / `TRENDING_DOWN (upper bound)` / `UNRESOLVED` on every asymptotic figure. The bound labels carry their own hypothesis. |
| **P2** | Did ingestion lose anything? | The edge-preservation test caught a real AutoGen bug: errors were being attributed to the wrong tool call. |
| **P3** | Is the method serious? | 216 loops, 0 injective → a theorem: at a global optimum, undoing any single-bit perturbation is never worse than any alternative, so the optimum has `n` preimages under one step. Irreversibility is structural. |

---

## L — List solutions

### A — Open-source the instrument
MIT core stays free. Zero deps, 7 adapters. Adoption play.

### B — "Blind-spot annotation" as the paid layer

```
agent-b inflates exploration 25.4x at Q3

  CLAIM       waste begins at tool-order resolution
  WARRANT     exact on this corpus
  PRESERVES   outcome, tool-family multiset, tool ordering
  FORGETS     attachment topology -- two systems with IDENTICAL
              n_j and L_j can be non-isomorphic trees
  INVARIANCE  persistent rate cofinal-invariant;
              waste metric presentation-dependent
  SOURCE      edges retained; view re-derivable on demand
```

### C — Sell it as a gate, not a dashboard
A CI step that fails the build when an agent's inflation crosses a threshold at a
resolution where the warrant is `STABLE`. Observability that *refuses* rather than
*reports*.

### D — Ship the research as the top of funnel
"We tried 216 loops to find an injective transport; 0 worked; then we proved why."
Link the theorem, not a landing page.

---

## E — Evaluate tradeoffs

**A is cheap and might get stars. It does not get revenue.**

**B is the only option with a moat** — nobody else computes what a summary forgets.
But it requires explaining "presentation-dependent" to a buyer who wants a green
checkmark. Real risk of *"interesting, we'll stick with Langfuse."*

**C is the strongest wedge** if one team can be shown it caught something real. It is
also the hardest to sell: telling an engineering org that its build should fail is a
political ask, not a technical one.

**D costs one weekend and buys credibility, not customers.**

**The tradeoff that matters:** warrants are a *trust* feature sold into a market that
buys *convenience*. Lead with warrants and it reads as a philosophy seminar. Lead
with cost and it sounds like every other tool — until the buyer notices we are the
only one printing `lower bound` next to a number.

> **Cost is the hook. Warrant is the retention.**

---

## S — Summarize the recommendation

**Do not market anything yet.** Sequence:

1. **Build the controlled corpus** — repeated tasks per agent. This is the single
   blocker for every claim we would otherwise make in public. Without it, "agent B
   inflates 25×" is an anecdote, not a finding.
2. **One report** — the blind-spot annotation above, on real data.
3. **Ten conversations** with eval engineers and platform leads. One question:
   *"Would this have caught something your current stack missed?"*
4. **Then** the README rewrite, the public post, and pricing.

### Kill criterion

If 7 of 10 say *"nice, but Langfuse is fine,"* the profiler is a feature, not a
company — and the honest move is to publish the method as a paper and let the
theorem be the artifact.

### Positioning, final

> **PDI — Warrant-Carrying Observability for AI Agents**
>
> Counts measure. Edges remember. Warrants constrain claims.

**What we are not:** a LangSmith competitor. We are the epistemic layer that tells
you whether the trace viewer's number means anything.

---

## The risk at the top of the board deck

Every hard result in this repository — `UNRESOLVED`, presentation-dependence,
non-injective ledgers, *"these trees share a ledger but are not isomorphic"* — is a
product **feature** that reads to a buyer like a product **failure**.

Normal tools never say *"I don't know."*

That is the whole bet. If refusals can be made to feel like rigour rather than
weakness, this is a category. If not, it is the best-documented profiler nobody
needed.
