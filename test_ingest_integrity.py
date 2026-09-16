#!/usr/bin/env python3
"""
test_ingest_integrity.py — the ingestion contract: what a trace *means* must
survive the round trip.

These fixtures fail on the v0.27.0 behaviour, for two demonstrated reasons:

  1. `load_canonical` dropped every zero-tool episode (`if not steps: continue`),
     so an agent that answered without calling a tool simply vanished.
  2. the Q6 comparison key shortened file-tool arguments to the path -- dropping
     `offset`/`limit` and every edit body -- so two reads of different ranges, or
     two edits with different content, collided. A key that maps different
     behaviour to the same class is not "the full normalised trace".

WARRANT DISCIPLINE. Q6 is **not** claimed injective. Keys preserve the declared
normalized argument representation; normalization may identify distinct raw
inputs, and fixed-width digests additionally admit collisions. These tests pin
(a) the specific collisions that were demonstrated, and (b) the normalisation
equivalences that are *intended*. They do not assert more than that.

Run: python3 test_ingest_integrity.py     (exit 0 on success)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from adapters import Step, Turn as Run, tool_tower
from ingest import load_canonical, to_canonical

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def Q6(h) -> tuple:
    """The finest level of the shipped tool tower."""
    return tool_tower().levels[5](h)


def write_jsonl(records: list[dict]) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def test_zero_tool_preserved() -> None:
    print("zero-tool episodes are runs, not noise")
    path = write_jsonl([
        {"model": "m", "outcome": "stop", "steps": []},                       # answered, no tools
        {"model": "m", "outcome": "stop",
         "steps": [{"tool": "read", "args": {"path": "a.py"}}]},
    ])
    runs = load_canonical(path)
    check("two canonical records -> two runs", len(runs) == 2, f"got {len(runs)}")
    if len(runs) == 2:
        check("the zero-tool episode survived with empty steps",
              runs[0].steps == [], str(runs[0].steps))
        check("its outcome survived too", runs[0].outcome == "stop", runs[0].outcome)


def test_read_ranges_differ() -> None:
    print("Q6 separates reads of the same file at different ranges")
    a = Run([Step("read", {"path": "a.py", "offset": 0, "limit": 10})], "stop")
    b = Run([Step("read", {"path": "a.py", "offset": 100, "limit": 10})], "stop")
    check("offset/limit are part of the class", Q6(a) != Q6(b),
          f"{Q6(a)} == {Q6(b)}")


def test_edit_bodies_differ() -> None:
    print("Q6 separates edits with different bodies")
    a = Run([Step("edit", {"path": "a.py", "old_string": "x", "new_string": "one"})], "stop")
    b = Run([Step("edit", {"path": "a.py", "old_string": "x", "new_string": "two"})], "stop")
    check("edit body is part of the class", Q6(a) != Q6(b), f"{Q6(a)} == {Q6(b)}")


def test_long_prefix_not_truncated() -> None:
    print("Q6 does not collapse arguments that share a long prefix")
    c1 = "echo " + "a" * 300 + "TAIL_ONE"
    c2 = "echo " + "a" * 300 + "TAIL_TWO"
    a = Run([Step("bash", {"command": c1})], "stop")
    b = Run([Step("bash", {"command": c2})], "stop")
    check("post-prefix difference survives", Q6(a) != Q6(b))
    check("the full command text is present in the key", c1 in str(Q6(a)),
          f"len={len(str(Q6(a)))} (display shortening leaked into the key?)")


def test_whitespace_equivalence_is_intended() -> None:
    print("intended normalisation equivalence (positive test)")
    a = Run([Step("bash", {"command": "ls   -la"})], "stop")
    b = Run([Step("bash", {"command": "ls -la"})], "stop")
    check("incidental whitespace collapses to one class", Q6(a) == Q6(b),
          f"{Q6(a)} != {Q6(b)}")


def test_empty_vs_populated() -> None:
    print("a no-tool run is distinguishable from a tool-using run")
    a = Run([], "stop")
    b = Run([Step("read", {"path": "a.py"})], "stop")
    check("empty step sequence is its own class", Q6(a) != Q6(b))


def test_round_trip_preserves_payload() -> None:
    print("canonical round-trip keeps ranges and bodies")
    r = Run([Step("read", {"path": "a.py", "offset": 5, "limit": 7}),
             Step("edit", {"path": "a.py", "old_string": "x", "new_string": "body"})],
            "stop")
    d = to_canonical(r)
    check("read offset survives to_canonical", d["steps"][0]["args"].get("offset") == 5,
          str(d["steps"][0]["args"]))
    check("edit body survives to_canonical",
          d["steps"][1]["args"].get("new_string") == "body",
          str(d["steps"][1]["args"]))
    path = write_jsonl([d])
    back = load_canonical(path)
    check("round-trip yields the same Q6 class", back and Q6(back[0]) == Q6(r))


if __name__ == "__main__":
    print("=" * 70)
    print("test_ingest_integrity")
    print("=" * 70)
    test_zero_tool_preserved()
    test_read_ranges_differ()
    test_edit_bodies_differ()
    test_long_prefix_not_truncated()
    test_whitespace_equivalence_is_intended()
    test_empty_vs_populated()
    test_round_trip_preserves_payload()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
