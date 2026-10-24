"""Shared menu typography and floating panels for the YoRHa desktop."""
from pathlib import Path
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

ROOT = Path.home() / '.local/share/yorha'
PALETTES = {
    'day': dict(ink='#454438', muted='#605d4e', surface='#dedac4', line='#a8a28d',
                band='#454438', band_ink='#eeead5', soft='#c9c4ad', shadow='rgba(69,68,56,0.40)'),
    'night': dict(ink='#c8c2a9', muted='#aaa18f', surface='#2c2925', line='#625b50',
                  band='#c8c2a9', band_ink='#292622', soft='#3c3730', shadow='rgba(0,0,0,0.45)'),
}

def mode():
    value = os.environ.get('YORHA_PREVIEW_MODE', '')
    if value not in PALETTES:
        try: value = (ROOT / 'mode').read_text().strip()
        except OSError: value = 'night'
    return value if value in PALETTES else 'night'

def klass(widget, names):
    for name in names.split(): widget.get_style_context().add_class(name)
    return widget

def text(value, names='', align=0):
    item = Gtk.Label(label=value)
    item.set_xalign(align)
    item.set_line_wrap(True)
    item.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if names: klass(item, names)
    return item

def panel(title, number, width):
    outer = klass(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), 'floating-panel')
    outer.set_size_request(width, -1)
    heading = klass(Gtk.Box(spacing=12), 'panel-heading')
    heading.pack_start(text('■', 'heading-square'), False, False, 0)
    heading.pack_start(text(title, 'panel-title'), True, True, 0)
    heading.pack_end(text(number, 'panel-number'), False, False, 0)
    outer.pack_start(heading, False, False, 0)
    body = klass(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12), 'panel-body')
    outer.pack_start(body, True, True, 0)
    return outer, body

def stylesheet(selected_mode):
    p = PALETTES[selected_mode]
    return f'''
    window.yorha-desktop {{ background: transparent; }}
    .desktop-root {{ padding: 8px; }}
    label {{ font-family: "Noto Sans", sans-serif; font-size: 14px; color: {p['ink']}; }}
    .floating-panel {{ background: {p['surface']}; border: 1px solid {p['line']};
        box-shadow: 5px 5px 0 {p['shadow']}; }}
    .panel-heading {{ background: {p['band']}; padding: 7px 14px; }}
    .panel-heading label {{ color: {p['band_ink']}; }}
    .panel-title {{ font-size: 17px; letter-spacing: 1px; }}
    .heading-square {{ font-size: 10px; }}
    .panel-number {{ font-family: "JetBrains Mono", monospace; font-size: 11px; }}
    .panel-body {{ padding: 18px 20px; }}
    label.muted, label.section, label.date, label.weekday, label.task-tag,
    label.interaction-hint, label.metric-label, label.micro {{ color: {p['muted']}; }}
    label.section, label.kicker, label.date, label.weekday, label.task-tag,
    label.interaction-hint, label.metric-label, label.micro, label.count,
    label.event-time {{ font-family: "JetBrains Mono", monospace; }}
    label.section, label.kicker {{ font-size: 11px; letter-spacing: 1.7px; }}
    label.micro, label.date, label.interaction-hint {{ font-size: 11px; letter-spacing: 0.6px; }}
    label.weekday {{ font-size: 11px; }}
    label.month {{ font-size: 16px; letter-spacing: 1px; }}
    label.count {{ font-size: 12px; }}
    label.task-tag {{ font-size: 10px; letter-spacing: 1px; }}
    label.objective-primary {{ font-size: 15px; background: {p['soft']};
        border-left: 3px solid {p['band']}; padding: 10px 12px; }}
    label.objective-secondary {{ font-size: 14px; padding: 4px 0; }}
    label.task-title, label.event-title {{ font-size: 14px; }}
    label.task-complete {{ font-size: 14px; color: {p['muted']}; }}
    label.event-time {{ font-size: 12px; min-width: 88px; }}
    separator {{ min-height: 1px; background: {p['line']}; margin: 4px 0; }}
    button {{ background-image: none; background: transparent; border: 1px solid transparent;
        box-shadow: none; border-radius: 0; color: {p['ink']}; padding: 5px; }}
    button:hover {{ background: {p['soft']}; border-color: {p['line']}; }}
    button label {{ color: {p['ink']}; }}
    button.day {{ min-width: 40px; min-height: 31px; padding: 0; }}
    button.day label {{ font-family: "JetBrains Mono", monospace; font-size: 14px; }}
    button.day.today {{ border-bottom: 2px solid {p['band']}; }}
    button.day.selected {{ background: {p['band']}; border-color: {p['band']}; }}
    button.day.selected label {{ color: {p['band_ink']}; }}
    button.month-nav {{ min-width: 25px; min-height: 25px; border-color: {p['line']}; padding: 0; }}
    checkbutton.task-check check {{ min-width: 14px; min-height: 14px;
        background: {p['surface']}; border: 1px solid {p['muted']}; color: {p['band_ink']}; }}
    checkbutton.task-check:checked check {{ background: {p['band']}; color: {p['band_ink']}; }}
    button#planner-button {{ background: {p['band']}; min-height: 30px; padding: 4px 12px; }}
    button#planner-button label {{ color: {p['band_ink']}; font-size: 12px; letter-spacing: 1.2px; }}
    button#planner-button:hover {{ opacity: 0.88; }}
    button.access-row {{ padding: 9px 10px; border-bottom: 1px solid {p['line']}; }}
    button.access-row label {{ font-size: 15px; letter-spacing: 0.5px; }}
    button.access-row:hover {{ background: {p['band']}; }}
    button.access-row:hover label {{ color: {p['band_ink']}; }}
    label.clock-time {{ font-size: 72px; font-weight: 300; letter-spacing: -3px; }}
    label.clock-weekday {{ font-size: 17px; letter-spacing: 3px; }}
    label.clock-date {{ font-size: 19px; letter-spacing: 1.5px; }}
    label.metric-value {{ font-family: "JetBrains Mono", monospace; font-size: 14px; }}
    label.metric-label {{ font-size: 11px; letter-spacing: 1px; }}
    progressbar trough {{ background: {p['soft']}; border: none; border-radius: 0; min-height: 4px; }}
    progressbar progress {{ background: {p['band']}; border: none; border-radius: 0; min-height: 4px; }}
    label.footer {{ font-family: "JetBrains Mono", monospace; font-size: 12px;
        letter-spacing: 3px; color: {p['muted']}; }}
    button.media-control {{ border-color: {p['line']}; min-width: 43px; min-height: 27px; }}
    button.media-control label {{ font-size: 15px; }}
    tooltip {{ background: {p['surface']}; color: {p['ink']}; border: 1px solid {p['line']}; }}
    tooltip label {{ color: {p['ink']}; padding: 6px; }}
    '''

def load_style(provider, selected_mode):
    provider.load_from_data(stylesheet(selected_mode).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                          Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
