#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null; then
    printf 'Install Python 3 first (Fedora: sudo dnf install python3; Arch: sudo pacman -S python).\n' >&2
    exit 1
fi
exec python3 "$project_dir/scripts/wizard.py" "$@"
