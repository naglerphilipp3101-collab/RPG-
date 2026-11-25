extends SceneTree
## Rechnet Mixamo-Animationen (FBX, „Without Skin“) auf das Skelett von Mensch um.
## Liest jeden Unterordner von assets/animationen/mixamo/ und schreibt je Ordner eine
## AnimationLibrary assets/animationen/mixamo/<ordner>.res (Spuren "Skelett:<Knochen>").
## Die Mixamo-Dateien und die .res-Dateien bleiben lokal (gitignored, nicht frei weiterzugeben).
##
## Verfahren: je Bild die Drehung jedes Mixamo-Knochens gegenüber seiner Ruhe (in Weltkoordinaten)
## auf den passenden Knochen von Mensch übertragen. Vorher wird jeder Knochen von Mensch so gedreht,
## dass er in der Ruhe in dieselbe Richtung zeigt wie der Mixamo-Knochen (Füße, Wirbelsäule, Finger),
## damit die Haltung gleich aussieht, auch wenn die Ruhehaltungen etwas abweichen.
## Die Hüfte wandert nicht (Bewegung nach vorn/seitlich wird herausgerechnet, auf und ab bleibt).
##
## Start: Godot --headless --path godot -s res://assets/animationen/mixamo_umwandeln.gd [-- ordner1,ordner2]

const ORDNER := "res://assets/animationen/mixamo/"
const BILDER_PRO_S := 30.0
## Wörter im Dateinamen, die eine Schleife bedeuten.
const SCHLEIFE := ["idle", "walk", "run", "strafe", "sprint", "loop", "crouching", "fishing idle"]

## Mixamo-Name (ohne "mixamorig_") -> Name bei Mensch (Godot-Humanoid).
static func zuordnung() -> Dictionary:
	var z := {"Hips": "Hips", "Spine": "Spine", "Spine1": "Chest", "Spine2": "UpperChest", "Neck": "Neck", "Head": "Head"}
	for s in ["Left", "Right"]:
		z[s + "Shoulder"] = s + "Shoulder"
		z[s + "Arm"] = s + "UpperArm"
		z[s + "ForeArm"] = s + "LowerArm"
		z[s + "Hand"] = s + "Hand"
		z[s + "UpLeg"] = s + "UpperLeg"
		z[s + "Leg"] = s + "LowerLeg"
		z[s + "Foot"] = s + "Foot"
		z[s + "ToeBase"] = s + "Toes"
		var teile := ["Proximal", "Intermediate", "Distal"]
		for f in [["Thumb", "Thumb"], ["Index", "Index"], ["Middle", "Middle"], ["Ring", "Ring"], ["Pinky", "Little"]]:
			for i in 3:
				var ziel: String = (["Metacarpal", "Proximal", "Distal"] if f[0] == "Thumb" else teile)[i]
				z[s + "Hand" + f[0] + str(i + 1)] = s + f[1] + ziel
	return z


## Knochen von Mensch -> Kind, das seine Richtung angibt (fehlt = keine Richtungsanpassung).
static func richtungs_kind() -> Dictionary:
	var k := {"Spine": "Chest", "Chest": "UpperChest", "UpperChest": "Neck", "Neck": "Head"}
	for s in ["Left", "Right"]:
		k[s + "Shoulder"] = s + "UpperArm"
		k[s + "UpperArm"] = s + "LowerArm"
		k[s + "LowerArm"] = s + "Hand"
		k[s + "Hand"] = s + "MiddleProximal"
		k[s + "UpperLeg"] = s + "LowerLeg"
		k[s + "LowerLeg"] = s + "Foot"
		k[s + "Foot"] = s + "Toes"
		k[s + "ThumbMetacarpal"] = s + "ThumbProximal"
		k[s + "ThumbProximal"] = s + "ThumbDistal"
		for f in ["Index", "Middle", "Ring", "Little"]:
			k[s + f + "Proximal"] = s + f + "Intermediate"
			k[s + f + "Intermediate"] = s + f + "Distal"
	return k


func _init() -> void:
	_los.call_deferred()


func _los() -> void:
	var nur: PackedStringArray = []
	var args := OS.get_cmdline_user_args()
	if args.size() > 0 and not args[0].begins_with("--"):
		nur = args[0].split(",")
	var mensch: Mensch = Mensch.new()
	root.add_child(mensch)
	await process_frame
	var ziel: Skeleton3D = mensch.skelett
	var anzahl := 0
	for ordner in DirAccess.get_directories_at(ORDNER):
		if nur.size() > 0 and not ordner in nur:
			continue
		var lib := AnimationLibrary.new()
		for datei in DirAccess.get_files_at(ORDNER + ordner):
			if not datei.to_lower().ends_with(".fbx"):
				continue
			var a := umwandeln(ORDNER + ordner + "/" + datei, ziel)
			if a == null:
				continue
			var name := anim_name(datei)
			lib.add_animation(name, a)
			if OS.get_cmdline_user_args().has("--liste"):
				var w: Vector3 = a.get_meta("weg")
				print("  %-45s %5.2fs %s weg(%5.2f %5.2f %5.2f) treffer %.2f" % [name, a.length, "S" if a.loop_mode else " ", w.x, w.y, w.z, a.get_meta("treffer")])
			anzahl += 1
		var pfad := ORDNER + ordner + ".res"
		var fehler := ResourceSaver.save(lib, pfad, ResourceSaver.FLAG_COMPRESS)
		print("%s: %d Animationen -> %s (%s)" % [ordner, lib.get_animation_list().size(), pfad, error_string(fehler)])
	print("Fertig: %d Animationen" % anzahl)
	quit()


## "sword and shield slash (2).fbx" -> "sword_and_shield_slash_2"
static func anim_name(datei: String) -> String:
	var n := datei.get_basename().to_lower()
	for z in ["(", ")", ".", ",", ":", "[", "]", "/"]:
		n = n.replace(z, "")
	n = n.strip_edges().replace(" ", "_").replace("-", "_")
	while n.contains("__"):
		n = n.replace("__", "_")
	return n


static func _skelett(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var r := _skelett(c)
		if r:
			return r
	return null


static func umwandeln(pfad: String, ziel: Skeleton3D) -> Animation:
	var szene: Node = load(pfad).instantiate()
	var quelle := _skelett(szene)
	var ap: AnimationPlayer = szene.find_child("AnimationPlayer", true, false)
	if quelle == null or ap == null or ap.get_animation_list().is_empty():
		szene.free()
		return null
	var src: Animation = ap.get_animation(ap.get_animation_list()[0])
	var z := zuordnung()
	var rk := richtungs_kind()
	# Quelle: Knochen je Zielknochen
	var q_von := {}   # Zielknochen-Index -> Quellknochen-Index
	for i in quelle.get_bone_count():
		var n := quelle.get_bone_name(i).trim_prefix("mixamorig_").trim_prefix("mixamorig:")
		if z.has(n):
			var t := ziel.find_bone(z[n])
			if t >= 0:
				q_von[t] = i
	# Spuren der Quelle je Knochen
	var spur_rot := {}
	var spur_pos := {}
	for t in src.get_track_count():
		var b := quelle.find_bone(src.track_get_path(t).get_concatenated_subnames())
		if b < 0:
			continue
		if src.track_get_type(t) == Animation.TYPE_ROTATION_3D:
			spur_rot[b] = t
		elif src.track_get_type(t) == Animation.TYPE_POSITION_3D:
			spur_pos[b] = t
	# Ruhe in Weltkoordinaten
	var q_ruhe: Array[Transform3D] = []
	for i in quelle.get_bone_count():
		q_ruhe.append(quelle.get_bone_global_rest(i))
	var z_ruhe: Array[Quaternion] = []
	for b in ziel.get_bone_count():
		z_ruhe.append(ziel.get_bone_global_rest(b).basis.get_rotation_quaternion())
	# Richtungsanpassung je Zielknochen
	var korr: Array[Quaternion] = []
	for b in ziel.get_bone_count():
		var c := Quaternion.IDENTITY
		var name := ziel.get_bone_name(b)
		if rk.has(name) and q_von.has(b):
			var kind := ziel.find_bone(rk[name])
			if kind >= 0 and q_von.has(kind):
				var d_z := ziel.get_bone_global_rest(kind).origin - ziel.get_bone_global_rest(b).origin
				var d_q := q_ruhe[q_von[kind]].origin - q_ruhe[q_von[b]].origin
				if d_z.length() > 0.0001 and d_q.length() > 0.0001:
					c = Quaternion(d_z.normalized(), d_q.normalized())
		korr.append(c)
	var hips_q := quelle.find_bone("mixamorig_Hips")
	var hips_z := ziel.find_bone("Hips")
	var hoehe_q: float = q_ruhe[hips_q].origin.y
	# Bilder abtasten
	var bilder := maxi(1, int(round(src.length * BILDER_PRO_S)))
	var posen := []      # je Bild: Array[Quaternion] lokale Drehungen des Ziels
	var hueften: Array[Vector3] = []
	var haende: Array[Vector3] = []   # rechte Hand relativ zur Hüfte (für den Trefferzeitpunkt)
	var hand_q := quelle.find_bone("mixamorig_RightHand")
	for f in bilder + 1:
		var zeit := minf(f / BILDER_PRO_S, src.length)
		var g: Array[Transform3D] = []
		g.resize(quelle.get_bone_count())
		for i in quelle.get_bone_count():
			var lokal := quelle.get_bone_rest(i)
			if spur_rot.has(i):
				lokal.basis = Basis(src.rotation_track_interpolate(spur_rot[i], zeit))
			if spur_pos.has(i):
				lokal.origin = src.position_track_interpolate(spur_pos[i], zeit)
			var p := quelle.get_bone_parent(i)
			g[i] = g[p] * lokal if p >= 0 else lokal
		var welt: Array[Quaternion] = []
		welt.resize(ziel.get_bone_count())
		var lokal_z: Array[Quaternion] = []
		lokal_z.resize(ziel.get_bone_count())
		for b in ziel.get_bone_count():
			var w := z_ruhe[b]
			if q_von.has(b):
				var i: int = q_von[b]
				var delta := g[i].basis.get_rotation_quaternion() * q_ruhe[i].basis.get_rotation_quaternion().inverse()
				w = delta * korr[b] * z_ruhe[b]
			welt[b] = w.normalized()
			var p := ziel.get_bone_parent(b)
			lokal_z[b] = (welt[p].inverse() * welt[b]).normalized() if p >= 0 else welt[b]
		posen.append(lokal_z)
		hueften.append(g[hips_q].origin)
		haende.append(g[hand_q].origin - g[hips_q].origin if hand_q >= 0 else Vector3.ZERO)
	# Wanderung der Hüfte (vorn/seitlich) herausrechnen
	var anfang := hueften[0]
	var ende := hueften[hueften.size() - 1]
	var a := Animation.new()
	a.length = src.length
	a.step = 1.0 / BILDER_PRO_S
	var pt := a.add_track(Animation.TYPE_POSITION_3D)
	a.track_set_path(pt, NodePath("Skelett:Hips"))
	for f in hueften.size():
		var anteil := float(f) / maxf(1.0, hueften.size() - 1)
		var h := hueften[f] - Vector3(lerpf(anfang.x, ende.x, anteil), 0.0, lerpf(anfang.z, ende.z, anteil))
		a.position_track_insert_key(pt, minf(f / BILDER_PRO_S, src.length), h / hoehe_q)
	for b in ziel.get_bone_count():
		if ziel.get_bone_parent(b) < 0:
			continue
		var t := a.add_track(Animation.TYPE_ROTATION_3D)
		a.track_set_path(t, NodePath("Skelett:" + ziel.get_bone_name(b)))
		var vorher := Quaternion.IDENTITY
		for f in posen.size():
			var q: Quaternion = posen[f][b]
			if f > 0 and vorher.dot(q) < 0.0:
				q = -q
			vorher = q
			a.rotation_track_insert_key(t, minf(f / BILDER_PRO_S, src.length), q)
	var klein := pfad.get_file().to_lower()
	for w in SCHLEIFE:
		if klein.contains(w):
			a.loop_mode = Animation.LOOP_LINEAR
			break
	# Weg der Hüfte in m/s (Figur blickt nach +Z, +X = ihre linke Seite) und Trefferzeitpunkt
	# (Anteil der Länge, an dem die rechte Hand am schnellsten ist)
	a.set_meta("weg", (ende - anfang) / maxf(src.length, 0.01))
	var schnellste := 0.0
	var treffer := 0.5
	for f in range(1, haende.size()):
		var v := (haende[f] - haende[f - 1]).length()
		if v > schnellste:
			schnellste = v
			treffer = float(f) / maxf(1.0, haende.size() - 1)
	a.set_meta("treffer", treffer)
	a.optimize()
	szene.free()
	return a
