# Optional login screen

Choose `--sddm` in the wizard to prepare assets. This does not select a display manager or alter authentication/PAM. After review, on a system already using SDDM with Qt 6:

```sh
python3 ~/.local/share/yorha/sddm/install.py --check
sudo python3 ~/.local/share/yorha/sddm/install.py --mode night
```

Use `--mode day` for the parchment greeter. Desktop palette changes do not change the root-owned greeter automatically. SDDM must already be installed and selected by the administrator; this project does not disable GDM/LightDM or enable a display-manager service.

The installer backs up the previous theme and override under `/var/backups/yorha-sddm/TIMESTAMP`, copies a root-owned theme into `/usr/share/sddm/themes/YoRHa` and writes `/etc/sddm.conf.d/zzzzzz-yorha.conf`. It reapplies SELinux labels when `restorecon` exists. It never restarts SDDM or ends the active session. The greeter appears on the next ordinary login.

The command prints its exact recovery path:

```sh
sudo python3 ~/.local/share/yorha/sddm/install.py --restore /var/backups/yorha-sddm/TIMESTAMP
```

Restore SDDM before removing the user theme source if you still need that script. Components derive from Sequoia under GPLv3; the included icon font retains its OFL license. Both palettes and portrait/landscape assets are generated from the selected crest and procedural wallpaper source.
