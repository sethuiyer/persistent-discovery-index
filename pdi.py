#!/usr/bin/env python3
"""
pdi.py — Persistent Discovery Index (v0.1.0)

A multiresolution data structure that separates what a system discovers
persistently from the transient exploration structure generated while
discovering it. Two deliberately separate information channels:

    n_j = |X_j|      "what was explored"          (exploration ledger)
    L_j = |live(j)|  "what survived to the horizon" (persistent ledger)

Motivation is a theorem, not a metaphor:

    D = limsup_j log L_j / (-log eps_j)   intrinsic, cofinal-invariant  (proved)
    S = limsup_j log n_j / (-log eps_j)   presentation-dependent
    Delta = S - D  >= 0                   presentation-dependent (refuted as invariant)

See concepts/cofinal-invariance and concepts/regular-growth-identification.
The full/transient distinction is classical elsewhere: coaccessible vs all
states in automata, essential vs transient in sofic shifts, where entropy is
a function of the essential part only (Lind-Marcus). PDI is the data structure
that keeps both ledgers.

Design rules this file obeys:

  R1  Never collapse the two ledgers into one counter.
  R2  LIVE is terminal/monotone only WITHIN a fixed horizon. See HorizonRelativity.
  R3  UNKNOWN is not a fallback; deciding live-vs-dead is the stabilisation
      problem and is undecidable in general. In a streaming setting the third
      state is forced.
  R4  Refinement stops on PHYSICAL resolution, not on tree depth.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Hashable, Iterable, Iterator, Optional, Sequence


class Status(str, Enum):
    LIVE = "LIVE"            # lies on a path reaching the observed horizon
    TRANSIENT = "TRANSIENT"  # dies before the horizon
    UNKNOWN = "UNKNOWN"      # not yet decided (streaming, or horizon not fixed)


# --------------------------------------------------------------------------
# Node
# --------------------------------------------------------------------------
@dataclass
class Node:
    profile: tuple           # resolution-dependent behavioural profile
    level: int               # resolution level j
    parent: Optional["Node"] = None
    children: dict = field(default_factory=dict)
    status: Status = Status.UNKNOWN
    payload: Any = None      # cached computation / agent outcome / embeddings
    seen: int = 0            # observation count (reuse statistics)

    # ---- convenience -----------------------------------------------------
    @property
    def is_leaf(self) -> bool:
        return not self.children

    def path(self) -> Iterator["Node"]:
        node: Optional[Node] = self
        while node is not None:
            yield node
            node = node.parent

    def __hash__(self) -> int:
        return id(self)


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------
class PDI:
    """Persistent Discovery Index.

    label : callable mapping an atomic observation to its resolution-0 class
            (this is the *behavioural quotient*; equal labels are identified)
    eps   : physical resolution at level j. Default eps_j = 2^-j.
    """

    def __init__(
        self,
        label: Callable[[Any], Hashable] = lambda x: x,
        eps: Optional[Callable[[int], float]] = None,
        tower: Optional[Any] = None,
    ) -> None:
        self.label = label
        self.tower = tower
        self.eps = eps if eps is not None else (
            tower.eps if tower is not None else (lambda j: 2.0 ** -j)
        )

        self.root = Node(profile=(), level=0, status=Status.LIVE)

        # R1: two ledgers, never merged
        self.n: dict[int, int] = defaultdict(int)   # exploration ledger
        self.L: dict[int, int] = defaultdict(int)   # persistent ledger
        self.n[0] = 1
        self.L[0] = 1

        self.max_level = 0
        self._finalised = False
        self.stats = {"inserts": 0, "nodes_created": 0, "reuses": 0}

    # ------------------------------------------------------------------ util
    def _profile(self, trace: Sequence[Any], j: int) -> tuple:
        return tuple(self.label(a) for a in trace[:j])

    def level_nodes(self, j: int) -> list[Node]:
        if j == 0:
            return [self.root]
        out: list[Node] = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.level == j:
                out.append(node)
            else:
                stack.extend(node.children.values())
        return out

    # ---------------------------------------------------------------- insert
    def insert(self, trace: Sequence[Any], live: bool = False) -> Node:
        """Descend by physical resolution, creating nodes as needed.

        Streaming-friendly: only ever sets LIVE (never clears it), which is
        sound at a fixed horizon. When the horizon grows, call
        recompute_statuses() (see HorizonRelativity below).

        `live=True` marks the whole prefix chain as LIVE via coaccessibility
        propagation -- use this for explicit live rules (e.g. "this prefix lies
        on a successful agent trajectory") instead of the horizon rule.
        """
        node = self.root
        if self.tower is not None:
            chain = self.tower.signature(trace)
        else:
            chain = [self.label(x) for x in trace]
        for j, lab in enumerate(chain, start=1):
            child = node.children.get(lab)
            if child is None:
                child = Node(profile=node.profile + (lab,), level=j, parent=node)
                node.children[lab] = child
                self.n[j] += 1
                self.stats["nodes_created"] += 1
            node = child
            node.seen += 1
            self.max_level = max(self.max_level, j)

        self.stats["inserts"] += 1
        self._finalised = False
        if live:
            self.mark_live(node)
        return node

    def fit(self, runs: Iterable[tuple], validate: bool = True) -> "PDI":
        """Insert (history, succeeded) runs through a tower, validating the
        refinement law on the corpus first when a tower is present."""
        runs = list(runs)
        if validate and self.tower is not None:
            self.tower.validate(h for h, _ in runs)
        for h, ok in runs:
            self.insert(h, live=ok)
        return self

    def count_live(self) -> dict[int, int]:
        """Recompute L_j from node statuses (authoritative for explicit-mode)."""
        out: dict[int, int] = defaultdict(int)
        stack = [self.root]
        while stack:
            nd = stack.pop()
            if nd is not self.root and nd.status is Status.LIVE:
                out[nd.level] += 1
            stack.extend(nd.children.values())
        return out

    def finalize_explicit(self) -> "PDI":
        """Adopt the mark_live-based (explicit) classification rather than the
        horizon rule. Use when LIVE means something task-specific -- e.g. "this
        prefix lies on a successful trajectory". Transient nodes are those
        explored but on no live prefix."""
        self.L = self.count_live()
        self.L[0] = 1 if self.root.children else 0
        for nd in self._all_nodes():
            if nd is not self.root and nd.status is not Status.LIVE:
                nd.status = Status.TRANSIENT
        self._finalised = True
        return self

    def _all_nodes(self) -> Iterator[Node]:
        stack = [self.root]
        while stack:
            nd = stack.pop()
            yield nd
            stack.extend(nd.children.values())

    def insert_all(self, traces: Iterable[Sequence[Any]]) -> "PDI":
        for t in traces:
            self.insert(t)
        self.recompute_statuses()
        return self

    # -------------------------------------------------------------- statuses
    def mark_live(self, node: Node) -> None:
        """Coaccessibility propagation: a node with a live child is LIVE."""
        cur: Optional[Node] = node
        while cur is not None and cur.status is not Status.LIVE:
            cur.status = Status.LIVE
            if cur is not self.root:
                self.L[cur.level] += 1
            cur = cur.parent

    def recompute_statuses(self, horizon: Optional[int] = None) -> None:
        """Batch, authoritative classification relative to `horizon`.

        LIVE      : has a descendant at the horizon (or is at the horizon)
        TRANSIENT : level < horizon and no descendant at the horizon
        UNKNOWN   : only if no horizon is fixed

        Because LIVE means 'reaches the horizon', the map live(j) -> live(j+1)
        that selects a node's child on a horizon-reaching path is injective.
        Hence L_j <= L_{j+1} at all times at a fixed horizon.
        """
        H = self.max_level if horizon is None else horizon
        self.L = defaultdict(int)
        self.L[0] = 1 if H > 0 else 0

        # bottom-up: a node is live iff it is at the horizon or has a live child
        def walk(node: Node) -> bool:
            if node.level == H:
                node.status = Status.LIVE
                return True
            live_child = False
            for c in node.children.values():
                if walk(c):
                    live_child = True
            if live_child:
                node.status = Status.LIVE
                return True
            node.status = Status.TRANSIENT if node.level < H else Status.UNKNOWN
            return False

        walk(self.root)
        for j in range(1, H + 1):
            self.L[j] = sum(1 for nd in self.level_nodes(j) if nd.status is Status.LIVE)
        self._finalised = True

    # ---------------------------------------------------------------- ledgers
    def ledgers(self) -> tuple[dict[int, int], dict[int, int]]:
        if not self._finalised:
            self.recompute_statuses()
        return dict(self.n), dict(self.L)

    def exponents(self) -> dict:
        """D (persistent), S (exploration), Delta (discovery overhead)."""
        if not self._finalised:
            self.recompute_statuses()
        H = self.max_level

        def sup(counts: dict[int, int]) -> float:
            vals = []
            for j in range(1, H + 1):
                c = counts.get(j, 0)
                if c > 0:
                    vals.append(math.log(c) / (-math.log(self.eps(j))))
            return max(vals) if vals else 0.0

        S = sup(self.n)
        D = sup(self.L)
        return {"D": D, "S": S, "delta": S - D, "horizon": H}

    def live_non_decreasing(self) -> bool:
        if not self._finalised:
            self.recompute_statuses()
        return all(self.L.get(j, 0) <= self.L.get(j + 1, 0)
                   for j in range(self.max_level))

    # ------------------------------------------------------------------ STOP
    def refine_worthwhile(
        self,
        j: int,
        gain: float,
        cost: float,
        ambiguity: float = 1.0,
    ) -> bool:
        """R4: STOP is decided on physical resolution, not tree depth.

        Expected information gain is discounted by the observed persistent
        growth at this level, because growth is what makes the next
        resolution informative per unit cost.
        """
        persistent = self.L.get(j, 0) or 1
        exploration = self.n.get(j, 0) or 1
        yield_ratio = persistent / exploration  # how much of this level persisted
        expected_gain = gain * ambiguity * yield_ratio
        return expected_gain >= cost

    # ----------------------------------------------------------------- cache
    def lookup_or_refine(
        self,
        query: Sequence[Any],
        equivalent: Callable[[Any, Any], bool],
        max_level: Optional[int] = None,
    ) -> tuple[Any, int]:
        """Hierarchical reuse: walk coarse -> fine, return the first cached
        payload whose stored key is `equivalent` to the query at that level.
        Refine only when reuse fails.

        Returns (payload, level_used). payload is None if nothing matched.
        """
        node = self.root
        limit = self.max_level if max_level is None else max_level
        for j in range(1, min(len(query), limit) + 1):
            lab = self.label(query[j - 1])
            child = node.children.get(lab)
            if child is None:
                return (None, j - 1)
            node = child
            if node.payload is not None and equivalent(node.profile, self._profile(query, j)):
                self.stats["reuses"] += 1
                return (node.payload, j)
        return (node.payload, node.level)


# --------------------------------------------------------------------------
# HorizonRelativity
# --------------------------------------------------------------------------
# LIVE is defined relative to an observed horizon H. This matters:
#
#   * At fixed H, LIVE is monotone under additive insertion, and L_j <= L_{j+1}.
#   * When a longer trace arrives and H grows, nodes that reached the old H but
#     not the new one must be demoted. So a horizon-relative LIVE is NOT
#     monotone in H, and TRANSIENT is always "dead given the data so far" --
#     revisable, never final.
#
# A streaming index therefore cannot promise stable classification. That is not
# an implementation defect; it is the stabilisation problem, and it is
# undecidable in general. The UNKNOWN state is a theorem, not a convenience.
