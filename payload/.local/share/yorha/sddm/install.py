#!/usr/bin/env python3
"""Install the reviewed YoRHa SDDM theme without restarting the login manager."""
from pathlib import Path
import argparse,datetime,os,shutil,subprocess,json,configparser,tempfile
def relabel(*paths):
 if shutil.which("restorecon"): subprocess.run(["restorecon","-RF",*map(str,paths)],check=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode',choices=['day','night'],default='night')
parser.add_argument('--restore',type=Path,help='Restore an installation backup')
parser.add_argument('--check',action='store_true',help='Validate the staged theme without installing')
a=parser.parse_args();source=Path(__file__).resolve().parent/'YoRHa'
target=Path('/usr/share/sddm/themes/YoRHa');override=Path('/etc/sddm.conf.d/zzzzzz-yorha.conf')
if not a.check and os.geteuid()!=0:raise SystemExit('Run with sudo to install system-owned SDDM files.')
if a.restore:
 b=a.restore.resolve();manifest=json.loads((b/'manifest.json').read_text())
 for name,p in [('theme',target),('override',override)]:
  if p.is_dir():shutil.rmtree(p)
  elif p.exists():p.unlink()
  if manifest[name]:
   if name=='theme':shutil.copytree(b/name,p)
   else:shutil.copy2(b/name,p)
 relabel(*(p for p in [target,override] if p.exists()))
 print('Previous login theme restored. Takes effect at the next login; SDDM was not restarted.');raise SystemExit(0)
for name in ['Main.qml','metadata.desktop','theme-'+a.mode+'.conf','assets/icons.ttf','assets/emblem-'+a.mode+'.png','backgrounds/'+a.mode+'/yorha-2560x1440.png','backgrounds/'+a.mode+'/yorha-1440x2560.png']:
 if not (source/name).is_file():raise SystemExit('Missing theme file: '+name)
config=configparser.ConfigParser();config.read(source/('theme-'+a.mode+'.conf'))
assert config['General']['allowEmptyPassword']=='false'
if a.check:print('Theme assets and configuration verified: '+str(source));raise SystemExit(0)
if not Path('/usr/bin/sddm').exists():raise SystemExit('Install SDDM first. This installer does not change display managers.')
target.parent.mkdir(parents=True,exist_ok=True)
b=Path('/var/backups/yorha-sddm')/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');b.mkdir(parents=True,mode=0o700)
manifest={'theme':target.exists(),'override':override.exists()}
if target.exists():shutil.copytree(target,b/'theme')
if override.exists():shutil.copy2(override,b/'override')
# Preserve all prior SDDM settings for reference, without changing them.
if Path('/etc/sddm.conf.d').exists():shutil.copytree('/etc/sddm.conf.d',b/'sddm.conf.d')
if Path('/etc/sddm.conf').exists():shutil.copy2('/etc/sddm.conf',b/'sddm.conf')
(b/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Stage a complete root-owned theme beside the final path before selecting it.
staged=Path(tempfile.mkdtemp(prefix='.yorha-',dir=target.parent))
try:
 shutil.copytree(source,staged,dirs_exist_ok=True)
 shutil.copy2(staged/('theme-'+a.mode+'.conf'),staged/'theme.conf')
 for p in staged.rglob('*'):os.chmod(p,0o755 if p.is_dir() else 0o644)
 os.chmod(staged,0o755)
 if target.exists():shutil.rmtree(target)
 os.replace(staged,target)
 override.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.yorha-',dir=override.parent)
 with os.fdopen(fd,'w') as out:out.write('[Theme]\nCurrent=YoRHa\n')
 os.chmod(tmp,0o644);os.replace(tmp,override)
 relabel(target,override)
except Exception:
 # Roll back a failed installation before returning the error.
 if target.exists():shutil.rmtree(target)
 if manifest['theme']:shutil.copytree(b/'theme',target)
 if manifest['override']:shutil.copy2(b/'override',override)
 elif override.exists():override.unlink()
 raise
finally:
 if staged.exists():shutil.rmtree(staged)
print('YoRHa '+a.mode+' login screen installed. SDDM was not restarted.')
print('Backup: '+str(b))
print('Restore: sudo python3 '+str(Path(__file__).resolve())+' --restore '+str(b))
