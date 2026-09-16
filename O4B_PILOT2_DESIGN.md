# O4B_PILOT2_DESIGN.md — design for the next experiment (draft, NOT frozen)

Goal of pilot 2 (**design (c)**): test whether **PDI adds value over ordinary
success-and-cost guidance**, on a corpus with a real difficulty range.

This is a design draft. Nothing here is frozen; pilot 2 gets its own predeclaration
before its first baseline run, exactly as pilot 1 did. The ruler
([`o4b_stat.py`](o4b_stat.py)) is reused unchanged.

## 1. What pilot 1 forces

1. **Failure-linked liveness is blind when everything succeeds.** With all runs
   successful, `L_j = n_j` and `τ_j = 0`, so no level can be selected. Pilot 2
   needs a waste signal that is **not** defined by failure.
2. **Traces are mandatory.** The runner already persists
   `o4b_corpus/runs/<task>_r<run>.jsonl`; that is now a hard prerequisite, checked
   before any run is counted.
3. **Do not select tasks because this agent failed them.** Task identity and
   difficulty must come from a rule fixed before outcomes are seen.

## 2. Corpus — broader difficulty range, fixed in advance

- A **difficulty ladder** declared before any run: task families chosen so the
  baseline success rate spans a range (e.g. easy / medium / hard), not a single
  point. Selection is by design, not by observed failure.
- **Mandatory trace persistence** per run; a run without a persisted trace is
  recorded as ineligible (coverage), never silently used.
- Same separation rules as pilot 1: clusters disjoint across discovery and
  held-out; held-out sealed; every attempt and exclusion recorded.

## 3. Waste signal — outcome-independent

The localizer must be able to see overhead **inside** successful runs. Candidate
outcome-independent signals (to be frozen before the run):

- **cost / token detail energies** from [`multiresolution.py`](multiresolution.py):
  `E_j = ‖D_j (cost)‖²` localises *which refinement* carries cost, independent of
  success;
- **behavioural transient share with a cost-based live rule**: a class is live if
  it contains a run whose cost is at or below a predeclared budget quantile,
  rather than one that merely succeeded;
- combinations are allowed only if fixed in advance.

Whichever is chosen, it must be computable when **every** run succeeds.

## 4. Two arms — the value-add test

| arm | localisation | purpose |
|---|---|---|
| **P** | PDI, frozen rule over the outcome-independent signal | the claim under test |
| **H** | ordinary success-and-cost guidance (e.g. the behaviour with the largest raw cost or tool-count contribution) | the baseline PDI must beat |

Both arms pick a behaviour, receive a manifest-permitted intervention of the same
class, and are evaluated identically. **The question is not "does an intervention
help?" but "does PDI's localisation beat ordinary guidance?"** If P and H perform
the same, PDI has not demonstrated value on this task, and that is a valid result.

## 5. Endpoints

Reuse pilot 1's statistic verbatim (`o4b_stat.py`): task-level paired bootstrap,
seed fixed, `D*₅ ≥ −δ` for non-inferior verified success, `Δ*₉₅ < 0` for cost
reduction, `n_both < 6 → D`. Add a secondary **P-vs-H** contrast on held-out cost at
non-inferior success, reported whatever it shows.

## 6. To fix before pilot 2 runs

`[FIX BEFORE RUN]`: difficulty ladder and task list; the outcome-independent waste
signal; the P and H selection rules; `δ`, `τ_min`, `K`, seed, `R`, splits;
verifier; and the intervention manifests for both arms.

## 7. Non-negotiable

- No task chosen because this agent failed it.
- No held-out inspection before both arms' interventions are frozen.
- No commercial savings language from a pilot.
- If the outcome-independent localizer also yields nothing, that is **C** again —
  reported as C, not reframed.
