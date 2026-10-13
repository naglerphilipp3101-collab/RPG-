@tool
class_name Felsbrocken
extends Node3D
## Abbaubarer Stein ohne Erz (für Stein und Feuerstein). Nutzt die Brockenformen der Erzvorkommen
## mit dem Material stein.tres. abbauen() -> Brocken verschwindet, Schutt bleibt, nach respawn_zeit kommt er zurück.

signal abgebaut(menge: int)
signal nachgewachsen

@export_range(1, 5) var groesse: int = 2:
	set(v):
		groesse = v
		_aufbauen()
## Sekunden bis der Brocken wieder da ist
@export var respawn_zeit: float = 300.0
## Zufällige Drehung und ±15 % Größe, abhängig von der Position (bleibt bei jedem Laden gleich)
@export var zufalls_variation: bool = true

static var _formen := {}
var ist_abgebaut := false
var _brocken: Node3D
var _schutt: Node3D
var _koerper: StaticBody3D
var _timer: Timer


func _ready() -> void:
	_aufbauen()


func abbauen() -> int:
	if ist_abgebaut:
		return 0
	ist_abgebaut = true
	_setze_zustand()
	abgebaut.emit(groesse)
	_timer.start(respawn_zeit)
	return groesse


func nachwachsen() -> void:
	ist_abgebaut = false
	_setze_zustand()
	nachgewachsen.emit()


func _setze_zustand() -> void:
	_brocken.visible = not ist_abgebaut
	_schutt.visible = ist_abgebaut
	for c in _koerper.get_children():
		(c as CollisionShape3D).set_deferred("disabled", ist_abgebaut)


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	for n in [_brocken, _schutt, _koerper, _timer]:
		if is_instance_valid(n):
			n.queue_free()
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	_brocken = _modell(basis + "/modelle/erz_groesse_%d.glb" % groesse, basis + "/materialien/stein.tres")
	_schutt = _modell(basis + "/modelle/schutt.glb", basis + "/materialien/schutt_stein.tres")
	_schutt.scale = Vector3.ONE * (0.5 + 0.15 * groesse)
	if zufalls_variation:
		var rng := RandomNumberGenerator.new()
		rng.seed = hash(Vector3i(global_position.round()))
		_brocken.rotation.y = rng.randf() * TAU
		_brocken.scale = Vector3.ONE * rng.randf_range(0.85, 1.15)
		_schutt.rotation.y = _brocken.rotation.y
	# leicht eingesunken, damit er auf Hängen nicht schwebt
	_brocken.position.y = -0.06 * groesse
	_koerper = StaticBody3D.new()
	add_child(_koerper)
	var gefunden := _brocken.find_children("*", "MeshInstance3D", true, false)
	if gefunden.size() > 0:
		var form := CollisionShape3D.new()
		if not _formen.has(groesse): # Hülle je Größe nur einmal berechnen (teuer)
			_formen[groesse] = (gefunden[0] as MeshInstance3D).mesh.create_convex_shape(true, true)
		form.shape = _formen[groesse]
		form.transform = _brocken.transform
		_koerper.add_child(form)
	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(nachwachsen)
	add_child(_timer)
	_setze_zustand()


func _modell(pfad: String, material_pfad: String) -> Node3D:
	var n := (load(pfad) as PackedScene).instantiate() as Node3D
	add_child(n)
	var mat := load(material_pfad) as Material
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = mat
	return n
