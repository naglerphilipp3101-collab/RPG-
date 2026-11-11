class_name Mensch
extends Node3D
## Ein Mensch aus der MakeHuman-Basis (CC0): Form aus Reglern, Skelett mit den
## Godot-Humanoid-Knochennamen (passt zu Mixamo nach dem Retargeting), Haut, Augen.
##
## Aussehen als Dictionary (siehe standard_aussehen()):
##   geschlecht 0 (Frau) … 1 (Mann), alter 0 (25 J.) … 1 (≈75 J.), muskeln, gewicht, groesse 0…1,
##   herkunft [afrikanisch, asiatisch, europäisch] (Mischung, Summe 1), brust, brust_fest 0…1,
##   regler {id: -1…1}, sowie Farben und Haare (charakter_aussehen.gd).
## Der Körper steht in Ruhe in T-Pose (wie Mixamo); ruhe_a_pose() zeigt die Modellpose.

signal aufgebaut

## Knochen, die für die T-Pose auf die Richtung des Godot-Humanoid-Profils gedreht werden.
const T_POSE := ["UpperArm", "LowerArm", "Hand", "Thumb", "Index", "Middle", "Ring", "Little"]

@export var aussehen: Dictionary = {}

var skelett: Skeleton3D
var netze := {}          # Teilname -> MeshInstance3D
var pos: PackedVector3Array     # aktuelle Punkte (MakeHuman-Reihenfolge)
var _bind_lokal: Array[Transform3D] = []   # Modellpose (A-Pose) je Knochen, lokal
var _a_pose := false
var materialien := {}


func _ready() -> void:
	if skelett == null:
		aufbauen()


static func standard_aussehen() -> Dictionary:
	return CharakterAussehen.standard()


## Verfügbare Frisuren (Ids) für Männer bzw. Frauen.
static func frisuren(_mann: bool) -> Array:
	return []


const ANZEIGE := {"glatze": "Glatze", "keiner": "Kein Bart"}


static func anzeige_name(id: String) -> String:
	return ANZEIGE.get(id, id.capitalize())


## Verfügbare Bärte (Ids, ohne "keiner").
static func baerte() -> Array:
	return []


## Neues Aussehen übernehmen und den Menschen neu aufbauen.
func aussehen_setzen(a: Dictionary) -> void:
	aussehen = a
	aufbauen()


func wert(schluessel: String, standard: float = 0.5) -> float:
	return float(aussehen.get(schluessel, standard))


# ------------------------------------------------------------------ Formen
static func _zwei(v: float) -> Array:
	## MakeHuman-Interpolation für Regler mit Mitte: [min, mitte, max]
	v = clampf(v, 0.0, 1.0)
	if v < 0.5:
		return [1.0 - v * 2.0, v * 2.0, 0.0]
	return [0.0, 2.0 - v * 2.0, v * 2.0 - 1.0]


## Gewichte aller Formen nach den MakeHuman-Regeln (vereinfacht für Erwachsene).
func form_gewichte() -> Dictionary:
	var g := {}
	var mann := clampf(wert("geschlecht", 1.0), 0.0, 1.0)
	var geschl := {"female": 1.0 - mann, "male": mann}
	var alt := clampf(wert("alter", 0.1), 0.0, 1.0) * 0.8   # MakeHuman: young 25 J., old 90 J.
	var alter := {"young": 1.0 - alt, "old": alt}
	var m3 := _zwei(wert("muskeln"))
	var w3 := _zwei(wert("gewicht"))
	var mus := {"minmuscle": m3[0], "averagemuscle": m3[1], "maxmuscle": m3[2]}
	var gew := {"minweight": w3[0], "averageweight": w3[1], "maxweight": w3[2]}
	var h := clampf(wert("groesse"), 0.0, 1.0)
	var hoehe := {"minheight": maxf(0.0, 1.0 - h * 2.0), "maxheight": maxf(0.0, h * 2.0 - 1.0)}
	var herk: Array = aussehen.get("herkunft", [0.0, 0.0, 1.0])
	var hs: float = maxf(0.001, float(herk[0]) + float(herk[1]) + float(herk[2]))
	var herkunft := {"african": float(herk[0]) / hs, "asian": float(herk[1]) / hs, "caucasian": float(herk[2]) / hs}
	for gs in geschl:
		for al in alter:
			var ga: float = geschl[gs] * alter[al]
			if ga < 0.001:
				continue
			for r in herkunft:
				_dazu(g, "%s-%s-%s" % [r, gs, al], ga * herkunft[r])
			for m in mus:
				for w in gew:
					_dazu(g, "universal-%s-%s-%s-%s" % [gs, al, m, w], ga * mus[m] * gew[w])
			for hh in hoehe:
				_dazu(g, "hoehe-%s-%s-%s" % [gs, al, hh], ga * hoehe[hh])
	# Brust (nur Frauen)
	var c3 := _zwei(wert("brust"))
	var f3 := _zwei(wert("brust_fest"))
	var cup := {"mincup": c3[0], "averagecup": c3[1], "maxcup": c3[2]}
	var fest := {"minfirmness": f3[0], "averagefirmness": f3[1], "maxfirmness": f3[2]}
	for al in alter:
		for c in cup:
			for f in fest:
				_dazu(g, "brust-%s-%s-%s" % [al, c, f], geschl["female"] * alter[al] * cup[c] * fest[f])
	# Einzelregler
	var regler: Dictionary = aussehen.get("regler", {})
	for id in regler:
		var v: float = regler[id]
		if v > 0.0:
			_dazu(g, id + "+", v)
		elif v < 0.0:
			_dazu(g, id + "-", -v)
	return g


static func _dazu(g: Dictionary, name: String, w: float) -> void:
	if w > 0.002 and MenschDaten.hat_form(name):
		g[name] = g.get(name, 0.0) + w


func form_berechnen() -> PackedVector3Array:
	MenschDaten.laden()
	var p := MenschDaten.grund_pos.duplicate()
	var gew := form_gewichte()
	for name in gew:
		var w: float = gew[name]
		var paar: Array = MenschDaten.form(name)
		var idx: PackedInt32Array = paar[0]
		var d: PackedVector3Array = paar[1]
		for i in idx.size():
			var k := idx[i]
			p[k] += d[i] * w
	# Füße auf den Boden (MakeHuman hat den Ursprung in der Körpermitte)
	var boden := Vector3.ZERO
	var bereiche: Array = MenschDaten.meta["gruppen"]["joint-ground"]
	var zahl := 0
	for b in bereiche:
		for k in range(int(b[0]), int(b[1]) + 1):
			boden += p[k]
			zahl += 1
	boden /= float(zahl)
	boden.x = 0.0
	boden.z = 0.0
	for k in p.size():
		p[k] -= boden
	return p


static func normalen(p: PackedVector3Array, dreiecke_mh: PackedInt32Array) -> PackedVector3Array:
	var n := PackedVector3Array()
	n.resize(p.size())
	var i := 0
	var anzahl := dreiecke_mh.size()
	while i < anzahl:
		var a := dreiecke_mh[i]
		var b := dreiecke_mh[i + 1]
		var c := dreiecke_mh[i + 2]
		# Godot-Reihenfolge ist im Uhrzeigersinn -> (c-a)×(b-a)
		var fn := (p[c] - p[a]).cross(p[b] - p[a])
		n[a] += fn
		n[b] += fn
		n[c] += fn
		i += 3
	return n


# ------------------------------------------------------------------ Aufbau
func aufbauen() -> void:
	MenschDaten.laden()
	pos = form_berechnen()
	_skelett_bauen()
	_teil_bauen("koerper", _haut_material())
	_teil_bauen("wimpern", _wimpern_material())
	_teil_bauen("zaehne", _einfach_material(Color(0.86, 0.83, 0.76), 0.35))
	_teil_bauen("zunge", _einfach_material(Color(0.55, 0.25, 0.25), 0.5))
	_augen_bauen()
	if _a_pose:
		ruhe_a_pose(true)
	aufgebaut.emit()


func _mittel(liste: Array) -> Vector3:
	var s := Vector3.ZERO
	for v in liste:
		s += pos[int(v)]
	return s / float(liste.size())


func _skelett_bauen() -> void:
	if skelett == null:
		skelett = Skeleton3D.new()
		skelett.name = "Skelett"
		add_child(skelett)
	skelett.clear_bones()
	var knochen: Array = MenschDaten.meta["knochen"]
	var profil := SkeletonProfileHumanoid.new()
	# Profil-Basis global je Knochenname
	var profil_global := {}
	for i in profil.bone_size:
		var par := profil.get_bone_parent(i)
		var t := profil.get_reference_pose(i)
		profil_global[profil.get_bone_name(i)] = (profil_global[par] if par != &"" else Transform3D()) * t
	skelett.add_bone("Root")
	var n := knochen.size()
	var kopf: Array[Vector3] = []
	var dreh: Array[Basis] = []       # globale Drehung Modellpose -> T-Pose
	var t_global: Array[Transform3D] = []
	var a_global: Array[Transform3D] = []
	for i in n:
		var k: Dictionary = knochen[i]
		var name: String = k["name"]
		skelett.add_bone(name)
		var h := _mittel(k["kopf"])
		var e := _mittel(k["ende"])
		kopf.append(h)
		var eltern: int = k["eltern"]
		var b_t: Basis = (profil_global[StringName(name)] as Transform3D).basis
		var q := Basis()
		if _t_pose_knochen(name):
			var d_a := (e - h).normalized()
			q = Basis(Quaternion(d_a, b_t.y.normalized()))
		elif eltern >= 0:
			q = dreh[eltern]
		dreh.append(q)
		var p_t := h
		if eltern >= 0:
			p_t = t_global[eltern].origin + dreh[eltern] * (h - kopf[eltern])
		t_global.append(Transform3D(b_t, p_t))
		a_global.append(Transform3D(q.inverse() * b_t, h))
	var skin := Skin.new()
	_bind_lokal.clear()
	skelett.set_bone_rest(0, Transform3D())
	skin.add_named_bind("Root", Transform3D())
	_bind_lokal.append(Transform3D())
	for i in n:
		var k: Dictionary = knochen[i]
		var eltern: int = k["eltern"]
		skelett.set_bone_parent(i + 1, eltern + 1 if eltern >= 0 else 0)
		var rest := t_global[i] if eltern < 0 else t_global[eltern].affine_inverse() * t_global[i]
		skelett.set_bone_rest(i + 1, rest)
		var a_lok := a_global[i] if eltern < 0 else a_global[eltern].affine_inverse() * a_global[i]
		_bind_lokal.append(a_lok)
		skin.add_named_bind(k["name"], a_global[i].affine_inverse())
	skelett.reset_bone_poses()
	set_meta("skin", skin)


func _t_pose_knochen(name: String) -> bool:
	for s in T_POSE:
		if name.contains(s):
			return true
	return false


## Zeigt die Modellpose (A-Pose, Arme schräg) statt der T-Pose.
func ruhe_a_pose(an: bool) -> void:
	_a_pose = an
	if skelett == null:
		return
	for i in skelett.get_bone_count():
		var t := _bind_lokal[i] if an else skelett.get_bone_rest(i)
		skelett.set_bone_pose_position(i, t.origin)
		skelett.set_bone_pose_rotation(i, t.basis.get_rotation_quaternion())


func _teil_bauen(name: String, mat: Material) -> void:
	var t := MenschDaten.teil(name)
	var mh: PackedInt32Array = t["mh_index"]
	var nrm_mh := normalen(pos, t["dreiecke_mh"])
	var v := PackedVector3Array()
	var nv := PackedVector3Array()
	var uv := PackedVector2Array()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	var anzahl := mh.size()
	v.resize(anzahl)
	nv.resize(anzahl)
	uv.resize(anzahl)
	bones.resize(anzahl * 4)
	weights.resize(anzahl * 4)
	var uvf: PackedFloat32Array = t["uv"]
	var ki := MenschDaten.knochen_index
	var kg := MenschDaten.knochen_gewicht
	for i in anzahl:
		var k := mh[i]
		v[i] = pos[k]
		nv[i] = nrm_mh[k].normalized()
		uv[i] = Vector2(uvf[i * 2], uvf[i * 2 + 1])
		for j in 4:
			bones[i * 4 + j] = ki[k * 4 + j] + 1
			weights[i * 4 + j] = kg[k * 4 + j]
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nv
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = t["dreiecke"]
	_netz_setzen(name, arr, mat)


func _netz_setzen(name: String, arr: Array, mat: Material) -> void:
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	m.surface_set_material(0, mat)
	var mi: MeshInstance3D = netze.get(name)
	if mi == null:
		mi = MeshInstance3D.new()
		mi.name = name.capitalize()
		skelett.add_child(mi)
		netze[name] = mi
	mi.mesh = m
	mi.skin = get_meta("skin")
	mi.skeleton = NodePath("..")


func _augen_bauen() -> void:
	var a := MenschDaten.anbau("augen")
	var bd: PackedFloat32Array = a["bindung"]
	var sk: Dictionary = a["skalierung"]
	var s := Vector3(_skal(sk["x"], 0), _skal(sk["y"], 1), _skal(sk["z"], 2))
	var anzahl := bd.size() / 9
	var v := PackedVector3Array()
	v.resize(anzahl)
	for i in anzahl:
		var o := i * 9
		var p := pos[int(bd[o])] * bd[o + 3] + pos[int(bd[o + 1])] * bd[o + 4] + pos[int(bd[o + 2])] * bd[o + 5]
		v[i] = p + Vector3(bd[o + 6], bd[o + 7], bd[o + 8]) * s
	var uvf: PackedFloat32Array = a["uv"]
	var uv := PackedVector2Array()
	uv.resize(anzahl)
	for i in anzahl:
		uv[i] = Vector2(uvf[i * 2], uvf[i * 2 + 1])
	var dr: PackedInt32Array = a["dreiecke"]
	var nv := PackedVector3Array()
	nv.resize(anzahl)
	for i in range(0, dr.size(), 3):
		var fn := (v[dr[i + 2]] - v[dr[i]]).cross(v[dr[i + 1]] - v[dr[i]])
		for j in 3:
			nv[dr[i + j]] += fn
	var kopf := skelett.find_bone("Head")
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	for i in anzahl:
		nv[i] = nv[i].normalized()
		bones.append_array([kopf, 0, 0, 0])
		weights.append_array([1.0, 0.0, 0.0, 0.0])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nv
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = dr
	_netz_setzen("augen", arr, _augen_material())


func _skal(spec: Array, achse: int) -> float:
	return absf(pos[int(spec[0])][achse] - pos[int(spec[1])][achse]) / float(spec[2])


# ------------------------------------------------------------------ Materialien (vorläufig)
func _haut_material() -> Material:
	var m: StandardMaterial3D = materialien.get("haut")
	if m:
		m.albedo_color = Color.html(aussehen.get("haut", "#e8bfa0"))
		return m
	m = StandardMaterial3D.new()
	m.albedo_color = Color.html(aussehen.get("haut", "#e8bfa0"))
	m.roughness = 0.6
	m.subsurf_scatter_enabled = true
	m.subsurf_scatter_strength = 0.4
	materialien["haut"] = m
	return m


func _wimpern_material() -> Material:
	return _einfach_material(Color(0.05, 0.04, 0.03), 0.8)


func _augen_material() -> Material:
	var m: ShaderMaterial = materialien.get("augen")
	if m == null:
		m = ShaderMaterial.new()
		m.shader = preload("res://assets/charakter/auge.gdshader")
		m.set_shader_parameter("textur", preload("res://assets/charakter/texturen/auge.png"))
		materialien["augen"] = m
	m.set_shader_parameter("iris_farbe", Color.html(aussehen.get("augen", "#6b3f1f")))
	return m


func _einfach_material(c: Color, r: float) -> Material:
	var schluessel := "einfach_" + c.to_html()
	if materialien.has(schluessel):
		return materialien[schluessel]
	var m := StandardMaterial3D.new()
	materialien[schluessel] = m
	m.albedo_color = c
	m.roughness = r
	return m
