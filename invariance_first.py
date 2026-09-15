#!/usr/bin/env python3
"""
invariance_first.py — one principle, or three?

The claim under test:

    "The invariance-first principle: build equivalence classes only modulo
     provable indistinguishability. Lindenbaum-Tarski, Hennessy-Milner, explicit
     coercion, 'no experiment without protocol', and 'make illegal states
     unrepresentable' are the same principle. PDI instantiates all of them."

Tested rather than agreed with. The five names are NOT one claim; they are three,
with different logical shapes, and PDI has different standing on each:

  (a) WITNESS-GATED CONSTRUCTION
        you may not perform operation O unless you supply a witness W
        - Lindenbaum-Tarski's FORM (quotient only modulo provable equivalence)
        - explicit coercions in Coq / Lean / Idris (convert only with a proof)
        - Minsky: make illegal states unrepresentable
      PDI: STRONG.  QuotientTower.validate raises TowerViolation; exponents()
      carries S_shallow/D_shallow; the estimator carries a convergence status.

  (b) CANONICITY
        the quotient is determined by the BEHAVIOUR, not by the presentation
        - Lindenbaum-Tarski's GUARANTEE (the algebra is canonical in the logic)
      PDI: ABSENT. The tower is an input, not derived (pdi.py: tower=None). The
      ledger says so itself: row 2.3 proves only COFINAL invariance, row 9.1
      leaves canonicity OPEN and records it as KNOWN TO VARY.

  (c) AGREEMENT OF TWO INDEPENDENT EQUIVALENCES
        a coarse observational notion equals a fine structural one
        - Hennessy-Milner: bisimilar iff modal-indistinguishable (a THEOREM)
      PDI: CONDITIONAL. v0.12.0's Omega = 0 exactly when the refinement axis is
      T-invariant, and Omega != 0 on the inclusion axis.

(a) is an axiom you enforce. (b) is a property you hope for. (c) is a theorem you
prove or refute. Conflating them is the error this file exists to prevent.

Run: python3 invariance_first.py
"""
from __future__ import annotations

import math

from pdi import PDI
from quotient_tower import QuotientTower, TowerViolation

H = 8


def traces():
    for m in range(2 ** H):
        yield tuple((m >> i) & 1 for i in range(H))


# ==========================================================================
# PART 1 — the gate is on the WITNESS, not on the result
# ==========================================================================
def part1():
    print("=" * 84)
    print("PART 1 - witness-gated construction (the gate)")
    print("=" * 84)

    good = QuotientTower([lambda h: h[0], lambda h: h[:2], lambda h: h[:3]])
    bad = QuotientTower([lambda h: h[:2], lambda h: h[0], lambda h: h[:3]])
    corpus = [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]

    ok_good, ok_bad = None, None
    try:
        ok_good = good.validate(corpus)
    except TowerViolation as e:
        ok_good = f"VIOLATION: {e}"
    try:
        bad.validate(corpus)
        ok_bad = "accepted"
    except TowerViolation as e:
        ok_bad = f"VIOLATION ({str(e)[:44]}...)"

    print(f"  refining tower   (h[0] -> h[:2] -> h[:3]) : checked {ok_good}")
    print(f"  non-refining     (h[:2] -> h[0] -> h[:3]) : {ok_bad}")
    print()
    print("  -> The gate fires on the WITNESS (the refinement law on the corpus),")
    print("     not on the output. You cannot build the object without the proof.")
    print("     This is the shape shared by Lindenbaum-Tarski's construction, the")
    print("     explicit-coercion rule, and 'make illegal states unrepresentable'.")
    print()
    return isinstance(ok_good, int) and "VIOLATION" in str(ok_bad)


# ==========================================================================
# PART 2 — but the quotient is NOT canonical. Ask the ledger's own question.
# ==========================================================================
def reindexed(runs, marks, prepend):
    """The SAME histories and the SAME success marks, at a shifted resolution
    index. A legal tower either way -- validate() accepts both."""
    idx = PDI()
    for t, live in zip(runs, marks):
        idx.insert((("p",) + t) if prepend else t, live=live)
    idx.recompute_statuses()
    return idx


def part2():
    print("=" * 84)
    print("PART 2 - presentation-dependence, and what PDI does about it")
    print("=" * 84)
    runs = list(traces())
    marks = [t[0] == t[1] for t in runs]           # a mark on the SAME histories

    a = reindexed(runs, marks, prepend=False)
    b = reindexed(runs, marks, prepend=True)
    ea, eb = a.exponents(), b.exponents()

    print("  identical traces, identical success marks, resolution index shifted")
    print("  by one prepended symbol. Both towers pass the refinement-law gate.\n")
    print(f"  {'j':>3} {'L_j (A)':>9} {'log2L/j':>9}   {'L_j (B)':>9} {'log2L/j':>9}")
    Ha = max(a.L)
    Hb = max(b.L)
    for j in range(1, max(Ha, Hb) + 1):
        sa = "" if j not in a.L else f"{math.log(a.L[j], 2)/j:>9.5f}"
        sb = "" if j not in b.L else f"{math.log(b.L[j], 2)/j:>9.5f}"
        print(f"  {j:>3} {a.L.get(j,''):>9} {sa:>9}   {b.L.get(j,''):>9} {sb:>9}")
    print()
    print("  FINITE-SCALE LAYER -- what the repo explicitly calls not a rate")
    print(f"    A:  D = {ea['D']:.6f}  attained at j={ea['D_at']}  D_shallow={ea['D_shallow']}")
    print(f"    B:  D = {eb['D']:.6f}  attained at j={eb['D_at']}  D_shallow={eb['D_shallow']}")
    differs = abs(ea["D"] - eb["D"]) > 1e-12
    print(f"    presentation-dependent : {differs}")
    print()
    print("  ASYMPTOTIC LAYER -- the tail estimate, with its status")
    from agent_profiler import asymptotic

    def dseq(idx, H):
        return {j: math.log(idx.L[j]) / (-math.log(idx.eps(j)))
                for j in range(1, H + 1) if idx.L.get(j, 0) > 0}

    aa = asymptotic({"d_seq": dseq(a, Ha), "s_seq": {}, "horizon": Ha})["D"]
    ab = asymptotic({"d_seq": dseq(b, Hb), "s_seq": {}, "horizon": Hb})["D"]
    print(f"    A:  value={aa['value']:.6f}  status={aa['status']:<13} bound={aa['bound']}")
    print(f"    B:  value={ab['value']:.6f}  status={ab['status']:<13} bound={ab['bound']}")
    print()
    print("  The true limsup is 1 for BOTH: A has log2L_j/j = 1 exactly, and B has")
    print("  (j-1)/j -> 1. So the presentations differ ONLY at finite scale, and the")
    print("  asymptotic layer does not claim otherwise -- it reports B as a LOWER")
    print("  BOUND with status TRENDING_UP, which is correct (1 >= 8/9), while A is")
    print("  STABLE at 1.")
    print()
    print("  -> PDI does NOT eliminate presentation-dependence. It QUARANTINES it:")
    print("     the finite-scale number is still reported, and it is reported with")
    print("     a flag saying it is not a rate, and the asymptotic number carries")
    print("     the status of its own convergence. The principle here is not")
    print("     'quantities are invariant'. It is 'you may not assert an invariance")
    print("     you do not have -- the representation must carry the status'.")
    print("     That is the same shape as the explicit-coercion rule: the claim is")
    print("     not forbidden, it must come with its witness.")
    print()
    return differs


# ==========================================================================
# PART 3 — the ledger already says this. Two invariances, one proved.
# ==========================================================================
def part3():
    print("=" * 84)
    print("PART 3 - the ledger's own accounting")
    print("=" * 84)
    print("""
  PDI does not claim canonicity. It distinguishes two invariances and proves
  only the weaker one:

    row 2.3   cofinal invariance of D          PROVED
              (D is unchanged by dropping finitely many coarse levels)

    row 9.1   canonicity of the stable fibre   OPEN -- known to vary
              (the fibre is loop-independent)

  These are not the same property. Cofinal invariance says the answer survives
  TRUNCATION of the index. Canonicity says the answer survives a change of
  PRESENTATION.

  Part 2 is a LIVE INSTANCE of a third, already-proved row:

    row 3.1   the finite-window sup is not the limsup     PROVED by counterexample

  Dropping B's first level recovers A, and the finite-window sup moves 8/9 -> 1
  while the limsup stays 1 for both. So Part 2 is row 3.1 firing on a
  presentation shift, and the asymptotic layer with its convergence status is the
  repo's response to row 3.1. The cofinal-invariant object survives; the
  finite-scale number does not, and is labelled.

  So the deepest instantiation of the invariance-first principle in this repo is
  not an object that satisfies it. It is the LEDGER ROW that records its absence.
  The principle, applied to PDI itself, forbids PDI from printing D as though it
  were a property of the task -- which is exactly why row 2.3 is about D being
  intrinsic and row 2.4 is about Delta NOT being cofinal-invariant, and why the
  estimator carries a convergence status rather than a number.
""")


# ==========================================================================
def part4():
    print("=" * 84)
    print("PART 4 - the split: three claims, not one")
    print("=" * 84)
    rows = [
        ("witness-gated construction", "(a) axiomatic",
         "Lindenbaum-Tarski FORM, explicit coercion, Minsky", "PDI: STRONG"),
        ("canonicity", "(b) property to hope for",
         "Lindenbaum-Tarski GUARANTEE", "PDI: ABSENT (9.1 open)"),
        ("agreement of two equivalences", "(c) theorem",
         "Hennessy-Milner", "PDI: CONDITIONAL (v0.12)"),
    ]
    for name, kind, source, standing in rows:
        print(f"  {name:<30} {kind:<24} {source:<46} {standing}")
    print()
    print("  (a) is an axiom you enforce.  (b) is a property you hope for.")
    print("  (c) is a theorem you prove or refute.  They are not one principle,")
    print("  and PDI's standing on them is not the same.")
    print()
    print("  The honest form of the original claim:")
    print()
    print("      PDI enforces (a) everywhere it can -- TowerViolation on the")
    print("      refinement law, a convergence status on every asymptotic number,")
    print("      S_shallow/D_shallow so a non-rate is never printed as a rate.")
    print()
    print("      PDI does NOT have (b), and says so in row 9.1 instead of")
    print("      asserting it. That row is the principle applied to the ledger.")
    print()
    print("      PDI has one instance of (c) -- Omega = 0 iff the refinement axis")
    print("      is T-invariant -- and one counterexample, on the inclusion axis.")
    print()


if __name__ == "__main__":
    ok1 = part1()
    ok2 = part2()
    part3()
    part4()
    print("=" * 84)
    print(f"  part 1 (gate fires on the witness)      : {'PASS' if ok1 else 'FAIL'}")
    print(f"  part 2 (canonicity fails, 9.1 confirmed): {'PASS' if ok2 else 'FAIL'}")
    print("=" * 84)
