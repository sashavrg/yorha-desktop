"""Optional, pinned community trace. It is not part of the distributed artwork."""
import hashlib
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

URL = 'https://raw.githubusercontent.com/gigsoll/YoRHaLogo/5e24e32cae8a3028b87676f87a58962182975115/YORHA_clear.svg'
SHA256 = 'fa1e237c8f19685d41554942f0180e5f7fe278546a0685f3c09d48c882352477'
SVG = 'http://www.w3.org/2000/svg'

def fetch(destination):
    request=urllib.request.Request(URL,headers={'User-Agent':'YoRHa-Desktop-Installer/1'})
    with urllib.request.urlopen(request,timeout=20) as response:
        data=response.read(65537)
    if len(data)>65536 or hashlib.sha256(data).hexdigest()!=SHA256:
        raise ValueError('Optional emblem checksum mismatch; no artwork was installed')
    source=ET.fromstring(data)
    ET.register_namespace('',SVG)
    output=ET.Element('{'+SVG+'}svg',dict(viewBox='6.5 21.25 196.75 231.5',width='196.75',height='231.5'))
    def visit(node,parent):
        for child in node:
            name=child.tag.rsplit('}',1)[-1]
            if name not in ['g','path']: continue
            allowed=['d','transform','fill','fill-rule','style']
            attrs={key:value for key,value in child.attrib.items() if key in allowed}
            target=ET.SubElement(parent,'{'+SVG+'}'+name,attrs)
            visit(child,target)
    visit(source,output)
    destination=Path(destination)
    destination.write_bytes(ET.tostring(output,encoding='utf-8',xml_declaration=True))
    (destination.parent/'emblem-origin.txt').write_text('Optional upstream game emblem\n'+URL+'\nSHA256 '+SHA256+'\nGame branding: Square Enix / PlatinumGames; community trace: gigsoll.\nNot covered by the project GPL.\n')
