#!/usr/bin/env python3
"""
test_collision_mechanism.py — self-checking suite for collision_mechanism.py

SPINE §18 cited this file before it existed. It exists now, and it asserts rather
than prints: collision_mechanism.py ended with PASS/FAIL text but no sys.exit(1),
so it could not fail a build.

Pins the three results the §18 proof rests on:
  1. the composition lemma  T injective ==> first leg injective
  2. the characterisation   g(x)=g(y) <=> x^y = {v(x),v(y)}, v(x) != v(y)
  3. the mechanism          a collision is a SWAP, two bits, reciprocal argmins

Run: python3 test_collision_mechanism.py     (exit 0 on success)
"""
from __future__ import annotations

import sys
from collections import defaultdict

from collision_mechanism import EDGES, N, bits, one_step_vertex
from transport import Searcher

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_composition_lemma() -> None:
    print("1. composition lemma")
    S = Searcher(N, EDGES, tabu_len=3)

    def leg_inj(lam, steps):
        img = {}
        for m in range(1 << N):
            y = S.run(bits(m), lam, steps)
            img[y] = img.get(y, 0) + 1
        return all(c == 1 for c in img.values())

    def comp_inj(sch, steps):
        img = {}
        for m in range(1 << N):
            y = bits(m)
            for lam in sch[1:]:
                y = S.run(y, lam, steps)
            img[y] = img.get(y, 0) + 1
        return all(c == 1 for c in img.values())

    bad = checked = 0
    for sch in ([0.1, 0.5, 0.9, 0.1], [0.1, 0.9, 0.1], [0.3, 0.7, 0.3]):
        for steps in (1, 4, 8):
            checked += 1
            if comp_inj(sch, steps) and not leg_inj(sch[1], steps):
                bad += 1
    check("checked real composed loops", checked > 0, str(checked))
    check("no violation: composed injective => first leg injective", bad == 0, str(bad))


def test_characterisation() -> None:
    print("2. collision characterisation")
    total = ok = 0
    for tl in (2, 3, 4):
        for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
            S = Searcher(N, EDGES, tabu_len=tl)
            vof, gof = {}, {}
            for m in range(1 << N):
                v, y = one_step_vertex(S, bits(m), lam)
                vof[m], gof[m] = v, y
            pre = defaultdict(list)
            for m in range(1 << N):
                pre[gof[m]].append(m)
            for ms in pre.values():
                for i in range(len(ms)):
                    for j in range(i + 1, len(ms)):
                        x, y = ms[i], ms[j]
                        diff = {b for b in range(N) if bits(x)[b] != bits(y)[b]}
                        a, b = vof[x], vof[y]
                        total += 1
                        if a is not None and b is not None and a != b and diff == {a, b}:
                            ok += 1
    check("checked a non-trivial number of colliding pairs", total > 1000, str(total))
    check("x^y == {v(x),v(y)} with v(x)!=v(y) in every case", ok == total, f"{ok}/{total}")


def test_swap_mechanism() -> None:
    print("3. the mechanism is a swap")
    S = Searcher(N, EDGES, tabu_len=3)
    lam = 0.5
    vof, gof = {}, {}
    for m in range(1 << N):
        v, y = one_step_vertex(S, bits(m), lam)
        vof[m], gof[m] = v, y
    pre = defaultdict(list)
    for m in range(1 << N):
        pre[gof[m]].append(m)

    best = None
    for ms in pre.values():
        if len(ms) < 2:
            continue
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                d = sum(a != b for a, b in zip(bits(ms[i]), bits(ms[j])))
                if best is None or d < best[0]:
                    best = (d, ms[i], ms[j])
    check("a colliding pair exists", best is not None)
    if best:
        d, xm, ym = best
        check("cleanest collision is at Hamming distance 2", d == 2, str(d))
        check("the two states have different argmins", vof[xm] != vof[ym],
              f"{vof[xm]} vs {vof[ym]}")
        # reciprocal: each wants to flip the other's distinguishing bit
        check("x wants to flip the bit only y has, and vice versa",
              {vof[xm], vof[ym]} == {b for b in range(N) if bits(xm)[b] != bits(ym)[b]})


def test_no_injective_leg() -> None:
    print("4. no leg is injective")
    total = injective = 0
    for tl in (2, 3, 4, 5):
        S = Searcher(N, EDGES, tabu_len=tl)
        for steps in (1, 2, 4, 8, 16):
            for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
                img = {S.run(bits(m), lam, steps) for m in range(1 << N)}
                total += 1
                injective += len(img) == (1 << N)
    check("legs tested", total > 50, str(total))
    check("none injective", injective == 0, f"{injective} injective of {total}")


if __name__ == "__main__":
    print("=" * 70)
    print("test_collision_mechanism")
    print("=" * 70)
    test_composition_lemma()
    test_characterisation()
    test_swap_mechanism()
    test_no_injective_leg()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
