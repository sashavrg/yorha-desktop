#!/usr/bin/env python3
"""YoRHa desktop installer. Review a complete plan before changing user files."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

import dependencies
from install_lib import InstallError, Transaction, restore, validate

REPO = Path(__file__).resolve().parent.parent
CORE_PREFIXES = ('.config/hypr/', '.config/waybar/', '.config/rofi/', '.config/swaync/', '.config/kitty/')
COMPONENTS = {'desktop', 'agenda', 'standby', 'apps'}

def ask(prompt, default):
    value = input(f'  {prompt} [{default}]: ').strip()
    return value or default

def yes(prompt, default=True):
    while True:
        value = ask(prompt + ' (yes/no)', 'yes' if default else 'no').lower()
        if value in ['y','yes']: return True
        if value in ['n','no']: return False
        print('  Please enter yes or no.')

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--yes', action='store_true', help='Use explicit/default options without wizard questions')
    p.add_argument('--dry-run', action='store_true', help='Print plan; no writes, package queries, downloads or service calls')
    p.add_argument('--target', type=Path, default=Path.home(), help='Target home directory (alternate homes never activate services)')
    p.add_argument('--layout', choices=['overlay','standalone'], help='Append one source line, or replace the main Hyprland config')
    p.add_argument('--mode', choices=['day','night'], default='night')
    p.add_argument('--components', default='desktop,agenda,standby,apps')
    p.add_argument('--fedora-copr', action='store_true', help='Opt into Fedora community repositories for Hyprland tools and Starship')
    p.add_argument('--distro', choices=['fedora','arch'], default=dependencies.distro() or None)
    dep=p.add_mutually_exclusive_group()
    dep.add_argument('--deps', dest='deps', action='store_true', help='Install native dependencies using sudo and the package manager')
    dep.add_argument('--no-deps', dest='deps', action='store_false')
    p.set_defaults(deps=None)
    p.add_argument('--no-venv', action='store_true', help='Skip calendar venv creation (for staging/tests only)')
    p.add_argument('--no-assets', action='store_true', help='Skip emblem download and wallpaper generation (for staging/tests only)')
    p.add_argument('--no-bindings', action='store_true', help='Keep existing key bindings; add theme/startup only')
    p.add_argument('--keyboard', default='us', help='XKB layout for standalone config')
    # Accept the old opt-in flag so existing install commands still work.
    p.add_argument('--game-emblem', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--phonecam', action='store_true', help='Add optional DroidCam button (DroidCam CLI must be installed separately)')
    p.add_argument('--sddm', action='store_true', help='Stage optional SDDM theme and print its separate sudo installation command')
    p.add_argument('--activate', action='store_true', help='Reload live Hyprland and restart bar/widgets after installation')
    return p

def choose(args):
    args.target=args.target.expanduser().absolute()
    args.components={s for s in args.components.split(',') if s}
    if not args.components <= COMPONENTS: raise InstallError('Unknown component name')
    if not re.fullmatch(r'[a-z0-9_,+-]+', args.keyboard): raise InstallError('Invalid keyboard layout')
    existing=(args.target/'.config/hypr/hyprland.conf').exists()
    if not args.layout: args.layout='overlay' if existing else 'standalone'
    if not args.yes and not args.dry_run:
        if not sys.stdin.isatty(): raise InstallError('Wizard needs a terminal; use --yes with explicit options in automation')
        print('\n  ■ YoRHa / DEPLOYMENT CONSOLE\n  Warm parchment by day. Quiet graphite by night.\n')
        while True:
            args.layout=ask('Hyprland layout (overlay / standalone)', args.layout)
            if args.layout in ['overlay','standalone']: break
        while True:
            args.mode=ask('Initial mode (day / night)', args.mode)
            if args.mode in ['day','night']: break
        for item, title in [('desktop','Floating Access, Status, Clock and Operator panels'),('agenda','Calendar and interactive local Quests'),('standby','Animated standby and idle locking'),('apps','GTK, Qt, editor and terminal companion themes')]:
            if yes(title, item in args.components): args.components.add(item)
            else: args.components.discard(item)
        args.no_bindings=not yes('Install YoRHa shortcuts (listed in the plan)', not args.no_bindings)
        args.phonecam=yes('Add optional USB / Wi-Fi DroidCam button (requires DroidCam CLI)', args.phonecam)
        args.sddm=yes('Prepare optional SDDM login theme for separate installation', args.sddm)
        if args.deps is None: args.deps=yes('Install native prerequisites with the distribution package manager', bool(args.distro))
        if args.deps and args.distro=='fedora': args.fedora_copr=yes('Enable community COPRs solopasha/hyprland and atim/starship if using Fedora', args.fedora_copr)
        if args.layout=='standalone': args.keyboard=ask('Keyboard layout',args.keyboard)
        if args.target==Path.home(): args.activate=yes('Apply to this running session now (restarts the bar/widgets)', False)
    if args.deps is None: args.deps=True
    if args.deps and not args.distro: raise InstallError('Choose --distro fedora|arch, or --no-deps and install prerequisites manually')
    if not re.fullmatch(r'[a-z0-9_,+-]+',args.keyboard): raise InstallError('Invalid keyboard layout')
    if args.activate and args.target!=Path.home(): raise InstallError('Alternate target homes cannot activate this session')
    if args.target!=Path.home() and args.deps and not args.dry_run:
        raise InstallError('For staging in another home, use --no-deps (packages affect this machine)')
    if args.layout=='overlay' and not existing: raise InstallError('Overlay needs an existing ~/.config/hypr/hyprland.conf; choose standalone')
    if args.target==Path('/') or not args.target.is_absolute(): raise InstallError('Choose a user home directory')
    if args.target.is_symlink(): raise InstallError('Target home must be a real directory')
    if any(c in str(args.target) for c in '\n\r\0'): raise InstallError('Unsupported home path')
    if os.geteuid()==0 and args.target==Path.home(): raise InstallError('Run the wizard as your desktop user, never with sudo')
    return args

def plan(args):
    print('\n  ■ DEPLOYMENT PLAN')
    print('  Home:       '+str(args.target))
    print('  Hyprland:   '+args.layout+(' (preserve main config, append one source)' if args.layout=='overlay' else ' (replace main config; back up previous file)'))
    print('  Palette:    '+args.mode)
    print('  Components: '+', '.join(sorted(args.components)))
    print('  Emblem:     YoRHa game emblem (checksum-pinned upstream download)')
    print('  Backups:    ~/.local/state/yorha/backups/<UTC timestamp>/')
    print('  Recovery:   yorha-restore <backup> (or python3 scripts/restore.py <backup>)')
    print('  Startup:    guarded bar/notifications/wallpaper + selected user services at next login')
    print('  Live reload:'+(' yes' if args.activate else ' no (current session stays as it is)'))
    if not args.no_bindings:
        print('  Shortcuts:  Super+Enter terminal; D apps; A windows; B browser; E files; L lock; Space float; N comms')
        print('              Super+Esc system; Super+Alt+N palette; R reload; S standby; W widgets')
    print('  Managed configs include Waybar, Rofi, notifications, Kitty and selected application palettes.')
    print('  Existing files and leaf symlinks are backed up before replacement.')
    print('  Calendar feeds and tasks remain local; no account connection is required.')
    if args.deps:
        groups=(args.components-{'agenda'}) | ({'desktop'} if 'agenda' in args.components else set()) | ({'sddm'} if args.sddm else set()) | ({'phonecam'} if args.phonecam else set())
        dependencies.install(args.distro,sorted(groups),dry_run=True,fedora_copr=args.fedora_copr)
    else: print('  Native packages: skipped')
    if args.phonecam: print('  Phone camera: button only; install DroidCam CLI and loopback module separately (docs/PHONECAM.md)')
    if args.sddm: print('  SDDM: staged only; separate sudo command, no login-manager restart')
    print()

def transform(value, home, runtime):
    if isinstance(value,str): return value.replace('@HOME@',str(home)).replace('@RUNTIME@',runtime)
    if isinstance(value,list): return [transform(v,home,runtime) for v in value]
    if isinstance(value,dict): return {k:transform(v,home,runtime) for k,v in value.items()}
    return value

def render(data, home, runtime):
    try: text=data.decode()
    except UnicodeDecodeError: return data
    try:
        parsed=json.loads(text)
    except ValueError: return text.replace('@HOME@',str(home)).replace('@RUNTIME@',runtime).encode()
    return (json.dumps(transform(parsed,home,runtime),indent=2)+'\n').encode()

def session_config(args):
    lines=['# Managed by YoRHa. Edit visual profiles in ~/.local/share/yorha/modes.',
        'source = $HOME/.config/hypr/yorha.conf',
        'exec-once = "$HOME/.local/bin/yorha-session-start"',
        'env = XDG_CURRENT_DESKTOP,Hyprland',
        'env = XDG_SESSION_TYPE,wayland']
    if 'apps' in args.components: lines.append('env = QT_QPA_PLATFORMTHEME,qt6ct')
    if not args.no_bindings:
        bindings=[('SUPER','RETURN','kitty'),('SUPER','D','rofi -show drun'),
            ('SUPER','E','xdg-open "$HOME"'),('SUPER','B','"$HOME/.local/bin/yorha-browser"'),
            ('SUPER','A','rofi -show window'),
            ('SUPER','L','"$HOME/.local/bin/yorha-lock"'),('SUPER','SPACE','"$HOME/.local/bin/yorha-toggle-float"'),
            ('SUPER ALT','SPACE','"$HOME/.local/bin/yorha-workspace-float"'),
            ('SUPER','N','swaync-client -t'),('SUPER','ESCAPE','"$HOME/.local/bin/yorha-power"'),
            ('SUPER ALT','N','"$HOME/.local/bin/yorha-mode" toggle'),('SUPER ALT','R','"$HOME/.local/bin/yorha-reload"')]
        if 'standby' in args.components: bindings.append(('SUPER ALT','S','"$HOME/.local/bin/yorha-standby" preview'))
        if args.components & {'desktop','agenda'}: bindings.append(('SUPER ALT','W','"$HOME/.local/bin/yorha-desktop" toggle'))
        for modifiers,key,command in bindings:
            lines += [f'unbind = {modifiers}, {key}',f'bind = {modifiers}, {key}, exec, {command}']
    return '\n'.join(lines)+'\n'

def standalone(args):
    lines=['# YoRHa standalone baseline. Customize hardware/input here.',
        'monitor = , preferred, auto, 1',
        'input {',f'    kb_layout = {args.keyboard}','    follow_mouse = 1','    touchpad {','        natural_scroll = true','    }','}',
        'general {','    layout = dwindle','}','misc {','    disable_hyprland_logo = true','}',
        'bind = SUPER, Q, killactive,','bind = SUPER, F, fullscreen, 0',
        'bind = SUPER, J, movefocus, d','bind = SUPER, K, movefocus, u',
        'bind = SUPER, H, movefocus, l','bind = SUPER, semicolon, movefocus, r',
        'bindm = SUPER, mouse:272, movewindow','bindm = SUPER, mouse:273, resizewindow']
    for i in range(1,11):
        key=str(i%10)
        lines += [f'bind = SUPER, {key}, workspace, {i}',
            f'bind = SUPER SHIFT, {key}, exec, "$HOME/.local/bin/yorha-move-workspace" {i}']
    lines += ['source = $HOME/.config/hypr/yorha-session.conf']
    return '\n'.join(lines)+'\n'

def selected_file(relative, args):
    if '/sddm/' in relative and not args.sddm: return False
    if relative=='.config/hypr/hypridle.conf' and 'standby' not in args.components: return False
    if relative.startswith('.config/') and not relative.startswith(CORE_PREFIXES) and 'apps' not in args.components:
        if not relative.startswith('.config/systemd/'): return False
    if relative.startswith(('.local/share/themes/','.local/share/icons/')) and 'apps' not in args.components: return False
    return True

def stage(args, folder):
    runtime=os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}')
    for source in sorted((REPO/'payload').rglob('*')):
        if not source.is_file(): continue
        relative=source.relative_to(REPO/'payload').as_posix()
        if not selected_file(relative,args): continue
        target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(render(source.read_bytes(),args.target,runtime))
        target.chmod(source.stat().st_mode & 0o777)
    root=folder/'.local/share/yorha'
    files=json.loads((root/'modes/files.json').read_text())
    files=[f for f in files if selected_file(f,args)]
    (root/'modes/files.json').write_text(json.dumps(files,indent=2)+'\n')
    if args.phonecam:
        for mode in ['day','night']:
            p=root/'modes'/mode/'.config/waybar/config'
            bar=json.loads(p.read_text())
            bar['modules-right'].insert(-2,'custom/phonecam')
            bar['custom/phonecam']={'exec':'"$HOME/.local/bin/yorha-phonecam" status',
                'return-type':'json','interval':2,'format':'{}',
                'on-click':'"$HOME/.local/bin/yorha-phonecam" toggle','tooltip':True}
            p.write_text(json.dumps(bar,indent=2)+'\n')
        for name in ['yorha-phonecam','yorha-phonecam-connect','yorha-phonecam.service']:
            target=folder/('.config/systemd/user' if name.endswith('.service') else '.local/bin')/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(REPO/'addons/phonecam'/name,target)
    for name in files:
        dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/'modes'/args.mode/name,dest)
    (root/'mode').write_text(args.mode+'\n')
    (folder/'.config/hypr/yorha-session.conf').write_text(session_config(args))
    main=folder/'.config/hypr/hyprland.conf'
    if args.layout=='standalone': main.write_text(standalone(args))
    else:
        existing=(args.target/'.config/hypr/hyprland.conf').read_text()
        marker='source = $HOME/.config/hypr/yorha-session.conf'
        if marker not in existing: existing=existing.rstrip()+'\n\n# YoRHa desktop\n'+marker+'\n'
        main.write_text(existing)
    flags=folder/'.config/yorha';flags.mkdir(exist_ok=True)
    for component,flag in [('desktop','yorha-desktop'),('agenda','yorha-cockpit-widget')]:
        if component in args.components: (flags/(flag+'-enabled')).write_text('enabled\n')
    (flags/'yorha-soundwave-enabled').write_text('enabled\n')
    if 'standby' in args.components: (flags/'standby-enabled').write_text('enabled\n')
    # Private settings/tasks/calendar are never overwritten by reinstall/update.
    defaults=dict(timezone='',planner_url='',cockpit_file='',include_edidless=False,
                  exclude_outputs=['HEADLESS-','Virtual-','Sunshine'])
    if not (args.target/'.config/yorha/settings.json').exists():
        (flags/'settings.json').write_text(json.dumps(defaults,indent=2)+'\n')
    if not args.no_assets:
        sys.path.insert(0,str(REPO/'scripts'))
        from fetch_emblem import fetch
        fetch(root/'assets/yorha-emblem.svg')
        subprocess.run(['/usr/bin/python3',str(root/'render-interface.py')],check=True)
        if args.sddm:
            subprocess.run(['/usr/bin/python3',str(REPO/'scripts/prepare-sddm.py'),str(root)],check=True)
    # Recovery stays usable even if the original clone moves or is removed.
    recovery=root/'installer';recovery.mkdir()
    for name in ['install_lib.py','restore.py']:
        shutil.copy2(REPO/'scripts'/name,recovery/name)
    return root

def create_venv(args, tx):
    env=dict(os.environ, PYTHONNOUSERSITE='1')
    if args.no_venv or not args.components & {'desktop','agenda'}: return
    dest=args.target/'.local/share/yorha/calendar-venv'
    if dest.exists():
        try:
            result=subprocess.run([str(dest/'bin/python'),'-c','import gi, cairo, psutil, icalendar, recurring_ical_events'],capture_output=True,env=env)
            if result.returncode == 0: return
        except OSError:
            pass
        print('Calendar runtime needs rebuilding for the current system Python; preserving it in the transaction backup.',flush=True)
        tx.replace_directory('.local/share/yorha/calendar-venv')
    tx.generated_dir('.local/share/yorha/calendar-venv')
    subprocess.run(['/usr/bin/python3','-m','venv','--system-site-packages',str(dest)],check=True,env=env)
    subprocess.run([str(dest/'bin/python'),'-m','pip','install','--disable-pip-version-check','-r',str(args.target/'.local/share/yorha/calendar-requirements.txt')],check=True,env=env)

def apply(args):
    if args.deps:
        groups=(args.components-{'agenda'}) | ({'desktop'} if 'agenda' in args.components else set()) | ({'sddm'} if args.sddm else set()) | ({'phonecam'} if args.phonecam else set())
        dependencies.install(args.distro,sorted(groups),fedora_copr=args.fedora_copr)
    with tempfile.TemporaryDirectory(prefix='yorha-stage-') as work:
        folder=Path(work)
        stage(args,folder)
        # Preflight all destinations before creating a transaction or writing user files.
        for path in folder.rglob('*'):
            if path.is_file(): validate(args.target,path.relative_to(folder).as_posix())
        tx=Transaction(args.target)
        print('Recovery backup: '+str(tx.backup),flush=True)
        try:
            for path in sorted(folder.rglob('*')):
                if path.is_file(): tx.put(path.relative_to(folder).as_posix(),path.read_bytes(),path.stat().st_mode & 0o777)
            for component, flag in [('desktop','yorha-desktop-enabled'),('agenda','yorha-cockpit-widget-enabled'),('standby','standby-enabled')]:
                if component not in args.components: tx.delete('.config/yorha/'+flag)
            create_venv(args,tx)
            tx.finish()
        except BaseException:
            print('Installation interrupted. Restoring changed files from '+str(tx.backup),file=sys.stderr)
            restore(tx.backup,force=True)
            raise
    if args.activate:
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run([str(args.target/'.local/bin/yorha-session-start')],check=True)
        subprocess.run([str(args.target/'.local/bin/yorha-reload')],check=True)
        for unit in ['yorha-desktop','yorha-cockpit-widget']:
            if (args.target/'.config/yorha'/(unit+'-enabled')).exists():
                subprocess.run(['systemctl','--user','restart',unit+'.service'],check=True)
    print('\n  ■ DEPLOYMENT COMPLETE\n  Files installed. '+('Session refreshed.' if args.activate else 'The theme starts at your next Hyprland login.'))
    print('  Restore: python3 '+shlex.quote(str(REPO/'scripts/restore.py'))+' '+shlex.quote(str(tx.backup)))
    if args.sddm:
        print('  Optional login theme: sudo python3 '+shlex.quote(str(args.target/'.local/share/yorha/sddm/install.py'))+' --mode '+args.mode)
    print('  Check setup: '+shlex.quote(str(args.target/'.local/bin/yorha-doctor')))

def main():
    p=parser()
    try:
        args=choose(p.parse_args())
        plan(args)
        sys.stdout.flush()
        if args.dry_run:
            print('Dry run complete. Nothing changed.');return
        if not args.yes and not yes('Apply this plan',False):
            print('Cancelled. Nothing changed.');return
        apply(args)
    except (InstallError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1,'Deployment failed: '+str(exc)+'\n')
    except (KeyboardInterrupt,EOFError):
        p.exit(130,'\nCancelled.\n')

if __name__=='__main__': main()
