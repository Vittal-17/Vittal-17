#!/usr/bin/env python3
"""
render_cards.py — Vittal J G / GitHub Profile README Card Generator
Renders lively animated SVG cards into cards/ directory.

Design tokens lifted directly from assets/hero.svg and assets/toolkit.svg:
  Background gradient : #EEFABD → #F7F7EF → #EEF1FB  (horizontal)
  Accent (lime)       : #D7FF68  (highlight fill & energy beams)
  Accent (olive)      : #92B346  (active/status dot, left accent bar)
  Periwinkle          : #CEDAFF  (secondary accent chip)
  Card surface        : #FFFFFD  stroke #DADDD1
  Inner surface       : #F8F9F5  stroke #E4E5DB
  Dark surface        : #171916  (#141812 → #1B1E18)
  Body text           : #171916
  Muted text          : #60665F
  Grid lines          : #D1D5C6
  Sans font           : Arial, Helvetica, sans-serif  (weight 800 headlines, 600/400 body)
  Mono font           : ui-monospace, SFMono-Regular, Consolas, monospace

Real-Time Scrolling Animations:
  - Continuous border-tracing laser beams (stroke-dashoffset loops)
  - Specular glass sheen sweeps across cards at staggered frequencies
  - Expanding radar sonar pings on active beacons and "LIVE ↗" buttons
  - Real-time data pulse packets running down repo card splitters
  - Breathing ambient atmospheric orbs and peak-month contribution glow
  - Continuous luminous wave sweeping over the contribution heatmap
  - Full prefers-reduced-motion: reduce safety & STATIC=1 final-frame mode

Usage:
  python3 render_cards.py              # lively animated cards
  STATIC=1 python3 render_cards.py     # final-frame only (no animation), for screenshots
"""

import json
import os
import sys
import math
import subprocess
import tempfile
import base64
import textwrap
from pathlib import Path

# ─────────────────────────── config ────────────────────────────────────────

ROOT    = Path(__file__).parent
DATA    = ROOT / "contributions.json"
OUT     = ROOT / "cards"
STATIC  = os.environ.get("STATIC", "0") == "1"
W       = 1280   # standard card width (matches original vector assets)

# ─────────── design tokens (from SVG source-of-truth) ──────────────────────
BG_GRAD   = "#EEFABD,#F7F7EF,#EEF1FB"   # left → mid → right
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

# ─────────── font subsetting ────────────────────────────────────────────────
FONT_EMBED_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789.,·/—:()↗·%#@!?-_*★[]{}<>\n "
)

# Stagger delays (seconds) for initial top-to-bottom intro reveal
CARD_DELAYS = {
    "hero":  0.0,
    "links": 0.3,
    "chart": 0.6,
    "repo":  0.9,   # +0.12 per repo
    "graph": 1.7,
}

# ─────────── helpers ────────────────────────────────────────────────────────

def load_data() -> dict:
    with open(DATA) as f:
        return json.load(f)

def esc(s: str) -> str:
    """XML-escape a string."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def wrap_text(text: str, max_chars: int) -> list[str]:
    return textwrap.wrap(text, max_chars)

# ─────────── font subsetting ────────────────────────────────────────────────

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

# ─────────── SVG primitives & shared defs ───────────────────────────────────

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

    # Keyframes: Initial intro + Continuous real-time ambient loops
    anim_css = "" if STATIC else """
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(14px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulseGlow {
      0%, 100% { opacity: 0.85; transform: scale(1); }
      50%      { opacity: 1;    transform: scale(1.02); }
    }
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
  <linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0"  stop-color="#FFFFFF"/>
    <stop offset="1"  stop-color="#F6F9EC"/>
  </linearGradient>
  <radialGradient id="orbGrad">
    <stop offset="0%"   stop-color="#DEFF83" stop-opacity=".75"/>
    <stop offset="100%" stop-color="#DEFF83" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="beamGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#D7FF68" stop-opacity="0"/>
    <stop offset="50%"  stop-color="#D7FF68" stop-opacity="0.95"/>
    <stop offset="100%" stop-color="#92B346" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="shimmerGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#FFFFFF" stop-opacity="0"/>
    <stop offset="40%"  stop-color="#FFFFFF" stop-opacity="0.04"/>
    <stop offset="50%"  stop-color="#D7FF68" stop-opacity="0.22"/>
    <stop offset="60%"  stop-color="#FFFFFF" stop-opacity="0.08"/>
    <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="heatSweep" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#D7FF68" stop-opacity="0"/>
    <stop offset="50%"  stop-color="#D7FF68" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#D7FF68" stop-opacity="0"/>
  </linearGradient>
  <filter id="cardShadow" x="-5%" y="-5%" width="115%" height="130%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="10"/>
    <feOffset dy="6"/>
    <feComponentTransfer><feFuncA type="linear" slope=".10"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
{extra_defs}
</defs>
"""

def grid_lines(width: int, height: int, step: int = 54) -> str:
    """Faint blueprint grid identical to existing assets."""
    lines = []
    x = 0
    while x <= width:
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" '
                     f'stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
        x += step
    y = 0
    while y <= height:
        lines.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" '
                     f'stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
        y += step
    return "\n".join(lines)

def accent_bar(height: int) -> str:
    """Left olive accent bar with subtle real-time energy flow."""
    bar = [f'<line x1="40" y1="0" x2="40" y2="{height}" stroke="{OLIVE}" stroke-width="4" opacity="0.95"/>']
    if not STATIC:
        bar.append(
            f'<line x1="40" y1="0" x2="40" y2="{height}" stroke="{LIME}" stroke-width="4" '
            f'stroke-dasharray="60 {height}" stroke-linecap="round" opacity="0.8">'
            f'<animate attributeName="stroke-dashoffset" values="0;-{height+60}" dur="3.5s" repeatCount="indefinite"/>'
            f'</line>'
        )
    return "\n".join(bar)

def logo_badge(x: int = 53, y: int = 28) -> str:
    """V badge + name + tagline identical to hero.svg header."""
    return f"""
  <rect x="{x}" y="{y}" width="42" height="42" rx="12" fill="{LIME}"/>
  <text x="{x+21}" y="{y+29}" font-family="{SANS}" font-size="24" font-weight="800"
        fill="{DARK}" text-anchor="middle">V</text>
  <text x="{x+52}" y="{y+17}" font-family="{SANS}" font-size="19" font-weight="800"
        fill="{DARK}" letter-spacing="0.35">VITTAL J G</text>
  <text x="{x+52}" y="{y+36}" font-family="{MONO}" font-size="10" font-weight="600"
        fill="{MUTED}" letter-spacing="0.9">FULL-STACK ENGINEER / BENGALURU</text>
"""

def anim_style(delay: float, dur: float = 0.55) -> str:
    if STATIC:
        return ""
    return f'style="animation: fadeUp {dur}s ease-out {delay:.2f}s both; opacity:0"'

def radar_ping(cx: int, cy: int, color: str = OLIVE, dur: float = 2.4) -> str:
    """Lively sonar radar ping radiating continuous outward ripples."""
    if STATIC:
        return f'<circle cx="{cx}" cy="{cy}" r="5" fill="{color}"/>'
    return f"""
  <circle cx="{cx}" cy="{cy}" r="4" fill="none" stroke="{color}" stroke-width="1.8" opacity="0.85">
    <animate attributeName="r" values="4;13" dur="{dur}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.85;0" dur="{dur}s" repeatCount="indefinite"/>
    <animate attributeName="stroke-width" values="1.8;0.3" dur="{dur}s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{cx}" cy="{cy}" r="4.5" fill="{color}">
    <animate attributeName="opacity" values="1;0.45;1" dur="{dur}s" repeatCount="indefinite"/>
  </circle>
"""

def card_shimmer(x: int, y: int, w: int, h: int, clip_id: str, dur: float = 4.8, delay: float = 0.0) -> str:
    """Glancing specular light sheen sweeping across card faces in real time."""
    if STATIC:
        return ""
    return f"""
  <g clip-path="url(#{clip_id})">
    <rect x="{x - 420}" y="{y}" width="380" height="{h}" fill="url(#shimmerGrad)">
      <animate attributeName="x" values="{x - 420};{x + w + 120}" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>
    </rect>
  </g>
"""

# ─────────── card 01 · hero ─────────────────────────────────────────────────

def render_hero(data: dict, font_uri: str | None) -> str:
    H = 420
    delay = CARD_DELAYS["hero"]
    clip_id = "heroClip"
    extra = f'<clipPath id="{clip_id}"><rect x="0" y="0" width="{W}" height="{H}"/></clipPath>'

    out = [svg_open(W, H, "Vittal J G — Big ideas. Built for real.")]
    out.append(defs_block(font_uri, extra_defs=extra))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGrad)"/>')
    out.append(grid_lines(W, H))

    # Lively breathing atmospheric orb
    if not STATIC:
        out.append(
            f'<ellipse cx="640" cy="{H}" rx="500" ry="250" fill="url(#orbGrad)" opacity="0.55">'
            f'<animate attributeName="rx" values="480;540;480" dur="6s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.45;0.75;0.45" dur="6s" repeatCount="indefinite"/>'
            f'</ellipse>'
        )
    else:
        out.append(f'<ellipse cx="640" cy="{H}" rx="500" ry="250" fill="url(#orbGrad)" opacity="0.55"/>')

    out.append(accent_bar(H))
    out.append(logo_badge())

    # Separator
    out.append(f'<line x1="53" y1="90" x2="{W-50}" y2="90" stroke="{CARD_STR}" stroke-width="1"/>')

    # Section label
    g1 = f'<g {anim_style(delay, 0.55)}>' if not STATIC else '<g>'
    out.append(g1)
    out.append(
        f'<text x="59" y="131" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="{MUTED}" letter-spacing="1.8">01 / SOFTWARE · SYSTEMS · AI</text>'
    )
    out.append("</g>")

    # Big headline with lively highlighted pill
    g2 = f'<g {anim_style(delay+0.08, 0.6)}>' if not STATIC else '<g>'
    out.append(g2)
    out.append(
        f'<text x="54" y="225" font-family="{SANS}" font-size="96" font-weight="800" '
        f'fill="{DARK}" letter-spacing="-4.7">Big ideas.</text>'
    )
    out.append(f'<rect x="53" y="258" width="650" height="94" rx="12" fill="{LIME}"/>')
    if not STATIC:
        # Subtle light sheen glancing across the lime pill
        out.append(
            f'<rect x="53" y="258" width="160" height="94" rx="12" fill="url(#shimmerGrad)" opacity="0.75">'
            f'<animate attributeName="x" values="53;650;53" dur="5s" repeatCount="indefinite"/>'
            f'</rect>'
        )
    out.append(
        f'<text x="62" y="336" font-family="{SANS}" font-size="88" font-weight="800" '
        f'fill="{DARK}" letter-spacing="-5.0">Built for real.</text>'
    )
    out.append("</g>")

    # Tagline
    g3 = f'<g {anim_style(delay+0.16, 0.6)}>' if not STATIC else '<g>'
    out.append(g3)
    out.append(
        f'<text x="57" y="378" font-family="{SANS}" font-size="21" font-weight="600" '
        f'fill="{DARK}">Thoughtful interfaces. Serious engineering.</text>'
    )
    out.append(
        f'<text x="57" y="406" font-family="{SANS}" font-size="17" font-weight="400" '
        f'fill="{MUTED}">From the first database table to the final interaction.</text>'
    )
    out.append("</g>")

    # Real-time Status beacon badge (top-right)
    g4 = f'<g {anim_style(delay+0.22, 0.6)}>' if not STATIC else '<g>'
    out.append(g4)
    out.append(f'<rect x="{W-280}" y="28" width="232" height="34" rx="17" fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>')
    out.append(radar_ping(W - 263, 45, color=OLIVE, dur=2.2))
    out.append(f'<text x="{W-247}" y="50" font-family="{MONO}" font-size="13" font-weight="700" fill="{DARK}" letter-spacing="1.0">AVAILABLE FOR HIRE</text>')
    out.append("</g>")

    out.append(svg_close())
    return "".join(out)

# ─────────── card 02 · link tiles (three separate 420×140 SVGs) ─────────────

LINKS = [
    {"label": "PORTFOLIO", "sub": "vittal-dev.vercel.app",          "url": "https://vittal-dev.vercel.app/",          "accent": LIME,  "slug": "portfolio"},
    {"label": "GITHUB",    "sub": "github.com/Vittal-17",           "url": "https://github.com/Vittal-17",            "accent": PERIW, "slug": "github"},
    {"label": "LINKEDIN",  "sub": "linkedin.com/in/vittal-dev",     "url": "https://www.linkedin.com/in/vittal-dev/", "accent": LIME,  "slug": "linkedin"},
]

def render_link_tile(lnk: dict, delay: float, font_uri: str | None) -> str:
    TW, TH = 420, 140
    clip_id = f"lc_{lnk['slug']}"
    extra = (
        f'  <clipPath id="{clip_id}">\n'
        f'    <rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16"/>\n'
        f'  </clipPath>'
    )

    out = [svg_open(TW, TH, lnk["label"])]
    out.append(defs_block(font_uri, extra_defs=extra))
    out.append(f'<rect width="{TW}" height="{TH}" fill="url(#bgGrad)"/>')

    # Compact blueprint grid
    for x in range(0, TW + 1, 42):
        out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{TH}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')
    for y in range(0, TH + 1, 42):
        out.append(f'<line x1="0" y1="{y}" x2="{TW}" y2="{y}" stroke="{GRID}" stroke-width="0.9" opacity="0.15"/>')

    # Olive accent bar
    out.append(f'<line x1="12" y1="0" x2="12" y2="{TH}" stroke="{OLIVE}" stroke-width="3" opacity="0.95"/>')

    g = f'<g {anim_style(delay, 0.45)}>' if not STATIC else '<g>'
    out.append(g)

    # Card surface
    out.append(
        f'<rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1" filter="url(#cardShadow)"/>'
    )
    # Subtle accent tint
    out.append(
        f'<rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16" '
        f'fill="{lnk["accent"]}" opacity="0.07"/>'
    )

    # Lively real-time border beam running around the tile perimeter
    if not STATIC:
        peri = 2 * ((TW - 34) + (TH - 20))  # ≈ 1012 px
        out.append(
            f'<rect x="22" y="10" width="{TW-34}" height="{TH-20}" rx="16" fill="none" '
            f'stroke="url(#beamGrad)" stroke-width="1.8" stroke-dasharray="80 {peri-80}" stroke-linecap="round">'
            f'<animate attributeName="stroke-dashoffset" values="0;-{peri}" dur="3.8s" repeatCount="indefinite"/>'
            f'</rect>'
        )

    # Glancing specular shimmer sheen
    out.append(card_shimmer(22, 10, TW-34, TH-20, clip_id, dur=4.2, delay=delay*1.5))

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

    # Arrow top-right with continuous gentle floating motion
    if not STATIC:
        out.append(
            f'<text x="{TW-26}" y="38" font-family="{SANS}" font-size="20" '
            f'fill="{MUTED}" text-anchor="end" font-weight="600">'
            f'<animateTransform attributeName="transform" type="translate" values="0,0; 2,-2; 0,0" dur="2.4s" repeatCount="indefinite"/>'
            f'↗</text>'
        )
    else:
        out.append(
            f'<text x="{TW-26}" y="38" font-family="{SANS}" font-size="20" '
            f'fill="{MUTED}" text-anchor="end" font-weight="600">↗</text>'
        )

    # Bottom separator + real-time status beacon CTA
    sep_y = TH - 50
    out.append(f'<line x1="36" y1="{sep_y}" x2="{TW-26}" y2="{sep_y}" stroke="{CARD_STR}" stroke-width="1"/>')
    out.append(radar_ping(46, TH - 26, color=OLIVE, dur=2.4))
    out.append(
        f'<text x="58" y="{TH-22}" font-family="{MONO}" font-size="11" font-weight="700" '
        f'fill="{DARK}" letter-spacing="0.5">OPEN ↗</text>'
    )

    out.append("</g>")
    out.append(svg_close())
    return "".join(out)

# ─────────── card 03 · contributions chart ──────────────────────────────────

def render_chart(data: dict, font_uri: str | None) -> str:
    H      = 280
    delay  = CARD_DELAYS["chart"]
    months = data["months"]
    streak = data["streak_days"]
    active = data["active_days_ytd"]
    busy   = data["busiest_day"]
    total  = data["total_ytd"]

    max_c  = max(m["count"] for m in months) or 1
    BAR_MAX_H = 110
    BAR_W  = 48
    LEFT   = 60
    BOTTOM = 200
    BAR_GAP = (W - LEFT - 60 - len(months) * BAR_W) // (len(months) - 1 or 1)

    clip_id = "chartClip"
    extra = f'<clipPath id="{clip_id}"><rect x="{LEFT-10}" y="70" width="{W-LEFT}" height="145"/></clipPath>'

    out = [svg_open(W, H, "Contributions per month")]
    out.append(defs_block(font_uri, extra_defs=extra))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGrad)"/>')
    out.append(grid_lines(W, H))
    out.append(accent_bar(H))

    # Title
    out.append(
        f'<text x="59" y="40" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="{MUTED}" letter-spacing="1.8">02 / CONTRIBUTION ACTIVITY</text>'
    )

    # Stats pills row (right side)
    stats = [
        (f"{streak}d", "STREAK", True),
        (f"{active}", "ACTIVE DAYS", False),
        (busy["date"][-5:], "BUSIEST DAY", False),
        (f"{total}", "TOTAL YTD", False),
    ]
    pw = 170
    for si, (val, lbl, has_ping) in enumerate(stats):
        px = W - 50 - (len(stats)-si) * (pw + 10)
        out.append(
            f'<rect x="{px}" y="12" width="{pw}" height="52" rx="12" '
            f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>'
        )
        if has_ping:
            out.append(radar_ping(px + pw - 18, 22, color=OLIVE, dur=2.0))
        out.append(
            f'<text x="{px+14}" y="34" font-family="{SANS}" font-size="20" '
            f'font-weight="800" fill="{DARK}">{esc(val)}</text>'
        )
        out.append(
            f'<text x="{px+14}" y="52" font-family="{MONO}" font-size="10" '
            f'font-weight="600" fill="{MUTED}" letter-spacing="0.9">{esc(lbl)}</text>'
        )

    # Real-time horizontal laser scan line sweeping across the chart bars
    if not STATIC:
        out.append(
            f'<line x1="{LEFT}" y1="{BOTTOM}" x2="{W-50}" y2="{BOTTOM}" stroke="{LIME}" stroke-width="2" opacity="0.6">'
            f'<animate attributeName="opacity" values="0.2;0.7;0.2" dur="3s" repeatCount="indefinite"/>'
            f'</line>'
        )

    # Bars
    for i, m in enumerate(months):
        bh = int(m["count"] / max_c * BAR_MAX_H)
        bx = LEFT + i * (BAR_W + BAR_GAP)
        by = BOTTOM - bh
        is_peak = m["count"] == max_c
        fill = LIME if is_peak else INNER_BG
        stroke = OLIVE if is_peak else CARD_STR

        g = f'<g {anim_style(delay + i*0.03, 0.4)}>' if not STATIC else '<g>'
        out.append(g)

        # Bar rect
        out.append(
            f'<rect x="{bx}" y="{by}" width="{BAR_W}" height="{bh}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{1.5 if is_peak else 1}">'
        )
        if not STATIC:
            # Initial growth
            out.append(
                f'<animate attributeName="height" from="0" to="{bh}" '
                f'begin="{delay + i*0.03:.2f}s" dur="0.45s" fill="freeze"/>'
                f'<animate attributeName="y" from="{BOTTOM}" to="{by}" '
                f'begin="{delay + i*0.03:.2f}s" dur="0.45s" fill="freeze"/>'
            )
            # Continuous subtle breathing on the peak bar
            if is_peak:
                out.append(
                    f'<animate attributeName="opacity" values="0.88;1;0.88" dur="2.2s" repeatCount="indefinite"/>'
                )
        out.append('</rect>')

        # Peak month glowing crown
        if is_peak and not STATIC:
            out.append(
                f'<ellipse cx="{bx + BAR_W//2}" cy="{by}" rx="{BAR_W//2}" ry="3" fill="{LIME}" opacity="0.7">'
                f'<animate attributeName="opacity" values="0.3;0.85;0.3" dur="2.2s" repeatCount="indefinite"/>'
                f'</ellipse>'
            )

        # Count label
        out.append(
            f'<text x="{bx + BAR_W//2}" y="{by - 6}" '
            f'font-family="{MONO}" font-size="11" font-weight="700" '
            f'fill="{DARK if is_peak else MUTED}" text-anchor="middle">{m["count"]}</text>'
        )
        # Month label
        out.append(
            f'<text x="{bx + BAR_W//2}" y="{BOTTOM + 20}" '
            f'font-family="{MONO}" font-size="11" font-weight="600" '
            f'fill="{MUTED}" text-anchor="middle">{esc(m["label"])}</text>'
        )
        out.append("</g>")

    # Baseline
    out.append(
        f'<line x1="{LEFT-10}" y1="{BOTTOM}" x2="{W-50}" y2="{BOTTOM}" '
        f'stroke="{CARD_STR}" stroke-width="1"/>'
    )

    out.append(svg_close())
    return "".join(out)

# ─────────── card 04 · repo cards ───────────────────────────────────────────

LANG_COLOR = {
    "Python":     "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Rust":       "#DEA584",
    "Go":         "#00ADD8",
}

def render_repo(repo: dict, idx: int, font_uri: str | None) -> str:
    H      = 190
    delay  = CARD_DELAYS["repo"] + idx * 0.12

    CARD_L = 53
    CARD_R = W - 53          # 1227
    CARD_T = 16
    CARD_B = H - 16          # 174
    CARD_W = CARD_R - CARD_L  # 1174
    CARD_H = CARD_B - CARD_T  # 158

    # 72% / 28% two-column split
    DIV_X  = CARD_L + int(CARD_W * 0.72)   # ≈ 898

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

    g = f'<g {anim_style(delay, 0.45)}>' if not STATIC else '<g>'
    out.append(g)

    # Main card surface
    out.append(
        f'<rect x="{CARD_L}" y="{CARD_T}" width="{CARD_W}" height="{CARD_H}" rx="20" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1" filter="url(#cardShadow)"/>'
    )

    # Right panel tinted background
    out.append(
        f'<rect x="{DIV_X}" y="{CARD_T}" width="{CARD_R - DIV_X}" height="{CARD_H}" '
        f'fill="{INNER_BG}" clip-path="url(#{clip_id})"/>'
    )

    # Lively real-time border beam racing along the card perimeter
    if not STATIC:
        card_peri = 2 * (CARD_W + CARD_H)  # ≈ 2664 px
        out.append(
            f'<rect x="{CARD_L}" y="{CARD_T}" width="{CARD_W}" height="{CARD_H}" rx="20" fill="none" '
            f'stroke="url(#beamGrad)" stroke-width="2" stroke-dasharray="140 {card_peri-140}" stroke-linecap="round">'
            f'<animate attributeName="stroke-dashoffset" values="0;-{card_peri}" dur="{5.0 + idx*0.4:.1f}s" repeatCount="indefinite"/>'
            f'</rect>'
        )

    # Glancing specular sheen across the card
    out.append(card_shimmer(CARD_L, CARD_T, CARD_W, CARD_H, clip_id, dur=4.6 + idx*0.3, delay=idx*0.7))

    # Vertical divider line
    out.append(
        f'<line x1="{DIV_X}" y1="{CARD_T + 14}" x2="{DIV_X}" y2="{CARD_B - 14}" '
        f'stroke="{CARD_STR}" stroke-width="1"/>'
    )
    # Real-time data pulse running down the vertical divider
    if not STATIC:
        div_len = CARD_H - 28
        out.append(
            f'<line x1="{DIV_X}" y1="{CARD_T + 14}" x2="{DIV_X}" y2="{CARD_B - 14}" '
            f'stroke="{LIME}" stroke-width="2.5" stroke-dasharray="32 {div_len}" stroke-linecap="round" opacity="0.9">'
            f'<animate attributeName="stroke-dashoffset" values="0;-{div_len+32}" dur="{2.6 + idx*0.3:.1f}s" repeatCount="indefinite"/>'
            f'</line>'
        )

    # ── LEFT PANEL ───────────────────────────────────────────────────────────
    # Number chip
    chip_x, chip_y = CARD_L + 17, CARD_T + 14
    out.append(f'<rect x="{chip_x}" y="{chip_y}" width="32" height="28" rx="8" fill="{LIME}"/>')
    out.append(
        f'<text x="{chip_x + 16}" y="{chip_y + 20}" font-family="{MONO}" font-size="13" '
        f'font-weight="800" fill="{DARK}" text-anchor="middle">{idx+1:02d}</text>'
    )

    # Name
    out.append(
        f'<text x="{CARD_L + 60}" y="{CARD_T + 36}" font-family="{SANS}" font-size="21" '
        f'font-weight="800" fill="{DARK}" letter-spacing="-0.5">{esc(repo["name"])}</text>'
    )

    # Description (wrapped to left panel width)
    max_chars = max(20, int((DIV_X - CARD_L - 70) / 8.3))
    desc_lines = wrap_text(repo["description"], max_chars)
    for li, line in enumerate(desc_lines[:2]):
        out.append(
            f'<text x="{CARD_L + 17}" y="{CARD_T + 68 + li * 21}" '
            f'font-family="{SANS}" font-size="14" font-weight="400" fill="{MUTED}">'
            f'{esc(line)}</text>'
        )

    # Topic chips
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

    # ── RIGHT PANEL ──────────────────────────────────────────────────────────
    RP_TOP = CARD_T + 22

    # Language indicator
    lang_col = LANG_COLOR.get(repo.get("language", ""), MUTED)
    out.append(f'<circle cx="{DIV_X + 24}" cy="{RP_TOP + 7}" r="6" fill="{lang_col}"/>')
    out.append(
        f'<text x="{DIV_X + 38}" y="{RP_TOP + 12}" font-family="{MONO}" font-size="12" '
        f'font-weight="600" fill="{DARK}">{esc(repo.get("language", ""))}</text>'
    )

    # Stars
    out.append(
        f'<text x="{CARD_R - 20}" y="{RP_TOP + 12}" font-family="{MONO}" font-size="13" '
        f'font-weight="800" fill="{DARK}" text-anchor="end">★ {repo.get("stars", 0)}</text>'
    )

    # Horizontal separator
    sep_y = CARD_T + CARD_H // 2
    out.append(
        f'<line x1="{DIV_X + 16}" y1="{sep_y}" x2="{CARD_R - 16}" y2="{sep_y}" '
        f'stroke="{CARD_STR}" stroke-width="1"/>'
    )

    # LIVE and SOURCE buttons
    btn_y    = sep_y + 12
    btn_h    = 32
    rp_inner = CARD_R - DIV_X - 32
    btn_w    = (rp_inner - 8) // 2
    live_x   = DIV_X + 16
    src_x    = live_x + btn_w + 8

    # LIVE button with real-time status radar ping
    out.append(
        f'<rect x="{live_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="14" fill="{LIME}"/>'
    )
    out.append(radar_ping(live_x + 18, btn_y + 16, color=OLIVE, dur=2.0 + idx*0.2))
    out.append(
        f'<text x="{live_x + btn_w // 2 + 6}" y="{btn_y + 21}" font-family="{MONO}" '
        f'font-size="11" font-weight="800" fill="{DARK}" text-anchor="middle">LIVE ↗</text>'
    )

    # SOURCE button
    out.append(
        f'<rect x="{src_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="14" '
        f'fill="{CARD_BG}" stroke="{CARD_STR}" stroke-width="1"/>'
    )
    out.append(
        f'<text x="{src_x + btn_w // 2}" y="{btn_y + 21}" font-family="{MONO}" '
        f'font-size="11" font-weight="700" fill="{MUTED}" text-anchor="middle">SOURCE ↗</text>'
    )

    out.append("</g>")
    out.append(svg_close())
    return "".join(out)

# ─────────── card 05 · contribution graph ────────────────────────────────────

def render_graph(data: dict, font_uri: str | None) -> str:
    """Render a living GitHub-style contribution heatmap in brand colours."""
    H       = 180
    delay   = CARD_DELAYS["graph"]
    weeks   = data.get("graph_weeks", [])
    CELL    = 14
    GAP     = 3
    GRID_X  = 60
    GRID_Y  = 50
    DAYS    = ["Mon","","Wed","","Fri","","Sun"]
    max_val = max((v for w in weeks for v in w), default=1)

    clip_id = "graphClip"
    extra = f'<clipPath id="{clip_id}"><rect x="{GRID_X-4}" y="{GRID_Y-4}" width="{len(weeks)*(CELL+GAP)+8}" height="7*(CELL+GAP)+8"/></clipPath>'

    # Colour scale: 0 → deep dark slate, low → light lime, high → OLIVE
    def cell_color(v: int) -> str:
        if v == 0:
            return "#1E241B"      # dark muted cell
        t = v / max_val
        if t < 0.25:
            return "#D7FF68"      # electric lime
        if t < 0.50:
            return "#B8E04A"
        if t < 0.75:
            return "#92B346"      # olive
        return "#7A9933"          # deep olive

    out = [svg_open(W, H, "Contribution graph")]
    out.append(defs_block(font_uri, extra_defs=extra))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bgGradDark)"/>')

    # Grid background lines
    for gx in range(0, W + 1, 64):
        out.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="#FFFFFF" stroke-width="0.8" opacity="0.04"/>')
    for gy in range(0, H + 1, 30):
        out.append(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="#FFFFFF" stroke-width="0.8" opacity="0.04"/>')

    # Title with active radar status dot
    out.append(
        f'<text x="59" y="34" font-family="{MONO}" font-size="13" font-weight="700" '
        f'fill="#C6D5B2" letter-spacing="1.8">05 / CONTRIBUTION GRAPH</text>'
    )
    out.append(radar_ping(W - 80, 30, color=LIME, dur=2.5))
    out.append(
        f'<text x="{W - 95}" y="34" font-family="{MONO}" font-size="10" font-weight="700" '
        f'fill="#C6D5B2" letter-spacing="1.0" text-anchor="end">LIVE FEED</text>'
    )

    g = f'<g {anim_style(delay, 0.5)}>' if not STATIC else '<g>'
    out.append(g)

    # Render heatmap cells
    for wi, week in enumerate(weeks):
        for di, val in enumerate(week):
            cx = GRID_X + wi * (CELL + GAP)
            cy = GRID_Y + di * (CELL + GAP)
            col = cell_color(val)
            out.append(
                f'<rect x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{col}" opacity="0.95"/>'
            )
            # Continuous subtle glimmer on peak contribution days
            if val == max_val and not STATIC:
                out.append(
                    f'<rect x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="3" fill="{LIME}" opacity="0">'
                    f'<animate attributeName="opacity" values="0;0.55;0" dur="{2.0 + (wi%3)*0.5:.1f}s" repeatCount="indefinite"/>'
                    f'</rect>'
                )

    # Continuous real-time luminous energy wave sweeping across the contribution cells
    if not STATIC:
        grid_w = len(weeks) * (CELL + GAP)
        out.append(
            f'<rect x="{GRID_X - 250}" y="{GRID_Y - 2}" width="240" height="{7 * (CELL + GAP)}" '
            f'fill="url(#heatSweep)" opacity="0.45" clip-path="url(#{clip_id})">'
            f'<animate attributeName="x" values="{GRID_X - 250};{GRID_X + grid_w + 100}" dur="5.5s" repeatCount="indefinite"/>'
            f'</rect>'
        )

    # Day labels
    for di, lbl in enumerate(DAYS):
        if lbl:
            cy = GRID_Y + di * (CELL + GAP) + CELL - 2
            out.append(
                f'<text x="{GRID_X - 8}" y="{cy}" font-family="{MONO}" font-size="9" '
                f'font-weight="600" fill="#B5B9AF" text-anchor="end">{lbl}</text>'
            )

    out.append("</g>")

    # Legend
    lx = W - 220
    out.append(f'<text x="{lx}" y="{H-16}" font-family="{MONO}" font-size="10" fill="#B5B9AF">Less</text>')
    for li, col in enumerate(["#1E241B", "#D7FF68", "#B8E04A", "#92B346", "#7A9933"]):
        out.append(
            f'<rect x="{lx+42+li*18}" y="{H-28}" width="{CELL}" height="{CELL}" rx="3" fill="{col}"/>'
        )
    out.append(f'<text x="{lx+42+5*18 + 6}" y="{H-16}" font-family="{MONO}" font-size="10" fill="#B5B9AF">More</text>')

    out.append(svg_close())
    return "".join(out)

# ─────────── README writer ───────────────────────────────────────────────────

def build_readme(repos: list[dict]) -> str:
    """Regenerate README.md using img tags pointing at cards/."""
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

# ─────────── main ────────────────────────────────────────────────────────────

def main():
    OUT.mkdir(exist_ok=True)
    data   = load_data()
    repos  = data["repos"]
    mode   = "STATIC" if STATIC else "ANIMATED (LIVELY REAL-TIME)"
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

    # 02 link tiles (three separate narrow SVGs)
    link_delay = CARD_DELAYS["links"]
    for lnk in LINKS:
        path = OUT / f"02-link-{lnk['slug']}.svg"
        path.write_text(render_link_tile(lnk, link_delay, font_uri), encoding="utf-8")
        cards.append(str(path))
        print(f"   ✓ {path.name}")
        link_delay += 0.12

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
    if STATIC:
        print("   Run without STATIC=1 to get animated versions.")

if __name__ == "__main__":
    main()
