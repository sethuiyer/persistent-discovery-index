#!/usr/bin/env python3
"""
zeta_separation.py — can a zeta-type invariant separate what the ledger cannot?

THE QUESTION (strand proposed after v0.21.0)
  §15.2 exhibits two traces with identical ledger projections (n_j, L_j) but
  non-isomorphic discovery structure. The ledger is lossy; the information lives
  in the edges. A natural candidate for a *richer*, edge-sensitive invariant is
  the Ihara zeta function

      Z_G(u) = prod_{[P]} (1 - u^{len P})^{-1},   [P] primitive non-backtracking
                                                  closed cycles,

  with the Ihara–Bass closed form

      Z_G(u)^{-1} = (1 - u^2)^{|E|-|V|} det(I - u A + u^2 (D - I)).

  Does Z separate the §15.2 pair where (n_j, L_j) does not?

THE ANSWER, COMPUTED HERE: NO — and for a structural reason, not a numerical one.
  * The §15.2 pair is a TREE. A tree has no non-backtracking closed cycle, so
    Z = 1 identically, for BOTH members. The Bass determinant is
    det(I - uA + u^2(D-I)) = 1 - u^2 for BOTH. The zeta family is identically
    blind on the very witness §15 uses.
  * The mechanism: zeta listens to edges ONLY THROUGH CYCLES. "Edges" and
    "cycles" are not the same information, and this witness has zero cycles.
  * Computed over every forest tested, det = (1 - u^2)^{#components}. The Bass
    determinant of a forest depends only on the NUMBER OF COMPONENTS — it carries
    no tree-shape information at all.

SO WHERE DOES ZETA BELONG? On the RECURRENT part (§6).
  Positive control: C3+C3 and C6 have the same degree sequence (all 2) and the
  same (|V|, |E|) = (6, 6), but Z^{-1} = (1-u^3)^4 vs (1-u^6)^2. Zeta SEPARATES
  them. Blind to acyclic structure, sharp on cyclic structure.

That locates zeta in the spine exactly: the recurrent core R is the union of
cycles, the transient remainder F\\R is trees. Zeta is the right instrument for R
and is provably empty on F\\R. It is a COMPLEMENT to the ledger, not a stronger
replacement:

    ledger (n_j, L_j)    blind to arrangement         sees levels
    zeta  Z_G(u)         blind to acyclic structure   sees cycles
    char poly            partial (cospectral trees)   sees some shape
    AHU canonical form   complete (rooted trees)      sees everything

  And what does separate the §15.2 pair today is the last two: the rooted-tree
  canonical form (already used in §15.2) and, for this pair, the characteristic
  polynomial (8x^3 - 6x^5 + x^7 vs 7x^3 - 6x^5 + x^7). Zeta is not needed for
  that job and cannot do it.

A WORD ON THE TEMPTING ANALOGY.
  Ihara's standard reduction strips degree-1 vertices to reach the 2-core; PDI's
  §6 splits a functional graph into a recurrent core and transient trees. These
  are DIFFERENT constructions on different objects: a graph leaf-pruning versus
  the union of cycles of a map T. The word "core" is shared; the construction is
  not. Treat the resemblance as an analogy to test, not an identification — the
  same caution §12 applies to "persistent".

WARRANTS
  proved     a tree has no non-backtracking closed cycles, so Z = 1
  computed   every polynomial is exact rational arithmetic (no floats)
  verified   Bass det == prime-cycle product for C3, C4, C3+C3, C6 (full degree)
             and K4 (truncated: K4 has prime cycles of unbounded length)
  negative   zeta does NOT separate the §15.2 pair
  computed   det(I-uA+u^2(D-I)) = (1-u^2)^{#components} on every forest tested

Run: python3 zeta_separation.py
"""
from __future__ import annotations

from fractions import Fraction as F
from itertools import combinations

# --------------------------------------------------------------------------
# exact rational polynomial arithmetic
# --------------------------------------------------------------------------
def cut(p: list) -> list:
    p = list(p)
    while p and p[-1] == 0:
        p.pop()
    return p or [F(0)]


def mul(a: list, b: list) -> list:
    if not any(a) or not any(b):
        return [F(0)]
    r = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    r[i + j] += x * y
    return cut(r)


def trunc(p: list, d: int) -> list:
    return cut(p[: d + 1])


def _det_frac(M: list) -> F:
    n = len(M)
    M = [row[:] for row in M]
    sign = F(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if M[r][c] != 0), None)
        if piv is None:
            return F(0)
        if piv != c:
            M[c], M[piv] = M[piv], M[c]
            sign = -sign
        pv = M[c][c]
        for r in range(c + 1, n):
            if M[r][c]:
                f = M[r][c] / pv
                for k in range(c, n):
                    M[r][k] -= f * M[c][k]
    d = sign
    for i in range(n):
        d *= M[i][i]
    return d


def _interp(vals: list, deg: int) -> list:
    """Exact interpolation of P(0..deg) -> monomial coefficients."""
    n = deg + 1
    A = [[F(i) ** k for k in range(n)] + [vals[i]] for i in range(n)]
    for c in range(n):
        piv = next(r for r in range(c, n) if A[r][c] != 0)
        A[c], A[piv] = A[piv], A[c]
        pv = A[c][c]
        A[c] = [v / pv for v in A[c]]
        for r in range(n):
            if r != c and A[r][c]:
                f = A[r][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [A[i][n] for i in range(n)]


# --------------------------------------------------------------------------
# graphs
# --------------------------------------------------------------------------
def _matrix(n: int, edges: list):
    A = [[F(0)] * n for _ in range(n)]
    deg = [0] * n
    for u, v in edges:
        A[u][v] += 1
        A[v][u] += 1
        deg[u] += 1
        deg[v] += 1
    return A, deg


def bass_determinant(n: int, edges: list) -> list:
    """det(I - uA + u^2(D-I)) as exact rational coefficients. Degree <= 2|E|."""
    A, deg = _matrix(n, edges)
    d = 2 * len(edges)

    def at(u: F) -> F:
        M = [[F(0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    M[i][j] = F(1) + u * u * F(deg[i] - 1)
                if A[i][j]:
                    M[i][j] -= u * A[i][j]
        return _det_frac(M)

    return cut(_interp([at(F(i)) for i in range(d + 1)], d))


def charpoly(n: int, edges: list) -> list:
    """det(xI - A), degree n."""
    A, _ = _matrix(n, edges)

    def at(x: F) -> F:
        M = [[F(0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    M[i][j] = x
                if A[i][j]:
                    M[i][j] -= A[i][j]
        return _det_frac(M)

    return cut(_interp([at(F(i)) for i in range(n + 1)], n))


def prime_cycles(n: int, edges: list, maxlen: int) -> list:
    """Primitive non-backtracking tailless closed walks, up to rotation.
    Orientation is NOT identified (Ihara counts both)."""
    nb: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        nb[u].append(v)
        nb[v].append(u)
    found = set()
    for s in range(n):
        stack = [(s, [s])]
        while stack:
            v, path = stack.pop()
            if len(path) - 1 >= maxlen:
                continue
            for w in nb[v]:
                if len(path) >= 2 and w == path[-2]:      # no immediate backtrack
                    continue
                np_ = path + [w]
                if w == s and len(np_) >= 4:              # closed, length >= 3
                    cyc = np_[:-1]
                    k = len(cyc)
                    if cyc[1] == cyc[-1]:                 # tailless
                        continue
                    if any(all(cyc[i] == cyc[(i + d) % k] for i in range(k))
                           for d in range(1, k) if k % d == 0):   # primitive
                        continue
                    found.add(min(tuple(cyc[i:] + cyc[:i]) for i in range(k)))
                if len(np_) - 1 < maxlen:
                    stack.append((w, np_))
    return sorted(found, key=lambda c: (len(c), c))


def ihara_from_cycles(n: int, edges: list, maxlen: int) -> list:
    """Z^{-1} = prod (1 - u^{len P}) over the enumerated prime cycles."""
    z = [F(1)]
    for c in prime_cycles(n, edges, maxlen):
        k = len(c)
        z = mul(z, [F(1)] + [F(0)] * (k - 1) + [F(-1)])
    return cut(z)


def ihara_from_bass(n: int, edges: list) -> list:
    """Z^{-1} = (1-u^2)^{|E|-|V|} * det(I-uA+u^2(D-I)), for min degree >= 2."""
    e, v = len(edges), n
    if e - v < 0:
        raise ValueError("Bass form needs |E| >= |V|; prune leaves first")
    pref = [F(1)]
    for _ in range(e - v):
        pref = mul(pref, [F(1), F(0), F(-1)])
    return cut(mul(pref, bass_determinant(n, edges)))


def ahu(n: int, edges: list, root: int = 0) -> str:
    """Canonical form (AHU) of a rooted tree — complete for rooted trees."""
    children: dict[int, list[int]] = {i: [] for i in range(n)}
    seen = {root}
    stack = [root]
    while stack:
        v = stack.pop()
        for w in ([u for u, x in edges if x == v] + [x for u, x in edges if u == v]):
            if w not in seen:
                seen.add(w)
                children[v].append(w)
                stack.append(w)

    def emit(v: int) -> str:
        return "(" + "".join(sorted(emit(c) for c in children[v])) + ")"
    return emit(root)


def show(p: list, var: str = "u") -> str:
    return " + ".join(f"{c}{var}^{i}" for i, c in enumerate(p) if c) or "0"


# --------------------------------------------------------------------------
# the witness: §15.2
# --------------------------------------------------------------------------
TRIE_A = (7, [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)])
TRIE_B = (7, [(0, 1), (0, 2), (1, 3), (1, 4), (1, 5), (2, 6)])

# forests: (name, n, edges) — the Bass determinant law det = (1-u^2)^{#comp}
FORESTS = [
    ("P2", 2, [(0, 1)]),
    ("P3", 3, [(0, 1), (1, 2)]),
    ("P4", 4, [(0, 1), (1, 2), (2, 3)]),
    ("star K1,4", 5, [(0, 1), (0, 2), (0, 3), (0, 4)]),
    ("trie A", *TRIE_A),
    ("trie B", *TRIE_B),
    ("two P3 (c=2)", 6, [(0, 1), (1, 2), (3, 4), (4, 5)]),
    ("K1,3 + P2 (c=2)", 6, [(0, 1), (0, 2), (0, 3), (4, 5)]),
]

# cyclic controls: (name, n, edges, components)
CYCLIC = [
    ("C3", 3, [(0, 1), (1, 2), (0, 2)], 1),
    ("C4", 4, [(0, 1), (1, 2), (2, 3), (0, 3)], 1),
    ("C3+C3", 6, [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)], 2),
    ("C6", 6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)], 1),
]


def _p1_minus_u2_pow(c: int) -> list:
    p = [F(1)]
    for _ in range(c):
        p = mul(p, [F(1), F(0), F(-1)])
    return p


def main() -> int:
    print("=" * 78)
    print("zeta_separation — does an edge-sensitive zeta invariant beat the ledger?")
    print("=" * 78)

    print("\n1. ORACLE  Bass determinant == prime-cycle product (external check)\n")
    for name, n, edges, _c in CYCLIC + [("K4", 4, list(combinations(range(4), 2)), 1)]:
        ml = 2 * n
        full = name != "K4"                       # K4 has unbounded prime cycles
        try:
            lhs = ihara_from_bass(n, edges)
        except ValueError:
            lhs = None
        rhs = ihara_from_cycles(n, edges, ml)
        ok = (lhs is not None and
              (lhs == rhs if full else trunc(lhs, ml) == trunc(rhs, ml)))
        print(f"   {name:6} #prime={len(prime_cycles(n, edges, ml)):3}  "
              f"{'full' if full else f'truncated to u^{ml}'}  MATCH={ok}")

    print("\n2. THE WITNESS  §15.2 pair (rooted tries, 7 nodes, 6 edges)\n")
    rows = []
    for nm, (n, edges) in (("A", TRIE_A), ("B", TRIE_B)):
        deg = sorted((sum(1 for u, v in edges if u == i or v == i) for i in range(n)),
                     reverse=True)
        rows.append({
            "name": nm,
            "prime": len(prime_cycles(n, edges, 2 * n)),
            "zeta": ihara_from_cycles(n, edges, 2 * n),
            "bass": bass_determinant(n, edges),
            "char": charpoly(n, edges),
            "deg": deg,
            "ahu": ahu(n, edges),
        })
        print(f"   {nm}: degrees={deg}  #prime cycles={rows[-1]['prime']}  "
              f"Z^-1={show(rows[-1]['zeta'])}")
        print(f"      Bass det = {show(rows[-1]['bass'])}   "
              f"charpoly = {show(rows[-1]['char'], 'x')}   AHU = {rows[-1]['ahu']}")
    same_zeta = rows[0]["zeta"] == rows[1]["zeta"]
    same_bass = rows[0]["bass"] == rows[1]["bass"]
    diff_char = rows[0]["char"] != rows[1]["char"]
    print(f"\n   zeta separates?      {not same_zeta}")
    print(f"   Bass det separates?  {not same_bass}")
    print(f"   charpoly separates?  {diff_char}")
    print("   -> The zeta family is IDENTICALLY BLIND here: no cycles, nothing to listen to.")

    print("\n3. THE LAW  Bass determinant of a forest = (1-u^2)^(#components)\n")
    law_ok = True
    for name, n, edges in FORESTS:
        c = n - len(edges)                        # components of a forest
        got, want = bass_determinant(n, edges), _p1_minus_u2_pow(c)
        law_ok &= got == want
        print(f"   {name:18} c={c}  det={show(got):22} == (1-u^2)^{c}? {got == want}")

    print("\n4. POSITIVE CONTROL  where zeta DOES separate (same (|V|,|E|), degrees)\n")
    for name, n, edges, _c in CYCLIC:
        deg = sorted((sum(1 for u, v in edges if u == i or v == i) for i in range(n)),
                     reverse=True)
        print(f"   {name:6} degrees={deg}  Z^-1={show(ihara_from_bass(n, edges))}")
    print("   -> C3+C3 and C6 share degree sequence and (|V|,|E|); zeta separates them.")
    print("      Zeta is sharp on cycles, empty on trees.")

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print("""
  The proposal was: use the Ihara/Bass zeta to separate the §15.2 pair, because
  the ledger is blind and the information is in the edges.

  It cannot. The §15.2 pair is a TREE, a tree has no non-backtracking closed
  cycles, so Z = 1 for both and the Bass determinant is 1-u^2 for both. Zeta
  listens to edges only through CYCLES, and this witness has none. On forests the
  Bass determinant is a function of the component count alone.

  This is a NEGATIVE result, and it is the useful kind: it LOCATES zeta in the
  spine rather than discarding it. The recurrent core R (§6) is the union of
  cycles; the transient remainder F\\R is trees. Zeta is exactly the instrument
  for R and provably empty on F\\R. The ledger and zeta are complements:

      ledger   sees levels,      blind to cycles
      zeta     sees cycles,      blind to trees
      AHU      sees tree shape,  complete on rooted trees

  What separates §15.2 today is the last one (and the char poly for this pair) --
  not a zeta. The next question is the TRANSPORT-DECORATED one: on the recurrent
  core, a closed cycle P carries a holonomy chi(P); does the twisted product
  prod (1 - chi(P) u^{len P})^{-1} see structure the bare zeta does not? That is
  a question about R, where zeta is defined and non-trivial. It is not a question
  §15's trees can answer.
""")
    return 0 if (same_zeta and same_bass and law_ok and diff_char) else 1


if __name__ == "__main__":
    raise SystemExit(main())
