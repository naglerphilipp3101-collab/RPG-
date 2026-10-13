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

## Kachelgröße der Bodentexturen in Metern (Biom-Reihenfolge wie im Generator)
## dazu ein Farbton, mit dem die Textur im Spiel multipliziert wird (Wiese gedämpfter, Waldböden etwas grüner)
const BODEN := [
	["sand", 4.0, Color(1.0, 0.98, 0.95)], ["wiese", 3.0, Color(0.6, 0.64, 0.82)], ["laubboden", 3.0, Color(0.8, 0.88, 0.76)],
	["nadelboden", 3.0, Color(0.9, 0.95, 0.85)], ["sumpf", 4.0, Color.WHITE], ["steppe", 3.0, Color(0.92, 0.9, 0.88)],
	["fels", 8.0, Color.WHITE], ["schnee", 6.0, Color.WHITE], ["weg", 3.0, Color.WHITE],
]

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
	_wege_importieren()
	_seen_importieren(mat)
	if Engine.is_editor_hint():
		terrain.get("data").save_directory(datenordner)
	print("Weltimport: %d x %d Pixel, %.1f m/Pixel, Höhen %.1f … %.1f m" % [n, n, mpp, meta["hoehe"]["min"], meta["hoehe"]["max"]])


func _texturen_einrichten(terrain: Node3D) -> void:
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var assets = terrain.get("assets")
	if assets == null:
		assets = ClassDB.instantiate("Terrain3DAssets")
		terrain.set("assets", assets)
	for id in BODEN.size():
		var name_: String = BODEN[id][0]
		var t = ClassDB.instantiate("Terrain3DTextureAsset")
		t.set("name", name_.capitalize())
		t.set("albedo_texture", load(basis.path_join("texturen/%s_albedo_hoehe.png" % name_)))
		t.set("normal_texture", load(basis.path_join("texturen/%s_normal_rauheit.png" % name_)))
		t.set("uv_scale", 1.0 / BODEN[id][1])
		t.set("albedo_color", BODEN[id][2])
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
	mat.call("set_shader_param", "macro_variation1", Color(1.0, 0.94, 0.86))
	mat.call("set_shader_param", "macro_variation2", Color(0.86, 0.96, 0.88))
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


## Wege aus wege.json: je Strecke ein Path3D (für NPC-Routen, Wagen, Wegweiser …) unter "Wege/Strassen" bzw. "Wege/Wege",
## Brücken als einfache Holzbrücken-Modelle unter "Wege/Bruecken". Das Gelände selbst ist beim Export schon eingeebnet.
func _wege_importieren() -> void:
	var pfad := daten_ordner.path_join("wege.json")
	var alt := get_node_or_null("Wege")
	if alt:
		remove_child(alt)
		alt.free()
	if not FileAccess.file_exists(pfad):
		return
	var liste: Array = JSON.parse_string(FileAccess.get_file_as_string(pfad))
	var wurzel := Node3D.new()
	wurzel.name = "Wege"
	add_child(wurzel)
	_besitzer(wurzel)
	var gruppen := {}
	for name_ in ["Strassen", "Wege", "Bruecken"]:
		var g := Node3D.new()
		g.name = name_
		wurzel.add_child(g)
		_besitzer(g)
		gruppen[name_] = g
	var nr := 0
	var gebaut: Array[Vector3] = []   # Brückenmitten – gemeinsam genutzte Brücken nur einmal bauen
	for w in liste:
		nr += 1
		var typ: String = w["typ"]
		var punkte: Array = w["punkte"]
		var br: Array = w["bruecke"]
		var pf := Path3D.new()
		pf.name = "%s_%d" % [typ.capitalize(), nr]
		pf.curve = Curve3D.new()
		for q in punkte:
			pf.curve.add_point(Vector3(q[0], q[1] + 0.1, q[2]))
		pf.set_meta("typ", typ)
		pf.set_meta("breite", w["breite"])
		pf.add_to_group("welt_wege", true)
		gruppen["Strassen" if typ == "strasse" else "Wege"].add_child(pf)
		_besitzer(pf)
		# zusammenhängende Brückenabschnitte zu je einem Modell
		var k := 1
		while k < punkte.size():
			if int(br[k]) == 1:
				var e := k
				while e + 1 < punkte.size() and int(br[e + 1]) == 1:
					e += 1
				var ab := punkte.slice(k - 1, e + 1)
				var m := (Vector3(ab[0][0], 0, ab[0][2]) + Vector3(ab[-1][0], 0, ab[-1][2])) / 2.0
				var doppelt := false
				for g in gebaut:
					if g.distance_to(m) < 8.0:
						doppelt = true
				if not doppelt:
					gebaut.append(m)
					var bruecke := _bruecke_bauen(ab, float(w["breite"]))
					bruecke.name = "Bruecke_%d" % gebaut.size()
					gruppen["Bruecken"].add_child(bruecke)
					_besitzer_rekursiv(bruecke)
				k = e + 1
			else:
				k += 1


## Seen aus welt.json ("seen"): je See eine Wasserfläche auf Höhe seines Wasserspiegels unter "Seen".
## Die Fläche deckt das Rechteck der Seezellen aus seen_<Raster>.u8 ab; das Ufer ringsum liegt höher, deshalb
## ist das Wasser nur im See zu sehen. Jede Fläche ist in der Gruppe "welt_seen" mit Metadaten (nr, wasserspiegel, flaeche_m2).
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
	# Rechteck je See (in Zellen): [min_x, min_y, max_x, max_y]
	var rechteck := {}
	for s in liste:
		rechteck[int(s["nr"])] = [raster, raster, -1, -1]
	for y in raster:
		var zeile := y * raster
		for x in raster:
			var nr := maske[zeile + x]
			if nr == 0 or not rechteck.has(nr):
				continue
			var r: Array = rechteck[nr]
			r[0] = mini(r[0], x); r[1] = mini(r[1], y); r[2] = maxi(r[2], x); r[3] = maxi(r[3], y)
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
	for s in liste:
		var r: Array = rechteck[int(s["nr"])]
		if r[2] < 0:
			continue
		var ebene := PlaneMesh.new()
		ebene.size = Vector2((r[2] - r[0] + 3) * zelle, (r[3] - r[1] + 3) * zelle)
		var see := MeshInstance3D.new()
		see.name = "See_%d" % int(s["nr"])
		see.mesh = ebene
		see.material_override = wasser
		see.position = Vector3((r[0] + r[2] + 1) / 2.0 * zelle - halb, float(s["wasserspiegel"]), (r[1] + r[3] + 1) / 2.0 * zelle - halb)
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


## Einfache Holzbrücke: Fahrbahn aus Planken, Geländer, Stützpfeiler bis zum Boden
func _bruecke_bauen(punkte: Array, breite: float) -> Node3D:
	var a := Vector3(punkte[0][0], punkte[0][1], punkte[0][2])
	var b := Vector3(punkte[-1][0], punkte[-1][1], punkte[-1][2])
	var mitte := (a + b) / 2.0
	var richtung := b - a
	var laenge := Vector2(richtung.x, richtung.z).length() + 6.0   # 3 m Auflage je Seite
	var knoten := StaticBody3D.new()
	knoten.position = mitte
	knoten.rotation.y = atan2(-richtung.z, richtung.x)
	var neigung := atan2(richtung.y, Vector2(richtung.x, richtung.z).length())
	var holz := StandardMaterial3D.new()
	holz.albedo_color = Color(0.42, 0.29, 0.18)
	holz.roughness = 0.9
	var dunkel := StandardMaterial3D.new()
	dunkel.albedo_color = Color(0.3, 0.2, 0.12)
	dunkel.roughness = 0.9
	var b_breite := breite + 1.0
	var deck := Node3D.new()
	deck.rotation.z = neigung
	knoten.add_child(deck)
	# Fahrbahn
	_kiste(deck, Vector3(laenge, 0.35, b_breite), Vector3(0, -0.05, 0), holz)
	# Querbalken sichtbar unter der Fahrbahn
	var x := -laenge / 2.0 + 0.6
	while x < laenge / 2.0:
		_kiste(deck, Vector3(0.3, 0.3, b_breite + 0.4), Vector3(x, -0.35, 0), dunkel)
		x += 1.6
	# Geländer
	for seite in [-1.0, 1.0]:
		_kiste(deck, Vector3(laenge, 0.15, 0.15), Vector3(0, 1.0, seite * b_breite / 2.0), holz)
		x = -laenge / 2.0 + 0.3
		while x <= laenge / 2.0:
			_kiste(deck, Vector3(0.2, 1.1, 0.2), Vector3(x, 0.5, seite * b_breite / 2.0), dunkel)
			x += 2.5
	# Stützpfeiler alle ~8 m bis zum Boden
	var anzahl := int(laenge / 8.0)
	for i in range(1, anzahl + 1):
		var t := float(i) / float(anzahl + 1)
		var welt_pos := a.lerp(b, t)
		var boden := hoehe_bei(welt_pos)
		var h := welt_pos.y - 0.4 - boden + 1.0
		if h < 1.0:
			continue
		var lokal_x := (t - 0.5) * (laenge - 6.0)
		for seite in [-1.0, 1.0]:
			var p := MeshInstance3D.new()
			var zyl := CylinderMesh.new()
			zyl.top_radius = 0.22
			zyl.bottom_radius = 0.28
			zyl.height = h
			p.mesh = zyl
			p.material_override = dunkel
			p.position = Vector3(lokal_x, -0.4 - h / 2.0 + (welt_pos.y - mitte.y), seite * (b_breite / 2.0 - 0.3))
			knoten.add_child(p)
	# Kollision: Fahrbahn
	var form := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(laenge, 0.4, b_breite)
	form.shape = box
	form.rotation.z = neigung
	knoten.add_child(form)
	return knoten


func _kiste(eltern: Node3D, groesse: Vector3, pos: Vector3, mat: Material) -> void:
	var m := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = groesse
	m.mesh = box
	m.material_override = mat
	m.position = pos
	eltern.add_child(m)


func _besitzer_rekursiv(n: Node) -> void:
	_besitzer(n)
	for c in n.get_children():
		_besitzer_rekursiv(c)


func _platzhalter(mk: Marker3D, m: Dictionary) -> void:
	var farbe: Color = MARKER_FARBEN.get(m["typ"], Color.WHITE)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = farbe
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
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
