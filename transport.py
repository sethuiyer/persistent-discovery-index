#!/usr/bin/env python3
"""
transport.py — does a closed loop of presentations move the persistent branch?

The PDI result proved that transient structure is PRESENTATION-dependent. That is
path dependence in the weak sense ("which presentation"). Holonomy needs the
stronger thing: dependence on the ROUTE, so that a closed loop in parameter space
returns the external parameter but not the internal state.

This module tests the prerequisite, on the smallest object where it can exist.

Requirements for a non-trivial transport:
  (a) DEGENERACY      more than one optimum, so "which branch" is a real question
  (b) WALLS           a parameter family where the behaviour changes
  (c) HISTORY         a stateful process, x_{t+1} = F(x_t, lam_t)

A memoryless solver has x = f(lam), so every closed schedule returns f(lam_0)
and the transport is identity BY CONSTRUCTION. The earlier Sudoku probe showed
(a) and (b) exist there and (c) does not. This module supplies (c).

Construction:
  problem  small Max-Cut instance with exactly TWO optimal cuts, found by
           enumeration, so the branch set is finite and known
  searcher deterministic min-conflicts local search with a TABU list
           (the memory) and a lam-controlled tie-break (the presentation)
  branch   canonical projection: settle(state) under pure greedy descent to an
           optimum, then label that optimum. Well-defined for any state.

Observable:
  Hol(gamma): B_0 -> B'_0   the branch at the end of the loop vs the start.

Tests that separate a real monodromy from annealing drift:
  reverse   T(gamma^-1) should equal T(gamma)^-1
  loop^2    T(gamma^2) should equal T(gamma)^2
  order     smallest k with T(gamma^k) = identity
  all-branch  apply the loop to EVERY starting branch; a genuine monodromy is a
              permutation of the branch set, not a drift that depends on where
              you happened to start

Run: python3 transport.py
"""
from __future__ import annotations

import itertools
import random
from collections import deque
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# problem: Max-Cut on a small graph with a prescribed degeneracy
# --------------------------------------------------------------------------
def energy(x: tuple, edges: list) -> int:
    """Number of UNCUT edges. 0 means every edge is cut."""
    return sum(1 for i, j in edges if x[i] == x[j])


def all_optima(n: int, edges: list) -> list[tuple]:
    vals = [(energy(tuple((m >> i) & 1 for i in range(n)), edges), m)
            for m in range(1 << n)]
    best = min(v for v, _ in vals)
    return [tuple((m >> i) & 1 for i in range(n)) for v, m in vals if v == best]


def find_instance(n: int, edges: list, want: int = 2, tries: int = 4000):
    """Reroll edge sets until the number of optima equals `want`."""
    rng = random.Random(0)
    for _ in range(tries):
        k = len(edges)
        es = sorted({tuple(sorted(rng.sample(range(n), 2))) for _ in range(k)})
        if len(es) != k:
            continue
        opt = all_optima(n, es)
        if len(opt) == want:
            return es, opt
    raise RuntimeError("no instance with the requested degeneracy found")


# --------------------------------------------------------------------------
# the stateful searcher
# --------------------------------------------------------------------------
@dataclass
class Searcher:
    """Deterministic min-conflicts search with tabu memory.

    state  : the assignment (x)
    memory : a deque of recently flipped vertices, never re-flipped while hot
    lam    : tie-break policy among equally-damaging flips. lam=0 prefers the
             lowest vertex index, lam=1 the highest; intermediate values prefer
             the vertex nearest lam*(n-1). This is the presentation parameter.
    """
    n: int
    edges: list
    tabu_len: int = 3

    def delta(self, x, v) -> int:
        d = 0
        for i, j in self.edges:
            if i == v or j == v:
                before = x[i] == x[j]
                xi, xj = x[i], x[j]
                if i == v:
                    xi ^= 1
                if j == v:
                    xj ^= 1
                after = xi == xj
                d += int(after) - int(before)
        return d

    def best_flip(self, x, lam, tabu):
        best_key, best_v = None, None
        for v in range(self.n):
            if v in tabu:
                continue
            key = (self.delta(x, v), abs(v - lam * (self.n - 1)))
            if best_key is None or key < best_key:
                best_key, best_v = key, v
        return best_v

    def run(self, x, lam: float, steps: int, tabu_len: int | None = None):
        """Carry the state (and its tabu memory) forward under presentation lam."""
        x = list(x)
        tl = self.tabu_len if tabu_len is None else tabu_len
        tabu: deque = deque(maxlen=tl)
        for _ in range(steps):
            v = self.best_flip(x, lam, tabu)
            if v is None:
                break
            x[v] ^= 1
            tabu.append(v)
        return tuple(x)

    def settle(self, x, cap: int = 500) -> tuple:
        """Pure greedy descent to a local optimum. Used to label a branch."""
        x = list(x)
        for _ in range(cap):
            best_v, best_d = None, 0
            for v in range(self.n):
                d = self.delta(x, v)
                if d < best_d:
                    best_d, best_v = d, v
            if best_v is None:
                break
            x[best_v] ^= 1
        return tuple(x)


# --------------------------------------------------------------------------
# loop driver
# --------------------------------------------------------------------------
@dataclass
class Transport:
    searcher: Searcher
    optima: list[tuple]
    steps: int = 12
    steps_per_leg: int = 8

    def branch(self, x) -> int:
        """Canonical projection onto the branch set: the nearest optimum by
        Hamming distance, ties broken by index.

        `settle()` is NOT used here because greedy descent can stop at a
        non-global local optimum, which would leave the state unlabelled. The
        projection must be a total function on states for the loop to be
        well-defined.
        """
        return min((sum(a != b for a, b in zip(x, o)), i)
                   for i, o in enumerate(self.optima))[1]

    def run_loop(self, schedule: list[float]) -> dict:
        """schedule = [lam0, lam1, ..., lam0]; the last entry closes the loop."""
        x = self.optima[0]
        marks = [self.branch(x)]
        for lam in schedule[1:]:
            x = self.searcher.run(x, lam, self.steps_per_leg)
            marks.append(self.branch(x))
        return {"schedule": schedule, "branches": marks,
                "start": marks[0], "end": marks[-1], "final_state": x}

    def permutation(self, schedule: list[float]) -> dict:
        """Apply the loop to EVERY starting branch."""
        out = {}
        for b, x0 in enumerate(self.optima):
            x = x0
            for lam in schedule[1:]:
                x = self.searcher.run(x, lam, self.steps_per_leg)
            out[b] = self.branch(x)
        return out

    def branch_determined(self, schedule, samples: int = 60, seed: int = 0,
                          noise: float = 0.30):
        """THE decisive test. A transport is only a permutation of branches if the
        image depends on the BRANCH alone.

        Sample states near each optimum, keep the ones the projection still
        labels with that branch, push each around the loop, and collect the
        resulting branches. If the image set for a branch has more than one
        element, the loop is NOT well-defined on branches -- it is state
        dependent drift, and calling it a monodromy is unjustified regardless of
        whether the identity test failed.
        """
        rng = random.Random(seed)
        images: dict[int, set] = {}
        counted: dict[int, int] = {}
        for b, o in enumerate(self.optima):
            seen: set = set()
            k = 0
            for _ in range(samples * 20):
                if k >= samples:
                    break
                x = tuple(v ^ (1 if rng.random() < noise else 0) for v in o)
                if self.branch(x) != b:
                    continue
                k += 1
                y = x
                for lam in schedule[1:]:
                    y = self.searcher.run(y, lam, self.steps_per_leg)
                seen.add(self.branch(y))
            images[b] = seen
            counted[b] = k
        return images, counted

    def fibre_determined(self, schedule, samples: int = 400, seed: int = 0,
                         min_group: int = 3):
        """Refine the fibre. Group starting states by their greedy-descent
        attractor (the basin), and ask whether the loop's image is constant
        within each basin.

        If branches are too coarse a fibre but basins are the right one, this
        returns all singletons and the transport IS a map -- just on basins
        rather than on optima. If it still returns multi-element images, the
        process has no bundle structure at this resolution at all.
        """
        rng = random.Random(seed)
        groups: dict[tuple, set] = {}
        for _ in range(samples):
            x = tuple(rng.randint(0, 1) for _ in range(self.searcher.n))
            f = self.searcher.settle(x)
            y = x
            for lam in schedule[1:]:
                y = self.searcher.run(y, lam, self.steps_per_leg)
            groups.setdefault(f, set()).add(self.branch(y))
        big = {f: v for f, v in groups.items() if len(v) >= 1}
        sizes = [len(v) for v in groups.values()]
        return {"n_basins": len(groups),
                "n_determined": sum(1 for s in sizes if s == 1),
                "n_ambiguous": sum(1 for s in sizes if s > 1),
                "max_image": max(sizes) if sizes else 0,
                "groups": big}

    def power(self, schedule: list[float], k: int) -> list[float]:
        """Concatenate the loop k times (cycle starts and ends at schedule[0])."""
        core = schedule[1:]
        out = [schedule[0]]
        for _ in range(k):
            out.extend(core)
        return out


# --------------------------------------------------------------------------
# permutation helpers
# --------------------------------------------------------------------------
def compose(p, q):
    return {k: p[v] for k, v in q.items()}


def inverse(p):
    return {v: k for k, v in p.items()}


def perm_power(p, k):
    r = {b: b for b in p}
    for _ in range(k):
        r = compose(p, r)
    return r


def order_of(p, cap=12):
    r = {b: b for b in p}
    for k in range(1, cap + 1):
        r = compose(p, r)
        if all(r[b] == b for b in p):
            return k
    return None


def fmt(p):
    return "  ".join(f"{chr(65+k)}->{chr(65+v)}" for k, v in sorted(p.items()))


# --------------------------------------------------------------------------
if __name__ == "__main__":
    n = 12
    base = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 4) % n) for i in range(n)]
    edges, opt = find_instance(n, base, want=2)

    print("=" * 96)
    print("transport.py - closed loops in presentation space")
    print("=" * 96)
    print(f"  Max-Cut, n={n}, {len(edges)} edges")
    print(f"  optima enumerated over all {1 << n} configurations: {len(opt)}")
    for i, o in enumerate(opt):
        print(f"    branch {chr(65+i)}: {''.join(map(str, o))}   uncut={energy(o, edges)}")

    lam0, lam1, lam2 = 0.10, 0.50, 0.90
    gamma = [lam0, lam1, lam2, lam0]
    gamma_inv = [lam0, lam2, lam1, lam0]

    print(f"\n  loop: {' -> '.join(f'{l:.2f}' for l in gamma)}")
    print(f"  {'tabu':>4} {'steps':>6} {'perm':>16} {'bij':>5} {'id':>5} "
          f"{'rev=inv':>8} {'sq=sq':>6} {'ord':>4}  branch-determined?")
    print("  " + "-" * 92)

    for tabu_len in (2, 3, 4, 5):
        for steps in (4, 8, 16, 32):
            s_ = Searcher(n, edges, tabu_len=tabu_len)
            T = Transport(s_, opt, steps_per_leg=steps)

            fwd = T.permutation(gamma)
            rev = T.permutation(gamma_inv)
            sq = T.permutation(T.power(gamma, 2))
            idn = {b: b for b in fwd}

            bij = len(set(fwd.values())) == len(fwd)
            is_id = fwd == idn
            rev_is_inv = rev == inverse(fwd)
            sq_is_sq = sq == compose(fwd, fwd)
            o = order_of(fwd)

            images, _ = T.branch_determined(gamma)
            det = all(len(v) <= 1 for v in images.values())
            if det:
                det_txt = "YES"
            else:
                det_txt = "NO " + " ".join(
                    f"{chr(65+b)}:{{{','.join(chr(65+x) for x in sorted(v))}}}"
                    for b, v in sorted(images.items()))

            print(f"  {tabu_len:>4} {steps:>6} {fmt(fwd):>16} {str(bij):>5} "
                  f"{str(is_id):>5} {str(rev_is_inv):>8} {str(sq_is_sq):>6} "
                  f"{str(o):>4}  {det_txt}")

    print()
    print("=" * 96)
    print("refining the fibre: is the loop determined by the greedy-descent BASIN?")
    print("=" * 96)
    for tabu_len, steps in ((3, 16), (4, 8), (5, 32)):
        s_ = Searcher(n, edges, tabu_len=tabu_len)
        T = Transport(s_, opt, steps_per_leg=steps)
        d = T.fibre_determined(gamma)
        print(f"  tabu={tabu_len} steps={steps}: basins={d['n_basins']}  "
              f"determined={d['n_determined']}  ambiguous={d['n_ambiguous']}  "
              f"largest image={d['max_image']}")

    print()
    print("=" * 96)
    print("verdict logic")
    print("=" * 96)
    print("""
  A genuine branch monodromy needs ALL FOUR:

      bijective          the loop maps the branch set to itself
      branch-determined  the image depends on the BRANCH, not the fine state
      rev = inv          the reverse loop undoes the forward loop
      sq = sq            two loops equal composing the map with itself

  A non-identity result that fails `branch-determined` is STATE DRIFT, not
  monodromy. Two states sitting in the same branch get transported to different
  branches, so there is no map on branches at all -- and therefore no
  permutation, no order, and nothing for a Berry phase to be a phase OF.
""")
