extends Node3D
## Bodenbewuchs rund um den Spieler: Gras, Farne, Kräuter/kleine Sträucher und Blumen als MultiMeshes in
## 16-m-Kacheln bis RADIUS (ferner trägt die Bodentextur). Mischung, Dichte und Farbton nach den Biom-Regeln
## (data/biome.json, "gras"): im Wald vor allem Farne und Kräuter, auf Wiesen Gras mit Blumenflecken.
## Kein Bewuchs in Flüssen, Städten/Dörfern, Feldern, Seen, am Strand, auf Fels/Schnee und an Steilhängen.
## Nutzt die Daten von scripts/natur.gd.

const GrasShader := preload("res://scripts/gras.gdshader")
const GrasScanShader := preload("res://scripts/gras_scan.gdshader")

const KACHEL := 16.0
const RADIUS := 35.0
const ABSTAND := 0.55            # Raster der Stellen in Metern (bei voller Dichte)
const BUDGET_US := 3000          # Zeit je Frame für neue Kacheln
const NAH := 15.0                # bis hier volle Dichte, dahinter halb so viel (etwas größer)

enum { GRAS, FARN, KRAUT, BLUME }
## Anteile und Farben je Biom stehen in data/biome.json unter "gras" (gras, farn, kraut, blume, farbe, ton)
const ARTEN := ["gras", "farn", "kraut", "blume"]
const FARN_FARBE := Color(0.26, 0.42, 0.16)
const KRAUT_FARBE := Color(0.3, 0.44, 0.2)

var natur                         # scripts/natur.gd
var ziel: Node3D
var frei: Array = []              # zusätzliche freie Kreise [Vector2 Mitte, Radius] (Dorfplatz, Lager)
var _kacheln := {}                # Vector2i -> Node3D (je Art ein MultiMeshInstance3D)
var _offen: Array = []
var _mitte := Vector2(INF, INF)
var _material := ShaderMaterial.new()
var _materialien: Array = []      # alle Materialien, die "mitte" brauchen
## je Art eine Liste von Varianten {mesh, xf (Transform aus dem Scan), mat, s (Skalierung min, max)}
var _varianten: Array = []
var _scans := false

## Fotogescannter Bewuchs (Poly Haven, scripts/scan_modelle.gd): Scan, Teil-Filter, Skalierung
const SCANS := [
	[["grass_medium_01", "tall", Vector2(2.4, 3.2)], ["grass_medium_01", "mid", Vector2(2.2, 3.0)], ["grass_medium_01", "large", Vector2(2.0, 2.6)]],
	[["fern_02", "_a", Vector2(1.0, 1.4)], ["fern_02", "_d", Vector2(1.0, 1.4)], ["fern_02", "_b", Vector2(0.9, 1.2)]],
	[["celandine_01", "_a_", Vector2(1.3, 1.8)], ["celandine_01", "_b_", Vector2(1.3, 1.8)], ["celandine_01", "_e_", Vector2(1.3, 1.8)]],
	[["dandelion_01", "_c_", Vector2(1.3, 1.7)], ["dandelion_01", "_d_", Vector2(1.5, 2.0)], ["dandelion_01", "_e_", Vector2(1.3, 1.7)]],
]
func setup(natur_node, spieler: Node3D) -> void:
	natur = natur_node
	ziel = spieler
	_material.shader = GrasShader
	_material.set_shader_parameter("radius", RADIUS)
	_materialien = [_material]
	_scans = ScanModelle.vorhanden("grass_medium_01")
	if _scans:
		for art in 4:
			var liste: Array = []
			for eintrag in SCANS[art]:
				for teil in ScanModelle.teile(eintrag[0], eintrag[1]):
					liste.append({"mesh": teil["mesh"], "xf": teil["xf"], "mat": _scan_material(teil), "s": eintrag[2]})
			if liste.is_empty():
				_scans = false
			_varianten.append(liste)
	if not _scans:
		_varianten = []
		for m in [_gras_mesh(), _farn_mesh(), _kraut_mesh(), _blumen_mesh()]:
			_varianten.append([{"mesh": m, "xf": Transform3D.IDENTITY, "mat": _material, "s": Vector2(0.7, 1.3)}])


## Shader-Material für einen Scan-Teil: Texturen aus dem Material des Scans übernehmen
func _scan_material(teil: Dictionary) -> ShaderMaterial:
	var orig := (teil["mesh"] as Mesh).surface_get_material(0) as BaseMaterial3D
	var m := ShaderMaterial.new()
	m.shader = GrasScanShader
	if orig:
		m.set_shader_parameter("farbe", orig.albedo_texture)
		m.set_shader_parameter("normale", orig.normal_texture)
		m.set_shader_parameter("orm", orig.roughness_texture)
		var pfad := "res://assets/scans/%s/textures/%s_alpha_2k.png" % [orig.resource_name, orig.resource_name]
		if ResourceLoader.exists(pfad):
			m.set_shader_parameter("alpha_map", load(pfad))
			m.set_shader_parameter("mit_alpha", true)
	m.set_shader_parameter("hoehe", maxf(0.05, (teil["aabb"] as AABB).size.y))
	m.set_shader_parameter("radius", RADIUS)
	_materialien.append(m)
	return m


func _process(_delta: float) -> void:
	if ziel == null:
		return
	var p := Vector2(ziel.global_position.x, ziel.global_position.z)
	for m in _materialien:
		m.set_shader_parameter("mitte", p)
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
	# Felder/freie Kreise nur prüfen, wenn die Kachel überhaupt welche berührt
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
			var regel: Dictionary = natur._regel(x, z)
			var anteil: Dictionary = regel.get("gras", {})
			if anteil.is_empty():
				continue
			# Art auswählen; Blumen wachsen in Flecken (Rauschen)
			var flecken: float = clampf(natur.rauschen.get_noise_2d(x * 4.0, z * 4.0) * 2.5 + 0.4, 0.1, 2.5)
			var art := -1
			var summe := 0.0
			for a in 4:
				summe += float(anteil.get(ARTEN[a], 0.0)) * faktor * (flecken if a == BLUME else 1.0)
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
			if pruefen and (natur._im_feld(x, z) or _im_freien_kreis(x, z)):
				continue
			var c: Color
			var farbe := _farbe(anteil.get("farbe", [0.4, 0.58, 0.2]))
			if _scans:
				var ton := _farbe(anteil.get("ton", [1.0, 1.0, 1.0]))
				c = ton.lerp(ton * Color(1.1, 1.08, 0.9), rng.randf())
			else:
				match art:
					GRAS:
						c = farbe
					FARN:
						c = FARN_FARBE
					_:
						c = KRAUT_FARBE.lerp(farbe, 0.4)
				c = c.lerp(Color(c.r * 1.25, c.g * 1.15, c.b * 0.9), rng.randf())
			# Blütenfarbe im Alpha (nur eigene Formen): meist lila, sonst weiß, gelb, rosa
			c.a = 0.0 if farbwahl < 0.45 else (0.33 if farbwahl < 0.7 else (0.66 if farbwahl < 0.88 else 1.0))
			# gescannte Grasbüschel sind kleiner: je Stelle zwei
			for kk in (4 if _scans and art == GRAS else 1):
				var varianten: Array = _varianten[art]
				var vi := rng.randi_range(0, varianten.size() - 1)
				var sv: Vector2 = varianten[vi]["s"]
				var s := (groesse if not _scans else 1.0) * lerpf(sv.x, sv.y, rng.randf())
				var basis := Basis(Vector3.UP, dreh + kk * 2.1).scaled(Vector3(s, s * (1.1 if regel["biom"] == "wiese" else 0.9), s))
				var versatz := Vector3(rng.randf_range(-0.25, 0.25), 0, rng.randf_range(-0.3, 0.3)) * minf(kk, 1.0)
				listen[art].append([Transform3D(basis, Vector3(x, h - 0.03, z) + versatz) * (varianten[vi]["xf"] as Transform3D), c, vi])
	var knoten := Node3D.new()
	knoten.set_meta("voll", voll)
	for art in 4:
		# je Variante ein MultiMesh
		var je_variante := {}
		for e in listen[art]:
			if not je_variante.has(e[2]):
				je_variante[e[2]] = []
			je_variante[e[2]].append(e)
		for vi in je_variante:
			var liste: Array = je_variante[vi]
			var v: Dictionary = _varianten[art][vi]
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true # Farbton und Blütenfarbe (im Shader INSTANCE_CUSTOM)
			mm.mesh = v["mesh"]
			mm.instance_count = liste.size()
			for i in liste.size():
				mm.set_instance_transform(i, liste[i][0])
				mm.set_instance_custom_data(i, liste[i][1])
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.material_override = v["mat"]
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			knoten.add_child(mmi)
	add_child(knoten)
	return knoten



func _farbe(werte: Array) -> Color:
	return Color(float(werte[0]), float(werte[1]), float(werte[2]))


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
