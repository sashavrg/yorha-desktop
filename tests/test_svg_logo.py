"""Native regression check for Glycin's SVG MIME sniffing (optional GTK deps)."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'payload/.local/share/yorha'
try:
    import gi
    gi.require_version('Gtk','3.0')
    gi.require_version('GtkLayerShell','0.1')
    import cairo,psutil
    NATIVE=True
except (ImportError,ValueError):
    NATIVE=False

@unittest.skipUnless(NATIVE,'Native GTK/Cairo dependencies are not installed')
class LogoTests(unittest.TestCase):
    def test_recolored_logo_loads_in_both_palettes(self):
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location('yorha_desktop_svg_test',ROOT/'desktop-shell.py')
        desktop=importlib.util.module_from_spec(spec);spec.loader.exec_module(desktop)
        class Image:
            def set_from_pixbuf(self,pixbuf):self.pixbuf=pixbuf
        class Panel:pass
        with tempfile.TemporaryDirectory() as work:
            desktop.ROOT=Path(work)
            (desktop.ROOT/'assets').mkdir()
            (desktop.ROOT/'assets/yorha-emblem.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0H10V10H0Z" fill="#000000"/></svg>')
            for mode in ['day','night']:
                shell=Panel();shell.palette=mode;shell.emblem=Image()
                desktop.DesktopShell.tint_emblem(shell)
                pix=shell.emblem.pixbuf
                self.assertEqual((pix.get_width(),pix.get_height()),(65,100))
                offset=50*pix.get_rowstride()+32*pix.get_n_channels()
                self.assertEqual(tuple(pix.get_pixels()[offset:offset+3]),tuple(bytes.fromhex(desktop.PALETTES[mode]['ink'][1:])))
