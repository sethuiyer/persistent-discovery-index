#!/usr/bin/env python3
"""
test_o2_theorem.py — self-checking suite for o2_theorem.py

O2 asked: exhibit an injective loop, or prove non-injectivity is necessary.
This pins the second outcome. Four things must hold:

  Lemma A   at a global optimum z, delta(z^e_a, b) >= delta(z^e_a, a) for all a,b
  Theorem   |g^-1(z)| >= n - 2*d2(z)
  Chain     the first step of every leg is g and is tabu-free (true); but a
            first-step collision does NOT always compose -- the first step writes
            the tabu list, so G(x) = (g(x), tabu_1(x)) is injective. Pinned.
  Legs      legs with more steps are non-injective EMPIRICALLY, not inherited
  Mechanism the collapse is monotone in energy and maximal at the optima

Run: python3 test_o2_theorem.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from transport import Searcher, all_optima, energy

from o2_theorem import bits, d2_of, flip, instances

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def sz(S: Searcher, z: tuple, lam: float) -> int:
    """|g^-1(z)| = |{ a : v(z^e_a) = a }|."""
    n = S.n
    c = 0
    for a in range(n):
        w = flip(z, a)
        y = S.run(w, lam, 1)
        d = [i for i in range(n) if w[i] != y[i]]
        if len(d) == 1 and d[0] == a:
            c += 1
    return c


def test_instances_are_real() -> None:
    print("sanity: the instance generator produces real instances")
    inst = instances()
    check("generator produced instances", len(inst) > 0, str(len(inst)))
    check("every instance has >=1 optimum", all(len(o) >= 1 for _, _, o in inst))
    check("n varies across instances", len({n for n, _, _ in inst}) > 1)


def test_lemma_a() -> None:
    print("Lemma A -- a is always an argmin at z^e_a")
    total = ok = 0
    for n, es, opt in instances():
        S = Searcher(n=n, edges=es, tabu_len=3)
        for z in opt:
            for a in range(n):
                da = S.delta(flip(z, a), a)
                for b in range(n):
                    total += 1
                    ok += S.delta(flip(z, a), b) >= da
    check("checked a non-trivial number of triples", total > 1000, str(total))
    check("delta(z^e_a,b) >= delta(z^e_a,a) for all a,b", ok == total, f"{ok}/{total}")


def test_theorem_bound() -> None:
    print("Theorem -- |g^-1(z)| >= n - 2*d2(z)")
    checked = held = 0
    for n, es, opt in instances():
        for lam in (0.0, 0.35, 0.5, 0.8, 1.0):
            S = Searcher(n=n, edges=es, tabu_len=3)
            for z in opt:
                checked += 1
                if sz(S, z, lam) >= n - 2 * d2_of(z, opt):
                    held += 1
    check("cases checked", checked > 100, str(checked))
    check("bound holds in every case", held == checked, f"{held}/{checked}")


def test_corollary_non_injective() -> None:
    print("Corollary -- the fibre at an optimum has >= 2 preimages")
    tot = noninj = 0
    for n, es, opt in instances():
        for lam in (0.0, 0.5, 1.0):
            S = Searcher(n=n, edges=es, tabu_len=3)
            for z in opt:
                tot += 1
                noninj += sz(S, z, lam) >= 2
    check("every optimum is a non-injective fibre", noninj == tot, f"{noninj}/{tot}")


def test_first_step_is_tabu_free() -> None:
    print("Chain -- the first step is tabu-free, so tabu cannot rescue it")
    n, es, opt = instances(count=1)[0]
    sizes = {}
    for tl in (2, 3, 4, 5, 6, 8):
        S = Searcher(n=n, edges=es, tabu_len=tl)
        sizes[tl] = len({S.run(bits(m, n), 0.5, 1) for m in range(1 << n)})
    check("one-step image identical across tabu lengths",
          len(set(sizes.values())) == 1, str(sizes))
    check("and strictly smaller than the state space",
          list(sizes.values())[0] < (1 << n), str(sizes))


def test_legs_with_more_steps_are_non_injective() -> None:
    print("Legs -- more steps stay non-injective (EMPIRICAL, not inherited from g)")
    n, es, opt = instances(count=1)[0]
    S = Searcher(n=n, edges=es, tabu_len=3)
    for steps in (1, 2, 4, 8):
        img = {}
        for m in range(1 << n):
            y = S.run(bits(m, n), 0.5, steps)
            img[y] = img.get(y, 0) + 1
        collapse = (1 << n) - len(img)
        check(f"steps={steps}: leg is non-injective", collapse > 0, f"collapse={collapse}")


def test_first_step_collision_does_not_compose() -> None:
    print("Chain -- a first-step collision does NOT always compose (counterexample)")
    found = None
    for (n, es, opt) in instances():
        S = Searcher(n=n, edges=es, tabu_len=3)
        for lam in (0.0, 0.5, 1.0):
            for z in opt:
                Sset = []
                for a in range(n):
                    w = flip(z, a)
                    y = S.run(w, lam, 1)
                    d = [i for i in range(n) if w[i] != y[i]]
                    if len(d) == 1 and d[0] == a:
                        Sset.append(a)
                if len(Sset) >= 2:
                    a, b = Sset[0], Sset[1]
                    if S.run(flip(z, a), lam, 4) != S.run(flip(z, b), lam, 4):
                        found = (n, lam, a, b)
                        break
            if found:
                break
        if found:
            break
    check("at least one g-collision re-separates within 4 steps",
          found is not None, str(found))
    check("so 'non-injectivity composes' is FALSE as stated", found is not None, str(found))


def test_collapse_is_at_the_optima() -> None:
    print("Mechanism -- collapse is monotone in energy, maximal at the optima")
    n, es, opt = instances(count=1)[0]
    S = Searcher(n=n, edges=es, tabu_len=3)
    by_e: dict[int, list[int]] = {}
    for m in range(1 << n):
        z = bits(m, n)
        by_e.setdefault(energy(z, es), []).append(sz(S, z, 0.5))
    emin, emax = min(by_e), max(by_e)
    lo = sum(by_e[emin]) / len(by_e[emin])
    hi = sum(by_e[emax]) / len(by_e[emax])
    check("optima have |S| = n (every perturbation returns)", lo == n, f"{lo} vs {n}")
    check("highest-energy states have |S| = 0", hi == 0, str(hi))
    # The ordering is APPROXIMATE, not pointwise: mean |S| bumps upward at a few
    # energy levels. What is exact is the maximum (attained at the optima) and the
    # floor (0). Pin those, and pin the aggregate trend as a concordance rate.
    by_energy = [(energy(z2, es), sz(S, z2, 0.5)) for z2 in
                 (bits(m, n) for m in range(1 << n))]
    conc = tot_pairs = 0
    for (e1, s1), (e2, s2) in ((a, b) for a in by_energy for b in by_energy):
        if e1 < e2:
            tot_pairs += 1
            conc += s1 >= s2
    rate = conc / tot_pairs
    check("aggregate trend strongly decreasing (concordance > 0.9)", rate > 0.9, f"{rate:.4f}")
    check("ordering is NOT exact (so the claim stays 'concentrated')", rate < 1.0, f"{rate:.4f}")


if __name__ == "__main__":
    print("=" * 70)
    print("test_o2_theorem")
    print("=" * 70)
    test_instances_are_real()
    test_lemma_a()
    test_theorem_bound()
    test_corollary_non_injective()
    test_first_step_is_tabu_free()
    test_legs_with_more_steps_are_non_injective()
    test_first_step_collision_does_not_compose()
    test_collapse_is_at_the_optima()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
