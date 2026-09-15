#!/usr/bin/env python3
"""
test_proof_awareness.py — self-checking suite for proof_awareness.py

Pins two things:
  1. the falsification is real: each old bound label is violated by an
     observation-consistent continuation
  2. the fix holds: the labels now carry their hypothesis, and the
     no-classes / not-monotone cases claim no bound at all

Run: python3 test_proof_awareness.py     (exit 0 on success)
"""
from __future__ import annotations

import sys

from agent_profiler import asymptotic
from proof_awareness import limsup

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def rep(seq, k=4):
    return asymptotic({"d_seq": {i + 1: v for i, v in enumerate(seq)},
                       "s_seq": {}, "horizon": len(seq)}, k)["D"]


def test_limsup_helper() -> None:
    print("the limsup helper")
    check("constant sequence", abs(limsup([0.5] * 10) - 0.5) < 1e-12)
    check("decaying finite sequence -> its last term (1/49)",
          abs(limsup([1.0 / j for j in range(1, 50)]) - 1 / 49) < 1e-12)
    check("the SAME prefix, extended with zeros, has limsup 0",
          abs(limsup([1.0 / j for j in range(1, 50)] + [0.0] * 10)) < 1e-12)
    check("...so the prefix does not determine the limsup (the whole point)",
          abs(limsup([1.0 / j for j in range(1, 50)])
              - limsup([1.0 / j for j in range(1, 50)] + [0.0] * 10)) > 1e-3)
    check("rising then collapsing", abs(limsup([0.1, 0.9] + [0.0] * 10)) < 1e-12)
    check("jump at the end", abs(limsup([0.1] * 5 + [9.0] * 5) - 9.0) < 1e-12)


def test_labels_are_falsifiable() -> None:
    print("each bound label is falsifiable (the unfixable part)")
    cases = [
        ("TRENDING_UP", [0.10, 0.20, 0.30, 0.40], [1.0 / j for j in range(5, 400)]),
        ("TRENDING_DOWN", [0.40, 0.30, 0.20, 0.10], [9.0] * 400),
        ("STABLE", [0.50, 0.50, 0.50, 0.50], [9.0] * 400),
    ]
    for want, obs, cont in cases:
        r = rep(obs)
        check(f"{want}: status detected", r["status"] == want, r["status"])
        true_ls = limsup(obs + cont)
        check(f"{want}: a continuation violates the reported value",
              abs(true_ls - r["value"]) > 1e-9,
              f"reported {r['value']:.6f}, true limsup {true_ls:.6f}")


def test_labels_now_carry_hypotheses() -> None:
    print("the fix: labels carry their hypothesis")
    up = rep([0.10, 0.20, 0.30, 0.40])
    down = rep([0.40, 0.30, 0.20, 0.10])
    flat = rep([0.50, 0.50, 0.50, 0.50])
    check("TRENDING_UP label names the hypothesis", "IF" in up["bound"], up["bound"])
    check("TRENDING_DOWN label names the hypothesis", "IF" in down["bound"], down["bound"])
    check("STABLE is 'window-exact', not 'exact'",
          flat["bound"].startswith("window-exact") and flat["bound"] != "exact",
          flat["bound"])
    check("no label is the bare word 'exact'", up["bound"] != "exact"
          and down["bound"] != "exact" and flat["bound"] != "exact")
    check("no label is the bare word 'unknown'", "unknown" not in (
        up["bound"] + down["bound"] + flat["bound"]))


def test_honest_refusals() -> None:
    print("the honest refusals still claim nothing")
    none_r = asymptotic({"d_seq": {}, "s_seq": {}, "horizon": 5})["D"]
    check("NONE status", none_r["status"] == "NONE", none_r["status"])
    check("NONE claims no bound", "no classes" in none_r["bound"], none_r["bound"])
    # non-monotone tail -> UNRESOLVED -> no bound
    unres = rep([0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6])
    check("UNRESOLVED status", unres["status"] == "UNRESOLVED", unres["status"])
    check("UNRESOLVED claims no bound", unres["bound"] == "no bound claimed",
          unres["bound"])


if __name__ == "__main__":
    print("=" * 70)
    print("test_proof_awareness")
    print("=" * 70)
    test_limsup_helper()
    test_labels_are_falsifiable()
    test_labels_now_carry_hypotheses()
    test_honest_refusals()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
