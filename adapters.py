#!/usr/bin/env python3
"""
adapters.py — real agent trace adapter (pi session JSONL).

Reads the session transcripts written by the pi agent harness, which are JSONL
event streams:

    {"type":"session", "cwd": ..., "version": ...}
    {"type":"model_change", "modelId": ..., "provider": ...}
    {"type":"message", "message": {"role": "user"|"assistant"|"toolResult", ...}}

Assistant messages carry `toolCall` content blocks with an id, a tool name and
arguments; toolResult messages carry the matching `toolCallId`, `toolName` and
`isError`. That is everything needed to reconstruct a run.

A RUN is one user turn: the ordered tool calls between one user message and the
next. Its terminal outcome is the stopReason of the last assistant message, and
its live/transient status is decided by that outcome.

Nothing here is synthetic. Point `load_pi_runs` at ~/.pi/agent/sessions.
"""
from __future__ import annotations

import glob
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional

PI_SESSIONS = os.path.expanduser("~/.pi/agent/sessions")


# --------------------------------------------------------------------------
@dataclass
class Step:
    """One tool invocation, paired with its result."""
    tool: str
    args: dict
    error: Optional[str] = None

    @property
    def family(self) -> str:
        """Coarse tool family: mcp servers collapse to 'mcp'."""
        return "mcp" if self.tool.startswith("mcp") else self.tool


@dataclass
class Turn:
    """One agent run: a user turn and the tool calls it produced."""
    steps: list[Step]
    outcome: str                 # terminal stopReason of the last assistant msg
    model: str = "unknown"
    project: str = "unknown"
    cwd: str = ""
    session: str = ""
    prompt: str = ""             # normalised opening user text (the task)

    @property
    def succeeded(self) -> bool:
        """Terminal outcome is the success criterion: the model stopped on its
        own terms. `toolUse` (= never finished), `error`, `aborted` and `length`
        are all terminal failures."""
        return self.outcome == "stop"

    @property
    def tool_sequence(self) -> tuple:
        return tuple(s.tool for s in self.steps)

    @property
    def family_sequence(self) -> tuple:
        return tuple(s.family for s in self.steps)

    @property
    def family_multiset(self) -> tuple:
        return tuple(sorted(Counter(self.family_sequence).items()))

    @property
    def error_classes(self) -> tuple:
        return tuple(bool(s.error) for s in self.steps)


# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------
_WS = re.compile(r"\s+")


def arg_class(step: Step) -> Any:
    """Coarse argument class — what kind of thing was the tool pointed at."""
    a = step.args or {}
    t = step.tool
    if t == "bash":
        cmd = _WS.sub(" ", (a.get("command") or "")).strip()
        return (cmd.split(" ")[0] if cmd else "", "|" in cmd, ">" in cmd)
    if t in ("read", "write", "edit"):
        p = a.get("path") or a.get("file_path") or a.get("filePath") or ""
        return os.path.splitext(str(p))[1]
    if t.startswith("mcp"):
        return a.get("tool") or a.get("name") or t
    return t


def normalize_args(step: Step) -> Any:
    """Finest normalised argument form — stable across incidental whitespace."""
    a = step.args or {}
    t = step.tool
    if t == "bash":
        return _WS.sub(" ", (a.get("command") or "")).strip()[:160]
    if t in ("read", "write", "edit"):
        return str(a.get("path") or a.get("file_path") or a.get("filePath") or "")[:160]
    if t.startswith("mcp"):
        return f"{a.get('tool') or a.get('name') or t}:{str(a.get('args') or a.get('arguments') or '')[:80]}"
    return json.dumps(a, sort_keys=True)[:160]


# --------------------------------------------------------------------------
# loader
# --------------------------------------------------------------------------
def load_pi_session(path: str) -> list[Turn]:
    """Reconstruct every turn in one pi session file."""
    cwd = model = ""
    session_id = os.path.basename(path).split("_")[-1].replace(".jsonl", "")
    pending: dict[str, Step] = {}          # toolCallId -> Step
    steps: list[Step] = []
    best_outcome = ""
    cur_prompt = ""
    turns: list[Turn] = []
    started = False

    def flush():
        nonlocal steps, best_outcome
        if started and steps:
            turns.append(Turn(steps=steps, outcome=best_outcome or "noToolUse",
                              model=model, cwd=cwd,
                              project=os.path.basename(cwd.rstrip("/")) or cwd,
                              session=session_id, prompt=cur_prompt))
        steps, best_outcome = [], ""

    for line in open(path, errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        typ = d.get("type")
        if typ == "session":
            cwd = d.get("cwd", "")
        elif typ == "model_change":
            model = d.get("modelId", model)
        elif typ == "message":
            m = d.get("message", {})
            role = m.get("role")
            if role == "user":
                flush()
                cur_prompt = _WS.sub(" ", " ".join(
                    b.get("text", "") for b in (m.get("content") or [])
                    if isinstance(b, dict))).strip()[:120]
                started = True
            elif role == "assistant":
                # only the terminal stopReason of the turn matters
                if m.get("stopReason"):
                    best_outcome = m["stopReason"]
                for c in (m.get("content") or []):
                    if isinstance(c, dict) and c.get("type") == "toolCall":
                        st = Step(tool=c.get("name", "?"), args=c.get("arguments") or {})
                        steps.append(st)
                        pending[c.get("id")] = st
            elif role == "toolResult":
                st = pending.pop(m.get("toolCallId"), None)
                if st is not None and m.get("isError"):
                    # keep a short error class, not the whole payload
                    txt = " ".join(
                        b.get("text", "") for b in (m.get("content") or [])
                        if isinstance(b, dict)
                    )
                    st.error = _WS.sub(" ", txt).strip()[:80] or "error"
    flush()
    return turns


def load_pi_runs(
    root: str = PI_SESSIONS,
    projects: Optional[Iterable[str]] = None,
    models: Optional[Iterable[str]] = None,
) -> list[Turn]:
    """Load every (non-empty) turn under the pi sessions root, optionally
    filtered by project basename and/or model id."""
    projects = set(projects) if projects else None
    models = set(models) if models else None
    out: list[Turn] = []
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        for t in load_pi_session(path):
            if projects and t.project not in projects:
                continue
            if models and t.model not in models:
                continue
            out.append(t)
    return out


# --------------------------------------------------------------------------
# the tool-trace quotient tower
# --------------------------------------------------------------------------
def tool_tower():
    """Q1..Q6 for tool-using agent traces. Each level explicitly contains the
    previous one, so the refinement law is structural rather than accidental.

        Q1  terminal outcome
        Q2  + tool-family multiset
        Q3  + tool-family sequence
        Q4  + per-step error classes
        Q5  + normalised argument classes
        Q6  + full normalised trace
    """
    from quotient_tower import QuotientTower
    return QuotientTower([
        lambda h: h.outcome,
        lambda h: (h.outcome, h.family_multiset),
        lambda h: (h.outcome, h.family_multiset, h.family_sequence),
        lambda h: (h.outcome, h.family_multiset, h.family_sequence, h.error_classes),
        lambda h: (h.outcome, h.family_multiset, h.family_sequence, h.error_classes,
                   tuple(arg_class(s) for s in h.steps)),
        lambda h: (h.outcome, h.family_multiset, h.family_sequence, h.error_classes,
                   tuple(arg_class(s) for s in h.steps),
                   tuple((s.tool, normalize_args(s)) for s in h.steps)),
    ])


TOOL_LEVEL_NAMES = [
    "Q1  terminal outcome",
    "Q2  + tool multiset",
    "Q3  + tool sequence",
    "Q4  + error classes",
    "Q5  + arg classes",
    "Q6  + full trace",
]
