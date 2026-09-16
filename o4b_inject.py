#!/usr/bin/env python3
"""
o4b_inject.py — the seeded defect injector (see O4B_INJECTOR.md, op/v1).

Manufactures executable behavioural defects in PRODUCTION modules, validates
eligibility (clean PASS -> mutated FAIL, not a broken file), records full
provenance, and seals a 12/8 module-cluster split. It NEVER runs an agent and
NEVER edits a test.

    python3 o4b_inject.py generate [--seed N] [--out o4b_corpus/corpus.json]

Stdlib only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPERATOR_VERSION = "op/v1"
SEED = 20260916
M = 20
N_DISCOVERY = 12
CANDIDATE_LIMIT = 5          # seeded start, then in order; every attempt recorded
TIMEOUT = 90
FAST_LIMIT = 20              # clean suites slower than this get at most one operator
SLOW_MAX_OPS = 1
SKIP_DIRS = {".git", "__pycache__", "corpus", "o4b_corpus", ".venv", "venv", "node_modules"}

MODULE_SUITE = {
    "pdi.py": "test_pdi.py",
    "quotient_tower.py": "test_tower.py",
    "adapters.py": "test_adapter.py",
    "ingest.py": "test_ingest.py",
    "multiresolution.py": "test_multiresolution.py",
    "cofinal_mesh.py": "test_cofinal_mesh.py",
    "transport.py": "test_transport.py",
    "stable_quotient.py": "test_stable_quotient.py",
    "collision_mechanism.py": "test_collision_mechanism.py",
    "both_structures.py": "test_both_structures.py",
    "one_question.py": "test_one_question.py",
    "invariance_first.py": "test_invariance_first.py",
    "proof_awareness.py": "test_proof_awareness.py",
    "prime_holonomy.py": "test_prime_holonomy.py",
    "survival_commutation.py": "test_survival_commutation.py",
    "core_monodromy.py": "test_core_monodromy.py",
    "o2_theorem.py": "test_o2_theorem.py",
    "sudoku.py": "test_sudoku.py",
    "agent_profiler.py": "test_profiler.py",
    "zeta_separation.py": "test_ihara_separation.py",
}

CMP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt,
       ast.LtE: ast.Gt, ast.Gt: ast.LtE}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ordered(tree) -> list:
    return sorted(ast.walk(tree),
                  key=lambda n: (getattr(n, "lineno", 10 ** 9),
                                 getattr(n, "col_offset", 10 ** 9), type(n).__name__))


# --------------------------------------------------------------------------
# operators
# --------------------------------------------------------------------------
def _find_arith(tree):
    return [n for n in ordered(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]


def _mut_arith(node):
    node.value = node.value + 1 if isinstance(node.value, int) else node.value * 2
    return True


def _find_cmp(tree):
    return [n for n in ordered(tree) if isinstance(n, ast.Compare)
            and len(n.ops) == 1 and type(n.ops[0]) in CMP]


def _mut_cmp(node):
    node.ops[0] = CMP[type(node.ops[0])]()
    return True


def _find_branch(tree):
    return [n for n in ordered(tree) if isinstance(n, ast.If) and n.body and n.orelse]


def _mut_branch(node):
    node.body, node.orelse = node.orelse, node.body
    return True


def _find_return(tree):
    return [n for n in ordered(tree) if isinstance(n, ast.Return) and n.value is not None]


def _mut_return(node):
    node.value = ast.Constant(value=None)
    return True


def _find_range(tree):
    return [n for n in ordered(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "range" and len(n.args) == 1]


def _mut_range(node):
    node.args[0] = ast.BinOp(left=node.args[0], op=ast.Add(), right=ast.Constant(value=1))
    return True


def _find_default(tree):
    out = []
    for f in ordered(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in f.args.defaults:
                if isinstance(d, ast.Constant) and isinstance(d.value, (int, bool)):
                    out.append(d)
    return sorted(out, key=lambda n: (n.lineno, n.col_offset))


def _mut_default(node):
    node.value = (not node.value) if isinstance(node.value, bool) else node.value + 1
    return True


def _is_validate_call(call: ast.Call) -> bool:
    name = call.func.attr if isinstance(call.func, ast.Attribute) else (
        call.func.id if isinstance(call.func, ast.Name) else "")
    return "validate" in name.lower()


def _find_drop(tree):
    return [n for n in ordered(tree)
            if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                and _is_validate_call(n.value))
            or isinstance(n, ast.Assert)]


class _Remover(ast.NodeTransformer):
    def __init__(self, target):
        self.target = target

    def visit(self, node):
        if node is self.target:
            return None
        return super().visit(node)


def _fix_empty_bodies(tree):
    """Removing a statement can empty a block; insert `pass` so it still parses."""
    for node in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody"):
            body = getattr(node, attr, None)
            if isinstance(body, list) and not body:
                setattr(node, attr, [ast.Pass()])
    return tree


def _mut_drop(tree, node):
    _Remover(node).visit(tree)
    _fix_empty_bodies(tree)
    return True


# --------------------------------------------------------------------------
# operator registry: (id, find, mutate, tree-aware?)
# --------------------------------------------------------------------------
def _apply_drop(tree, node):
    _mut_drop(tree, node)


OPERATORS = [
    ("arith_literal", _find_arith, "node"),
    ("cmp_invert", _find_cmp, "node"),
    ("branch_swap", _find_branch, "node"),
    ("return_sentinel", _find_return, "node"),
    ("off_by_one", _find_range, "node"),
    ("default_arg", _find_default, "node"),
    ("drop_validate", _find_drop, "drop"),
]


def apply_operator(module_src: str, op_id: str, index: int):
    """Return (mutated_source, location) or raise for the indexed candidate."""
    tree = ast.parse(module_src)
    spec = {o[0]: o for o in OPERATORS}[op_id]
    _, find, kind = spec
    cands = find(tree)
    if index >= len(cands):
        raise IndexError("candidate index out of range")
    node = cands[index]
    loc = f"{getattr(node, 'lineno', '?')}:{getattr(node, 'col_offset', '?')}"
    if kind == "drop":
        _apply_drop(tree, node)
    else:
        {"arith_literal": _mut_arith, "cmp_invert": _mut_cmp, "branch_swap": _mut_branch,
         "return_sentinel": _mut_return, "off_by_one": _mut_range,
         "default_arg": _mut_default}[op_id](node)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n", loc, len(cands)


def seeded_index(seed: int, module: str, op_id: str, n: int) -> int:
    return int(sha(f"{seed}:{module}:{op_id}"), 16) % n if n else 0


# --------------------------------------------------------------------------
# snapshots and the verifier
# --------------------------------------------------------------------------
def snapshot(dest: str) -> None:
    def ignore(_d, names):
        return [n for n in names if n in SKIP_DIRS]
    shutil.copytree(HERE, dest, ignore=ignore, dirs_exist_ok=True)


def run_verifier(workdir: str, suite: str):
    """Return (status, detail, elapsed_seconds). status in PASS/FAIL/INFRA/TIMEOUT."""
    import time
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, suite], cwd=workdir, capture_output=True,
                           text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", f"exceeded {TIMEOUT}s", time.time() - t0
    out = (r.stdout or "") + (r.stderr or "")
    for marker in ("SyntaxError", "ImportError", "ModuleNotFoundError", "IndentationError"):
        if marker in out:
            return "INFRA", marker, time.time() - t0
    return (("PASS" if r.returncode == 0 else "FAIL"), f"exit {r.returncode}", time.time() - t0)


def source_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        return "unknown"


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------
def generate(seed: int = SEED) -> dict:
    clean = tempfile.mkdtemp(prefix="o4b_clean_")
    snapshot(clean)
    tasks = []
    print(f"clean snapshot: {clean}", flush=True)
    for module, suite in MODULE_SUITE.items():
        if not os.path.exists(os.path.join(HERE, module)):
            continue
        cstatus, cdetail, celapsed = run_verifier(clean, suite)
        src = open(os.path.join(HERE, module)).read()
        record = {"task_id": f"t{len(tasks):02d}_{module.replace('.py','')}",
                  "module_cluster": module, "seed": seed,
                  "verifier_command": f"python3 {suite}",
                  "clean_result": f"{cstatus} ({cdetail}) {celapsed:.1f}s", "attempts": []}
        if cstatus != "PASS":
            record.update(eligibility="no", exclusion_reason="clean_fail", task_text="")
            tasks.append(record)
            print(f"  {module:<24} clean_fail", flush=True)
            continue
        slow = celapsed > FAST_LIMIT
        ops = OPERATORS
        climit = 1 if slow else CANDIDATE_LIMIT   # slow: all operators, one candidate each
        work = tempfile.mkdtemp(prefix="o4b_mut_")
        snapshot(work)                       # ONE workdir per module, reused
        task = None
        for op_id, find, _kind in ops:
            cands = find(ast.parse(src))
            if not cands:
                record["attempts"].append({"operator": op_id, "reason": "no_candidates"})
                continue
            start = seeded_index(seed, module, op_id, len(cands))   # seeded start, then in order
            for k in range(min(climit, len(cands))):
                idx = (start + k) % len(cands)
                try:
                    mutated, loc, n = apply_operator(src, op_id, idx)
                    ast.parse(mutated)
                except Exception as e:  # noqa: BLE001
                    record["attempts"].append({"operator": op_id, "index": idx,
                                               "reason": f"syntax_error:{type(e).__name__}"})
                    continue
                with open(os.path.join(work, module), "w") as f:
                    f.write(mutated)
                status, detail, elapsed = run_verifier(work, suite)
                with open(os.path.join(work, module), "w") as f:   # restore the clean module
                    f.write(src)
                reason = {"PASS": "did_not_flip", "INFRA": "infra_error",
                          "TIMEOUT": "timeout"}.get(status)
                record["attempts"].append({"operator": op_id, "index": idx, "location": loc,
                                           "candidates": n, "result": status, "detail": detail,
                                           "elapsed": round(elapsed, 2), "reason": reason or ""})
                print(f"  {module:<24} {op_id:<16} idx={idx:<4} {status:<7} {elapsed:5.1f}s",
                      flush=True)
                if status == "FAIL":
                    task = {"task_text": (
                        f"The repository's test suite `python3 {suite}` is failing. A regression "
                        f"was introduced into the production code. Find and fix the defect. "
                        f"Do not modify the tests."),
                        "operator": op_id, "operator_version": OPERATOR_VERSION,
                        "candidate_index": idx, "candidate_location": loc,
                        "clean_hash": sha(src), "mutated_hash": sha(mutated),
                        "patch_hash": sha(src + "=>" + mutated),
                        "mutated_result": f"{status} ({detail})", "eligibility": "yes",
                        "exclusion_reason": ""}
                    break
            if task:
                break
        shutil.rmtree(work, ignore_errors=True)
        record.update(task if task else
                      {"eligibility": "no", "exclusion_reason": "exhausted", "task_text": ""})
        tasks.append(record)
    shutil.rmtree(clean, ignore_errors=True)

    eligible = [t for t in tasks if t["eligibility"] == "yes"]
    order = sorted(t["module_cluster"] for t in eligible)
    random.Random(seed).shuffle(order)
    discovery_clusters = set(order[:N_DISCOVERY])
    for t in tasks:
        t["split"] = ("discovery" if t["module_cluster"] in discovery_clusters
                      else ("heldout" if t["eligibility"] == "yes" else "none"))
    core = {"operator_version": OPERATOR_VERSION, "seed": seed, "M": M,
            "source_commit": source_commit(), "verifier_env": {
                "python": sys.version.split()[0], "platform": platform.platform()},
            "n_eligible": len(eligible), "n_discovery": len(discovery_clusters),
            "n_heldout": len(eligible) - len(discovery_clusters),
            "tasks": [{k: t.get(k) for k in
                       ("task_id", "module_cluster", "operator", "candidate_location",
                        "clean_hash", "mutated_hash", "eligibility", "split")}
                      for t in tasks]}
    return {"fingerprint": sha(json.dumps(core, sort_keys=True)), "core": core, "tasks": tasks}


def main() -> None:
    ap = argparse.ArgumentParser(description="O4b seeded defect injector")
    ap.add_argument("cmd", choices=["generate"])
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=os.path.join(HERE, "o4b_corpus", "corpus.json"))
    a = ap.parse_args()
    result = generate(a.seed)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=2)
    c = result["core"]
    print(f"eligible {c['n_eligible']}/{len(result['tasks'])}  "
          f"discovery {c['n_discovery']}  heldout {c['n_heldout']}")
    print(f"fingerprint {result['fingerprint']}")
    print(f"wrote {a.out}")
    for t in result["tasks"]:
        print(f"  {t['split']:<9} {t['module_cluster']:<24} {t.get('operator','-'):<16} "
              f"{t.get('eligibility')} {t.get('exclusion_reason','')}")


if __name__ == "__main__":
    main()
