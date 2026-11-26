# Profile maintenance

Edit `README.md` directly. The card generator never rewrites it.

- `cards/`: activity, languages, and snake SVGs, each with desktop and mobile variants, generated locally with Python's standard library. The README uses native `<picture>` sources to select a readable layout. Mobile calendars show the last 26 weeks; the totals still cover the full contribution period.
- `contributions.json`: last successful public contribution calendar snapshot.
- `profile-data.json`: last successful public profile and repository-language snapshot.
- `assets/`: local hero GIF and tech icons. See `assets/ATTRIBUTION.md`.
- `assets/tool-labels/`: flat brand-color badges, with a dark icon area and a readable name. Each badge is one local SVG so the logo and name stay together when a row wraps. Text uses black or white according to contrast. Rebuild these with `python3 build_tools.py` after changing the labels, colors, or source icons.
- `preview.html`: local approximation of GitHub styling. Open in a browser; no server required. Regenerate it with `python3 build_preview.py` after editing README content. It is not a GitHub sanitizer check.

```sh
python3 render_cards.py             # fetch public data and render cards
python3 render_cards.py --offline   # render the saved snapshots
STATIC=1 python3 render_cards.py --offline  # export without snake animation
python3 build_preview.py            # rebuild the local README preview
python3 build_tools.py              # rebuild the icon-and-name pairs
python3 -m unittest discover -s tests
```

The workflow refreshes cards daily at 02:30 UTC (08:00 IST), when its generator changes on `main`, or from **Actions → Refresh Profile Cards → Run workflow**. It uses GitHub's built-in token; no paid service or personal access token is required. Push this repository to GitHub to activate those changes. Scheduled runs depend on GitHub Actions being enabled with write access for the workflow token.

Counts come from GitHub's public REST API and contribution calendar. Language percentages use language bytes across public, non-fork repositories; small languages are grouped as **Other**. Stars count public, non-fork repositories. Streaks cover the displayed contribution period, not the account's entire history. An empty ongoing day does not break yesterday's current streak. The snake follows the actual active calendar cells and loops; it is an illustration, not a live activity feed. SVG motion respects the viewer's reduced-motion preference.

If either fetch fails, the generator keeps that source's last successful snapshot and its update date. It fails if a source has no saved snapshot. Offline generation makes no network requests. For authenticated local requests, optionally set `GH_TOKEN` in your environment; tokens are never written to the snapshots.
