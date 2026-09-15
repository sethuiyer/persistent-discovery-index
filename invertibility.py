#!/usr/bin/env python3
"""
invertibility.py — go after the one missing property.

v0.8.0 constructed the fibre: the coarsest T-stable quotient of the branch
partition, 4-40 blocks from 4096 states, on which the loop transport is a
well-defined function. The remaining obstruction is that T is MANY-TO-ONE, so it
is not a permutation and there is no order and no monodromy.

Two questions, attacked separately:

  Q1  does an injective loop exist on the CURRENT fibre (states = x alone)?
  Q2  does AUGMENTING the fibre with the memory recover invertibility?

Q2 has a principled motivation, not a hopeful one. The searcher is a stateful
process; `run()` projects the tabu memory away and returns only x. That
projection is a place where information is destroyed by construction. A
deterministic process can look irreversible after projecting away memory while
its augmented dynamics (x, tabu) is far closer to reversible.

Both attacks run over the FULL state space and are exact, not sampled.

Run: python3 invertibility.py
"""
from __future__ import annotations

import itertools
from collections import Counter

from stable_quotient import (block_map, branch_labels, build_transport,
                             coarsest_stable, functional_graph, pack, unpack)
from transport import Searcher, find_instance


# --------------------------------------------------------------------------
# Q1 — injective loops on the current fibre
# --------------------------------------------------------------------------
def collision_report(part, T):
    """Where does information get destroyed? Blocks that share an image."""
    bm = block_map(part, T)
    img = Counter(bm.values())
    colliding = {b for b, c in img.items() if c > 1}
    lost = sum(1 for b in bm if bm[b] in colliding)
    return {"colliding_images": len(colliding), "blocks_feeding_them": lost,
            "blocks": len(bm), "surplus": len(bm) - len(img)}


def attack_q1(n: int, want_degenerate: int = 2, verbose: bool = True):
    base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
    edges, opt = find_instance(n, base, want=want_degenerate)
    branch = branch_labels(opt, n)
    states = 1 << n

    rng_schedules = []
    for a in (0.05, 0.10, 0.25):
        for b in (0.50, 0.75, 0.90):
            rng_schedules.append([0.0, a, b, 0.0])
            rng_schedules.append([0.0, b, a, 0.0])

    results = []
    for sch in rng_schedules:
        for tabu_len in (1, 2, 3):
            for steps in (2, 4, 8, 16):
                s = Searcher(n, edges, tabu_len=tabu_len)
                T = build_transport(s, sch, steps, n)
                part, profile = coarsest_stable(branch, T)
                bm = block_map(part, T)
                bij = len(set(bm.values())) == len(bm)
                coll = collision_report(part, T)
                results.append({
                    "schedule": sch, "tabu": tabu_len, "steps": steps,
                    "blocks": len(set(part)), "bijective": bij,
                    "profile": profile, "collision": coll,
                })

    n_inj = sum(1 for r in results if r["bijective"])
    sizes = Counter(r["blocks"] for r in results)
    if verbose:
        print(f"  Q1  injective loops on the CURRENT fibre   (n={n}, {states} states)")
        print(f"      loops tested         : {len(results)}")
        print(f"      injective induced map: {n_inj}")
        print(f"      quotient sizes       : {dict(sorted(sizes.items()))}")
        if n_inj:
            for r in results:
                if r["bijective"]:
                    print(f"        INJECTIVE: sch={r['schedule']} tabu={r['tabu']} "
                          f"steps={r['steps']} blocks={r['blocks']}")
        else:
            worst = min(results, key=lambda r: r["collision"]["surplus"])
            print(f"      least-collapsing loop: blocks={worst['blocks']} "
                  f"surplus={worst['collision']['surplus']} "
                  f"(sch={worst['schedule']} tabu={worst['tabu']} steps={worst['steps']})")
    return results


# --------------------------------------------------------------------------
# Q2 — augment the fibre with memory
# --------------------------------------------------------------------------
def aug_tabu_states(n: int, tabu_len: int):
    out = [()]
    for k in range(1, tabu_len + 1):
        out.extend(itertools.product(range(n), repeat=k))
    return out


def build_transport_aug(searcher: Searcher, schedule, steps: int, n: int):
    """T on (x, tabu) -- memory NOT projected away."""
    tabs = aug_tabu_states(n, searcher.tabu_len)
    tindex = {t: i for i, t in enumerate(tabs)}
    T = {}
    for x in range(1 << n):
        bits = unpack(x, n)
        for ti, tab in enumerate(tabs):
            y = bits
            t = tab
            for lam in schedule[1:]:
                y, t = searcher.run_state(y, t, lam, steps)
            T[(x, ti)] = (pack(y), tindex[t])
    return T, tabs


def refine_aug(T, initial, order):
    """Partition refinement on a dict-based state space."""
    part = dict(initial)
    profile = [len(set(part.values()))]
    while True:
        ids = {}
        new = {}
        for st in order:
            key = (part[st], part[T[st]])
            b = ids.get(key)
            if b is None:
                b = len(ids)
                ids[key] = b
            new[st] = b
        k = len(ids)
        profile.append(k)
        part = new
        if k == profile[-2]:
            break
    return part, profile


def attack_q2(n: int, schedule, tabu_len: int, steps: int, verbose: bool = True):
    base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
    edges, opt = find_instance(n, base, want=2)
    s = Searcher(n, edges, tabu_len=tabu_len)
    T, tabs = build_transport_aug(s, schedule, steps, n)

    order = sorted(T)
    states = len(order)

    # (a) is the AUGMENTED dynamics itself injective?
    images = set(T.values())
    inj_aug = len(images) == states

    # (b) refine the branch projection (memory-blind) over the augmented space
    branch = branch_labels(opt, n)
    initial = {st: branch[st[0]] for st in order}
    part, profile = refine_aug(T, initial, order)
    bm = {}
    stable = True
    for st in order:
        t = part[T[st]]
        if bm.setdefault(part[st], t) != t:
            stable = False
    bij = len(set(bm.values())) == len(bm)

    if verbose:
        print(f"\n  Q2  augmented fibre (x, tabu)   n={n} tabu_len={tabu_len} steps={steps}")
        print(f"      augmented states     : {states}  (base {1<<n} x {len(tabs)} tabu states)")
        print(f"      augmented map injective: {inj_aug}"
              + (f"  -> the AUGMENTED dynamics is reversible" if inj_aug
                 else f"  ({states - len(images)} collisions remain)"))
        print(f"      refinement profile   : {' -> '.join(map(str, profile))}")
        print(f"      stable quotient      : {len(set(part.values()))} blocks  (stable={stable})")
        print(f"      induced map bijective: {bij}"
              + ("   <-- PERMUTATION RECOVERED" if bij else "   (still many-to-one)"))
        if bij:
            o = 1
            cur = {b: bm[b] for b in bm}
            acc = dict(cur)
            while not all(acc[b] == b for b in acc) and o < 64:
                acc = {b: cur[acc[b]] for b in acc}
                o += 1
            fg = functional_graph(bm)
            print(f"      order of T           : {o}")
            print(f"      cycle structure      : {fg['cycle_lengths']}")
    return {"states": states, "injective_aug": inj_aug, "blocks": len(set(part.values())),
            "bijective": bij, "profile": profile}


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 88)
    print("invertibility — the one missing property")
    print("=" * 88)
    print()
    attack_q1(10)
    print()
    print("=" * 88)
    print("augmenting the fibre with memory")
    print("=" * 88)
    for tabu_len in (1, 2):
        for steps in (4, 8):
            attack_q2(8, [0.10, 0.50, 0.90, 0.10], tabu_len, steps)
    print()
    print("=" * 88)
    print("reading")
    print("=" * 88)
    print("""
  Q1 asks whether the current fibre already admits an injective loop. If no loop
  tested is injective, the collapse is not a bad choice of schedule -- it is
  structural, and no amount of schedule search fixes it.

  Q2 asks whether the collapse is an artefact of PROJECTING THE MEMORY AWAY. The
  searcher keeps a tabu list; `run()` discards it and returns only the
  configuration. Two different tabu histories reaching the same configuration
  become indistinguishable, which is exactly a collision. Carrying (x, tabu)
  through keeps that information in the state.
""")
