@tool
class_name AesteBusch
extends Node3D
## ~1 m hoher Busch, der nur Äste gibt. ernten() -> Busch wird zu Stummeln, wächst nach respawn_zeit nach.
## Keine Kollision: man läuft hindurch. Für die Interaktion einen Area3D-Bereich (wird automatisch angelegt).

signal geerntet(menge: int)
signal nachgewachsen

## Sekunden bis zum Nachwachsen
@export var respawn_zeit: float = 300.0
## Anzahl Äste pro Ernte – Platzhalter
@export var ertrag: int = 2
## 1–3 = feste Form, 0 = automatisch (abhängig von der Position)
@export_range(0, 3) var variante: int = 0:
	set(v):
		variante = v
		_aufbauen()
## Zufällige Drehung + Größe (0,8–1,2), abhängig von der Position
@export var zufalls_variation: bool = true:
	set(v):
		zufalls_variation = v
		_aufbauen()

var ist_geerntet := false
var _busch: Node3D
var _stummel: Node3D
var _bereich: Area3D
var _timer: Timer


func _ready() -> void:
	_aufbauen()


func ernten() -> int:
	if ist_geerntet:
		return 0
	ist_geerntet = true
	_setze_zustand()
	geerntet.emit(ertrag)
	_timer.start(respawn_zeit)
	return ertrag


func nachwachsen() -> void:
	ist_geerntet = false
	_setze_zustand()
	nachgewachsen.emit()


func _setze_zustand() -> void:
	_busch.visible = not ist_geerntet
	_stummel.visible = ist_geerntet


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	for n in [_busch, _stummel, _bereich, _timer]:
		if is_instance_valid(n):
			n.queue_free()
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(global_position.round()))
	var v: int = variante if variante > 0 else rng.randi_range(1, 3)
	var mats := {"rinde": load(basis + "/materialien/busch_rinde.tres"),
				 "nadeln": load(basis + "/materialien/busch_nadeln.tres")}
	_busch = _modell(basis + "/modelle/busch_%d.glb" % v, mats)
	_stummel = _modell(basis + "/modelle/busch_geerntet.glb", mats)
	if zufalls_variation:
		var drehung := rng.randf() * TAU
		var groesse := rng.randf_range(0.8, 1.2)
		for n in [_busch, _stummel]:
			n.rotation.y = drehung
			n.scale = Vector3.ONE * groesse
	# Interaktionsbereich (Raycast/Area des Spielers trifft diesen), blockiert aber nicht
	_bereich = Area3D.new()
	var form := CollisionShape3D.new()
	var zyl := CylinderShape3D.new()
	zyl.radius = 0.45
	zyl.height = 1.1
	form.shape = zyl
	form.position.y = 0.55
	_bereich.add_child(form)
	add_child(_bereich)
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
