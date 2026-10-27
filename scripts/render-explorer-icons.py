#!/usr/bin/env python3
"""Generate original geometric archive icons; Breeze supplies unlisted icons."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]/'payload/.local/share/icons'

FOLDER = '<path d="M3 8h10l3 3h13v17H3Z" fill="{ink}" fill-opacity=".12"/><path d="M3 8h10l3 3h13v17H3ZM3 13h26"/>'
PAGE = '<path d="M6 3h15l5 5v21H6Z" fill="{ink}" fill-opacity=".08"/><path d="M6 3h15l5 5v21H6ZM21 3v6h5"/>'
LINES = '<path d="M10 14h12M10 18h12M10 22h8"/>'
ARROW = '<path d="M16 15v8m-4-4 4 4 4-4M10 25h12"/>'
IMAGE = '<path d="M9 14h14v10H9ZM9 24l5-6 4 4 2-3 3 5"/><circle cx="20" cy="17" r="1"/>'
MUSIC = '<path d="M14 23V13l8-2v10M14 16l8-2"/><circle cx="11.5" cy="23" r="2.5"/><circle cx="19.5" cy="21" r="2.5"/>'
VIDEO = '<path d="M10 14h13v11H10ZM14 17l5 3-5 3Z"/>'
CODE = '<path d="m13 15-4 4 4 4m6-8 4 4-4 4m-2-10-2 12"/>'
ARCHIVE = '<path d="M15 12h3v3h-3Zm0 6h3v3h-3Zm0 6h3v2h-3Z"/>'
HOME = '<path d="m4 15 12-11 12 11M7 13v15h18V13M13 28V18h6v10"/>'
SCREEN = '<path d="M3 5h26v18H3ZM11 28h10M16 23v5M6 9h8"/>'
DRIVE = '<path d="M6 5h20v23H6ZM6 20h20M10 24h2M16 24h6M10 9h12"/>'
NETWORK = '<path d="M11 3h10v8H11ZM3 22h10v7H3Zm16 0h10v7H19ZM16 11v6M8 22v-5h16v5"/>'
TRASH = '<path d="M8 9h16l-1 19H9ZM6 9h20M12 9V5h8v4M13 13v11m6-11v11"/>'


def svg(body, ink, paper):
    body = body.replace('{ink}', ink)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            '<rect x="1" y="1" width="30" height="30" fill="'+paper+'"/><g fill="none" stroke="'+ink+'" stroke-width="1.5" stroke-linejoin="miter" stroke-linecap="square">'
            +body+'</g></svg>\n')


def main():
    places = {'folder': FOLDER, 'folder-open': FOLDER+'<path d="M7 17h18l-4 11H3Z"/>',
              'folder-documents': FOLDER+LINES, 'folder-download': FOLDER+ARROW,
              'folder-downloads': FOLDER+ARROW, 'folder-pictures': FOLDER+IMAGE,
              'folder-music': FOLDER+MUSIC, 'folder-videos': FOLDER+VIDEO,
              'folder-templates': FOLDER+LINES, 'folder-publicshare': FOLDER+'<path d="M16 15v5M11 20h10M11 20v5m10-5v5"/>',
              'user-home': HOME, 'go-home': HOME, 'user-desktop': SCREEN, 'computer': SCREEN,
              'user-trash': TRASH, 'user-trash-full': TRASH,
              'document-open-recent': '<circle cx="16" cy="16" r="11"/><path d="M16 9v8l5 3"/>',
              'network-workgroup': NETWORK, 'network-server': DRIVE,
              'drive-harddisk': DRIVE, 'drive-removable-media': DRIVE}
    types = {'text-x-generic': LINES, 'text-plain': LINES, 'text-x-markdown': LINES,
             'text-markdown': LINES, 'x-office-document': LINES,
             'application-json': CODE, 'text-x-script': CODE, 'text-x-python': CODE,
             'application-x-executable': '<path d="m10 15 5 4-5 4m7 0h6"/>',
             'application-octet-stream': CODE, 'application-zip': ARCHIVE,
             'application-x-compressed-tar': ARCHIVE, 'application-x-7z-compressed': ARCHIVE,
             'application-pdf': LINES, 'image-x-generic': IMAGE,
             'audio-x-generic': MUSIC, 'video-x-generic': VIDEO}
    for theme, ink, paper, fallback in [('YoRHa', '#454438', '#e5e1cb', 'breeze,hicolor'),
                                         ('YoRHa-Night', '#c8c2a9', '#2f2c28', 'breeze-dark,breeze,hicolor')]:
        root = ROOT/theme
        root.mkdir(parents=True, exist_ok=True)
        for context, icons in [('places', places), ('mimetypes', {k: PAGE+v for k,v in types.items()})]:
            target = root/'yorha'/context;target.mkdir(parents=True, exist_ok=True)
            for name, body in icons.items():(target/(name+'.svg')).write_text(svg(body, ink, paper))
        (root/'index.theme').write_text(('[Icon Theme]\nName='+theme+
            '\nComment=Original geometric archive icons with system Breeze fallback\nInherits='+fallback+
            '\nDirectories=yorha/places,yorha/mimetypes\n\n'+''.join(
                f'[yorha/{folder}]\nSize=32\nMinSize=8\nMaxSize=512\nType=Scalable\nContext={context}\n\n'
                for folder,context in [('places','Places'),('mimetypes','MimeTypes')])).rstrip()+'\n')


if __name__ == '__main__':
    main()
