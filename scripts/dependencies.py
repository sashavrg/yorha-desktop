#!/usr/bin/env python3
"""Install native prerequisites from configured Fedora or Arch repositories."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent

def distro():
    try:
        content = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    except OSError: return ''
    name = content.get('ID', '').strip('"')
    # Derivatives must be chosen explicitly; never assume their repositories are compatible.
    return name if name in ['fedora', 'arch'] else ''

def packages(name, components):
    table = json.loads((ROOT/'packages.json').read_text())
    if name not in table: raise ValueError('Automatic dependencies support Fedora and Arch. Use --no-deps elsewhere.')
    return list(dict.fromkeys(p for group in ['core', *components] for p in table[name].get(group, [])))

def command(name, components):
    items = packages(name, components)
    # Resolve the Wayland fork only during execution (dry-run never queries the network).
    return (['sudo', 'dnf', 'install'] if name == 'fedora' else ['sudo', 'pacman', '-S', '--needed']) + items

def install(name, components, dry_run=False, fedora_copr=False):
    cmd = command(name, components)
    if fedora_copr and name != 'fedora': raise ValueError('--fedora-copr is only valid on Fedora')
    copr_commands = [['sudo','dnf','install','dnf5-plugins'],
                     ['sudo','dnf','copr','enable','solopasha/hyprland'],
                     ['sudo','dnf','copr','enable','atim/starship']]
    if fedora_copr:
        for step in copr_commands: print('Opt-in community repository setup: '+shlex.join(step),flush=True)
    print('Native package plan: '+shlex.join(cmd), flush=True)
    if dry_run: return
    if not shutil.which('sudo'): raise RuntimeError('sudo is required to install system packages')
    if fedora_copr:
        for step in copr_commands: subprocess.run(step,check=True)
    if name == 'fedora':
        items=packages(name, components)
        # Already installed native packages are sufficient; do not upgrade a working stack.
        installed=subprocess.run(['rpm','-q','--queryformat','%{NAME}\\n',*items],capture_output=True,text=True)
        present=set(installed.stdout.splitlines())
        missing=[item for item in items if item not in present]
        # An existing user-installed Starship binary also satisfies its optional theme.
        if 'starship' in missing and shutil.which('starship'): missing.remove('starship')
        if missing:
            result=subprocess.run(['dnf','repoquery','--available','--queryformat','%{name}\\n',*missing,'rofi'],capture_output=True,text=True,check=True)
            available=set(result.stdout.splitlines())
            if 'rofi-wayland' in missing and 'rofi-wayland' not in available and 'rofi' in available:
                missing[missing.index('rofi-wayland')]='rofi'
            unavailable=[item for item in missing if item not in available]
            if unavailable:
                raise RuntimeError('Missing from enabled Fedora repositories: '+', '.join(unavailable)+
                    '. Rerun with --fedora-copr to opt into the documented community sources, or install prerequisites yourself and use --no-deps.')
        if not missing:
            print('Native packages are already installed.');return
        cmd=['sudo','dnf','install',*missing]
    print('Installing: '+shlex.join(cmd),flush=True)
    # Keep the package manager's own confirmation; never upgrade the whole system.
    subprocess.run(cmd, check=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--distro', choices=['fedora','arch'], default=distro() or None)
    p.add_argument('--components', default='desktop,standby,apps')
    p.add_argument('--fedora-copr', action='store_true', help='Opt into solopasha/hyprland and atim/starship community repositories on Fedora')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    install(args.distro, [s for s in args.components.split(',') if s], args.dry_run,args.fedora_copr)

if __name__ == '__main__': main()
