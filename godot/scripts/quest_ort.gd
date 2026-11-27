extends Node3D
## Stelle, die man für eine Quest untersuchen kann (Ziel-Art „untersuchen“). Nur aktiv, solange eine
## laufende Quest sie braucht; dann schimmert sie und F untersucht sie. Gesteuert von scripts/quest_welt.gd.

var ort_id := ""
var def: Dictionary = {}
var interact_radius := 2.5
var aktiv := false
var _schimmer: MeshInstance3D
var _licht: OmniLight3D
var _zeit := 0.0


func setup(id: String) -> void:
	ort_id = id
	def = Game.quest_orte.get(id, {})
	interact_radius = maxf(float(def.get("radius", 2.5)), 1.5)


func _ready() -> void:
	add_to_group("interactable")
	add_to_group("quest_ort")
	var kugel := SphereMesh.new()
	kugel.radius = 0.18
	kugel.height = 0.36
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.85, 0.4, 0.8)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.8, 0.3)
	mat.emission_energy_multiplier = 3.0
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_schimmer = MeshInstance3D.new()
	_schimmer.mesh = kugel
	_schimmer.material_override = mat
	_schimmer.position.y = 0.6
	add_child(_schimmer)
	_licht = OmniLight3D.new()
	_licht.light_color = Color(1.0, 0.8, 0.4)
	_licht.light_energy = 0.8
	_licht.omni_range = 3.0
	_licht.position.y = 0.8
	add_child(_licht)
	aktiv_setzen(false, true)


func aktiv_setzen(an: bool, erzwingen := false) -> void:
	if an == aktiv and not erzwingen:
		return
	aktiv = an
	_schimmer.visible = an
	_licht.visible = an


func _process(delta: float) -> void:
	if aktiv:
		_zeit += delta
		_schimmer.position.y = 0.6 + sin(_zeit * 2.5) * 0.1
		_schimmer.scale = Vector3.ONE * (1.0 + sin(_zeit * 4.0) * 0.15)


# --- Schnittstelle für den Spieler ------------------------------------------

func get_ort_id() -> String:
	return ort_id


func get_prompt_titel() -> String:
	return String(def.get("name", ort_id))


func is_interactable() -> bool:
	return aktiv


func is_fishing() -> bool:
	return false


func get_prompt() -> String:
	return "Untersuchen: %s" % get_prompt_titel()


func get_profession() -> String:
	return ""


func get_required_level() -> int:
	return 0
