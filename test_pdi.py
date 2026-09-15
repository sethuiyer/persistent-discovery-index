#!/usr/bin/env python3
"""Self-checks for the PDI prototype. Run: python3 test_pdi.py"""
import math
from pdi import PDI, Status

H = 8   # NB: the spike must land on an ODD level (H-1) for the reindexing
        # test to bite. With H=7 the spike is at level 6 (even) and even-only
        # reindexing happens to agree -- a real fragility worth knowing about.
FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def live(H):
    for m in range(2 ** H):
        yield tuple((m >> i) & 1 for i in range(H))


def build(agent):
    idx = PDI()
    for t in live(H):
        idx.insert(t)
    if agent == "B":
        for k in range(1, H - 1):
            for m in range(2 ** k):
                prefix = tuple((m >> i) & 1 for i in range(k))
                for d in range(2 ** k):
                    idx.insert(prefix + (("d", k, d),))
    idx.recompute_statuses()
    return idx


print("PDI self-checks")
A, B = build("A"), build("B")
exA, exB = A.exponents(), B.exponents()

# 1. the two ledgers are distinct channels for B, identical for A
check("A: n_j == L_j (no transient mass)", all(A.n[j] == A.L[j] for j in range(1, H + 1)))
check("B: n_j > L_j (transient mass present)", all(B.n[j] > B.L[j] for j in range(2, H)))

# 2. L_j non-decreasing at a fixed horizon (injectivity live(j) -> live(j+1))
check("A: L_j non-decreasing", A.live_non_decreasing())
check("B: L_j non-decreasing", B.live_non_decreasing())

# 3. identical persistent ledger, different exploration ledger
check("same persistent ledger L_j", all(A.L.get(j, 0) == B.L.get(j, 0) for j in range(H + 1)))
check("same D", abs(exA["D"] - exB["D"]) < 1e-12)
check("different S", abs(exA["S"] - exB["S"]) > 1e-9)
check("different Delta", abs(exA["delta"] - exB["delta"]) > 1e-9)
check("Delta >= 0 for both", exA["delta"] >= -1e-12 and exB["delta"] >= -1e-12)

# 4. D is cofinal-invariant; Delta is not
def exps_at(idx, levels):
    def sup(c):
        v = [math.log(c[j]) / (j * math.log(2.0)) for j in levels if c.get(j, 0) > 0]
        return max(v) if v else 0.0
    S, D = sup(idx.n), sup(idx.L)
    return D, S, S - D

allv = list(range(1, H + 1))
even = [j for j in allv if j % 2 == 0]
D1, _, d1 = exps_at(B, allv)
D2, _, d2 = exps_at(B, even)
check("D invariant under cofinal reindexing", abs(D1 - D2) < 1e-12)
check("Delta NOT invariant under reindexing", abs(d1 - d2) > 1e-9)

# 5. statuses are meaningful
lv = B.level_nodes(4)
check("level-4 nodes all classified", all(nd.status in (Status.LIVE, Status.TRANSIENT) for nd in lv))
check("some level-4 nodes TRANSIENT (dead ends)", any(nd.status is Status.TRANSIENT for nd in lv))
check("some level-4 nodes LIVE", any(nd.status is Status.LIVE for nd in lv))

# 6. hierarchical reuse
A.root.payload = "root"
node = A.root
for _ in range(3):
    node = node.children[1]          # follow the all-1s branch, query below is all-1s
    node.payload = f"cached@{node.level}"
payload, used = A.lookup_or_refine(tuple([1] * H), lambda a, b: a == b)
check("hierarchical reuse returns a cached payload", payload is not None and used >= 1)

print()
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
raise SystemExit(1 if FAILS else 0)
