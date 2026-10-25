# Fedora 44 / Hyprland 0.56 upgrade audit

Validated 2026-10-25 on Fedora 44, Python 3.14.8 and Hyprland 0.56.2. This is an upgrade of a working desktop; a fresh VM installation and Arch runtime remain separate validation targets.

## Problems fixed

- A Python 3.13 calendar virtual environment lost its installed libraries when `/usr/bin/python3` became Python 3.14. The installer now probes an existing runtime and, if necessary, backs it up before rebuilding. Recovery restores the previous directory and interpreter links. Calendar configuration and task data are outside that environment.
- New GdkPixbuf/Glycin SVG sniffing rejected recolored XML serialized with an `ns0:svg` root as `text/plain`. The media panel now serializes an explicit default SVG namespace and XML declaration. A native regression check loads the recolored crest in both palettes and verifies its pixels.
- `workspaceopt allfloat` is retired. Super+Alt+Space uses a reversible helper instead. It records only originally tiled windows, fits them inside their monitor's work area, and restores those windows on the next toggle. Pre-existing floating dialogs remain floating.
- Browser launching now resolves the actual default HTTPS application through Gio and opens `about:blank`; it no longer sends an incomplete `https://` URL. Super+A uses the existing Rofi window overview rather than requiring a legacy AGS installation.
- `yorha-doctor` checks selected services and the actual calendar/widget Python environment, including older installations without the new marker files. It finds a single running Hyprland instance when invoked from a terminal/SSH environment missing the compositor variables, and flags retired `workspaceopt` shortcuts.

## Personal dotfiles migrating from older Hyprland

The public standalone configuration already avoids the removed settings. For a separate older configuration:

```ini
# Old: windowrulev2 = float, class:^(Example)$
windowrule = match:class ^(Example)$, float on
# Old: layerrule = blur, example-layer
layerrule = match:namespace example-layer, blur on
# Old: bind = SUPER SHIFT, I, togglesplit
bind = SUPER SHIFT, I, layoutmsg, togglesplit
```

Remove the obsolete `dwindle:pseudotile` and `misc:vfr` settings; the per-window `pseudo` dispatcher is still supported by 0.56. Inactive plugin configuration can contain options the new compositor rejects: remove/comment obsolete settings when the plugin is not loaded. Keep gaming/NVIDIA/monitor workarounds specific to the machine where they were verified. The `.conf` format is validated here specifically on 0.56.2; this is not a guarantee for later config-format changes.

## Browser-specific GPU failures

The audit encountered an older Zen AppImage crashing with `wp_image_description_v1 has no event 2` through the upgraded NVIDIA Wayland stack. A per-application desktop-entry override using `MOZ_ENABLE_WAYLAND=0 GDK_BACKEND=x11 EGL_PLATFORM=x11` launched it successfully through XWayland. This workaround belongs in that application's local launcher; the public theme does not force X11 or NVIDIA variables on all browsers. Review an application's current release before assuming every browser needs the same override.

## Verification performed

| Check | Result |
| --- | --- |
| 16 automated checks, including native SVG loading | Passed on Fedora 44 |
| Real old-Python venv rebuild and transaction recovery | Passed |
| Installed and newly staged standalone `Hyprland --verify-config` | Passed |
| Live day/night switch, all managed files compared, then restored to original mode | Passed |
| Waybar, Rofi applications/window overview, notifications and fresh Kitty window | Opened successfully |
| Main desktop panels on landscape; agenda only on portrait; none on streaming output | Confirmed with layer inspection |
| Single-window floating/centering within reserved work area, landscape and rotated portrait | Passed |
| Workspace float/restore with an existing floating dialog | Passed |
| Default-browser launch after local app-specific repair | Passed |
| Standby preview and clean dismissal | Passed |
| Shared Cava analyser and graphical spectrum output | Running |
| SDDM offscreen test using existing installed theme | Opened without QML/image errors |
| Desktop, agenda and audio services after the audit | Active, no restart loops |

Lock bindings and configuration were inspected; authenticated lock/unlock, suspend/shutdown, actual SDDM authentication, an active Moonlight stream and USB/Wi-Fi video frames were not triggered by the audit. Tests never changed planner tasks or calendar events. Private captures/logs stay outside the repository.

For your own upgrade:

```sh
yorha-doctor
Hyprland --verify-config --config "$HOME/.config/hypr/hyprland.conf"
yorha-mode day
yorha-mode night
systemctl --user status yorha-desktop yorha-cockpit-widget yorha-soundwave
```

Run GUI commands in the intended session, with its normal `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY` and D-Bus environment. Reapply whichever palette you prefer after testing.
