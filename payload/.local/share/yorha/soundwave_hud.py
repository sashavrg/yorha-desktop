"""Shared geometry and live state for the NieR Sound Waves HUD."""
import json
import os
import time
from pathlib import Path

import cairo

ROOT = Path.home() / '.local/share/yorha'
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'yorha-soundwave'
STATE = RUNTIME / 'spectrum.json'
IMAGE = RUNTIME / 'waybar.png'
BANDS = 24
SIGNAL = 9
COLORS = {'day': '#454438', 'night': '#c8c2a9'}


def palette():
    try:
        value = (ROOT / 'mode').read_text().strip()
    except OSError:
        value = 'night'
    return value if value in COLORS else 'night'


def read_levels():
    """A stopped or failed analyser must not leave a frozen active spectrum."""
    try:
        data = json.loads(STATE.read_text())
        values = data['levels']
        if len(values) != BANDS or time.monotonic() - data['monotonic'] > 3:
            raise ValueError('stale spectrum')
        return [max(0., min(1., float(value))) for value in values]
    except (OSError, ValueError, KeyError, TypeError):
        return [0.] * BANDS


def draw_hud(ctx, width, height, levels, color):
    """Thin frequency bars over twin rules and square terminal marks.

    Ratios follow the user's in-game screenshot. This is a true low-to-high
    spectrum: do not impose a decorative hill or duplicate/mirror the bands.
    """
    rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    left, right = 2., max(3., width - 2.)
    step = (right - left) / BANDS
    thickness = min(5., max(1., round(step * .48)))
    floor = max(2., height - 12.)
    extent = max(1., floor - 2.)
    ctx.set_source_rgb(*rgb)
    for i in range(BANDS):
        # Use solid narrow columns with clear gaps, rather than block glyphs.
        value = max(0., min(1., levels[i])) if i < len(levels) else 0.
        bar_height = max(2., round(value * extent))
        x = round(left + (i + .5) * step - thickness / 2)
        ctx.rectangle(x, floor - bar_height, thickness, bar_height)
    ctx.fill()
    ctx.set_source_rgba(*rgb, .9)
    ctx.rectangle(left, floor + 4, right - left, 1)
    ctx.fill()
    ctx.set_source_rgba(*rgb, .45)
    ctx.rectangle(left, floor + 6, right - left, 1)
    ctx.fill()
    ctx.set_source_rgba(*rgb, .9)
    for x in (left, right - 3):
        ctx.rectangle(x, floor + 8, 3, 3)
    ctx.fill()


def png(path, levels, mode, width=148, height=32, scale=2):
    """Publish an antialiased, transparent frame atomically in runtime tmpfs."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * scale, height * scale)
    ctx = cairo.Context(surface)
    ctx.scale(scale, scale)
    draw_hud(ctx, width, height, levels, COLORS[mode])
    temp = path.with_name(path.name + '.tmp')
    surface.write_to_png(str(temp))
    os.replace(temp, path)


def atomic_state(levels, mode, connected):
    value = {'levels': levels, 'mode': mode, 'connected': connected,
             'monotonic': time.monotonic(), 'bands': BANDS}
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(value, separators=(',', ':')) + '\n')
    os.replace(temp, STATE)
