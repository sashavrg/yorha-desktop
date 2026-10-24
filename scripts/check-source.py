#!/usr/bin/env python3
"""Syntax, manifest and publication hygiene checks, including hidden payload files."""
import ast
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or any(part in ['.git','__pycache__'] for part in path.relative_to(ROOT).parts): continue
    relative=path.relative_to(ROOT).as_posix()
    data=path.read_bytes()
    try: text=data.decode()
    except UnicodeDecodeError: continue
    if path.suffix=='.py' or data.startswith(b'#!/usr/bin/env python3'):
        try: ast.parse(text,filename=relative)
        except SyntaxError as exc: errors.append(str(exc))
    if path.suffix in ['.json','.jsonc'] or relative.endswith('/waybar/config'):
        try: json.loads(text)
        except ValueError as exc: errors.append(relative+': '+str(exc))
    if relative.startswith('payload/') or relative.startswith('addons/'):
        forbidden=[r'/home/[^@\s"/]+',r'/run/user/\d{3,}',r'https?://[^\s"\']+\.ts\.net',r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,})\b',r'BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY']
        for pattern in forbidden:
            if re.search(pattern,text):errors.append('Possible private/machine-specific data: '+relative)
    if relative.startswith('payload/') and path.name in ['calendar-feed-url','tasks.json','signing.p12','backup-path']:
        errors.append('Private state must not be distributed: '+relative)

profiles=ROOT/'payload/.local/share/yorha/modes'
for name in json.loads((profiles/'files.json').read_text()):
    for mode in ['day','night']:
        if not (profiles/mode/name).is_file():errors.append('Missing palette source: '+mode+'/'+name)
if errors:
    print('\n'.join(errors),file=sys.stderr);sys.exit(1)
print('Source syntax, palette manifest and publication hygiene checks passed.')
