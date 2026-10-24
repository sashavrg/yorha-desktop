#!/usr/bin/env python3
"""Restore one wizard transaction. Also works after a failed or interrupted install."""
import argparse
from pathlib import Path
import subprocess
from install_lib import restore, InstallError
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('backup',type=Path)
p.add_argument('--force',action='store_true',help='Overwrite edits made after installation')
p.add_argument('--stop-services',action='store_true',help='Stop the three YoRHa services before recovery (real home only)')
a=p.parse_args()
try:
    if a.stop_services:
        import json
        recorded=json.loads((a.backup/'manifest.json').read_text())['home']
        if Path(recorded)!=Path.home():raise InstallError('Service operations require your real home')
        subprocess.run(['systemctl','--user','stop','yorha-desktop.service','yorha-cockpit-widget.service','yorha-soundwave.service'],check=False)
    home=restore(a.backup,force=a.force)
    if a.stop_services:subprocess.run(['systemctl','--user','daemon-reload'],check=False)
    print('Files restored. Backups retained. Log out and in when convenient to restore the full session.')
except (InstallError,OSError,ValueError) as exc:
    p.exit(1,str(exc)+'\n')
