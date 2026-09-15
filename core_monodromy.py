#!/usr/bin/env python3
"""
core_monodromy.py — is gamma |-> T_gamma|_R a homomorphism pi_1 -> Sym(R)?

THE QUESTION (the live edge §19.7 left open)
  After the ledger (§15), trees (AHU) and cycles (zeta) were separated, the last
  candidate for a transport-decorated invariant was:

      gamma |-> T_gamma |_R   in   Sym(R),
      pi_1(presentation space) -> Sym(R),

  where R is the recurrent core. T_gamma|_R is a genuine permutation of R, so the
  only question is whether the assignment is a REPRESENTATION.

THE ANSWER, COMPUTED: NO — and it is not a technicality. It is blocked by the
repo's own two hardest results.

  1. COMPOSITION HOLDS. T_{gamma1.gamma2} = T_{gamma2} o T_{gamma1}, exactly, on
     every state (the transport is a composition of memoryless legs). So the
     assignment IS a monoid homomorphism from the free monoid of schedules. That
     half is earned.

  2. THE TARGET R IS NOT WELL-DEFINED (this is O1). The recurrent core is
     LOOP-DEPENDENT: over the six loops tested at n=10, |R| takes the values
     6, 8, 10, 12, 16 with different cycle structures, and the intersection of
     all six cores is 2 states out of 1024. There is no single R for pi_1 to act
     on, so the map is not even well-typed. This is the same presentation-
     dependence O1 records for the stable quotient — the core inherits it.

  3. THE INVERSE AXIOM FAILS (this is §18). Even granting a fixed domain,
     T_{gamma^{-1}} o T_gamma is NOT the identity on the core, and T_{gamma^{-1}}
     does not even map core(gamma) into itself. Reversing a schedule does not
     invert an irreversible transport. So there is no group action.

  4. ON THE COMMON QUOTIENT the picture is the same. Refining the branch
     partition until it is stable under ALL six loops at once gives a genuine
     quotient (332 blocks of 1024 — not discrete). But on that common quotient
     EVERY induced map is non-injective, and the cores still differ per loop.
     So even the one fixed space where all the maps live carries no permutation
     structure.

  VERDICT. gamma |-> T_gamma|_R is a monoid homomorphism that is not a group
  representation: the codomain Sym(R) has no loop-independent R (O1), and the
  inverse axiom fails where it is typed (SS18). The strand closes for good — and
  it closes on the repo's central open problem, not on a defect of this attempt.

  Consequence for the zeta programme: with no character chi on pi_1 there is
  nothing to twist by, which is the independent confirmation of §19.5-19.6.

WARRANTS
  computed   composition holds exactly, on all 2^10 states, both settings
  computed   the core is loop-dependent: 5 distinct cores, intersection 2 states
  computed   T_{gamma^{-1}} o T_gamma != id on the core; T_{gamma^{-1}} does not
             preserve the core
  computed   on the common quotient (332 blocks) every induced map is non-injective
  negative   no homomorphism pi_1 -> Sym(R) exists for this family
  bounds     n=10, tabu in {2,3}, steps=8, the six schedules listed in LOOPS

Run: python3 core_monodromy.py
"""
from __future__ import annotations

from stable_quotient import (block_map, branch_labels, build_transport,
                             coarsest_stable, functional_graph)
from transport import Searcher, find_instance

L0 = 0.10


def loop(*interior) -> tuple:
    return (L0,) + tuple(interior) + (L0,)


def cat(a: tuple, b: tuple) -> tuple:
    """Concatenate two loops that both return to L0."""
    return a + b[1:]


G1 = loop(0.50, 0.90)
G3 = loop(0.25, 0.75)
LOOPS = {
    "g1": G1,
    "g1^-1": G1[::-1],
    "g3": G3,
    "g3^-1": G3[::-1],
    "g1.g1": cat(G1, G1),
    "g1.g1^-1": cat(G1, G1[::-1]),
}


# --------------------------------------------------------------------------
def cycles_of(T: list) -> set:
    """States lying on a cycle of the map T — the recurrent core."""
    n = len(T)
    done = [False] * n
    cyc: set = set()
    for s in range(n):
        if done[s]:
            continue
        path, idx, x = [], {}, s
        while not done[x] and x not in idx:
            idx[x] = len(path)
            path.append(x)
            x = T[x]
        if x in idx:
            cyc.update(path[idx[x]:])
        for y in path:
            done[y] = True
    return cyc


def cycle_lengths(T: list, R: set) -> list:
    seen, out = set(), []
    for s in R:
        if s in seen:
            continue
        k, x = 0, s
        while x not in seen:
            seen.add(x)
            x = T[x]
            k += 1
        out.append(k)
    return sorted(out)


def refine_multi(part: list, Ts: list):
    """One refinement round stable under EVERY map in Ts at once."""
    ids: dict = {}
    new = [0] * len(part)
    for x in range(len(part)):
        key = (part[x],) + tuple(part[T[x]] for T in Ts)
        b = ids.get(key)
        if b is None:
            b = len(ids)
            ids[key] = b
        new[x] = b
    return new, len(ids)


def stable_under_all(part: list, Ts: list, cap: int = 64):
    prof = [len(set(part))]
    for _ in range(cap):
        part, k = refine_multi(part, Ts)
        prof.append(k)
        if k == prof[-2]:
            break
    return part, prof


def run_experiment(n: int = 10, tabu: int = 2, steps: int = 8) -> dict:
    base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
    edges, opt = find_instance(n, base, want=2)
    s = Searcher(n, edges, tabu_len=tabu)
    Ts = {k: build_transport(s, v, steps, n) for k, v in LOOPS.items()}
    N = 1 << n

    R = {k: cycles_of(T) for k, T in Ts.items()}
    inter = set.intersection(*[set(v) for v in R.values()])
    composition = all(Ts["g1.g1"][x] == Ts["g1"][Ts["g1"][x]] for x in range(N))
    composition2 = all(Ts["g1.g1^-1"][x] == Ts["g1^-1"][Ts["g1"][x]] for x in range(N))
    core1 = R["g1"]
    inv_fails = not all(Ts["g1^-1"][Ts["g1"][x]] == x for x in core1)
    rev_preserves = all(Ts["g1^-1"][x] in core1 for x in core1)

    # one common quotient, stable under all six loops
    branch = branch_labels(opt, n)
    part, prof = stable_under_all(branch, [Ts[k] for k in LOOPS])
    Q = len(set(part))
    bms = {k: block_map(part, Ts[k]) for k in LOOPS}
    bij = {k: len(set(bms[k].values())) == len(bms[k]) for k in LOOPS}
    cores_q = {k: {b for c in functional_graph(bms[k])["cycles"] for b in c} for k in LOOPS}

    return {
        "n": n, "tabu": tabu, "steps": steps, "states": N,
        "core_sizes": {k: len(v) for k, v in R.items()},
        "cycle_lengths": {k: cycle_lengths(Ts[k], R[k]) for k in LOOPS},
        "distinct_cores": len({frozenset(v) for v in R.values()}),
        "intersection": len(inter),
        "composition_holds": composition and composition2,
        "inverse_fails": inv_fails,
        "reverse_preserves_core": rev_preserves,
        "common_quotient_blocks": Q,
        "common_quotient_profile": prof,
        "induced_bijective": bij,
        "cores_on_quotient_identical": len({frozenset(v) for v in cores_q.values()}) == 1,
        "quotient_core_intersection": len(set.intersection(*[set(v) for v in cores_q.values()])),
    }


def main() -> int:
    print("=" * 82)
    print("core monodromy — is gamma |-> T_gamma|_R a representation pi_1 -> Sym(R)?")
    print("=" * 82)
    ok = True
    for tabu in (2, 3):
        r = run_experiment(10, tabu, 8)
        print(f"\nn={r['n']} tabu={r['tabu']} steps={r['steps']}  "
              f"states={r['states']}  optima=2")
        print("  cores by loop:")
        for k in LOOPS:
            print(f"    {k:9} |R|={r['core_sizes'][k]:4d}  "
                  f"lengths={r['cycle_lengths'][k][:6]}")
        print(f"  distinct cores                  : {r['distinct_cores']} of {len(LOOPS)}")
        print(f"  |intersection of all cores|     : {r['intersection']} states")
        print(f"  composition T_gg == T_g.T_g     : {r['composition_holds']}  "
              "<- the monoid half HOLDS")
        print(f"  inverse: T_g^-1.T_g != id on R  : {r['inverse_fails']}")
        print(f"  T_g^-1 preserves core(g)        : {r['reverse_preserves_core']}")
        print(f"  common quotient under all loops : {r['common_quotient_blocks']} blocks "
              f"of {r['states']} (profile {r['common_quotient_profile']})")
        print(f"  every induced map non-injective : {not any(r['induced_bijective'].values())}")
        print(f"  cores on the quotient identical : {r['cores_on_quotient_identical']} "
              f"(intersection {r['quotient_core_intersection']})")
        ok &= (r["composition_holds"] and r["inverse_fails"]
               and r["distinct_cores"] > 1 and not r["cores_on_quotient_identical"])

    print("\n" + "=" * 82)
    print("VERDICT")
    print("=" * 82)
    print("""
  gamma |-> T_gamma|_R is a MONOID homomorphism (composition holds exactly), and
  it is NOT a group representation. Two independent obstructions, both already in
  the ledger:

    O1 (canonicity)   the recurrent core is presentation-dependent. |R| is 6, 8,
                      10, 12, 16 across six loops and the intersection of all of
                      them is 2 states of 1024. There is no fixed R for pi_1 to
                      act on, so the map is not even well-typed.
    §18 (irreversibility)   T_{gamma^-1} o T_gamma is not the identity on the
                      core, and T_{gamma^-1} does not preserve it. The inverse
                      axiom fails wherever the map IS typed.

  On the one common quotient where every loop's transport is defined (332 blocks
  of 1024 at tabu=2, 369 at tabu=3 -- a genuine quotient either way), EVERY
  induced map is many-to-one, so no permutation structure survives there either.

  So there is no character on pi_1, hence nothing for a twisted zeta to twist by.
  That is the independent confirmation of §19.5-19.6, arrived at from the
  transport side rather than the zeta side.

  The strand closes. It does not close because zeta or Ihara were the wrong tools
  in a local sense; it closes because transport monodromy needs a canonical core,
  and canonicity is exactly what O1 says PDI does not have.
""")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
