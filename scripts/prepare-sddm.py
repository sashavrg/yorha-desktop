#!/usr/bin/env python3
"""Generate greeter assets from the selected local crest and wallpapers."""
import sys
from pathlib import Path
import shutil
import cairo
import gi
gi.require_version('Rsvg','2.0')
from gi.repository import Rsvg
root=Path(sys.argv[1]);theme=root/'sddm/YoRHa'
for mode,color in [('day','#454438'),('night','#c8c2a9')]:
    background=theme/'backgrounds'/mode;background.mkdir(parents=True,exist_ok=True)
    source=root/'wallpapers/interface'/('night' if mode=='night' else '')
    for size in ['2560x1440','1440x2560']:
        shutil.copy2(source/f'yorha-{size}.png',background/f'yorha-{size}.png')
    surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,197,232);cr=cairo.Context(surface)
    handle=Rsvg.Handle.new_from_file(str(root/'assets/yorha-emblem.svg'))
    viewport=Rsvg.Rectangle();viewport.width=197;viewport.height=232
    cr.push_group();handle.render_document(cr,viewport);pattern=cr.pop_group()
    cr.set_source_rgb(*(int(color[i:i+2],16)/255 for i in [1,3,5]));cr.mask(pattern)
    surface.write_to_png(str(theme/'assets'/f'emblem-{mode}.png'))
