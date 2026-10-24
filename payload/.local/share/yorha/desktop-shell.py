#!/usr/bin/env python3
"""Interactive YoRHa desktop panels, underneath application windows."""
from pathlib import Path
import argparse
import json
import os
import socket
import subprocess
import threading
import time
import gi
import psutil
import settings
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell, Pango
from desktop_ui import ROOT, PALETTES, klass, text, panel, mode, load_style
from soundwave_hud import draw_hud, read_levels

class SoundwaveArea(Gtk.DrawingArea):
    """Native vector HUD, consuming the same output spectrum as Waybar."""
    def __init__(self):
        super().__init__()
        self.levels = read_levels()
        self.selected_mode = mode()
        self.set_size_request(-1, 64)
        self.set_tooltip_text('HUD: Sound Waves · live system playback')
        self.connect('draw', self.draw)
        self.timer = GLib.timeout_add(50, self.refresh)
        self.connect('destroy', self.cleanup)

    def refresh(self):
        selected_mode, levels = mode(), read_levels()
        if selected_mode != self.selected_mode or levels != self.levels:
            self.selected_mode, self.levels = selected_mode, levels
            self.queue_draw()
        return True

    def draw(self, _widget, ctx):
        area = self.get_allocation()
        draw_hud(ctx, area.width, area.height, self.levels, PALETTES[self.selected_mode]['ink'])
        return False

    def cleanup(self, *_args):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None

def run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): return ''

def launch(args):
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class DesktopShell:
    def __init__(self, preview=False):
        self.preview = preview
        self.provider = Gtk.CssProvider()
        self.palette = mode()
        load_style(self.provider, self.palette)
        self.windows = []
        self.fields = {}
        self.meters = {}
        self.busy = False
        self.snapshot = {}
        self.player = ''
        self.display = Gdk.Display.get_default()
        psutil.cpu_percent()
        if not preview:
            self.rebuild()
            self.display.connect('monitor-added', self.monitor_change)
            self.display.connect('monitor-removed', self.monitor_change)
        GLib.timeout_add_seconds(1, self.tick)
        self.collect_async()

    def monitor_change(self, *_args):
        GLib.timeout_add(300, self.rebuild)

    @staticmethod
    def layout(w, h):
        if h>w:
            return {'access':(64,280,248),'status':(64,670,376),
                    'clock':(64,1110,376),'media':(64,1510,480),'footer':(72,h-77,600)}
        top = 252 if h>=1300 else 230
        return {'access':(72,top,248),'status':(356,top,376),
                'clock':(w-448,top,376),'media':(72,h-462,480),'footer':(72,h-77,800)}

    def rebuild(self):
        for window in self.windows: window.destroy()
        self.windows.clear();self.fields.clear();self.meters.clear()
        physical = settings.physical_monitors(self.display)
        landscape = [m for m in physical if m.get_geometry().width>=m.get_geometry().height]
        candidates = landscape or physical
        if not candidates: return False
        primary = self.display.get_primary_monitor()
        monitor = primary if primary in candidates else candidates[0]
        geom = monitor.get_geometry()
        agenda_here = (Path.home()/'.config/yorha/yorha-cockpit-widget-enabled').exists() and not any(
            m.get_geometry().height > m.get_geometry().width for m in physical)
        for name,(x,y,width) in self.layout(geom.width,geom.height).items():
            if agenda_here and name == 'clock':
                if geom.width < 1800: continue
                x = 768
            if agenda_here and name == 'status' and geom.width < 1440: continue
            if name == 'status' and geom.width < 1440: continue
            if name == 'media' and geom.height < 950: y = geom.height - 380
            window = Gtk.Window()
            klass(window,'yorha-desktop')
            window.set_title('YoRHa / '+name.title())
            window.set_decorated(False);window.set_resizable(False)
            window.set_app_paintable(True)
            visual=window.get_screen().get_rgba_visual()
            if visual: window.set_visual(visual)
            GtkLayerShell.init_for_window(window)
            GtkLayerShell.set_namespace(window,'yorha-desktop-'+name)
            GtkLayerShell.set_monitor(window,monitor)
            GtkLayerShell.set_layer(window,GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_keyboard_mode(window,GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_anchor(window,GtkLayerShell.Edge.TOP,True)
            GtkLayerShell.set_anchor(window,GtkLayerShell.Edge.LEFT,True)
            GtkLayerShell.set_margin(window,GtkLayerShell.Edge.TOP,y-8)
            GtkLayerShell.set_margin(window,GtkLayerShell.Edge.LEFT,x-8)
            GtkLayerShell.set_exclusive_zone(window,-1)
            window.add(self.build(name,width));window.show_all()
            self.windows.append(window)
        self.apply_snapshot(self.snapshot)
        return False

    def build(self,name,width):
        root = klass(Gtk.Box(orientation=Gtk.Orientation.VERTICAL),'desktop-root')
        root.set_size_request(width+16,-1)
        if name=='footer':
            self.fields['uptime']=text('UPTIME  /  …','footer')
            root.pack_start(self.fields['uptime'],False,False,0)
            return root
        titles={'access':('Access','01'),'status':('Status','02'),
                'clock':('Local time','03'),'media':('Operator transmissions','04')}
        card,body=panel(*titles[name],width)
        root.pack_start(card,False,False,0)
        if name=='access': self.access(body)
        elif name=='status': self.status(body)
        elif name=='clock': self.clock(body)
        elif name=='media': self.media(body)
        return root

    def access(self,body):
        body.set_spacing(4)
        targets=[('Home',['xdg-open',str(Path.home())]),
                 ('Documents',['xdg-open',str(Path.home()/'Documents')]),
                 ('Downloads',['xdg-open',str(Path.home()/'Downloads')]),
                 ('Terminal',['kitty']),
                 ('Applications',['rofi','-show','drun'])]
        for index,(title,cmd) in enumerate(targets):
            button=klass(Gtk.Button(),'access-row')
            row=Gtk.Box(spacing=12)
            row.pack_start(text('■','micro'),False,False,0)
            row.pack_start(text(title),True,True,0)
            row.pack_end(text(f'{index+1:02}','micro'),False,False,0)
            button.add(row)
            button.connect('clicked',lambda _b,c=cmd:launch(c))
            body.pack_start(button,False,False,0)
        body.pack_start(text('SELECT  /  OPEN','micro'),False,False,8)

    def status(self,body):
        row=Gtk.Box()
        row.pack_start(text('YoRHa UNIT' if self.preview else socket.gethostname()),True,True,0)
        row.pack_end(text('LOCAL UNIT','micro'),False,False,0)
        body.pack_start(row,False,False,0)
        body.pack_start(Gtk.Separator(),False,False,0)
        for key,title in [('cpu','CPU'),('ram','MEMORY'),('gpu','GPU'),('disk','STORAGE')]:
            row=Gtk.Box()
            row.pack_start(text(title,'metric-label'),True,True,0)
            value=text('…','metric-value');self.fields[key]=value
            row.pack_end(value,False,False,0)
            body.pack_start(row,False,False,0)
            meter=Gtk.ProgressBar();self.meters[key]=meter
            body.pack_start(meter,False,False,0)
        body.pack_start(Gtk.Separator(),False,False,0)
        self.fields['network']=text('NETWORK  /  …','micro')
        body.pack_start(self.fields['network'],False,False,0)

    def clock(self,body):
        for key,cls in [('weekday','clock-weekday'),('time','clock-time')]:
            self.fields[key]=text('','%s'%cls,.5)
            body.pack_start(self.fields[key],False,False,0)
        body.pack_start(Gtk.Separator(),False,False,0)
        self.fields['date']=text('','clock-date',.5)
        body.pack_start(self.fields['date'],False,False,0)
        button=Gtk.Button();button.add(text('VIEW CALENDAR  ↗','micro',.5))
        button.connect('clicked',lambda _b:launch(['xdg-open','https://calendar.google.com/calendar/r']))
        body.pack_start(button,False,False,0)

    def media(self,body):
        row=Gtk.Box(spacing=22)
        self.emblem=Gtk.Image();self.tint_emblem()
        emblem=self.emblem;emblem.set_opacity(.8)
        row.pack_start(emblem,False,False,0)
        col=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=9)
        self.fields['track']=text('Awaiting transmission')
        self.fields['track'].set_max_width_chars(29)
        self.fields['track'].set_ellipsize(Pango.EllipsizeMode.END)
        self.fields['artist']=text('Start playback to connect an audio channel.','muted')
        self.fields['artist'].set_max_width_chars(32)
        self.fields['artist'].set_ellipsize(Pango.EllipsizeMode.END)
        col.pack_start(self.fields['track'],False,False,0)
        col.pack_start(self.fields['artist'],False,False,0)
        self.fields['playback']=text('STANDBY','micro')
        col.pack_start(self.fields['playback'],False,False,0)
        row.pack_start(col,True,True,0);body.pack_start(row,False,False,0)
        sound=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        sound.pack_start(text('■  HUD: SOUND WAVES','micro'),False,False,0)
        sound.pack_start(SoundwaveArea(),False,False,0)
        body.pack_start(sound,False,False,0)
        body.pack_start(Gtk.Separator(),False,False,0)
        controls=Gtk.Box(spacing=8)
        controls.pack_start(text('AUDIO CHANNEL','micro'),True,True,0)
        for caption,action,hint in [('‹‹','previous','Previous track'),('Ⅱ / ▷','play-pause','Play / pause'),('››','next','Next track')]:
            button=klass(Gtk.Button(label=caption),'media-control');button.set_tooltip_text(hint)
            button.connect('clicked',lambda _b,a=action:self.media_action(a))
            controls.pack_start(button,False,False,0)
        body.pack_start(controls,False,False,0)

    def media_action(self,action):
        launch(['playerctl']+(['-p',self.player] if self.player else [])+[action])

    def tint_emblem(self):
        import xml.etree.ElementTree as ET
        svg=ET.fromstring((ROOT/'assets/yorha-emblem.svg').read_bytes())
        for path in svg.iter('{http://www.w3.org/2000/svg}path'):
            path.set('fill',PALETTES[self.palette]['ink'])
        loader=GdkPixbuf.PixbufLoader.new_with_type('svg')
        loader.set_size(65,100);loader.write(ET.tostring(svg));loader.close()
        self.emblem.set_from_pixbuf(loader.get_pixbuf())

    def tick(self):
        selected=mode()
        if selected!=self.palette:
            self.palette=selected;load_style(self.provider,selected)
            if hasattr(self,'emblem'):self.tint_emblem()
        now=time.localtime()
        for key,value in [('weekday',time.strftime('%A',now).upper()),('time',time.strftime('%H:%M',now)),
                          ('date',time.strftime('%d %B %Y',now).upper())]:
            if key in self.fields:self.fields[key].set_text(value)
        seconds=int(time.time()-psutil.boot_time())
        if 'uptime' in self.fields:
            self.fields['uptime'].set_text(f'UPTIME  /  {seconds//3600:02d} H  {(seconds//60)%60:02d} M    ·    YoRHa OS')
        if int(time.monotonic())%5==0:self.collect_async()
        return True

    def collect_async(self):
        if self.preview:
            self.apply_snapshot(dict(cpu=12, ram=38, gpu=4, disk=25, ram_text='6.1 / 16.0 GiB',
                network='NETWORK  /  CONNECTED', track='Peaceful Sleep', artist='NieR:Automata · demo metadata',
                playback='PLAYING', player=''))
            return
        if self.busy:return
        self.busy=True
        def worker():
            data={}
            try:
                ram=psutil.virtual_memory();disk=psutil.disk_usage(str(Path.home()))
                data.update(cpu=psutil.cpu_percent(interval=.15),ram=ram.percent,disk=disk.percent)
                data['ram_text']=f'{ram.used/2**30:.1f} / {ram.total/2**30:.1f} GiB'
                data['disk_text']=f'{disk.used/2**30:.0f} / {disk.total/2**30:.0f} GiB'
                gpu=run([str(Path.home()/'.local/bin/yorha-gpu')])
                try:data['gpu']=float(gpu)
                except ValueError:data['gpu']=0;data['gpu_text']='N/A'
                addresses=psutil.net_if_addrs();stats=psutil.net_if_stats()
                ip=next((a.address for nic,entries in addresses.items() if nic.startswith(('en','eth','wl'))
                         and stats[nic].isup for a in entries if a.family==socket.AF_INET),'OFFLINE')
                data['network']='NETWORK  /  '+ip
                players=run(['playerctl','-l']).splitlines()
                if players:
                    player=next((p for p in players if run(['playerctl','-p',p,'status'])=='Playing'),players[0])
                    data['player']=player
                    meta=run(['playerctl','-p',player,'metadata','--format','{{title}}\n{{artist}}']).splitlines()
                    data['track']=meta[0] if meta else 'Audio transmission'
                    data['artist']=meta[1] if len(meta)>1 else player
                    data['playback']=run(['playerctl','-p',player,'status']).upper()
                else:
                    data['player']=''
                    data.update(track='Awaiting transmission',artist='Start playback to connect an audio channel.',playback='STANDBY')
            except Exception as exc:
                print('Telemetry refresh:',type(exc).__name__,flush=True)
            GLib.idle_add(self.apply_snapshot,data)
        threading.Thread(target=worker,daemon=True).start()

    def apply_snapshot(self,data):
        self.busy=False;self.snapshot=data
        self.player=data.get('player','')
        for key in ['cpu','ram','gpu','disk']:
            if key in data and key in self.meters:
                self.meters[key].set_fraction(max(0,min(1,data[key]/100)))
                self.fields[key].set_text(data.get(key+'_text',f'{data[key]:.0f}%'))
        for key in ['network','track','artist','playback']:
            if key in data and key in self.fields:self.fields[key].set_text(data[key])
        return False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    previews=parser.add_mutually_exclusive_group()
    previews.add_argument('--render-preview',metavar='PNG')
    previews.add_argument('--render-media-preview',metavar='PNG')
    args=parser.parse_args()
    Gtk.init(None)
    preview_path=args.render_preview or args.render_media_preview
    shell=DesktopShell(preview=bool(preview_path))
    if preview_path:
        if args.render_media_preview:
            canvas=shell.build('media',480)
        else:
            canvas=Gtk.Fixed();canvas.set_size_request(2560,1440)
            background=ROOT/'wallpapers/interface'/('night' if mode()=='night' else '')/'yorha-2560x1440.png'
            canvas.put(Gtk.Image.new_from_file(str(background)),0,0)
            for name,(x,y,width) in shell.layout(2560,1440).items():canvas.put(shell.build(name,width),x-8,y-8)
        window=Gtk.OffscreenWindow();klass(window,'yorha-desktop')
        window.add(canvas);window.show_all();shell.collect_async();shell.tick()
        def save():
            window.get_pixbuf().savev(preview_path,'png',[],[]);Gtk.main_quit();return False
        GLib.timeout_add(1500,save)
    Gtk.main()

if __name__=='__main__':main()
