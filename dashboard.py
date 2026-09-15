#!/usr/bin/env python3
"""
dashboard.py — a self-contained, interpretable dashboard over a trace corpus.

    python3 dashboard.py traces/                     # autodetect, write dashboard.html
    python3 dashboard.py traces/ --group-by model --out report.html
    python3 dashboard.py --demo                      # synthetic, no data needed

WHAT "INTERPRETABLE" MEANS HERE
-------------------------------
Not "has charts". Every panel states, on the page, what its own numbers are
licensed to claim — the same discipline SPINE.md applies to the ledger, applied
at the point of reading. A reader who opens only this file must not be able to
take a stronger reading than the corpus supports. Concretely:

  * a page-level WARRANT banner, always visible;
  * D and S carry their `_shallow` flag as a badge, because a window sup attained
    inside the horizon is not a rate (§3, §16.2);
  * the asymptotic layer prints the tail status and the *hypothesis-carrying*
    bound label verbatim from agent_profiler.asymptotic (§17.3);
  * the comparison panel says "paired on this corpus only", because no
    population reference distribution exists yet — the regression is that no
    absolute good/bad claim is made anywhere;
  * the finite-scale layer (exact: counts, yield, onset) is visually separated
    from the asymptotic layer (status-bearing: D, S, Δ), because conflating them
    is the estimator defect v0.4.1 was written to fix.

Output is ONE HTML file with inline CSS and inline SVG. No JavaScript, no CDN,
no fonts, no telemetry. It renders offline, from a file:// URL, forever.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter, defaultdict

from adapters import TOOL_LEVEL_NAMES, tool_tower
from agent_profiler import AgentProfiler, asymptotic
from ingest import FORMATS, detect_format, load_paths
from pdi import PDI
from quotient_tower import prefix_tower

# imported from the CLI module so the dashboard and the text profiler can never
# disagree about what a run is, what the demo is, or what a tower is.
from pdi_profile import build_tower, demo_runs, ingest, summarize

WARRANT_BANNER = [
    "Descriptive of THIS corpus. Not a statement about agents in general.",
    "No reference distribution exists: D has no good/bad threshold. "
    "Compare agents to each other on the same tasks, not to a norm.",
    "\u0394 (Delta) is presentation-dependent. Differences are meaningful "
    "between presentations of the SAME task, not across tasks.",
    "A value badged SHALLOW is a window sup, not a rate. It is the levelwise "
    "maximum over the observed horizon and nothing more.",
]

CSS = """
:root{--bg:#0f1115;--panel:#171a21;--ink:#e6e8ee;--dim:#9aa3b2;--line:#2a2f3a;
--live:#3fb950;--explored:#3b4252;--warn:#d29922;--bad:#f85149;--accent:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:19px;margin:0 0 2px} h2{font-size:15px;margin:30px 0 10px;
border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:13px;margin:18px 0 8px;color:var(--dim);font-weight:600}
.sub{color:var(--dim);font-size:12px;margin:0 0 18px}
.warrant{background:#12161d;border:1px solid var(--line);border-left:3px solid var(--accent);
padding:12px 16px;border-radius:6px;margin:16px 0 22px}
.warrant b{color:var(--accent)} .warrant ul{margin:8px 0 0;padding-left:18px}
.warrant li{color:var(--dim);margin:3px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:999px;
padding:3px 11px;font-size:12px;color:var(--dim)}
.chip b{color:var(--ink);font-weight:600}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
padding:14px 16px;margin:10px 0}
.metric{display:flex;gap:12px;flex-wrap:wrap}
.metric .card{flex:1 1 200px;margin:0}
.v{font-size:24px;font-weight:700;letter-spacing:-.5px}
.v.d{color:var(--live)} .v.s{color:var(--accent)} .v.x{color:var(--warn)}
.k{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim)}
.why{color:var(--dim);font-size:12px;margin-top:8px;border-top:1px dashed var(--line);
padding-top:8px}
.badge{display:inline-block;font-size:10px;padding:1px 7px;border-radius:4px;
border:1px solid var(--line);color:var(--dim);vertical-align:middle;margin-left:6px}
.badge.warn{color:var(--warn);border-color:#4a3a12;background:#1f1a0d}
.badge.ok{color:var(--live);border-color:#17381c;background:#0d1a10}
.badge.none{color:var(--bad);border-color:#4a1d1a;background:#1f0f0e}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{text-align:right;padding:6px 10px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase;
letter-spacing:.05em}
tr.ref td{color:var(--dim)} td.hot{color:var(--warn);font-weight:700}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--dim);font-size:12px;margin:6px 0 0}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;
vertical-align:middle}
.layer{border-left:3px solid var(--line);padding-left:14px;margin:14px 0}
.layer.finite{border-color:var(--live)} .layer.asym{border-color:var(--warn)}
.note{color:var(--dim);font-size:12px} footer{margin-top:36px;color:var(--dim);
font-size:11.5px;border-top:1px solid var(--line);padding-top:14px}
code{background:#12161d;border:1px solid var(--line);padding:1px 5px;border-radius:4px;
font-size:12px}
.fig{margin:8px 0 4px}
"""


# --------------------------------------------------------------------------
# SVG primitives (server-rendered: no JavaScript anywhere)
# --------------------------------------------------------------------------
def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def svg_tower(rows: list[dict], width: int = 1120, height: int = 300) -> str:
    """Grouped bars: n_j (explored) vs L_j (live), log-scaled so a 23,232x
    spread stays readable. Counts printed above every bar — the bar is a shape,
    the label is the datum."""
    if not rows:
        return '<p class="note">no levels observed.</p>'
    pad_l, pad_b, pad_t = 46, 34, 26
    plot_w = width - pad_l - 14
    plot_h = height - pad_b - pad_t
    bw = plot_w / (len(rows) * 3.0)
    maxv = max(max(r["n"], r["L"], 1) for r in rows)

    def y(v: int) -> float:
        if v <= 0:
            return pad_t + plot_h
        # log2(1+v) keeps 0..23232 legible without a second axis
        return pad_t + plot_h * (1 - (v.bit_length() - (v - 1).bit_length() * 0 if v else 0)
                                 if False else 1 - (_lg(v) / _lg(maxv)))

    p = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
         f'aria-label="explored vs live classes per resolution level">']
    for gy in (0, .25, .5, .75, 1.0):
        yy = pad_t + plot_h * (1 - gy)
        val = int(round(maxv ** gy))
        p.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-8}" y2="{yy:.1f}" '
                 f'stroke="#2a2f3a" stroke-width="1"/>')
        p.append(f'<text x="{pad_l-8}" y="{yy+4:.1f}" fill="#9aa3b2" font-size="10" '
                 f'text-anchor="end">{val}</text>')
    for i, r in enumerate(rows):
        cx = pad_l + plot_w * (i + .5) / len(rows)
        for off, key, col in ((-1, "n", "#3b4252"), (1, "L", "#3fb950")):
            v = r[key]
            x = cx + off * bw * .55 - bw * .5
            h = pad_t + plot_h - y(v)
            p.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw*.92:.1f}" '
                     f'height="{max(h,0):.1f}" fill="{col}" rx="2"><title>'
                     f'level {r["level"]}  {key}={v}</title></rect>')
            p.append(f'<text x="{x+bw*.46:.1f}" y="{y(v)-5:.1f}" fill="#9aa3b2" '
                     f'font-size="9.5" text-anchor="middle">{v}</text>')
        p.append(f'<text x="{cx:.1f}" y="{height-12}" fill="#9aa3b2" font-size="11" '
                 f'text-anchor="middle">Q{r["level"]}</text>')
    p.append("</svg>")
    return "".join(p)


def _lg(v: int) -> float:
    import math
    return math.log2(1 + v)


def svg_yield(rows: list[dict], onset: int | None, width: int = 1120, height: int = 170) -> str:
    """Persistent yield per level, with the 10% onset line drawn in."""
    if not rows:
        return ""
    pad_l, pad_b, pad_t = 46, 30, 14
    plot_w, plot_h = width - pad_l - 14, height - pad_b - pad_t
    xs = [pad_l + plot_w * (i + .5) / len(rows) for i in range(len(rows))]

    def y(v: float) -> float:
        return pad_t + plot_h * (1 - v)

    p = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
         f'aria-label="persistent yield per resolution level">']
    for gv, lab in ((0.0, "0%"), (.5, "50%"), (1.0, "100%")):
        p.append(f'<line x1="{pad_l}" y1="{y(gv):.1f}" x2="{width-8}" y2="{y(gv):.1f}" '
                 f'stroke="#2a2f3a"/>')
        p.append(f'<text x="{pad_l-8}" y="{y(gv)+4:.1f}" fill="#9aa3b2" font-size="10" '
                 f'text-anchor="end">{lab}</text>')
    # 10% onset threshold
    p.append(f'<line x1="{pad_l}" y1="{y(.10):.1f}" x2="{width-8}" y2="{y(.10):.1f}" '
             f'stroke="#d29922" stroke-dasharray="4 4"/>')
    p.append(f'<text x="{width-10}" y="{y(.10)-5:.1f}" fill="#d29922" font-size="10" '
             f'text-anchor="end">stop threshold 10%</text>')
    pts = " ".join(f"{xs[i]:.1f},{y(r['yield']):.1f}" for i, r in enumerate(rows))
    p.append(f'<polyline points="{pts}" fill="none" stroke="#58a6ff" stroke-width="2"/>')
    for i, r in enumerate(rows):
        col = "#d29922" if onset == r["level"] else "#58a6ff"
        p.append(f'<circle cx="{xs[i]:.1f}" cy="{y(r["yield"]):.1f}" r="3.4" fill="{col}">'
                 f'<title>Q{r["level"]}: yield {r["yield"]*100:.1f}%</title></circle>')
        p.append(f'<text x="{xs[i]:.1f}" y="{height-9}" fill="#9aa3b2" font-size="10" '
                 f'text-anchor="middle">Q{r["level"]}</text>')
        if onset == r["level"]:
            p.append(f'<text x="{xs[i]:.1f}" y="{y(r["yield"])-9:.1f}" fill="#d29922" '
                     f'font-size="10.5" text-anchor="middle">j*</text>')
    p.append("</svg>")
    return "".join(p)


def svg_exponents(s_seq: dict, d_seq: dict, width: int = 1120, height: int = 170) -> str:
    """Per-level exponents log2(count)/j: S (explored) vs D (live).
    The shaded gap is Delta made visible level by level — NOT an area claim."""
    js = sorted(set(s_seq) | set(d_seq))
    if not js:
        return ""
    pad_l, pad_b, pad_t = 46, 30, 14
    plot_w, plot_h = width - pad_l - 14, height - pad_b - pad_t
    hi = max([s_seq.get(j, 0) for j in js] + [d_seq.get(j, 0) for j in js] + [.5])
    xs = {j: pad_l + plot_w * (i + .5) / len(js) for i, j in enumerate(js)}

    def y(v: float) -> float:
        return pad_t + plot_h * (1 - v / hi)

    p = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
         f'aria-label="levelwise exponents: exploration S and persistent D">']
    p.append(f'<line x1="{pad_l}" y1="{pad_t+plot_h:.1f}" x2="{width-8}" '
             f'y2="{pad_t+plot_h:.1f}" stroke="#2a2f3a"/>')
    p.append(f'<text x="{pad_l-8}" y="{pad_t+4:.1f}" fill="#9aa3b2" font-size="10" '
             f'text-anchor="end">{hi:.2f}</text>')
    for key, col in (("s", "#58a6ff"), ("d", "#3fb950")):
        seq = s_seq if key == "s" else d_seq
        pts = [(xs[j], y(seq[j])) for j in js if j in seq]
        if len(pts) > 1:
            p.append('<polyline points="' +
                     " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
                     f'" fill="none" stroke="{col}" stroke-width="2"/>')
        for a, b in pts:
            p.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{col}"/>')
    for j in js:
        p.append(f'<text x="{xs[j]:.1f}" y="{height-9}" fill="#9aa3b2" font-size="10" '
                 f'text-anchor="middle">Q{j}</text>')
    p.append("</svg>")
    return "".join(p)


# --------------------------------------------------------------------------
def badge(profile_shallow: bool, at: int, horizon: int) -> str:
    if profile_shallow:
        return ('<span class="badge warn">SHALLOW \u2014 not a rate</span>')
    return f'<span class="badge ok">attained at Q{at}</span>'


def metric_cards(prof: dict) -> str:
    H = prof["horizon"]
    d_at, s_at = prof["D_at"], prof["S_at"]
    return f"""<div class="metric">
  <div class="card">
    <div class="k">D \u2014 persistent complexity (task)</div>
    <div class="v d">{prof['D']:.4f}</div>
    {badge(prof['D_shallow'], d_at, H)}
    <div class="why">Window sup at Q{d_at} of {H}. Cofinal-invariant as a quantity (\u00a72.3);
    the printed finite-window number is not \u2014 it moves under reindexing (\u00a716.2).
    Reads as: how much structure the task has.</div>
  </div>
  <div class="card">
    <div class="k">S \u2014 exploration complexity (algorithm)</div>
    <div class="v s">{prof['S']:.4f}</div>
    {badge(prof['S_shallow'], s_at, H)}
    <div class="why">Presentation-dependent by construction. Reads as: how much structure
    this algorithm walked through to get there.</div>
  </div>
  <div class="card">
    <div class="k">\u0394 = S \u2212 D \u2014 discovery overhead</div>
    <div class="v x">{prof['delta']:.4f}</div>
    <div class="why">\u0394 is NOT cofinal-invariant (\u00a72.4). It is a legitimate
    <i>algorithm</i> comparison only when the task is held fixed. Never compare \u0394
    across tasks.</div>
  </div>
</div>"""


def asymptotic_block(prof: dict) -> str:
    a = asymptotic(prof)
    out = []
    for name, key, meaning in (("S", "S", "exploration"), ("D", "D", "persistent")):
        st = a[key]
        cls = {"STABLE": "ok", "NONE": "none"}.get(st["status"], "warn")
        out.append(
            f'<tr><td>{name} <span class="note">({meaning})</span></td>'
            f'<td>{st["value"]:.6f}</td>'
            f'<td><span class="badge {cls}">{_esc(st["status"])}</span></td>'
            f'<td>{_esc(st["bound"])}</td>'
            f'<td>{st["window_sup"]:.6f}</td>'
            f'<td class="note">{_esc(", ".join(f"{v:.3f}" for v in st["tail"]))}</td></tr>')
    return f"""<div class="layer asym">
  <h3>Asymptotic layer \u2014 status-bearing, NOT a finite window sup</h3>
  <table><thead><tr><th>quantity</th><th>tail estimate</th><th>status</th>
  <th>what the label licenses</th><th>window sup</th><th>last {a['k']} levels</th>
  </tr></thead><tbody>{''.join(out)}</tbody></table>
  <p class="note">No finite prefix determines a limsup (\u00a717.2). STABLE means the tail is
  flat so far; TRENDING_* means the value is a bound <i>only if the tail stays monotone</i>;
  UNRESOLVED means the asymptotic layer is unavailable at this horizon \u2014 a legitimate
  result, not a failure. The finite-scale layer below is the exact one.</p>
</div>"""


def inflation_panel(agents: dict, profiles: dict) -> str:
    """Paired comparison on the corpus. The one strong reading the data supports
    today: differences between agents on the same tasks, with no population norm."""
    if len(agents) < 2:
        return ""
    ref = min(agents, key=lambda m: profiles[m]["S"])
    levels = [r["level"] for r in profiles[ref]["rows"]]
    refn = {r["level"]: r["n"] for r in profiles[ref]["rows"]}
    out = []
    for name in agents:
        rows = {r["level"]: r["n"] for r in profiles[name]["rows"]}
        cells = []
        for j in levels:
            base = refn.get(j, 0)
            if not base:
                cells.append('<td class="note">\u2013</td>')
            else:
                v = rows.get(j, 0) / base
                cls = ' class="hot"' if v >= 2 else ""
                cells.append(f"<td{cls}>{v:.2f}\u00d7</td>")
        mark = " (reference)" if name == ref else ""
        out.append(f'<tr><td>{_esc(name)}{mark}</td>{"".join(cells)}</tr>')
    head = "".join(f"<th>Q{j}</th>" for j in levels)
    return f"""<h2>Paired comparison \u2014 inflation n_j / n_j(reference)</h2>
<div class="layer finite">
  <table><thead><tr><th>agent</th>{head}</tr></thead><tbody>{''.join(out)}</tbody></table>
  <p class="note">Reference = <b>{_esc(ref)}</b>, the group with the lowest window S.
  This is the strongest claim the current corpus supports: <b>paired, on these tasks
  only</b>. Cells \u2265 2\u00d7 are highlighted. Where an agent manufactures distinctions
  that the reference does not is where its exploration stops being useful \u2014 a
  <i>relative</i> statement. There is still no reference distribution, so no cell here
  says any agent is good or bad in absolute terms.</p>
</div>"""


def group_section(name: str, prof: dict) -> str:
    rows = prof["rows"]
    onset = next((r["level"] for r in rows if r["yield"] < 0.10), None)
    onset_txt = (f"Q{onset}" if onset is not None else
                 "none \u2014 yield never fell below 10% on this corpus")
    return f"""<h2>{_esc(name)}</h2>
<div class="chips">
  <span class="chip">runs <b>{prof['runs']}</b></span>
  <span class="chip">succeeded <b>{prof['successes']}</b>
    ({prof['successes']/max(prof['runs'],1)*100:.0f}%)</span>
  <span class="chip">horizon <b>Q{prof['horizon']}</b></span>
  <span class="chip">onset j* <b>{onset_txt}</b></span>
</div>
{metric_cards(prof)}
<div class="layer finite">
  <h3>Finite-scale layer \u2014 exact on this corpus</h3>
  <div class="fig">{svg_tower(rows)}</div>
  <div class="legend">
    <span><span class="sw" style="background:#3b4252"></span>n_j explored (a class count, exact)</span>
    <span><span class="sw" style="background:#3fb950"></span>L_j live (survived to the horizon)</span>
  </div>
  <div class="fig">{svg_yield(rows, onset)}</div>
  <div class="legend"><span><span class="sw" style="background:#58a6ff"></span>yield L_j/n_j</span>
    <span><span class="sw" style="background:#d29922"></span>onset j*</span></div>
  <div class="fig">{svg_exponents(prof['s_seq'], prof['d_seq'])}</div>
  <div class="legend"><span><span class="sw" style="background:#58a6ff"></span>S_j (explored)</span>
    <span><span class="sw" style="background:#3fb950"></span>D_j (live)</span>
    <span>the gap is \u0394, level by level</span></div>
  <p class="note">n_j = |H/\u223c_j| exactly; L_j is non-decreasing at a fixed horizon
  (\u00a72.5). Nothing in this panel is an estimate.</p>
</div>
{asymptotic_block(prof)}
"""


# --------------------------------------------------------------------------
def build_html(groups: dict[str, list], source: str, command: str, tower: str,
               fmt_counts: Counter) -> str:
    agents, profiles = {}, {}
    for name, runs in groups.items():
        p = AgentProfiler(index=PDI(tower=build_tower(tower)[0]))
        for r in runs:
            p.add_run(r, r.succeeded)
        agents[name] = p
        profiles[name] = p.profile()

    tools = Counter(s.tool for runs in groups.values() for r in runs for s in r.steps)
    total_runs = sum(len(v) for v in groups.values())
    total_steps = sum(len(r.steps) for runs in groups.values() for r in runs)
    total_err = sum(1 for runs in groups.values() for r in runs for s in r.steps if s.error)

    banner = "".join(f"<li>{_esc(w)}</li>" for w in WARRANT_BANNER)
    chips = (f'<span class="chip">runs <b>{total_runs}</b></span>'
             f'<span class="chip">tool calls <b>{total_steps}</b></span>'
             f'<span class="chip">errors <b>{total_err}</b> '
             f'({total_err/max(total_steps,1)*100:.1f}%)</span>'
             f'<span class="chip">groups <b>{len(groups)}</b></span>'
             f'<span class="chip">tower <b>{_esc(tower)}</b></span>')
    tool_chips = "".join(f'<span class="chip">{_esc(t)} <b>{c}</b></span>'
                         for t, c in tools.most_common(8))
    sections = "".join(group_section(n, profiles[n]) for n in groups)

    # machine-readable copy of exactly what is on screen
    payload = {"source": source, "command": command, "tower": tower,
               "warrant": WARRANT_BANNER,
               "groups": {n: {k: v for k, v in profiles[n].items()
                              if k in ("D", "S", "delta", "D_at", "S_at",
                                       "D_shallow", "S_shallow", "runs",
                                       "successes", "horizon", "rows")}
                          for n in groups}}
    data = json.dumps(payload, default=str).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDI dashboard \u2014 {_esc(source)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<h1>PDI \u2014 where useful discovery ends and unnecessary exploration begins</h1>
<p class="sub">source: {_esc(source)} &nbsp;\u00b7&nbsp; tower: {_esc(tower)}
 &nbsp;\u00b7&nbsp; generated offline, self-contained, no network</p>
<div class="chips">{chips}</div>
<div class="chips">{tool_chips}</div>

<div class="warrant"><b>WARRANT \u2014 what this page licenses, and what it does not</b>
<ul>{banner}</ul></div>

{sections}
{inflation_panel(agents, profiles)}

<h2>Reading order</h2>
<div class="card"><p class="note">
1. Read the <b>finite-scale</b> panel first: it is exact. Counts, yield, and the onset
Q where yield first falls below 10% need no asymptotics.<br>
2. Only then read <b>D / S / \u0394</b>, and check the badges. A SHALLOW value is the
levelwise maximum, not a rate.<br>
3. Use the <b>paired comparison</b> for differences between agents on the same tasks.
Do not use any number here as an absolute verdict about an agent.
</p></div>

<footer>
Generated by <code>dashboard.py</code> (stdlib only).
Reproduce: <code>{_esc(command)}</code><br>
Every panel states its own warrant; the ledger behind them is <code>SPINE.md</code> \u00a70.
Machine-readable copy of this page:
<code>&lt;script type="application/json" id="pdi-data"&gt;</code>.
</footer>
<script type="application/json" id="pdi-data">{data}</script>
</div></body></html>
"""


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PDI \u2014 interpretable trace dashboard")
    ap.add_argument("paths", nargs="*", help="trace files or directories")
    ap.add_argument("--format", choices=list(FORMATS), default=None)
    ap.add_argument("--group-by", choices=["model", "project", "file", "none"],
                    default="model")
    ap.add_argument("--tower", choices=["tool", "prefix"], default="tool")
    ap.add_argument("--min", type=int, default=2, help="min runs per group (default 2)")
    ap.add_argument("--out", default="dashboard.html")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args(argv)

    if a.demo or not a.paths:
        runs, source = demo_runs(), "synthetic demo (--demo)"
        command = "python3 dashboard.py --demo"
    else:
        runs = ingest(a.paths, a.format)
        source = ", ".join(a.paths)
        command = "python3 dashboard.py " + " ".join(a.paths)
        if a.format:
            command += f" --format {a.format}"

    if not runs:
        print("  nothing to profile.")
        return 1

    if a.group_by == "none":
        groups = {"all runs": runs}
    else:
        key = {"model": lambda r: r.model, "project": lambda r: r.project,
               "file": lambda r: r.session}[a.group_by]
        g: dict[str, list] = defaultdict(list)
        for r in runs:
            g[key(r) or "(unset)"].append(r)
        groups = dict(g)

    keep = {k: v for k, v in groups.items() if len(v) >= a.min}
    if not keep:
        keep = dict(max(groups.items(), key=lambda kv: len(kv[1])), ) or {}
        keep = {k: v for k, v in groups.items() if len(v) == max(len(x) for x in groups.values())}
        print(f"  no group had >= {a.min} runs; showing the largest group only.")

    fmt_counts = Counter()
    for p in a.paths:
        if os.path.isfile(p):
            fmt_counts[a.format or detect_format(p)] += 1

    doc = build_html(keep, source, command, a.tower, fmt_counts)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"  wrote {a.out}  ({len(doc):,} bytes, {len(keep)} group(s), "
          f"self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
