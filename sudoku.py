#!/usr/bin/env python3
"""
sudoku.py — a backtracking solver that records its search tree.

Sudoku is the cleanest possible case for PDI, because the solution is unique:
the persistent structure is a single thin path, and *everything else the solver
does is transient*. That makes `D = 0` and `Delta = S` by construction, so every
number PDI reports is a statement about waste.

Two things are recorded per solve:

    nodes_at_depth[j]   how many search-tree nodes the solver visited at depth j
    solution_path       the assignments on the solution

`run_records()` turns that into PDI runs: one run per visited node, whose history
is the assignment path from the root to that node, and whose success is whether
that node lies on the solution path.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator, Optional

N = 9
ALL = 0x1FF


# --------------------------------------------------------------------------
# board plumbing
# --------------------------------------------------------------------------
def parse(puzzle: str) -> list[int]:
    return [0 if ch in ".0" else int(ch) for ch in puzzle if ch.isdigit() or ch in ".0"]


def _masks(board):
    rows = [0] * N
    cols = [0] * N
    boxes = [0] * N
    for i, v in enumerate(board):
        if v:
            b = 1 << (v - 1)
            rows[i // N] |= b
            cols[i % N] |= b
            boxes[(i // N // 3) * 3 + (i % N) // 3] |= b
    return rows, cols, boxes


def _candidates(board, rows, cols, boxes, i):
    r, c = divmod(i, N)
    b = (r // 3) * 3 + c // 3
    used = rows[r] | cols[c] | boxes[b]
    return [v for v in range(1, N + 1) if not (used >> (v - 1)) & 1]


# --------------------------------------------------------------------------
@dataclass
class Trace:
    nodes_at_depth: list[int] = field(default_factory=lambda: [0] * (N * N + 1))
    solution_path: list[tuple[int, int]] = field(default_factory=list)  # (cell, value)
    total_nodes: int = 0
    backtracks: int = 0
    solved: bool = False
    capped: bool = False
    max_depth: int = 0


def solve(puzzle: str, *, cell_order: str = "first", value_order: str = "asc",
          seed: int = 0, cap: int = 400_000) -> Trace:
    """Backtracking solver with a recorded trace.

    cell_order  'first'  scan cells in index order
                'mrv'    fewest candidates first
                'random' random unfilled cell
    value_order 'asc'    try 1..9
                'random' random order
    """
    board = parse(puzzle)
    rows, cols, boxes = _masks(board)
    empties = [i for i, v in enumerate(board) if not v]
    rng = random.Random(seed)
    tr = Trace()
    path: list[tuple[int, int]] = []
    on_solution: list[tuple[int, int]] = []

    def record(depth):
        tr.nodes_at_depth[depth] += 1
        tr.total_nodes += 1
        tr.max_depth = max(tr.max_depth, depth)
        if tr.total_nodes >= cap:
            tr.capped = True

    def rec(depth: int) -> bool:
        record(depth)
        if tr.capped:
            return False
        if depth == len(empties):
            tr.solved = True
            tr.solution_path = list(path)
            return True

        if cell_order == "mrv":
            best, cand = None, None
            for i in empties:
                if board[i]:
                    continue
                cd = _candidates(board, rows, cols, boxes, i)
                if best is None or len(cd) < len(cand):
                    best, cand = i, cd
                    if len(cd) == 0:
                        break
            i = best
        elif cell_order == "random":
            free = [i for i in empties if not board[i]]
            i = rng.choice(free)
            cand = _candidates(board, rows, cols, boxes, i)
        else:
            i = next(i for i in empties if not board[i])
            cand = _candidates(board, rows, cols, boxes, i)

        if cand is None:
            cand = _candidates(board, rows, cols, boxes, i)
        if value_order == "random":
            rng.shuffle(cand)

        r, c = divmod(i, N)
        b = (r // 3) * 3 + c // 3
        for v in cand:
            bit = 1 << (v - 1)
            board[i] = v
            rows[r] |= bit
            cols[c] |= bit
            boxes[b] |= bit
            path.append((i, v))
            if rec(depth + 1):
                on_solution.append((i, v))
                return True
            path.pop()
            board[i] = 0
            rows[r] &= ~bit
            cols[c] &= ~bit
            boxes[b] &= ~bit
            tr.backtracks += 1
        return False

    rec(0)
    return tr


# --------------------------------------------------------------------------
# traces -> PDI runs
# --------------------------------------------------------------------------
def run_records(puzzle: str, *, label: str = "solver", **kw) -> tuple[list, dict]:
    """Replay the SAME search non-destructively to emit one run per visited node.

    Each run is (history, succeeded) where history is the tuple of assignments
    from the root to that node and succeeded is true exactly when that node is
    an ancestor of (or equal to) the solution. That is the maze model applied to
    a Sudoku search tree.
    """
    from adapters import Step, Turn

    board = parse(puzzle)
    rows, cols, boxes = _masks(board)
    empties = [i for i, v in enumerate(board) if not v]
    rng = random.Random(kw.get("seed", 0))
    cell_order = kw.get("cell_order", "first")
    value_order = kw.get("value_order", "asc")
    cap = kw.get("cap", 400_000)

    runs: list = []
    stats = {"nodes": 0, "capped": False}
    path: list[tuple[int, int]] = []

    # first pass: find the solution's assignment SET so we can mark ancestors
    tr = solve(puzzle, cell_order=cell_order, value_order=value_order,
               seed=kw.get("seed", 0), cap=cap)
    sol = list(tr.solution_path)

    def mkrun(on_solution: bool):
        steps = [Step(tool="assign", args={"cell": i, "value": v},
                      error=None if on_solution else "dead branch")
                 for i, v in path]
        runs.append(Turn(steps=steps, outcome="stop" if on_solution else "dead",
                         model=label, project="sudoku",
                         prompt=puzzle[:40]))

    def rec(depth: int, sol_prefix: list):
        if stats["nodes"] >= cap:
            stats["capped"] = True
            return False
        stats["nodes"] += 1

        # is the current node a prefix of the solution?
        on_sol = len(path) <= len(sol) and list(path) == sol[:len(path)]
        if depth > 0:
            mkrun(on_sol)
        if depth == len(empties):
            return True

        if cell_order == "mrv":
            best, cand = None, None
            for i in empties:
                if board[i]:
                    continue
                cd = _candidates(board, rows, cols, boxes, i)
                if best is None or len(cd) < len(cand):
                    best, cand = i, cd
                    if len(cd) == 0:
                        break
            i = best
        elif cell_order == "random":
            i = rng.choice([x for x in empties if not board[x]])
            cand = _candidates(board, rows, cols, boxes, i)
        else:
            i = next(x for x in empties if not board[x])
            cand = _candidates(board, rows, cols, boxes, i)
        if cand is None:
            cand = _candidates(board, rows, cols, boxes, i)
        if value_order == "random":
            rng.shuffle(cand)

        r, c = divmod(i, N)
        b = (r // 3) * 3 + c // 3
        for v in cand:
            bit = 1 << (v - 1)
            board[i] = v
            rows[r] |= bit
            cols[c] |= bit
            boxes[b] |= bit
            path.append((i, v))
            if rec(depth + 1, sol_prefix):
                path.pop()
                board[i] = 0
                rows[r] &= ~bit
                cols[c] &= ~bit
                boxes[b] &= ~bit
                return True
            path.pop()
            board[i] = 0
            rows[r] &= ~bit
            cols[c] &= ~bit
            boxes[b] &= ~bit
        return False

    rec(0, [])
    stats["total_nodes"] = tr.total_nodes
    stats["solved"] = tr.solved
    stats["backtracks"] = tr.backtracks
    stats["solution_len"] = len(sol)
    return runs, stats


# --------------------------------------------------------------------------
PUZZLES = {
    "easy":   "530070000600195000098000060800060003400803001700020006060000280000419005000080079",
    "medium": "000000907000420180000705026100904000050000040000507009920108000034059000507000000",
    "hard":   "000000000000003085001020000000507000004000100090000000500000073002010000000040009",
    "empty":  "000000000000000000000000000000000000000000000000000000000000000000000000000000000",
}

STRATEGIES = {
    "first/asc":     dict(cell_order="first",  value_order="asc"),
    "mrv/asc":       dict(cell_order="mrv",    value_order="asc"),
    "first/random":  dict(cell_order="first",  value_order="random"),
}
