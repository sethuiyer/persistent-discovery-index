#!/usr/bin/env python3
"""
o4b_run.py — run the discovery-baseline captures for the frozen experiment.

Per (task, run):
  1. materialise a FRESH mutated tree (regenerated deterministically from the
     sealed corpus) and VERIFY the regenerated clean/mutated hashes match before
     anything runs;
  2. run `pi --mode rpc`, wait for `agent_settled`, capture the session;
  3. RESTORE the verifier files from the pristine snapshot (the agent cannot edit
     its own grader), then run the verifier independently;
  4. record the outcome. Every scheduled run is recorded — crashes, timeouts,
     UNKNOWN and missing cost included; missing usage stays `null`.

No silent reruns, no dropped records, no held-out tasks.

    python3 o4b_run.py --smoke    # no paid agent
    python3 o4b_run.py --run      # the 24 discovery baseline runs

Stdlib only.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adapters import load_pi_session                              # noqa: E402
from evaluators import command_exit                               # noqa: E402
from o4b_inject import HERE, OPERATORS, SKIP_DIRS, apply_operator, sha  # noqa: E402

CORPUS = os.path.join(HERE, "o4b_corpus", "corpus.json")
RESULTS = os.path.join(HERE, "o4b_corpus", "baseline.json")
MODEL = "deepseek-flash"
AGENT_TIMEOUT = 900
# never expose the O4b apparatus (mutation metadata, the ruler, the corpus) to the agent
AGENT_HIDE = {"O4B_INJECTOR.md", "O4B_PREDECLARATION.md", "O4B_SCOPE.md", "o4b_inject.py",
              "o4b_run.py", "o4b_stat.py", "o4b.py", "test_o4b_stat.py", "o4b_corpus"}


def load_corpus() -> dict:
    with open(CORPUS) as f:
        return json.load(f)


def agent_snapshot(dest: str) -> None:
    """A pristine copy of the repo, minus anything that could leak the mutation."""
    def ignore(_d, names):
        return [n for n in names if n in SKIP_DIRS or n in AGENT_HIDE]
    shutil.copytree(HERE, dest, ignore=ignore, dirs_exist_ok=True)


def regenerate(task: dict):
    """Regenerate the mutated source and check it against the sealed hashes."""
    src = open(os.path.join(HERE, task["module_cluster"])).read()
    mutated, loc, n = apply_operator(src, task["operator"], task["candidate_index"])
    ok = sha(src) == task["clean_hash"] and sha(mutated) == task["mutated_hash"]
    return src, mutated, ok


def session_usage(session_dir: str):
    files = glob.glob(os.path.join(session_dir, "*.jsonl"))
    if not files:
        return None, None, None, None
    path = max(files, key=os.path.getmtime)
    turns = load_pi_session(path)
    costs = [t.cost for t in turns if t.cost is not None]
    tins = [t.tokens_input for t in turns if t.tokens_input is not None]
    touts = [t.tokens_output for t in turns if t.tokens_output is not None]
    return ((sum(costs) if costs else None), (sum(tins) if tins else None),
            (sum(touts) if touts else None), path)


def run_agent_rpc(workdir: str, prompt: str, session_dir: str, model: str, timeout: int):
    """Start `pi --mode rpc`, send the prompt, wait for agent_settled."""
    cmd = ["pi", "--mode", "rpc", "--model", model, "--session-dir", session_dir]
    p = subprocess.Popen(cmd, cwd=workdir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, bufsize=1)
    settled = threading.Event()
    events = []

    def reader():
        try:
            for line in p.stdout:
                events.append(line)
                try:
                    o = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                if o.get("type") == "agent_settled":
                    settled.set()
                    return
        except Exception:  # noqa: BLE001
            return

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=lambda: [None for _ in p.stderr], daemon=True).start()
    try:
        p.stdin.write(json.dumps({"id": "1", "type": "prompt", "message": prompt}) + "\n")
        p.stdin.flush()
    except Exception as e:  # noqa: BLE001
        return "error", f"stdin: {e}", events
    ok = settled.wait(timeout)
    if ok:
        status = "settled"
    elif p.poll() is not None:
        status = f"exit({p.returncode})"
    else:
        status = "timeout"
    try:
        p.terminate()
        p.wait(timeout=10)
    except Exception:  # noqa: BLE001
        try:
            p.kill()
        except Exception:  # noqa: BLE001
            pass
    return status, f"{len(events)} events", events


def restore_tests(workdir: str, pristine: str) -> None:
    """The agent cannot edit its own grader: verifier files come from pristine."""
    for f in os.listdir(pristine):
        if f.startswith("test_") and f.endswith(".py"):
            shutil.copy2(os.path.join(pristine, f), os.path.join(workdir, f))


def run_one(task: dict, run_index: int, pristine: str, agent: str, model: str,
            timeout: int) -> dict:
    suite = task["verifier_command"].split()[-1]
    rec = {"task_id": task["task_id"], "module_cluster": task["module_cluster"],
           "run_index": run_index, "suite": suite, "scheduled": True,
           "operator": task.get("operator"), "verified_outcome": None,
           "cost": None, "tokens_input": None, "tokens_output": None,
           "regeneration_ok": False, "agent_status": None, "status": "error"}
    work = tempfile.mkdtemp(prefix="o4b_run_")
    try:
        agent_snapshot(work)
        src, mutated, ok = regenerate(task)
        rec["regeneration_ok"] = ok
        if not ok:
            rec["status"] = "invalid_regeneration"
            return rec
        with open(os.path.join(work, task["module_cluster"]), "w") as f:
            f.write(mutated)
        if agent == "stub":
            rec["agent_status"] = "stub"
        else:
            sdir = os.path.join(work, ".sessions")
            os.makedirs(sdir, exist_ok=True)
            st, det, _ = run_agent_rpc(work, task["task_text"], sdir, model, timeout)
            rec["agent_status"], rec["agent_detail"] = st, det
            c, ti, to, sp = session_usage(sdir)
            rec.update(cost=c, tokens_input=ti, tokens_output=to, session=sp)
        restore_tests(work, pristine)
        outcome, ev = command_exit([sys.executable, suite], cwd=work, timeout=300)
        rec["verified_outcome"], rec["evaluator"] = outcome, str(ev)
        rec["status"] = "ok"
    except Exception as e:  # noqa: BLE001
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return rec


# --------------------------------------------------------------------------
def smoke() -> int:
    print("=" * 70)
    print("o4b_run SMOKE (no paid agent)")
    print("=" * 70)
    corpus = load_corpus()
    disc = [t for t in corpus["tasks"] if t["split"] == "discovery"]
    print(f"corpus fingerprint: {corpus['fingerprint'][:16]}  discovery tasks: {len(disc)}")
    pristine = tempfile.mkdtemp(prefix="o4b_pristine_")
    agent_snapshot(pristine)
    fails = 0

    # 1. regeneration
    ok = sum(1 for t in disc[:3] if regenerate(t)[2])
    print(f"1. regeneration hashes match sealed corpus: {ok}/3")
    fails += (ok != 3)

    # 2. isolation: two fresh trees, same regenerated content, different dirs
    a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
    agent_snapshot(a); agent_snapshot(b)
    same = open(os.path.join(a, "pdi.py")).read() == open(os.path.join(b, "pdi.py")).read()
    distinct = a != b
    print(f"2. fresh trees: distinct dirs={distinct} identical clean content={same}")
    fails += not (distinct and same)
    shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)

    # 3. outcome recording + verifier protection (stub does not fix the defect)
    rec = run_one(disc[0], 1, pristine, "stub", MODEL, 5)
    print(f"3. stub run record: status={rec['status']} regen={rec['regeneration_ok']} "
          f"outcome={rec['verified_outcome']} cost={rec['cost']}")
    fails += not (rec["status"] == "ok" and rec["regeneration_ok"]
                  and rec["verified_outcome"] == "failure" and rec["cost"] is None)

    # 4. usage capture: synthetic session with usage, and one without
    def synth(dirpath, with_usage):
        os.makedirs(dirpath, exist_ok=True)
        p = os.path.join(dirpath, "s.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"type": "session", "cwd": "/x"}) + "\n")
            f.write(json.dumps({"type": "message", "message": {
                "role": "user", "content": [{"type": "text", "text": "hi"}]}}) + "\n")
            m = {"role": "assistant", "stopReason": "stop",
                 "content": [{"type": "text", "text": "ok"}]}
            if with_usage:
                m["usage"] = {"input": 11, "output": 4, "cost": 0.03}
            f.write(json.dumps({"type": "message", "message": m}) + "\n")
        return p
    d1, d0 = tempfile.mkdtemp(), tempfile.mkdtemp()
    synth(d1, True); synth(d0, False)
    c1, i1, o1, _ = session_usage(d1)
    c0, i0, o0, _ = session_usage(d0)
    print(f"4. usage capture: with={c1}/{i1}/{o1}  without={c0}/{i0}/{o0}")
    fails += not (c1 == 0.03 and i1 == 11 and o1 == 4 and c0 is None and i0 is None)
    shutil.rmtree(d1, ignore_errors=True); shutil.rmtree(d0, ignore_errors=True)

    # 5. leakage: the agent snapshot has no O4b apparatus
    leaked = [n for n in AGENT_HIDE if os.path.exists(os.path.join(pristine, n))]
    print(f"5. mutation metadata hidden from agent tree: {'none' if not leaked else leaked}")
    fails += bool(leaked)

    shutil.rmtree(pristine, ignore_errors=True)
    print("=" * 70)
    print("SMOKE PASS" if not fails else f"SMOKE FAIL ({fails})")
    return 1 if fails else 0


def run(limit: int | None = None) -> int:
    corpus = load_corpus()
    disc = [t for t in corpus["tasks"] if t["split"] == "discovery"]
    pristine = tempfile.mkdtemp(prefix="o4b_pristine_")
    agent_snapshot(pristine)
    records = []
    t0 = time.time()
    for task in disc:
        for r in (1, 2):
            if limit and len(records) >= limit:
                break
            rec = run_one(task, r, pristine, "pi", MODEL, AGENT_TIMEOUT)
            records.append(rec)
            print(f"  {task['task_id']:<26} run {r}  {rec['status']:<10} "
                  f"agent={rec['agent_status']:<12} verified={rec['verified_outcome']} "
                  f"cost={rec['cost']}", flush=True)
    shutil.rmtree(pristine, ignore_errors=True)
    out = {"corpus_fingerprint": corpus["fingerprint"], "scheduled": len(records),
           "model": MODEL, "elapsed_s": round(time.time() - t0, 1), "records": records}
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    ok = [r for r in records if r["status"] == "ok"]
    succ = [r for r in ok if r["verified_outcome"] == "success"]
    priced = [r for r in ok if r["cost"] is not None]
    print(f"\nscheduled {len(records)}  ok {len(ok)}  verified success {len(succ)}  "
          f"cost present {len(priced)}  wrote {RESULTS}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="O4b discovery-baseline runner")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.smoke:
        sys.exit(smoke())
    if a.run:
        sys.exit(run(a.limit))
    ap.print_help()
