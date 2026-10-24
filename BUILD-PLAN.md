# Public distribution plan

1. Extract only PC theme code and curated artwork; exclude personal dotfiles, account data, screenshots of live applications, backup manifests, runtime data and the phone project.
2. Make monitor selection, paths, timezone and optional planner connections portable. Provide local tasks without requiring the author's cockpit service.
3. Add a terminal wizard with a readable plan, Fedora/Arch dependency installation, dry run, component selection, standalone/overlay modes, file backups, recovery and diagnostics.
4. Preserve day/night palettes, floating GTK panels, calendar/quests, Sound Waves HUD, wallpapers, lock/standby and application themes. Keep SDDM explicitly optional.
5. Retain third-party licenses and attribution; supply an original crest by default and a checksum-pinned optional upstream game-emblem download.
6. Test in temporary homes, including symlinked dotfiles, install/update/restore, interrupted installs and path validation. Render synthetic day/night previews and scan the complete publication tree for private data.
7. Publish the reviewed initial history under sashavrg/yorha-desktop and verify the public repository.

The existing desktop remains untouched during development and validation.

## Initial release validation

- Explicit payload allowlist; no live account URLs, task snapshots, phone source, private backup manifests or copied personal screenshots.
- 14 automated checks passed: install/update/recovery, symlink handling, path escape refusal, edit protection, interrupted installation, component selection, local task conflicts, complete palette switching and Fedora package preflight.
- Complete staged installations generated all six wallpapers, a pinned calendar venv and both SDDM palettes. Hyprland 0.51.1 parsed the standalone config successfully. Calendar `pip check` and SDDM `--check` passed.
- Both GTK palettes and standby crest front/edge/back angles rendered. Optional checksum-pinned upstream emblem downloaded and parsed successfully.
- ShellCheck and source/publication scans passed. Fresh distro VM deployment, actual login authentication and the optional camera addon remain separate integration checks.
- Fedora source audit found community Hyprland packages; the wizard offers explicit COPR opt-in and preflights missing dependencies. Existing packages are reused.

Publication note: the connected GitHub OAuth app can publish repository contents but lacks workflow-write scope. Automated checks are supplied as `docs/ci-checks.yml`, ready for an authorized maintainer to enable. All 14 checks ran locally before publication.
