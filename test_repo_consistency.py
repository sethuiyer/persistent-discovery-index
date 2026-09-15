#!/usr/bin/env python3
"""
test_repo_consistency.py — the repo's own discipline, applied to the repo.

v0.17.1 fixed a stale suite count and v0.18.0 reintroduced it. v0.18.0 also cited
`test_collision_mechanism` in SPINE.md before that file existed. Both are the same
failure: a claim about the repository, hand-maintained, drifting from the artefact.

A warrant-carrying system cannot hand-maintain its own claims. This suite tests
them instead, so they cannot drift again.

Checks:
  1. every suite cited in SPINE.md / README.md exists on disk
  2. the README's suite count equals the real count
  3. every module named in the README's "What is implemented" exists
  4. no ledger row is malformed
  5. every .py module compiles

Run: python3 test_repo_consistency.py     (exit 0 on success)
"""
from __future__ import annotations

import os
import py_compile
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def read(fn: str) -> str:
    with open(os.path.join(HERE, fn), encoding="utf-8", errors="ignore") as f:
        return f.read()


def real_suites() -> list[str]:
    return sorted(f for f in os.listdir(HERE)
                  if (f.startswith("test_") and f.endswith(".py")) or f == "toys.py")


def test_cited_suites_exist() -> None:
    print("1. every cited suite exists")
    cited: set[str] = set()
    for doc in ("SPINE.md", "README.md"):
        cited |= set(re.findall(r"\b(test_[a-z_]+\.py)\b", read(doc)))
        cited |= set(re.findall(r"\btest_([a-z_]+)\b(?!\.py)", read(doc)))
    # normalise the bare-name form back to filenames
    names = {c if c.endswith(".py") else f"test_{c}.py" for c in cited}
    missing = sorted(n for n in names if not os.path.exists(os.path.join(HERE, n)))
    check(f"{len(names)} distinct suites cited in SPINE/README", len(names) > 0)
    check("none are missing from disk", not missing, f"missing: {missing}")


def test_suite_count_matches() -> None:
    print("2. the README's suite count is the real count")
    txt = read("README.md")
    m = re.search(r"\*\*([A-Z][a-z]+) self-checking suites\*\*", txt)
    check("README states a suite count", m is not None)
    if not m:
        return
    words = {"Ten": 10, "Eleven": 11, "Twelve": 12, "Thirteen": 13, "Fourteen": 14,
             "Fifteen": 15, "Sixteen": 16, "Seventeen": 17, "Eighteen": 18,
             "Nineteen": 19, "Twenty": 20}
    claimed = words.get(m.group(1))
    check("the number word is recognised", claimed is not None, m.group(1))
    actual = len(real_suites())
    check("README count == suites on disk", claimed == actual,
          f"README says {claimed}, disk has {actual}")
    # and no OTHER stale count lurks elsewhere
    others = re.findall(r"\b(?:Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty) self-checking suites\b", txt)
    check("exactly one suite-count claim in the README", len(others) <= 1, str(others))


def test_modules_named_in_readme_exist() -> None:
    print("3. modules named in the README exist")
    named = set(re.findall(r"`([a-z_0-9]+\.py)`", read("README.md")))
    missing = sorted(n for n in named if not os.path.exists(os.path.join(HERE, n)))
    check(f"{len(named)} modules named", len(named) > 0)
    check("all present", not missing, f"missing: {missing}")


def test_ledger_wellformed() -> None:
    print("4. the ledger is well-formed")
    rows = [l for l in read("SPINE.md").splitlines() if re.match(r"^\| *[0-9]", l)]
    check("ledger has rows", len(rows) > 10, str(len(rows)))
    bad = [l for l in rows if l.count("|") < 3]
    check("every row has at least 3 columns", not bad, str(bad[:2]))
    # every row must carry an explicit status, not an empty cell
    empty = [l for l in rows if l.rstrip().endswith("||")]
    check("no row has an empty status cell", not empty, str(empty[:2]))


def test_everything_compiles() -> None:
    print("5. every module compiles")
    bad = []
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py"):
            try:
                py_compile.compile(os.path.join(HERE, f), doraise=True)
            except py_compile.PyCompileError:
                bad.append(f)
    check("all modules compile", not bad, str(bad))


if __name__ == "__main__":
    print("=" * 70)
    print("test_repo_consistency")
    print("=" * 70)
    test_cited_suites_exist()
    test_suite_count_matches()
    test_modules_named_in_readme_exist()
    test_ledger_wellformed()
    test_everything_compiles()
    print("=" * 70)
    if FAILS:
        print(f"FAILED: {len(FAILS)} -> {FAILS}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
