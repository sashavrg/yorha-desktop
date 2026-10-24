# Widgets and connections

The GTK 3 panels use `gtk-layer-shell`'s bottom layer with no exclusive zone or keyboard grab. Normal application windows cover them. `yorha-desktop show|hide|toggle|status` controls the two panel services. Audio analysis remains available to Waybar when panels are hidden.

## Local quests

Local mode is the default. No network request is made to a planner.

```sh
yorha-tasks add "Check the next objective"
yorha-tasks add "Prepare the briefing" --day 2026-11-01
yorha-tasks list
yorha-tasks done TASK_ID
yorha-tasks remove TASK_ID
yorha-tasks menu
```

The edit button opens the Rofi quest menu. Click a checkbox directly in the desktop card to complete/reopen an objective. Changes are stored atomically in `~/.local/share/yorha/tasks.json` with owner-only permissions and revision checks. The widget refreshes external edits every minute. `done` toggles the selected task's completion state.

## Read-only Google Calendar

In Google Calendar's web settings, select a calendar, then **Integrate calendar → Secret address in iCal format**. Configure it locally:

```sh
yorha-calendar-feed set
yorha-calendar-feed status
systemctl --user restart yorha-cockpit-widget.service
```

The input prompt is hidden. The URL is stored only in `~/.config/yorha/calendar-feed-url` with mode 0600; treat it as a password. Do not paste it into an issue or commit it. `yorha-calendar-feed remove` removes the local connection. The feed supports recurring events and updates every five minutes. It is a read-only subscription, not Google OAuth or a two-way calendar editor. Google controls publication/refresh timing.

Without a feed, the calendar remains interactive and displays a setup hint. Timezone follows the system IANA zone; set `timezone` to an IANA name in `~/.config/yorha/settings.json` if desired.

## Optional compatible planner

Set `planner_url` in `~/.config/yorha/settings.json` only if you operate a compatible service. The default is empty and uses local quests. The widget expects:

- `GET /api/state` → `{"rev": 1, "items": [{"id":"task-id","title":"Objective","day":"2026-11-01","done":false}]}`
- `PUT /api/state` with the next full state and `If-Match: <revision>` → saved state with incremented revision.
- A `409` conflict response containing the latest state; the widget retries up to three times.

This repository does not deploy that planner server or authenticate to an author's server. Configure TLS/network access yourself. Local quests remain a separate store when switching to a remote planner. `yorha-tasks` always edits the local store.

An optional `cockpit_file` points to a local generated `TODAY.md` snapshot for informational focus objectives. These extra focus rows are not checkboxes. They appear only when the snapshot date matches today. No sample personal snapshot is shipped.

## Displays and audio

Main panels select a physical landscape output; Calendar/Quests prefer a portrait output and otherwise use the primary physical one. Windows retarget after display hotplug. Small single-screen layouts omit crowded status/clock cards; the agenda scrolls within available height. Monitors without EDID metadata are excluded by default to skip virtual streaming screens. Set `include_edidless: true` to include such hardware. `exclude_outputs` matches GTK monitor model prefixes. Waybar/wallpaper have conventional `HEADLESS-`, `Virtual-` and `Sunshine` exclusions as well; edit your two Waybar profile configs if your virtual output has a different name.

The Sound Waves daemon reads the default PulseAudio/PipeWire playback monitor with Cava, writes atomic PNG/JSON frames under `$XDG_RUNTIME_DIR/yorha-soundwave` and updates all views. Silence/stale data stays at the idle floor. A changed default output reconnects the analyser. No microphone or generated fake spectrum is used.

```sh
systemctl --user restart yorha-soundwave.service
journalctl --user -u yorha-desktop -u yorha-cockpit-widget -u yorha-soundwave
```

Journal messages and player metadata can contain personal information; review before sharing diagnostics.
