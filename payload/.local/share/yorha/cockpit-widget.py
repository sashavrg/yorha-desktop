#!/usr/bin/python3
"""YoRHa cockpit agenda surface, rendered between wallpaper and app windows."""

from __future__ import annotations

import calendar
import argparse
import desktop_ui
import planner_store
import settings
import copy
import json
import sys
import subprocess
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell, Pango
from icalendar import Calendar
import recurring_ical_events

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import cockpit_agenda  # noqa: E402

ASSETS = Path.home() / ".local/share/yorha"
MODE_FILE = ASSETS / "mode"
PLANNER_URL = cockpit_agenda.PLANNER_URL
CALENDAR_FEED_FILE = Path.home() / ".config/yorha/calendar-feed-url"
TZ = settings.timezone()
REFRESH_SECONDS = 60
CALENDAR_CACHE_SECONDS = 300
CALENDAR_MAX_BYTES = 5 * 1024 * 1024



def current_mode() -> str:
    return desktop_ui.mode()


def add_class(widget: Gtk.Widget, name: str) -> Gtk.Widget:
    for token in name.split():
        widget.get_style_context().add_class(token)
    return widget


def label(text: str, css_class: str = "", align: float = 0.0) -> Gtk.Label:
    item = Gtk.Label(label=text)
    item.set_xalign(align)
    item.set_yalign(0.5)
    item.set_line_wrap(True)
    item.set_max_width_chars(42)
    item.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if css_class:
        add_class(item, css_class)
    return item


class CockpitAgenda:
    def __init__(self, preview: bool = False) -> None:
        self.provider = Gtk.CssProvider()
        self.windows: list[Gtk.Window] = []
        self.current_palette = ""
        self.selected_day = datetime.now(TZ).date()
        self.state: dict | None = None
        self.api_error = ""
        self.loading = False
        self.mutating_ids: set[str] = set()
        self.state_lock = threading.Lock()
        self.calendar_feed: Calendar | None = None
        self.calendar_error = "loading"
        self.calendar_loading = False
        self.calendar_fetched_at = 0.0
        self.calendar_lock = threading.Lock()
        self.update_palette(force=True)
        display = Gdk.Display.get_default()
        if display is None:
            raise RuntimeError("No graphical display is available")
        self.display = display
        if not preview:
            self.retarget()
            display.connect("monitor-added", self.monitors_changed)
            display.connect("monitor-removed", self.monitors_changed)
        self.refresh()
        self.fetch_state_async()
        self.fetch_calendar_async(force=True)
        GLib.timeout_add_seconds(REFRESH_SECONDS, self.periodic_refresh)
        GLib.timeout_add_seconds(2, self.palette_tick)

    def monitors_changed(self, *_args) -> None:
        GLib.timeout_add(300, self.retarget)

    def retarget(self) -> bool:
        for window in self.windows:
            window.destroy()
        self.windows.clear()
        display = self.display
        physical = settings.physical_monitors(display)
        # Prefer the vertical portrait display when connected. Otherwise use one
        # primary physical display, falling back to the first physical output.
        vertical = [m for m in physical if m.get_geometry().height > m.get_geometry().width]
        primary = display.get_primary_monitor()
        if vertical:
            target = next((m for m in vertical if m == primary), vertical[0])
        elif primary in physical:
            target = primary
        elif physical:
            target = physical[0]
        else:
            target = None
        if target is not None:
            self.windows.append(self.make_window(target))
        self.refresh()
        return False

    def palette_tick(self) -> bool:
        self.update_palette()
        return True

    def update_palette(self, force: bool = False) -> None:
        mode = current_mode()
        if mode == self.current_palette and not force:
            return
        desktop_ui.load_style(self.provider, mode)
        self.current_palette = mode

    def make_window(self, monitor: Gdk.Monitor) -> Gtk.Window:
        window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        window.set_name("yorha-cockpit-agenda")
        add_class(window, "yorha-desktop")
        window.set_title("YoRHa / Cockpit Agenda")
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_skip_taskbar_hint(True)
        window.set_skip_pager_hint(True)
        window.set_app_paintable(True)
        visual = window.get_screen().get_rgba_visual()
        if visual:
            window.set_visual(visual)
        GtkLayerShell.init_for_window(window)
        GtkLayerShell.set_namespace(window, "yorha-cockpit-agenda")
        GtkLayerShell.set_layer(window, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_monitor(window, monitor)
        GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.NONE)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(window, edge, False)
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(window, GtkLayerShell.Edge.TOP, 244)
        GtkLayerShell.set_margin(window, GtkLayerShell.Edge.RIGHT, 64)
        GtkLayerShell.set_exclusive_zone(window, -1)
        window.yorha_max_height = max(200, monitor.get_geometry().height - 324)
        window.set_default_size(480, 1)
        return window

    def move_month(self, amount: int) -> None:
        year, month = self.selected_day.year, self.selected_day.month + amount
        while month < 1:
            year, month = year - 1, month + 12
        while month > 12:
            year, month = year + 1, month - 12
        self.selected_day = date(year, month, min(self.selected_day.day, calendar.monthrange(year, month)[1]))
        self.refresh()

    def select_day(self, chosen: date) -> None:
        self.selected_day = chosen
        self.refresh()

    def calendar_widget(self) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=7, row_spacing=2)
        grid.set_name("agenda-calendar")
        grid.set_hexpand(True)
        grid.set_column_homogeneous(True)
        for col, name in enumerate(("MO", "TU", "WE", "TH", "FR", "SA", "SU")):
            grid.attach(label(name, "weekday", 0.5), col, 0, 1, 1)
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(self.selected_day.year, self.selected_day.month)
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if not day:
                    grid.attach(Gtk.Label(), col, row, 1, 1)
                    continue
                chosen = date(self.selected_day.year, self.selected_day.month, day)
                classes = "day"
                if chosen == datetime.now(TZ).date():
                    classes += " today"
                if chosen == self.selected_day:
                    classes += " selected"
                item = Gtk.Button()
                item.get_style_context().add_class("day")
                for css_class in classes.split()[1:]:
                    item.get_style_context().add_class(css_class)
                item.set_relief(Gtk.ReliefStyle.NONE)
                item.add(label(f"{day:02d}", "", 0.5))
                item.connect("clicked", lambda _button, value=chosen: self.select_day(value))
                grid.attach(item, col, row, 1, 1)
        return grid

    def tasks_box(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        key = self.selected_day.isoformat()
        items = (self.state or {}).get("items", [])
        tasks = [task for task in items if task.get("day") == key]
        tasks.sort(key=lambda task: (bool(task.get("done")), task.get("time") or "", task.get("title", "").casefold()))
        if self.api_error:
            content.pack_start(label("Planner unavailable · " + self.api_error, "muted"), False, False, 0)
        elif self.state is None:
            content.pack_start(label("Syncing planner…", "muted"), False, False, 0)
        elif not tasks:
            content.pack_start(label("No planner tasks for this date", "muted"), False, False, 0)
        else:
            for task in tasks:
                task_id = str(task.get("id", ""))
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
                check = Gtk.CheckButton()
                check.get_style_context().add_class("task-check")
                check.set_active(bool(task.get("done")))
                check.set_sensitive(task_id not in self.mutating_ids)
                check.connect("toggled", self.toggle_task, task_id)
                row.pack_start(check, False, False, 0)
                title = (task.get("title") or "Untitled task").strip()
                if task.get("time"):
                    title = f"{task['time']}  /  {title}"
                text = label(title, "task-complete" if task.get("done") else "task-title")
                text.set_ellipsize(Pango.EllipsizeMode.END)
                row.pack_start(text, True, True, 0)
                content.pack_start(row, False, False, 0)
        return content

    def calendar_events_box(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if self.calendar_error == "loading" and self.calendar_feed is None:
            content.pack_start(label("Syncing calendar…", "muted"), False, False, 0)
            return content
        if self.calendar_error == "not-configured":
            content.pack_start(label("No calendar feed configured", "muted"), False, False, 0)
            content.pack_start(label("Run yorha-calendar-feed set to connect Google Calendar", "interaction-hint"), False, False, 0)
            return content
        if self.calendar_error and self.calendar_feed is None:
            content.pack_start(label("Calendar feed unavailable; check network or feed access", "muted"), False, False, 0)
            return content
        if self.calendar_feed is None:
            content.pack_start(label("No calendar events for this date", "muted"), False, False, 0)
            return content

        day = self.selected_day
        start = datetime.combine(day, datetime.min.time(), TZ)
        end = start + timedelta(days=1)
        try:
            occurrences = recurring_ical_events.of(self.calendar_feed).between(start, end)
            events = []
            for event in occurrences:
                if str(event.get("STATUS", "CONFIRMED")).upper() == "CANCELLED" or not event.get("DTSTART"):
                    continue
                begins = event.decoded("DTSTART")
                local_day = begins.astimezone(TZ).date() if isinstance(begins, datetime) and begins.tzinfo else (
                    begins.date() if isinstance(begins, datetime) else begins
                )
                if local_day == day:
                    events.append(event)
            def event_order(event):
                begins = event.decoded("DTSTART")
                if isinstance(begins, datetime):
                    local = begins.astimezone(TZ) if begins.tzinfo else begins.replace(tzinfo=TZ)
                else:
                    local = datetime.combine(begins, datetime.min.time(), TZ)
                return local
            events.sort(key=event_order)
        except Exception:
            content.pack_start(label("Calendar feed could not be read", "muted"), False, False, 0)
            return content

        if not events:
            content.pack_start(label("No calendar events for this date", "muted"), False, False, 0)
            return content
        for event in events[:6]:
            start_value = event.decoded("DTSTART")
            end_value = event.decoded("DTEND") if event.get("DTEND") else None
            if isinstance(start_value, datetime):
                local_start = start_value.astimezone(TZ) if start_value.tzinfo else start_value.replace(tzinfo=TZ)
                time_text = local_start.strftime("%H:%M")
                if isinstance(end_value, datetime):
                    local_end = end_value.astimezone(TZ) if end_value.tzinfo else end_value.replace(tzinfo=TZ)
                    time_text += "–" + local_end.strftime("%H:%M")
            else:
                time_text = "ALL DAY"
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
            row.pack_start(label(time_text, "event-time"), False, False, 0)
            title = label(str(event.get("SUMMARY", "Untitled event")).strip(), "event-title")
            title.set_ellipsize(Pango.EllipsizeMode.END)
            row.pack_start(title, True, True, 0)
            content.pack_start(row, False, False, 0)
        if len(events) > 6:
            content.pack_start(label(f"+ {len(events) - 6:02d} more events", "muted"), False, False, 0)
        if self.calendar_error:
            content.pack_start(label("Feed refresh failed; showing last saved view", "interaction-hint"), False, False, 0)
        return content

    def fetch_calendar_async(self, force: bool = False) -> None:
        with self.calendar_lock:
            if self.calendar_loading or (not force and time.monotonic() - self.calendar_fetched_at < CALENDAR_CACHE_SECONDS):
                return
            self.calendar_loading = True

        def worker() -> None:
            feed = None
            error = ""
            try:
                url = CALENDAR_FEED_FILE.read_text(encoding="utf-8").strip()
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme != "https" or parsed.hostname != "calendar.google.com" or not parsed.path.startswith("/calendar/ical/"):
                    raise ValueError("invalid feed")
                request = urllib.request.Request(url, headers={"Accept": "text/calendar"})
                with urllib.request.urlopen(request, timeout=12) as response:
                    raw = response.read(CALENDAR_MAX_BYTES + 1)
                if len(raw) > CALENDAR_MAX_BYTES or b"BEGIN:VCALENDAR" not in raw[:4096]:
                    raise ValueError("invalid calendar response")
                feed = Calendar.from_ical(raw)
                if feed.name != "VCALENDAR":
                    raise ValueError("invalid calendar response")
            except FileNotFoundError:
                error = "not-configured"
            except Exception:
                # HTTP errors may contain the secret feed URL; keep details out of UI/logs.
                error = "refresh-failed"
            with self.calendar_lock:
                self.calendar_loading = False
                self.calendar_fetched_at = time.monotonic()
            GLib.idle_add(self.receive_calendar, feed, error)

        threading.Thread(target=worker, daemon=True).start()

    def receive_calendar(self, feed: Calendar | None, error: str) -> bool:
        if feed is not None:
            self.calendar_feed = feed
        self.calendar_error = error
        self.refresh()
        return False

    @staticmethod
    def api_request(method: str = "GET", payload: dict | None = None, rev: int | None = None) -> dict:
        if not PLANNER_URL:
            return planner_store.write(payload, rev) if payload is not None else planner_store.read()
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if rev is not None:
            headers["If-Match"] = str(rev)
        request = urllib.request.Request(f"{PLANNER_URL}/api/state", data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_state_async(self) -> None:
        with self.state_lock:
            if self.loading:
                return
            self.loading = True
        def worker() -> None:
            try:
                result, error = self.api_request(), ""
            except Exception as exc:
                result, error = None, type(exc).__name__
            with self.state_lock:
                self.loading = False
            GLib.idle_add(self.receive_state, result, error)
        threading.Thread(target=worker, daemon=True).start()

    def receive_state(self, state: dict | None, error: str) -> bool:
        if state is not None:
            self.state = state
        self.api_error = error
        self.refresh()
        return False

    def toggle_task(self, check: Gtk.CheckButton, task_id: str) -> None:
        if task_id in self.mutating_ids:
            return
        self.mutating_ids.add(task_id)
        check.set_sensitive(False)
        done = check.get_active()
        def worker() -> None:
            try:
                state = self.api_request()
                for _ in range(3):
                    next_state = copy.deepcopy(state)
                    task = next((item for item in next_state.get("items", []) if str(item.get("id")) == task_id), None)
                    if task is None:
                        raise RuntimeError("Task no longer exists")
                    stamp = datetime.now(TZ).isoformat()
                    task.update({"done": done, "done_at": stamp if done else None, "updated": stamp})
                    try:
                        state = self.api_request("PUT", next_state, state["rev"])
                        break
                    except planner_store.Conflict as exc:
                        state = exc.state
                    except urllib.error.HTTPError as exc:
                        if exc.code != 409:
                            raise
                        state = json.loads(exc.read().decode("utf-8"))
                else:
                    raise RuntimeError("Planner changed repeatedly; try again")
                error = ""
            except Exception as exc:
                state, error = None, type(exc).__name__
            GLib.idle_add(self.finish_toggle, task_id, state, error)
        threading.Thread(target=worker, daemon=True).start()

    def finish_toggle(self, task_id: str, state: dict | None, error: str) -> bool:
        self.mutating_ids.discard(task_id)
        if state is not None:
            self.state = state
        self.api_error = error
        self.refresh()
        return False

    def schedule_box(self, meetings: list[str]) -> Gtk.Box:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        events = [item for item in meetings if not item.startswith("NEXT  ")]
        next_events = [item[6:] for item in meetings if item.startswith("NEXT  ")]
        if events:
            for item in events:
                content.pack_start(label("›  " + item, "objective"), False, False, 0)
        else:
            content.pack_start(label("No meetings remaining today", "muted"), False, False, 0)
        for item in next_events:
            content.pack_start(label("NEXT  /  " + item, "muted"), False, False, 0)
        return content

    def objective_box(self, focus: list[str]) -> Gtk.Box:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        groups: dict[str, list[str]] = defaultdict(list)
        for item in focus:
            if "  " in item:
                category, task = item.split("  ", 1)
                groups[category].append(task)
        primary = groups.get("JOB SEARCH", [])
        if primary:
            active = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            active.pack_start(label("◆", "task-tag"), False, False, 0)
            active.pack_start(label(primary[0], "objective-primary"), True, True, 0)
            content.pack_start(active, False, False, 0)
            for task in primary[1:]:
                content.pack_start(label("◇  " + task, "objective-secondary"), False, False, 0)
        elif focus:
            content.pack_start(label("◇  " + focus[0].split("  ", 1)[-1], "objective-primary"), False, False, 0)

        side = [(category, task) for category, tasks in groups.items()
                if category != "JOB SEARCH" for task in tasks]
        if side:
            if primary:
                content.pack_start(label("SIDE OPERATIONS", "section"), False, False, 3)
            for category, task in side:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.pack_start(label("◇", "task-tag"), False, False, 0)
                item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                item.pack_start(label(category, "task-tag"), False, False, 0)
                item.pack_start(label(task, "objective-secondary"), False, False, 0)
                row.pack_start(item, True, True, 0)
                content.pack_start(row, False, False, 0)
        if not focus:
            content.pack_start(label("No active objectives in today's cockpit snapshot", "muted"), False, False, 0)
        return content

    def build_card(self) -> Gtk.Widget:
        self.update_palette()
        now = datetime.now(TZ)
        try:
            source = cockpit_agenda.TODAY_FILE.read_text(encoding="utf-8")
            meetings, focus, todo_status, snapshot = cockpit_agenda.cockpit_sections(source, now)
        except OSError:
            meetings, focus, todo_status, snapshot = [], [], [], "unavailable"
        stale = snapshot != now.strftime("%Y-%m-%d")
        if stale:
            focus, meetings, todo_status = [], [], []
        root = add_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=28), "desktop-root")
        calendar_panel, body = desktop_ui.panel("Calendar", "01", 464)
        root.pack_start(calendar_panel, False, False, 0)
        body.pack_start(label(now.strftime("%A  /  %d %B %Y").upper(), "date"), False, False, 0)
        month_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        month_row.pack_start(label(self.selected_day.strftime("%B %Y").upper(), "month"), True, True, 0)
        for caption, delta in [("‹", -1), ("›", 1)]:
            button = add_class(Gtk.Button(label=caption), "month-nav")
            button.connect("clicked", lambda _b, amount=delta: self.move_month(amount))
            month_row.pack_start(button, False, False, 0)
        body.pack_start(month_row, False, False, 0)
        body.pack_start(self.calendar_widget(), False, True, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)
        body.pack_start(label("SCHEDULE  /  " + self.selected_day.strftime("%d %b").upper(), "section"), False, False, 0)
        body.pack_start(self.calendar_events_box(), False, False, 0)
        body.pack_start(label("Select a date to view its schedule", "interaction-hint"), False, False, 0)

        quest_panel, body = desktop_ui.panel("Quests", "02", 464)
        root.pack_start(quest_panel, False, False, 0)
        body.pack_start(label("PLANNER TASKS  /  " + self.selected_day.strftime("%d %b %Y").upper(), "section"), False, False, 0)
        body.pack_start(self.tasks_box(), False, False, 0)
        body.pack_start(label("Check an objective to update the planner", "interaction-hint"), False, False, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)
        if stale and settings.load().get("cockpit_file"):
            body.pack_start(label("COCKPIT  /  AWAITING UPDATE", "section"), False, False, 0)
            body.pack_start(label("Today's cockpit objectives have not been refreshed.", "muted"), False, False, 0)
        elif focus:
            body.pack_start(label("ACTIVE OBJECTIVE", "section"), False, False, 0)
            body.pack_start(self.objective_box(focus), False, False, 0)
        if todo_status:
            body.pack_start(Gtk.Separator(), False, False, 0)
            for status in todo_status[:3]:
                body.pack_start(label("·  " + status.strip(), "muted"), False, False, 0)
        button = Gtk.Button()
        button.set_name("planner-button")
        button.add(label("OPEN PLANNER  ↗" if PLANNER_URL else "EDIT LOCAL QUESTS  ↗", "planner-label", 0.5))
        button.connect("clicked", self.open_planner)
        body.pack_start(button, False, False, 0)
        return root

    @staticmethod
    def open_planner(_button: Gtk.Button) -> None:
        subprocess.Popen(["xdg-open", PLANNER_URL] if PLANNER_URL else [str(Path.home()/".local/bin/yorha-tasks"), "menu"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def refresh(self) -> bool:
        self.update_palette()
        for window in self.windows:
            child = window.get_child()
            if child:
                window.remove(child)
            card = self.build_card()
            if hasattr(window, 'yorha_max_height'):
                scroll = Gtk.ScrolledWindow()
                scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                scroll.set_propagate_natural_height(True)
                scroll.set_max_content_height(window.yorha_max_height)
                scroll.add(card)
                window.add(scroll)
            else:
                window.add(card)
            window.show_all()
        return True

    def periodic_refresh(self) -> bool:
        self.fetch_state_async()
        self.fetch_calendar_async()
        return self.refresh()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-preview", metavar="PNG")
    args = parser.parse_args()
    Gtk.init(None)
    agenda = CockpitAgenda(preview=bool(args.render_preview))
    if args.render_preview:
        window = Gtk.OffscreenWindow()
        add_class(window, "yorha-desktop")
        agenda.windows.append(window)
        agenda.refresh()
        def save():
            window.get_pixbuf().savev(args.render_preview, "png", [], [])
            Gtk.main_quit()
            return False
        GLib.timeout_add(4500, save)
    Gtk.main()


if __name__ == "__main__":
    main()
