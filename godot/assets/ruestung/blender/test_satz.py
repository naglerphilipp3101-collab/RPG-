"""Testbild eines Waffensatzes: python3 test_satz.py -- <waffe> [slot,slot] (Bild nach $AUSBILD oder ins Temp-Verzeichnis)."""
import sys, os, time, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import rgeo as g, vorschau, waffensaetze as ws, iron, nachbearbeitung as nb
K = g.Koerper(); K.objekt()
a = sys.argv[sys.argv.index("--") + 1:]
waffe = a[0]
slots = a[1].split(",") if len(a) > 1 else ws.SLOTS
for slot in slots:
	t = time.time()
	ob = ws.BAU[waffe][slot](K) if waffe in ws.BAU else getattr(iron, waffe + "_" + slot)(K)
	if os.environ.get("NACH", "1") == "1":
		nb.bearbeiten(ob, K, slot, **json.loads(os.environ.get("NB", "{}")))
	print(slot, len(ob.data.polygons), "Flächen", "%.1fs" % (time.time() - t))
import json
opt = json.loads(os.environ.get("VOR", "{}"))
vorschau.bilder(os.environ.get("AUSBILD", os.path.join(tempfile.gettempdir(), "satz_" + waffe)),
	hoehe=tuple(opt.get("h", (-0.02, 1.9))), groesse=tuple(opt.get("g", (360, 560))), mitte_x=opt.get("x", 0.0),
	ansichten=[tuple(x) for x in opt.get("a", [(0, "v"), (90, "s"), (180, "h"), (35, "vs")])])
