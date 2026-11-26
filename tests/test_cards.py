"""Guard real data calculations, cache fallback and GitHub image compatibility."""
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import render_cards as cards


def day(ds, count):
    return {'date': ds, 'count': count, 'level': min(count, 4)}


class ContributionTests(unittest.TestCase):
    def test_attribute_order_and_nested_tooltip_text(self):
        html = '''<td id="a" class="extra ContributionCalendar-day" data-level="2" data-date="2026-11-18"></td>
        <tool-tip for="a"><span>1,234 contributions</span> on November 18.</tool-tip>'''
        self.assertEqual(cards.parse_calendar(html), [day('2026-11-18', 1234) | {'level': 2}])

    def test_missing_tooltips_reject_changed_markup(self):
        with self.assertRaises(ValueError):
            cards.parse_calendar('<td class="ContributionCalendar-day" id="a" data-date="2026-11-18"></td>')

    def test_today_empty_keeps_yesterdays_streak(self):
        days = [day('2026-11-16', 1), day('2026-11-17', 3), day('2026-11-18', 0)]
        stats = cards.calendar_stats(days, date(2026, 11, 18))
        self.assertEqual((stats['current_streak'], stats['longest_streak'], stats['total']), (2, 2, 4))

    def test_missing_day_breaks_streak_and_future_is_excluded(self):
        days = [day('2026-11-15', 4), day('2026-11-17', 2), day('2026-11-18', 5)]
        stats = cards.calendar_stats(days, date(2026, 11, 17))
        self.assertEqual((stats['current_streak'], stats['longest_streak'], stats['total']), (1, 1, 6))
        self.assertEqual(stats['weeks'][0][0]['date'], '2026-11-15')

    def test_failed_fetch_keeps_both_snapshots_and_their_dates(self):
        original_activity = cards.read_json(cards.DATA)
        original_profile = cards.read_json(cards.PROFILE)
        with patch.object(cards, 'request', side_effect=OSError('offline')):
            with patch.object(cards, 'save_json') as save:
                activity, profile = cards.refresh()
        self.assertEqual(activity, original_activity)
        self.assertEqual(profile, original_profile)
        save.assert_not_called()


class ProfileTests(unittest.TestCase):
    def test_fork_stars_do_not_count_as_earned(self):
        user = {'login': 'test', 'created_at': '2023-05-28T00:00:00Z', 'public_repos': 2, 'followers': 1}
        repos = [{'fork': False, 'stargazers_count': 3}, {'fork': True, 'stargazers_count': 99}]
        stats = cards.profile_stats(user, repos, [{'Python': 75, 'CSS': 25}])
        self.assertEqual(stats['stars'], 3)
        self.assertEqual(stats['source_repos'], 1)
        self.assertAlmostEqual(sum(percent for _, percent in cards.language_rows(stats)), 100)

    def test_small_languages_group_without_losing_bytes(self):
        stats = {'languages': {str(i): 10-i for i in range(8)}}
        rows = cards.language_rows(stats)
        self.assertEqual(rows[-1][0], 'Other')
        self.assertAlmostEqual(sum(percent for _, percent in rows), 100)

    def test_all_cards_are_self_contained_svg_images(self):
        a, p = cards.read_json(cards.DATA), cards.read_json(cards.PROFILE)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cards, 'OUT', Path(tmp)):
                cards.render(a, p)
            paths = list(Path(tmp).glob('*.svg'))
            self.assertEqual(len(paths), 6)
            for path in paths:
                root = ET.fromstring(path.read_text())
                self.assertIn('viewBox', root.attrib)
                self.assertIsNotNone(root.find('{http://www.w3.org/2000/svg}title'))
                self.assertNotIn('<script', path.read_text())
                self.assertNotIn('<foreignObject', path.read_text())
                self.assertNotIn('<image', path.read_text())
                self.assertNotIn('Gradient', path.read_text())

    def test_desktop_and_mobile_exports_have_readable_type(self):
        a, p = cards.read_json(cards.DATA), cards.read_json(cards.PROFILE)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cards, 'OUT', Path(tmp)):
                cards.render(a, p)
            for name in ['activity', 'languages', 'snake']:
                desktop = ET.fromstring((Path(tmp)/(name+'.svg')).read_text())
                mobile = ET.fromstring((Path(tmp)/(name+'-mobile.svg')).read_text())
                self.assertGreater(float(desktop.attrib['width']), float(mobile.attrib['width']))
                for root in [desktop, mobile]:
                    for node in root.iter('{http://www.w3.org/2000/svg}text'):
                        self.assertGreaterEqual(float(node.attrib['font-size']), 15)

    def test_static_snake_has_no_animation_and_retains_calendar(self):
        a = cards.read_json(cards.DATA)
        with patch.object(cards, 'STATIC', True):
            for compact in [False, True]:
                svg = cards.snake_card(a, compact=compact)
                root = ET.fromstring(svg)
                self.assertNotIn('animateMotion', svg)
                self.assertGreater(len(list(root.iter('{http://www.w3.org/2000/svg}rect'))), 100)

    def test_snake_handles_a_calendar_with_no_contributions(self):
        a = cards.calendar_stats([day('2026-11-01', 0)], date(2026, 11, 7))
        for compact in [False, True]:
            svg = cards.snake_card(a, compact=compact)
            ET.fromstring(svg)
            self.assertNotIn('animateMotion', svg)
            self.assertIn('0 contributions', svg)


if __name__ == '__main__':
    unittest.main()
