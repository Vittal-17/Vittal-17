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
BLUE = '#58a6ff'
MUTED = '#909ba7'
TEXT = '#e3eaf2'
PURPLE = '#c792ea'
LEVELS = ['#232b32', '#28485e', '#31658c', '#4089c8', BLUE]
LANG_COLORS = {'Python': '#5197c3', 'Jupyter Notebook': '#ef7651',
               'JavaScript': '#f1e05a', 'TypeScript': '#4b8dd0',
               'CSS': '#a365d9', 'HTML': '#e76a47', 'Other': '#8b949e'}


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


def shell(w, h, title, body, *, inner=True):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">Public GitHub data for {USER}. Generated locally; no external image service required.</desc>
<defs>
 <linearGradient id="base" x2="0.8" y2="1"><stop stop-color="#1b242e"/><stop offset="1" stop-color="#20232c"/></linearGradient>
 <radialGradient id="blue"><stop stop-color="#408ee6" stop-opacity=".34"/><stop offset="1" stop-color="#408ee6" stop-opacity="0"/></radialGradient>
 <radialGradient id="green"><stop stop-color="#22b86a" stop-opacity=".21"/><stop offset="1" stop-color="#22b86a" stop-opacity="0"/></radialGradient>
 <radialGradient id="violet"><stop stop-color="#a569e8" stop-opacity=".32"/><stop offset="1" stop-color="#a569e8" stop-opacity="0"/></radialGradient>
 <radialGradient id="cyan"><stop stop-color="#009cb8" stop-opacity=".23"/><stop offset="1" stop-color="#009cb8" stop-opacity="0"/></radialGradient>
 <clipPath id="clip">{rect(1,1,w-2,h-2,'white',23)}</clipPath>
</defs>
<style>text{{font-family:Arial,Helvetica,sans-serif}}.snake-still{{display:none}}@media(prefers-reduced-motion:reduce){{.snake-motion{{display:none}}.snake-still{{display:inline}}}}</style>
{rect(1,1,w-2,h-2,'url(#base)',23,'#478cd1',extra='stroke-opacity=".85"')}
<g clip-path="url(#clip)">
 <ellipse cx="{w*.19}" cy="{h*.10}" rx="{w*.32}" ry="{h*.70}" fill="url(#blue)"/>
 <ellipse cx="{w*.78}" cy="{h*.20}" rx="{w*.33}" ry="{h*.86}" fill="url(#green)"/>
 <ellipse cx="{w*.64}" cy="{h*1.1}" rx="{w*.38}" ry="{h*.65}" fill="url(#violet)"/>
 <ellipse cx="{w*1.02}" cy="{h*.90}" rx="{w*.30}" ry="{h*.70}" fill="url(#cyan)"/>
</g>
{rect(32,30,w-64,h-60,'#101619',24,'#386b96',extra='fill-opacity=".69"') if inner else ''}
{body}
</svg>'''


def updated_label(data):
    return 'Updated ' + date.fromisoformat(data['_updated']).strftime('%d %b %Y')


def signal_card(a, p):
    body = text(31, 39, 'Profile Signal', 21, weight=700)
    body += text(31, 57, updated_label(p), 10, MUTED)
    items = [('Stars', p['stars'], BLUE), ('Contributions', a['total'], '#42cfdb'),
             ('Repos', p['public_repos'], '#b482ef'), ('Followers', p['followers'], '#4bd282')]
    for i, (label, value, color) in enumerate(items):
        x = 31 + i*108
        body += rect(x, 70, 101, 84, '#11181c', 12, '#3c6386', extra='fill-opacity=".88"')
        body += text(x+12, 91, label, 10, MUTED)
        body += text(x+12, 124, f'{value:,}', 25, color, 700)
        body += rect(x+12, 136, 77, 4, '#29313a', 2)
        body += rect(x+12, 136, 13 if value else 0, 4, color, 2)
    return shell(490, 185, 'Profile Signal: stars, contributions, repositories and followers', body, inner=False)


def streak_card(a):
    body = ''
    for x in (161, 329):
        body += f'<path d="M{x} 31V149" stroke="#465362"/>'
    body += f'<circle cx="245" cy="79" r="39" fill="none" stroke="{PURPLE}" stroke-width="5" stroke-dasharray="225 20" transform="rotate(-74 245 79)"/>'
    # A tiny flame above the ring.
    body += f'<path d="M245 27c-9 9-5 15 1 15s11-7 3-16c1 7-5 7-4 1Z" fill="{PURPLE}"/>'
    body += text(80, 86, f'{a["total"]:,}', 29, PURPLE, 700, 'middle')
    body += text(80, 119, 'Year contributions', 12, PURPLE, anchor='middle')
    body += text(245, 89, a['current_streak'], 30, '#ffe58b', 700, 'middle')
    body += text(245, 146, 'Current streak', 13, '#ffe58b', 700, 'middle')
    body += text(410, 86, a['longest_streak'], 29, PURPLE, 700, 'middle')
    body += text(410, 119, 'Best streak', 12, PURPLE, anchor='middle')
    body += text(245, 170, 'Streaks in days · last 12 months', 10, MUTED, anchor='middle')
    return shell(490, 185, 'Contributions and daily streaks over the last 12 months', body, inner=False)


def language_rows(p):
    pairs = list(p['languages'].items())
    total = sum(v for _, v in pairs)
    if not total:
        return []
    # Keep every byte accounted for, including less-used languages.
    if len(pairs) > 5:
        pairs = pairs[:5] + [('Other', sum(v for _, v in pairs[5:]))]
    return [(name, value/total*100) for name, value in pairs]


def languages_card(p):
    rows = language_rows(p)
    h = 140 + max(len(rows), 1)*37
    body = text(52, 71, 'Language Stack', 31, weight=700)
    body += text(54, 96, 'Code across public source repositories', 15, MUTED)
    body += text(930, 71, '> stack.scan', 15, BLUE, 700, 'end')
    if not rows:
        body += text(54, 135, 'No language data available yet.', 18, MUTED)
    for i, (name, value) in enumerate(rows):
        y = 127 + i*37
        color = LANG_COLORS.get(name, BLUE)
        body += f'<circle cx="62" cy="{y-5}" r="6" fill="{color}"/>'
        body += text(83, y, name, 16, weight=600)
        body += text(322, y, f'{value:.1f}%', 15, color, anchor='end')
        body += rect(350, y-15, 545, 10, '#303b40', 5)
        body += rect(350, y-15, round(545*value/100, 2), 10, color, 5)
    return shell(1000, h, 'Language Stack: ' + ', '.join(f'{n} {v:.1f}%' for n, v in rows), body)


def highlights_card(p):
    body = text(35, 50, 'H I G H L I G H T S', 12, MUTED, 700)
    for i, (heading, caption, color) in enumerate([
        ('Open Source', f'{p["public_repos"]} public repositories', BLUE),
        ('Impact', f'{p["stars"]} stars earned', '#38cc7b'),
        ('Community', f'{p["followers"]} ' + ('follower' if p['followers']==1 else 'followers'), '#ad74ed'),
    ]):
        x = 33 + i*319
        body += rect(x, 70, 301, 111, '#11181c', 19, '#4c8fce', extra='fill-opacity=".68"')
        body += rect(x, 97, 4, 59, color, 1)
        body += text(x+28, 113, heading, 19, weight=700)
        body += text(x+28, 143, caption, 15, MUTED)
    return shell(1000, 210, 'Highlights: open source, impact and community', body, inner=False)


def grid(a, x=54, y=116, width=870):
    weeks = a['weeks']
    pitch = width / max(len(weeks), 1)
    size = min(pitch-3, 14)
    body, active = '', []
    for col, week in enumerate(weeks):
        for row, d in enumerate(week):
            if d['date'] > a['period_end']:
                continue
            px, py = x+col*pitch, y+row*pitch
            color = LEVELS[max(0, min(4, d['level']))]
            body += rect(round(px,2), round(py,2), round(size,2), round(size,2), color, 2)
            if d['count']:
                active.append((round(px+size/2,2), round(py+size/2,2)))
    return body, active, y + 6*pitch + size


def activity_card(a):
    body = text(52, 70, 'Contribution Activity', 29, weight=700)
    body += text(54, 98, f'{a["total"]:,} contributions in the last year', 16, MUTED)
    body += text(727, 83, 'Less', 12, MUTED)
    for i, color in enumerate(LEVELS):
        body += rect(765+i*18, 72, 13, 13, color, 2)
    body += text(861, 83, 'More', 12, MUTED)
    cells, _, bottom = grid(a)
    body += cells
    h = round(bottom+58)
    body += text(946, h-13, updated_label(a), 11, MUTED, anchor='end')
    return shell(1000, h, 'Contribution Activity: ' + str(a['total']) + ' contributions in the last year', body)


def snake_card(a):
    body = text(54, 67, 'S N A K E   T R A I L', 12, BLUE, 700)
    body += text(54, 96, f'{a["total"]:,} contributions, one continuous run', 23, weight=700)
    body += text(943, 69, 'KEEP BUILDING', 11, '#bbdbff', anchor='end', extra='letter-spacing="1.5"')
    cells, active, bottom = grid(a, y=122)
    body += cells
    if active:
        # Traverse the real active cells with orthogonal turns, then close the loop.
        first_x, first_y = active[0]
        route = 'M0 0 '
        for x, y in active[1:] + active[:1]:
            route += f'H{round(x-first_x,2)} V{round(y-first_y,2)} '
        head = (rect(-7,-7,15,15,'#b9e3ff',5) + rect(2,-4,2,3,'#183950',1)
                + rect(2,2,2,3,'#183950',1))
        still_x, still_y = active[-1]
        body += f'<g class="{"" if STATIC else "snake-still"}" transform="translate({still_x} {still_y})">{head}</g>'
        if not STATIC:
            body += f'<g class="snake-motion" transform="translate({first_x} {first_y})">'
            for i in range(5, 0, -1):
                body += (f'<g opacity="{1-i*.12}"><circle r="{6-i*.5}" fill="#79c6ff"/>'
                         f'<animateMotion path="{route}" dur="32s" begin="{i*.16}s" repeatCount="indefinite"/></g>')
            body += f'<g>{head}<animateMotion path="{route}" dur="32s" repeatCount="indefinite" rotate="auto"/></g></g>'
    h = round(bottom+72)
    body += text(54, h-39, 'Small commits. Steady progress.', 13, MUTED)
    body += text(946, h-13, updated_label(a), 11, MUTED, anchor='end')
    return shell(1000, h, 'Animated snake following real contribution activity', body)


def render(a, p):
    OUT.mkdir(exist_ok=True)
    cards = {'signal.svg': signal_card(a,p), 'streak.svg': streak_card(a),
             'languages.svg': languages_card(p), 'highlights.svg': highlights_card(p),
             'activity.svg': activity_card(a), 'snake.svg': snake_card(a)}
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
