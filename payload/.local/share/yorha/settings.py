"""Public, optional configuration. Secrets belong in separate private files."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

CONFIG = Path.home() / '.config/yorha/settings.json'

def load():
    try:
        value = json.loads(CONFIG.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def timezone():
    name = load().get('timezone', '')
    if name:
        try: return ZoneInfo(name)
        except (KeyError, ValueError): pass
    # Read the distribution's local IANA zone for correct DST on future calendar dates.
    try:
        name = str(Path('/etc/localtime').resolve()).split('/zoneinfo/', 1)[1]
        return ZoneInfo(name)
    except (IndexError, KeyError, OSError):
        return ZoneInfo("UTC")

def physical_monitors(display):
    excluded = tuple(load().get('exclude_outputs', ['HEADLESS-', 'Virtual-', 'Sunshine']))
    result = []
    for i in range(display.get_n_monitors()):
        monitor = display.get_monitor(i)
        model = monitor.get_model() or ''
        # Wayland headless outputs have no EDID. EDID-less physical panels can be opted in.
        if any(model.startswith(prefix) for prefix in excluded): continue
        if load().get('include_edidless', False) or (monitor.get_manufacturer() and model):
            result.append(monitor)
    return result
