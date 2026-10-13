extends Node3D
## Gras rund um den Spieler: Büschel als MultiMesh in 16-m-Kacheln bis RADIUS (ferner trägt die Wiesentextur).
## Dichte und Farbton nach Biom (Wiese satt grün, Steppe gelblich, Wald licht), nicht auf Wegen, in Seen,
## auf Fels/Schnee und an Steilhängen. Nutzt die Biom- und Sperrdaten von scripts/natur.gd.

const GrasShader := preload("res://scripts/gras.gdshader")

const KACHEL := 16.0
const RADIUS := 35.0
const ABSTAND := 0.55            # Raster der Büschel in Metern (bei voller Dichte)
const BUDGET_US := 3000          # Zeit je Frame für neue Kacheln
const NAH := 15.0                # bis hier volle Dichte, dahinter halb so viele (etwas größere) Büschel

## Dichte (0..1) und Farbton je Biom: Strand, Wiese, Laubwald, Nadelwald, Sumpf, Steppe, Fels, Schnee
const DICHTE := [0.06, 1.0, 0.35, 0.15, 0.7, 0.8, 0.04, 0.0]
const FARBE := [Color(0.62, 0.62, 0.38), Color(0.4, 0.58, 0.2), Color(0.34, 0.48, 0.18), Color(0.32, 0.42, 0.2),
	Color(0.38, 0.48, 0.22), Color(0.72, 0.64, 0.34), Color(0.45, 0.5, 0.3), Color(0.6, 0.6, 0.6)]

var natur                         # scripts/natur.gd
var ziel: Node3D
var frei: Array = []              # zusätzliche grasfreie Kreise [Vector2 Mitte, Radius] (Dorfplatz, Lager)
var _kacheln := {}                # Vector2i -> MultiMeshInstance3D
var _offen: Array = []
var _mitte := Vector2(INF, INF)
var _material := ShaderMaterial.new()
var _mesh: ArrayMesh


func setup(natur_node, spieler: Node3D) -> void:
	natur = natur_node
	ziel = spieler
	_material.shader = GrasShader
	_material.set_shader_parameter("radius", RADIUS)
	_mesh = _bueschel_mesh()


func _process(_delta: float) -> void:
	if ziel == null:
		return
	var p := Vector2(ziel.global_position.x, ziel.global_position.z)
	_material.set_shader_parameter("mitte", p)
	if p.distance_to(_mitte) > 4.0:
		_aktualisieren(p)
	var ende := Time.get_ticks_usec() + BUDGET_US
	while not _offen.is_empty() and Time.get_ticks_usec() < ende:
		var k: Vector2i = _offen.pop_front()
		var d := _kachel_abstand(k, _mitte)
		if d >= RADIUS:
			continue
		var voll := d < NAH
		if _kacheln.has(k):
			if _kacheln[k].get_meta("voll") == voll:
				continue
			_kacheln[k].queue_free() # Detailstufe hat sich geändert
		_kacheln[k] = _kachel_bauen(k, voll)


func _kachel_abstand(k: Vector2i, p: Vector2) -> float:
	var r := Rect2(Vector2(k) * KACHEL, Vector2.ONE * KACHEL)
	return p.distance_to(p.clamp(r.position, r.end))


func _aktualisieren(p: Vector2) -> void:
	_mitte = p
	var n := int(ceil(RADIUS / KACHEL)) + 1
	var m := Vector2i(floori(p.x / KACHEL), floori(p.y / KACHEL))
	var neu: Array = []
	for dz in range(-n, n + 1):
		for dx in range(-n, n + 1):
			var k := m + Vector2i(dx, dz)
			var d := _kachel_abstand(k, p)
			if d < RADIUS and (not _kacheln.has(k) or _kacheln[k].get_meta("voll") != (d < NAH)):
				neu.append([d, k])
	neu.sort_custom(func(a, b): return a[0] < b[0])
	_offen = neu.map(func(e): return e[1])
	for k in _kacheln.keys():
		if _kachel_abstand(k, p) > RADIUS + 8.0:
			_kacheln[k].queue_free()
			_kacheln.erase(k)


func _kachel_bauen(k: Vector2i, voll: bool) -> Node3D:
	var x0 := k.x * KACHEL
	var z0 := k.y * KACHEL
	# Höhen auf 2-m-Raster vorab holen und dazwischen interpolieren (spart viele Terrain-Abfragen)
	var hs := PackedFloat32Array()
	hs.resize(81)
	for j in 9:
		for i in 9:
			hs[j * 9 + i] = natur._hoehe(x0 + i * 2.0, z0 + j * 2.0)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(k.x, k.y, 77))
	# Wege/Felder/freie Kreise nur prüfen, wenn die Kachel überhaupt welche berührt
	var pruefen: bool = natur.sperr.has(Vector2i(floori(x0 / 32.0), floori(z0 / 32.0)))
	for f in frei:
		if Rect2(x0, z0, KACHEL, KACHEL).grow(f[1]).has_point(f[0]):
			pruefen = true
	var transforms: Array[Transform3D] = []
	var farben: Array[Color] = []
	var n := int(KACHEL / ABSTAND)
	for gz in n:
		for gx in n:
			var lx := (gx + rng.randf()) * ABSTAND
			var lz := (gz + rng.randf()) * ABSTAND
			var r := rng.randf()
			var dreh := rng.randf() * TAU
			var groesse := rng.randf_range(0.7, 1.3)
			var x := x0 + lx
			var z := z0 + lz
			var b: int = natur._biom(x, z)
			if b < 0 or r > DICHTE[b] * (1.0 if voll else 0.45):
				continue
			if not voll:
				groesse *= 1.3
			# Höhe bilinear, Steigung aus dem Raster
			var fi := lx / 2.0
			var fj := lz / 2.0
			var i := mini(int(fi), 7)
			var j := mini(int(fj), 7)
			var tx := fi - i
			var tz := fj - j
			var h00 := hs[j * 9 + i]
			var h10 := hs[j * 9 + i + 1]
			var h01 := hs[(j + 1) * 9 + i]
			var h11 := hs[(j + 1) * 9 + i + 1]
			var h := lerpf(lerpf(h00, h10, tx), lerpf(h01, h11, tx), tz)
			if h < 0.4 or maxf(absf(h10 - h00), absf(h01 - h00)) > 1.4:
				continue
			if pruefen and (natur._auf_weg(x, z) or natur._im_feld(x, z) or _im_freien_kreis(x, z)):
				continue
			var basis := Basis(Vector3.UP, dreh).scaled(Vector3(groesse, groesse * (1.1 if b == WIESE_ID else 0.9), groesse))
			transforms.append(Transform3D(basis, Vector3(x, h - 0.03, z)))
			var c: Color = FARBE[b]
			farben.append(c.lerp(Color(c.r * 1.25, c.g * 1.15, c.b * 0.9), rng.randf()))
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true # Farbton je Büschel (im Shader INSTANCE_CUSTOM)
	mm.mesh = _mesh
	mm.instance_count = transforms.size()
	for i in transforms.size():
		mm.set_instance_transform(i, transforms[i])
		mm.set_instance_custom_data(i, farben[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = _material
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.set_meta("voll", voll)
	add_child(mmi)
	return mmi

const WIESE_ID := 1


func _im_freien_kreis(x: float, z: float) -> bool:
	for f in frei:
		if Vector2(x, z).distance_to(f[0]) < f[1]:
			return true
	return false


## Büschel aus 10 schmalen, leicht gebogenen Halmen (UV.y = Höhe im Halm)
func _bueschel_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 12345
	for b in 10:
		var a := rng.randf() * TAU
		var fuss := Vector3(cos(a), 0, sin(a)) * rng.randf_range(0.0, 0.2)
		var neigung := Vector3(cos(a), 0, sin(a)) * rng.randf_range(0.04, 0.16)
		var hoehe := rng.randf_range(0.22, 0.5)
		var breite := rng.randf_range(0.016, 0.028)
		var quer := Vector3(-sin(a + 1.2), 0, cos(a + 1.2)) * breite
		# zwei Segmente: unten breit, oben spitz
		var p0 := fuss
		var p1 := fuss + neigung * 0.35 + Vector3(0, hoehe * 0.55, 0)
		var p2 := fuss + neigung + Vector3(0, hoehe, 0)
		var v := [p0 - quer, p0 + quer, p1 - quer * 0.6, p1 + quer * 0.6, p2]
		var uv := [0.0, 0.0, 0.55, 0.55, 1.0]
		for tri in [[0, 1, 2], [1, 3, 2], [2, 3, 4]]:
			for idx in tri:
				st.set_uv(Vector2(0.5, uv[idx]))
				st.set_color(Color.WHITE)
				st.add_vertex(v[idx])
	st.generate_normals()
	return st.commit()
