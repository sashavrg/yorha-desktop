"""File safety and repeatability tests run only in disposable homes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from install_lib import Transaction, restore, InstallError

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix='yorha-test-')
        self.home=Path(self.work.name)/'home with spaces'
        self.home.mkdir()
    def tearDown(self): self.work.cleanup()

    def test_regular_and_leaf_symlink_roundtrip(self):
        original=self.home/'original';original.write_text('external data')
        link=self.home/'theme';link.symlink_to('original')
        file=self.home/'regular';file.write_text('before');file.chmod(0o640)
        tx=Transaction(self.home)
        tx.put('theme',b'after')
        tx.put('regular',b'after')
        tx.put('new-file',b'new')
        tx.finish()
        self.assertFalse(link.is_symlink())
        self.assertEqual(original.read_text(),'external data')
        restore(tx.backup)
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link),'original')
        self.assertEqual(file.read_text(),'before')
        self.assertEqual(file.stat().st_mode&0o777,0o640)
        self.assertFalse((self.home/'new-file').exists())

    def test_parent_dotfiles_symlink_is_preserved(self):
        actual=self.home/'dotfiles';actual.mkdir()
        (self.home/'.config').symlink_to('dotfiles')
        (actual/'config').write_text('before')
        tx=Transaction(self.home);tx.put('.config/config',b'after');tx.finish()
        restore(tx.backup)
        self.assertEqual((actual/'config').read_text(),'before')
        self.assertTrue((self.home/'.config').is_symlink())

    def test_parent_symlink_outside_home_is_refused(self):
        outside=Path(self.work.name)/'outside';outside.mkdir()
        (self.home/'escape').symlink_to(outside)
        tx=Transaction(self.home)
        with self.assertRaises(InstallError):tx.put('escape/file',b'no')
        self.assertFalse((outside/'file').exists())

    def test_edited_files_require_force(self):
        tx=Transaction(self.home);tx.put('file',b'new');tx.finish()
        (self.home/'file').write_text('user edit')
        with self.assertRaises(InstallError):restore(tx.backup)
        self.assertEqual((self.home/'file').read_text(),'user edit')
        restore(tx.backup,force=True)
        self.assertFalse((self.home/'file').exists())

    def test_interrupted_install_is_recoverable(self):
        tx=Transaction(self.home);tx.put('file',b'new')
        restore(tx.backup)
        self.assertFalse((self.home/'file').exists())

    def test_runtime_directory_rebuild_and_rollback(self):
        runtime=self.home/'runtime';runtime.mkdir()
        (runtime/'old-library').write_text('Python before the upgrade')
        (runtime/'interpreter').symlink_to('/usr/bin/python3')
        tx=Transaction(self.home)
        tx.replace_directory('runtime')
        tx.generated_dir('runtime')
        runtime.mkdir();(runtime/'new-library').write_text('Python after the upgrade')
        tx.finish()
        restore(tx.backup)
        self.assertEqual((runtime/'old-library').read_text(),'Python before the upgrade')
        self.assertTrue((runtime/'interpreter').is_symlink())
        self.assertFalse((runtime/'new-library').exists())

    def test_traversal_is_refused(self):
        tx=Transaction(self.home)
        with self.assertRaises(InstallError):tx.put('../escape',b'no')
        with self.assertRaises(InstallError):tx.put('/tmp/escape',b'no')

    def test_wizard_install_reinstall_restore(self):
        args=['./install.sh','--yes','--no-deps','--no-venv','--no-assets','--target',str(self.home)]
        subprocess.run(args,cwd=REPO,check=True,capture_output=True,text=True)
        main=self.home/'.config/hypr/hyprland.conf'
        before=main.read_text()
        main.write_text(before+'\n# personal monitor\n')
        config=self.home/'.config/yorha/settings.json'
        config.write_text('{"timezone":"UTC"}')
        subprocess.run(args+['--layout','overlay'],cwd=REPO,check=True,capture_output=True,text=True)
        self.assertEqual(main.read_text().count('source = $HOME/.config/hypr/yorha-session.conf'),1)
        self.assertIn('# personal monitor',main.read_text())
        self.assertEqual(json.loads(config.read_text()),{'timezone':'UTC'})
        backups=sorted((self.home/'.local/state/yorha/backups').iterdir())
        restore(backups[-1])
        self.assertEqual(main.read_text(),before+'\n# personal monitor\n')
        restore(backups[0],force=True)
        self.assertFalse(main.exists())
        self.assertFalse(config.exists())

    def test_dry_run_has_no_writes(self):
        target=self.home/'new-home'
        subprocess.run(['./install.sh','--dry-run','--no-deps','--target',str(target)],cwd=REPO,check=True,capture_output=True)
        self.assertFalse(target.exists())

    def test_alternate_home_cannot_activate(self):
        result=subprocess.run(['./install.sh','--yes','--no-deps','--activate','--target',str(self.home)],cwd=REPO,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.home/'.config').exists())

class LocalTaskTests(unittest.TestCase):
    def test_revision_conflict_and_persistence(self):
        sys.path.insert(0,str(REPO/'payload/.local/share/yorha'))
        import planner_store
        with tempfile.TemporaryDirectory() as work:
            previous=planner_store.PATH
            planner_store.PATH=Path(work)/'tasks.json'
            try:
                a=planner_store.read();b=planner_store.read()
                a['items']=[{'id':'sample','title':'Demo','done':False}]
                first=planner_store.write(a,a['rev'])
                with self.assertRaises(planner_store.Conflict):planner_store.write(b,b['rev'])
                self.assertEqual(planner_store.read(),first)
                self.assertEqual(planner_store.PATH.stat().st_mode&0o777,0o600)
            finally:planner_store.PATH=previous


class ComponentTests(unittest.TestCase):
    def test_component_disable_and_optional_camera(self):
        with tempfile.TemporaryDirectory() as work:
            home=Path(work)/'operator'
            command=['./install.sh','--yes','--no-deps','--no-venv','--no-assets','--target',str(home)]
            subprocess.run(command+['--phonecam'],cwd=REPO,check=True,capture_output=True)
            bar=json.loads((home/'.config/waybar/config').read_text())
            self.assertIn('custom/phonecam',bar['modules-right'])
            subprocess.run(command+['--components',''],cwd=REPO,check=True,capture_output=True)
            self.assertFalse((home/'.config/yorha/yorha-desktop-enabled').exists())
            self.assertFalse((home/'.config/yorha/yorha-cockpit-widget-enabled').exists())
            self.assertFalse((home/'.config/yorha/standby-enabled').exists())
            managed=json.loads((home/'.local/share/yorha/modes/files.json').read_text())
            self.assertNotIn('.config/starship.toml',managed)
            self.assertIn('.config/kitty/yorha.conf',managed)

class PaletteTests(unittest.TestCase):
    def test_switches_all_managed_sources_without_live_session(self):
        with tempfile.TemporaryDirectory() as work:
            home=Path(work)/'operator'
            subprocess.run(['./install.sh','--yes','--no-deps','--no-venv','--no-assets','--target',str(home)],cwd=REPO,check=True,capture_output=True)
            stub=Path(work)/'bin';stub.mkdir()
            command=stub/'gsettings';command.write_text('#!/bin/sh\nexit 0\n');command.chmod(0o755)
            env=dict(os.environ,HOME=str(home),PATH=str(stub)+':'+os.environ['PATH'],HYPRLAND_INSTANCE_SIGNATURE='',DBUS_SESSION_BUS_ADDRESS='')
            for mode in ['day','night']:
                subprocess.run([str(home/'.local/bin/yorha-mode'),mode],env=env,check=True,capture_output=True)
                profiles=home/'.local/share/yorha/modes'
                for name in json.loads((profiles/'files.json').read_text()):
                    self.assertEqual((home/name).read_bytes(),(profiles/mode/name).read_bytes())
                self.assertEqual((home/'.local/share/yorha/mode').read_text().strip(),mode)


class DependencyTests(unittest.TestCase):
    def test_fedora_resolves_wayland_provider_and_reuses_installed_stack(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import dependencies
        calls=[]
        def run(command, **kwargs):
            calls.append(command)
            if command[0]=='rpm':
                return SimpleNamespace(stdout='hyprland\nswww\nstarship\n',returncode=0)
            if command[:2]==['dnf','repoquery']:
                return SimpleNamespace(stdout='rofi\nkitty\n',returncode=0)
            return SimpleNamespace(stdout='',returncode=0)
        with patch.object(dependencies,'packages',return_value=['hyprland','swww','rofi-wayland','kitty','starship']), patch.object(dependencies.subprocess,'run',side_effect=run), patch.object(dependencies.shutil,'which',return_value='/usr/bin/command'):
            dependencies.install('fedora',[])
        self.assertEqual(calls[-1],['sudo','dnf','install','rofi','kitty'])
        query=next(c for c in calls if c[:2]==['dnf','repoquery'])
        self.assertEqual(query[query.index('--queryformat')+1],'%{name}'+chr(92)+'n')

    def test_missing_fedora_package_stops_before_package_install(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import dependencies
        calls=[]
        def run(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(stdout='',returncode=0)
        with patch.object(dependencies,'packages',return_value=['missing-package']), patch.object(dependencies.subprocess,'run',side_effect=run), patch.object(dependencies.shutil,'which',return_value='/usr/bin/command'):
            with self.assertRaises(RuntimeError):dependencies.install('fedora',[])
        self.assertFalse(any(c[0]=='sudo' for c in calls))

if __name__=='__main__':unittest.main()
