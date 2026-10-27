# Installation and recovery

## Prerequisites

Use a working, supported Linux installation with systemd user services and a Wayland-capable GPU. Keep your distribution's working graphics drivers and display-manager configuration. Installing packages does not select Hyprland as your login session: choose **Hyprland** in your existing login manager after setup.

The bootstrap needs Python 3 and Git. On Fedora: `sudo dnf install python3 git`. On Arch: `sudo pacman -S --needed python git`. Run `./install.sh` as your desktop user. Native package lists live in [`scripts/packages.json`](../scripts/packages.json); `scripts/install-deps.sh` installs them separately. Fedora automatically chooses `rofi-wayland` when available, otherwise `rofi` from the enabled repositories. Arch uses the Wayland-capable `rofi` package. Third-party repositories are never enabled implicitly. Fedora may need `--fedora-copr` as described below.

`./scripts/install-deps.sh --distro arch --components desktop,standby,apps` installs the core plus selected package groups. If your distribution lacks a listed package, installation stops; provide it manually, inspect `yorha-doctor`, and retry with `--no-deps`. Derivative distributions require an explicit `--distro` choice or manual installation.

### Fedora package sources

Some required Hyprland companion tools and Starship are absent from Fedora's stock repositories. An existing working native installation is reused. For a fresh setup, the wizard offers an explicit community-source choice, also available through:

```sh
./install.sh --fedora-copr
# Or dependencies alone:
./scripts/install-deps.sh --distro fedora --fedora-copr
```

This installs the DNF 5 plugin package, then asks DNF to enable [`solopasha/hyprland`](https://copr.fedorainfracloud.org/coprs/solopasha/hyprland/) and [`atim/starship`](https://copr.fedorainfracloud.org/coprs/atim/starship/). Review their package sources before opting in. These are community repositories, not official Fedora packages. Starship documents its Fedora COPR in its [official guide](https://starship.rs/guide/). Availability depends on the maintainers supporting your Fedora release. These repository changes are system package-manager state and are not reverted by user-dotfile recovery. Prefer a supported Fedora release, or use an already working stack and `--no-deps`.

Without this option the dependency script preflights enabled repositories and reports missing packages before applying user files. It does not silently skip a required package. Arch's package list uses official repositories and needs no such option.

Python GI, Cairo, NumPy, psutil and fontTools come from native packages. Calendar libraries and their pure Python dependencies are pinned in `calendar-requirements.txt` and installed from PyPI in `~/.local/share/yorha/calendar-venv` with system GI bindings visible. User-site Python packages are disabled for the service runtime. Native package versions follow the distribution; this is reproducible configuration, not a bit-for-bit OS image.

Native dialogs and the Super+R console automatically use a separately installed `hyprland-guiutils`; otherwise they use Rofi. Hyprtoolkit palettes and wrappers are included in every install. See [native UI integration](NATIVE-UI.md) for command discovery, theme customization and safe confirmation previews.

The `apps` component also includes Thunar-specific GTK styling and original archive icons. Thunar is optional; its visual layout is configured separately with `yorha-thunar-layout apply`, which records the previous preferences for `yorha-thunar-layout restore`. See [the explorer guide](EXPLORER.md). The installer does not change your default file manager.

## Wizard choices

| Option | Meaning |
| --- | --- |
| `--layout overlay` | Preserve main Hyprland config and append the managed source once |
| `--layout standalone` | Back up and replace the main config with a minimal baseline |
| `--mode day` / `night` | Initial full palette |
| `--components desktop,agenda,standby,apps` | Select optional pieces; empty string selects only the core |
| `--no-bindings` | Do not override existing shortcuts |
| `--keyboard us` | Standalone XKB layout, e.g. `it` or `us,de` |
| `--fedora-copr` | Explicitly enable the two documented community repositories on Fedora |
| `--deps` / `--no-deps` | Install native packages / use existing prerequisites |
| `--sddm` | Stage greeter and print separate privileged installation command |
| `--phonecam` | Add DroidCam button; CLI/loopback setup remains separate |
| `--activate` | Reload Hyprland, restart Waybar and selected widgets now |
| `--dry-run` | Plan only, with no network access or writes |
| `--target PATH` | Stage in a different home; requires `--no-deps`, prohibits activation |
| `--no-assets`, `--no-venv` | Test/staging shortcuts; result is incomplete for normal daily use |

Every normal install uses the YoRHa game emblem, including unattended installs. Its SVG is downloaded from the checksum-pinned source described in [asset credits](../THIRD_PARTY.md), so internet access is required. If that download fails or its checksum differs, staging stops before managed user files are replaced. There is no logo selection or alternative crest. The old `--game-emblem` flag is still accepted for compatibility but is no longer needed. `--no-assets` skips the emblem download and wallpaper generation for incomplete test/staging installs. `--dry-run` never downloads anything.

Overlay preserves the *main* config and its existing startup. It still replaces managed application configuration files and selected shortcut bindings. Review the plan. If another framework autostarts a second bar, notification daemon or wallpaper recoloring script, disable its conflicting commands in your own configuration. The guarded startup helper avoids launching duplicate standard process names but cannot control other frameworks' custom services.

The installer preflights every managed destination. Parent symlinks inside the selected home are supported (including Stow-style dotfiles). Leaf symlinks are saved and replaced without writing through them. A parent link outside the selected home is refused: put a managed config inside your home before retrying.

After install, add `~/.local/bin` to your shell PATH if needed:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Persist that line in your preferred shell configuration. The installer does not overwrite shell startup files. For Starship, add its normal shell initialization yourself; for example `eval "$(starship init bash)"` in Bash. The Neovim colorscheme is installed without replacing your editor setup; load it with `:colorscheme yorha`. Btop's palette is available as `yorha` in its theme selector. These optional apps keep their own startup/settings choices.

### Overlay workspace movement

Overlay mode retains your existing numbered workspace-move bindings. To make floating windows keep the same percentage width, height and placement when moving between monitors, change those bindings to execute `"$HOME/.local/bin/yorha-move-workspace" NUMBER`, where NUMBER is 1–10. Match the key or keycode used by your existing binding when replacing it, so both actions do not run on the same shortcut. Standalone mode installs the helper bindings automatically.

## Recovery

Every managed write is preceded by a private backup record under `~/.local/state/yorha/backups`. The backup manifest is updated before each destination is changed. A caught installation error rolls back file changes. A hard process kill/power loss leaves a recoverable manifest; use the restore script printed near the start of installation.

```sh
python3 scripts/restore.py ~/.local/state/yorha/backups/TIMESTAMP --stop-services
```

Or use the installed `yorha-restore` helper. Its recovery source is copied into the installed tree, so it remains available if the original clone moves. Keep the clone/recovery script available while restoring multiple older transactions; the earliest restore removes the installed helper itself.

If recovery reports subsequent edits, copy those edits somewhere safe and rerun with `--force`. A day/night switch also changes managed live palettes and can trigger this check. Restore preflights the complete manifest before touching files. Restore transactions newest first; do not reuse an already restored transaction after making new changes. Recovery restores user files and symlinks, removes files introduced by that transaction, and removes a calendar venv created by it. A runtime rebuild restores the complete previous environment, including its original symlinks. Empty parent directories and backup records remain. Local task/calendar data added after install is not part of the managed payload, and is not removed.

`--stop-services` stops the three desktop/audio widget units in the real home before recovery and reloads the user service manager afterward. It does not log out, change your wallpaper live, uninstall packages, revert user edits to shell startup or change system account/GTK database settings. Log out and in when convenient for the restored session to take effect.

SDDM has its own root-owned backup and separate restore procedure in [SDDM.md](SDDM.md).

## Update

Read changes, `git pull --ff-only`, then rerun the wizard with the same options. Every update creates another transaction. Private settings, task state and calendar URLs are preserved on reinstall. Existing working calendar venvs are reused. If a distribution Python upgrade makes that runtime unusable, the wizard backs up the complete old environment and rebuilds it for the current interpreter. A rebuild failure rolls back both the runtime and managed file changes. Read [the upgrade checklist](UPGRADING.md) before applying a new desktop stack.

Disabling optional components removes their startup markers on the next install. Already running services stop at logout; use `systemctl --user stop yorha-desktop yorha-cockpit-widget` as appropriate to stop them immediately. Optional source/theme files may remain installed but inactive.
