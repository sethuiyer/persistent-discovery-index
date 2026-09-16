# Use cases

Six applications of PDI, spanning different buyers and functions. Each file follows
the same shape: **pain → what PDI measures → an illustrative sketch → proof status
→ pilot → risks.**

> **Read the proof status before the pitch.** Every number marked *illustrative* is
> constructed, not measured. The instrument is real and self-checking; the
> commercial claims are not yet validated on customer data. See
> [`../O4_SCOPE.md`](../O4_SCOPE.md) §5 and [`../SPINE.md`](../SPINE.md) §0.

| # | Use case | Buyer | PDI feature exercised | Evidence today |
|---|---|---|---|---|
| [01](01-ci-regression-gate.md) | CI regression gate for agents | Dev / platform lead | `n_j`/`L_j` inflation, `j*` onset | **computed** (instrument); prediction **needs O4b** |
| [02](02-production-waste-apm.md) | Production token-waste APM | FinOps / eng director | transient mass, yield, STOP | **illustrative** (simulated corpus) |
| [03](03-governance-assurance.md) | Governance & assurance reports | CISO / risk / AI governance | warrant labels, convergence status, reproducibility | **implemented** (discipline + 25 suites) |
| [04](04-model-and-scaffold-selection.md) | Model & scaffold selection | ML platform / procurement | `D` vs `Δ`, `--matched` tasks | **method implemented**; **needs matched corpus** |
| [05](05-agentic-rl-curation.md) | Agentic-RL data curation & reward | Training / research | detail energies, pruning error budget | **algebra discharged** (O4a); utility **needs experiments** |
| [06](06-search-and-solver-tuning.md) | Search & solver tuning beyond agents | Industrial / optimization | per-depth waste, inflation vs reference | **computed** (Sudoku: 137×, 76.2% localised) |

### Adjacent (not among the six)

- **Behavioural drift & safety monitoring** (SRE / trust & safety) — nightly profiling
  of live traffic, alerting on `Δ`/resolution-shift. Close cousin of 02 and 06; blocked
  on the same missing piece — *a reference distribution*.

### The common denominator

All six consume the **same primitive**: two ledgers at a chosen behavioural
resolution, and the level at which the gap between them opens. The applications
differ in buyer, data path, and what counts as proof — not in the measurement.
