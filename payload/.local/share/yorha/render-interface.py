#!/usr/bin/env python3
"""Procedural menu-study wallpaper: mesh, traces and score-like borders."""
from pathlib import Path
import math
import cairo
import numpy as np
import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

ROOT = Path(__file__).resolve().parent

def rgb(value):
    return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))

def draw(cr, w, h, night, labels=True, frame=True):
    ink = rgb('#c8c2a9' if night else '#454438')
    center = np.array([44,40,36] if night else [223,219,196], dtype=float)
    edge = np.array([28,26,24] if night else [194,189,166], dtype=float)
    yy,xx = np.mgrid[0:h,0:w]
    radius = np.clip((((xx/w-.48)*1.25)**2+((yy/h-.43)*.9)**2)**.5,0,1)
    base = center[None,None,:]*(1-radius[:,:,None])+edge[None,None,:]*radius[:,:,None]
    grain = np.random.default_rng(29).normal(0,.65,(h,w,1))
    pixels = np.zeros((h,w,4),dtype=np.uint8)
    pixels[:,:,:3] = np.clip(base[:,:,::-1]+grain,0,255).astype(np.uint8)
    pixels[:,:,3]=255
    surface=cairo.ImageSurface.create_for_data(pixels,cairo.FORMAT_ARGB32,w,h)
    cr.set_source_surface(surface);cr.paint()
    def color(a=1): cr.set_source_rgba(*ink,a)
    def lens(x,y):
        nx=(x-w/2)/(w/2);ny=(y-h/2)/(h/2)
        k=.006 if h>w else .014
        f=1-k*(nx*nx+ny*ny)
        return w/2+(x-w/2)*f,h/2+(y-h/2)*f
    def line(points,a=.16,width=1,fringe=False):
        color(a);cr.set_line_width(width)
        for i,p in enumerate(points):
            (cr.move_to if i==0 else cr.line_to)(*lens(*p))
        cr.stroke()
        if fringe:
            for dx,tint in [(-1.15,(.70,.30,.28)),(1.15,(.26,.58,.60))]:
                gradient=cairo.LinearGradient(0,0,w,0)
                for stop,alpha in [(0,a*.34),(.20,0),(.80,0),(1,a*.34)]:
                    gradient.add_color_stop_rgba(stop,*tint,alpha)
                cr.set_source(gradient)
                for i,p in enumerate(points):
                    px,py=lens(*p)
                    (cr.move_to if i==0 else cr.line_to)(px+dx,py)
                cr.stroke()
    # A very fine woven mesh, with gentle edge distortion.
    for x in range(-40,w+40,8): line([(x,-30+h*i/20) for i in range(22)],.055,.55,True)
    for y in range(-40,h+40,8): line([(-30+w*i/28,y) for i in range(30)],.055,.55,True)
    for off in [-h*.55,-h*.49,-h*.12,h*.16,h*.74]:
        line([(0,off),(w,off+w)],.13,.9)
    for cx,cy,radii in [(-65,90,[410,422,440]),(w+90,h+110,[475,488,540,552])]:
        for r in radii:
            line([(cx+r*math.cos(t),cy+r*math.sin(t)) for t in np.linspace(0,math.tau,240)],.15)
    # Discrete instrument-ring ticks, echoing the concept's lower-right arc.
    for i in range(92):
        t=math.pi+i*math.pi/100
        line([(w+90+rr*math.cos(t),h+110+rr*math.sin(t)) for rr in (446,469)],.25,6)
    # In-game square + three-dot repeating ornament.
    for border in ([105,h-104] if frame else []):
        line([(x,border) for x in np.linspace(38,w-38,96)],.80,1.2)
        for x in range(48,w-38,64):
            px,py=lens(x,border)
            color(.76);cr.rectangle(px,py,9,4);cr.fill()
            for dx,dy in [(27,8),(38,8),(32.5,18)]:
                px,py=lens(x+dx,border+dy)
                cr.arc(px,py,1.9,0,math.tau);cr.fill()
    if not labels:return
    portrait=h>w
    title='OPERATIONS' if portrait else 'SYSTEM'
    x,y=72,196
    cr.select_font_face('Noto Sans',cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(48)
    color(.13);cr.move_to(x+5,y+5);cr.show_text(title)
    color(.9);cr.move_to(x,y);cr.show_text(title)
    advance=cr.text_extents(title).x_advance
    cr.set_font_size(17);color(.85)
    cr.move_to(x+advance+16,y-3);cr.show_text('/  Calendar & quests' if portrait else '/  Personal terminal')
    cr.set_font_size(12)
    cr.move_to(w-280,169);cr.show_text('YoRHa  /  AUTOMATA OS')
    cr.move_to(w-280,192);cr.show_text('LOCAL ACCESS  ·  AUTHORIZED')
    cr.set_font_size(11);color(.86)
    cr.move_to(w-295,h-52);cr.show_text('FOR THE GLORY OF MANKIND.')
    emblem=ROOT/'assets/yorha-emblem.svg'
    if emblem.exists():
        cr.save();cr.translate(w-85,h-89)
        handle=Rsvg.Handle.new_from_file(str(emblem))
        viewport=Rsvg.Rectangle();viewport.x=0;viewport.y=0;viewport.width=26;viewport.height=47
        cr.push_group();handle.render_document(cr,viewport);pattern=cr.pop_group()
        color(.70);cr.mask(pattern);cr.restore()

def main():
    for mode in ['day','night']:
        folder=ROOT/'wallpapers/interface'/('night' if mode=='night' else '')
        folder.mkdir(parents=True,exist_ok=True)
        for w,h in [(2560,1440),(1440,2560),(2732,2048)]:
            stem=folder/f'yorha-{w}x{h}'
            png=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h)
            draw(cairo.Context(png),w,h,mode=='night');png.write_to_png(str(stem)+'.png')
            svg=cairo.SVGSurface(str(stem)+'.svg',w,h)
            draw(cairo.Context(svg),w,h,mode=='night');svg.finish()
            print(mode,w,h,flush=True)

if __name__=='__main__': main()
