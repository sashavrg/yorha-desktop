"""Optional archive-layout recovery and icon contrast on selected rows."""
import importlib.machinery
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
layout = importlib.machinery.SourceFileLoader('archive_layout', str(ROOT/'payload/.local/bin/yorha-thunar-layout')).load_module()


class LayoutTests(unittest.TestCase):
    def test_apply_reapply_and_restore_keep_original_preferences(self):
        original = {'/last-view': 'ThunarIconView', '/last-separator-position': '190',
                    '/misc-recursive-permissions': 'existing unrelated setting'}
        current = dict(original)
        def write(name, kind, value):
            if value is None:current.pop(name, None)
            else:current[name] = value
        with tempfile.TemporaryDirectory() as work, \
             patch.object(layout, 'read_property', side_effect=lambda name: current.get(name)), \
             patch.object(layout, 'write_property', side_effect=write):
            backup = Path(work)/'layout.json'
            layout.configure(backup)
            self.assertEqual(current['/last-view'], 'ThunarDetailsView')
            self.assertEqual(current['/misc-recursive-permissions'], original['/misc-recursive-permissions'])
            layout.configure(backup)
            self.assertEqual(json.loads(backup.read_text())['before']['/last-view'], 'ThunarIconView')
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            layout.restore(backup)
            self.assertEqual(current, original)

    def test_failed_application_rolls_back_partial_preference_changes(self):
        original = {'/last-view': 'ThunarCompactView', '/last-separator-position': '190'}
        current = dict(original)
        def write(name, kind, value):
            if name == '/last-separator-position' and value == '232':
                raise RuntimeError('Simulated settings failure')
            if value is None:current.pop(name, None)
            else:current[name] = value
        with tempfile.TemporaryDirectory() as work, \
             patch.object(layout, 'read_property', side_effect=lambda name: current.get(name)), \
             patch.object(layout, 'write_property', side_effect=write):
            backup = Path(work)/'layout.json'
            with self.assertRaises(RuntimeError):layout.configure(backup)
            self.assertEqual(current, original)
            self.assertEqual(json.loads(backup.read_text())['status'], 'restored')


class ArchiveIconTests(unittest.TestCase):
    def test_icons_retain_contrast_when_the_selected_row_matches_their_ink(self):
        def luminance(color):
            values = [int(color[i:i+2],16)/255 for i in [1,3,5]]
            return sum((v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4)*w
                       for v,w in zip(values,[.2126,.7152,.0722]))
        for theme in ['YoRHa', 'YoRHa-Night']:
            for path in (ROOT/'payload/.local/share/icons'/theme/'yorha').rglob('*.svg'):
                with self.subTest(theme=theme, icon=path.name):
                    svg = ET.parse(path).getroot()
                    background = svg.find('{http://www.w3.org/2000/svg}rect')
                    group = svg.find('{http://www.w3.org/2000/svg}g')
                    self.assertIsNotNone(background, 'An opaque tile preserves the glyph on selected rows')
                    lo,hi = sorted([luminance(background.attrib['fill']),luminance(group.attrib['stroke'])])
                    self.assertGreaterEqual((hi+.05)/(lo+.05),4.5)


if __name__ == '__main__':
    unittest.main()
