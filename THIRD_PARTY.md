# Artwork and third-party notices

This unofficial fan theme is inspired by NieR:Automata's menu, quest log and HUD. NieR:Automata, YoRHa and associated game branding belong to Square Enix / PlatinumGames. This repository is not affiliated with or endorsed by them.

## Original project assets

The procedural mesh/traces/rings wallpaper generator, desktop panel layout, native Sound Waves geometry and installer are project source distributed under GPL-3.0-or-later. Generated wallpapers are made locally; game screenshots, the author's concept reference image and character illustrations are not redistributed.

Visual references: [Interface In Game menu archive](https://interfaceingame.com/games/nierautomata/) and the game's HUD: Sound Waves chip. Reference captures are not included in this repository. README previews are newly rendered with synthetic metadata/local demo tasks; they are not screenshots of the author's accounts or desktop session.

## Game emblem download

Every normal install downloads gigsoll's [community SVG trace](https://github.com/gigsoll/YoRHaLogo) from one pinned revision, verifies its SHA-256, crops the viewBox and removes editor metadata. Source: `YORHA_clear.svg`, revision `5e24e32cae8a3028b87676f87a58962182975115`; SHA-256 `fa1e237c8f19685d41554942f0180e5f7fe278546a0685f3c09d48c882352477`.

The upstream repository does not supply a license grant. The trace is **not bundled** and is **not covered by this project's GPL**; it is fetched separately during installation. The underlying game emblem remains its owners' artwork. Attribution does not grant redistribution rights. The YoRHa emblem is the only supplied logo option; there is no bundled alternative crest.

## SDDM

`payload/.local/share/yorha/sddm/YoRHa` includes modified Sequoia 1.5 components by minMelody, GPLv3. [Upstream](https://codeberg.org/minMelody/sddm-sequoia). The original license and QML notices are retained there. YoRHa layout/colors/assets are local modifications. The bundled JetBrains Mono Nerd Font icon font retains its SIL OFL license at `assets/OFL.txt`; no proprietary Favorit font is shipped.

## Qt/Kvantum

The two `payload/.config/Kvantum/YoRHa*` themes are recolored derivatives of Catppuccin Latte assets by elkrien based on Arc Dark. Existing author metadata is retained. [Catppuccin Kvantum upstream](https://github.com/catppuccin/kvantum) uses MIT; see `LICENSES/Catppuccin-Kvantum-MIT.txt`. The inherited Kvantum/Arc theme lineage and GPL text are preserved through `LICENSES/Kvantum-GPL-3.0.txt` and the root GPL. This project does not claim exclusive authorship of these theme resources.

## System assets and dependencies

Breeze icons are installed from distribution packages and used through inheritance; GTK themes import the system Adwaita base. The author's recolored icon collection is not redistributed. Noto Sans and JetBrains Mono text fonts are also distribution packages. Native applications and Python dependencies retain their upstream licenses. Installing optional DroidCam does not make it part of this repository or the project's license.
