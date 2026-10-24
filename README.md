# YoRHa Desktop

A NieR:Automata inspired Hyprland desktop: parchment and graphite palettes, floating menu panels, a quest log, procedural wallpapers and a rotating standby crest.

![Day palette with synthetic preview data](docs/images/day.webp)
![Night palette with synthetic preview data](docs/images/night.webp)

## Install

Start from a Linux desktop with working graphics, systemd user services, Git and Python 3. Native dependency scripts support **Fedora and Arch Linux**. Fedora may need its optional community package sources for Hyprland tools and Starship. Run as your normal desktop user; the installer invokes `sudo` only for distribution packages.

```sh
git clone https://github.com/sashavrg/yorha-desktop.git
cd yorha-desktop
./install.sh
```

The terminal wizard walks through layout, palette, widgets, standby, application themes, optional assets and dependency installation. On Fedora it also offers `solopasha/hyprland` and `atim/starship` COPRs, disabled unless selected; Arch uses its official repositories. It shows a plan before applying anything. Package managers retain their own confirmation prompts. There is no `curl | sh`, AUR helper or whole-system upgrade. Fedora users can explicitly opt into the community repositories described below.

- **Overlay:** retains your main Hyprland config and monitor rules; adds one source line. Managed application configs are backed up and replaced. Existing startup commands remain: review them if another dotfile framework also changes wallpapers or colors.
- **Standalone:** writes a small complete Hyprland config with automatic monitor discovery and workspace/navigation bindings. It backs up an existing main config first.

By default the current session stays as it is until the next Hyprland login. The wizard can explicitly reload it immediately. It never logs you out or restarts your display manager.

Inspect without writes, downloads or service calls:

```sh
./install.sh --dry-run
./scripts/install-deps.sh --distro fedora --dry-run
```

For an unattended configuration install with prerequisites already present:

```sh
./install.sh --yes --no-deps --layout overlay --mode night
```

`--yes` accepts installer defaults; it does not suppress package-manager authentication or confirmation. See `./install.sh --help` and [installation details](docs/INSTALL.md).

## What is included

- Matched **day/night** profiles for Hyprland, Waybar, Rofi, SwayNC, Kitty, Hyprlock, GTK 3/4, Qt/Kvantum, KDE colors, Starship, Fastfetch, Btop, Cava and Neovim palettes.
- **Floating desktop panels:** Access, machine telemetry, Local time and Operator transmissions with real MPRIS media controls. They sit above the wallpaper and below normal windows.
- **Calendar and Quests:** interactive date selection and local checkable tasks; optional private Google Calendar iCal feed and optional compatible planner connection. No account is needed for local quests.
- **Sound Waves HUD:** a shared 24-band Cava analyser drives Waybar and the media panel from the playback monitor. It never selects a microphone.
- **Standby:** one unlit perspective-projected crest, a 60-second rotation, slow vertical bob, fine grain and quiet transmission messages. Mouse/keyboard dismisses it; Hyprlock provides authentication separately.
- Procedural landscape/portrait wallpapers with a woven grid, edge fringing and gentle lens distortion. Generated locally from source.
- Optional SDDM theme and optional DroidCam USB/Wi-Fi button.

Public defaults use an original wing crest, packaged Noto Sans / JetBrains Mono, and system Breeze icons. For the community trace of the game logo, select it in the wizard or add `--game-emblem`. The upstream SVG is checksum pinned and downloaded only when requested; it is not bundled or relicensed. See [asset credits](THIRD_PARTY.md).

## Daily controls

| Shortcut | Action |
| --- | --- |
| Super + Enter | Kitty terminal |
| Super + D | Application/search launcher |
| Super + E | Home folder in your default file manager |
| Super + L | Authenticated lock |
| Super + Space | Toggle floating, fit within the window's own monitor and center |
| Super + N | Communications / notifications |
| Super + Escape | System menu; destructive power actions require confirmation |
| Super + Alt + N | Toggle day/night |
| Super + Alt + W | Show/hide selected desktop widgets |
| Super + Alt + S | Preview standby |
| Super + Alt + R | Reload theme components |

The wizard can leave your key bindings alone. Standalone also supplies Super + Q/F, Super + 1…0, Super + Shift + 1…0, Super + H/J/K/semicolon and Super + mouse drag.

```sh
yorha-mode day
yorha-mode night
yorha-desktop toggle
yorha-standby preview
yorha-doctor

yorha-tasks add "Review today's objectives"
yorha-tasks list
yorha-tasks menu
```

Commands live in `~/.local/bin`; add it to your shell's PATH if your distribution does not already do so.

![Rotating standby crest, shown at one frame](docs/images/standby-night.webp)

## Customize and recover

Edit visual sources in `~/.local/share/yorha/modes/{day,night}`, then reapply the mode. Live managed files are regenerated when modes change. Edit monitor/input settings in your own Hyprland config. Toolkit applications may need reopening after a palette switch; application-supplied RGB colors and web content can bypass the theme.

Before replacing a file, the installer saves its contents, permissions or original symlink in a private transaction directory:

```sh
yorha-restore --list
yorha-restore ~/.local/state/yorha/backups/TIMESTAMP --stop-services
# Also works from the clone, including after an interrupted installation:
python3 scripts/restore.py ~/.local/state/yorha/backups/TIMESTAMP --stop-services
```

Recovery checks for subsequent edits before changing files. Save any edits you want to keep, then add `--force` if necessary, including after a palette switch. Recover multiple installation transactions newest first. Backups are retained. Dependencies installed through your package manager remain installed. See [recovery and updates](docs/INSTALL.md#recovery).

## Optional connections

![Calendar and local quests using demo objectives](docs/images/agenda-night.webp)

- [Calendar, quests and monitor behavior](docs/WIDGETS.md)
- [SDDM login theme](docs/SDDM.md)
- [USB/Wi-Fi DroidCam addon](docs/PHONECAM.md)
- [Architecture and development](docs/DEVELOPMENT.md)

The portrait display receives Calendar/Quests when present; otherwise they use the primary physical display. Main panels prefer a landscape display. Layout reduces crowded cards on smaller single-monitor setups. EDID-less outputs are excluded by default; `include_edidless` enables them. Keep your own monitor rotation/scaling configuration. Typical targets are 1920×1080 or larger at 1× and a portrait companion; very small logical displays may need fewer panels. Waybar, widgets and wallpaper skip conventional headless/streaming outputs.

## Validation and scope

File transaction tests cover leaf and parent symlinks, outside-home refusal, interrupted installs, edit protection, idempotent overlay setup, update/restore, dry-run behavior and task revision conflicts. A ready-to-enable [GitHub Actions template](docs/ci-checks.yml) runs these without touching a real desktop; it is not activated in the initial publication. Development checks also stage complete installs, render both palettes, validate generated Hyprland configuration and check SDDM assets.

The first release was staged and rendered on Fedora 42 with Hyprland 0.51.1. Fedora and Arch package scripts are provided; fresh virtual-machine installs and current Arch runtime behavior have **not** been validated. Other distributions require manual dependency installation. This is a Hyprland/Wayland setup; GNOME/KDE sessions and X11 are outside the installer scope. Nonstandard XDG config/data roots are not currently supported.

Phone launchers, personal cloud accounts, private planner servers, streaming servers, GPU drivers and machine-specific monitor layouts are outside this repository. The optional streaming idle guard recognizes `$XDG_RUNTIME_DIR/sunshine-streaming`; your own stream hooks must maintain it.

Original project code/artwork: GPL-3.0-or-later. Third-party files retain their individual licenses; game branding remains with its respective owners. This is an unofficial fan project.
