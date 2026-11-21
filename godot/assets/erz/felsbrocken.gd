@tool
class_name Felsbrocken
extends Node3D
## Abbaubarer Stein ohne Erz: Stein oder Feuerstein in 5 Größen und 7 Varianten (Modelle aus blender/steine.py:
## Icosphere mit 9 Noise-Schichten). Material: Felstextur triplanar (scripts/fels_triplanar.gdshader), der Fotoscan
## aus assets/welt/texturen_scan/, wenn er umgewandelt wurde, sonst die eigene Felstextur.
## abbauen() -> Brocken verschwindet, Schutt bleibt, nach respawn_zeit kommt er zurück.

signal abgebaut(menge: int)
signal nachgewachsen

const VARIANTEN := ["rund", "kantig", "plattig", "gespalten", "hoch", "liegend", "zerklüftet"]

@export_range(1, 5) var groesse: int = 2:
	set(v):
		groesse = v
		_aufbauen()
## 1–7 (siehe VARIANTEN), 0 = nach der Position
@export_range(0, 7) var variante: int = 0:
	set(v):
		variante = v
		_aufbauen()
@export_enum("Stein", "Feuerstein") var art: int = 0:
	set(v):
		art = v
		_aufbauen()
## Sekunden bis der Brocken wieder da ist
@export var respawn_zeit: float = 300.0
## Zufällige Drehung und ±15 % Größe, abhängig von der Position (bleibt bei jedem Laden gleich)
@export var zufalls_variation: bool = true

static var _formen := {}
static var _materialien := {}
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
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(global_position.round()))
	var v := variante if variante > 0 else rng.randi_range(1, 7)
	var pfad := basis + "/modelle/stein_%d_%d.glb" % [groesse, v]
	_brocken = (load(pfad) as PackedScene).instantiate() as Node3D
	add_child(_brocken)
	var gefunden := _brocken.find_children("*", "MeshInstance3D", true, false)
	for mi in gefunden:
		(mi as MeshInstance3D).material_override = material(art)
	if zufalls_variation:
		_brocken.rotation.y = rng.randf() * TAU
		_brocken.scale = Vector3.ONE * rng.randf_range(0.85, 1.15)
	_brocken.position.y = -0.04 - 0.04 * groesse # leicht eingesunken, damit er auf Hängen nicht schwebt
	_schutt = (load(basis + "/modelle/schutt.glb") as PackedScene).instantiate() as Node3D
	add_child(_schutt)
	var schutt_mat := load(basis + "/materialien/schutt_stein.tres") as Material
	for mi in _schutt.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = schutt_mat
	_schutt.scale = Vector3.ONE * (0.35 + 0.17 * groesse)
	_schutt.rotation.y = _brocken.rotation.y
	_koerper = StaticBody3D.new()
	add_child(_koerper)
	if gefunden.size() > 0:
		var form := CollisionShape3D.new()
		if not _formen.has(pfad): # Hülle je Modell nur einmal berechnen (teuer)
			_formen[pfad] = (gefunden[0] as MeshInstance3D).mesh.create_convex_shape(true, true)
		form.shape = _formen[pfad]
		form.transform = _brocken.transform
		_koerper.add_child(form)
	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(nachwachsen)
	add_child(_timer)
	_setze_zustand()


## Gemeinsames Material je Art (0 Stein, 1 Feuerstein)
static func material(a: int) -> Material:
	if _materialien.has(a):
		return _materialien[a]
	var ordner := "res://assets/welt/texturen_scan/"
	if not ResourceLoader.exists(ordner + "fels_albedo_hoehe.png"):
		ordner = "res://assets/welt/texturen/"
	var mat := ShaderMaterial.new()
	mat.shader = preload("res://scripts/fels_triplanar.gdshader")
	mat.set_shader_parameter("farbe", load(ordner + "fels_albedo_hoehe.png"))
	mat.set_shader_parameter("normale", load(ordner + "fels_normal_rauheit.png"))
	if a == 1: # Feuerstein: dunkel, bräunlich, glatter, ohne Moos
		mat.set_shader_parameter("ton", Color(0.42, 0.38, 0.36))
		mat.set_shader_parameter("glanz", 0.45)
		mat.set_shader_parameter("moos", 0.0)
		mat.set_shader_parameter("groesse", 1.2)
	_materialien[a] = mat
	return mat
