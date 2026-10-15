extends Node3D
## 3D-Vorschau der Biome ohne Terrain3D: Gelände aus dem Weltgenerator-Export (res://welt_daten) mit den
## Bodentexturen nach den Biom-Regeln, dazu Natur, Gras, Flüsse und Seen wie im Spiel.
## Aufruf (mit Fenster bzw. xvfb): Godot --path godot --rendering-method gl_compatibility res://tests/biom_3d.tscn
##   -- --biom wald|wiese|fluss|strand|berg|moor [--luft] [--blick <grad>] [--objekt <Knotenname>, z. B. Totbaum]
## Mit --write-movie <ordner>/f.png --fixed-fps 10 entstehen Bilder; beendet sich nach 3 s.

const ORDNER := "res://welt_daten"
const NaturScript := preload("res://scripts/natur.gd")
const GrasScript := preload("res://scripts/gras.gd")
const Wasser := preload("res://scripts/wasser.gd")
const ErsatzTerrain := preload("res://tests/ersatz_terrain.gd")
const GROESSE := 260.0   # Kantenlänge des Vorschau-Geländes in Metern
const RASTER := 1.0

var terrain
var natur
var kamera: Camera3D
var _zeit := 0.0


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var gesucht := _arg(args, "--biom", "wald")
	terrain = ErsatzTerrain.new()
	terrain.laden(ORDNER)
	var ziel := Node3D.new()
	add_child(ziel)
	natur = NaturScript.new()
	natur.setup(self, ziel, ORDNER)
	add_child(natur)
	var ort := _ort_finden(gesucht)
	var h: float = terrain.get_height(Vector3(ort.x, 0, ort.y))
	ziel.position = Vector3(ort.x, h, ort.y)
	print("BIOM3D %s bei %s, Höhe %.1f m" % [gesucht, ort.round(), h])

	_umgebung()
	_gelaende(ort)
	var welt = load("res://assets/welt/welt_import.gd").new()
	welt.daten_ordner = ORDNER
	add_child(welt)
	welt._fluesse_importieren(Wasser.material("fluss"))
	welt._seen_importieren(Wasser.material("see"))
	var meer := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(6000, 6000)
	meer.mesh = ebene
	meer.material_override = Wasser.material("meer")
	add_child(meer)
	natur.sofort_laden()
	var gras = GrasScript.new()
	gras.setup(natur, ziel)
	add_child(gras)

	kamera = Camera3D.new()
	kamera.far = 3000.0
	add_child(kamera)
	var blick := deg_to_rad(float(_arg(args, "--blick", "30")))
	var richtung := Vector3(sin(blick), 0, -cos(blick))
	if args.has("--luft"):
		kamera.position = ziel.position - richtung * 70.0 + Vector3(0, 45, 0)
		kamera.look_at(ziel.position + richtung * 25.0)
	else:
		var p := ziel.position - richtung * 6.0
		p.y = terrain.get_height(p) + 1.8
		kamera.position = p
		kamera.look_at(p + richtung * 10.0 + Vector3(0, -1.2, 0))
	var objekt := _arg(args, "--objekt", "")
	if objekt != "":
		# Nächstes Objekt mit diesem Knotennamen aus der Nähe ansehen
		var bestes: Node3D = null
		for k in natur.find_children(objekt + "*", "Node3D", true, false):
			if bestes == null or k.global_position.distance_to(ziel.position) < bestes.global_position.distance_to(ziel.position):
				bestes = k
		if bestes:
			var p := bestes.global_position - richtung * 7.0
			p.y = terrain.get_height(p) + 2.0
			kamera.position = p
			kamera.look_at(bestes.global_position + Vector3(0, 1.5, 0))
	kamera.current = true


func _process(delta: float) -> void:
	_zeit += delta
	if _zeit > 3.0:
		get_tree().quit()


func _arg(args: PackedStringArray, name_: String, standard: String) -> String:
	var i := args.find(name_)
	return args[i + 1] if i >= 0 and i + 1 < args.size() else standard


## Stelle mitten im gesuchten Biom (12 m ringsum gleiches Biom), vom Startdorf aus gesucht
func _ort_finden(gesucht: String) -> Vector2:
	var start := Vector2.ZERO
	for m in JSON.parse_string(FileAccess.get_file_as_string(ORDNER.path_join("marker.json"))):
		if m.get("name", "") == "Startdorf":
			start = Vector2(float(m["x"]), float(m["z"]))
	var rand := 3.0 if gesucht == "fluss" else 14.0
	for r in range(150, 3000, 15):
		for i in 36:
			var p := start + Vector2.from_angle(TAU * i / 36.0) * r
			var drin: bool = natur.biom_name(p.x, p.y) == gesucht
			for j in 8:
				var q := p + Vector2.from_angle(TAU * j / 8.0) * rand
				drin = drin and natur.biom_name(q.x, q.y) == gesucht
			if drin and terrain.get_height(Vector3(p.x, 0, p.y)) > 1.0:
				return p
	return start


func _umgebung() -> void:
	var licht := DirectionalLight3D.new()
	licht.rotation = Vector3(deg_to_rad(-42), deg_to_rad(35), 0)
	licht.light_energy = 1.25
	licht.shadow_enabled = true
	licht.directional_shadow_max_distance = 120.0
	add_child(licht)
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = Sky.new()
	env.sky.sky_material = ProceduralSkyMaterial.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_density = 0.002
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


## Gelände-Netz (GROESSE × GROESSE) mit Texturgewichten aus der umgebauten Steuerkarte
func _gelaende(mitte: Vector2) -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ORDNER.path_join("welt.json")))
	var n: int = int(meta["aufloesung"])
	var mpp: float = float(meta["meter_pro_pixel"])
	var welt_m: float = float(meta["welt_m"])
	var importer = load("res://assets/welt/welt_import.gd").new()
	importer.daten_ordner = ORDNER
	var sb := FileAccess.get_file_as_bytes(ORDNER.path_join(meta["steuerung"]["datei"]))
	var werte: PackedInt32Array = importer._steuerkarte_umbauen(sb, n, mpp, welt_m, meta).to_int32_array()
	importer.free()
	var schritte := int(GROESSE / RASTER)
	var x0 := mitte.x - GROESSE / 2.0
	var z0 := mitte.y - GROESSE / 2.0
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var punkte: Array = []
	for j in schritte + 1:
		for i in schritte + 1:
			var x := x0 + i * RASTER
			var z := z0 + j * RASTER
			var px := clampi(int((x + welt_m / 2.0) / mpp), 0, n - 1)
			var pz := clampi(int((z + welt_m / 2.0) / mpp), 0, n - 1)
			var v := werte[pz * n + px]
			var w := PackedFloat32Array()
			w.resize(9)
			var bl := float((v >> 14) & 255) / 255.0
			w[(v >> 27) & 31] += 1.0 - bl
			w[(v >> 22) & 31] += bl
			punkte.append([Vector3(x, terrain.get_height(Vector3(x, 0, z)), z), w])
	for j in schritte:
		for i in schritte:
			var a := j * (schritte + 1) + i
			for k in [a, a + 1, a + schritte + 1, a + 1, a + schritte + 2, a + schritte + 1]:
				var e: Array = punkte[k]
				var w: PackedFloat32Array = e[1]
				st.set_color(Color(w[0], w[1], w[2], w[3]))
				st.set_uv(Vector2(w[4], w[5]))
				st.set_uv2(Vector2(w[6], w[7]))
				st.add_vertex(e[0])
	st.generate_normals()
	st.generate_tangents()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var mat := ShaderMaterial.new()
	mat.shader = load("res://tests/biom_3d.gdshader")
	var farben: Array[Texture2D] = []
	var normalen: Array[Texture2D] = []
	var groessen := PackedFloat32Array()
	var basis := "res://assets/welt/"
	var WI = load("res://assets/welt/welt_import.gd")
	for t in WI.BODEN:
		var ordner := "texturen_scan" if ResourceLoader.exists(basis + "texturen_scan/%s_albedo_hoehe.png" % t[0]) else "texturen"
		farben.append(load(basis + "%s/%s_albedo_hoehe.png" % [ordner, t[0]]))
		normalen.append(load(basis + "%s/%s_normal_rauheit.png" % [ordner, t[0]]))
		groessen.append(float(t[1 if ordner == "texturen_scan" else 2]))
	mat.set_shader_parameter("farbe", farben)
	mat.set_shader_parameter("normale", normalen)
	mat.set_shader_parameter("groesse", groessen)
	mi.material_override = mat
	add_child(mi)
