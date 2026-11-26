#!/usr/bin/env python3
"""Render this README's Markdown/HTML subset locally, without dependencies or uploads.

This is a visual approximation of GitHub's README styling, not its sanitizer.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def inline(value):
    value = escape(value)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)


def render_readme(markdown):
    out, in_table = [], False
    for line in markdown.splitlines():
        if line.startswith('|'):
            cells = [x.strip() for x in line.strip('|').split('|')]
            if not in_table:
                out.append('<table><thead><tr>' + ''.join(f'<th>{inline(x)}</th>' for x in cells) + '</tr></thead><tbody>')
                in_table = True
            elif not all(re.fullmatch(r':?-+:?', x) for x in cells):
                out.append('<tr>' + ''.join(f'<td>{inline(x)}</td>' for x in cells) + '</tr>')
            continue
        if in_table:
            out.append('</tbody></table>')
            in_table = False
        heading = re.fullmatch(r'(#{1,6}) (.+)', line)
        if heading:
            level = len(heading[1])
            ident = re.sub(r'[^a-z0-9 -]', '', heading[2].lower()).replace(' ', '-')
            out.append(f'<h{level} id="{ident}">{inline(heading[2])}</h{level}>')
        elif line.startswith('> ### '):
            out.append(f'<blockquote><h3>{inline(line[6:])}</h3></blockquote>')
        elif line.startswith('> '):
            out.append(f'<blockquote><p>{inline(line[2:])}</p></blockquote>')
        elif not line.strip() or line.lstrip().startswith('<'):
            out.append(line)
        else:
            out.append(f'<p>{inline(line)}</p>')
    if in_table:
        out.append('</tbody></table>')
    return '\n'.join(out)


CSS = '''
*{box-sizing:border-box}body{margin:0;background:#0d1117;color:#e6edf3;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;padding:40px 20px 70px}
main{max-width:860px;margin:auto;border:1px solid #30363d;border-radius:12px;overflow:hidden}
header{padding:14px 24px;border-bottom:1px solid #30363d;background:#161b22;color:#8b949e;font-size:13px;display:flex;align-items:center;gap:12px}header strong{color:#e6edf3}header span:last-child{margin-left:auto;color:#c9d1d9}
article{padding:32px 40px}h1,h2,h3{line-height:1.25;font-weight:600}h1{font-size:32px;margin:8px 0 18px;padding-bottom:16px;border-bottom:1px solid #30363d}h2{font-size:24px;margin:28px 0 16px;padding-bottom:9px;border-bottom:1px solid #30363d}h3{font-size:20px;margin:24px 0 16px}p{margin:0 0 18px}img{max-width:100%;vertical-align:middle;height:auto}img[height="24"]{height:24px}img[height="42"]{height:42px}img[height="40"]{height:40px}a{color:#58a6ff;text-decoration:none}a:hover{text-decoration:underline}blockquote{padding:0 16px;border-left:3px solid #3d4944;margin:0 0 18px;color:#b5c0cb}blockquote h3{color:#e6edf3;padding:2px 0 9px;border-bottom:1px solid #30363d}blockquote p{font-size:14px;padding:2px 0}table{border-collapse:collapse;font-size:14px;margin:20px 0;width:100%}td,th{border:1px solid #30363d;padding:8px 12px;text-align:left}tr:nth-child(2n){background:#161b22}details{margin:28px 0 22px}summary{cursor:pointer}sub{font-size:12px;color:#8b949e}article>p:last-child{margin-top:25px;margin-bottom:8px}
@media(max-width:560px){body{padding:12px 8px 30px}article{padding:22px 16px}header{padding:12px 16px}h1{font-size:25px}h2{font-size:21px}h3{font-size:18px}img[height="42"]{width:36px;height:36px}table{font-size:11px}td,th{padding:5px}}
'''


def main():
    body = render_readme((ROOT/'README.md').read_text())
    page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Vittal · README preview</title><style>{CSS}</style></head>
<body><main><header><strong>◉</strong><span>vittal-17 / <strong>README.md</strong></span><span>Preview</span></header><article>{body}</article></main></body></html>'''
    (ROOT/'preview.html').write_text(page + '\n')
    print('Wrote preview.html from README.md (local rendering).')


if __name__ == '__main__':
    main()
