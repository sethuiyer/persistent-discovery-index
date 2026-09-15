# PDI — Product Breakdown for Sales & Non-Technical Stakeholders

> **The 30-Second Pitch:**  
> Two AI agents solve the exact same customer request. Both succeed.  
> One takes **3 tool actions**. The other wanders in circles, burning **13 tool actions and 4× the tokens** before stumbling onto the answer.  
> Traditional monitoring tools (LangSmith, Langfuse, Datadog) report: *"Both succeeded at 100%."*  
> **PDI reports:** *"Agent B is hemorrhaging 70% of its budget on dead-end exploration — and here is the exact prompt layer where the waste begins."*

---

## 1. The Three Value Hooks (Who Buys & Why)

### 1. To the Developer & Platform Lead
> *"Here is a GitHub Action that automatically fails the pull request if your prompt change causes the agent to start looping or burning 3× more tool calls."*

* **The Pain:** Developers change a system prompt or add a tool, run a 50-task eval, and see "90% pass rate." They merge it. Three days later, production latency doubles, users complain about sluggish responses, and API rate limits start throttling the app.
* **The PDI Fix:** PDI acts as an automated CI/CD regression gate. If a code change makes an agent wander or thrash, PDI blocks the pull request before bad prompts reach production.

### 2. To the FinOps Lead & Engineering Director
> *"We find the 35% to 70% of your LLM token spend that went to dead-end wandering, without hurting your success rate."*

* **The Pain:** The company receives a $30,000 monthly bill from OpenAI or Anthropic. Finance asks why token costs are skyrocketing while active users only grew 10%. Engineering shows span logs, but nobody can distinguish productive reasoning from useless trial-and-error.
* **The PDI Fix:** PDI measures the **Reasoning Signal-to-Noise Ratio (SNR)**. It separates necessary steps from pure exploratory waste, showing management exactly how many dollars were incinerated on dead branches.

### 3. To the CISO, Risk Officer & AI Governance Lead
> *"The Warrants & Rigor: Why customers trust your numbers over LangSmith or Phoenix when the board or regulators ask if the metrics are real."*

* **The Pain:** Most agent evaluation metrics are arbitrary vanity scores. If a company claims an agent is "95% reliable," but the metric hides massive behavioral instability or data drift, the company faces compliance, security, and reputational risk.
* **The PDI Fix:** Every claim in PDI carries a mathematical warrant (`STABLE`, `TRENDING_UP`, `UNRESOLVED`). PDI is the only system with the intellectual honesty to flag when a metric is an unproven estimate versus a mathematically backed fact.

---

## 2. "Where Does the Money Go?" — The 6 Zoom Levels

When an AI agent runs, it takes actions. PDI examines those actions under a 6-level microscope (the **Resolution Tower**), making it easy to find the exact "leak in the pipe":

```
[Zoom 1: The Result]    Did the agent finish successfully?
        ↓
[Zoom 2: Tool Choice]   Did it pick the right tools? (e.g. calculator vs bash search)
        ↓
[Zoom 3: Tool Order]    Did it use them in a logical order? (e.g. read before edit)
        ↓
[Zoom 4: Error State]   Did it handle tool errors or get stuck in panic loops?
        ↓
[Zoom 5: Arguments]     Did it target the right files, or read 10 unrelated folders?
        ↓
[Zoom 6: Full Replay]   The exact, verbatim execution trace.
```

### Why this matters to non-technical teams:
In traditional tools, diagnosing an agent requires an engineer to read through thousands of lines of raw JSON traces.  
With PDI, the system outputs one clear sentence:
> **"Distinction Onset at Level 3 (Tool Order): Your agent is re-running the same search commands 4 times in a row."**

---

## 3. Real Sales Proof Points: The Cost of Dead Ends

### Example 1: The Sudoku Stress Test (137× Cost Multiplier)
* Two algorithms solve the exact same puzzle with 100% accuracy.
* **Algorithm A (Smart):** Explores **169 steps**.
* **Algorithm B (Naive):** Explores **23,232 steps** (**137× more steps**).
* **The Diagnostic:** PDI reveals that **76.2% of Algorithm B's entire search occurred in depth band 21–30**, proving exactly where it stopped deducing and started blind guessing.

### Example 2: The Enterprise Coding Agent Simulation
* Tested across 300 runs on 5 standardized software engineering tasks:
  * **Disciplined Agent:** 97% success rate, **3.0 tool calls/run**.
  * **Wanderer Agent:** 89% success rate, **12.75 tool calls/run** (**4.25× more calls**).
* **The Dollar Impact:**
  * For 100,000 agent runs at $0.05/run:
    * Disciplined: **$5,000**
    * Wanderer: **$21,250**
  * **PDI identifies $16,250/month in pure waste** that standard eval dashboards completely missed.

---

## 4. Sales Battlecard: "Why Not Just Use LangSmith / Langfuse / Phoenix?"

| Capability | Traditional APMs (LangSmith, Langfuse, Phoenix) | PDI (Persistent Discovery Index) |
|---|---|---|
| **What happened?** (Traces & Logs) | ✅ Yes (Waterfalls & Spans) | ✅ Yes (7 formats normalized) |
| **Token & Latency Counter** | ✅ Yes (Raw numbers) | ✅ Yes |
| **Separates Productive Work from Waste** | ❌ No (Counts all tokens equally) | ✅ **Yes (Dual Ledgers: $n_j$ vs $L_j$)** |
| **Pinpoints WHERE waste began** | ❌ No (Manual inspection required) | ✅ **Yes (Resolution Tower $Q_1 \dots Q_6$)** |
| **Automated Pull Request Regression Gate** | ❌ Flaky (fails on noise/heuristics) | ✅ **Warrant-Backed (only fails if `STABLE`)** |
| **Reports What Metrics Forget** | ❌ No (Presents lossy scalars as truth) | ✅ **Yes (Blind-Spot Annotation)** |
| **Zero Dependencies / Self-Checking** | ❌ Requires cloud service or database | ✅ **Zero deps, 100% stdlib Python** |

### How to handle the objection:
> **Customer:** *"We already use LangSmith / Langfuse for our LLM observability."*  
> **Sales Rep:** *"That’s great — keep them! Those tools are like a car odometer: they tell you how many miles you drove and how much gas you bought. PDI is the engine diagnostic that tells you why your car is burning 4× more fuel per mile than it should."*

---

## 5. Five Discovery Questions for Sales Calls

When speaking to an Engineering VP, Head of AI, or FinOps Lead, ask these questions:

1. *"When two versions of your agent both get an 85% success score on your evals, how do you know which one won by luck and which one won efficiently?"*
2. *"Have you ever merged a prompt update that passed your eval suite, only to see your OpenAI or Bedrock bill spike the following week?"*
3. *"How much time do your senior engineers spend manually reading through JSON traces to understand why an agent took 30 steps instead of 3?"*
4. *"If your CFO asked you today: 'What percentage of our LLM token budget was burned on failed attempts and dead ends?', could you answer them?"*
5. *"Would it be valuable to have a CI check that automatically blocks any prompt or agent change that inflates exploration by more than 2×?"*

---

## 6. The Commercial Offer & ROI Guarantee

* **Low-Friction Wedge (Free):** Open-source normalizer and local terminal profiler (`python3 pdi_profile.py`).
* **Team Tier ($299/mo):** Automated GitHub Action regression gate for up to 5 repositories.
* **Enterprise Tier ($999/mo - $2,500/mo):** Production trace integration (OpenTelemetry / Langfuse exporter) + continuous waste localization dashboard.
* **The Sales Closing Guarantee:**
  > *"If PDI does not identify at least 3× its annual subscription cost in wasted token spend during your 14-day trial, you owe us nothing."*
