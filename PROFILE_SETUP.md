# Profile maintenance

Edit `README.md` directly. The card generator never rewrites it.

- `cards/`: six SVG cards, generated locally with Python's standard library.
- `contributions.json`: last successful public contribution calendar snapshot.
- `profile-data.json`: last successful public profile and repository-language snapshot.
- `assets/`: local hero GIF and tech icons. See `assets/ATTRIBUTION.md`.
- `preview.html`: local approximation of GitHub styling. Open in a browser; no server required. Regenerate it with `python3 build_preview.py` after editing README content. It is not a GitHub sanitizer check.

```sh
python3 render_cards.py             # fetch public data and render cards
python3 render_cards.py --offline   # render the saved snapshots
STATIC=1 python3 render_cards.py --offline  # export without snake animation
python3 build_preview.py            # rebuild the local README preview
python3 -m unittest discover -s tests
```

The workflow refreshes cards daily at 02:30 UTC (08:00 IST), when its generator changes on `main`, or from **Actions → Refresh Profile Cards → Run workflow**. It uses GitHub's built-in token; no paid service or personal access token is required. Push this repository to GitHub to activate those changes. Scheduled runs depend on GitHub Actions being enabled with write access for the workflow token.

Counts come from GitHub's public REST API and contribution calendar. Language percentages use language bytes across public, non-fork repositories; small languages are grouped as **Other**. Stars count public, non-fork repositories. Streaks cover the displayed contribution period, not the account's entire history. An empty ongoing day does not break yesterday's current streak. The snake follows the actual active calendar cells and loops; it is an illustration, not a live activity feed. SVG motion respects the viewer's reduced-motion preference.

If either fetch fails, the generator keeps that source's last successful snapshot and its update date. It fails if a source has no saved snapshot. Offline generation makes no network requests. For authenticated local requests, optionally set `GH_TOKEN` in your environment; tokens are never written to the snapshots.
