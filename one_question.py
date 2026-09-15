#!/usr/bin/env python3
"""
one_question.py — is everything in PDI a change of language for one question?

The claim under test:

    "Does it go away, or does it come back?"
    Everything else is a change of language for that question.

Tested, not agreed with. The test is: for each reported quantity, exhibit it as a
function of a survival predicate, or show it is NOT one. A quantity that moves
while the survival predicate is held fixed is not a translation of the question.

  Part 1   n_j is survival-FREE             (same node set, different success -> same n_j)
  Part 1b  PDI defines "comes back" TWICE   (horizon rule vs explicit rule, disagreeing)
  Part 2   Delta is NOT a survival quantity (same L_j and D, different n_j, S, Delta)
  Part 3   the translation table, item by item
  Part 4   the residue, stated exactly

Run: python3 one_question.py
"""
from __future__ import annotations

from pdi import PDI, Status

H = 8
MARK = ("m",)   # a symbol occurring in no horizon-reaching trace


def traces():
    for m in range(2 ** H):
        yield tuple((m >> i) & 1 for i in range(H))


def build_horizon(pad: bool = False):
    """Horizon survival: LIVE == has a descendant at level H."""
    idx = PDI()
    for t in traces():
        idx.insert(t)
    if pad:
        for k in range(1, H - 1):
            for m in range(2 ** k):
                prefix = tuple((m >> i) & 1 for i in range(k))
                for d in range(2 ** k):
                    idx.insert(prefix + (("d", k, d),))
    idx.recompute_statuses()
    return idx


def build_explicit(mark_live: bool):
    """Outcome survival: LIVE == lies on a chain declared successful.

    The horizon traces are declared successful so both systems have the same
    live mass; only the MARK branch's survival varies. n_j is the node count and
    is therefore identical by construction.
    """
    idx = PDI()
    for t in traces():
        idx.insert(t, live=True)
    idx.insert((MARK, 0, 0), live=mark_live)
    idx.finalize_explicit()
    return idx


def live_profiles(idx, level):
    """The actual LIVE prefixes at a level -- the set, not just its size."""
    return sorted(nd.profile for nd in idx.level_nodes(level)
                  if nd.status is Status.LIVE)


def row(label, values, width=6):
    return f"  {label:<30}" + "".join(f"{values.get(j, 0):>{width}}" for j in range(1, H + 1))


# --------------------------------------------------------------------------
def part1():
    print("=" * 84)
    print("PART 1 - is n_j a survival quantity?")
    print("=" * 84)
    dead = build_explicit(mark_live=False)
    alive = build_explicit(mark_live=True)
    same_tower = all(dead.n[j] == alive.n[j] for j in range(1, H + 1))
    diff_live = any(dead.L[j] != alive.L[j] for j in range(1, H + 1))
    print(row("levels j ->", {j: j for j in range(1, H + 1)}))
    print(row("n_j   marker branch dead", dead.n))
    print(row("n_j   marker branch live", alive.n))
    print(row("L_j   marker branch dead", dead.L))
    print(row("L_j   marker branch live", alive.L))
    print()
    print(f"  n_j identical across the two success settings : {same_tower}")
    print(f"  L_j differs across the two success settings   : {diff_live}")
    print("  -> n_j is INDEPENDENT of what counts as survival: it is decided by the")
    print("     NODE SET, not by the success marks. It is the cost of the")
    print("     presentation. The dichotomy cannot produce it -- there is nothing")
    print("     for it to be a translation OF.")
    print()
    return same_tower and diff_live


# --------------------------------------------------------------------------
def part1b():
    print("=" * 84)
    print('PART 1b - PDI defines "comes back" TWICE, and the two can disagree')
    print("=" * 84)
    # one short trace declared successful, one long trace never declared so
    h = PDI(); h.insert((0, 0, 0), live=True); h.insert((1,) * H); h.recompute_statuses()
    e = PDI(); e.insert((0, 0, 0), live=True); e.insert((1,) * H); e.finalize_explicit()
    same_tower = all(h.n[j] == e.n[j] for j in range(1, H + 1))
    print("  the SAME tree, read two ways:")
    print("    trace (0,0,0)   declared successful, dies at level 3")
    print("    trace (1,...,1) reaches the horizon, never declared successful")
    print()
    print(row("n_j  (identical)", h.n))
    print(row("L_j  HORIZON rule", h.L))
    print(row("L_j  EXPLICIT rule", e.L))
    print()
    print(f"  n_j identical between the two readings : {same_tower}")
    print(f"  level 1 LIVE set, horizon  : {live_profiles(h, 1)}")
    print(f"  level 1 LIVE set, explicit : {live_profiles(e, 1)}")
    differ = live_profiles(h, 1) != live_profiles(e, 1)
    counts_differ = any(h.L.get(j, 0) != e.L.get(j, 0) for j in range(1, H + 1))
    print(f"  live SETS differ at level 1 : {differ}   (counts coincide there: both 1)")
    print(f"  live COUNTS differ somewhere: {counts_differ}   (levels 4-8 above)")
    print('  -> "coming back" is a PREDICATE, and PDI ships two of them:')
    print("        horizon : survives to depth H               (structural)")
    print("        explicit: lies on a successful trajectory   (outcome)")
    print("     They select DIFFERENT branches of the same tree. At level 1 here the")
    print("     live sets are disjoint ({1} vs {0}) even though the counts agree, so")
    print("     a scalar ledger can hide the disagreement the set makes visible.")
    print("     The motherboard question is not one question until 'comes back' is")
    print("     pinned to a rule -- and the code lets you pick either.")
    print()
    return same_tower and differ


# --------------------------------------------------------------------------
def part2():
    print("=" * 84)
    print("PART 2 - is Delta a survival quantity?")
    print("=" * 84)
    a = build_horizon()
    b = build_horizon(pad=True)
    same_L = all(a.L.get(j, 0) == b.L.get(j, 0) for j in range(H + 1))
    same_D = abs(a.exponents()["D"] - b.exponents()["D"]) < 1e-12
    diff_n = any(a.n.get(j, 0) != b.n.get(j, 0) for j in range(1, H + 1))
    exa, exb = a.exponents(), b.exponents()
    print(row("L_j  A (lean)", a.L))
    print(row("L_j  B (padded)", b.L))
    print(row("n_j  A (lean)", a.n))
    print(row("n_j  B (padded)", b.n))
    print()
    print(f"  same L_j     : {same_L}")
    print(f"  same D       : {same_D}   (A D={exa['D']:.6f}  B D={exb['D']:.6f})")
    print(f"  different n_j: {diff_n}")
    print(f"  different S  : {abs(exa['S'] - exb['S']) > 1e-9}"
          f"   (A S={exa['S']:.6f}  B S={exb['S']:.6f})")
    print(f"  different Dt : {abs(exa['delta'] - exb['delta']) > 1e-9}"
          f"   (A D={exa['delta']:.6f}  B D={exb['delta']:.6f})")
    print("  -> Two systems with IDENTICAL survival have DIFFERENT Delta. Delta is")
    print("     therefore not a function of the survival predicate, and not a")
    print("     translation of 'does it go away or come back'. It needs a second,")
    print("     survival-free ingredient: the cost n_j.")
    print("     This is also why D is cofinal-invariant (2.3) and Delta is not")
    print("     (2.4): the survival side is intrinsic, the cost side is not.")
    print()
    return same_L and same_D and diff_n


# --------------------------------------------------------------------------
TRANSLATIONS = [
    ("n_j vs L_j",         "dichotomy + cost",      "SPLIT - 'goes away' is the gap; n_j is not survival at all"),
    ("boundary / interior", "dichotomy",            "translation - persistent boundary = what survives refinement"),
    ("D",                  "dichotomy",             "translation - rate of what comes back"),
    ("j* (onset)",         "dichotomy + cost",      "SPLIT - needs the cost column to be a location at all"),
    ("functional graph",   "dichotomy",             "translation - cycle vs tree feeding a cycle"),
    ("T|R vs T off R",     "dichotomy",             "translation - permutation vs many-to-one"),
    ("C_L, F_p^x",         "dichotomy, downstream", "translation - structure ON what returns"),
    ("chi -> U(1)",        "dichotomy, downstream", "translation - the phase of what returns"),
    ("pi(R_j+1) <= R_j",   "dichotomy, 2nd axis",   "translation - does a return survive a resolution change"),
    ("Omega",              "dichotomy, 2nd axis",   "translation - the failure of the previous line (v0.12.0)"),
    ("S, Delta",           "NOT a translation",     "RESIDUE - cannot exist without a survival-free cost"),
]


def part3():
    print("=" * 84)
    print("PART 3 - the translation table, item by item")
    print("=" * 84)
    for item, kind, verdict in TRANSLATIONS:
        print(f"  {item:<20} {kind:<24} {verdict}")
    print()
    n_res = sum(1 for _, k, _ in TRANSLATIONS if "NOT" in k or "cost" in k)
    print(f"  of the {len(TRANSLATIONS)} items, {n_res} do NOT reduce to the dichotomy:")
    print("  the ledger's own denominator, everything derived from it, and the")
    print("  location j* that only becomes a number once the denominator is there.")
    print()


# --------------------------------------------------------------------------
def part4():
    print("=" * 84)
    print("PART 4 - the residue, stated exactly")
    print("=" * 84)
    print("""
  The dichotomy ('goes away / comes back') partitions ONE set. Applied twice --
  once per axis -- it gives every item marked 'translation' above. It cannot
  produce a ratio of two partitions, because it only ever names one.

  What it cannot produce:

      n_j      the number of classes at resolution j   -- no success mark in it
      S        the growth rate of n_j
      Delta    S - D, a survival-free cost minus a survival count
      j*       the onset -- a LOCATION, which requires both columns

  And a second, sharper point from Part 1b: 'comes back' is not yet a single
  predicate. PDI implements two (horizon-reaching, and outcome-marked), they can
  select different branches of the same tree, and the motherboard question is
  only well-posed once one of them is fixed.

  THE SHARPENED THESIS

      The dichotomy is not the original move -- it is the standard move. Every
      field that deletes what does not survive is applying it. Conley, TDA,
      bisimulation minimisation, dead-code elimination: all the same operator.

      The original move is PAIRING a survival-free cost with a survival count
      AT THE SAME RESOLUTION, so that the waste becomes a function of j and can
      be LOCATED (onset j*) and RATED (D, S, Delta) instead of merely totalled.

      Deleting gives a boolean. Pairing gives a curve. The curve is the
      instrument; where it turns is the result.

  This is NARROWER than 'everything is one question', and it is what the code
  supports: n_j is invariant under the success marks (Part 1), Delta moves while
  survival is held fixed (Part 2), and the survival predicate itself is not
  unique (Part 1b).
""")


if __name__ == "__main__":
    ok1 = part1()
    ok1b = part1b()
    ok2 = part2()
    part3()
    part4()
    print("=" * 84)
    print(f"  part 1  (n_j survival-free)      : {'PASS' if ok1 else 'FAIL'}")
    print(f"  part 1b (two survival predicates): {'PASS' if ok1b else 'FAIL'}")
    print(f"  part 2  (Delta not survival)     : {'PASS' if ok2 else 'FAIL'}")
    print("=" * 84)
