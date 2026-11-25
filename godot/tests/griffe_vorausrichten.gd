extends SceneTree
## Richtet die Griffe der Waffen (data/griffe.json) nach den Mixamo-Posen aus: bei Zweihändern zeigt die Waffe von der
## rechten zur linken Hand, die linke Hand greift dort, wo sie in der Pose liegt. Stäbe werden in der Mitte gefasst.
## Start: Godot --headless --path godot -s res://tests/griffe_vorausrichten.gd [-- --nur greatsword,spear]
## Vorhandene Einträge in griffe.json werden überschrieben (Philipps Einstellungen aus der Werkstatt also vorher sichern).

const WeaponModels := preload("res://scripts/weapon_models.gd")

# Waffe -> Art der Ausrichtung, Pose (Satz-Schlüssel), Lage der rechten Hand
#   "zweihand": +Z (Knauf/Ende) zeigt von der rechten zur linken Hand, rechte Hand bei Anteil `rechts` der Länge ab Spitze
#   "gewehr":   -Z (Mündung/Spitze) zeigt von der rechten zur linken Hand, oben = Welt-oben
#   "stab":     einhändig, Lage bleibt, Hand bei Anteil `rechts` ab Spitze
const REGELN := {
	"greatsword": {"art": "zweihand", "pose": "ruhe", "rechts": -1.0},
	"hammer": {"art": "zweihand", "pose": "ruhe", "rechts": 0.55},
	"axe": {"art": "zweihand", "pose": "ruhe", "rechts": 0.55},
	"spear": {"art": "gewehr", "pose": "ruhe", "rechts": 0.72},
	"musket": {"art": "gewehr", "pose": "zielen", "rechts": -1.0},
	"crossbow": {"art": "gewehr", "pose": "zielen", "rechts": -1.0},
	"fire_magic": {"art": "stab", "rechts": 0.45},
	"ice_magic": {"art": "stab", "rechts": 0.45},
	"lightning_magic": {"art": "stab", "rechts": 0.45},
	"life_magic": {"art": "stab", "rechts": 0.45},
}


func _init() -> void:
	call_deferred("_los")


func _los() -> void:
	var nur: PackedStringArray = []
	var args := OS.get_cmdline_user_args()
	var i := args.find("--nur")
	if i >= 0 and i + 1 < args.size():
		nur = args[i + 1].split(",")
	var waffen: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/weapons.json"))
	waffen = waffen.get("weapons", waffen)
	var m := Mensch.new()
	root.add_child(m)
	await process_frame
	var fig := SpielerAnimation.new(m)
	m.add_child(fig)
	await process_frame
	var sk := m.skelett
	var ergebnis: Dictionary = SpielerAnimation.griffe().duplicate(true)
	# Bogen links (Wurfarme senkrecht durch die Faust, Sehne zum Körper), Leerenhandschuh auf der Hand
	if nur.is_empty() or nur.has("bow"):
		ergebnis["bow"] = {"hand": "links", "pos": [0.0, -0.28, 0.0], "rot": [90.0, 0.0, 0.0]}
	if nur.is_empty() or nur.has("void_magic"):
		# Handschuh (nach der Drehung in build_gear): Unterarm +Z, Knöchel -Z, Griffachse X, Handrücken +Y.
		# Im Griff der Hand: Finger +Y, Griffachse Z, Handrücken +X
		var b := Basis(Vector3(0, 0, -1), Vector3(1, 0, 0), Vector3(0, -1, 0))
		ergebnis["void_magic"] = {"hand": "rechts", "pos": [0.0, 0.0, 0.0], "rot": _grad(b)}
	var rechts_griff := SpielerAnimation.griff_transform(sk, false)
	var links_griff := SpielerAnimation.griff_transform(sk, true)
	var hand_r := sk.find_bone("RightHand")
	var hand_l := sk.find_bone("LeftHand")
	for typ in REGELN:
		if not nur.is_empty() and not nur.has(typ):
			continue
		var regel: Dictionary = REGELN[typ]
		var def: Dictionary = waffen[typ]
		var laenge := _ausdehnung(def)     # [z_spitze (min), z_ende (max)]
		var art: String = regel["art"]
		var basis := Basis()
		var zweite: Variant = null
		var punkt := 0.0 # Lage der rechten Hand entlang Z im Raum der Waffe
		if float(regel["rechts"]) >= 0.0:
			punkt = lerpf(laenge.x, laenge.y, float(regel["rechts"]))
		if art != "stab":
			fig.waffe_setzen(typ)
			var n = fig.satz.get(regel["pose"], "")
			if n is Array:
				n = n[0]
			if n == "":
				print("ohne Pose (Mixamo fehlt?): ", typ)
				continue
			# Bild, in dem beide Hände am nächsten beieinander sind (Pose und Schläge der Waffe)
			var kandidaten := [n]
			for k in fig.satz.get("schlaege", {}).values():
				kandidaten.append(k[0] if k is Array else k)
			var r_welt := Transform3D()
			var l := Vector3(9, 9, 9)
			var beste := ""
			for kn in kandidaten:
				var anim := fig.ap.get_animation(SpielerAnimation._voll(kn))
				fig.ap.play(SpielerAnimation._voll(kn))
				var t := 0.0
				while t <= anim.length:
					fig.ap.seek(t, true)
					await process_frame
					# Griffpunkte in Weltkoordinaten -> Raum des rechten Griffs
					var rw := sk.global_transform * sk.get_bone_global_pose(hand_r) * rechts_griff
					var lw := sk.global_transform * sk.get_bone_global_pose(hand_l) * links_griff
					var lv := rw.affine_inverse() * lw.origin
					if lv.length() < l.length():
						l = lv
						r_welt = rw
						beste = "%s bei %.1f s" % [kn, t]
					t += 0.1
			print("  ", typ, ": ", beste)
			var a := l.normalized()
			if art == "zweihand":
				var x := (Vector3.RIGHT - a * a.dot(Vector3.RIGHT)).normalized()
				basis = Basis(x, a.cross(x), a)
			else:
				var oben := r_welt.basis.inverse() * Vector3.UP
				var z := -a
				var y := (oben - z * z.dot(oben)).normalized()
				basis = Basis(y.cross(z), y, z)
			var pos := -(basis * Vector3(0, 0, punkt))
			zweite = basis.inverse() * (l - pos)
			ergebnis[typ] = {"hand": "rechts", "pos": _liste(pos), "rot": _grad(basis), "zweite": _liste(zweite)}
			print("%-16s Abstand der Hände %.2f m, Waffe %.2f … %.2f, rechte Hand bei %.2f" % [typ, l.length(), laenge.x, laenge.y, punkt])
		else:
			ergebnis[typ] = {"hand": "rechts", "pos": _liste(Vector3(0, 0, -punkt)), "rot": [0.0, 0.0, 0.0]}
			print("%-16s Stab %.2f … %.2f, Hand bei %.2f" % [typ, laenge.x, laenge.y, punkt])
	print("gespeichert: ", SpielerAnimation.griffe_speichern(ergebnis))
	quit()


## Ausdehnung des Modells entlang Z (x = Spitze, y = Ende).
func _ausdehnung(def: Dictionary) -> Vector2:
	var halter := Node3D.new()
	root.add_child(halter)
	if not WeaponModels.build_gear(def, {}, 1, halter):
		WeaponModels.build(def.get("model", "sword"), halter)
	var lo := INF
	var hi := -INF
	for mi in halter.find_children("*", "MeshInstance3D", true, false):
		var t: Transform3D = halter.global_transform.affine_inverse() * (mi as MeshInstance3D).global_transform
		var b: AABB = t * (mi as MeshInstance3D).get_aabb()
		lo = minf(lo, b.position.z)
		hi = maxf(hi, b.end.z)
	halter.free()
	return Vector2(lo, hi)


func _liste(v: Vector3) -> Array:
	return [snappedf(v.x, 0.0001), snappedf(v.y, 0.0001), snappedf(v.z, 0.0001)]


func _grad(b: Basis) -> Array:
	var e := b.orthonormalized().get_euler() * (180.0 / PI)
	return [snappedf(e.x, 0.01), snappedf(e.y, 0.01), snappedf(e.z, 0.01)]
