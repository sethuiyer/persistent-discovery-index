#!/usr/bin/env python3
"""
test_invertibility.py — the Q1/Q2 attacks, made fail-capable.

invertibility.py has been an entry point since v0.9.0 with no suite. Its printed
claims are cited in SPINE.md §8.1/§8.2, and until now nothing failed if the code
behind them drifted. This suite closes that gap — the last uncovered entry point
listed in INTRODUCTION.md §9.

What is pinned, with warrants:

  Q1  "0 injective induced maps among 216 loops" (n=10) — COMPUTED here over the
      SAME exhaustive grid the entry point states (18 schedules x 3 tabu lengths
      x 4 step counts, full 1024-state transport each — exact, not sampled), and
      consistent with the §18 theorem, which proves that NO schedule in this
      family can be injective. The suite pins the computation; it does not
      reprove the theorem.

  Q2  the augmented-fibre claims (n=8, tabu_len in {1,2}, steps in {4,8}) —
      COMPUTED exact over the full augmented state space (2,304 states at
      tabu_len=1, 18,688 at tabu_len=2):

        - the augmented map (x, tabu) -> (x', tabu') is NOT injective;
        - the refined partition IS T-stable — checked independently here, not
          via the module's own flag;
        - the induced map on the stable quotient is NOT bijective;
        - the documented block counts and collision counts, exactly.

  PROJECTION  run(x, lam, steps) is the memory-projection of
      run_state(x, (), lam, steps), for every base state. This is the claim the
      Q2 motivation rests on ("run() projects the memory away"); it is checked
      exhaustively over the 256 base states, not sampled.

  DETERMINISM  the attacks are seeded (find_instance uses Random(0)); the same
      configuration run twice returns the same result.

Bounds are stated per check. Nothing here upgrades a warrant: Q1 remains
computed-consistent-with-a-theorem, Q2 remains an empirical negative (§8.2).

Run: python3 test_invertibility.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from invertibility import attack_q1, attack_q2, build_transport_aug, refine_aug
from stable_quotient import branch_labels, find_instance
from transport import Searcher

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------
# Q1 — the current fibre: 0 injective among the 216
# --------------------------------------------------------------------------
def test_q1() -> None:
    print("=" * 70)
    print("Q1  injective induced maps over the entry point's 216-loop grid (n=10)")
    print("=" * 70)
    results = attack_q1(10, verbose=False)
    n_inj = sum(1 for r in results if r["bijective"])
    sizes = sorted({r["blocks"] for r in results})

    check("grid is exactly the documented 216 loops", len(results) == 216, str(len(results)))
    check("0 injective induced maps among the 216", n_inj == 0, f"{n_inj} injective")
    check("quotient sizes span the documented 4..33",
          sizes[0] == 4 and sizes[-1] == 33, f"{sizes[0]}..{sizes[-1]}")

    worst = min(results, key=lambda r: r["collision"]["surplus"])
    check("least-collapsing loop: blocks=4, surplus=2 (as printed)",
          worst["blocks"] == 4 and worst["collision"]["surplus"] == 2,
          f"blocks={worst['blocks']} surplus={worst['collision']['surplus']}")
    check("every non-injective loop loses >= 1 block's worth of image",
          all(r["collision"]["surplus"] >= 1 for r in results))
    print()


# --------------------------------------------------------------------------
# Q2 — the augmented fibre, exact over the full augmented space
# --------------------------------------------------------------------------
# documented in SPINE.md §8.2 and printed by invertibility.py
Q2_CONFIGS = [
    # (tabu_len, steps, augmented states, blocks, collisions)
    (1, 4, 2304, 10, 2284),
    (1, 8, 2304, 8, 2292),
    (2, 4, 18688, 22, 18632),
    (2, 8, 18688, 6, 18652),
]
Q2_SCHEDULE = [0.10, 0.50, 0.90, 0.10]


def run_q2(n: int, tabu_len: int, steps: int):
    edges, opt = find_instance(n, [(i, (i + 1) % n) for i in range(n)]
                               + [(i, (i + 4) % n) for i in range(n)], want=2)
    s = Searcher(n, edges, tabu_len=tabu_len)
    T, tabs = build_transport_aug(s, Q2_SCHEDULE, steps, n)
    order = sorted(T)

    # the augmented map itself
    images = set(T.values())
    collisions = len(order) - len(images)

    # branch projection refined over the augmented space
    branch = branch_labels(opt, n)
    part, profile = refine_aug(T, {st: branch[st[0]] for st in order}, order)

    # T-stability, verified independently of the module's own flag:
    # every block must have a single image block under T.
    img_of_block: dict[int, int] = {}
    stable = True
    for st in order:
        b, bi = part[st], part[T[st]]
        if img_of_block.setdefault(b, bi) != bi:
            stable = False
    bm = img_of_block
    bij = len(set(bm.values())) == len(bm)
    return {"states": len(order), "collisions": collisions, "blocks": len(set(part.values())),
            "stable": stable, "bijective": bij, "profile": profile}


def test_q2() -> None:
    print("=" * 70)
    print("Q2  augmented fibre (x, tabu) — exact over the full augmented space")
    print("=" * 70)
    for tabu_len, steps, want_states, want_blocks, want_coll in Q2_CONFIGS:
        r = run_q2(8, tabu_len, steps)
        tag = f"tabu={tabu_len} steps={steps}"
        check(f"[{tag}] augmented space is {want_states} states",
              r["states"] == want_states, str(r["states"]))
        check(f"[{tag}] collision count == {want_coll} (map NOT injective)",
              r["collisions"] == want_coll and r["collisions"] > 0, str(r["collisions"]))
        check(f"[{tag}] refined partition is T-stable", r["stable"])
        check(f"[{tag}] stable quotient has {want_blocks} blocks",
              r["blocks"] == want_blocks, str(r["blocks"]))
        check(f"[{tag}] induced map on the quotient is still many-to-one",
              r["bijective"] is False)
        check(f"[{tag}] refinement terminates at the reported block count",
              r["profile"][-1] == r["blocks"], str(r["profile"]))
    print()


# --------------------------------------------------------------------------
# PROJECTION + DETERMINISM
# --------------------------------------------------------------------------
def test_projection_and_determinism() -> None:
    print("=" * 70)
    print("PROJECTION  run == projection of run_state, over all 256 base states")
    print("=" * 70)
    n = 8
    edges, _ = find_instance(n, [(i, (i + 1) % n) for i in range(n)]
                             + [(i, (i + 4) % n) for i in range(n)], want=2)
    s = Searcher(n, edges, tabu_len=2)
    lam = Q2_SCHEDULE[1]
    bad = 0
    for x in range(1 << n):
        bits = tuple((x >> i) & 1 for i in range(n))
        y_proj = s.run(bits, lam, 4)
        y_full, _ = s.run_state(bits, (), lam, 4)
        if tuple(y_proj) != tuple(y_full):
            bad += 1
    check("run(x, lam, steps) == run_state(x, (), lam, steps)[0] for all 256 states",
          bad == 0, f"{bad} mismatches")
    print()

    print("=" * 70)
    print("DETERMINISM  the same configuration twice, same answer")
    print("=" * 70)
    a = attack_q2(8, Q2_SCHEDULE, 1, 4, verbose=False)
    b = attack_q2(8, Q2_SCHEDULE, 1, 4, verbose=False)
    check("attack_q2 is deterministic", a == b)
    check("attack_q2 agrees with the independent recomputation",
          a["states"] == 2304 and a["blocks"] == 10 and a["injective_aug"] is False,
          str(a))
    print()


if __name__ == "__main__":
    print("=" * 70)
    print("test_invertibility")
    print("=" * 70)
    test_q1()
    test_q2()
    test_projection_and_determinism()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
