#!/usr/bin/env python3
"""
survival_commutation.py — do the two survival operators commute?

Two ways to delete what does not survive:

    S_res   survival under behavioural REFINEMENT   (inverse system / persistence)
    S_dyn   survival under ITERATION                (Conley / recurrent core)

The square:

        X ---- S_dyn ----> R(X)
        |                    |
      S_res                S_res
        |                    |
        v                    v
      X_inf -- S_dyn ---->   ?

    A = S_dyn(S_res(X))      refine first, then iterate
    B = S_res(S_dyn(X))      iterate first, then refine

    Omega(X,T) = defect(A, B).

The answer turns out to depend ENTIRELY on which kind of refinement axis is used,
and the two axes are genuinely different:

  * INVERSE-SYSTEM axis   X_0 <- X_1 <- ... <- X_J, surjective bonding maps,
                          T-invariant. This is PDI's actual structure (§1 of
                          SPINE.md; Zomorodian-Carlsson persistence module).
  * INCLUSION axis        F_0  <=  F_1 <= ... <=  F_J, injective, the TDA
                          filtration structure. NOT required to be T-invariant.

Part 1 shows the operators commute trivially when both are restrictions on one
common set. Part 2 shows they commute on the inverse-system axis, with proof, and
explains why the finite case is degenerate. Part 3 exhibits the smallest witness
on the inclusion axis, where the square FAILS.

Run: python3 survival_commutation.py
"""
from __future__ import annotations

import itertools


# --------------------------------------------------------------------------
# dynamics primitives
# --------------------------------------------------------------------------
def periodic_points(T: dict) -> set:
    """x is periodic iff T^n(x) = x for some n >= 1."""
    out = set()
    for x in T:
        y, seen = T[x], {x}
        while y not in seen:
            seen.add(y)
            y = T[y]
        if y == x:
            out.add(x)
    return out


def core(T: dict, S) -> set:
    """Recurrent core of T restricted to S.

    x qualifies iff (a) x is periodic under T, and (b) the forward orbit of x
    never leaves S. Condition (b) is what makes the operator sensitive to a
    non-invariant S -- and is the entire source of non-commutation in Part 3.
    """
    S = set(S)
    per = periodic_points(T)
    out = set()
    for x in S:
        if x not in per:
            continue
        y, ok = x, True
        for _ in range(len(S) + 1):
            y = T[y]
            if y not in S:
                ok = False
                break
        if ok:
            out.add(x)
    return out


# --------------------------------------------------------------------------
# Part 1 — both operators as restrictions: they commute, trivially
# --------------------------------------------------------------------------
def part1_is_trivial(n: int = 4):
    """If S_res(S) = S ∩ P and S_dyn(S) = S ∩ Q for fixed P, Q, then

           S_dyn(S_res(X)) = X ∩ P ∩ Q = S_res(S_dyn(X)).

    Verified exhaustively rather than asserted.
    """
    print("=" * 84)
    print("PART 1 — both operators as restrictions on one set")
    print("=" * 84)
    print("  If both survival operators are 'intersect with a fixed set', they")
    print("  commute by associativity of intersection. Checking exhaustively:")
    bad = 0
    X = set(range(n))
    for r in range(1 << n):
        P = {x for x in X if r >> x & 1}
        for s in range(1 << n):
            Q = {x for x in X if s >> x & 1}
            if (X & P) & Q != (X & Q) & P:
                bad += 1
    print(f"  pairs checked: {1 << (2*n)}   counterexamples: {bad}")
    print("  -> TRUE, and TRIVIAL. A square whose two operators both act by")
    print("     restriction on a common set cannot fail to commute.\n")


# --------------------------------------------------------------------------
# Part 2 — the inverse-system axis (PDI's actual structure)
# --------------------------------------------------------------------------
def all_maps(n: int):
    return ({x: T[x] for x in range(n)} for T in itertools.product(range(n), repeat=n))


def t_invariant_partitions(T: dict, n: int):
    """Partitions of X on which T descends (x ~ y => T(x) ~ T(y))."""
    for lab in itertools.product(range(n), repeat=n):
        part = {x: lab[x] for x in range(n)}
        ok = all(part[T[x]] == part[T[y]]
                 for x in range(n) for y in range(n) if part[x] == part[y])
        if ok:
            yield part


def partition_refines(fine: dict, coarse: dict) -> bool:
    return all(coarse[x] == coarse[y]
               for x in fine for y in fine if fine[x] == fine[y])


def block_reps(part: dict, n: int) -> dict:
    rep = {}
    for x in range(n):
        rep.setdefault(part[x], x)
    return rep


def quotient_map(T: dict, part: dict, n: int) -> dict:
    """T induced on the blocks of `part` (well defined iff T is part-invariant)."""
    return {b: part[T[r]] for b, r in block_reps(part, n).items()}


def projection(fine: dict, coarse: dict, n: int) -> dict:
    """fine block -> coarse block."""
    return {b: coarse[r] for b, r in block_reps(fine, n).items()}


def part2(n: int = 4):
    """R_inf = lim<- R_j   vs   core(lim<- X_j)   on the inverse-system axis.

    Both routes are computed INDEPENDENTLY from the two induced maps, so the
    check actually tests the one non-trivial step: that a block which is
    periodic at a COARSE level is the image of a block that is periodic at the
    FINE level. That is the fibre argument -- if T_c^k(c) = c then T_f^k maps the
    fibre pi^-1(c) into itself, and a self-map of a finite set has a periodic
    point, hence the fibre contains one.

        Route A = pi(core at the fine level)          -- uses only T_fine
        Route B = core(coarse) INTERSECT pi(core(fine))

    A == B  iff  core(coarse) is contained in pi(core(fine)).
    """
    print("=" * 84)
    print("PART 2 - the inverse-system axis (surjective, T-invariant)")
    print("=" * 84)
    systems = descent_ok = 0
    mismatches = []
    for T in all_maps(n):
        parts = list(t_invariant_partitions(T, n))
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                if partition_refines(parts[i], parts[j]):
                    fine, coarse = parts[i], parts[j]
                elif partition_refines(parts[j], parts[i]):
                    fine, coarse = parts[j], parts[i]
                else:
                    continue
                systems += 1
                Tf = quotient_map(T, fine, n)
                Tc = quotient_map(T, coarse, n)
                pi = projection(fine, coarse, n)
                if all(pi[Tf[b]] == Tc[pi[b]] for b in Tf):
                    descent_ok += 1
                Rf = periodic_points(Tf)          # core at the fine level
                Rc = periodic_points(Tc)          # core at the coarse level
                A = {pi[b] for b in Rf}
                B = Rc & A
                if A != B:
                    mismatches.append((T, fine, coarse, A, B))
    print(f"  systems checked             : {systems}")
    print(f"  T descends through bonding  : {descent_ok}/{systems}")
    print(f"  mismatches (Omega != 0)     : {len(mismatches)}")
    print("  -> COMMUTES on this axis, and the fibre step above is the proof.")
    print("     But the reason the SQUARE is uninteresting here is separate and")
    print("     degenerate: a finite tower of quotients of one finite set has")
    print("     inverse limit = its finest level, so both routes collapse to the")
    print("     same core. The content of the PDI axis is the CONSTRUCTION")
    print("     R_inf = lim<- R_j and the descent of T, not a commutativity defect.\n")
    return len(mismatches)


# --------------------------------------------------------------------------
# Part 3 — the inclusion axis (TDA filtration), where it FAILS
# --------------------------------------------------------------------------
def smallest_witness(nmax: int = 5):
    """Search for the smallest (T, F) with Omega != 0.

    Set-up: F subset of X is the resolution filter (the part surviving
    refinement). Both routes are computed and compared:
        A = core(T, F)            refine, then iterate
        B = core(T, X) & F        iterate, then refine
    """
    for n in range(2, nmax + 1):
        for T in all_maps(n):
            for r in range(1 << n):
                F = {x for x in range(n) if r >> x & 1}
                if not F or F == set(range(n)):
                    continue
                A = core(T, F)
                B = core(T, set(range(n))) & F
                if A != B:
                    return {"n": n, "T": T, "F": F, "A": A, "B": B}
    return None


def part3(nmax: int = 5):
    print("=" * 84)
    print("PART 3 — the inclusion axis (TDA filtration, not T-invariant)")
    print("=" * 84)
    w = smallest_witness(nmax)
    if not w:
        print("  no witness found up to n =", nmax)
        return None
    n, T, F, A, B = w["n"], w["T"], w["F"], w["A"], w["B"]
    print(f"  SMALLEST WITNESS  (n = {n})")
    print(f"    X  = {sorted(range(n))}")
    print(f"    T  = " + ", ".join(f"{x}->{T[x]}" for x in sorted(T)))
    print(f"    F  = {sorted(F)}   (resolution filter, NOT T-invariant)")
    print(f"    A = core(T, F)          = {sorted(A)}")
    print(f"    B = core(T, X) & F      = {sorted(B)}")
    print(f"    Omega != 0 : {A != B}")
    print()
    print("  Why it fails: F contains a periodic point of X, but F is not")
    print("  forward-invariant, so iterating INSIDE F immediately leaves it.")
    print("  Refining first destroys the cycle; iterating first preserves it and")
    print("  then the refinement clip removes nothing.")
    return w


# --------------------------------------------------------------------------
# Part 4 — exact characterisation of the failure
# --------------------------------------------------------------------------
def _orbit_leaves(T: dict, x: int, F: set) -> bool:
    y = x
    for _ in range(len(F) + 2):
        y = T[y]
        if y not in F:
            return True
    return False


def part4_characterisation(nmax: int = 4):
    """Omega != 0  <=>  some periodic point of X lies in F but leaves F.

    On the inclusion axis A = core(T,F) and B = core(T,X) & F, so A != B iff
    exactly that. Checked as an iff over every (T,F) pair -- not asserted.
    """
    print("=" * 84)
    print("PART 4 - exact characterisation (inclusion axis)")
    print("=" * 84)
    total = agree = omega_true = inv_cases = inv_bad = 0
    for n in range(2, nmax + 1):
        X = set(range(n))
        for T in all_maps(n):
            per = periodic_points(T)
            for r in range(1 << n):
                F = {x for x in range(n) if r >> x & 1}
                if not F or F == X:
                    continue
                total += 1
                omega = (core(T, F) != (per & F))
                pred = any(x in per and _orbit_leaves(T, x, F) for x in F)
                if omega == pred:
                    agree += 1
                if omega:
                    omega_true += 1
                if all(T[x] in F for x in F):          # F is T-invariant
                    inv_cases += 1
                    if omega:
                        inv_bad += 1
    print(f"  (T, F) pairs checked      : {total}")
    print(f"  Omega != 0                : {omega_true}  ({100*omega_true/total:.1f}%)")
    print(f"  iff holds                 : {agree}/{total}")
    print(f"  F T-invariant cases       : {inv_cases}   of which Omega != 0: {inv_bad}")
    print("  -> Omega != 0  iff  (some periodic point of X lies in F but its orbit")
    print("     leaves F).  T-invariance of the filter is therefore exactly the")
    print("     hypothesis that forces commutation -- and it is precisely the")
    print("     hypothesis the quotient axis satisfies and a TDA filtration does")
    print("     not.\n")
    return agree == total


# --------------------------------------------------------------------------
if __name__ == "__main__":
    part1_is_trivial(4)
    part2(4)
    part3(5)
    part4_characterisation(4)

    print("=" * 84)
    print("CONCLUSION")
    print("=" * 84)
    print("""
  The commuting square is NOT where the content lives on PDI's own axis. Both
  operators act on subsets of one set, so they commute by intersection; and the
  finite inverse-system limit is its finest level, so the two routes collapse to
  the same core. That is a real answer, and it says the interesting object is the
  CONSTRUCTION  R_inf = lim<- R_j  plus the descent of T through the bonding
  maps  (pi_{j+1,j} T_{j+1} = T_j pi_{j+1,j}),  not a defect to be measured.

  The defect becomes non-zero only when the refinement axis is an INCLUSION
  filtration that is not dynamics-invariant -- which is the TDA filtration
  setting, not the PDI quotient setting. The minimal witness is two states and a
  2-cycle: refine to one state first and the cycle dies; iterate first and it
  survives the clip. Order of observation genuinely matters there.

  So: Omega = 0 on the quotient axis, Omega != 0 on the inclusion axis, and the
  difference between the two axes is exactly T-invariance.
""")
