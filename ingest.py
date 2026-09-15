#!/usr/bin/env python3
"""
ingest.py — one behavioural-run representation across agent frameworks.

PDI does not care which framework produced a trace. It needs three things per run:

    the ordered tool calls   (what the agent did)
    their arguments          (what it pointed them at)
    the terminal outcome     (whether it got somewhere)

Everything else is decoration. This module normalises several real trace formats
into that one representation, so the same instrument reads any of them.

    canonical   the minimal format below — emit this from anything
    pi          pi agent session JSONL (event stream)
    openai      OpenAI-style chat with tool_calls
    langsmith   LangSmith / LangGraph run exports (JSONL of run objects)

CANONICAL FORMAT
----------------
One JSON object per line:

    {"model": "...", "project": "...", "prompt": "...", "outcome": "stop",
     "steps": [{"tool": "bash", "args": {"command": "ls"}, "error": null}, ...]}

`outcome` is the terminal state: "stop" means the run finished on its own terms
and counts as a success; anything else ("error", "aborted", "length", "toolUse")
does not. If your framework has a different success notion, map it onto "stop".

That is the whole contract. If you can emit four keys and a list, PDI can read
your agent.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable, Iterator, Optional

from adapters import Step, Turn as Run, load_pi_session

CANONICAL, PI, OPENAI, LANGSMITH = "canonical", "pi", "openai", "langsmith"
FORMATS = (CANONICAL, PI, OPENAI, LANGSMITH)


# --------------------------------------------------------------------------
# tolerant JSON reading
# --------------------------------------------------------------------------
def _iter_objects(path: str) -> Iterator[dict]:
    """Yield JSON objects from a file that may be JSONL, a JSON array, or one
    JSON object. Blank and malformed lines are skipped rather than fatal."""
    text = open(path, errors="ignore").read().strip()
    if not text:
        return
    # a whole-file JSON value?
    try:
        whole = json.loads(text)
    except json.JSONDecodeError:
        whole = None
    if isinstance(whole, list):
        for o in whole:
            if isinstance(o, dict):
                yield o
        return
    if isinstance(whole, dict) and _looks_like_a_run(whole):
        yield whole
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            yield o


def _looks_like_a_run(o: dict) -> bool:
    return bool({"steps", "messages", "run_type", "trace_id", "type"} & set(o))


def _mk(tool: str, args: Any, error: Optional[str] = None) -> Step:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"raw": args}
    return Step(tool=tool or "?", args=args if isinstance(args, dict) else {"raw": args},
                error=error)


def _run(steps, outcome, model="unknown", project="unknown", path="", prompt=""):
    return Run(steps=list(steps), outcome=outcome or "unknown", model=model or "unknown",
               project=project or "unknown",
               session=os.path.basename(path), prompt=prompt, cwd=project or "")


# --------------------------------------------------------------------------
# format 1: canonical
# --------------------------------------------------------------------------
def load_canonical(path: str) -> list[Run]:
    out = []
    for o in _iter_objects(path):
        steps = [_mk(s.get("tool"), s.get("args"), s.get("error"))
                 for s in (o.get("steps") or []) if isinstance(s, dict)]
        if not steps:
            continue
        out.append(_run(steps, o.get("outcome"), o.get("model"), o.get("project"),
                        path, o.get("prompt", "")))
    return out


def to_canonical(run: Run) -> dict:
    """Emit the canonical form — so any tool can write what PDI reads."""
    return {
        "model": run.model, "project": run.project, "prompt": run.prompt,
        "outcome": run.outcome,
        "steps": [{"tool": s.tool, "args": s.args, "error": s.error} for s in run.steps],
    }


def write_canonical(runs: Iterable[Run], path: str) -> int:
    n = 0
    with open(path, "w") as f:
        for r in runs:
            f.write(json.dumps(to_canonical(r)) + "\n")
            n += 1
    return n


# --------------------------------------------------------------------------
# format 2: OpenAI-style chat with tool_calls
# --------------------------------------------------------------------------
def load_openai(path: str) -> list[Run]:
    """Handles a conversation object ({"messages": [...]}) or an event stream
    where assistant messages carry `tool_calls` and `role: "tool"` replies."""
    msgs: list[dict] = []
    for o in _iter_objects(path):
        if isinstance(o.get("messages"), list):
            msgs.extend(o["messages"])
        elif "role" in o:
            msgs.append(o)

    model = next((m.get("model") for m in msgs if m.get("model")), "unknown")
    runs: list[Run] = []
    steps: list[Step] = []
    pending: dict[str, Step] = {}
    prompt, outcome = "", ""

    def flush():
        nonlocal steps, outcome, prompt
        if steps:
            runs.append(_run(steps, outcome or "noToolUse", model, "openai", path, prompt))
        steps, outcome, prompt = [], "", ""

    for m in msgs:
        role = m.get("role")
        if role == "user":
            flush()
            c = m.get("content")
            prompt = (c if isinstance(c, str) else json.dumps(c))[:120] if c else ""
        elif role == "assistant":
            for tc in (m.get("tool_calls") or []):
                fn = tc.get("function") or {}
                st = _mk(fn.get("name") or tc.get("name"), fn.get("arguments") or {})
                steps.append(st)
                pending[tc.get("id")] = st
            # OpenAI has no terminal stopReason; a final text reply means done
            if not (m.get("tool_calls")) and (m.get("content") or "").strip():
                outcome = outcome or "stop"
        elif role in ("tool", "function"):
            st = pending.pop(m.get("tool_call_id") or m.get("id"), None)
            if st is None:
                continue
            # heuristic: explicit flag, else an Error-prefixed payload
            txt = m.get("content")
            txt = txt if isinstance(txt, str) else json.dumps(txt)
            if m.get("is_error") or m.get("error") or (txt or "").lstrip().startswith(("Error", "error", "Traceback")):
                st.error = (txt or "error")[:80]
    flush()
    return runs


# --------------------------------------------------------------------------
# format 3: LangSmith / LangGraph run exports
# --------------------------------------------------------------------------
def load_langsmith(path: str) -> list[Run]:
    """Groups run objects by trace_id, orders by start_time, keeps tool runs as
    steps. There is no success flag in this format, so the outcome is derived:
    'stop' when no run in the trace errored, otherwise 'error'. Documented
    because it is a heuristic, not a field."""
    traces: dict[str, list[dict]] = {}
    for o in _iter_objects(path):
        tid = o.get("trace_id") or o.get("session_id") or o.get("id")
        if tid:
            traces.setdefault(str(tid), []).append(o)

    runs: list[Run] = []
    for tid, objs in traces.items():
        objs.sort(key=lambda o: (o.get("start_time") or "", o.get("id") or ""))
        steps: list[Step] = []
        err = None
        for o in objs:
            if (o.get("run_type") or "").lower() not in ("tool", "chain", "retriever"):
                continue
            args = o.get("inputs") if isinstance(o.get("inputs"), dict) else o.get("inputs")
            e = o.get("error")
            if e and not err:
                err = str(e)[:80]
            steps.append(_mk(o.get("name"), args or {}, str(e)[:80] if e else None))
        if not steps:
            continue
        model = next((o.get("extra", {}).get("metadata", {}).get("ls_model_name")
                      for o in objs
                      if isinstance(o.get("extra"), dict)), None) or "unknown"
        runs.append(_run(steps, "error" if err else "stop", model, "langsmith",
                         path, str(objs[0].get("name", ""))[:120]))
    return runs


# --------------------------------------------------------------------------
# detection and dispatch
# --------------------------------------------------------------------------
def detect_format(path: str) -> str:
    """Sniff the first JSON object. Falls back to counting structural markers."""
    scores = {CANONICAL: 0, PI: 0, OPENAI: 0, LANGSMITH: 0}
    seen = 0
    for o in _iter_objects(path):
        keys = set(o)
        if {"type", "message"} <= keys or o.get("type") in ("session", "message", "model_change"):
            scores[PI] += 3
        if "run_type" in keys or "trace_id" in keys:
            scores[LANGSMITH] += 3
        if "messages" in keys or (o.get("role") in ("user", "assistant", "tool")):
            scores[OPENAI] += 2
        if "steps" in keys:
            scores[CANONICAL] += 3
        seen += 1
        if seen >= 50:
            break
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else CANONICAL


LOADERS = {CANONICAL: load_canonical, PI: load_pi_session,
           OPENAI: load_openai, LANGSMITH: load_langsmith}


def load_any(path: str, fmt: Optional[str] = None) -> list[Run]:
    fmt = fmt or detect_format(path)
    return LOADERS.get(fmt, load_canonical)(path)


def load_paths(paths: Iterable[str], fmt: Optional[str] = None) -> list[Run]:
    """Accept files or directories; walk directories for *.jsonl / *.json."""
    out: list[Run] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith((".jsonl", ".json")):
                        try:
                            out.extend(load_any(os.path.join(root, f), fmt))
                        except Exception:
                            continue
        elif os.path.isfile(p):
            try:
                out.extend(load_any(p, fmt))
            except Exception:
                continue
    return out
