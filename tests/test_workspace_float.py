"""Monitor-aware geometry for the all-float helper."""
import importlib.machinery
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'payload/.local/bin/yorha-workspace-float'
workspace_float=importlib.machinery.SourceFileLoader('workspace_float',str(SCRIPT)).load_module()

class WorkspaceFloatGeometryTests(unittest.TestCase):
    def test_portrait_monitor_scales_uniformly_and_clamps_position(self):
        monitor={'width':2560,'height':1440,'x':5689,'y':0,'scale':1,
                 'transform':1,'reserved':[0,78,0,0]}
        size=(2532,1334)
        fitted=workspace_float.fit(size,(3143,632),monitor)
        width,height,x,y=fitted
        self.assertLessEqual(width,1416)
        self.assertLessEqual(height,2482)
        self.assertAlmostEqual(width/height,size[0]/size[1],delta=0.002)
        self.assertGreaterEqual(x,5701)
        self.assertGreaterEqual(y,90)

    def test_landscape_window_inside_work_area_keeps_size_and_position(self):
        monitor={'width':2560,'height':1440,'x':3129,'y':540,'scale':1,
                 'transform':0,'reserved':[0,78,0,0]}
        self.assertEqual(workspace_float.fit((1280,720),(3500,800),monitor),
                         (1280,720,3500,800))

if __name__=='__main__': unittest.main()
