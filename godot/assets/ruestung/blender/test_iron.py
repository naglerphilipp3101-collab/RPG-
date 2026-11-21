import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import rgeo as g, vorschau, iron, importlib
K = g.Koerper(); K.objekt()
for name in sys.argv[sys.argv.index("--") + 1:]:
	getattr(iron, name)(K)
import json
opt = json.loads(os.environ.get("VOR", "{}"))
vorschau.bilder("/tmp/claude-0/-home-user/dd1e65eb-5903-5677-845e-5a5de5df456f/scratchpad/iron", hoehe=tuple(opt.get("h", (0.7, 1.85))), groesse=tuple(opt.get("g", (420, 460))), mitte_x=opt.get("x", 0.0), ansichten=[tuple(a) for a in opt.get("a", [(0, "vorne"), (90, "seite"), (180, "hinten")])])
