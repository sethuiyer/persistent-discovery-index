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
import re
import sqlite3
from typing import Any, Iterable, Iterator, Optional

from adapters import Evaluator, Step, Turn as Run, load_pi_session

CANONICAL, PI, OPENAI, LANGSMITH = "canonical", "pi", "openai", "langsmith"
OTEL, AUTOGEN, CREWAI = "otel", "autogen", "crewai"
CLAUDE, CODEX, OPENCODE, ANTIGRAVITY = "claude", "codex", "opencode", "antigravity"
FORMATS = (CANONICAL, PI, OPENAI, LANGSMITH, OTEL, AUTOGEN, CREWAI,
           CLAUDE, CODEX, OPENCODE, ANTIGRAVITY)


# --------------------------------------------------------------------------
# input warrants — what each loader's records actually support
#
# Parsing N steps does not mean two ecosystems are comparable. Every loader
# declares, per semantic, one of four states, and every analysis declares a
# minimum. The states are deliberately NOT collapsed:
#
#   SUPPORTED    recovered under a validated interpretation
#   INFERRED     reconstructed from an undocumented / reverse-engineered format
#   UNAVAILABLE  the source demonstrably cannot provide it
#   UNKNOWN      we have not established whether it can be recovered
#
# UNKNOWN and UNAVAILABLE are different claims: one is a gap in our knowledge,
# the other is a fact about the source.
# --------------------------------------------------------------------------
SUPPORTED, INFERRED, UNAVAILABLE, UNKNOWN = "supported", "inferred", "unavailable", "unknown"
CAP_RANK = {SUPPORTED: 3, INFERRED: 2, UNKNOWN: 1, UNAVAILABLE: 0}

SEMANTICS = ("steps", "run_boundaries", "task_identity", "tool_errors",
             "terminal_outcome", "cost", "tokens", "verified_outcome")


def _caps(**kw) -> dict:
    return {s: kw.get(s, UNAVAILABLE) for s in SEMANTICS}


# Values are set from what each loader actually populates, not from intent.
CAPABILITIES: dict[str, dict] = {
    CANONICAL: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                     tool_errors=SUPPORTED, terminal_outcome=SUPPORTED,
                     cost=SUPPORTED, tokens=SUPPORTED, verified_outcome=SUPPORTED),
    PI: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
              tool_errors=SUPPORTED, terminal_outcome=SUPPORTED),
    OPENAI: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                  terminal_outcome=SUPPORTED),
    LANGSMITH: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                     tool_errors=SUPPORTED, terminal_outcome=SUPPORTED),
    OTEL: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, tool_errors=SUPPORTED,
                terminal_outcome=SUPPORTED),
    AUTOGEN: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, tool_errors=SUPPORTED,
                   terminal_outcome=SUPPORTED),
    CREWAI: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, tool_errors=SUPPORTED,
                  terminal_outcome=SUPPORTED),
    CLAUDE: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                  tool_errors=SUPPORTED, terminal_outcome=INFERRED),
    CODEX: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                 tool_errors=INFERRED, terminal_outcome=UNKNOWN),
    OPENCODE: _caps(steps=SUPPORTED, run_boundaries=SUPPORTED, task_identity=SUPPORTED,
                    tool_errors=SUPPORTED, terminal_outcome=UNKNOWN,
                    cost=SUPPORTED, tokens=SUPPORTED),
    ANTIGRAVITY: _caps(steps=INFERRED),
}

ANALYSIS_REQUIREMENTS: dict[str, dict] = {
    "steps_only": {
        "requires": {"steps": INFERRED},
        "message": "No step-level claim is warranted for this capture."},
    "run_profile": {
        "requires": {"steps": SUPPORTED, "run_boundaries": SUPPORTED},
        "message": "No run-level claim is warranted for this capture."},
    "agent_comparison": {
        "requires": {"steps": SUPPORTED, "run_boundaries": SUPPORTED,
                     "task_identity": SUPPORTED},
        "message": "No agent-comparison claim is warranted for this capture."},
    "o4b_cost": {
        "requires": {"steps": SUPPORTED, "run_boundaries": SUPPORTED,
                     "task_identity": SUPPORTED, "verified_outcome": SUPPORTED,
                     "cost": SUPPORTED},
        "message": "No O4b cost claim is warranted for this capture."},
    "o4b_behavioral": {
        "requires": {"steps": SUPPORTED, "run_boundaries": SUPPORTED,
                     "task_identity": SUPPORTED, "verified_outcome": SUPPORTED,
                     "tool_errors": SUPPORTED},
        "message": "No O4b behavioural claim is warranted for this capture."},
}


class CapabilityError(ValueError):
    """The input does not warrant the requested analysis."""


def capabilities_of(fmt: str) -> dict:
    return dict(CAPABILITIES.get(fmt, _caps()))


def reconcile_capabilities(fmts) -> dict:
    """The meet (weakest state per semantic) across the source formats."""
    fmts = list(fmts)
    if not fmts:
        return _caps()
    return {s: min((capabilities_of(f)[s] for f in fmts), key=lambda st: CAP_RANK[st])
            for s in SEMANTICS}


def require_capabilities(fmts, analysis: str) -> dict:
    """Raise CapabilityError unless the input warrants `analysis`. Returns the
    effective capabilities when it passes."""
    if analysis not in ANALYSIS_REQUIREMENTS:
        raise KeyError(f"unknown analysis {analysis!r}; known: {sorted(ANALYSIS_REQUIREMENTS)}")
    spec = ANALYSIS_REQUIREMENTS[analysis]
    have = reconcile_capabilities(fmts if isinstance(fmts, (list, tuple, set)) else [fmts])
    if any(CAP_RANK[have[s]] < CAP_RANK[need] for s, need in spec["requires"].items()):
        req = "\n".join(f"  {s:<15} >= {need}" for s, need in spec["requires"].items())
        got = "\n".join(f"  {s:<15} = {have[s]}" for s in spec["requires"])
        raise CapabilityError(
            f"Analysis refused: {analysis}.\n\nRequires:\n{req}\n\n"
            f"Input:\n{got}\n\n{spec['message']}")
    return have


def capability_table() -> str:
    """The machine-readable matrix, rendered."""
    head = f"{'format':<12} " + " ".join(f"{s[:9]:>9}" for s in SEMANTICS)
    rows = [head, "-" * len(head)]
    for f in FORMATS:
        c = capabilities_of(f)
        rows.append(f"{f:<12} " + " ".join(f"{c[s][:9]:>9}" for s in SEMANTICS))
    return "\n".join(rows)


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


def _run(steps, outcome, model="unknown", project="unknown", path="", prompt="",
         verified_outcome=None, evaluator=None, cost=None,
         tokens_input=None, tokens_output=None):
    return Run(steps=list(steps), outcome=outcome or "unknown", model=model or "unknown",
               project=project or "unknown",
               session=os.path.basename(path), prompt=prompt, cwd=project or "",
               verified_outcome=verified_outcome, evaluator=evaluator,
               cost=cost, tokens_input=tokens_input, tokens_output=tokens_output)


def _evaluator(x):
    """Parse an evaluator provenance field from canonical JSON."""
    if x is None:
        return None
    if isinstance(x, str):
        return Evaluator(id=x)
    if isinstance(x, dict):
        return Evaluator(id=str(x.get("id", "")), version=str(x.get("version", "")),
                         method=str(x.get("method", "")))
    raise ValueError(f"evaluator must be a string or object, got {type(x).__name__}")


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
                        path, o.get("prompt", ""),
                        verified_outcome=o.get("verified_outcome"),
                        evaluator=_evaluator(o.get("evaluator")),
                        cost=o.get("cost"), tokens_input=o.get("tokens_input"),
                        tokens_output=o.get("tokens_output")))
    return out


def to_canonical(run: Run) -> dict:
    """Emit the canonical form — so any tool can write what PDI reads."""
    d = {
        "model": run.model, "project": run.project, "prompt": run.prompt,
        "outcome": run.outcome,
        "steps": [{"tool": s.tool, "args": s.args, "error": s.error} for s in run.steps],
    }
    if run.verified_outcome is not None:
        d["verified_outcome"] = run.verified_outcome
    if run.evaluator is not None:
        d["evaluator"] = {"id": run.evaluator.id, "version": run.evaluator.version,
                          "method": run.evaluator.method}
    if run.cost is not None:
        d["cost"] = run.cost
    if run.tokens_input is not None:
        d["tokens_input"] = run.tokens_input
    if run.tokens_output is not None:
        d["tokens_output"] = run.tokens_output
    return d


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
# CLI agent formats: Claude Code, Codex, OpenCode, Antigravity
#
# Confidence, stated honestly (the repo's convention):
#   claude      -- written to a LIVE CAPTURE (the author's on-disk sessions)
#   codex       -- LIVE CAPTURE; `custom_tool_call.input` wraps JSON in a
#                  snippet, so the object is extracted by brace matching
#   opencode    -- LIVE CAPTURE; SQLite `part.data` is documented JSON
#   antigravity -- INFERRED, lowest confidence: SQLite with protobuf blobs and
#                  no public schema. Tool calls are recovered by scanning
#                  length-delimited fields (call_id, tool, JSON args). Run
#                  boundaries are NOT recoverable, so a conversation is one run.
# --------------------------------------------------------------------------
CLAUDE_TOOL_ALIASES = {
    "Bash": "bash", "Read": "read", "Edit": "edit", "MultiEdit": "edit",
    "Write": "write", "NotebookEdit": "edit", "Glob": "glob", "Grep": "grep",
    "Task": "task", "TodoWrite": "todo", "WebFetch": "webfetch",
    "WebSearch": "websearch", "BashOutput": "bash",
}


def _text_of(content) -> str:
    """Flatten a message content field (str, or a list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if isinstance(b.get("text"), str):
                    parts.append(b["text"])
        return "\n".join(parts)
    return ""


def _clean_prompt(s: str, cap: int = 500) -> str:
    return " ".join((s or "").split())[:cap]


def _claude_is_meta(text: str) -> bool:
    """Claude Code injects bookkeeping as `user` records (slash-command names and
    output, the local-command caveat). They are not user turns."""
    t = (text or "").lstrip()
    return (t.startswith("<command-name>") or t.startswith("<local-command-stdout>")
            or t.startswith("<local-command-caveat>")
            or t.startswith("Caveat: The messages below were generated"))


def load_claude(path: str) -> list[Run]:
    """Claude Code transcript JSONL (`~/.claude/projects/*/*.jsonl`).

    A run is one real user prompt: a `user` record that is NOT a pure carrier of
    `tool_result` blocks. Subagent sidechains (`isSidechain`) are skipped.
    """
    out: list[Run] = []
    steps: list[Step] = []
    by_id: dict = {}
    prompt = ""
    session = os.path.basename(path).replace(".jsonl", "")
    project = ""
    started = False
    last_text = False

    def flush(outcome: str) -> None:
        nonlocal steps, by_id, prompt, started, last_text
        if started:
            out.append(Run(steps=steps, outcome=outcome, model="claude",
                           project=project or "claude", session=session, prompt=prompt))
        steps, by_id, prompt, started, last_text = [], {}, "", False, False

    for o in _iter_objects(path):
        if o.get("isSidechain"):
            continue
        session = o.get("sessionId") or session
        project = o.get("cwd") or project
        t = o.get("type")
        msg = o.get("message")
        if t == "assistant" and isinstance(msg, dict):
            blocks = msg.get("content") if isinstance(msg.get("content"), list) else []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    args = b.get("input") if isinstance(b.get("input"), dict) else {"raw": b.get("input")}
                    tool = CLAUDE_TOOL_ALIASES.get(b.get("name"), str(b.get("name") or "?").lower())
                    s = Step(tool=tool, args=args)
                    steps.append(s)
                    started = True
                    last_text = False
                    if b.get("id"):
                        by_id[b.get("id")] = s
                elif b.get("type") == "text":
                    started = True
                    last_text = True
        elif t == "user" and isinstance(msg, dict):
            blocks = msg.get("content")
            is_tool_result = (isinstance(blocks, list) and blocks and
                              all(isinstance(b, dict) and b.get("type") == "tool_result"
                                  for b in blocks))
            if is_tool_result:
                for b in blocks:
                    s = by_id.get(b.get("tool_use_id"))
                    if s is not None and b.get("is_error"):
                        s.error = _text_of(b.get("content"))[:200] or "error"
            else:
                text = _text_of(blocks)
                if _claude_is_meta(text):
                    continue
                if started:
                    flush("stop" if last_text else "toolUse")
                if text.strip():
                    prompt = _clean_prompt(text)
                started = True
    if started:
        flush("stop" if last_text else "toolUse")
    return out


def _codex_args(pl: dict) -> dict:
    raw = pl.get("arguments") if pl.get("arguments") is not None else pl.get("input")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            pass
        i = raw.find("{")            # custom_tool_call wraps JSON in a snippet
        if i >= 0:
            depth = 0
            for j in range(i, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(raw[i:j + 1])
                        except Exception:
                            break
        return {"raw": raw}
    return {}


def load_codex(path: str) -> list[Run]:
    """Codex rollout JSONL (`~/.codex/sessions/*/*/*/rollout-*.jsonl`)."""
    out: list[Run] = []
    steps: list[Step] = []
    by_id: dict = {}
    prompt = ""
    session = os.path.basename(path)
    project = ""
    started = False

    def flush() -> None:
        nonlocal steps, by_id, prompt, started
        if started:
            out.append(Run(steps=steps, outcome="unknown", model="codex",
                           project=project or "codex", session=session, prompt=prompt))
        steps, by_id, prompt, started = [], {}, "", False

    for o in _iter_objects(path):
        t = o.get("type")
        pl = o.get("payload") if isinstance(o.get("payload"), dict) else {}
        if t == "session_meta":
            session = pl.get("id") or pl.get("session_id") or session
            project = pl.get("cwd") or project
        elif t == "response_item":
            pt = pl.get("type")
            if pt == "message":
                role = pl.get("role")
                if role == "user":
                    if started:
                        flush()
                    prompt = _clean_prompt(_text_of(pl.get("content")))
                    started = True
                elif role == "assistant":
                    started = True
            elif pt in ("custom_tool_call", "function_call", "local_shell_call"):
                s = Step(tool=str(pl.get("name") or pt), args=_codex_args(pl))
                steps.append(s)
                started = True
                if pl.get("call_id"):
                    by_id[pl["call_id"]] = s
            elif pt in ("custom_tool_call_output", "function_call_output"):
                s = by_id.get(pl.get("call_id"))
                txt = _text_of(pl.get("output")) or str(pl.get("output") or "")
                if (s is not None and "completed" not in txt.lower()
                        and re.search(r"\b(error|failed|exception)\b", txt, re.I)):
                    s.error = txt[:200]
    if started:
        flush()
    return out


def load_opencode(path: str) -> list[Run]:
    """OpenCode SQLite store (`~/.local/share/opencode/opencode.db`).

    `part.data` is JSON; a `tool` part carries {tool, state:{input,output,status}}.
    Per-message `cost` / `tokens` are summed onto the run they belong to, so the
    capability claim (cost + tokens supported) is actually carried by the data.
    """
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        meta: dict = {}
        for mid, data in con.execute("select id, data from message"):
            try:
                d = json.loads(data)
            except Exception:
                d = {}
            toks = d.get("tokens") if isinstance(d.get("tokens"), dict) else {}
            meta[mid] = {"role": d.get("role"), "cost": d.get("cost"),
                         "tin": toks.get("input"), "tout": toks.get("output")}
        out: list[Run] = []
        for sid, model in con.execute("select id, model from session"):
            steps: list[Step] = []
            prompt = ""
            started = False
            msgs: list[str] = []

            def flush() -> None:
                nonlocal steps, prompt, started, msgs
                if not started:
                    return
                costs = [meta[m]["cost"] for m in msgs if meta.get(m, {}).get("cost") is not None]
                tins = [meta[m]["tin"] for m in msgs if meta.get(m, {}).get("tin") is not None]
                touts = [meta[m]["tout"] for m in msgs if meta.get(m, {}).get("tout") is not None]
                out.append(Run(steps=steps, outcome="unknown", model=str(model or "opencode"),
                               project="opencode", session=str(sid), prompt=prompt,
                               cost=(sum(costs) if costs else None),
                               tokens_input=(sum(tins) if tins else None),
                               tokens_output=(sum(touts) if touts else None)))
                steps, prompt, started, msgs = [], "", False, []

            for mid, data in con.execute(
                    "select message_id, data from part where session_id=? order by time_created, id",
                    (sid,)):
                try:
                    d = json.loads(data)
                except Exception:
                    continue
                ptype = d.get("type")
                if ptype == "text" and meta.get(mid, {}).get("role") == "user":
                    if started:
                        flush()
                    prompt = _clean_prompt(d.get("text") or "")
                    msgs = [mid]
                    started = True
                    continue
                if started and mid not in msgs:
                    msgs.append(mid)
                if ptype == "tool":
                    if mid not in msgs:
                        msgs.append(mid)
                    st = d.get("state") if isinstance(d.get("state"), dict) else {}
                    err = str(st.get("output") or "error")[:200] if st.get("status") == "error" else None
                    steps.append(Step(tool=str(d.get("tool") or "?"),
                                      args=st.get("input") if isinstance(st.get("input"), dict) else {},
                                      error=err))
                    started = True
            flush()
        return out
    finally:
        con.close()


def _pb_varint(b: bytes, i: int):
    shift = val = 0
    while i < len(b):
        x = b[i]; i += 1
        val |= (x & 0x7F) << shift
        if not (x & 0x80):
            break
        shift += 7
    return val, i


def _pb_fields(b: bytes):
    i = 0
    while i < len(b):
        tag, i = _pb_varint(b, i)
        if tag == 0:
            break
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            _, i = _pb_varint(b, i)
            yield fn, wt, None
        elif wt == 2:
            ln, i = _pb_varint(b, i)
            yield fn, wt, b[i:i + ln]; i += ln
        elif wt == 5:
            yield fn, wt, b[i:i + 4]; i += 4
        elif wt == 1:
            yield fn, wt, b[i:i + 8]; i += 8
        else:
            break


def _pb_texts(b: bytes, out: list, depth: int = 0) -> None:
    for _fn, wt, val in _pb_fields(b):
        if wt == 2 and val:
            if len(val) > 1 and all(32 <= c < 127 for c in val):
                out.append(val.decode("ascii"))
            elif depth < 6:
                _pb_texts(val, out, depth + 1)


def _antigravity_steps(payload: bytes) -> list[Step]:
    texts: list[str] = []
    _pb_texts(payload, texts)
    steps: list[Step] = []
    for i in range(len(texts) - 2):
        if texts[i].startswith("call_"):
            tool, args = texts[i + 1], texts[i + 2]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tool) and args.startswith("{"):
                try:
                    a = json.loads(args)
                except Exception:
                    a = {"raw": args}
                steps.append(Step(tool=tool, args=a if isinstance(a, dict) else {"raw": args}))
    return steps


def load_antigravity(path: str) -> list[Run]:
    """Antigravity SQLite store (INFERRED; see the banner above).

    Tool calls are recovered from protobuf blobs heuristically; run boundaries
    are not recoverable, so one conversation yields one run with no prompt.
    """
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        steps: list[Step] = []
        for _idx, payload in con.execute("select idx, step_payload from steps order by idx"):
            if isinstance(payload, (bytes, bytearray)):
                steps.extend(_antigravity_steps(bytes(payload)))
        if not steps:
            return []
        return [Run(steps=steps, outcome="unknown", model="antigravity", project="antigravity",
                    session=os.path.basename(path).replace(".db", ""), prompt="")]
    finally:
        con.close()


# --------------------------------------------------------------------------
# detection and dispatch
# --------------------------------------------------------------------------
def _sqlite_kind(path: str):
    """Classify a SQLite file by its tables (OpenCode vs Antigravity)."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tabs = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        con.close()
    except Exception:
        return None
    if {"part", "session"} <= tabs:
        return OPENCODE
    if "steps" in tabs:
        return ANTIGRAVITY
    return None


def detect_format(path: str) -> str:
    """Sniff the file. SQLite by magic bytes; JSON by structural markers."""
    try:
        with open(path, "rb") as _f:
            magic = _f.read(16)
    except OSError:
        magic = b""
    if magic.startswith(b"SQLite format 3"):
        return _sqlite_kind(path) or CANONICAL
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
        if ({"type", "message"} <= keys or o.get("type") in ("session", "message", "model_change")) \
                and "parentUuid" not in keys:
            scores[PI] += 3
        # Claude Code transcript records carry uuid / parentUuid / sessionId
        if "parentUuid" in keys or "isSidechain" in keys:
            scores[CLAUDE] += 5
        # Codex rollout records
        if o.get("type") in ("session_meta", "response_item", "event_msg", "turn_context"):
            scores[CODEX] += 5
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
           OTEL: load_otel_genai, AUTOGEN: load_autogen, CREWAI: load_crewai,
           CLAUDE: load_claude, CODEX: load_codex,
           OPENCODE: load_opencode, ANTIGRAVITY: load_antigravity}


def load_any(path: str, fmt: Optional[str] = None) -> list[Run]:
    fmt = fmt or detect_format(path)
    return LOADERS.get(fmt, load_canonical)(path)


def load_paths(paths: Iterable[str], fmt: Optional[str] = None) -> list[Run]:
    """Accept files or directories; walk directories for *.jsonl / *.json / *.db."""
    out: list[Run] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith((".jsonl", ".json", ".db")):
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


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) == 1 or "--capabilities" in _sys.argv:
        print(capability_table())
    else:
        print("usage: python3 ingest.py [--capabilities]")
