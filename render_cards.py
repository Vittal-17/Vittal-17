#!/usr/bin/env python3
"""
render_cards.py — Vittal J G / GitHub Profile README Card Generator
Renders clean, editorial SVG cards matching vittal-dev.vercel.app tokens.

Design tokens:
  Background gradient : #EEFABD → #F7F7EF → #EEF1FB  (horizontal)
  Accent (lime)       : #D7FF68  (highlight fill)
  Accent (olive)      : #92B346  (active status indicator, left bar)
  Periwinkle          : #CEDAFF  (secondary accent chip)
  Card surface        : #FFFFFD  stroke #DADDD1
  Inner surface       : #F8F9F5  stroke #E4E5DB
  Dark surface        : #141812 → #171916 (graph card)
  Body text           : #171916
  Muted text          : #60665F
  Grid lines          : #D1D5C6
  Sans font           : Arial, Helvetica, sans-serif
  Mono font           : ui-monospace, SFMono-Regular, Consolas, monospace

Live Data:
  - Fetches real-time contribution data directly from GitHub (https://github.com/users/Vittal-17/contributions)
  - Accurate monthly breakdown, streaks, active days, and 53-week heatmap matrix
  - Offline fallback to contributions.json

Animations:
  - Silky-smooth 60fps GPU-accelerated motion (no CPU color raster thrashing)
  - Deliberate pacing (1.5s - 2.5s reveals + calm, rhythmic ambient living loops)
  - Zero cheap neon laser slop
  - Full prefers-reduced-motion safety and STATIC=1 capture mode
"""

import json
import os
import sys
import subprocess
import tempfile
import base64
import textwrap
import urllib.request
import re
from datetime import datetime, date, timedelta
from collections import defaultdict
from pathlib import Path

# ─────────────────────────── config ────────────────────────────────────────

ROOT    = Path(__file__).parent
DATA    = ROOT / "contributions.json"
OUT     = ROOT / "cards"
STATIC  = os.environ.get("STATIC", "0") == "1"
W       = 1280

# ─────────── design tokens ─────────────────────────────────────────────────
LIME      = "#D7FF68"
OLIVE     = "#92B346"
PERIW     = "#CEDAFF"
CARD_BG   = "#FFFFFD"
CARD_STR  = "#DADDD1"
INNER_BG  = "#F8F9F5"
INNER_STR = "#E4E5DB"
DARK      = "#171916"
BODY      = "#171916"
MUTED     = "#60665F"
GRID      = "#D1D5C6"
SANS      = "Arial, Helvetica, sans-serif"
MONO      = "ui-monospace, SFMono-Regular, Consolas, monospace"

FONT_EMBED_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789.,·/—:()↗·%#@!?-_*★[]{}<>\n █"
)

# ─────────── Live Data Fetcher ──────────────────────────────────────────────

def fetch_and_load_data(username: str = "Vittal-17") -> dict:
    """Fetch live contribution data directly from GitHub."""
    existing = {}
    if DATA.exists():
        try:
            with open(DATA) as f:
                existing = json.load(f)
        except Exception:
            pass

    try:
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")

        td_chunks = re.findall(r'<td[^>]*class="[^"]*ContributionCalendar-day[^"]*"[^>]*>', html)
        tt_pattern = re.compile(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>')
        tooltips = dict(tt_pattern.findall(html))

        by_date = {}
        monthly_map = defaultdict(int)

        for td in td_chunks:
            date_m = re.search(r'data-date="([^"]+)"', td)
            lvl_m = re.search(r'data-level="([^"]+)"', td)
            id_m = re.search(r'id="([^"]+)"', td)
            if date_m and lvl_m and id_m:
                d_str = date_m.group(1)
                lvl = int(lvl_m.group(1))
                cid = id_m.group(1)
                tt_text = tooltips.get(cid, "")
                cnt_m = re.search(r"(\d+)\s+contribution", tt_text)
                count = int(cnt_m.group(1)) if cnt_m else 0
                by_date[d_str] = {
                    "count": count,
                    "level": lvl,
                    "desc": tt_text,
                }
                monthly_map[d_str[:7]] += count

        sorted_dates = sorted(by_date.keys())
        if sorted_dates:
            start_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
            end_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d").date()

            cur_date = start_date - timedelta(days=start_date.weekday())
            weeks_grid = []
            while cur_date <= end_date:
                week_col = []
                for _ in range(7):
                    ds = cur_date.strftime("%Y-%m-%d")
                    week_col.append(by_date[ds]["count"] if ds in by_date else 0)
                    cur_date += timedelta(days=1)
                weeks_grid.append(week_col)

            if len(weeks_grid) > 53:
                weeks_grid = weeks_grid[-53:]

            months_out = []
            for m_key in sorted(monthly_map.keys())[-12:]:
                dt = datetime.strptime(m_key + "-01", "%Y-%m-%d")
                months_out.append({
                    "month": m_key,
                    "label": dt.strftime("%b"),
                    "count": monthly_map[m_key],
                })

            streak = 0
            for d in reversed(sorted_dates):
                if by_date[d]["count"] > 0:
                    streak += 1
                else:
                    if streak == 0 and d == sorted_dates[-1]:
                        continue
                    break

            active_days = sum(1 for d in sorted_dates if by_date[d]["count"] > 0)
            busiest = max(sorted_dates, key=lambda d: by_date[d]["count"], default=sorted_dates[-1])
            total_ytd = sum(by_date[d]["count"] for d in sorted_dates)

            live_data = {
                "_note": "Auto-refreshed from real GitHub activity",
                "_updated": datetime.now().strftime("%Y-%m-%d"),
                "streak_days": streak,
                "active_days_ytd": active_days,
                "busiest_day": {"date": busiest, "count": by_date[busiest]["count"]},
                "total_ytd": total_ytd,
                "months": months_out,
                "repos": existing.get("repos", []),
                "graph_weeks": weeks_grid,
            }

            with open(DATA, "w") as f:
                json.dump(live_data, f, indent=2)
            print(f"   ✓ Live GitHub activity fetched: {total_ytd} contributions across {active_days} active days")
            return live_data

    except Exception as e:
        print(f"   ⚠ Live GitHub fetch fallback ({e}), using local contributions.json", file=sys.stderr)

    return existing

def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def wrap_text(text: str, max_chars: int) -> list[str]:
    return textwrap.wrap(text, max_chars)

# ─────────── Font Subsetting ───────────────────────────────────────────────

def _find_system_font() -> Path | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    try:
        out = subprocess.check_output(
            ["fc-list", ":spacing=proportional", "--format=%{file}\n"],
            text=True, stderr=subprocess.DEVNULL
        ).strip().splitlines()
        for line in out:
            line = line.strip()
            if line.lower().endswith((".ttf", ".otf")) and "Bold" not in line:
                return Path(line)
    except Exception:
        pass
    return None

def build_font_data_uri() -> str | None:
    src = _find_system_font()
    if src is None:
        return None
    with tempfile.TemporaryDirectory() as td:
        out_woff = Path(td) / "subset.woff"
        glyph_str = "".join(sorted(set(FONT_EMBED_CHARS)))
        try:
            subprocess.check_call([
                "pyftsubset", str(src),
                f"--text={glyph_str}",
                "--flavor=woff",
                f"--output-file={out_woff}",
                "--no-hinting",
                "--desubroutinize",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return None
        raw = out_woff.read_bytes()
        b64 = base64.b64encode(raw).decode()
        return f"data:font/woff;base64,{b64}"

# ─────────── SVG Helpers ───────────────────────────────────────────────────

def svg_open(width: int, height: int, card_id: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{esc(card_id)}">\n'
    )

def svg_close() -> str:
    return "</svg>"

def defs_block(font_uri: str | None, extra_defs: str = "") -> str:
    font_face = ""
    if font_uri:
        font_face = f"""
    @font-face {{
      font-family: 'VittalUI';
      src: url('{font_uri}') format('woff');
      font-weight: 400 800;
      font-style: normal;
    }}"""

    anim_css = "" if STATIC else """
    @media (prefers-reduced-motion: reduce) {
      * { animation: none !important; }
      animate, animateTransform { display: none !important; }
    }"""

    return f"""<defs>
  <style>{font_face}{anim_css}
  </style>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#EEFABD"/>
    <stop offset="43%"  stop-color="#F7F7EF"/>
    <stop offset="100%" stop-color="#EEF1FB"/>
  </linearGradient>
  <linearGradient id="bgGradDark" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#141812"/>
    <stop offset="50%"  stop-color="#171916"/>
    <stop offset="100%" stop-color="#1B1E18"/>
  </linearGradient>
  <radialGradient id="orbGrad">
    <stop offset="0%"   stop-color="#DEFF83" stop-opacity=".75"/>
    <stop offset="100%" stop-color="#DEFF83" stop-opacity="0"/>
  </radialGradient>
  <filter id="cardShadow" x="-5%" y="-5%" width="115%" height="130%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="8"/>
    <feOffset dy="4"/>
    <feComponentTransfer><feFuncA type="linear" slope=".08"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
{extra_defs}
</defs>
"""

def grid_lines(width: int, height: int, step: int = 54) -> str:
    lines = []
    x = 0
    while x <= width:
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
        x += step
    y = 0
    while y <= height:
        lines.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
        y += step
    return "\n".join(lines)

def accent_bar(height: int) -> str:
    return f'<line x1="40" y1="0" x2="40" y2="{height}" stroke="{OLIVE}" stroke-width="4" opacity="0.95"/>'

def logo_badge(x: int = 53, y: int = 28) -> str:
    return f"""
  <rect x="{x}" y="{y}" width="42" height="42" rx="12" fill="{LIME}"/>
  <text x="{x+21}" y="{y+29}" font-family="{SANS}" font-size="24" font-weight="800"
        fill="{DARK}" text-anchor="middle">V</text>
  <text x="{x+52}" y="{y+17}" font-family="{SANS}" font-size="19" font-weight="800"
        fill="{DARK}" letter-spacing="0.35">VITTAL J G</text>
  <text x="{x+52}" y="{y+36}" font-family="{MONO}" font-size="10" font-weight="600"
        fill="{MUTED}" letter-spacing="0.9">FULL-STACK ENGINEER / BENGALURU</text>
"""

def status_dot(cx: int, cy: int, color: str = OLIVE) -> str:
    """Clean status dot with a calm, visible breathing pulse."""
    if STATIC:
        return f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{color}"/>'
    return f"""
  <circle cx="{cx}" cy="{cy}" r="4.5" fill="{color}"/>
  <circle cx="{cx}" cy="{cy}" r="4.5" fill="{color}" opacity="0.6">
    <animate attributeName="r" values="4.5;13" dur="2.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.6;0" dur="2.8s" repeatCount="indefinite"/>
  </circle>
"""

# ─────────── Card 01 · Hero ────────────────────────────────────────────────

def render_hero(data: dict, font_uri: str | None) -> str:
    H = 420

    out = [svg_open(W, H, "Vittal J G — Big ideas. Built for real.")]
    out.append(defs_block(font_uri))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGrad)"/>')
    out.append(grid_lines(W, H))

    # Ambient backdrop orb
    out.append(f'<ellipse cx="640" cy="{H}" rx="500" ry="240" fill="url(#orbGrad)" opacity="0.6"/>')

    out.append(accent_bar(H))
    out.append(logo_badge())
    out.append(f'<line x1="53" y1="90" x2="{W-50}" y2="90" stroke="{CARD_STR}" stroke-width="1"/>')

    # Subtitle tag with blinking terminal cursor
    cursor_blink = "" if STATIC else f'<tspan fill="{OLIVE}">█<animate attributeName="opacity" values="1;0;1" dur="0.9s" repeatCount="indefinite"/></tspan>'
    out.append(
        f'<text x="59" y="131" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="{MUTED}" letter-spacing="1.8">01 / SOFTWARE · SYSTEMS · AI {cursor_blink}</text>'
    )

    # Big ideas.
    out.append(
        f'<text x="54" y="225" font-family="{SANS}" font-size="96" font-weight="800" '
        f'fill="{DARK}" letter-spacing="-4.7">Big ideas.</text>'
    )

    # Built for real. with smooth, deliberate 1.6s Highlighter marker wipe
    if STATIC:
        out.append(f'<rect x="53" y="258" width="650" height="94" rx="12" fill="{LIME}"/>')
    else:
        out.append(f"""
  <!-- Highlighter marker wipe effect (1.6s deliberate reveal) -->
  <rect x="53" y="258" width="650" height="94" rx="12" fill="{LIME}">
    <animate attributeName="width" from="0" to="650" dur="1.6s" begin="0.2s" fill="freeze"
             calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1"/>
    <animate attributeName="fill-opacity" values="1;0.88;1" dur="4.5s" begin="2.0s" repeatCount="indefinite"/>
  </rect>
""")
    out.append(
        f'<text x="62" y="336" font-family="{SANS}" font-size="88" font-weight="800" '
        f'fill="{DARK}" letter-spacing="-5.0">Built for real.</text>'
    )

    # Supporting copy
    out.append(
        f'<text x="57" y="378" font-family="{SANS}" font-size="21" font-weight="600" '
        f'fill="{DARK}">Thoughtful interfaces. Serious engineering.</text>'
    )
    out.append(
        f'<text x="57" y="406" font-family="{SANS}" font-size="17" font-weight="400" '
        f'fill="{MUTED}">From the first database table to the final interaction.</text>'
    )

    # Status pill with calm breathing pulse
    out.append(f'<rect x="{W-280}" y="28" width="232" height="34" rx="17" fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>')
    out.append(status_dot(W - 263, 45, color=OLIVE))
    out.append(f'<text x="{W-247}" y="50" font-family="{MONO}" font-size="13" font-weight="700" fill="{DARK}" letter-spacing="1.0">AVAILABLE FOR HIRE</text>')

    out.append(svg_close())
    return "".join(out)

# ─────────── Card 02 · Link Tiles (3 tiles at 32.5% each) ───────────────────

LINKS = [
    {"label": "PORTFOLIO", "sub": "vittal-dev.vercel.app",          "url": "https://vittal-dev.vercel.app/",          "accent": LIME,  "slug": "portfolio"},
    {"label": "GITHUB",    "sub": "github.com/Vittal-17",           "url": "https://github.com/Vittal-17",            "accent": PERIW, "slug": "github"},
    {"label": "LINKEDIN",  "sub": "linkedin.com/in/vittal-dev",     "url": "https://www.linkedin.com/in/vittal-dev/", "accent": LIME,  "slug": "linkedin"},
]

def render_link_tile(lnk: dict, font_uri: str | None) -> str:
    TW, TH = 420, 140

    out = [svg_open(TW, TH, lnk["label"])]
    out.append(defs_block(font_uri))
    out.append(f'<rect width="{TW}" height="{TH}" fill="url(#bgGrad)"/>')

    for x in range(0, TW + 1, 42):
        out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{TH}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
    for y in range(0, TH + 1, 42):
        out.append(f'<line x1="0" y1="{y}" x2="{TW}" y2="{y}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')

    out.append(f'<line x1="12" y1="0" x2="12" y2="{TH}" stroke="{OLIVE}" stroke-width="3" opacity="0.95"/>')

    sep_y = TH - 50

    out.append(
        f'<rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1" filter="url(#cardShadow)"/>'
    )
    out.append(
        f'<rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16" '
        f'fill="{lnk["accent"]}" opacity="0.08"/>'
    )

    # Icon badge
    out.append(f'<rect x="36" y="22" width="32" height="32" rx="9" fill="{lnk["accent"]}"/>')
    out.append(
        f'<text x="52" y="43" font-family="{SANS}" font-size="16" font-weight="800" '
        f'fill="{DARK}" text-anchor="middle">{esc(lnk["label"][0])}</text>'
    )

    # Title & Subtitle
    out.append(
        f'<text x="78" y="38" font-family="{MONO}" font-size="13" font-weight="800" '
        f'fill="{DARK}" letter-spacing="0.9">{esc(lnk["label"])}</text>'
    )
    out.append(
        f'<text x="78" y="56" font-family="{MONO}" font-size="10" font-weight="500" '
        f'fill="{MUTED}">{esc(lnk["sub"])}</text>'
    )

    # Diagonal Arrow ↗ with calm, continuous glide loop
    if STATIC:
        out.append(
            f'<text x="{TW-26}" y="38" font-family="{SANS}" font-size="20" '
            f'fill="{MUTED}" text-anchor="end" font-weight="600">↗</text>'
        )
    else:
        out.append(f"""
  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0; 3 -3; 0 0" keyTimes="0; 0.25; 1"
                     dur="4.0s" repeatCount="indefinite" calcMode="spline" keySplines="0.2 0.8 0.2 1; 0.2 0.8 0.2 1"/>
    <text x="{TW-26}" y="38" font-family="{SANS}" font-size="20"
          fill="{MUTED}" text-anchor="end" font-weight="600">↗</text>
  </g>
""")

    out.append(f'<line x1="36" y1="{sep_y}" x2="{TW-26}" y2="{sep_y}" stroke="{CARD_STR}" stroke-width="1"/>')
    out.append(status_dot(46, TH - 26, color=OLIVE))
    out.append(
        f'<text x="58" y="{TH-22}" font-family="{MONO}" font-size="11" font-weight="700" '
        f'fill="{DARK}" letter-spacing="0.5">OPEN ↗</text>'
    )

    out.append(svg_close())
    return "".join(out)

# ─────────── Card 03 · Contributions Chart ─────────────────────────────────

def render_chart(data: dict, font_uri: str | None) -> str:
    H      = 280
    months = data["months"]
    streak = data["streak_days"]
    active = data["active_days_ytd"]
    busy   = data["busiest_day"]
    total  = data["total_ytd"]

    max_c  = max((m["count"] for m in months), default=1) or 1
    BAR_MAX_H = 110
    BAR_W  = 48
    LEFT   = 60
    BOTTOM = 200
    BAR_GAP = (W - LEFT - 60 - len(months) * BAR_W) // (len(months) - 1 or 1)

    out = [svg_open(W, H, "Contributions per month")]
    out.append(defs_block(font_uri))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGrad)"/>')
    out.append(grid_lines(W, H))
    out.append(accent_bar(H))

    out.append(
        f'<text x="59" y="40" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="{MUTED}" letter-spacing="1.8">02 / CONTRIBUTION ACTIVITY</text>'
    )

    # Real stats pills
    stats = [
        (f"{streak}d", "STREAK", True),
        (f"{active}", "ACTIVE DAYS", False),
        (busy["date"][-5:], "BUSIEST DAY", False),
        (f"{total}", "TOTAL YTD", False),
    ]
    pw = 170
    for si, (val, lbl, has_dot) in enumerate(stats):
        px = W - 50 - (len(stats)-si) * (pw + 10)
        out.append(
            f'<rect x="{px}" y="12" width="{pw}" height="52" rx="12" '
            f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>'
        )
        if has_dot:
            out.append(status_dot(px + pw - 18, 22, color=OLIVE))
        out.append(
            f'<text x="{px+14}" y="34" font-family="{SANS}" font-size="20" '
            f'font-weight="800" fill="{DARK}">{esc(val)}</text>'
        )
        out.append(
            f'<text x="{px+14}" y="52" font-family="{MONO}" font-size="10" '
            f'font-weight="600" fill="{MUTED}" letter-spacing="0.9">{esc(lbl)}</text>'
        )

    # Bars representing real activity with smooth, deliberate 1.5s wave rise
    for i, m in enumerate(months):
        bh = int(m["count"] / max_c * BAR_MAX_H) if max_c > 0 else 0
        bx = LEFT + i * (BAR_W + BAR_GAP)
        by = BOTTOM - bh
        is_peak = (m["count"] == max_c and m["count"] > 0)
        fill = LIME if is_peak else (INNER_BG if m["count"] > 0 else CARD_STR)
        stroke = OLIVE if is_peak else (CARD_STR if m["count"] > 0 else "none")

        if bh > 0:
            stagger = 0.15 + i * 0.08
            out.append(
                f'<rect x="{bx}" y="{by}" width="{BAR_W}" height="{bh}" rx="6" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{1.5 if is_peak else 1}">'
            )
            if not STATIC:
                out.append(
                    f'<animate attributeName="height" from="0" to="{bh}" '
                    f'begin="{stagger:.2f}s" dur="1.4s" fill="freeze" '
                    f'calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1"/>\n'
                    f'<animate attributeName="y" from="{BOTTOM}" to="{by}" '
                    f'begin="{stagger:.2f}s" dur="1.4s" fill="freeze" '
                    f'calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1"/>\n'
                )
                if is_peak:
                    out.append(
                        f'<animate attributeName="stroke-width" values="1.5;3.2;1.5" dur="3.0s" begin="{stagger+1.4:.2f}s" repeatCount="indefinite"/>\n'
                    )
            out.append("</rect>\n")
        else:
            out.append(
                f'<rect x="{bx+BAR_W//2-4}" y="{BOTTOM-2}" width="8" height="2" rx="1" fill="{CARD_STR}" opacity="0.4"/>\n'
            )

        # Count label on top of bar
        if m["count"] > 0:
            out.append(
                f'<text x="{bx + BAR_W//2}" y="{by - 6}" font-family="{MONO}" font-size="11" font-weight="700" '
                f'fill="{DARK if is_peak else MUTED}" text-anchor="middle">{m["count"]}</text>\n'
            )

        # Month label
        out.append(
            f'<text x="{bx + BAR_W//2}" y="{BOTTOM + 20}" '
            f'font-family="{MONO}" font-size="11" font-weight="600" '
            f'fill="{MUTED}" text-anchor="middle">{esc(m["label"])}</text>\n'
        )

    out.append(
        f'<line x1="{LEFT-10}" y1="{BOTTOM}" x2="{W-50}" y2="{BOTTOM}" stroke="{CARD_STR}" stroke-width="1"/>'
    )

    out.append(svg_close())
    return "".join(out)

# ─────────── Card 04 · Repo Cards ──────────────────────────────────────────

LANG_COLOR = {
    "Python":     "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Rust":       "#DEA584",
    "Go":         "#00ADD8",
}

def render_repo(repo: dict, idx: int, font_uri: str | None) -> str:
    H      = 190

    CARD_L = 53
    CARD_R = W - 53
    CARD_T = 16
    CARD_B = H - 16
    CARD_W = CARD_R - CARD_L
    CARD_H = CARD_B - CARD_T

    DIV_X  = CARD_L + int(CARD_W * 0.72)

    clip_id = f"cc{idx}"
    extra = (
        f'  <clipPath id="{clip_id}">\n'
        f'    <rect x="{CARD_L}" y="{CARD_T}" width="{CARD_W}" height="{CARD_H}" rx="20" ry="20"/>\n'
        f'  </clipPath>'
    )

    out = [svg_open(W, H, f"Repo — {repo['name']}")]
    out.append(defs_block(font_uri, extra_defs=extra))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGrad)"/>')
    out.append(grid_lines(W, H))
    out.append(accent_bar(H))

    # Base card
    out.append(
        f'<rect x="{CARD_L}" y="{CARD_T}" width="{CARD_W}" height="{CARD_H}" rx="20" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1" filter="url(#cardShadow)"/>'
    )

    # Right panel tinted background
    out.append(
        f'<rect x="{DIV_X}" y="{CARD_T}" width="{CARD_R - DIV_X}" height="{CARD_H}" '
        f'fill="{INNER_BG}" clip-path="url(#{clip_id})"/>'
    )

    # Clean divider line
    out.append(
        f'<line x1="{DIV_X}" y1="{CARD_T + 14}" x2="{DIV_X}" y2="{CARD_B - 14}" '
        f'stroke="{CARD_STR}" stroke-width="1"/>'
    )

    # ── Left Panel ───────────────────────────────────────────────────────────
    chip_x, chip_y = CARD_L + 17, CARD_T + 14

    out.append(f'<rect x="{chip_x}" y="{chip_y}" width="32" height="28" rx="8" fill="{LIME}"/>')
    out.append(
        f'<text x="{chip_x + 16}" y="{chip_y + 20}" font-family="{MONO}" font-size="13" '
        f'font-weight="800" fill="{DARK}" text-anchor="middle">{idx+1:02d}</text>'
    )

    out.append(
        f'<text x="{CARD_L + 60}" y="{CARD_T + 36}" font-family="{SANS}" font-size="21" '
        f'font-weight="800" fill="{DARK}" letter-spacing="-0.5">{esc(repo["name"])}</text>'
    )

    max_chars = max(20, int((DIV_X - CARD_L - 70) / 8.3))
    desc_lines = wrap_text(repo["description"], max_chars)
    for li, line in enumerate(desc_lines[:2]):
        out.append(
            f'<text x="{CARD_L + 17}" y="{CARD_T + 68 + li * 21}" '
            f'font-family="{SANS}" font-size="14" font-weight="400" fill="{MUTED}">'
            f'{esc(line)}</text>'
        )

    # Topics
    tx   = CARD_L + 17
    ty   = CARD_B - 46
    for topic in repo["topics"][:5]:
        tw = len(topic) * 7 + 26
        if tx + tw > DIV_X - 10:
            break
        out.append(
            f'<rect x="{tx}" y="{ty}" width="{tw}" height="26" rx="12" '
            f'fill="{CARD_BG}" stroke="{INNER_STR}" stroke-width="1"/>'
        )
        out.append(f'<circle cx="{tx + 13}" cy="{ty + 13}" r="4" fill="{OLIVE}"/>')
        out.append(
            f'<text x="{tx + 24}" y="{ty + 18}" font-family="{SANS}" font-size="11" '
            f'font-weight="600" fill="{DARK}">{esc(topic)}</text>'
        )
        tx += tw + 8

    # ── Right Panel ──────────────────────────────────────────────────────────
    RP_TOP = CARD_T + 22

    lang_col = LANG_COLOR.get(repo.get("language", ""), MUTED)
    out.append(f'<circle cx="{DIV_X + 24}" cy="{RP_TOP + 7}" r="6" fill="{lang_col}"/>')
    out.append(
        f'<text x="{DIV_X + 38}" y="{RP_TOP + 12}" font-family="{MONO}" font-size="12" '
        f'font-weight="600" fill="{DARK}">{esc(repo.get("language", ""))}</text>'
    )

    # Star count
    out.append(
        f'<text x="{CARD_R - 24}" y="{RP_TOP + 12}" font-family="{MONO}" font-size="13" '
        f'font-weight="800" fill="{DARK}" text-anchor="end">★ {repo.get("stars", 0)}</text>'
    )

    sep_y = CARD_T + CARD_H // 2
    out.append(
        f'<line x1="{DIV_X + 16}" y1="{sep_y}" x2="{CARD_R - 16}" y2="{sep_y}" '
        f'stroke="{CARD_STR}" stroke-width="1"/>'
    )

    btn_y    = sep_y + 12
    btn_h    = 32
    rp_inner = CARD_R - DIV_X - 32
    btn_w    = (rp_inner - 8) // 2
    live_x   = DIV_X + 16
    src_x    = live_x + btn_w + 8

    # LIVE button with calm breathing fill
    if STATIC:
        out.append(
            f'<rect x="{live_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="14" fill="{LIME}"/>'
        )
    else:
        out.append(f"""
  <rect x="{live_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="14" fill="{LIME}">
    <animate attributeName="fill-opacity" values="1;0.82;1" dur="3.2s" repeatCount="indefinite"/>
  </rect>
""")
    out.append(
        f'<text x="{live_x + btn_w // 2}" y="{btn_y + 21}" font-family="{MONO}" '
        f'font-size="11" font-weight="800" fill="{DARK}" text-anchor="middle">LIVE ↗</text>'
    )
    out.append(
        f'<rect x="{src_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="14" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>'
    )
    out.append(
        f'<text x="{src_x + btn_w // 2}" y="{btn_y + 21}" font-family="{MONO}" '
        f'font-size="11" font-weight="700" fill="{MUTED}" text-anchor="middle">SOURCE ↗</text>'
    )

    out.append(svg_close())
    return "".join(out)

# ─────────── Card 05 · Contribution Graph ──────────────────────────────────

def render_graph(data: dict, font_uri: str | None) -> str:
    """Render a clean GitHub-style contribution heatmap with a silky smooth GPU-accelerated scanline sweep."""
    H       = 200
    weeks   = data.get("graph_weeks", [])
    CELL    = 14
    GAP     = 3
    GRID_X  = 60
    GRID_Y  = 62
    DAYS    = ["Mon", "", "Wed", "", "Fri", "", "Sun"]
    max_val = max((v for w in weeks for v in w), default=1) or 1

    def cell_color(v: int) -> tuple[str, str]:
        if v == 0:
            return "#161B14", "#20271D"
        t = v / max_val
        if t <= 0.25:
            return "#3E5219", "#4A611E"
        if t <= 0.50:
            return "#688A29", "#789F30"
        if t <= 0.75:
            return "#98C638", "#A4D43D"
        return "#D7FF68", "#E2FF7E"

    out = [svg_open(W, H, "Contribution graph")]
    out.append(defs_block(font_uri))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGradDark)"/>')

    for gx in range(0, W + 1, 64):
        out.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="#FFFFFF" stroke-width="0.8" opacity="0.04"/>')
    for gy in range(0, H + 1, 30):
        out.append(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="#FFFFFF" stroke-width="0.8" opacity="0.04"/>')

    total_ytd = data.get("total_ytd", sum(v for w in weeks for v in w))
    out.append(
        f'<text x="59" y="32" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="#C6D5B2" letter-spacing="1.8">05 / CONTRIBUTION GRAPH</text>'
    )
    out.append(
        f'<text x="320" y="32" font-family="{SANS}" font-size="13" font-weight="600" '
        f'fill="#A1AB98">({total_ytd} contributions in the last year)</text>'
    )

    # Real month headers
    today = date.today()
    cur = today - timedelta(days=len(weeks)*7 - 1)
    cur = cur - timedelta(days=cur.weekday())
    last_m = None
    for wi in range(len(weeks)):
        w_date = cur + timedelta(days=wi*7)
        for d in range(7):
            day = w_date + timedelta(days=d)
            if day.day <= 7 and day.month != last_m:
                out.append(
                    f'<text x="{GRID_X + wi * (CELL + GAP)}" y="{GRID_Y - 8}" '
                    f'font-family="{MONO}" font-size="10" font-weight="600" fill="#8E9988">'
                    f'{day.strftime("%b")}</text>'
                )
                last_m = day.month
                break

    # Real heatmap cells — 100% static, rock-solid 60 FPS, ZERO CPU color thrashing
    for wi, week in enumerate(weeks):
        for di, val in enumerate(week):
            cx = GRID_X + wi * (CELL + GAP)
            cy = GRID_Y + di * (CELL + GAP)
            bg, st = cell_color(val)
            out.append(
                f'<rect x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{bg}" stroke="{st}" stroke-width="0.8"/>\n'
            )

    for di, lbl in enumerate(DAYS):
        if lbl:
            cy = GRID_Y + di * (CELL + GAP) + CELL - 3
            out.append(
                f'<text x="{GRID_X - 8}" y="{cy}" font-family="{MONO}" font-size="9" '
                f'font-weight="600" fill="#8E9988" text-anchor="end">{lbl}</text>'
            )

    # Silky-smooth 60fps GPU-accelerated Luminous Radar Beam (sweeps every 5.5s)
    if not STATIC:
        out.append(f"""
  <linearGradient id="scanBeam" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#D7FF68" stop-opacity="0"/>
    <stop offset="35%"  stop-color="#D7FF68" stop-opacity="0.25"/>
    <stop offset="50%"  stop-color="#FFFFFF" stop-opacity="0.60"/>
    <stop offset="65%"  stop-color="#D7FF68" stop-opacity="0.25"/>
    <stop offset="100%" stop-color="#D7FF68" stop-opacity="0"/>
  </linearGradient>
  <rect x="{GRID_X - 100}" y="{GRID_Y - 8}" width="90" height="{7 * (CELL + GAP) + 12}"
        fill="url(#scanBeam)" rx="4">
    <animate attributeName="x"
             values="{GRID_X - 100}; {GRID_X + len(weeks) * (CELL + GAP) + 40}; {GRID_X + len(weeks) * (CELL + GAP) + 40}"
             keyTimes="0; 0.55; 1"
             dur="5.5s"
             repeatCount="indefinite"
             calcMode="spline"
             keySplines="0.25 0.1 0.25 1; 0 0 1 1"/>
    <animate attributeName="opacity"
             values="0; 1; 1; 0; 0"
             keyTimes="0; 0.08; 0.48; 0.54; 1"
             dur="5.5s"
             repeatCount="indefinite"/>
  </rect>
""")

    # Legend in brand colours
    lx = W - 220
    out.append(f'<text x="{lx}" y="{H-16}" font-family="{MONO}" font-size="10" fill="#8E9988">Less</text>')
    legend_colors = ["#161B14", "#3E5219", "#688A29", "#98C638", "#D7FF68"]
    for li, col in enumerate(legend_colors):
        out.append(
            f'<rect x="{lx+38+li*17}" y="{H-27}" width="{CELL}" height="{CELL}" rx="3" fill="{col}" stroke="#303828" stroke-width="0.8"/>'
        )
    out.append(f'<text x="{lx+38+5*17 + 6}" y="{H-16}" font-family="{MONO}" font-size="10" fill="#8E9988">More</text>')

    out.append(svg_close())
    return "".join(out)

# ─────────── README Writer ──────────────────────────────────────────────────

def build_readme(repos: list[dict]) -> str:
    lines = [
        "<!--",
        "  VITTAL J G / GITHUB PROFILE · V3 ANIMATED SVG CARDS",
        "  Generated by render_cards.py — DO NOT EDIT BY HAND",
        "  Source: https://vittal-dev.vercel.app/",
        "-->",
        "",
        '<div align="center">',
        "",
        "<!-- 01 hero -->",
        '<a href="https://vittal-dev.vercel.app/">',
        '  <img src="./cards/01-hero.svg" width="100%" alt="Vittal J G — Big ideas. Built for real."/>',
        "</a>",
        "",
        "<!-- 02 links row — three tiles at 32.5% each, inline so they sit side-by-side -->",
        '<a href="https://vittal-dev.vercel.app/"><img src="./cards/02-link-portfolio.svg" width="32.5%" alt="Portfolio ↗"/></a>&nbsp;'
        '<a href="https://github.com/Vittal-17"><img src="./cards/02-link-github.svg" width="32.5%" alt="GitHub ↗"/></a>&nbsp;'
        '<a href="https://www.linkedin.com/in/vittal-dev/"><img src="./cards/02-link-linkedin.svg" width="32.5%" alt="LinkedIn ↗"/></a>',
        "",
        "<!-- 03 chart -->",
        '<img src="./cards/03-chart.svg" width="100%" alt="Contributions per month"/>',
        "",
        "<!-- 04 repos -->",
    ]
    for i, r in enumerate(repos):
        slug = r["name"].lower().replace("/", "-")
        lines.append(
            f'<a href="{r["url"]}">'
            f'<img src="./cards/04-repo-{i+1:02d}-{slug}.svg" '
            f'width="100%" alt="{esc(r["name"])} — {esc(r["description"])}"/>'
            f'</a>'
        )

    lines += [
        "",
        "<!-- 05 contribution graph -->",
        '<img src="./cards/05-graph.svg" width="100%" alt="Contribution graph"/>',
        "",
        "</div>",
        "",
        "<p align=\"center\">",
        '  <a href="https://vittal-dev.vercel.app/"><strong>Portfolio ↗</strong></a> &nbsp;/&nbsp;',
        '  <a href="https://github.com/Vittal-17?tab=repositories"><strong>Repositories ↗</strong></a> &nbsp;/&nbsp;',
        '  <a href="https://www.linkedin.com/in/vittal-dev/"><strong>LinkedIn ↗</strong></a> &nbsp;/&nbsp;',
        '  <a href="mailto:vitthaljg@gmail.com"><strong>Contact ↗</strong></a>',
        "</p>",
        "",
        "<sub>FULL-STACK ENGINEERING · PYTHON BACKENDS · AI / RAG · AUTOMATION · CLOUD</sub>",
        "",
    ]
    return "\n".join(lines)

# ─────────── Main ────────────────────────────────────────────────────────────

def main():
    OUT.mkdir(exist_ok=True)
    data   = fetch_and_load_data("Vittal-17")
    repos  = data["repos"]
    mode   = "STATIC" if STATIC else "ANIMATED (60FPS HIGH CRAFT)"
    print(f"🎨  render_cards.py — {mode} mode")

    print("   subsetting font…")
    font_uri = build_font_data_uri()
    if font_uri:
        print(f"   font embedded ({len(font_uri)//1024} KB)")
    else:
        print("   no font embed — using system fonts")

    cards = []

    # 01 hero
    path = OUT / "01-hero.svg"
    path.write_text(render_hero(data, font_uri), encoding="utf-8")
    cards.append(str(path))
    print(f"   ✓ {path.name}")

    # 02 link tiles
    for lnk in LINKS:
        path = OUT / f"02-link-{lnk['slug']}.svg"
        path.write_text(render_link_tile(lnk, font_uri), encoding="utf-8")
        cards.append(str(path))
        print(f"   ✓ {path.name}")

    # 03 chart
    path = OUT / "03-chart.svg"
    path.write_text(render_chart(data, font_uri), encoding="utf-8")
    cards.append(str(path))
    print(f"   ✓ {path.name}")

    # 04 repos
    for i, repo in enumerate(repos):
        slug = repo["name"].lower().replace("/", "-")
        path = OUT / f"04-repo-{i+1:02d}-{slug}.svg"
        path.write_text(render_repo(repo, i, font_uri), encoding="utf-8")
        cards.append(str(path))
        print(f"   ✓ {path.name}")

    # 05 graph
    path = OUT / "05-graph.svg"
    path.write_text(render_graph(data, font_uri), encoding="utf-8")
    cards.append(str(path))
    print(f"   ✓ {path.name}")

    # Update README
    readme = ROOT / "README.md"
    readme.write_text(build_readme(repos), encoding="utf-8")
    print(f"   ✓ README.md regenerated")

    print(f"\n✅  {len(cards)} cards written to {OUT}/")

if __name__ == "__main__":
    main()
