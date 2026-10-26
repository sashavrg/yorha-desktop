"""Native dialog confirmation, preview isolation and day/night text contrast."""
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT/'payload/.local/bin'
dialog = importlib.machinery.SourceFileLoader('yorha_dialog', str(BIN/'yorha-dialog')).load_module()


class DialogTests(unittest.TestCase):
    def test_only_explicit_successful_execute_confirms(self):
        for output, code, expected in [('EXECUTE\n', 0, True), ('CANCEL\n', 0, False),
                                       ('', 0, False), ('EXECUTE\n', 1, False),
                                       ('EXECUTE extra\n', 0, False)]:
            with self.subTest(output=output, code=code), \
                 patch.object(dialog, 'find_command', return_value='/stub/hyprland-dialog'), \
                 patch.object(dialog.subprocess, 'run', return_value=SimpleNamespace(stdout=output, returncode=code)):
                self.assertEqual(dialog.show('confirm', 'SYSTEM', 'Request'), expected)

    def test_missing_native_tool_uses_rofi_and_still_requires_execute(self):
        with patch.object(dialog, 'find_command', side_effect=lambda name: '/stub/rofi' if name == 'rofi' else None), \
             patch.object(dialog.subprocess, 'run', return_value=SimpleNamespace(stdout='EXECUTE\n', returncode=0)) as run:
            self.assertTrue(dialog.show('confirm', 'SYSTEM', 'Request'))
        self.assertEqual(run.call_args.args[0][0], '/stub/rofi')
        self.assertEqual(run.call_args.kwargs['input'], 'CANCEL\nEXECUTE\n')


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        root = Path(self.work.name)
        self.home = root/'home';local = self.home/'.local/bin';local.mkdir(parents=True)
        self.stub = root/'bin';self.stub.mkdir()
        self.actions = root/'actions';self.dialogs = root/'dialogs'
        shutil.copy2(BIN/'yorha-dialog', local/'yorha-dialog')
        native = local/'hyprland-dialog'
        native.write_text('''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['DIALOG_LOG'],'a') as out:out.write(json.dumps(sys.argv[1:])+'\\n')
print(os.environ.get('DIALOG_CHOICE',''))
''')
        native.chmod(0o755)
        rofi = self.stub/'rofi'
        rofi.write_text("#!/usr/bin/env python3\nimport os\nprint(os.environ.get('MENU_CHOICE','05 : Shut down'))\n")
        rofi.chmod(0o755)
        for name in ['systemctl', 'hyprctl']:
            script = self.stub/name
            script.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
with open(os.environ['ACTION_LOG'],'a') as out:out.write(Path(sys.argv[0]).name+' '+ ' '.join(sys.argv[1:])+'\\n')
raise SystemExit(int(os.environ.get('ACTION_RETURN','0')))
''')
            script.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.stub)+':'+os.environ['PATH'],
                        ACTION_LOG=str(self.actions), DIALOG_LOG=str(self.dialogs), DIALOG_CHOICE='EXECUTE')

    def tearDown(self):
        self.work.cleanup()

    def run_power(self, args=(), **env):
        return subprocess.run([str(BIN/'yorha-power'), *args], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=5)

    def test_close_cancel_or_unknown_response_never_runs_action(self):
        for choice in ['', 'CANCEL', 'other']:
            with self.subTest(choice=choice):
                self.assertEqual(self.run_power(DIALOG_CHOICE=choice).returncode, 0)
                self.assertFalse(self.actions.exists())

    def test_preview_execute_never_runs_any_power_action(self):
        for action in ['logout', 'reboot', 'shutdown']:
            with self.subTest(action=action):
                self.assertEqual(self.run_power(['--preview', action]).returncode, 0)
                self.assertFalse(self.actions.exists())
        for line in self.dialogs.read_text().splitlines():
            self.assertIn('PREVIEW ONLY', json.loads(line)[json.loads(line).index('--text')+1])

    def test_execute_dispatches_selected_action_once(self):
        self.assertEqual(self.run_power().returncode, 0)
        self.assertEqual(self.actions.read_text(), 'systemctl poweroff\n')

    def test_failed_action_shows_request_failed_notice(self):
        self.assertEqual(self.run_power(ACTION_RETURN='1').returncode, 1)
        requests = [json.loads(line) for line in self.dialogs.read_text().splitlines()]
        self.assertEqual(len(requests), 2)
        self.assertIn('SYSTEM / REQUEST FAILED', requests[-1])
        self.assertEqual(self.actions.read_text(), 'systemctl poweroff\n')


class PaletteContrastTests(unittest.TestCase):
    def test_body_buttons_and_derived_placeholder_are_readable_in_both_modes(self):
        def luminance(rgb):
            linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            return sum(v*w for v,w in zip(linear, [.2126, .7152, .0722]))
        def contrast(a,b):
            hi,lo = sorted([luminance(a),luminance(b)], reverse=True)
            return (hi+.05)/(lo+.05)
        for mode in ['day', 'night']:
            path = ROOT/'payload/.local/share/yorha/modes'/mode/'.config/hypr/hyprtoolkit.conf'
            colors = {}
            for line in path.read_text().splitlines():
                if '= 0xff' in line:
                    key,value = (s.strip() for s in line.split('=',1))
                    colors[key] = tuple(int(value[i:i+2],16)/255 for i in [4,6,8])
            pairs = [('body', colors['text'], colors['background']),
                     ('button', colors['text'], colors['base']),
                     ('placeholder', tuple(c*.6 for c in colors['text']), colors['base']),
                     ('accent', colors['bright_text'] if mode == 'day' else colors['background'], colors['accent'])]
            # This toolkit version paints a half-opacity, darkened accent over
            # both the input background and its glyphs for a text selection.
            selection = tuple(c*.6 for c in colors['accent'])
            pairs.append(('selected text',
                          tuple((a+b)*.5 for a,b in zip(selection,colors['text'])),
                          tuple((a+b)*.5 for a,b in zip(selection,colors['base']))))
            for label,foreground,background in pairs:
                with self.subTest(mode=mode, element=label):
                    self.assertGreaterEqual(contrast(foreground,background), 4.5)


if __name__ == '__main__':
    unittest.main()
