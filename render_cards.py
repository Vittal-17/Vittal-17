#!/usr/bin/env python3
"""Build the profile's SVG cards from public GitHub data (Python stdlib only).

Run: python3 render_cards.py             # refresh public data and render
     python3 render_cards.py --offline   # render the saved snapshot
     STATIC=1 python3 render_cards.py --offline  # no motion
README.md is hand-authored and is never modified by this script.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'contributions.json'
PROFILE = ROOT / 'profile-data.json'
OUT = ROOT / 'cards'
USER = 'Vittal-17'
STATIC = os.environ.get('STATIC') == '1'
ACCENT = '#9bc4b0'
MUTED = '#9aa7a0'
TEXT = '#e5ebe7'
SURFACE = '#161c19'
BORDER = '#303b35'
TRACK = '#29332d'
LEVELS = ['#26302a', '#354f40', '#4d705a', '#739b7f', ACCENT]


def request(url: str, *, api: bool = False) -> str:
    headers = {'User-Agent': f'{USER}-profile-readme'}
    if api:
        headers['Accept'] = 'application/vnd.github+json'
        headers['X-GitHub-Api-Version'] = '2022-11-28'
        # Never send credentials to the HTML endpoint or third-party hosts.
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        return response.read().decode('utf-8')


def api(path: str):
    return json.loads(request(f'https://api.github.com/{path}', api=True))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


class CalendarParser(HTMLParser):
    """Associate cells and tooltip counts independently of HTML attribute order."""
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tooltips = {}
        self.target = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'ContributionCalendar-day' in attrs.get('class', '').split():
            if attrs.get('data-date') and attrs.get('id'):
                self.cells[attrs['id']] = {
                    'date': attrs['data-date'],
                    'level': int(attrs.get('data-level', 0)),
                }
        if tag == 'tool-tip':
            self.target = attrs.get('for')
            if self.target:
                self.tooltips[self.target] = ''

    def handle_data(self, data):
        if self.target:
            self.tooltips[self.target] += data

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.target = None


def parse_calendar(html: str) -> list[dict]:
    parser = CalendarParser()
    parser.feed(html)
    days = []
    for ident, cell in parser.cells.items():
        tooltip = parser.tooltips.get(ident, '')
        match = re.search(r'([\d,]+)\s+contributions?\b', tooltip)
        if match:
            count = int(match[1].replace(',', ''))
        elif re.search(r'\bNo contributions?\b', tooltip, re.I):
            count = 0
        else:
            # Changed markup must preserve the last good snapshot, not zero it.
            raise ValueError(f'Missing contribution count for {cell["date"]}')
        days.append({**cell, 'count': count})
    if not days:
        raise ValueError('No contribution calendar cells found')
    return sorted(days, key=lambda d: d['date'])


def calendar_stats(days: list[dict], today: date) -> dict:
    days = sorted((d for d in days if date.fromisoformat(d['date']) <= today),
                  key=lambda d: d['date'])
    if not days:
        raise ValueError('No past contribution days found')
    # Fill gaps so streaks cannot bridge a missing date.
    lookup = {d['date']: d for d in days}
    start = date.fromisoformat(days[0]['date'])
    complete = []
    day = start
    while day <= today:
        ds = day.isoformat()
        complete.append(lookup.get(ds, {'date': ds, 'count': 0, 'level': 0}))
        day += timedelta(days=1)
    longest = running = 0
    for d in complete:
        running = running + 1 if d['count'] else 0
        longest = max(longest, running)
    # An unfinished today does not break yesterday's ongoing streak.
    cursor = today
    if not lookup.get(cursor.isoformat(), {}).get('count', 0):
        cursor -= timedelta(days=1)
    current = 0
    while lookup.get(cursor.isoformat(), {}).get('count', 0):
        current += 1
        cursor -= timedelta(days=1)
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    weeks = []
    cursor = sunday
    while cursor <= today:
        week = []
        for _ in range(7):
            ds = cursor.isoformat()
            week.append(lookup.get(ds, {'date': ds, 'count': 0, 'level': 0}))
            cursor += timedelta(days=1)
        weeks.append(week)
    return {
        '_note': 'Public GitHub contribution calendar; streaks cover the displayed period.',
        '_updated': today.isoformat(),
        'total': sum(d['count'] for d in complete),
        'current_streak': current,
        'longest_streak': longest,
        'active_days': sum(bool(d['count']) for d in complete),
        'period_start': days[0]['date'],
        'period_end': today.isoformat(),
        'days': complete,
        'weeks': weeks,
    }


def profile_stats(user: dict, repos: list[dict], languages: list[dict]) -> dict:
    totals = Counter()
    for counts in languages:
        totals.update(counts)
    source_repos = [r for r in repos if not r['fork']]
    return {
        '_updated': datetime.now(timezone.utc).date().isoformat(),
        'login': user['login'], 'created_at': user['created_at'][:10],
        'public_repos': user['public_repos'], 'followers': user['followers'],
        'stars': sum(r['stargazers_count'] for r in source_repos),
        'languages': dict(totals.most_common()),
        'language_basis': 'Bytes across public, non-fork repositories',
        'source_repos': len(source_repos),
    }


def refresh() -> tuple[dict, dict]:
    activity, profile = read_json(DATA), read_json(PROFILE)
    try:
        days = parse_calendar(request(f'https://github.com/users/{USER}/contributions'))
        today = datetime.now(timezone.utc).date()
        activity = calendar_stats(days, today)
        save_json(DATA, activity)
        print(f'Activity: {activity["total"]} contributions; {activity["current_streak"]}-day streak')
    except Exception as exc:
        print(f'Activity refresh failed ({exc}); keeping saved snapshot.', file=sys.stderr)
    try:
        user = api(f'users/{USER}')
        repos, page = [], 1
        while True:
            batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        languages = [api(f'repos/{USER}/{r["name"]}/languages') for r in repos if not r['fork']]
        profile = profile_stats(user, repos, languages)
        save_json(PROFILE, profile)
        print(f'Profile: {profile["public_repos"]} repositories; {profile["stars"]} stars')
    except Exception as exc:
        print(f'Profile refresh failed ({exc}); keeping saved snapshot.', file=sys.stderr)
    if not activity or not profile:
        raise RuntimeError('No saved snapshot available. Run once with network access.')
    return activity, profile


def text(x, y, value, size=18, fill=TEXT, weight=400, anchor='start', extra=''):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(str(value))}</text>')


def rect(x, y, w, h, fill, rx=0, stroke='none', extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" {extra}/>'


def shell(w, h, title, body):
    """One quiet surface; the data carries the accent, not the frame."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">Public GitHub data for {USER}. Generated locally from saved snapshots.</desc>
<style>
text{{font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums}}
.meta{{font-family:Consolas,"Liberation Mono",monospace}}
.snake-still{{display:none}}
@media(prefers-reduced-motion:reduce){{.snake-motion{{display:none}}.snake-still{{display:inline}}}}
</style>
{rect(1, 1, w-2, h-2, SURFACE, 12, BORDER)}
{body}
</svg>'''


def updated_label(data):
    return 'Updated ' + date.fromisoformat(data['_updated']).strftime('%d %b %Y')


def language_rows(p):
    pairs = list(p['languages'].items())
    total = sum(v for _, v in pairs)
    if not total:
        return []
    # Keep every byte accounted for, including less-used languages.
    if len(pairs) > 5:
        pairs = pairs[:5] + [('Other', sum(v for _, v in pairs[5:]))]
    return [(name, value/total*100) for name, value in pairs]


def languages_card(p, *, compact=False):
    rows = language_rows(p)
    w = 400 if compact else 900
    step = 36 if compact else 32
    h = 112 + max(len(rows), 1)*step
    body = text(24, 40, 'Languages', 24, weight=600)
    if compact:
        body += text(24, 68, 'Public repositories · by code size', 16, MUTED)
    else:
        body += text(w-24, 40, 'Public repositories · by code size', 16, MUTED, anchor='end')
    if not rows:
        body += text(24, 104, 'No language data available yet', 16, MUTED)
    for i, (name, value) in enumerate(rows):
        y = 104 + i*step
        x = 202 if compact else 248
        bar_w = 104 if compact else 532
        body += text(24, y, name, 17, weight=500)
        body += rect(x, y-10, bar_w, 4, TRACK, 2)
        body += rect(x, y-10, round(bar_w*value/100, 2), 4,
                     ACCENT if i == 0 else '#73877a', 2)
        body += text(w-24, y, f'{value:.1f}%', 16, MUTED, anchor='end', extra='class="meta"')
    title = 'Languages: ' + ', '.join(f'{n} {v:.1f}%' for n, v in rows)
    return shell(w, h, title, body)


def grid(a, *, compact=False, y=164):
    """A Sunday-first calendar; mobile shows the most recent 26 weeks."""
    weeks = a['weeks'][-26:] if compact else a['weeks']
    w = 400 if compact else 900
    pitch = (w-48) / max(len(weeks), 1)
    size = max(1, min(pitch-3, 13))
    body, active = '', []
    last_month = None
    last_label_col = -3
    for col, week in enumerate(weeks):
        first = date.fromisoformat(week[0]['date'])
        month = (first.year, first.month)
        # Leave enough room for the label after a month boundary.
        if month != last_month:
            next_month_soon = col == 0 and any(
                date.fromisoformat(wk[0]['date']).month != first.month
                for wk in weeks[1:3]
            )
            if not next_month_soon and col-last_label_col >= 3 and col < len(weeks)-2:
                body += text(round(24+col*pitch, 2), y-12, first.strftime('%b'), 15, MUTED)
                last_label_col = col
            last_month = month
        for row, d in enumerate(week):
            if d['date'] > a['period_end']:
                continue
            px, py = 24+col*pitch, y+row*pitch
            color = LEVELS[max(0, min(4, d['level']))]
            body += rect(round(px, 2), round(py, 2), round(size, 2), round(size, 2), color, 2)
            if d['count']:
                active.append((round(px+size/2, 2), round(py+size/2, 2)))
    return body, active, y + 6*pitch + size


def activity_card(a, p, *, compact=False):
    w = 400 if compact else 900
    body = text(24, 40, 'GitHub activity', 24, weight=600)
    body += text(24, 100, f'{a["total"]:,}', 48, ACCENT, 500)
    body += text(132, 78, 'contributions', 17, MUTED)
    body += text(132, 102, 'in the last year', 17, MUTED)
    stats_y = 150 if compact else 72
    labels_y = stats_y+24
    for i, (label, value) in enumerate([
        ('Public repos', p['public_repos']), ('Stars', p['stars']), ('Followers', p['followers'])
    ]):
        x = 24 + i*120 if compact else 524 + i*124
        body += text(x, stats_y, f'{value:,}', 26, weight=500)
        body += text(x, labels_y, label, 16, MUTED)
    if compact:
        body += text(24, 214, f'{a["active_days"]} active days', 16, MUTED)
        body += text(24, 240, f'{a["current_streak"]}-day streak · {a["longest_streak"]}-day best', 16, MUTED)
        grid_y = 288
    else:
        body += text(24, 140, f'{a["active_days"]} active days   ·   {a["current_streak"]}-day current streak   ·   {a["longest_streak"]}-day best streak', 16, MUTED)
        grid_y = 188
    cells, _, bottom = grid(a, compact=compact, y=grid_y)
    body += cells
    h = round(bottom+64)
    if compact:
        body += text(24, h-36, 'Calendar: last 26 weeks', 15, MUTED)
        body += text(24, h-14, updated_label(a), 15, MUTED)
        # Profile and calendar can refresh independently when one source fails.
        if p['_updated'] != a['_updated']:
            h += 24
            body += text(24, h-14, 'Profile: ' + p['_updated'], 15, MUTED)
    else:
        body += text(24, h-24, 'Last 12 months', 15, MUTED)
        body += text(w-24, h-24, updated_label(a), 15, MUTED, anchor='end')
        if p['_updated'] != a['_updated']:
            h += 24
            body += text(w-24, h-16, 'Profile updated ' + p['_updated'], 15, MUTED, anchor='end')
    return shell(w, h, f'GitHub activity: {a["total"]:,} contributions, {p["public_repos"]} public repositories, {p["stars"]} stars and {p["followers"]} followers', body)


def snake_card(a, *, compact=False):
    w = 400 if compact else 900
    body = text(24, 40, 'The contribution trail', 24, weight=600)
    body += text(24, 72, f'{a["total"]:,} contributions in the last year', 16, MUTED)
    cells, active, bottom = grid(a, compact=compact, y=120)
    body += cells
    if active:
        # Follow real active cells with orthogonal turns, at a constant pace.
        first_x, first_y = active[0]
        route = 'M0 0 '
        for x, y in active[1:] + active[:1]:
            route += f'H{round(x-first_x, 2)} V{round(y-first_y, 2)} '
        head = (rect(-6, -6, 12, 12, '#d6e4d8', 3)
                + rect(1, -3, 2, 2, '#26342a', 1)
                + rect(1, 1, 2, 2, '#26342a', 1))
        still_x, still_y = active[-1]
        static_class = '' if STATIC else 'snake-still'
        body += f'<g class="{static_class}" transform="translate({still_x} {still_y})">{head}</g>'
        if not STATIC:
            body += f'<g class="snake-motion" transform="translate({first_x} {first_y})">'
            for i in range(4, 0, -1):
                body += (f'<g opacity="{1-i*.14}">{rect(-4, -4, 8, 8, ACCENT, 2)}'
                         f'<animateMotion path="{route}" dur="40s" begin="{i*.16}s" repeatCount="indefinite"/></g>')
            body += f'<g>{head}<animateMotion path="{route}" dur="40s" repeatCount="indefinite" rotate="auto"/></g></g>'
    h = round(bottom+64)
    if compact:
        body += text(24, h-36, 'Last 26 weeks · one commit at a time', 15, MUTED)
        body += text(24, h-14, updated_label(a), 15, MUTED)
    else:
        body += text(24, h-24, 'One commit at a time', 15, MUTED)
        body += text(w-24, h-24, updated_label(a), 15, MUTED, anchor='end')
    return shell(w, h, 'Animated snake following real contribution activity', body)


def render(a, p):
    OUT.mkdir(exist_ok=True)
    cards = {}
    for compact in (False, True):
        suffix = '-mobile.svg' if compact else '.svg'
        cards['activity'+suffix] = activity_card(a, p, compact=compact)
        cards['languages'+suffix] = languages_card(p, compact=compact)
        cards['snake'+suffix] = snake_card(a, compact=compact)
    for name, svg in cards.items():
        (OUT / name).write_text(svg + '\n')
    print(f'Rendered {len(cards)} SVG cards.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Use saved JSON, without network requests')
    args = parser.parse_args()
    activity, profile = (read_json(DATA), read_json(PROFILE)) if args.offline else refresh()
    if not activity or not profile:
        parser.error('Missing data. Run once without --offline.')
    render(activity, profile)


if __name__ == '__main__':
    main()
