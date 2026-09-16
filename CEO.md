# CEO.md — what we have, and what it's worth

> **Strategy, not a warrant.** This file is a business read of the repository. The
> numbers are reproducible from the code; the claims they support are licensed in
> [`SPINE.md`](SPINE.md) §0. If this file conflicts with the ledger, the ledger wins.

---

## The one-line asset

**A correct, self-auditing instrument for a newly-urgent question — *where did my
agent waste work, and what did it cost?* — wrapped in an epistemic discipline
almost nobody else in this market has, sitting on a research lab that is unusually
honest about its own limits.**

That is rare. It is also **pre-revenue, pre-evidence, and pre-customer**. So the
value today is not "product". It is **option**.

---

## Three assets, ranked by what they are actually worth

| # | Asset | What it is | Worth |
|---|---|---|---|
| 1 | **The discipline** | Every claim carries a warrant; 25 self-checking suites; a checker that catches its own documentation drift; "I don't know" is a first-class output | **The IP. The only durable moat.** |
| 2 | **The localization** | `n_j` vs `L_j` at resolution `j`, plus `j*` — *where useful behaviour ended* | **Feature, not fortress.** Replicable in a sprint; defensibility comes from #1 |
| 3 | **The story** | Video, blog, the long-form math, the closed negative results | **Marketing asset**, priced in attention |

The discipline is not a slogan. In one week of review it caught four real defects —
a dropped zero-tool ingestion case, `Q6` key collisions, an invalid `§2.4`
witness, an unsound `§2.3` proof — because the process demanded a warrant for
every claim. **The process is the product's most valuable property, and it is the
hardest thing to copy.**

---

## What is *not* real yet

- **No validated real-world result.** Every headline number — 137×, $16,250/month,
  35–70% — is synthetic or illustrative. We correctly *removed* the unsupported
  claims, which means the sales deck currently promises **nothing quantified**.
- **No customers, no design partner, no hosted product, no team.**
- **A positioning that may be too subtle to sell.** "Normal tools never say *I
  don't know*" is a great thesis and a hard PLG sell — which means **the buyer
  decides whether our best feature is an asset or a tax.**
- **Research ahead of the market's ability to consume it.** A credibility asset and
  an adoption liability at the same time.

---

## The strategic fork

Four plausible wedges, each needing different proof:

| Wedge | Buyer | Must be true | Verdict |
|---|---|---|---|
| **CI regression gate** | Dev / platform lead | Catches a real regression a normal eval misses, few false positives | Fast, but crowded — everyone is bolting on CI |
| **Production waste APM** | FinOps / eng director | Live integration + one credible % of recoverable spend | Biggest TAM, heaviest proof |
| **Governance / assurance** | CISO, risk, AI governance | "A signed, reproducible warrant that your metrics mean what they say" | **Best fit for asset #1**: lowest engineering, highest defensibility — the honesty *is* the product |
| **Open instrument + paid lab** | Everyone / enterprises | Instrument drives distribution; studies and audits drive revenue | Matches our own line: **"Give away the instrument. Sell the laboratory."** |

---

## The one thing that changes everything

**O4b** ([`O4_SCOPE.md`](O4_SCOPE.md) §5). One controlled, **matched-task** study on
a real agent setup — *"PDI localized N% of spend to unrecovered exploration; a
change removed it at equal success, validated held-out"* — converts this repository
from **impressive** to **sellable**.

Until that number exists we have a sophisticated instrument and a research brand,
not a business. The same discipline that makes the *absence* of proof visible is
the discipline we will sell.

---

## Next 30 days

1. **Pick governance/assurance as the wedge**, not the APM — the only one where
   asset #1 is the product rather than a nice-to-have.
2. **Get one design partner** and run O4b on their traces. **The corpus is the
   scarce asset.**
3. **Split the public surface:** instrument = one screen, five minutes; the long
   README and the math = the lab/content, behind the pitch.
4. **Set the open-core line explicitly:** profiler open (distribution); validated
   reports, matched-task studies and signed warrants paid (margin).
5. **Stop expanding the theory.** It is already three steps ahead of what any buyer
   can evaluate. More math now is comfort, not progress.

---

## The bet, in one sentence

> **We are betting that buyers will pay for calibrated uncertainty in a market that
> rewards confident numbers.**

If that is right, we own a category. If it is wrong, we have built the most
rigorous tool nobody buys. Everything hinges on **one real result** — and we have
already written it down as `O4b`.

**Bottom line: world-class asset quality, zero commercial validation, one obvious
next experiment.** The gap is not in the code. It is in a customer's trace file.

---

*See [`usecases/`](usecases/README.md) for six concrete applications, each with its
proof status and pilot plan.*
