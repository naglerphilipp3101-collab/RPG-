@tool
class_name Baum
extends Node3D
## Fällbarer Baum. Art und Alter im Inspector wählen.
## faellen() aufrufen -> Baum verschwindet, Stumpf bleibt, nach respawn_zeit wächst er nach.

signal gefaellt(holz: String, menge: int)
signal nachgewachsen

enum Art { FICHTE, KIEFER, EICHE }
enum Alter { JUNG, ALT, URALT }
const ART_DATEI := ["fichte", "kiefer", "eiche"]
const ALTER_DATEI := ["jung", "alt", "uralt"]
const HOLZ := ["Frischholz", "Frischholz", "Gereiftes Holz"]
## Kollisionsradius des Stamms je Alter (inkl. Wurzelanlauf)
const STAMM_RADIUS := [0.13, 0.3, 0.55]

@export var art: Art = Art.FICHTE:
	set(v):
		art = v
		_aufbauen()
@export var alter: Alter = Alter.ALT:
	set(v):
		alter = v
		_aufbauen()
## Sekunden bis der Baum nachgewachsen ist
@export var respawn_zeit: float = 600.0
## 1–3 = feste Variante, 0 = automatisch (abhängig von der Position)
@export_range(0, 3) var variante: int = 0:
	set(v):
		variante = v
		_aufbauen()
## Holzmenge je Alter (jung, alt, uralt) – Platzhalter
@export var ertrag: Array[int] = [3, 8, 12]
## Zufällige Drehung und ±15 % Größe, abhängig von der Position (bleibt bei jedem Laden gleich)
@export var zufalls_variation: bool = true:
	set(v):
		zufalls_variation = v
		_aufbauen()

var ist_gefaellt := false
var _baum: Node3D
var _stumpf: Node3D
var _koerper: StaticBody3D
var _timer: Timer


func _ready() -> void:
	_aufbauen()


func faellen() -> int:
	if ist_gefaellt:
		return 0
	ist_gefaellt = true
	_setze_zustand()
	var menge: int = ertrag[alter]
	gefaellt.emit(HOLZ[alter], menge)
	_timer.start(respawn_zeit)
	return menge


func nachwachsen() -> void:
	ist_gefaellt = false
	_setze_zustand()
	nachgewachsen.emit()


func _setze_zustand() -> void:
	_baum.visible = not ist_gefaellt
	_stumpf.visible = ist_gefaellt


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	for n in [_baum, _stumpf, _koerper, _timer]:
		if is_instance_valid(n):
			n.queue_free()
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(global_position.round()))
	var v: int = variante if variante > 0 else rng.randi_range(1, 3)
	var art_name: String = ART_DATEI[art]
	if not ResourceLoader.exists(basis + "/modelle/%s_%s_1.glb" % [art_name, ALTER_DATEI[alter]]):
		push_warning("Baum: '%s' gibt es noch nicht, zeige Fichte." % art_name)
		art_name = "fichte"
	var mats := {"schnitt": load(basis + "/materialien/schnitt.tres")}
	for teil in ["rinde", "rinde_oben", "nadeln", "kern"]:
		var pfad := basis + "/materialien/%s_%s.tres" % [art_name, teil]
		if ResourceLoader.exists(pfad):
			mats[teil] = load(pfad)
	_baum = _modell(basis + "/modelle/%s_%s_%d.glb" % [art_name, ALTER_DATEI[alter], v], mats)
	_stumpf = _modell(basis + "/modelle/%s_stumpf_%s.glb" % [art_name, ALTER_DATEI[alter]], mats)

	if zufalls_variation:
		var drehung := rng.randf() * TAU
		var groesse := rng.randf_range(0.85, 1.15)
		for n in [_baum, _stumpf]:
			n.rotation.y = drehung
			n.scale = Vector3.ONE * groesse

	# Kollision nur am Stamm – durch die Krone kann man nicht hängen bleiben
	_koerper = StaticBody3D.new()
	var form := CollisionShape3D.new()
	var zyl := CylinderShape3D.new()
	zyl.radius = STAMM_RADIUS[alter]
	zyl.height = 3.0
	form.shape = zyl
	form.position.y = 1.5
	_koerper.add_child(form)
	add_child(_koerper)

	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(nachwachsen)
	add_child(_timer)
	_setze_zustand()


func _modell(pfad: String, mats: Dictionary) -> Node3D:
	var n := (load(pfad) as PackedScene).instantiate() as Node3D
	add_child(n)
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = (mi as MeshInstance3D).mesh
		for i in mesh.get_surface_count():
			var m := mesh.surface_get_material(i)
			if m and mats.has(m.resource_name):
				(mi as MeshInstance3D).set_surface_override_material(i, mats[m.resource_name])
	return n
