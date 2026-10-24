#!/usr/bin/env python3
"""YoRHa standby display: native Cairo animation, GTK layer-shell, no network."""
from pathlib import Path
import argparse, os, sys, time, math, random, array, signal, json, subprocess, fcntl, copy, xml.etree.ElementTree as ET
import cairo, gi
import settings
gi.require_version('Gtk','3.0'); gi.require_version('GtkLayerShell','0.1'); gi.require_version('Rsvg','2.0'); gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, PangoCairo, Rsvg
HOME=Path.home(); ASSETS=HOME/'.local/share/yorha'; RUNTIME=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
STREAM=RUNTIME/'sunshine-streaming'; PIDFILE=RUNTIME/'yorha-standby.pid'

def current_mode():
    try:return (ASSETS/'mode').read_text().strip()
    except OSError:return 'night'

def rgba(ctx,color,alpha=1):
    ctx.set_source_rgba(*[int(color[i:i+2],16)/255 for i in [1,3,5]],alpha)

def text(ctx,label,x,y,size,color,alpha=1,spacing=0,align='left',mono=False,baseline=False):
    layout=PangoCairo.create_layout(ctx)
    desc=Pango.FontDescription.from_string(('JetBrains Mono' if mono else 'Noto Sans Light')+' '+str(max(8,size)))
    layout.set_font_description(desc);layout.set_text(label,-1)
    if spacing:
        attrs=Pango.AttrList();attrs.insert(Pango.attr_letter_spacing_new(int(spacing*Pango.SCALE)));layout.set_attributes(attrs)
    width,height=layout.get_pixel_size()
    if align=='center':x-=width/2
    elif align=='right':x-=width
    if baseline:y-=layout.get_baseline()/Pango.SCALE
    ctx.move_to(x,y);rgba(ctx,color,alpha);PangoCairo.show_layout(ctx,layout)
    return width,height

def curve(x,y,w,h):
    nx=(x-w/2)/(w/2);ny=(y-h/2)/(h/2);k=.010 if h>w else .028
    f=1-k*(nx*nx+ny*ny)
    return w/2+(x-w/2)*f,h/2+(y-h/2)*f

class RotatingEmblem:
    """One unlit emblem plane, projected as a supersampled vector outline."""
    def __init__(self):
        import numpy as np
        from fontTools.svgLib.path import parse_path
        from fontTools.pens.basePen import BasePen
        from fontTools.pens.transformPen import TransformPen
        self.np=np;self.surfaces={};self.outlines=[]
        source=ET.parse(ASSETS/'assets/yorha-emblem.svg').getroot()
        x,y,w,h=map(float,source.attrib['viewBox'].split())
        class OutlinePen(BasePen):
            def __init__(pen):super().__init__(None);pen.paths=[];pen.points=[]
            def _moveTo(pen,p):pen.points=[p]
            def _lineTo(pen,p):pen.points.append(p)
            def _curveToOne(pen,p1,p2,p3):
                p0=pen._getCurrentPoint()
                length=sum(math.dist(a,b) for a,b in zip([p0,p1,p2],[p1,p2,p3]))
                steps=max(8,min(160,math.ceil(length/2)))
                for i in range(1,steps+1):
                    t=i/steps;q=1-t
                    pen.points.append(tuple(q**3*p0[j]+3*q*q*t*p1[j]+3*q*t*t*p2[j]+t**3*p3[j] for j in [0,1]))
            def _closePath(pen):pen.paths.append(pen.points);pen.points=[]
            def _endPath(pen):pen._closePath()
        # This normalized source uses only translations; preserve all path transforms.
        def translation(value):
            import re
            if not value:return 0.,0.
            match=re.fullmatch(r'translate\(([-\d.e]+)[ ,]+([-\d.e]+)\)',value)
            if not match:raise ValueError('Unsupported emblem transform: '+value)
            return tuple(map(float,match.groups()))
        def visit(element,dx=0,dy=0):
            tx,ty=translation(element.attrib.get('transform',''));dx+=tx;dy+=ty
            if element.tag.endswith('path'):
                pen=OutlinePen();parse_path(element.attrib['d'],TransformPen(pen,(1,0,0,1,dx,dy)))
                for points in pen.paths:
                    vertices=np.asarray(points,dtype=float)
                    vertices[:,0]=(vertices[:,0]-x-w/2)/(w/2)
                    vertices[:,1]=(vertices[:,1]-y-h/2)/(w/2)
                    self.outlines.append(vertices)
            for child in element:visit(child,dx,dy)
        visit(source)
    def draw(self,ctx,cx,cy,size,t,ink,phase):
        # Render at twice the actual display size, then use a high-quality downsample.
        width=math.ceil(336*size);height=math.ceil(400*size);key=(width,height)
        if key not in self.surfaces:
            self.surfaces[key]=(cairo.ImageSurface(cairo.FORMAT_ARGB32,width*2,height*2),cairo.ImageSurface(cairo.FORMAT_ARGB32,width,height))
        surface,output=self.surfaces[key];c=cairo.Context(surface)
        c.set_operator(cairo.OPERATOR_CLEAR);c.paint();c.set_operator(cairo.OPERATOR_OVER)
        c.set_antialias(cairo.ANTIALIAS_BEST);c.translate(width,height);c.scale(280*size,280*size)
        rgba(c,ink);st,ct=math.sin(.12),math.cos(.12)
        angle=t*math.tau/60+phase
        sn,cs=math.sin(angle),math.cos(angle)
        # At edge-on the plane has zero area; no artificial minimum thickness.
        if abs(cs)>=1e-7:
            for vertices in self.outlines:
                u,v=vertices[:,0],vertices[:,1];denom=4-v*st+u*sn*ct
                xx=4*u*cs/denom;yy=4*(v*ct+u*sn*st)/denom
                c.move_to(float(xx[0]),float(yy[0]))
                for x,y in zip(xx[1:],yy[1:]):c.line_to(float(x),float(y))
                c.close_path()
            # The single plane stays the same unlit color throughout its rotation.
            c.fill()
        # Average 2×2 coverage samples explicitly: no ringing or colored edge halos.
        surface.flush();np=self.np
        source=np.frombuffer(surface.get_data(),dtype=np.uint8).reshape(height*2,width*2,4)
        coverage=((source[:,:,3].astype(np.uint16).reshape(height,2,width,2).sum(axis=(1,3))+2)//4).astype(np.uint16)
        pixels=np.frombuffer(output.get_data(),dtype=np.uint8).reshape(height,width,4)
        for channel,offset in enumerate([5,3,1]):pixels[:,:,channel]=(int(ink[offset:offset+2],16)*coverage+127)//255
        pixels[:,:,3]=coverage;output.mark_dirty()
        ctx.save();ctx.translate(cx-width/2,cy-height/2)
        ctx.set_source_surface(output,0,0);ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint();ctx.restore()

class Scene:
    def __init__(self):
        self.cache={};self.crests={}
        rng=random.Random(11945);self.noise=cairo.ImageSurface(cairo.FORMAT_ARGB32,128,128)
        # Native procedural grain: each opaque texel differs slightly in luminance.
        pixels=array.array('I',(0xff000000 | (n<<16) | (n<<8) | n for n in [rng.randrange(75,180) for _ in range(128*128)]))
        self.noise.get_data()[:]=pixels.tobytes();self.noise.mark_dirty()
        self.emblem=RotatingEmblem()
    def background(self,w,h,mode):
        key=(w,h,mode)
        if key in self.cache:return self.cache[key]
        base=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);ctx=cairo.Context(base)
        night=mode=='night';center='#302c27' if night else '#c8c0a9';edge='#151311' if night else '#938b78';ink='#c8c2a9' if night else '#454438'
        grad=cairo.RadialGradient(w*.5,h*.46,0,w*.5,h*.46,max(w,h)*.68)
        for pos,color in [(0,center),(1,edge)]:grad.add_color_stop_rgb(pos,*[int(color[i:i+2],16)/255 for i in [1,3,5]])
        ctx.set_source(grad);ctx.paint()
        grid=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);g=cairo.Context(grid)
        # Warped vector grid, cached once per output and palette.
        step=8
        def draw_grid(c,color,opacity,dx=0):
            rgba(c,color,opacity);c.set_line_width(.55)
            for x in range(-int(w*.1),int(w*1.1),step):
                for i in range(33):
                    xx,yy=curve(x,-h*.1+h*1.2*i/32,w,h)
                    (c.move_to if i==0 else c.line_to)(xx+dx,yy)
            for y in range(-int(h*.1),int(h*1.1),step):
                for i in range(49):
                    xx,yy=curve(-w*.1+w*1.2*i/48,y,w,h)
                    (c.move_to if i==0 else c.line_to)(xx+dx,yy)
            c.stroke()
        draw_grid(g,ink,.07)
        ctx.set_source_surface(grid,0,0);ctx.paint()
        fringe=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);f=cairo.Context(fringe)
        draw_grid(f,'#bc7066',.14,-2);draw_grid(f,'#699b9e',.14,2)
        # Mask color fringes to the outer part of the screen.
        mask=cairo.LinearGradient(0,0,w,0)
        for pos,a in [(0,1),(.18,.4),(.38,0),(.62,0),(.82,.4),(1,1)]:mask.add_color_stop_rgba(pos,1,1,1,a)
        masked=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);m=cairo.Context(masked);m.set_source_surface(fringe,0,0);m.mask(mask)
        self.cache[key]=(base,masked);return base,masked
    def draw(self,ctx,w,h,t,mode=None,phase=0,hint=False):
        mode=mode or current_mode();night=mode=='night';ink='#c8c2a9' if night else '#454438';muted='#aaa08b' if night else '#514c40'
        base,fringe=self.background(w,h,mode);ctx.set_source_surface(base,0,0);ctx.paint()
        ctx.set_source_surface(fringe,0,0);ctx.paint_with_alpha(.35+.16*math.sin(t/12))
        # Subtle moving grain helps gradients remain smooth on 8-bit displays.
        noise=cairo.SurfacePattern(self.noise);noise.set_extend(cairo.EXTEND_REPEAT)
        matrix=cairo.Matrix();matrix.translate(int(t*3)%128,int(t*2)%128);noise.set_matrix(matrix)
        ctx.set_source(noise);ctx.paint_with_alpha(.016)
        s=min(w,h)/1440
        bob=12*s*math.sin(t*math.tau/40+phase*.6)
        cx=w*.5;cy=h*.44+bob
        pulse=.62+.04*math.sin(t/8)
        # One unlit emblem turns slowly around its vertical axis.
        ctx.save();ctx.push_group()
        self.emblem.draw(ctx,cx,cy-85*s,.80*s,t,ink,phase)
        text(ctx,'YoRHa',cx,cy+58*s,70*s,ink,1,12*s,'center')
        rgba(ctx,ink,.7);ctx.set_line_width(max(.7,s));ctx.move_to(cx-240*s,cy+160*s);ctx.line_to(cx+240*s,cy+160*s);ctx.stroke()
        text(ctx,'FOR THE GLORY OF MANKIND',cx,cy+183*s,13*s,ink,1,3*s,'center')
        ctx.pop_group_to_source();ctx.paint_with_alpha(pulse);ctx.restore()
        # Staff-like framing stays quiet, with the same portrait lens coefficient.
        margin=max(24,min(w,h)*.052)
        rgba(ctx,ink,.19);ctx.set_line_width(.7)
        for yy in [margin,margin+4,h-margin,h-margin-4]:
            for i in range(65):
                xx,y=curve(margin+(w-2*margin)*i/64,yy,w,h)
                (ctx.move_to if i==0 else ctx.line_to)(xx,y)
        ctx.stroke()
        # Align labels to the actual bowed rule endpoints, with shared baselines.
        left,top=curve(margin,margin+4,w,h);right=w-left
        _,bottom=curve(margin,h-margin-4,w,h)
        header_baseline=top+max(24,42*s)
        footer_baseline=bottom-max(18,20*s)
        text(ctx,'■  YoRHa : STANDBY',left,header_baseline,max(11,16*s),muted,.78,1.6*s,baseline=True)
        text(ctx,'BUNKER / REMOTE OPERATIONS',right,header_baseline,max(10,13*s),muted,.65,0,'right',True,baseline=True)
        # Very faint scanline movement, entirely within the background.
        sweep=(t/38%1)*h
        band=cairo.LinearGradient(0,sweep-45,0,sweep+45)
        for pos,a in [(0,0),(.5,.021),(1,0)]:band.add_color_stop_rgba(pos,1,.94,.78,a)
        ctx.set_source(band);ctx.rectangle(0,sweep-45,w,90);ctx.fill()
        rgba(ctx,'#000000',.035);ctx.set_line_width(.6)
        for y in range(0,h,4):ctx.move_to(0,y+.5);ctx.line_to(w,y+.5)
        ctx.stroke()
        # Short transmission bursts, with no audio or flashing transitions.
        messages=['BUNKER CONNECTION ACTIVE','OPERATOR SIGNAL STABLE','MEMORY INTEGRITY VERIFIED','STANDBY PROTOCOL ENGAGED','NO HOSTILE SIGNATURES']
        slot=int(t/24)%len(messages);age=t%24
        visibility=max(0,min(1,age/1.2,(7-age)/1.8))
        if visibility:
            text(ctx,f'POD 042  :  {messages[slot]}',left,footer_baseline-max(22,28*s),max(10,14*s),muted,.72*visibility,0,'left',True,baseline=True)
            text(ctx,f'LOG / {slot+1:03d}       STATUS : NOMINAL',left,footer_baseline,max(9,11*s),muted,.48*visibility,0,'left',True,baseline=True)
        if hint:
            text(ctx,'MOVE MOUSE OR PRESS A KEY TO RESUME',w/2,footer_baseline-max(46,60*s),max(9,12*s),muted,.45,0,'center',True,baseline=True)
        text(ctx,'AUTOMATA : OS / '+mode.upper(),right,footer_baseline,max(9,12*s),muted,.53,0,'right',True,baseline=True)

class Standby:
    def __init__(self,preview=False,idle=False):
        self.scene=Scene();self.windows=[];self.started=time.monotonic();self.preview=preview;self.idle=idle;self.pointer=None;self.last_guard=0
        display=Gdk.Display.get_default()
        if not display:raise RuntimeError('No graphical display')
        monitors=settings.physical_monitors(display)
        if preview:monitors=[display.get_primary_monitor() or display.get_monitor(0)]
        for index,monitor in enumerate(monitors):
            if STREAM.exists():raise RuntimeError("Moonlight active: standby display skipped.")
            window=Gtk.Window(title='YoRHa : Standby Preview' if preview else 'YoRHa : Standby')
            window.set_wmclass('yorha-standby','yorha-standby')
            if preview:window.set_default_size(1100,650)
            else:
                GtkLayerShell.init_for_window(window);GtkLayerShell.set_namespace(window,'yorha-standby')
                GtkLayerShell.set_layer(window,GtkLayerShell.Layer.OVERLAY);GtkLayerShell.set_monitor(window,monitor)
                GtkLayerShell.set_keyboard_mode(window,GtkLayerShell.KeyboardMode.EXCLUSIVE)
                for edge in [GtkLayerShell.Edge.LEFT,GtkLayerShell.Edge.RIGHT,GtkLayerShell.Edge.TOP,GtkLayerShell.Edge.BOTTOM]:GtkLayerShell.set_anchor(window,edge,True)
                GtkLayerShell.set_exclusive_zone(window,0)
            area=Gtk.DrawingArea();area.add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.SCROLL_MASK)
            area.connect('draw',self.draw,index);window.add(area)
            for event in ['key-press-event','button-press-event','scroll-event']:window.connect(event,self.dismiss)
            area.connect('motion-notify-event',self.motion)
            window.connect('delete-event',self.dismiss)
            window.show_all();blank=Gdk.Cursor.new_for_display(display,Gdk.CursorType.BLANK_CURSOR);window.get_window().set_cursor(blank)
            self.windows.append((window,area))
        if not self.windows:raise RuntimeError('No physical monitors available')
        GLib.timeout_add(42,self.tick)
    def draw(self,area,ctx,index):
        self.scene.draw(ctx,area.get_allocated_width(),area.get_allocated_height(),time.monotonic()-self.started,phase=index*2.2,hint=True)
        return False
    def tick(self):
        if STREAM.exists():
            self.dismiss();return False
        now=time.monotonic()
        if now-self.last_guard>.5:
            self.last_guard=now
            if subprocess.run(['pgrep','-x','hyprlock'],stdout=subprocess.DEVNULL).returncode==0:
                self.dismiss();return False
        for _,area in self.windows:area.queue_draw()
        return True
    def motion(self,area,event):
        if time.monotonic()-self.started<1:return False
        point=(event.x_root,event.y_root)
        if self.pointer and math.hypot(point[0]-self.pointer[0],point[1]-self.pointer[1])>3:self.dismiss()
        self.pointer=point;return True
    def dismiss(self,*args):
        for window,_ in self.windows:window.destroy()
        Gtk.main_quit();return True

def export(scene,path,seconds,mode):
    w,h,fps=1280,720,24
    command=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','bgra','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as proc:
        surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);ctx=cairo.Context(surface)
        for frame in range(int(seconds*fps)):
            scene.draw(ctx,w,h,frame/fps,mode,hint=False);surface.flush();proc.stdin.write(surface.get_data())
        proc.stdin.close();proc.wait()
        if proc.returncode:raise RuntimeError('Video export failed')
    print(path)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',default='preview',choices=['preview','start','stop','status','export'])
    parser.add_argument('--idle',action='store_true');parser.add_argument('--seconds',type=float,default=16)
    parser.add_argument('--mode',choices=['day','night']);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.action=='export':
        export(Scene(),args.output or ASSETS/'previews/standby.mp4',args.seconds,args.mode or current_mode());return
    if args.action in ['stop','status']:
        try:
            pid=int(PIDFILE.read_text());os.kill(pid,0)
            if str(Path(__file__).resolve()).encode() not in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0'):raise ValueError('Stale PID')
        except (OSError,ValueError):
            if args.action=='status':print('stopped')
            return
        if args.action=='stop':os.kill(pid,signal.SIGTERM)
        else:print('running')
        return
    # The streaming guard is unconditional, including manual preview.
    if STREAM.exists():print('Moonlight active: standby display skipped.');return
    if args.idle and subprocess.run(['pgrep','-x','Plexamp'],stdout=subprocess.DEVNULL).returncode==0:return
    if subprocess.run(['pgrep','-x','hyprlock'],stdout=subprocess.DEVNULL).returncode==0:return
    lock=(RUNTIME/'yorha-standby.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    PIDFILE.write_text(str(os.getpid()))
    try:
        app=Standby(preview=args.action=='preview',idle=args.idle)
        def stop(*unused):GLib.idle_add(app.dismiss)
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        Gtk.main()
    finally:PIDFILE.unlink(missing_ok=True)

if __name__=='__main__':main()
