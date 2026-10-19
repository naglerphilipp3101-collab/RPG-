@tool
class_name WeltImport
extends Node3D
## Importiert einen Export aus dem Weltgenerator (welt.json + hoehe_*.r32 + farbe_1024.png) in Terrain3D.
## Benötigt das Plugin Terrain3D (Godot Asset Library) – aktiviert unter Projekt > Projekteinstellungen > Plugins.
##
## 1. welt_export.zip in einen Ordner im Projekt entpacken, z. B. res://welt_daten/
## 2. diesen Ordner unten bei "daten_ordner" eintragen
## 3. Knopf "Welt importieren" drücken, danach die Szene speichern (Strg+S)

## Ordner mit welt.json, hoehe_*.r32 und farbe_1024.png
@export_dir var daten_ordner: String = "res://welt_daten"
## Statt Bodentexturen die flache Farbkarte des Generators zeigen (zum Vergleich mit dem Editor)
@export var farbkarte_anzeigen: bool = false:
	set(v):
		farbkarte_anzeigen = v
		var t := get_node_or_null("Terrain3D")
		if t:
			t.set("show_colormap", v)
## Meeresfläche auf Höhe 0
@export var meer_anzeigen: bool = true:
	set(v):
		meer_anzeigen = v
		var m := get_node_or_null("Meer")
		if m:
			m.visible = v

## Bodentexturen in der Reihenfolge von data/biome.json ("texturen"; die IDs 0–7 entsprechen den Generator-Biomen,
## 8 ist das Kiesbett der Flüsse): Name, Kachelgröße in Metern und Farbton – einmal für die Fotoscans
## (texturen_scan/, siehe tests/scans_umwandeln.gd), einmal für die selbst erzeugten Texturen (texturen/),
## die genommen werden, wenn die Scans fehlen.
const BODEN := [
	["sand", 5.0, 3.0, Color.WHITE, Color(1.0, 0.98, 0.95)], ["wiese", 2.4, 3.0, Color(0.68, 0.84, 0.5), Color(0.6, 0.64, 0.82)],
	["laubboden", 3.0, 3.0, Color(0.7, 0.78, 0.58), Color(0.6, 0.72, 0.52)], ["nadelboden", 3.2, 3.0, Color(0.85, 0.88, 0.78), Color(0.72, 0.8, 0.64)],
	["sumpf", 2.6, 4.0, Color(0.85, 0.92, 0.75), Color.WHITE], ["steppe", 4.0, 3.0, Color(1.0, 1.0, 0.9), Color(0.92, 0.9, 0.88)],
	["fels", 5.4, 8.0, Color.WHITE, Color.WHITE], ["schnee", 3.0, 6.0, Color.WHITE, Color.WHITE],
	["kies", 2.2, 2.5, Color.WHITE, Color.WHITE],
]
const WEG_ID := 8 # in älteren Exporten des Generators: Weg-Textur (wird beim Import durch das Biom darunter ersetzt)

## Platzhalter (farbige Säulen, Namen, Feldflächen) für die Marker anzeigen
@export var marker_platzhalter: bool = true:
	set(v):
		marker_platzhalter = v
		var m := get_node_or_null("Marker")
		if m:
			for k in m.get_children():
				for c in k.get_children():
					c.visible = v

@export_tool_button("Welt importieren", "Load") var _knopf_import := importieren

## Seitenlänge der importierten Welt in Metern (z. B. 4096 oder 8192)
var welt_groesse := 0.0
var _hoehe_bild: Image
var _mpp := 1.0


func importieren() -> void:
	if not ClassDB.class_exists("Terrain3D"):
		push_error("Weltimport: Terrain3D ist nicht installiert oder nicht aktiviert.")
		return
	var meta_pfad := daten_ordner.path_join("welt.json")
	if not FileAccess.file_exists(meta_pfad):
		push_error("Weltimport: %s nicht gefunden." % meta_pfad)
		return
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(meta_pfad))
	var n: int = int(meta["aufloesung"])
	var mpp: float = float(meta["meter_pro_pixel"])

	# Höhen: float32, Meter
	var bytes := FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["hoehe"]["datei"]))
	if bytes.size() != n * n * 4:
		push_error("Weltimport: Höhendatei hat die falsche Größe (%d statt %d Bytes)." % [bytes.size(), n * n * 4])
		return
	var hoehe := Image.create_from_data(n, n, false, Image.FORMAT_RF, bytes)
	_hoehe_bild = hoehe
	_mpp = mpp

	# Farbkarte auf Höhenkarten-Größe bringen
	var farbe: Image = null
	var farb_pfad := daten_ordner.path_join(meta["farbe"]["datei"])
	var welt_m: float = float(meta.get("welt_m", n * mpp))
	# Die Farbkarte färbt in Terrain3D alle Bodentexturen ein (Wege würden grün, Waldboden sehr dunkel).
	# Deshalb nur laden, wenn sie zum Vergleich angezeigt werden soll.
	if (farbkarte_anzeigen or not meta.has("steuerung")) and FileAccess.file_exists(farb_pfad):
		farbe = Image.load_from_file(ProjectSettings.globalize_path(farb_pfad))
		farbe.convert(Image.FORMAT_RGBA8)
		farbe.resize(n, n, Image.INTERPOLATE_BILINEAR)

	# Biom-Steuerkarte (Terrain3D-Format, uint32 je Pixel)
	var steuer: Image = null
	if meta.has("steuerung"):
		var sb := FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["steuerung"]["datei"]))
		if sb.size() == n * n * 4:
			sb = _steuerkarte_umbauen(sb, n, mpp, float(meta.get("welt_m", n * mpp)), meta)
			steuer = Image.create_from_data(n, n, false, Image.FORMAT_RF, sb)
		else:
			push_warning("Weltimport: Steuerkarte hat falsche Größe, Biome werden übersprungen.")

	var terrain: Node3D = get_node_or_null("Terrain3D")
	if terrain == null:
		terrain = ClassDB.instantiate("Terrain3D")
		terrain.name = "Terrain3D"
		add_child(terrain)
		_besitzer(terrain)
	var datenordner := daten_ordner.path_join("terrain3d")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(datenordner))
	terrain.set("data_directory", datenordner)
	# Große Welten: größere Regionen (Terrain3D erlaubt max. 32 x 32 Regionen)
	var region := 256
	while n / region > 16 and region < 2048:
		region *= 2
	if int(terrain.get("region_size")) != region:
		terrain.call("change_region_size", region)
	terrain.set("vertex_spacing", mpp)
	# Welt zentriert um den Ursprung: x/z von -Größe/2 bis +Größe/2
	var groesse := welt_m
	welt_groesse = groesse
	_texturen_einrichten(terrain)
	terrain.get("data").import_images([hoehe, steuer, farbe], Vector3(-groesse / 2.0, 0, -groesse / 2.0), 0.0, 1.0)
	terrain.set("show_colormap", farbkarte_anzeigen or steuer == null)
	# außerhalb der Insel keine Terrain3D-Grundfläche (sonst flackert sie mit dem Meer)
	terrain.get("material").set("world_background", 0)

	var meer: MeshInstance3D = get_node_or_null("Meer")
	if meer == null:
		meer = MeshInstance3D.new()
		meer.name = "Meer"
		add_child(meer)
		_besitzer(meer)
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(groesse * 3, groesse * 3)
	meer.mesh = ebene
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.32, 0.5, 0.85)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.roughness = 0.08
	mat.metallic_specular = 0.8
	meer.material_override = mat
	meer.visible = meer_anzeigen

	# Meeresboden außerhalb der 4 x 4 km auf Höhe des tiefsten Punkts -> keine sichtbare Kante unter Wasser
	var boden: MeshInstance3D = get_node_or_null("Meeresboden")
	if boden == null:
		boden = MeshInstance3D.new()
		boden.name = "Meeresboden"
		add_child(boden)
		_besitzer(boden)
	var bebene := PlaneMesh.new()
	bebene.size = Vector2(groesse * 3, groesse * 3)
	boden.mesh = bebene
	boden.position.y = float(meta["hoehe"]["min"]) + 0.3
	var bmat := StandardMaterial3D.new()
	bmat.albedo_color = Color(0.32, 0.3, 0.24)
	bmat.roughness = 1.0
	boden.material_override = bmat

	_marker_importieren()
	_seen_importieren(mat)
	if Engine.is_editor_hint():
		terrain.get("data").save_directory(datenordner)
	print("Weltimport: %d x %d Pixel, %.1f m/Pixel, Höhen %.1f … %.1f m" % [n, n, mpp, meta["hoehe"]["min"], meta["hoehe"]["max"]])


## Bodentexturen nach den Biom-Regeln (data/biome.json): Die Steuerkarte des Generators (uint32 je Pixel: Bits 27–31
## Grundtextur, 22–26 Überlagerung, 14–21 Überblendung) behält ihre weichen Übergänge, die Texturen werden aber über
## die Biome neu zugeordnet. Alte Weg-Pixel bekommen den Boden des Bioms darunter (es gibt keine Straßen mehr), und
## entlang der Flüsse wird ein Kiesbett eingetragen, das zum Ufer hin ausläuft.
func _steuerkarte_umbauen(sb: PackedByteArray, n: int, mpp: float, welt_m: float, meta: Dictionary) -> PackedByteArray:
	var start := Time.get_ticks_msec()
	var regeln := BiomRegeln.laden()
	var biome := FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["biome"]["datei"]))
	var raster: int = int(meta["raster"])
	var zelle: float = float(meta["zelle_m"])
	# Generator-Textur (= Generator-Biom) -> Textur des neuen Bioms (-1: unverändert lassen)
	var neu := PackedInt32Array()
	neu.resize(32)
	for i in 32:
		neu[i] = i
	for g in regeln["generator"]:
		var t: int = int(regeln["generator"][g]["textur"])
		if t >= 0:
			neu[int(g)] = t
	var werte := sb.to_int32_array()
	var weg := 0
	var geaendert := 0
	var schritt := float(raster) / float(n)
	for y in n:
		var zeile := y * n
		var biom_zeile := mini(int(y * schritt), raster - 1) * raster
		for x in n:
			var v := werte[zeile + x]
			var basis := (v >> 27) & 31
			var auf := (v >> 22) & 31
			var nb := neu[basis]
			var na := neu[auf]
			if basis == WEG_ID or auf == WEG_ID:
				var unter := neu[biome[biom_zeile + mini(int(x * schritt), raster - 1)]]
				if basis == WEG_ID:
					nb = unter
				if auf == WEG_ID:
					na = unter
				weg += 1
			if nb == basis and na == auf:
				continue
			werte[zeile + x] = (v & ~((31 << 27) | (31 << 22))) | (nb << 27) | (na << 22)
			geaendert += 1
	var kies := _flussbett(werte, n, mpp, welt_m)
	var seeboden := _seeboden(werte, n, meta)
	print("Weltimport: Böden nach Biom-Regeln, %d Pixel neu zugeordnet (%d alte Weg-Pixel), %d Pixel Kiesbett, %d Pixel Seeboden, %.1f s" % [
		geaendert, weg, kies, seeboden, (Time.get_ticks_msec() - start) / 1000.0])
	return werte.to_byte_array()


## Seeboden aus seen_<Raster>.u8: Kies statt Wiese oder Wald unter dem Wasser, am Rand mit Überblendung. Gibt die Pixelzahl zurück.
func _seeboden(werte: PackedInt32Array, n: int, meta: Dictionary) -> int:
	var kies_id := BiomRegeln.textur_id("kies")
	if meta.get("seen") == null or kies_id < 0:
		return 0
	var raster: int = int(meta["raster"])
	var maske := FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["seen"]["datei"]))
	if maske.size() != raster * raster:
		return 0
	# je See nur sein Rechteck durchgehen
	var boxen := {}
	for y in raster:
		for x in raster:
			var nr := maske[y * raster + x]
			if nr == 0:
				continue
			if not boxen.has(nr):
				boxen[nr] = Rect2i(x, y, 1, 1)
			else:
				boxen[nr] = (boxen[nr] as Rect2i).expand(Vector2i(x, y)).expand(Vector2i(x + 1, y + 1))
	var anzahl := 0
	var schritt := float(raster) / float(n)
	var erledigt := {}
	for nr in boxen:
		var r: Rect2i = boxen[nr]
		for y in range(maxi(0, int((r.position.y - 1) / schritt)), mini(n, int((r.end.y + 1) / schritt) + 1)):
			var fy := (y + 0.5) * schritt - 0.5
			var ry := clampi(int(round(fy)), 0, raster - 1)
			var y0 := clampi(int(floor(fy)), 0, raster - 2)
			for x in range(maxi(0, int((r.position.x - 1) / schritt)), mini(n, int((r.end.x + 1) / schritt) + 1)):
				var o := y * n + x
				if erledigt.has(o):
					continue
				var fx := (x + 0.5) * schritt - 0.5
				var rx := clampi(int(round(fx)), 0, raster - 1)
				# Anteil Seezellen in der 2x2-Umgebung -> weicher Rand
				var x0 := clampi(int(floor(fx)), 0, raster - 2)
				var teil := 0
				for k in [0, 1, raster, raster + 1]:
					if maske[y0 * raster + x0 + k] > 0:
						teil += 1
				if teil == 0 and maske[ry * raster + rx] == 0:
					continue
				erledigt[o] = true
				var v := werte[o]
				if teil >= 4:
					v = (v & ~((31 << 27) | (31 << 22) | (255 << 14))) | (kies_id << 27) | (kies_id << 22)
				else:
					v = (v & ~((31 << 22) | (255 << 14))) | (kies_id << 22) | ((teil * 60) << 14)
				werte[o] = v
				anzahl += 1
	return anzahl


## Kiesbett entlang der Flüsse aus fluesse.json: voller Kies bis 0,5 m über die Wasserbreite hinaus,
## danach läuft er auf 3 m zum Ufer hin aus (Überlagerung mit steigender Überblendung). Gibt die Pixelzahl zurück.
func _flussbett(werte: PackedInt32Array, n: int, mpp: float, welt_m: float) -> int:
	var pfad := daten_ordner.path_join("fluesse.json")
	var kies_id := BiomRegeln.textur_id("kies")
	if not FileAccess.file_exists(pfad) or kies_id < 0:
		return 0
	var anzahl := 0
	var halb := welt_m / 2.0
	for f in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var punkte: Array = f["punkte"]
		for i in range(1, punkte.size()):
			var a := Vector2(float(punkte[i - 1][0]) + halb, float(punkte[i - 1][2]) + halb) / mpp
			var b := Vector2(float(punkte[i][0]) + halb, float(punkte[i][2]) + halb) / mpp
			var breite := (float(punkte[i - 1][3]) + float(punkte[i][3])) / 2.0
			var innen := (breite / 2.0 + 0.5) / mpp
			var aussen := (breite / 2.0 + 3.0) / mpp
			var von := a.min(b) - Vector2(aussen, aussen)
			var bis := a.max(b) + Vector2(aussen, aussen)
			for y in range(maxi(0, int(von.y)), mini(n, int(bis.y) + 1)):
				for x in range(maxi(0, int(von.x)), mini(n, int(bis.x) + 1)):
					var p := Vector2(x + 0.5, y + 0.5)
					var d := Geometry2D.get_closest_point_to_segment(p, a, b).distance_to(p)
					if d >= aussen:
						continue
					var w := clampf((aussen - d) / (aussen - innen), 0.0, 1.0)
					var o := y * n + x
					var v := werte[o]
					var basis := (v >> 27) & 31
					if basis == kies_id:
						continue
					if w >= 1.0:
						v = (v & ~((31 << 27) | (31 << 22) | (255 << 14))) | (kies_id << 27) | (kies_id << 22)
					else:
						var blend := roundi(w * 255.0)
						if ((v >> 22) & 31) == kies_id:
							blend = maxi(blend, (v >> 14) & 255)
						v = (v & ~((31 << 22) | (255 << 14))) | (kies_id << 22) | (blend << 14)
					werte[o] = v
					anzahl += 1
	return anzahl


func _texturen_einrichten(terrain: Node3D) -> void:
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var assets = terrain.get("assets")
	if assets == null:
		assets = ClassDB.instantiate("Terrain3DAssets")
		terrain.set("assets", assets)
	var scans := ResourceLoader.exists(basis.path_join("texturen_scan/wiese_albedo_hoehe.png"))
	for id in BODEN.size():
		var name_: String = BODEN[id][0]
		var ordner := "texturen_scan" if scans else "texturen"
		if not ResourceLoader.exists(basis.path_join("%s/%s_albedo_hoehe.png" % [ordner, name_])):
			ordner = "texturen" # fehlt ein einzelner Scan (z. B. Kies), die eigene Textur nehmen
		var t = ClassDB.instantiate("Terrain3DTextureAsset")
		t.set("name", String(BODEN[id][0]).capitalize())
		t.set("albedo_texture", load(basis.path_join("%s/%s_albedo_hoehe.png" % [ordner, name_])))
		t.set("normal_texture", load(basis.path_join("%s/%s_normal_rauheit.png" % [ordner, name_])))
		var scan := ordner == "texturen_scan"
		t.set("uv_scale", 1.0 / float(BODEN[id][1 if scan else 2]))
		t.set("albedo_color", BODEN[id][3 if scan else 4])
		t.set("detiling_rotation", 0.3)
		t.set("detiling_shift", 0.2)
		# Terrain3D 1.0.x: set_texture · neuere Versionen: set_texture_asset
		if assets.has_method("set_texture_asset"):
			assets.call("set_texture_asset", id, t)
		else:
			assets.call("set_texture", id, t)
	assets.call("update_texture_list")
	# Weichere Übergänge zwischen den Böden (über die Höhe in den Texturen) und großflächige Farbschwankungen,
	# damit die Kacheln aus der Ferne nicht als Muster auffallen
	var mat = terrain.get("material")
	mat.call("set_shader_param", "blend_sharpness", 0.6)
	mat.call("set_shader_param", "enable_macro_variation", true)
	mat.call("set_shader_param", "macro_variation1", Color(0.94, 1.0, 0.9))
	mat.call("set_shader_param", "macro_variation2", Color(1.0, 0.97, 0.92))
	mat.call("set_shader_param", "macro_variation_slope", 0.4)
	mat.call("set_shader_param", "noise1_scale", 0.012)
	mat.call("set_shader_param", "noise2_scale", 0.05)


const MARKER_FARBEN := {"stadt": Color(0.91, 0.69, 0.29), "dorf": Color(0.9, 0.83, 0.54), "dungeon": Color(0.75, 0.31, 0.3),
	"mine": Color(0.6, 0.64, 0.69), "poi": Color(0.44, 0.72, 0.91), "feld": Color(0.85, 0.76, 0.35)}

## Marker aus marker.json als Knoten unter "Marker/<Typ>" anlegen.
## Jeder Marker ist ein Marker3D mit Metadaten (typ, name, radius bzw. art/breite/laenge) – darauf baust du Städte, Dungeons usw. auf.
func _marker_importieren() -> void:
	var pfad := daten_ordner.path_join("marker.json")
	if not FileAccess.file_exists(pfad):
		return
	var liste: Array = JSON.parse_string(FileAccess.get_file_as_string(pfad))
	var alt := get_node_or_null("Marker")
	if alt:
		remove_child(alt)
		alt.free()
	var wurzel := Node3D.new()
	wurzel.name = "Marker"
	add_child(wurzel)
	_besitzer(wurzel)
	var gruppen := {}
	for m in liste:
		var typ: String = m["typ"]
		if not gruppen.has(typ):
			var g := Node3D.new()
			g.name = typ.capitalize()
			wurzel.add_child(g)
			_besitzer(g)
			gruppen[typ] = g
		var mk := Marker3D.new()
		var name_: String = m.get("name", "")
		mk.name = name_.validate_node_name() if name_ != "" else "%s_%d" % [typ, gruppen[typ].get_child_count() + 1]
		mk.position = Vector3(m["x"], m["hoehe"], m["z"])
		for k in m.keys():
			mk.set_meta(k, m[k])
		mk.add_to_group("welt_marker", true)
		mk.add_to_group("marker_" + typ, true)
		gruppen[typ].add_child(mk)
		_besitzer(mk)
		_platzhalter(mk, m)


## Seen aus welt.json ("seen"): je See eine Wasserfläche auf Höhe seines Wasserspiegels unter "Seen".
## Die Fläche besteht aus den Seezellen aus seen_<Raster>.u8 plus einer Zelle Rand (die liegt unter dem Ufer).
## Ein Rechteck reichte früher über das Ufer hinaus und setzte tiefer liegendes Land daneben unter Wasser. Jede Fläche ist in der Gruppe "welt_seen" mit Metadaten (nr, wasserspiegel, flaeche_m2).
func _seen_importieren(wasser: Material = null) -> void:
	var alt := get_node_or_null("Seen")
	if alt:
		remove_child(alt)
		alt.free()
	var meta_pfad := daten_ordner.path_join("welt.json")
	if not FileAccess.file_exists(meta_pfad):
		return
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(meta_pfad))
	if meta.get("seen") == null:
		return
	var seen: Dictionary = meta["seen"]
	var raster: int = int(meta["raster"])
	var zelle: float = float(meta["zelle_m"])
	var maske := FileAccess.get_file_as_bytes(daten_ordner.path_join(seen["datei"]))
	if maske.size() != raster * raster:
		push_warning("Weltimport: Seen-Maske hat die falsche Größe, Seen werden übersprungen.")
		return
	var liste: Array = seen["liste"]
	# Seezellen um eine Zelle erweitern (je See für sich), damit das Wasser bis unter das Ufer reicht
	var flaeche := PackedByteArray()
	flaeche.resize(raster * raster)
	for y in raster:
		for x in raster:
			var nr := maske[y * raster + x]
			if nr == 0:
				continue
			for dy in range(-1, 2):
				for dx in range(-1, 2):
					var xx := x + dx
					var yy := y + dy
					if xx >= 0 and yy >= 0 and xx < raster and yy < raster and flaeche[yy * raster + xx] == 0:
						flaeche[yy * raster + xx] = nr
	if wasser == null:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.12, 0.34, 0.45, 0.85)
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.roughness = 0.05
		m.metallic_specular = 0.8
		wasser = m
	var wurzel := Node3D.new()
	wurzel.name = "Seen"
	add_child(wurzel)
	_besitzer(wurzel)
	var halb := raster * zelle / 2.0
	# je See: Zeilen zu Streifen zusammenfassen (ein Rechteck je zusammenhängendem Stück einer Zeile)
	var flaechen := {}
	var mitte := {}
	for s in liste:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		flaechen[int(s["nr"])] = st
		mitte[int(s["nr"])] = Vector3(float(s["x"]), float(s["wasserspiegel"]), float(s["z"]))
	for y in raster:
		var x := 0
		while x < raster:
			var nr := flaeche[y * raster + x]
			if nr == 0 or not flaechen.has(nr):
				x += 1
				continue
			var x1 := x
			while x1 + 1 < raster and flaeche[y * raster + x1 + 1] == nr:
				x1 += 1
			var st: SurfaceTool = flaechen[nr]
			var m: Vector3 = mitte[nr]
			var a := Vector3(x * zelle - halb, 0, y * zelle - halb) - Vector3(m.x, 0, m.z)
			var b := Vector3((x1 + 1) * zelle - halb, 0, (y + 1) * zelle - halb) - Vector3(m.x, 0, m.z)
			for e in [Vector3(a.x, 0, a.z), Vector3(b.x, 0, a.z), Vector3(b.x, 0, b.z), Vector3(a.x, 0, a.z), Vector3(b.x, 0, b.z), Vector3(a.x, 0, b.z)]:
				st.set_normal(Vector3.UP)
				st.set_uv(Vector2(e.x + m.x, e.z + m.z))
				st.add_vertex(e)
			x = x1 + 1
	for s in liste:
		var nr := int(s["nr"])
		var st: SurfaceTool = flaechen[nr]
		var mesh := st.commit()
		if mesh.get_surface_count() == 0:
			continue
		var see := MeshInstance3D.new()
		see.name = "See_%d" % nr
		see.mesh = mesh
		see.material_override = wasser
		see.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		see.position = mitte[nr]
		for k in s.keys():
			see.set_meta(k, s[k])
		see.add_to_group("welt_seen", true)
		wurzel.add_child(see)
		_besitzer(see)


## Flüsse aus fluesse.json: Wasserbänder auf Höhe des Wasserspiegels entlang der Flussläufe, zusammengefasst
## in 512-m-Kacheln unter "Fluesse". UV in Metern (x quer, y flussabwärts) für die Strömung im Wasser-Shader.
func _fluesse_importieren(wasser: Material = null) -> void:
	var alt := get_node_or_null("Fluesse")
	if alt:
		remove_child(alt)
		alt.free()
	var pfad := daten_ordner.path_join("fluesse.json")
	if not FileAccess.file_exists(pfad):
		return
	var kacheln := {} # Vector2i -> SurfaceTool
	for f in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var roh: Array = f["punkte"]
		if roh.size() < 2:
			continue
		# Punkte als Vector4 (x, Wasserspiegel, z, Breite), einmal nach Chaikin geglättet (das Raster macht Zickzack)
		var pts: Array[Vector4] = []
		for q in roh:
			pts.append(Vector4(q[0], q[1], q[2], q[3]))
		var glatt: Array[Vector4] = [pts[0]]
		for i in pts.size() - 1:
			glatt.append(pts[i].lerp(pts[i + 1], 0.25))
			glatt.append(pts[i].lerp(pts[i + 1], 0.75))
		glatt.append(pts[-1])
		var laenge := 0.0
		var links_alt := Vector3.ZERO
		var rechts_alt := Vector3.ZERO
		var v_alt := 0.0
		for i in glatt.size():
			var p := glatt[i]
			var vor := glatt[mini(i + 1, glatt.size() - 1)]
			var nach := glatt[maxi(i - 1, 0)]
			var richtung := Vector2(vor.x - nach.x, vor.z - nach.z).normalized()
			var quer := Vector3(-richtung.y, 0, richtung.x) * p.w / 2.0
			var mitte := Vector3(p.x, p.y + 0.05, p.z)
			var links := mitte - quer
			var rechts := mitte + quer
			if i > 0:
				laenge += Vector2(p.x - glatt[i - 1].x, p.z - glatt[i - 1].z).length()
				var k := Vector2i(floori(p.x / 512.0), floori(p.z / 512.0))
				if not kacheln.has(k):
					var neu := SurfaceTool.new()
					neu.begin(Mesh.PRIMITIVE_TRIANGLES)
					neu.set_normal(Vector3.UP)
					kacheln[k] = neu
				var st: SurfaceTool = kacheln[k]
				var b := p.w
				for e in [[links_alt, 0.0, v_alt], [rechts_alt, b, v_alt], [links, 0.0, laenge],
						[rechts_alt, b, v_alt], [rechts, b, laenge], [links, 0.0, laenge]]:
					st.set_normal(Vector3.UP)
					st.set_uv(Vector2(e[1], e[2]))
					st.add_vertex(e[0])
			links_alt = links
			rechts_alt = rechts
			v_alt = laenge
	var wurzel := Node3D.new()
	wurzel.name = "Fluesse"
	add_child(wurzel)
	_besitzer(wurzel)
	for k in kacheln:
		var mi := MeshInstance3D.new()
		mi.name = "Fluss_%d_%d" % [k.x, k.y]
		mi.mesh = (kacheln[k] as SurfaceTool).commit()
		mi.material_override = wasser
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		wurzel.add_child(mi)
		_besitzer(mi)


func _besitzer_rekursiv(n: Node) -> void:
	_besitzer(n)
	for c in n.get_children():
		_besitzer_rekursiv(c)


func _platzhalter(mk: Marker3D, m: Dictionary) -> void:
	var farbe: Color = MARKER_FARBEN.get(m["typ"], Color.WHITE)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = farbe
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	if m["typ"] == "feld":
		return # Felder bleiben unsichtbar, bis sie gebaut werden (die flachen Platten schwebten an Hängen)
	var vis := MeshInstance3D.new()
	vis.name = "Platzhalter"
	if m["typ"] == "feld":
		var ebene := PlaneMesh.new()
		ebene.size = Vector2(m["breite"], m["laenge"])
		vis.mesh = ebene
		mat.albedo_color = Color(0.89, 0.77, 0.36, 0.55) if m.get("art", "") == "weizen" else Color(0.47, 0.67, 0.27, 0.55)
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		vis.position.y = 0.3
		vis.rotation.y = -float(m["winkel"])
	else:
		var saeule := CylinderMesh.new()
		saeule.top_radius = 1.5
		saeule.bottom_radius = 1.5
		saeule.height = 40.0
		vis.mesh = saeule
		vis.position.y = 20.0
		var schild := Label3D.new()
		schild.name = "Name"
		schild.text = "%s\n%s" % [m.get("name", ""), String(m["typ"]).capitalize()]
		schild.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		schild.font_size = 160
		schild.pixel_size = 0.05
		schild.position.y = 46.0
		schild.modulate = farbe
		schild.outline_size = 24
		schild.no_depth_test = true
		mk.add_child(schild)
		_besitzer(schild)
		schild.visible = marker_platzhalter
	vis.material_override = mat
	mk.add_child(vis)
	_besitzer(vis)
	vis.visible = marker_platzhalter


## Geländehöhe in Metern an einer Weltposition (x/z), direkt aus den importierten Höhendaten.
## Praktisch zum Platzieren von Spielern, Ressourcen usw. Lädt die Höhendaten beim ersten Aufruf nach.
func hoehe_bei(pos: Vector3) -> float:
	if _hoehe_bild == null:
		_hoehe_laden()
	if _hoehe_bild == null:
		return 0.0
	var n := _hoehe_bild.get_width()
	var x := clampi(int(pos.x / _mpp + n / 2.0), 0, n - 1)
	var y := clampi(int(pos.z / _mpp + n / 2.0), 0, n - 1)
	return _hoehe_bild.get_pixel(x, y).r


func _hoehe_laden() -> void:
	var meta_pfad := daten_ordner.path_join("welt.json")
	if not FileAccess.file_exists(meta_pfad):
		return
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(meta_pfad))
	var n: int = int(meta["aufloesung"])
	var bytes := FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["hoehe"]["datei"]))
	if bytes.size() == n * n * 4:
		_hoehe_bild = Image.create_from_data(n, n, false, Image.FORMAT_RF, bytes)
		_mpp = float(meta["meter_pro_pixel"])


func _besitzer(knoten: Node) -> void:
	# damit neue Knoten in der Szene gespeichert werden
	if Engine.is_editor_hint() and get_tree() and get_tree().edited_scene_root:
		knoten.owner = get_tree().edited_scene_root
