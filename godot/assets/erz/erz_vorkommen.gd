@tool
class_name ErzVorkommen
extends Node3D
## Ein abbaubares Erzvorkommen. Tier und Größe im Inspector wählen.
## abbauen() aufrufen -> Brocken verschwindet, Schutt erscheint, nach respawn_zeit kommt der Brocken zurück.

signal abgebaut(tier: Tier, menge: int)
signal nachgewachsen

enum Tier { IRON, PALLADIUM, MITHRIL, GLACIALORE, SUNGOLD, DARKSTEEL }
const TIER_DATEI := ["iron", "palladium", "mithril", "glacialore", "sungold", "darksteel"]
const MIT_KRISTALLEN := [Tier.GLACIALORE, Tier.DARKSTEEL]

@export var tier: Tier = Tier.IRON:
	set(v):
		tier = v
		_aufbauen()
@export_range(1, 5) var groesse: int = 3:
	set(v):
		groesse = v
		_aufbauen()
## Sekunden bis der Brocken wieder da ist
@export var respawn_zeit: float = 300.0
## Erz-Ausbeute je Größe 1..5 (Platzhalterwerte)
@export var ertrag: Array[int] = [2, 3, 5, 7, 10]

var ist_abgebaut := false
var _brocken: Node3D
var _kristalle: Node3D
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
	var menge: int = ertrag[groesse - 1]
	abgebaut.emit(tier, menge)
	_timer.start(respawn_zeit)
	return menge


func nachwachsen() -> void:
	ist_abgebaut = false
	_setze_zustand()
	nachgewachsen.emit()


func _setze_zustand() -> void:
	_brocken.visible = not ist_abgebaut
	if _kristalle:
		_kristalle.visible = not ist_abgebaut
	_schutt.visible = ist_abgebaut
	for c in _koerper.get_children():
		(c as CollisionShape3D).set_deferred("disabled", ist_abgebaut)


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	for n in [_brocken, _kristalle, _schutt, _koerper, _timer]:
		if is_instance_valid(n):
			n.queue_free()
	_kristalle = null
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var name_: String = TIER_DATEI[tier]

	_brocken = _modell(basis + "/modelle/erz_groesse_%d.glb" % groesse, basis + "/materialien/erz_%s.tres" % name_)
	if tier in MIT_KRISTALLEN:
		_kristalle = _modell(basis + "/modelle/kristalle_groesse_%d.glb" % groesse, basis + "/materialien/kristall_%s.tres" % name_)
	_schutt = _modell(basis + "/modelle/schutt.glb", basis + "/materialien/schutt_%s.tres" % name_)

	# Kollision aus der Brocken-Form (konvexe Hülle)
	_koerper = StaticBody3D.new()
	add_child(_koerper)
	var mesh_inst := _finde_mesh(_brocken)
	if mesh_inst:
		var form := CollisionShape3D.new()
		form.shape = mesh_inst.mesh.create_convex_shape(true, true)
		_koerper.add_child(form)

	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(nachwachsen)
	add_child(_timer)
	_setze_zustand()


func _modell(pfad: String, material_pfad: String) -> Node3D:
	var szene := load(pfad) as PackedScene
	var n := szene.instantiate() as Node3D
	add_child(n)
	var mat := load(material_pfad) as Material
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = mat
	return n


func _finde_mesh(n: Node) -> MeshInstance3D:
	var gefunden := n.find_children("*", "MeshInstance3D", true, false)
	return gefunden[0] if gefunden.size() > 0 else null
