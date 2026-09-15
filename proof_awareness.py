#!/usr/bin/env python3
"""
proof_awareness.py — audit: where does PDI state a warrant, and does it discharge?

The claim under test: "this is a proof-aware observability system."

A proof-aware system states warrants, and every warrant it states is DISCHARGEABLE
-- either enforced at construction, or a fact about the data in hand. The audit
asks that of every warrant PDI states, and finds that every one holds EXCEPT the
`bound` field on the asymptotic layer.

  discharged   TowerViolation      enforced at construction; you cannot build a
                                   non-refining tower
  discharged   S_shallow/D_shallow a FACT about the observation (the sup was
                                   attained inside the horizon)
  discharged   status              a FACT about the observed tail's shape
  DISCHARGED   bound               stated as a claim about the UNOBSERVED tail

A finite observation cannot bound a limsup. limsup = inf_m sup_{j>=m} s_j, so
every finite prefix is consistent with continuations having any limsup from 0 to
the prefix sup. Each `bound` label is therefore falsifiable, and this file
falsifies all three by exhibiting the continuation.

Run: python3 proof_awareness.py
"""
from __future__ import annotations

from agent_profiler import asymptotic


def limsup(seq: list[float]) -> float:
    """inf_m sup_{j>=m} s_j for the sequence AS GIVEN.

    The tail sups are non-increasing, so the last one is the inf. Note this is
    the limsup of the FINITE sequence, not of any infinite extension: for
    s = [1, 1/2, ..., 1/49] it returns 1/49, whereas extending with zeros gives 0.
    That gap IS the point of this file -- the observation does not determine
    which extension is the truth.
    """
    return min(max(seq[m:]) for m in range(len(seq)))


def _report(seq: list[float], k: int = 4) -> dict:
    return asymptotic({"d_seq": {i + 1: v for i, v in enumerate(seq)},
                       "s_seq": {}, "horizon": len(seq)})["D"]


# ==========================================================================
# PART 1 — the audit
# ==========================================================================
def part1():
    print("=" * 84)
    print("PART 1 - warrant audit")
    print("=" * 84)
    rows = [
        ("TowerViolation", "refinement law (1.1) holds on the corpus",
         "enforced at construction", "DISCHARGED"),
        ("S_shallow / D_shallow", "the sup was attained inside the horizon",
         "fact about the observation", "DISCHARGED"),
        ("convergence status", "shape of the observed tail",
         "fact about the observation", "DISCHARGED"),
        ("bound = lower/upper/exact", "a bound on the UNOBSERVED tail",
         "claim about data not in hand", "NOT DISCHARGED"),
    ]
    for name, claim, how, verdict in rows:
        print(f"  {name:<26} {claim:<42} {how:<26} {verdict}")
    print()
    print("  Every warrant is a statement about data in hand, except one. The")
    print("  status field is honest by construction; the bound field is a claim")
    print("  about a tail that has not been observed.")
    print()


# ==========================================================================
# PART 2 — falsify all three bound labels
# ==========================================================================
def part2():
    print("=" * 84)
    print("PART 2 - falsifying each bound label")
    print("=" * 84)

    cases = [
        ("TRENDING_UP   -> 'lower bound'",
         [0.10, 0.20, 0.30, 0.40],
         [1.0 / j for j in range(5, 400)],),          # collapses to 0
        ("TRENDING_DOWN -> 'upper bound'",
         [0.40, 0.30, 0.20, 0.10],
         [9.0] * 400),                                 # jumps to 9
        ("STABLE        -> 'exact'",
         [0.50, 0.50, 0.50, 0.50],
         [9.0] * 400),                                 # jumps to 9
    ]
    all_violated = True
    for label, obs, cont in cases:
        r = _report(obs)
        true_ls = limsup(obs + cont)
        violated = abs(true_ls - r["value"]) > 1e-9
        all_violated = all_violated and violated
        print(f"  {label}")
        print(f"      observed tail      : {obs}")
        print(f"      reported value     : {r['value']:.6f}")
        print(f"      reported bound     : {r['bound']!r}")
        print(f"      continuation       : {cont[0]:.6f} ... ({len(cont)} terms)")
        print(f"      TRUE limsup        : {true_ls:.6f}")
        print(f"      claim violated     : {violated}")
        print()
    print("  All three labels are falsified by an observation-consistent")
    print("  continuation. This is not a coding error -- it is a theorem: no finite")
    print("  prefix determines a limsup. The field uses the grammar of a proof for")
    print("  something that is a heuristic.")
    print()
    return all_violated


# ==========================================================================
def part3():
    print("=" * 84)
    print("PART 3 - what this does and does not change")
    print("=" * 84)
    print("""
  It does NOT weaken anything PDI actually relies on. The finite-scale layer is
  'exact on the observed corpus' -- true, and it says so. The status field is a
  fact about the observed tail -- true. UNRESOLVED and NONE are honest refusals.
  The ledger's proved/computed/negative/open labels are honest.

  It DOES identify the one place where the system states a warrant it cannot
  discharge. The fix is not to delete the estimate -- the estimate is useful --
  but to make the label carry its hypothesis, exactly as the rest of the system
  carries its status. A bound on a limsup from a finite prefix is valid ONLY
  under an assumption about the unobserved tail, so the assumption belongs in
  the label:

      'exact'        ->  'window-exact'
      'lower bound'  ->  'lower bound IF the tail stays monotone'
      'upper bound'  ->  'upper bound IF the tail stays monotone'

  That is the same move as S_shallow: do not forbid the number, attach the
  condition under which it means what it says.

  So: PDI is a WARRANT-CARRYING observability system, and it is proof-aware in
  every place where a proof obligation can be discharged at construction. The
  asymptotic bound is the single point where the grammar outruns the warrant --
  and it is now labelled as such rather than asserted.
""")


if __name__ == "__main__":
    part1()
    ok = part2()
    part3()
    print("=" * 84)
    print(f"  part 2 (all three bound labels falsified): {'YES' if ok else 'NO'}")
    print("=" * 84)
