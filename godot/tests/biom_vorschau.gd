extends SceneTree
## Prüft die Biom-Regeln ohne Terrain3D an einem Weltgenerator-Export in res://welt_daten:
##  1. Steuerkarte nach den Regeln umbauen (wie beim Weltimport) -> Bild der Bodentexturen (Kies an Flüssen)
##  2. Natur-Kacheln mit den echten Höhen berechnen -> Zählung je Biom und Übersichtsbild der Objekte
## Aufruf: Godot --headless --path godot -s res://tests/biom_vorschau.gd -- [ausschnitt_m]
## Bilder: user://biom_boden.png, user://biom_natur.png

const NaturScript := preload("res://scripts/natur.gd")
const FARBEN := [Color(0.86, 0.8, 0.6), Color(0.45, 0.65, 0.3), Color(0.35, 0.45, 0.2), Color(0.22, 0.35, 0.2),
	Color(0.4, 0.42, 0.3), Color(0.7, 0.62, 0.4), Color(0.5, 0.5, 0.5), Color(0.95, 0.95, 0.98), Color(0.35, 0.55, 0.8)]


## Ersatz für Terrain3D: Höhen aus hoehe_*.r32
class Hoehen:
	var bild: Image
	var n := 0
	var mpp := 1.0
	var halb := 0.0

	func get_height(p: Vector3) -> float:
		var fx := (p.x + halb) / mpp - 0.5
		var fz := (p.z + halb) / mpp - 0.5
		var x := clampi(int(fx), 0, n - 2)
		var z := clampi(int(fz), 0, n - 2)
		var tx := clampf(fx - x, 0.0, 1.0)
		var tz := clampf(fz - z, 0.0, 1.0)
		var a := lerpf(bild.get_pixel(x, z).r, bild.get_pixel(x + 1, z).r, tx)
		var b := lerpf(bild.get_pixel(x, z + 1).r, bild.get_pixel(x + 1, z + 1).r, tx)
		return lerpf(a, b, tz)


class FakeTerrain:
	var data


func _initialize() -> void:
	var ordner := "res://welt_daten"
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ordner.path_join("welt.json")))
	var n: int = int(meta["aufloesung"])
	var mpp: float = float(meta["meter_pro_pixel"])
	var welt_m: float = float(meta["welt_m"])

	# 1. Bodentexturen
	var importer = load("res://assets/welt/welt_import.gd").new()
	importer.daten_ordner = ordner
	var sb := FileAccess.get_file_as_bytes(ordner.path_join(meta["steuerung"]["datei"]))
	var neu: PackedByteArray = importer._steuerkarte_umbauen(sb, n, mpp, welt_m, meta)
	var werte := neu.to_int32_array()
	var zaehler := {}
	var schritt := maxi(1, n / 1024)
	var bild := Image.create(n / schritt, n / schritt, false, Image.FORMAT_RGB8)
	for y in range(0, n, schritt):
		for x in range(0, n, schritt):
			var v := werte[y * n + x]
			var b := (v >> 27) & 31
			var a := (v >> 22) & 31
			var bl := float((v >> 14) & 255) / 255.0
			zaehler[b] = int(zaehler.get(b, 0)) + 1
			bild.set_pixel(x / schritt, y / schritt, (FARBEN[b] as Color).lerp(FARBEN[a], bl))
	bild.save_png(ProjectSettings.globalize_path("user://biom_boden.png"))
	var namen: Array = BiomRegeln.laden()["texturen"]
	var anteile := {}
	for b in zaehler:
		anteile[namen[b] if b < namen.size() else str(b)] = "%.1f %%" % (100.0 * zaehler[b] / (n * n / schritt / schritt))
	print("BIOM Bodentexturen (Grundtextur): ", anteile)

	# 2. Natur
	var h := Hoehen.new()
	h.bild = Image.create_from_data(n, n, false, Image.FORMAT_RF, FileAccess.get_file_as_bytes(ordner.path_join(meta["hoehe"]["datei"])))
	h.n = n
	h.mpp = mpp
	h.halb = welt_m / 2.0
	var t := FakeTerrain.new()
	t.data = h
	var main := {"terrain": t}
	var natur = NaturScript.new()
	natur.setup(main, Node3D.new(), ordner)
	var ausschnitt := 1024.0
	var args := OS.get_cmdline_user_args()
	if args.size() > 0 and args[0].is_valid_float():
		ausschnitt = float(args[0])
	var kacheln := int(ausschnitt / natur.KACHEL)
	var je_biom := {}
	var karte := Image.create(int(ausschnitt), int(ausschnitt), false, Image.FORMAT_RGB8)
	var start := Time.get_ticks_msec()
	# Ausschnitt um das Startdorf
	var mitte := Vector2.ZERO
	for m in JSON.parse_string(FileAccess.get_file_as_string(ordner.path_join("marker.json"))):
		if m.get("name", "") == "Startdorf":
			mitte = Vector2(float(m["x"]), float(m["z"]))
	var k0 := Vector2i(floori((mitte.x - ausschnitt / 2.0) / natur.KACHEL), floori((mitte.y - ausschnitt / 2.0) / natur.KACHEL))
	var x0: float = k0.x * natur.KACHEL
	var z0: float = k0.y * natur.KACHEL
	for py in int(ausschnitt):
		for px in int(ausschnitt):
			var r: Dictionary = natur._regel(x0 + px, z0 + py)
			var tid: int = int(r.get("textur", -1))
			if r.is_empty():
				karte.set_pixel(px, py, Color(0.15, 0.3, 0.5))
			elif r["biom"] == "stadt":
				karte.set_pixel(px, py, Color(0.75, 0.55, 0.45))
			else:
				karte.set_pixel(px, py, (FARBEN[tid] as Color).darkened(0.25))
	for kz in kacheln:
		for kx in kacheln:
			for e in natur._kachel(k0 + Vector2i(kx, kz)):
				var biom: String = natur.biom_name(e[1], e[3])
				var art: String
				var farbe := Color.WHITE
				match int(e[0]):
					natur.BAUM:
						art = natur.BAUM_ID[int(e[4])] + ("_uralt" if int(e[5]) == 2 else "")
						farbe = Color(0.05, 0.2, 0.05)
					natur.BUSCH:
						art = "busch"
						farbe = Color(0.2, 0.35, 0.1)
					natur.PFLANZE:
						art = ["hanf", "beeren", "kraut"][int(e[4])]
						farbe = [Color(0.9, 0.9, 0.3), Color(0.8, 0.1, 0.2), Color(0.9, 0.5, 0.9)][int(e[4])]
					natur.TOTBAUM:
						art = "totbaum"
						farbe = Color(0.3, 0.2, 0.1)
					_:
						art = String(e[4])
						farbe = Color(0.5, 0.3, 0.1) if art != "pfuetze" else Color(0.2, 0.4, 0.9)
				if not je_biom.has(biom):
					je_biom[biom] = {}
				je_biom[biom][art] = int(je_biom[biom].get(art, 0)) + 1
				var p := Vector2i(int(e[1] - x0), int(e[3] - z0))
				if Rect2i(Vector2i.ZERO, karte.get_size()).has_point(p):
					karte.set_pixel(p.x, p.y, farbe)
	karte.save_png(ProjectSettings.globalize_path("user://biom_natur.png"))
	print("BIOM Natur im Ausschnitt %d m um das Startdorf (%d ms):" % [int(ausschnitt), Time.get_ticks_msec() - start])
	for b in je_biom:
		print("BIOM   %s: %s" % [b, je_biom[b]])
	print("BIOM Bilder: ", ProjectSettings.globalize_path("user://"))
	quit()
