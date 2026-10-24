# Development

## Tree

- `install.sh`: Python-stdlib terminal wizard bootstrap.
- `scripts/wizard.py`: choices, plan, source staging, optional generation, transaction and activation.
- `scripts/install_lib.py`: backup/write/recovery primitives; no live service or package operations.
- `scripts/dependencies.py`, `packages.json`: native dependency groups for Fedora/Arch and explicit optional Fedora COPR setup.
- `payload`: explicit distributable source/config allowlist. Private source machine dotfiles are never exported at runtime.
- `payload/.local/share/yorha`: GTK desktop/calendar code, renderer, shared Sound Waves daemon, palettes and optional greeter.
- `addons/phonecam`: opt-in DroidCam process controller and USB/local-Wi-Fi connector.
- `tests`: disposable-home transaction and task-state checks.

`@HOME@` and `@RUNTIME@` tokens are rendered into destination configuration. Systemd units use `%h`; runtime spectrum data lives in the user's runtime directory. No account URLs, real task snapshots, user IDs, GPU driver settings or named physical outputs belong in payload files.

The theme uses standard `~/.config` and `~/.local` roots. Alternate `--target` homes are for staging and cannot activate the live session. `--no-assets --no-venv --no-deps` permits network-free file transaction tests on plain Python.

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check-source.py
shellcheck install.sh scripts/install-deps.sh
./install.sh --dry-run --distro fedora
```

Use a disposable home for a complete native smoke test after installing prerequisites:

```sh
test_home=$(mktemp -d)
./install.sh --yes --no-deps --layout standalone --target "$test_home" --sddm
HOME="$test_home" Hyprland --verify-config --config "$test_home/.config/hypr/hyprland.conf"
python3 "$test_home/.local/share/yorha/sddm/install.py" --check
```

`--verify-config` is supported by the Hyprland version used during development; inspect `Hyprland --help` before using it elsewhere. It parses config without starting a compositor or executing `exec-once` commands.

`tests/` does not require GTK, a display, GitHub credentials, native package installation or network. Full GTK renders, actual audio I/O and distribution package installation require separate integration validation. The included `docs/ci-checks.yml` template never applies the theme to a runner desktop. To enable it, copy it to `.github/workflows/checks.yml` and commit using a GitHub connection with workflow-write permission. Initial publication leaves it as a template because the connected OAuth app lacks that scope.

## Public previews

`desktop-shell.py --render-preview FILE` renders an offscreen 2560×1440 desktop. Preview mode uses synthetic telemetry/metadata and a generic hostname. Set `YORHA_PREVIEW_MODE=day` or `night`; point HOME to a disposable staged install so no private calendar/settings can be read.

`cockpit-widget.py --render-preview FILE` uses that disposable home's local tasks/feed settings. Never render public examples from a home containing a personal calendar URL. Use made-up demo tasks. `standby.py` can be imported to draw a still using `Scene.draw`; its normal `preview` action opens an actual dismissible window.

## License and contributions

Project source is GPL-3.0-or-later except separately identified third-party material. Preserve attribution, avoid committing generated environments/runtime state, and add meaningful tests for installation/recovery changes. Keep optional integrations opt-in. Report distro and Hyprland versions with bugs, after reviewing diagnostics for personal information.
