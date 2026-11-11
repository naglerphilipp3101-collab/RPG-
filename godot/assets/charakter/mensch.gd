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
## Gleiche Menschen teilen sich Netze (Gegner, NPCs). Aus, wenn das Aussehen oft wechselt (Erstellung),
## weil die Materialien dann mitwandern würden.
var zwischenspeicher_nutzen := true

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


const FRISUREN_MANN := ["short02", "short01", "short03", "short04", "stoppeln", "afro01", "long01", "ponytail01", "braid01", "bob01", "bob02"]
const FRISUREN_FRAU := ["long01", "ponytail01", "braid01", "bob01", "bob02", "short01", "short02", "short03", "short04", "afro01", "stoppeln"]
## Bärte als Stärke der Masken (voll = Wangen/Kiefer, schnurr, kinn) und Dichte.
const BAERTE := {
	"stoppeln": {"voll": 0.75, "schnurr": 0.75, "kinn": 0.75, "dichte": 0.0},
	"kinnbart": {"voll": 0.0, "schnurr": 1.0, "kinn": 1.0, "dichte": 1.0},
	"schnurrbart": {"voll": 0.0, "schnurr": 1.0, "kinn": 0.0, "dichte": 1.0},
	"kurzer_bart": {"voll": 1.0, "schnurr": 1.0, "kinn": 1.0, "dichte": 0.75},
	"vollbart": {"voll": 1.0, "schnurr": 1.0, "kinn": 1.0, "dichte": 1.0},
}


## Verfügbare Frisuren (Ids) für Männer bzw. Frauen (gleiche Auswahl, andere Reihenfolge).
static func frisuren(mann: bool) -> Array:
	MenschDaten.laden()
	var out := []
	for id in (FRISUREN_MANN if mann else FRISUREN_FRAU):
		if id == "stoppeln" or MenschDaten.meta["anbau"].has("haar:" + id):
			out.append(id)
	return out


static func augenbrauen() -> Array:
	return _anbau_ids("brauen")


static func wimpern() -> Array:
	return _anbau_ids("wimpern")


static func _anbau_ids(art: String) -> Array:
	MenschDaten.laden()
	var out := []
	for k: String in MenschDaten.meta["anbau"]:
		if k.begins_with(art + ":"):
			out.append(k.substr(art.length() + 1))
	out.sort()
	return out


const ANZEIGE := {
	"glatze": "Glatze", "keiner": "Kein Bart", "stoppeln": "Stoppeln", "kinnbart": "Kinnbart",
	"schnurrbart": "Schnurrbart", "kurzer_bart": "Kurzer Bart", "vollbart": "Vollbart",
	"short01": "Kurz 1", "short02": "Kurz 2", "short03": "Kurz 3", "short04": "Kurz 4",
	"long01": "Lang", "ponytail01": "Pferdeschwanz", "braid01": "Zopf", "bob01": "Bob 1", "bob02": "Bob 2",
	"afro01": "Afro",
}


static func anzeige_name(id: String) -> String:
	if id.begins_with("eyebrow"):
		return "Brauen " + str(int(id.substr(7)))
	if id.begins_with("eyelashes"):
		return "Wimpern " + str(int(id.substr(9)))
	return ANZEIGE.get(id, id.capitalize())


## Verfügbare Bärte (Ids, ohne "keiner").
static func baerte() -> Array:
	return BAERTE.keys()


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
## Fertig gebaute Menschen je Aussehen (für viele gleiche NPCs/Gegner); klein halten.
static var _zwischenspeicher := {}
const ZWISCHENSPEICHER_MAX := 24


func aufbauen() -> void:
	MenschDaten.laden()
	var schluessel := JSON.stringify(aussehen)
	if not zwischenspeicher_nutzen:
		_neu_bauen()
		aufgebaut.emit()
		return
	if _zwischenspeicher.has(schluessel):
		_aus_zwischenspeicher(_zwischenspeicher[schluessel])
		aufgebaut.emit()
		return
	_neu_bauen()
	if _zwischenspeicher.size() >= ZWISCHENSPEICHER_MAX:
		_zwischenspeicher.erase(_zwischenspeicher.keys()[0])
	_zwischenspeicher[schluessel] = _fuer_zwischenspeicher()
	aufgebaut.emit()


func _fuer_zwischenspeicher() -> Dictionary:
	var knochen := []
	for i in skelett.get_bone_count():
		knochen.append([skelett.get_bone_name(i), skelett.get_bone_parent(i), skelett.get_bone_rest(i)])
	var meshes := {}
	for n in netze:
		meshes[n] = netze[n].mesh
	return {"pos": pos, "knochen": knochen, "bind": _bind_lokal.duplicate(), "skin": get_meta("skin"), "meshes": meshes}


func _aus_zwischenspeicher(z: Dictionary) -> void:
	pos = z["pos"]
	if skelett == null:
		skelett = Skeleton3D.new()
		skelett.name = "Skelett"
		add_child(skelett)
	skelett.clear_bones()
	for k in z["knochen"]:
		var i := skelett.add_bone(k[0])
		skelett.set_bone_parent(i, k[1])
		skelett.set_bone_rest(i, k[2])
	skelett.reset_bone_poses()
	_bind_lokal = z["bind"].duplicate()
	set_meta("skin", z["skin"])
	var meshes: Dictionary = z["meshes"]
	for n in netze.keys():
		if not meshes.has(n):
			netze[n].queue_free()
			netze.erase(n)
	for n in meshes:
		var mi: MeshInstance3D = netze.get(n)
		if mi == null:
			mi = MeshInstance3D.new()
			mi.name = String(n).capitalize()
			skelett.add_child(mi)
			netze[n] = mi
		mi.mesh = meshes[n]
		mi.skin = z["skin"]
		mi.skeleton = NodePath("..")
	if _a_pose:
		ruhe_a_pose(true)


func _neu_bauen() -> void:
	pos = form_berechnen()
	_skelett_bauen()
	_teil_bauen("koerper", _haut_material())
	_anbau_bauen("augen", "augen", _augen_material())
	_anbau_bauen("wimpern", "wimpern:" + String(aussehen.get("wimpern", "eyelashes01")), _haar_material("wimpern", true))
	_anbau_bauen("brauen", "brauen:" + String(aussehen.get("brauen", "eyebrow001")), _haar_material("brauen", true))
	_anbau_bauen("haar", "haar:" + String(aussehen.get("haar", "")), _haar_material("haar"))
	_anbau_bauen("zaehne", "zaehne:teeth_base", _textur_material("zaehne:teeth_base", 0.3))
	_anbau_bauen("zunge", "zunge:tongue01", _textur_material("zunge:tongue01", 0.45))
	if _a_pose:
		ruhe_a_pose(true)


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
	var masken := MenschDaten.masken
	var farben := PackedColorArray()
	farben.resize(anzahl)
	var uv2 := PackedVector2Array()
	uv2.resize(anzahl)
	var waesche := MenschDaten.waesche
	var ki := MenschDaten.knochen_index
	var kg := MenschDaten.knochen_gewicht
	for i in anzahl:
		var k := mh[i]
		v[i] = pos[k]
		nv[i] = nrm_mh[k].normalized()
		uv[i] = Vector2(uvf[i * 2], uvf[i * 2 + 1])
		farben[i] = Color8(masken[k * 4], masken[k * 4 + 1], masken[k * 4 + 2], masken[k * 4 + 3])
		uv2[i] = Vector2(waesche[k * 2] / 255.0, waesche[k * 2 + 1] / 255.0)
		for j in 4:
			bones[i * 4 + j] = ki[k * 4 + j] + 1
			weights[i * 4 + j] = kg[k * 4 + j]
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nv
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_COLOR] = farben
	arr[Mesh.ARRAY_TEX_UV2] = uv2
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


## Anbauteil (MakeHuman .mhclo) an die aktuelle Form anpassen: Augen, Haare, Brauen, Wimpern, Zähne.
## Die Gewichte kommen von den Punkten des Körpers, an denen das Teil hängt.
func _anbau_bauen(name: String, schluessel: String, mat: Material) -> void:
	if not MenschDaten.meta["anbau"].has(schluessel):
		if netze.has(name):
			netze[name].queue_free()
			netze.erase(name)
		return
	var a := MenschDaten.anbau(schluessel)
	var bd: PackedFloat32Array = a["bindung"]
	var sk: Dictionary = a["skalierung"]
	var s := Vector3(_skal(sk["x"], 0), _skal(sk["y"], 1), _skal(sk["z"], 2))
	var anzahl := bd.size() / 9
	var v := PackedVector3Array()
	v.resize(anzahl)
	for i in anzahl:
		var o := i * 9
		v[i] = pos[int(bd[o])] * bd[o + 3] + pos[int(bd[o + 1])] * bd[o + 4] + pos[int(bd[o + 2])] * bd[o + 5] \
			+ Vector3(bd[o + 6], bd[o + 7], bd[o + 8]) * s
	var bones: PackedInt32Array = a["knochen_index"]
	var weights: PackedFloat32Array = a["knochen_gewicht"]
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
	for i in anzahl:
		nv[i] = nv[i].normalized()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nv
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = dr
	_netz_setzen(name, arr, mat)


func _skal(spec: Array, achse: int) -> float:
	return absf(pos[int(spec[0])][achse] - pos[int(spec[1])][achse]) / float(spec[2])


# ------------------------------------------------------------------ Materialien
## Hauttextur passend zu Geschlecht, Alter und Hautfarbe (die nächstliegende Helligkeit).
func haut_textur() -> Dictionary:
	var liste: Array = MenschDaten.meta.get("haut", [])
	if liste.is_empty():
		return {}
	var frau := float(aussehen.get("geschlecht", 1.0)) < 0.5
	var ziel := Color.html(aussehen.get("haut", "#d1a184"))
	var alt := float(aussehen.get("alter", 0.1)) > 0.6
	var beste: Dictionary = {}
	var abstand := INF
	for h in liste:
		if (h["geschlecht"] == "female") != frau:
			continue
		# Abdunkeln sieht besser aus als Aufhellen: dunklere Texturen zählen dreifach
		var d := Color.html(h["mittel"]).get_luminance() - ziel.get_luminance()
		d = d if d >= 0.0 else -d * 3.0
		if (h["alter"] == "old") != alt:
			d += 0.12
		if d < abstand:
			abstand = d
			beste = h
	return beste


func _haut_material() -> Material:
	var m: ShaderMaterial = materialien.get("haut")
	if m == null:
		m = ShaderMaterial.new()
		m.shader = preload("res://assets/charakter/haut.gdshader")
		materialien["haut"] = m
	var h := haut_textur()
	if not h.is_empty():
		m.set_shader_parameter("textur", load(h["textur"]))
		m.set_shader_parameter("textur_mittel", Color.html(h["mittel"]))
	m.set_shader_parameter("haut_farbe", Color.html(aussehen.get("haut", "#d1a184")))
	m.set_shader_parameter("haar_farbe", Color.html(aussehen.get("haar_farbe", "#4a3122")))
	var b: Dictionary = BAERTE.get(aussehen.get("bart", "keiner"), {})
	var stoppel := 0.0
	if String(aussehen.get("haar", "")) == "stoppeln":
		stoppel = 0.8
	elif String(aussehen.get("haar", "")) != "glatze" and String(aussehen.get("haar", "")) != "":
		stoppel = 0.55   # Kopfhaut unter den Haarkarten abdunkeln
	m.set_shader_parameter("bart", Vector4(b.get("voll", 0.0), b.get("schnurr", 0.0), b.get("kinn", 0.0), stoppel))
	m.set_shader_parameter("stoppeln", float(b.get("dichte", 0.0)))
	m.set_shader_parameter("waesche_oben", 1.0 if float(aussehen.get("geschlecht", 1.0)) < 0.5 else 0.0)
	return m


func _haar_material(art: String, fein := false) -> Material:
	var schluessel := art + ":" + String(aussehen.get(art, {"haar": "", "brauen": "eyebrow001", "wimpern": "eyelashes01"}[art]))
	var m: ShaderMaterial = materialien.get(art)
	if m == null:
		m = ShaderMaterial.new()
		m.shader = preload("res://assets/charakter/haar.gdshader")
		materialien[art] = m
	if MenschDaten.meta["anbau"].has(schluessel):
		var a: Dictionary = MenschDaten.meta["anbau"][schluessel]
		if a.has("textur"):
			m.set_shader_parameter("textur", load(a["textur"]))
		m.set_shader_parameter("hell", float(a.get("hell", 0.15)))
	var farbe := Color.html(aussehen.get("haar_farbe", "#4a3122"))
	if art == "wimpern":
		farbe = farbe.darkened(0.6)
	elif art == "brauen":
		farbe = farbe.darkened(0.15)
	m.set_shader_parameter("farbe", farbe)
	m.set_shader_parameter("struktur", 0.3 if fein else 0.7)
	m.set_shader_parameter("alpha_grenze", 0.3 if fein else 0.45)
	return m


func _textur_material(schluessel: String, rauheit: float) -> Material:
	if materialien.has(schluessel):
		return materialien[schluessel]
	var m := StandardMaterial3D.new()
	var a: Dictionary = MenschDaten.meta["anbau"].get(schluessel, {})
	if a.has("textur"):
		m.albedo_texture = load(a["textur"])
	m.roughness = rauheit
	materialien[schluessel] = m
	return m


func _augen_material() -> Material:
	var m: ShaderMaterial = materialien.get("augen")
	if m == null:
		m = ShaderMaterial.new()
		m.shader = preload("res://assets/charakter/auge.gdshader")
		m.set_shader_parameter("textur", preload("res://assets/charakter/texturen/auge.png"))
		materialien["augen"] = m
	m.set_shader_parameter("iris_farbe", Color.html(aussehen.get("augen", "#6b3f1f")))
	return m
