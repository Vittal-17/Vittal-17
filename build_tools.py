#!/usr/bin/env python3
"""Build compact, local brand badges in GitHub-safe SVG images.

One image keeps each icon and its name together when a README row wraps.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
LABELS = {
    'javascript': 'JavaScript', 'typescript': 'TypeScript', 'python': 'Python',
    'react': 'React', 'nextjs': 'Next.js', 'html5': 'HTML5', 'css3': 'CSS3',
    'tailwindcss': 'Tailwind CSS', 'threejs': 'Three.js', 'fastapi': 'FastAPI',
    'django': 'Django REST', 'flask': 'Flask', 'convex': 'Convex',
    'postgresql': 'PostgreSQL', 'mongodb': 'MongoDB Atlas', 'mysql': 'MySQL',
    'sqlite': 'SQLite', 'docker': 'Docker', 'oracle': 'Oracle Cloud',
    'githubactions': 'GitHub Actions', 'vercel': 'Vercel', 'civo': 'Civo Cloud',
    'render': 'Render', 'jupyter': 'Jupyter Notebook', 'scikitlearn': 'scikit-learn',
    'git': 'Git', 'vscode': 'VS Code', 'postman': 'Postman', 'linux': 'Linux',
}

COLORS = {
    'javascript': '#f7df1e', 'typescript': '#3178c6', 'python': '#3776ab',
    'react': '#087ea4', 'nextjs': '#25282b', 'html5': '#e34f26', 'css3': '#1572b6',
    'tailwindcss': '#0e7490', 'threejs': '#313438', 'fastapi': '#008577',
    'django': '#0c4b33', 'flask': '#313438', 'convex': '#7a2d59',
    'postgresql': '#4169e1', 'mongodb': '#137d3a', 'mysql': '#00618a',
    'sqlite': '#14536f', 'docker': '#1d63ed', 'oracle': '#c74634',
    'githubactions': '#2088ff', 'vercel': '#25282b', 'civo': '#00ff6f',
    'render': '#313438', 'jupyter': '#e87919', 'scikitlearn': '#f7931e',
    'git': '#f05032', 'vscode': '#007acc', 'postman': '#ff6c37', 'linux': '#fcc624',
}


def text_color(background: str) -> str:
    """Prefer white type when it clears 4.5:1; use black on brighter colors."""
    rgb = [int(background[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    luminance = sum(c*w for c, w in zip(linear, [.2126, .7152, .0722]))
    return '#ffffff' if 1.05/(luminance+.05) >= 4.5 else '#000000'


def label_svg(source: str, label: str, background: str) -> str:
    # Keep the original vector paths and viewBox, sizing only the nested viewport.
    match = re.search(r'<svg\b([^>]*)>', source)
    if not match:
        raise ValueError('The logo must be an SVG')
    attrs = re.sub(r'\s(?:width|height|x|y)="[^"]*"', '', match[1])
    logo = '<svg x="5" y="5" width="14" height="14"' + attrs + '>'
    logo += source[match.end():source.rindex('</svg>')] + '</svg>'
    width = round(40 + len(label)*6.4)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="24" viewBox="0 0 {width} 24" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<rect width="{width}" height="24" fill="{background}"/>
<rect width="24" height="24" fill="#161c19"/>
{logo}
<text x="31" y="16.5" font-family="Arial,Helvetica,sans-serif" font-size="12" fill="{text_color(background)}">{escape(label)}</text>
</svg>
'''


def main():
    out = ROOT / 'assets' / 'tool-labels'
    out.mkdir(exist_ok=True)
    for slug, label in LABELS.items():
        source = (ROOT / 'assets' / 'icons' / (slug+'.svg')).read_text()
        (out / (slug+'.svg')).write_text(label_svg(source, label, COLORS[slug]))
    print(f'Built {len(LABELS)} technology badges.')


if __name__ == '__main__':
    main()
