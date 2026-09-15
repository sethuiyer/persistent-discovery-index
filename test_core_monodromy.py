#!/usr/bin/env python3
"""
test_core_monodromy.py — pins §19's live edge: core monodromy is NOT a representation.

`core_monodromy.py` asks whether gamma |-> T_gamma|_R is a homomorphism
pi_1(presentation space) -> Sym(R). The answer is no, for two independent
reasons that are both already in the ledger. This suite makes that fail loudly so
the strand cannot be reopened on a false premise.

Checks, each with its warrant and its bounds:

  computed   composition HOLDS: T_{g.g} == T_g . T_g and T_{g.g^-1} == T_{g^-1} . T_g
             exactly, on all 2^10 states (the monoid half is earned)
  computed   the core is LOOP-DEPENDENT: 5 distinct cores over 6 loops, sizes
             {6,8,10,12,16}, intersection = 2 states of 1024 (this is O1)
  computed   the INVERSE FAILS: T_{g^-1}.T_g is not the identity on core(g), and
             T_{g^-1} does not preserve core(g) (this is §18)
  computed   on the common quotient stable under all six loops (a genuine
             quotient, not discrete) every induced map is non-injective
  computed   the cores on that common quotient are still not identical

  BOUNDS  n=10, tabu in {2,3}, steps=8, the six schedules in core_monodromy.LOOPS.
  Nothing here is a general theorem about all instances; it is exact over the
  stated family, and the two mechanisms it exhibits are already proved elsewhere
  (O1 open as a general matter, §18 proved for the min-conflicts family).

Run: python3 test_core_monodromy.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from core_monodromy import LOOPS, run_experiment

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def main() -> int:
    print("=" * 74)
    print("test_core_monodromy")
    print("=" * 74)
    for tabu in (2, 3):
        print(f"\n-- n=10 tabu={tabu} steps=8, {len(LOOPS)} loops --")
        r = run_experiment(10, tabu, 8)

        check(f"[tabu={tabu}] composition T_gg == T_g.T_g holds exactly",
              r["composition_holds"] is True)
        check(f"[tabu={tabu}] the core is loop-dependent (5 distinct cores of 6)",
              r["distinct_cores"] == 5, str(r["distinct_cores"]))
        check(f"[tabu={tabu}] intersection of all cores is 2 states of 1024",
              r["intersection"] == 2, str(r["intersection"]))
        check(f"[tabu={tabu}] inverse fails: T_g^-1.T_g != id on core(g)",
              r["inverse_fails"] is True)
        check(f"[tabu={tabu}] T_g^-1 does not preserve core(g)",
              r["reverse_preserves_core"] is False)
        check(f"[tabu={tabu}] common quotient is genuine, not discrete",
              2 < r["common_quotient_blocks"] < r["states"],
              str(r["common_quotient_blocks"]))
        check(f"[tabu={tabu}] every induced map on the common quotient is non-injective",
              not any(r["induced_bijective"].values()), str(r["induced_bijective"]))
        check(f"[tabu={tabu}] cores on the common quotient are still not identical",
              r["cores_on_quotient_identical"] is False)

    print()
    print("=" * 74)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        return 1
    print("ALL PASS")
    print("Meaning: gamma |-> T_gamma|_R is a monoid homomorphism that is not a")
    print("group representation -- no loop-independent R (O1), and the inverse")
    print("axiom fails where it is typed (§18). No character on pi_1, so the")
    print("twisted zeta has nothing to twist by. Confirms §19.5-19.6 from the")
    print("transport side.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
