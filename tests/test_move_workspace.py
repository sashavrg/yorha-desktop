"""Workspace transfer geometry for floating windows across monitor orientations."""
import importlib.machinery
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, call

SCRIPT=Path(__file__).resolve().parents[1]/'payload/.local/bin/yorha-move-workspace'
move_workspace=importlib.machinery.SourceFileLoader('move_workspace',str(SCRIPT)).load_module()

class MoveWorkspaceGeometryTests(unittest.TestCase):
    def setUp(self):
        self.landscape={'width':2560,'height':1440,'x':3129,'y':540,'scale':1,
                        'transform':0,'reserved':[0,78,0,0]}
        self.portrait={'width':2560,'height':1440,'x':5689,'y':0,'scale':1,
                       'transform':1,'reserved':[0,78,0,0]}

    def test_portrait_to_landscape_keeps_monitor_relative_size_and_fits(self):
        src=move_workspace.usable_area(self.portrait)
        dst=move_workspace.usable_area(self.landscape)
        size=(1142,1985); at=(5838,326)
        width,height,x,y=move_workspace.geometry(size,at,src,dst)
        self.assertLessEqual(width,dst[2]-24)
        self.assertLessEqual(height,dst[3]-24)
        self.assertAlmostEqual(width/dst[2],size[0]/src[2],delta=1/dst[2])
        self.assertAlmostEqual(height/dst[3],size[1]/src[3],delta=1/dst[3])
        self.assertGreaterEqual(x,dst[0]+12)
        self.assertGreaterEqual(y,dst[1]+12)
        self.assertAlmostEqual((x+width/2-dst[0])/dst[2],0.5,delta=0.01)

    def test_landscape_to_portrait_keeps_monitor_relative_size_and_fits(self):
        src=move_workspace.usable_area(self.landscape)
        dst=move_workspace.usable_area(self.portrait)
        size=(2048,1079); at=(3385,760)
        width,height,x,y=move_workspace.geometry(size,at,src,dst)
        self.assertLessEqual(width,dst[2]-24)
        self.assertLessEqual(height,dst[3]-24)
        self.assertAlmostEqual(width/dst[2],size[0]/src[2],delta=1/dst[2])
        self.assertAlmostEqual(height/dst[3],size[1]/src[3],delta=1/dst[3])
        self.assertGreaterEqual(x,dst[0]+12)
        self.assertGreaterEqual(y,dst[1]+12)

    def test_off_center_window_keeps_relative_position_and_roundtrips(self):
        src=move_workspace.usable_area(self.landscape)
        dst=move_workspace.usable_area(self.portrait)
        size=(1280,681); at=(3385,754)
        width,height,x,y=move_workspace.geometry(size,at,src,dst)
        self.assertAlmostEqual((x-dst[0])/dst[2],(at[0]-src[0])/src[2],delta=1/dst[2])
        self.assertAlmostEqual((y-dst[1])/dst[3],(at[1]-src[1])/src[3],delta=1/dst[3])
        restored=move_workspace.geometry((width,height),(x,y),dst,src)
        for actual,expected in zip(restored,(*size,*at)):
            self.assertAlmostEqual(actual,expected,delta=1)

    def test_destination_wait_requires_monitor_to_match_workspace(self):
        window={'workspace':{'id':8},'monitor':1}
        destination={'id':8,'monitorID':0}
        self.assertFalse(move_workspace.reached_destination(window,8,destination))
        window['monitor']=0
        self.assertTrue(move_workspace.reached_destination(window,8,destination))

    def test_move_command_positions_resized_portrait_window_with_integer_pixels(self):
        original={'address':'0xtest','workspace':{'id':8},'monitor':0,
                  'at':[5838,326],'size':[1142,1985],'floating':True}
        moved={**original,'workspace':{'id':7},'monitor':1,'size':[2030,1089]}
        replies={'activewindow':original,
                 'monitors':[{**self.portrait,'id':0},{**self.landscape,'id':1}],
                 'clients':[moved],'workspaces':[{'id':7,'monitorID':1}]}
        with tempfile.TemporaryDirectory() as runtime, \
             patch.dict(os.environ,{'XDG_RUNTIME_DIR':runtime}), \
             patch('sys.argv',['yorha-move-workspace','7']), \
             patch.object(move_workspace,'query',side_effect=lambda name:replies[name]), \
             patch.object(move_workspace,'dispatch') as dispatch, \
             patch.object(move_workspace.time,'sleep'):
            move_workspace.main()
        self.assertIn(call('resizewindowpixel','exact 2030 1089,address:0xtest'),dispatch.call_args_list)
        self.assertEqual(dispatch.call_args_list[-1],
                         call('movewindowpixel','exact 3394 754,address:0xtest'))

if __name__=='__main__': unittest.main()
