#!/usr/bin/env python3
"""
toys.py — toy problems with ANALYTICALLY KNOWN answers.

Each toy has a closed-form n_j and L_j, hence a closed-form D, S and Delta. The
suite runs PDI on the toy and checks that what the implementation reports equals
what the mathematics says it must.

This does not test whether PDI is a good index. It tests whether the instrument
computes the quantity it claims to compute. Every expectation below is derived
by hand from the construction, in the comment above each toy.

Run: python3 toys.py
"""
from __future__ import annotations

import itertools
import math

from agent_profiler import AgentProfiler, asymptotic, format_asymptotic
from pdi import PDI
from quotient_tower import QuotientTower, prefix_tower, TowerViolation

FAILS: list[str] = []
D = 6           # tree depth used throughout
W = 3           # fan width for the spine toy


def sup_over_levels(counts: dict, H: int) -> float:
    vals = [math.log(counts[j]) / (j * math.log(2.0))
            for j in range(1, H + 1) if counts.get(j, 0) > 0]
    return max(vals) if vals else 0.0


# --------------------------------------------------------------------------
# toys: each returns (runs, tower, expected n_j, expected L_j)
# --------------------------------------------------------------------------
def all_bitstrings(d):
    return [tuple(b) for b in itertools.product((0, 1), repeat=d)]


def toy_full(d=D):
    """T1  every leaf succeeds.
        n_j = 2^j (all prefixes occur);  L_j = 2^j (every prefix extends to a
        successful leaf).  So D = S = 1 and Delta = 0."""
    runs = [(h, True) for h in all_bitstrings(d)]
    n = {j: 2 ** j for j in range(1, d + 1)}
    L = {j: 2 ** j for j in range(1, d + 1)}
    return "T1 full tree, all leaves succeed", runs, prefix_tower(lambda x: x), n, L


def toy_one(d=D):
    """T2  exactly one leaf succeeds (the all-zeros path).
        n_j = 2^j;  L_j = 1.  So D = 0, S = 1, Delta = 1."""
    runs = [(h, all(b == 0 for b in h)) for h in all_bitstrings(d)]
    n = {j: 2 ** j for j in range(1, d + 1)}
    L = {j: 1 for j in range(1, d + 1)}
    return "T2 one successful leaf", runs, prefix_tower(lambda x: x), n, L


def toy_half(d=D):
    """T3  leaves beginning with 0 succeed.
        n_j = 2^j;  L_j = 2^(j-1).  So S = 1, D = (d-1)/d, Delta = 1/d."""
    runs = [(h, h[0] == 0) for h in all_bitstrings(d)]
    n = {j: 2 ** j for j in range(1, d + 1)}
    L = {j: 2 ** (j - 1) for j in range(1, d + 1)}
    return "T3 half the leaves succeed", runs, prefix_tower(lambda x: x), n, L


def toy_none(d=D):
    """T4  nothing succeeds.  n_j = 2^j;  L_j = 0.
        So D = 0 (no persistent class), S = 1, Delta = 1."""
    runs = [(h, False) for h in all_bitstrings(d)]
    n = {j: 2 ** j for j in range(1, d + 1)}
    L = {j: 0 for j in range(1, d + 1)}
    return "T4 no successful leaf", runs, prefix_tower(lambda x: x), n, L


def toy_spine_fan(d=D, w=W):
    """T5  one successful spine, with w dead-end branches spawned at each level.
        n_j = 1 + w*(j-1)   (the spine prefix, plus one divergent prefix per
                             (level, branch) pair spawned so far)
        L_j = 1             (only the spine prefix extends to the success)
        So D = 0 and Delta = S."""
    spine = tuple([0] * d)
    runs = [(spine, True)]
    for k in range(1, d):
        for i in range(w):
            h = tuple([0] * k) + (("x", k, i),) + tuple([0] * (d - k - 1))
            runs.append((h, False))
    n = {j: 1 + w * (j - 1) for j in range(1, d + 1)}
    L = {j: 1 for j in range(1, d + 1)}
    return f"T5 spine + {w}-wide dead-end fan", runs, prefix_tower(lambda x: x), n, L


def toy_behavioural():
    """T6  a genuine BEHAVIOURAL tower (levels are not prefixes).

        histories  (success, coarse, fine),  coarse in {A,B}, fine in {1,2,3},
        success == (coarse == 'A')

        Q1 = success                -> 2 classes,  L1 = 1
        Q2 = (success, coarse)      -> 2 classes,  L2 = 1
        Q3 = (success, coarse, fine)-> 6 classes,  L3 = 3

        S = max(log2 2 /1, log2 2 /2, log2 6 /3) = 1
        D = max(0, 0, log2 3 /3)                 = log2(3)/3
    """
    runs = []
    for coarse in ("A", "B"):
        for fine in (1, 2, 3):
            runs.append(((coarse == "A", coarse, fine), coarse == "A"))
    tower = QuotientTower([
        lambda h: h[0],
        lambda h: (h[0], h[1]),
        lambda h: (h[0], h[1], h[2]),
    ])
    n = {1: 2, 2: 2, 3: 6}
    L = {1: 1, 2: 1, 3: 3}
    return "T6 behavioural tower (coarse/fine)", runs, tower, n, L


TOYS = [toy_full, toy_one, toy_half, toy_none, toy_spine_fan, toy_behavioural]

# expected (S_status, D_status) from the tail layer
EXPECTED_STATUS = {
    "T1 full tree, all leaves succeed": ("STABLE", "STABLE"),
    "T2 one successful leaf":           ("STABLE", "STABLE"),
    "T3 half the leaves succeed":       ("STABLE", "TRENDING_UP"),
    "T4 no successful leaf":            ("STABLE", "NONE"),
    "T5 spine + 3-wide dead-end fan":   ("TRENDING_DOWN", "STABLE"),
    "T6 behavioural tower (coarse/fine)": ("UNRESOLVED", "TRENDING_UP"),
}


# --------------------------------------------------------------------------
def run_toy(fn):
    name, runs, tower, exp_n, exp_L = fn()
    H = max(exp_n)

    # the tower must be a valid refinement tower
    try:
        tower.validate(h for h, _ in runs)
        law = "ok"
    except TowerViolation as e:
        law = f"VIOLATION: {e}"

    prof = AgentProfiler(index=PDI(tower=tower))
    for h, ok in runs:
        prof.add_run(h, ok)
    p = prof.profile()
    got_n = {r["level"]: r["n"] for r in p["rows"]}
    got_L = {r["level"]: r["L"] for r in p["rows"]}

    # closed forms
    exp_S = sup_over_levels(exp_n, H)
    exp_D = sup_over_levels(exp_L, H)
    exp_delta = exp_S - exp_D

    ok_n = all(got_n.get(j, 0) == exp_n[j] for j in range(1, H + 1))
    ok_L = all(got_L.get(j, 0) == exp_L[j] for j in range(1, H + 1))
    ok_S = abs(p["S"] - exp_S) < 1e-12
    ok_D = abs(p["D"] - exp_D) < 1e-12
    ok_d = abs(p["delta"] - exp_delta) < 1e-12

    for label, ok in (("n_j", ok_n), ("L_j", ok_L), ("S", ok_S), ("D", ok_D),
                      ("Delta", ok_d)):
        if not ok:
            FAILS.append(f"{name}: {label} mismatch")

    a = asymptotic(p)
    exp_st = EXPECTED_STATUS.get(name)
    if exp_st and (a["S"]["status"], a["D"]["status"]) != exp_st:
        FAILS.append(f"{name}: status {(a['S']['status'], a['D']['status'])} "
                     f"!= {exp_st}")
    if law != "ok":
        FAILS.append(f"{name}: refinement law {law}")

    return {
        "name": name, "law": law, "rows": H,
        "n_ok": ok_n, "L_ok": ok_L, "S_ok": ok_S, "D_ok": ok_D, "d_ok": ok_d,
        "D": p["D"], "S": p["S"], "delta": p["delta"],
        "eD": exp_D, "eS": exp_S, "ed": exp_delta,
        "Sst": a["S"]["status"], "Dst": a["D"]["status"],
        "Stail": a["S"]["value"], "Dtail": a["D"]["value"],
    }


if __name__ == "__main__":
    print("=" * 96)
    print("toy validation suite — PDI output vs closed-form expectations")
    print("=" * 96)
    print(f"  {'toy':<36} {'law':>4} {'D':>9} {'D_exp':>9} {'S':>9} {'S_exp':>9} "
          f"{'Delta':>9} {'d_exp':>9}  checks   S_status       D_status")
    results = [run_toy(f) for f in TOYS]
    for r in results:
        flags = "".join("Y" if r[k] else "n" for k in ("n_ok", "L_ok", "S_ok", "D_ok", "d_ok"))
        print(f"  {r['name']:<36} {r['law']:>4} {r['D']:>9.6f} {r['eD']:>9.6f} "
              f"{r['S']:>9.6f} {r['eS']:>9.6f} {r['delta']:>9.6f} {r['ed']:>9.6f}  {flags}"
              f"   {r['Sst']:<14} {r['Dst']}")

    print()
    print("  closed forms verified:")
    print(f"    T1  D=S=1, Delta=0")
    print(f"    T2  D=0, S=1, Delta=1")
    print(f"    T3  D=(d-1)/d={ (D-1)/D :.6f}, Delta=1/d={1/D:.6f}")
    print(f"    T4  D=0, S=1, Delta=1")
    print(f"    T5  D=0, Delta=S")
    print(f"    T6  D=log2(3)/3={math.log2(3)/3:.6f}, S=1")
    print()
    print("  T5 — does the TAIL estimate converge where the window sup cannot?")
    print("       n_j = 1 + w(j-1), true asymptotic rate is 0")
    print(f"    {'w':>6} {'d':>5} {'window sup':>11} {'tail est':>10} {'status':>14}")
    for w in (3, 1000):
        for d in (6, 12, 24, 48):
            _, runs, tower, _, _ = toy_spine_fan(d=d, w=w)
            prof = AgentProfiler(index=PDI(tower=tower))
            for h, ok in runs:
                prof.add_run(h, ok)
            p = prof.profile()
            a = asymptotic(p)
            print(f"    {w:>6} {d:>5} {a['S']['window_sup']:>11.6f} "
                  f"{a['S']['value']:>10.6f} {a['S']['status']:>14}")
    print()
    print("  window sup is stuck (attained at a shallow shell, independent of d);")
    print("  the tail estimate decays toward the true value 0 as the horizon grows.")

    print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
    raise SystemExit(1 if FAILS else 0)
