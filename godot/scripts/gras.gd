extends Node3D
## Bodenbewuchs rund um den Spieler: Gras, Farne, Kräuter/kleine Sträucher und Blumen als MultiMeshes in
## 16-m-Kacheln bis RADIUS (ferner trägt die Bodentextur). Mischung, Dichte und Farbton nach Biom:
## im Wald vor allem Farne und Kräuter, auf Wiesen Gras mit Blumenflecken, in der Steppe trockenes Gras.
## Nicht auf Wegen, in Feldern, Seen und Flüssen, auf Fels/Schnee und an Steilhängen. Nutzt die Daten von scripts/natur.gd.

const GrasShader := preload("res://scripts/gras.gdshader")

const KACHEL := 16.0
const RADIUS := 35.0
const ABSTAND := 0.55            # Raster der Stellen in Metern (bei voller Dichte)
const BUDGET_US := 3000          # Zeit je Frame für neue Kacheln
const NAH := 15.0                # bis hier volle Dichte, dahinter halb so viel (etwas größer)

enum { GRAS, FARN, KRAUT, BLUME }
## Wahrscheinlichkeit je Stelle und Art, je Biom: Strand, Wiese, Laubwald, Nadelwald, Sumpf, Steppe, Fels, Schnee
const ANTEIL := [
	[0.06, 0.8, 0.32, 0.18, 0.6, 0.8, 0.04, 0.0],    # Gras
	[0.0, 0.004, 0.1, 0.13, 0.06, 0.0, 0.01, 0.0],   # Farn
	[0.01, 0.05, 0.2, 0.12, 0.12, 0.03, 0.02, 0.0],  # Kraut
	[0.0, 0.07, 0.05, 0.015, 0.04, 0.02, 0.0, 0.0],  # Blume (in Flecken gehäuft)
]
## Blattfarbe je Biom (Gras) und Grundton für Farn/Kraut
const FARBE := [Color(0.62, 0.62, 0.38), Color(0.4, 0.58, 0.2), Color(0.34, 0.48, 0.18), Color(0.32, 0.42, 0.2),
	Color(0.38, 0.48, 0.22), Color(0.72, 0.64, 0.34), Color(0.45, 0.5, 0.3), Color(0.6, 0.6, 0.6)]
const FARN_FARBE := Color(0.26, 0.42, 0.16)
const KRAUT_FARBE := Color(0.3, 0.44, 0.2)

var natur                         # scripts/natur.gd
var ziel: Node3D
var frei: Array = []              # zusätzliche freie Kreise [Vector2 Mitte, Radius] (Dorfplatz, Lager)
var _kacheln := {}                # Vector2i -> Node3D (je Art ein MultiMeshInstance3D)
var _offen: Array = []
var _mitte := Vector2(INF, INF)
var _material := ShaderMaterial.new()
var _meshes: Array = []


func setup(natur_node, spieler: Node3D) -> void:
	natur = natur_node
	ziel = spieler
	_material.shader = GrasShader
	_material.set_shader_parameter("radius", RADIUS)
	_meshes = [_gras_mesh(), _farn_mesh(), _kraut_mesh(), _blumen_mesh()]


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
	# Wege/Flüsse/Felder/freie Kreise nur prüfen, wenn die Kachel überhaupt welche berührt
	var pruefen: bool = natur.sperr.has(Vector2i(floori(x0 / 32.0), floori(z0 / 32.0)))
	for f in frei:
		if Rect2(x0, z0, KACHEL, KACHEL).grow(f[1]).has_point(f[0]):
			pruefen = true
	var listen: Array = [[], [], [], []]   # je Art [Transform3D, Color]
	var faktor := 1.0 if voll else 0.45
	var n := int(KACHEL / ABSTAND)
	for gz in n:
		for gx in n:
			var lx := (gx + rng.randf()) * ABSTAND
			var lz := (gz + rng.randf()) * ABSTAND
			var r := rng.randf()
			var dreh := rng.randf() * TAU
			var groesse := rng.randf_range(0.7, 1.3)
			var farbwahl := rng.randf()
			var x := x0 + lx
			var z := z0 + lz
			var b: int = natur._biom(x, z)
			if b < 0:
				continue
			# Art auswählen; Blumen wachsen in Flecken (Rauschen)
			var flecken: float = clampf(natur.rauschen.get_noise_2d(x * 4.0, z * 4.0) * 2.5 + 0.4, 0.1, 2.5)
			var art := -1
			var summe := 0.0
			for a in 4:
				summe += ANTEIL[a][b] * faktor * (flecken if a == BLUME else 1.0)
				if r < summe:
					art = a
					break
			if art < 0:
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
			var c: Color
			match art:
				GRAS:
					c = FARBE[b]
				FARN:
					c = FARN_FARBE
				_:
					c = KRAUT_FARBE.lerp(FARBE[b], 0.4)
			c = c.lerp(Color(c.r * 1.25, c.g * 1.15, c.b * 0.9), rng.randf())
			# Blütenfarbe im Alpha: meist lila, sonst weiß, gelb, rosa
			c.a = 0.0 if farbwahl < 0.45 else (0.33 if farbwahl < 0.7 else (0.66 if farbwahl < 0.88 else 1.0))
			listen[art].append([Transform3D(basis, Vector3(x, h - 0.03, z)), c])
	var knoten := Node3D.new()
	knoten.set_meta("voll", voll)
	for art in 4:
		var liste: Array = listen[art]
		if liste.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true # Farbton und Blütenfarbe (im Shader INSTANCE_CUSTOM)
		mm.mesh = _meshes[art]
		mm.instance_count = liste.size()
		for i in liste.size():
			mm.set_instance_transform(i, liste[i][0])
			mm.set_instance_custom_data(i, liste[i][1])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _material
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		knoten.add_child(mmi)
	add_child(knoten)
	return knoten

const WIESE_ID := 1


func _im_freien_kreis(x: float, z: float) -> bool:
	for f in frei:
		if Vector2(x, z).distance_to(f[0]) < f[1]:
			return true
	return false


# --- Formen (UV.y = Höhe für den Wind, UV.x > 0.9 = Blüte) -----------------

func _dreieck(st: SurfaceTool, v: Array, uv: Array) -> void:
	for i in 3:
		st.set_uv(uv[i])
		st.add_vertex(v[i])


## Band aus Segmenten entlang punkte (je Punkt eine Breite), UV.y = Höhenanteil
func _band(st: SurfaceTool, punkte: Array, breiten: Array, quer_richtung: Vector3, max_h: float, uv_x := 0.5) -> void:
	for i in range(1, punkte.size()):
		var a: Vector3 = punkte[i - 1]
		var b: Vector3 = punkte[i]
		var qa: Vector3 = quer_richtung * float(breiten[i - 1])
		var qb: Vector3 = quer_richtung * float(breiten[i])
		var ua := Vector2(uv_x, clampf(a.y / max_h, 0.0, 1.0))
		var ub := Vector2(uv_x, clampf(b.y / max_h, 0.0, 1.0))
		_dreieck(st, [a - qa, a + qa, b - qb], [ua, ua, ub])
		_dreieck(st, [a + qa, b + qb, b - qb], [ua, ub, ub])


## Grasbüschel: 10 schmale, leicht gebogene Halme
func _gras_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 12345
	for b in 10:
		var a := rng.randf() * TAU
		var aus := Vector3(cos(a), 0, sin(a))
		var fuss := aus * rng.randf_range(0.0, 0.2)
		var neigung := aus * rng.randf_range(0.04, 0.16)
		var hoehe := rng.randf_range(0.22, 0.55)
		var breite := rng.randf_range(0.016, 0.028)
		var quer := Vector3(-sin(a + 1.2), 0, cos(a + 1.2))
		_band(st, [fuss, fuss + neigung * 0.35 + Vector3(0, hoehe * 0.55, 0), fuss + neigung + Vector3(0, hoehe, 0)],
			[breite, breite * 0.6, 0.0], quer, 0.55)
	st.generate_normals()
	return st.commit()


## Farn: 7 Wedel, die sich nach außen biegen und an den Spitzen absinken
func _farn_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 777
	for w in 7:
		var a := TAU * w / 7.0 + rng.randf_range(-0.3, 0.3)
		var aus := Vector3(cos(a), 0, sin(a))
		var laenge := rng.randf_range(0.5, 0.8)
		var hoch := rng.randf_range(0.3, 0.45)
		var punkte := []
		var breiten := []
		for s in 6:
			var t := s / 5.0
			# Bogen: steigt bis zur Mitte, sinkt zur Spitze
			punkte.append(aus * laenge * t + Vector3(0, hoch * sin(t * PI * 0.8) + 0.02, 0))
			breiten.append(0.11 * sin(t * PI) + 0.01)
		var quer := Vector3(-aus.z, 0, aus.x)
		_band(st, punkte, breiten, quer, 0.45)
		# Fiederblättchen: kleine Querblätter entlang des Wedels
		for s in range(1, 5):
			var p: Vector3 = punkte[s]
			for seite: float in [-1.0, 1.0]:
				var spitze: Vector3 = p + quer * seite * 0.16 + aus * 0.05 - Vector3(0, 0.03, 0)
				var uv := Vector2(0.5, clampf(p.y / 0.45, 0.0, 1.0))
				_dreieck(st, [p - aus * 0.04, p + aus * 0.05, spitze], [uv, uv, uv])
	st.generate_normals()
	return st.commit()


## Kraut / kleiner Strauch: 12 rautenförmige Blätter in verschiedenen Höhen
func _kraut_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 4242
	for b in 12:
		var a := rng.randf() * TAU
		var aus := Vector3(cos(a), 0, sin(a))
		var h := rng.randf_range(0.04, 0.38)
		var basis := aus * rng.randf_range(0.0, 0.1) + Vector3(0, h, 0)
		var laenge := rng.randf_range(0.12, 0.22)
		var spitze := basis + aus * laenge + Vector3(0, laenge * rng.randf_range(-0.2, 0.5), 0)
		var mitte := basis.lerp(spitze, 0.5)
		var quer := Vector3(-aus.z, 0, aus.x) * laenge * 0.35
		var uv_b := Vector2(0.5, h / 0.45)
		var uv_s := Vector2(0.5, clampf(spitze.y / 0.45, 0.0, 1.0))
		_dreieck(st, [basis, mitte + quer, spitze], [uv_b, uv_s, uv_s])
		_dreieck(st, [basis, spitze, mitte - quer], [uv_b, uv_s, uv_s])
		# Stängel zum Boden
		_band(st, [aus * 0.02, basis], [0.008, 0.006], Vector3(-aus.z, 0, aus.x), 0.45)
	st.generate_normals()
	return st.commit()


## Blumen: 5 dünne Stängel mit kleinen Blütenköpfen (UV.x = 1) und zwei Blättern am Fuß
func _blumen_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 999
	for b in 5:
		var a := rng.randf() * TAU
		var aus := Vector3(cos(a), 0, sin(a))
		var fuss := aus * rng.randf_range(0.0, 0.15)
		var hoehe := rng.randf_range(0.25, 0.5)
		var kopf := fuss + aus * 0.04 + Vector3(0, hoehe, 0)
		var quer := Vector3(-aus.z, 0, aus.x)
		_band(st, [fuss, fuss + Vector3(0, hoehe * 0.5, 0), kopf], [0.007, 0.006, 0.005], quer, 0.5)
		# Blütenkopf: drei gekreuzte kleine Rauten
		var uv := Vector2(1.0, 1.0)
		for k in 3:
			var r := Vector3(cos(a + k * PI / 3.0), 0, sin(a + k * PI / 3.0)) * 0.04
			var o := Vector3(0, 0.035, 0)
			_dreieck(st, [kopf - r, kopf + o, kopf + r], [uv, uv, uv])
			_dreieck(st, [kopf - r, kopf + r, kopf - o * 0.5], [uv, uv, uv])
		# Blätter am Fuß
		for seite: float in [-1.0, 1.0]:
			var s: Vector3 = fuss + quer * seite * 0.1 + Vector3(0, 0.06, 0)
			var uv_b := Vector2(0.5, 0.15)
			_dreieck(st, [fuss, s + aus * 0.03, s - aus * 0.03], [uv_b, uv_b, uv_b])
	st.generate_normals()
	return st.commit()
