#!/usr/bin/env python3
"""Configure a private Google Calendar iCal feed for the YoRHa desktop widget."""
from __future__ import annotations

import getpass
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".config/yorha/calendar-feed-url"
MAX_BYTES = 5 * 1024 * 1024


def fetch_and_validate(url: str) -> int:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "calendar.google.com" or not parsed.path.startswith("/calendar/ical/"):
        raise ValueError("Expected the HTTPS secret iCal address from Google Calendar settings")
    request = urllib.request.Request(url, headers={"Accept": "text/calendar"})
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise ValueError("Google Calendar did not return a calendar feed")
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("Calendar feed is larger than 5 MB")
    if b"BEGIN:VCALENDAR" not in body[:4096]:
        raise ValueError("The address did not return an iCalendar feed")
    from icalendar import Calendar
    cal = Calendar.from_ical(body)
    if cal.name != "VCALENDAR":
        raise ValueError("The address did not return an iCalendar feed")
    return sum(1 for component in cal.walk() if component.name == "VEVENT")


def set_feed() -> int:
    url = getpass.getpass("Paste Google Calendar's secret iCal address (input hidden): ").strip()
    try:
        event_count = fetch_and_validate(url)
    except Exception as exc:
        # Never print the exception: HTTP errors can contain the private URL.
        print(f"Feed check failed ({type(exc).__name__}). No URL was saved.", file=sys.stderr)
        return 1
    CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    CONFIG.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(prefix=".calendar-feed-", dir=CONFIG.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(url + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, CONFIG)
        CONFIG.chmod(0o600)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    print(f"Read-only calendar feed saved locally ({event_count} events found).")
    print("Restart the widget with: systemctl --user restart yorha-cockpit-widget.service")
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    if command == "set":
        return set_feed()
    if command == "status":
        if CONFIG.is_file():
            print("Private calendar feed is configured locally.")
        else:
            print("No private calendar feed configured. Run: yorha-calendar-feed set")
        return 0
    if command == "remove":
        try:
            CONFIG.unlink()
            print("Private calendar feed removed.")
        except FileNotFoundError:
            print("No private calendar feed was configured.")
        return 0
    print("Usage: yorha-calendar-feed [set|status|remove]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
