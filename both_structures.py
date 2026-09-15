#!/usr/bin/env python3
"""
both_structures.py — is the transient/recurrent distinction itself information?

The claim under test:

    "Keep both the transient and recurrent structure, because the distinction
     between what disappears and what returns is itself information."

A distinction is information only if it is not recoverable from either half
alone. So the claim is forced by two negative results:

  PART 1  the recurrent core does NOT determine the transient structure
          (same core, same transient COUNT, different transient ARRANGEMENT)

  PART 2  the ledger counts do NOT determine the structure
          (identical n_j and L_j, NON-ISOMORPHIC trees)

  PART 3  therefore the distinction lives in the structure, not in the counts.
          Keeping the ledger is not the same as keeping the structure.

Run: python3 both_structures.py
"""
from __future__ import annotations

from pdi import PDI


# ==========================================================================
# PART 1 — the recurrent core does not determine the transients
# ==========================================================================
def periodic_points(T: dict) -> set:
    out = set()
    for x in T:
        y, seen = T[x], {x}
        while y not in seen:
            seen.add(y)
            y = T[y]
        if y == x:
            out.add(x)
    return out


def transient_profile(T: dict) -> dict:
    """For each transient node, its distance to the core; returns {depth: count}."""
    core = periodic_points(T)
    prof: dict[int, int] = {}
    for x in T:
        if x in core:
            continue
        d, y = 0, x
        while y not in core:
            y = T[y]
            d += 1
        prof[d] = prof.get(d, 0) + 1
    return prof


def part1():
    print("=" * 82)
    print("PART 1 - does the recurrent core determine the transient structure?")
    print("=" * 82)
    # both have the SAME 3-cycle 0->1->2->0 and the SAME two transient nodes
    T1 = {0: 1, 1: 2, 2: 0, 3: 0, 4: 0}      # 3 and 4 both fall straight in
    T2 = {0: 1, 1: 2, 2: 0, 3: 4, 4: 0}      # 3 -> 4 -> core: one is deeper
    for name, T in (("T1", T1), ("T2", T2)):
        core = sorted(periodic_points(T))
        prof = transient_profile(T)
        print(f"  {name}: edges " + ", ".join(f"{k}->{v}" for k, v in sorted(T.items())))
        print(f"      recurrent core      : {core}   (cycle length 3)")
        print(f"      transient count     : {sum(prof.values())}")
        print(f"      transient profile   : {dict(sorted(prof.items()))}"
              f"   (depth -> nodes)")
        print()
    p1, p2 = transient_profile(T1), transient_profile(T2)
    same_core = periodic_points(T1) == periodic_points(T2)
    same_count = sum(p1.values()) == sum(p2.values())
    diff_shape = p1 != p2
    print(f"  same recurrent core        : {same_core}")
    print(f"  same transient COUNT       : {same_count}")
    print(f"  different transient SHAPE  : {diff_shape}"
          f"   ({dict(sorted(p1.items()))} vs {dict(sorted(p2.items()))})")
    print("  -> The core is identical and the number of transients is identical,")
    print("     yet the two systems differ. So neither the core nor the transient")
    print("     count recovers the arrangement: the distinction is extra.")
    print()
    return same_core and same_count and diff_shape


# ==========================================================================
# PART 2 — the ledger counts do not determine the structure
# ==========================================================================
def canon(node) -> str:
    """Canonical form of a rooted tree (AHU). Equal iff isomorphic."""
    if not node.children:
        return "()"
    return "(" + "".join(sorted(canon(c) for c in node.children.values())) + ")"


def build(traces):
    idx = PDI()
    for t in traces:
        idx.insert(t, live=True)      # all live, so L_j == n_j: the ledger is maximal
    idx.finalize_explicit()
    return idx


def degrees_by_level(idx, max_level):
    out = {}
    for nd in idx._all_nodes():
        if nd.level < max_level and nd.children:
            out.setdefault(nd.level, []).append(len(nd.children))
    return {k: sorted(v) for k, v in sorted(out.items())}


def part2():
    print("=" * 82)
    print("PART 2 - do the ledger counts determine the structure?")
    print("=" * 82)
    # same number of distinct length-1 and length-2 prefixes; different attachment
    a = build([("a", "b"), ("a", "c"), ("d", "e"), ("d", "f")])
    b = build([("a", "b"), ("a", "c"), ("a", "d"), ("e", "f")])
    same_n = all(a.n.get(j, 0) == b.n.get(j, 0) for j in range(1, 3))
    same_L = all(a.L.get(j, 0) == b.L.get(j, 0) for j in range(1, 3))
    ca, cb = canon(a.root), canon(b.root)
    print(f"  tree A traces: (a,b) (a,c) (d,e) (d,f)")
    print(f"  tree B traces: (a,b) (a,c) (a,d) (e,f)")
    print()
    print(f"  n_j   A = {[a.n.get(j,0) for j in (1,2)]}   B = {[b.n.get(j,0) for j in (1,2)]}")
    print(f"  L_j   A = {[a.L.get(j,0) for j in (1,2)]}   B = {[b.L.get(j,0) for j in (1,2)]}")
    print(f"  out-degrees by level  A = {degrees_by_level(a,2)}  B = {degrees_by_level(b,2)}")
    print(f"  canonical tree form   A = {ca}")
    print(f"                        B = {cb}")
    print()
    print(f"  identical n_j        : {same_n}")
    print(f"  identical L_j        : {same_L}")
    print(f"  isomorphic trees     : {ca == cb}")
    print("  -> The ledgers are identical and the trees are NOT isomorphic. Every")
    print("     scalar PDI reports is a level-size profile, so it cannot see the")
    print("     difference. The information is in the EDGES, which the ledger")
    print("     summarises away.")
    print()
    return same_n and same_L and (ca != cb)


# ==========================================================================
def part3():
    print("=" * 82)
    print("PART 3 - what this settles")
    print("=" * 82)
    print("""
  Two negative results, and together they force the claim:

    1. The recurrent core does not determine the transients.
       (Part 1: same core, same transient count, different arrangement.)

    2. The ledger counts do not determine the structure.
       (Part 2: identical n_j and L_j, non-isomorphic trees.)

  So the transient/recurrent distinction is NOT a summary of either half. It is
  not recoverable from the core, and it is not recoverable from the counts. It
  is carried by the STRUCTURE -- by which node feeds which.

  This CORRECTS the v0.13.0 sharpening rather than replacing it. v0.13.0 said
  the original move is the PAIRING of two counts at the same resolution. That is
  right about what makes the ledger possible, and it is why n_j is survival-free.
  But a pairing of two level-size profiles is still a summary: it says HOW MUCH
  is transient at each resolution, and never HOW the transients are arranged.

  The fully general statement is the one the structures give:

      keep both, and keep the EDGES -- because the distinction is information
      precisely where the counts are blind.

  The reproduction in the transport work is that the recurrent core is a
  permutation on cycles (earned, SPINE 6.2) while the trees feeding it stay
  many-to-one (SPINE 8.x). Those are the two halves, and PDI's value is that it
  reports both instead of discarding the second the moment the first is found.
""")


if __name__ == "__main__":
    ok1 = part1()
    ok2 = part2()
    part3()
    print("=" * 82)
    print(f"  part 1 (core does not determine transients) : {'PASS' if ok1 else 'FAIL'}")
    print(f"  part 2 (counts do not determine structure)  : {'PASS' if ok2 else 'FAIL'}")
    print("=" * 82)
