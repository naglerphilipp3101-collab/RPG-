extends StaticBody3D
## Platzhalter-NPC (bis es NPC-Modelle gibt): Figur aus Grundformen, Name darüber und ein Zeichen für Quests.
## „!“ = hat eine neue Quest, „?“ = Quest kann abgegeben werden, „…“ = will etwas sagen (Gesprächsziel).
## Werte aus data/npcs.json; Sichtbarkeit und Zeichen setzt scripts/quest_welt.gd.

const MeshUtil := preload("res://scripts/mesh_util.gd")

var npc_id := ""
var def: Dictionary = {}
var interact_radius := 2.6
var sichtbar := true
var _zeichen: Label3D
var _koerper: Node3D


func setup(id: String) -> void:
	npc_id = id
	def = Game.npcs.get(id, {})


func _ready() -> void:
	add_to_group("interactable")
	add_to_group("npc")
	collision_layer = 1
	collision_mask = 0
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.8
	var col := CollisionShape3D.new()
	col.shape = capsule
	col.position.y = 0.9
	add_child(col)
	_build_model()

	var name_label := Label3D.new()
	name_label.text = "%s\n%s" % [String(def.get("name", npc_id)), String(def.get("titel", ""))]
	name_label.position.y = 2.25
	name_label.font_size = 40
	name_label.outline_size = 10
	name_label.pixel_size = 0.005
	name_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	name_label.modulate = Color(0.9, 0.95, 1.0)
	add_child(name_label)
	_zeichen = Label3D.new()
	_zeichen.position.y = 2.75
	_zeichen.font_size = 110
	_zeichen.outline_size = 18
	_zeichen.pixel_size = 0.006
	_zeichen.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(_zeichen)


## zeichen: "", "!", "?" oder "…"
func zeichen_setzen(zeichen: String) -> void:
	if _zeichen == null:
		return
	_zeichen.text = zeichen
	_zeichen.modulate = {"!": Color(1.0, 0.85, 0.2), "?": Color(1.0, 0.75, 0.1), "…": Color(0.6, 0.85, 1.0)}.get(zeichen, Color.WHITE)


func sichtbar_setzen(an: bool) -> void:
	if an == sichtbar:
		return
	sichtbar = an
	visible = an
	collision_layer = 1 if an else 0


# --- Schnittstelle für den Spieler (wie Werkstätten) -----------------------

func get_npc_id() -> String:
	return npc_id


func is_interactable() -> bool:
	return sichtbar


func is_fishing() -> bool:
	return false


func get_prompt() -> String:
	return "Mit %s reden" % String(def.get("name", npc_id))


func get_profession() -> String:
	return ""


func get_required_level() -> int:
	return 0


# --- Modell ---------------------------------------------------------------

func _build_model() -> void:
	_koerper = Node3D.new()
	add_child(_koerper)
	var f: Array = def.get("farbe", [0.5, 0.5, 0.5])
	var farbe := Color(float(f[0]), float(f[1]), float(f[2]))
	var geist := bool(def.get("geist", false))
	var stoff := MeshUtil.mat(farbe)
	var haut := MeshUtil.mat(Color(0.85, 0.68, 0.55))
	if geist:
		for m: StandardMaterial3D in [stoff, haut]:
			m.albedo_color = Color(farbe, 0.45)
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.emission_enabled = true
			m.emission = farbe
			m.emission_energy_multiplier = 1.5
	var rumpf := CapsuleMesh.new()
	rumpf.radius = 0.3
	rumpf.height = 1.35
	MeshUtil.part(_koerper, rumpf, stoff, Vector3(0, 0.75, 0))
	var kopf := SphereMesh.new()
	kopf.radius = 0.17
	kopf.height = 0.34
	MeshUtil.part(_koerper, kopf, haut, Vector3(0, 1.62, 0))
	# Nase zeigt die Blickrichtung
	MeshUtil.part(_koerper, MeshUtil.box(Vector3(0.05, 0.06, 0.08)), haut, Vector3(0, 1.6, -0.18))
	if geist:
		var licht := OmniLight3D.new()
		licht.light_color = farbe
		licht.light_energy = 1.2
		licht.omni_range = 5.0
		licht.position.y = 1.2
		_koerper.add_child(licht)
