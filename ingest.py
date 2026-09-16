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
    otel        OpenTelemetry GenAI spans (OTLP/JSON) — gen_ai.* attributes
    autogen     AutoGen conversation histories (v0.2 message dicts, v0.4 typed events)
    crewai      CrewAI crew output (tolerant)

SCHEMA CONFIDENCE
-----------------
    otel     written to a PUBLISHED SPEC (`gen_ai.*` semantic conventions)
    autogen  written to a DOCUMENTED message schema, both major shapes it has shipped
    crewai   written to an INFERRED schema — CrewAI publishes no stable trace format

None of the three was validated against a live capture. The fixtures in
`fixtures/` are CONSTRUCTED to the schemas above, so these tests establish
schema conformance and edge preservation, not field-testedness. The OTel loader
is the one to trust, because it is the one written to a spec; CrewAI is the one
most likely to need adjustment, and CrewAI users are the ones most likely to
need `to_canonical`.

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
OTEL, AUTOGEN, CREWAI = "otel", "autogen", "crewai"
FORMATS = (CANONICAL, PI, OPENAI, LANGSMITH, OTEL, AUTOGEN, CREWAI)


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
    """True if this dict is a whole trace container rather than one event line.

    Must include the container keys of every supported format, or _iter_objects
    will fall through to line-parsing and silently drop a pretty-printed file.
    """
    return bool({"steps", "messages", "run_type", "trace_id", "type",
                 "resourceSpans", "scopeSpans", "instrumentationLibrarySpans",
                 "tasks_output", "final_output", "chat_history", "tasks"} & set(o))


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
        # A zero-tool episode ("steps": []) is a real run: the agent answered
        # without calling a tool. Only an object with no `steps` key at all is
        # not a canonical run. v0.27.0 dropped the zero-tool case (`if not steps`).
        if "steps" not in o:
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
# format 5: OpenTelemetry GenAI spans (OTLP/JSON)
# --------------------------------------------------------------------------
# Written to the published semantic conventions, not to a capture:
#   gen_ai.operation.name        "execute_tool" | "chat" | "invoke_agent" | ...
#   gen_ai.tool.name             the tool
#   gen_ai.tool.call.arguments   THE EDGES -- what it pointed at
#   gen_ai.tool.call.id          pairs a call with its result
#   gen_ai.request.model         the model
#   gen_ai.response.finish_reasons  e.g. ["stop"]
#   error.type / status.code == 2   the failure marker
# No live capture was made. Fixtures are constructed to this schema.
def _otel_value(v: Any) -> Any:
    """Decode an OTLP AnyValue."""
    if not isinstance(v, dict):
        return v
    if "stringValue" in v:
        return v["stringValue"]
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return v["intValue"]
    if "doubleValue" in v:
        return v["doubleValue"]
    if "boolValue" in v:
        return v["boolValue"]
    if "arrayValue" in v:
        av = v["arrayValue"]
        # spec form is {"values": [...]}; tolerate a bare list too
        if isinstance(av, list):
            return [_otel_value(x) for x in av]
        return [_otel_value(x) for x in (av or {}).get("values", [])]
    if "kvlistValue" in v:
        kv = v["kvlistValue"]
        items = kv if isinstance(kv, list) else (kv or {}).get("values", [])
        return {i.get("key"): _otel_value(i.get("value", {})) for i in items}
    return None


def _otel_attrs(container: dict) -> dict:
    out = {}
    for a in (container.get("attributes") or []):
        if isinstance(a, dict) and "key" in a:
            out[a["key"]] = _otel_value(a.get("value", {}))
    return out


def _iter_spans(path: str) -> Iterator[tuple[dict, dict]]:
    """Yield (resource attrs, span) from OTLP/JSON, tolerating JSONL and the
    older instrumentationLibrarySpans key."""
    for o in _iter_objects(path):
        for rs in (o.get("resourceSpans") or []):
            if not isinstance(rs, dict):
                continue
            res = _otel_attrs(rs.get("resource") or {})
            scopes = rs.get("scopeSpans") or rs.get("instrumentationLibrarySpans") or []
            for ss in scopes:
                if not isinstance(ss, dict):
                    continue
                for sp in (ss.get("spans") or []):
                    if isinstance(sp, dict):
                        yield res, sp


def load_otel_genai(path: str) -> list[Run]:
    """Group spans by traceId; tool spans become steps ordered by start time.

    Tool spans are typically NESTED under agent/chat spans, so every span in the
    trace is considered, not just the roots.
    """
    traces: dict[str, list[tuple[int, dict, dict]]] = {}
    for res, sp in _iter_spans(path):
        tid = sp.get("traceId") or "no-trace"
        try:
            t0 = int(sp.get("startTimeUnixNano") or 0)
        except (TypeError, ValueError):
            t0 = 0
        traces.setdefault(tid, []).append((t0, res, sp))

    runs: list[Run] = []
    for tid, members in traces.items():
        members.sort(key=lambda m: m[0])
        steps: list[Step] = []
        model = project = ""
        errored = False
        stopped = False
        timed_out = False
        for _, res, sp in members:
            at = _otel_attrs(sp)
            project = project or str(res.get("service.name") or res.get("service.namespace") or "")
            model = model or str(at.get("gen_ai.request.model") or at.get("gen_ai.response.model") or "")
            op = str(at.get("gen_ai.operation.name") or "")
            tool = at.get("gen_ai.tool.name")
            if tool or op in ("execute_tool", "tool_call"):
                raw = at.get("gen_ai.tool.call.arguments")
                if raw is None:
                    raw = at.get("gen_ai.tool.arguments")
                err = at.get("error.type")
                status = sp.get("status") or {}
                if not err and status.get("code") == 2:
                    err = status.get("message") or "error"
                steps.append(_mk(str(tool or "?"), raw, str(err) if err else None))
            if at.get("error.type") or (sp.get("status") or {}).get("code") == 2:
                errored = True
            if op == "invoke_agent" and at.get("error.type") == "timeout":
                timed_out = True
            fr = at.get("gen_ai.response.finish_reasons") or at.get("gen_ai.response.finish_reason")
            if isinstance(fr, list):
                if "stop" in fr:
                    stopped = True
            elif fr == "stop":
                stopped = True
        if not steps:
            continue
        if timed_out:
            outcome = "timeout"
        elif errored:
            outcome = "error"
        elif stopped:
            outcome = "stop"
        else:
            outcome = "noToolUse"
        runs.append(_run(steps, outcome, model or "unknown", project or "otel",
                         path, ""))
    return runs


# --------------------------------------------------------------------------
# format 6: AutoGen conversation histories
# --------------------------------------------------------------------------
# Handles both shapes AutoGen has shipped:
#   v0.2/0.3  [{"role":..,"name":..,"content":..,"function_call":{..}}]
#             [{"role":"tool","tool_call_id":..,"content":..}]
#   v0.4      typed events: ToolCallRequestEvent / ToolCallExecutionEvent
# No live capture was made. Fixtures are constructed to this schema.
def _autogen_steps_from_messages(msgs: list[dict],
                                 top_stop_reason: str = "") -> tuple[list[Step], str, bool]:
    """Normalise an AutoGen message list into steps.

    Pairing note: v0.2/0.3 put `function_call` on the assistant message but the
    id on the FUNCTION message (or omit it entirely), so keying pending calls by
    tool_call_id alone silently mis-attributes results -- including errors -- to
    the wrong step. We therefore pair by id when present, else by tool NAME to
    the oldest unpaired call, else FIFO.
    """
    steps: list[Step] = []
    by_id: dict[str, Step] = {}
    unpaired: list[tuple[Optional[str], Step]] = []
    errored = False
    stop_reason = top_stop_reason

    for m in msgs:
        if not isinstance(m, dict):
            continue
        stop_reason = str(m.get("stop_reason") or m.get("stopReason")
                          or stop_reason or "")
        mtype = m.get("type")

        # --- v0.4 typed events --------------------------------------------
        if mtype == "ToolCallRequestEvent":
            for c in (m.get("content") or []):
                if not isinstance(c, dict):
                    continue
                st = _mk(c.get("name"), c.get("arguments"))
                steps.append(st)
                if c.get("id"):
                    by_id[str(c["id"])] = st
                else:
                    unpaired.append((c.get("name"), st))
            continue
        if mtype == "ToolCallExecutionEvent":
            for c in (m.get("content") or []):
                if not isinstance(c, dict):
                    continue
                st = by_id.pop(str(c.get("call_id") or ""), None)
                if st is None:
                    st = _take_unpaired(unpaired, c.get("name"))
                if st is None:
                    continue
                if c.get("is_error"):
                    st.error = str(c.get("content") or "error")[:80]
                    errored = True
            continue

        # --- v0.2/0.3 -----------------------------------------------------
        if m.get("function_call"):
            fc = m["function_call"] or {}
            st = _mk(fc.get("name"), fc.get("arguments"))
            steps.append(st)
            if m.get("tool_call_id"):
                by_id[str(m["tool_call_id"])] = st
            else:
                unpaired.append((fc.get("name"), st))
        for tc in (m.get("tool_calls") or []):
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") or {}
            st = _mk(fn.get("name") or tc.get("name"), fn.get("arguments"))
            steps.append(st)
            if tc.get("id"):
                by_id[str(tc["id"])] = st
            else:
                unpaired.append((fn.get("name") or tc.get("name"), st))

        if m.get("role") in ("tool", "function"):
            st = by_id.pop(str(m.get("tool_call_id") or m.get("id") or ""), None)
            if st is None:
                st = _take_unpaired(unpaired, m.get("name"))
            if st is None:
                continue
            txt = m.get("content")
            txt = txt if isinstance(txt, str) else json.dumps(txt)
            if m.get("is_error") or m.get("error") or (txt or "").lstrip().startswith(
                    ("Error", "error", "Traceback")):
                st.error = (txt or "error")[:80]
                errored = True
    return steps, stop_reason, errored


def _take_unpaired(unpaired: list, name: Optional[str]) -> Optional[Step]:
    """Oldest unpaired call matching `name`, else oldest overall."""
    for i, (pname, pstep) in enumerate(unpaired):
        if name is None or pname == name:
            unpaired.pop(i)
            return pstep
    if unpaired:
        return unpaired.pop(0)[1]
    return None


def load_autogen(path: str) -> list[Run]:
    runs: list[Run] = []
    for o in _iter_objects(path):
        msgs = o.get("messages") or o.get("chat_history") or []
        if not msgs and o.get("type") in ("ToolCallRequestEvent", "ToolCallExecutionEvent",
                                           "TextMessage", "ToolCallSummaryMessage"):
            msgs = [o]
        steps, stop_reason, errored = _autogen_steps_from_messages(
            msgs, str(o.get("stop_reason") or o.get("stopReason") or ""))
        if not steps:
            continue
        model = str(o.get("model") or "unknown")
        proj = str(o.get("project") or (o.get("name") or "autogen"))
        outcome = "error" if errored else ("stop" if stop_reason in ("stop", "completed", "success")
                                           else (stop_reason or "noToolUse"))
        runs.append(_run(steps, outcome, model, proj, path, ""))
    return runs


# --------------------------------------------------------------------------
# format 7: CrewAI crew output
# --------------------------------------------------------------------------
# CrewAI does not publish a stable machine-readable TRACE schema the way OTel
# does, so this loader is deliberately tolerant across the shapes seen in the
# wild: a top-level {"tasks_output": [...]} or {"tasks": [...]}, each task
# carrying an agent and one or more tool calls.
#
# CONFIDENCE NOTE: this is the least certain of the three. OTel is written to a
# published spec; AutoGen to a documented message schema; CrewAI to an inferred
# one. CrewAI users are the ones most likely to need `to_canonical`.
def _crewai_steps(task: dict) -> list[Step]:
    steps: list[Step] = []
    # a task may carry its calls under any of these keys
    for key in ("tool_calls", "tools_used", "steps", "actions"):
        for c in (task.get(key) or []):
            if isinstance(c, dict):
                name = c.get("tool") or c.get("tool_name") or c.get("name") or c.get("action")
                args = c.get("tool_input") or c.get("input") or c.get("arguments") \
                    or c.get("args") or c.get("tool_args")
                err = c.get("error")
                if name:
                    steps.append(_mk(str(name), args, str(err) if err else None))
            elif isinstance(c, str):
                steps.append(_mk(c, None))
    # a bare per-task tool field
    if not steps and (task.get("tool") or task.get("tool_name")):
        args = task.get("tool_input") or task.get("input") or task.get("arguments")
        steps.append(_mk(str(task.get("tool") or task.get("tool_name")), args))
    return steps


def load_crewai(path: str) -> list[Run]:
    runs: list[Run] = []
    for o in _iter_objects(path):
        tasks = o.get("tasks_output") or o.get("tasks") or []
        if isinstance(tasks, dict):
            tasks = list(tasks.values())
        steps: list[Step] = []
        errored = False
        for t in tasks:
            if not isinstance(t, dict):
                continue
            steps.extend(_crewai_steps(t))
            if t.get("error") or t.get("status") in ("failed", "error"):
                errored = True
        if not steps:
            continue
        model = str(o.get("model") or "unknown")
        proj = str(o.get("crew") or o.get("project") or "crewai")
        outcome = "error" if errored else str(o.get("outcome") or "stop")
        runs.append(_run(steps, outcome, model, proj, path, ""))
    return runs


# --------------------------------------------------------------------------
# detection and dispatch
# --------------------------------------------------------------------------
def detect_format(path: str) -> str:
    """Sniff the first JSON object. Falls back to counting structural markers."""
    scores = {f: 0 for f in FORMATS}
    seen = 0
    for o in _iter_objects(path):
        keys = set(o)
        # OTLP / OpenTelemetry GenAI -- resourceSpans is unambiguous
        if "resourceSpans" in keys or "scopeSpans" in keys or "instrumentationLibrarySpans" in keys:
            scores[OTEL] += 5
        # AutoGen typed events (v0.4) are unambiguous
        if o.get("type") in ("ToolCallRequestEvent", "ToolCallExecutionEvent"):
            scores[AUTOGEN] += 4
        # AutoGen v0.2/0.3 nests its markers INSIDE messages, so the top-level
        # key set cannot see them -- look one level down.
        msgs = o.get("messages") if isinstance(o.get("messages"), list) else []
        if "chat_history" in keys or "function_call" in keys or "stop_reason" in keys:
            scores[AUTOGEN] += 3
        for m in msgs[:20]:
            if not isinstance(m, dict):
                continue
            if "function_call" in m or m.get("type") in ("ToolCallRequestEvent",
                                                          "ToolCallExecutionEvent"):
                scores[AUTOGEN] += 3
                break
        # CrewAI crew output
        if "tasks_output" in keys or "final_output" in keys:
            scores[CREWAI] += 4
        # AutoGen v0.2/0.3 uses function_call; OpenAI uses tool_call_id
        if "tool_call_id" in keys:
            scores[OPENAI] += 3
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
           OPENAI: load_openai, LANGSMITH: load_langsmith,
           OTEL: load_otel_genai, AUTOGEN: load_autogen, CREWAI: load_crewai}


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
