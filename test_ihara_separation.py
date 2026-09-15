#!/usr/bin/env python3
"""
test_ihara_separation.py — pins a NEGATIVE result about zeta invariants.

zeta_separation.py asks whether the Ihara/Bass zeta family can separate the
§15.2 pair (identical ledger (n_j, L_j), non-isomorphic discovery structure).
It cannot, and this suite makes that fail loudly — so no later turn can
"discover" Ihara, assume it is richer than the ledger, and ship a claim the
witness does not support.

Checks, each with its warrant:

  computed   §15.2 pair: Z^-1 == 1 and Bass det == 1-u^2 for BOTH — no separation
  computed   every forest tested has Bass det == (1-u^2)^(#components):
             the determinant is shape-blind, a function of component count only
  verified   Bass determinant == prime-cycle product on C3, C4, C3+C3, C6 (full
             degree) and K4 (truncated at u^8, since K4 has prime cycles of
             unbounded length). This is an external closed-form oracle; it is
             not a self-consistency check.
  computed   positive control: C3+C3 and C6 share degree sequence and (|V|,|E|),
             and zeta separates them — so the negative is not vacuity. Zeta is
             sharp on cycles and empty on trees.
  computed   what DOES separate §15.2: the characteristic polynomial differs, and
             so does the AHU canonical form (§15.2's existing witness)

Run: python3 test_ihara_separation.py     (exit 0 on success)
"""
from __future__ import annotations

import sys
from itertools import combinations

from zeta_separation import (CYCLIC, FORESTS, TRIE_A, TRIE_B, _p1_minus_u2_pow,
                             ahu, bass_determinant, charpoly, ihara_from_bass,
                             ihara_from_cycles, prime_cycles, show, trunc)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_oracle() -> None:
    print("=" * 72)
    print("ORACLE  Bass determinant == prime-cycle product (external check)")
    print("=" * 72)
    for name, n, edges, _c in CYCLIC:
        ml = 2 * n
        check(f"[{name}] Bass det == prod(1-u^len) over prime cycles (full degree)",
              ihara_from_bass(n, edges) == ihara_from_cycles(n, edges, ml))
    # K4: prime cycles are unbounded in length, so only a truncated comparison
    # is available; the two sides must agree through u^8.
    n4, e4 = 4, list(combinations(range(4), 2))
    check("[K4] Bass det == prime-cycle product, truncated at u^8",
          trunc(ihara_from_bass(n4, e4), 8) == trunc(ihara_from_cycles(n4, e4, 8), 8),
          "truncated oracle failed")
    print()


def test_witness_no_separation() -> None:
    print("=" * 72)
    print("THE WITNESS  §15.2 pair — zeta is IDENTICALLY blind")
    print("=" * 72)
    (na, ea), (nb, eb) = TRIE_A, TRIE_B
    za = ihara_from_cycles(na, ea, 2 * na)
    zb = ihara_from_cycles(nb, eb, 2 * nb)
    ba = bass_determinant(na, ea)
    bb = bass_determinant(nb, eb)

    check("trie A has no non-backtracking closed cycle",
          len(prime_cycles(na, ea, 2 * na)) == 0)
    check("trie B has no non-backtracking closed cycle",
          len(prime_cycles(nb, eb, 2 * nb)) == 0)
    check("Z^-1 == 1 for both (trees are zeta-trivial)", za == [1] and zb == [1],
          f"{show(za)} vs {show(zb)}")
    check("Bass det == 1 - u^2 for both", ba == [1, 0, -1] and bb == [1, 0, -1],
          f"{show(ba)} vs {show(bb)}")
    check("therefore zeta does NOT separate the §15.2 pair", za == zb and ba == bb)
    print()


def test_forest_law() -> None:
    print("=" * 72)
    print("THE LAW  Bass det(forest) = (1-u^2)^(#components) — shape-blind")
    print("=" * 72)
    for name, n, edges in FORESTS:
        c = n - len(edges)
        got = bass_determinant(n, edges)
        check(f"[{name}] det == (1-u^2)^{c}", got == _p1_minus_u2_pow(c), show(got))
    check("two different 2-component forests share a determinant (shape-blind)",
          bass_determinant(6, [(0, 1), (1, 2), (3, 4), (4, 5)])
          == bass_determinant(6, [(0, 1), (0, 2), (0, 3), (4, 5)]))
    print()


def test_positive_control_and_what_does_separate() -> None:
    print("=" * 72)
    print("CONTROLS")
    print("=" * 72)
    # zeta is not vacuous: it separates two graphs a degree summary cannot.
    c33 = bass_determinant(6, [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)])
    c6 = bass_determinant(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)])
    deg = lambda n, ed: sorted((sum(1 for u, v in ed if u == i or v == i)
                                for i in range(n)), reverse=True)
    e33 = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)]
    e6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)]
    check("C3+C3 and C6 share a degree sequence and (|V|,|E|)",
          deg(6, e33) == deg(6, e6) == [2] * 6 and len(e33) == len(e6) == 6)
    check("zeta SEPARATES C3+C3 from C6 (negative is not vacuity)", c33 != c6,
          f"{show(c33)} vs {show(c6)}")

    # what separates the §15.2 pair today
    (na, ea), (nb, eb) = TRIE_A, TRIE_B
    check("char poly separates the §15.2 pair",
          charpoly(na, ea) != charpoly(nb, eb),
          f"{show(charpoly(na, ea), 'x')} vs {show(charpoly(nb, eb), 'x')}")
    check("AHU canonical form separates the §15.2 pair",
          ahu(na, ea) != ahu(nb, eb), f"{ahu(na, ea)} vs {ahu(nb, eb)}")
    print()


if __name__ == "__main__":
    print("=" * 72)
    print("test_ihara_separation")
    print("=" * 72)
    test_oracle()
    test_witness_no_separation()
    test_forest_law()
    test_positive_control_and_what_does_separate()
    print("=" * 72)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
