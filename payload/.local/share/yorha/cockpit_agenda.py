"""Optional cockpit snapshot parser; no private service is configured by default."""
import re
from pathlib import Path
from settings import load

config = load()
TODAY_FILE = Path(config.get('cockpit_file') or Path.home() / 'Documents/cockpit/TODAY.md').expanduser()
PLANNER_URL = str(config.get('planner_url', '')).rstrip('/')

def cockpit_sections(text, today):
    header = next((s for s in text.splitlines() if s.startswith('COCKPIT ')), '')
    match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', header)
    snapshot = match.group(1) if match else 'unknown'
    if snapshot != today.strftime('%Y-%m-%d'): return [], [], [], snapshot
    focus = []
    active = False
    for line in text.splitlines():
        if line.startswith("TODAY'S FOCUS:"):
            active = True
        elif line and not line.startswith((' ', '\t')):
            active = False
        elif active and ':' in line:
            label, values = line.strip().split(':', 1)
            focus.extend(label.upper() + '  ' + item.strip() for item in values.split(';') if item.strip())
    return [], focus, [], snapshot
