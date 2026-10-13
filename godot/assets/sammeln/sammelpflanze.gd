@tool
class_name Sammelpflanze
extends Node3D
## Sammelbare Pflanze: Hanf, Beerenstrauch, Kraut. sammeln() -> Pflanze wird abgeerntet, wächst nach respawn_zeit nach.
## Keine Kollision (man läuft hindurch), dafür ein Area3D-Bereich für die Interaktion.
## Was gedroppt wird steht in `drop` – so kann dieselbe Pflanze je nach Region etwas anderes geben.

signal gesammelt(drop: String, menge: int)
signal nachgewachsen

enum Art { HANF, BEEREN, KRAEUTER }
const ART_DATEI := ["hanf", "beeren", "kraut"]
## Beeren: rot, blau, schwarz, gelb · Kräuter: weiß, gelb, lila, rot · Hanf: ohne Bedeutung
enum Farbe { ROT, BLAU, SCHWARZ, GELB, WEISS, LILA }
const FARB_DATEI := ["rot", "blau", "schwarz", "gelb", "weiss", "lila"]
const FARB_NAME := ["rot", "blau", "schwarz", "gelb", "weiß", "lila"]
## Höhe des Interaktionsbereichs je Art
const BEREICH_HOEHE := [1.6, 1.0, 0.6]

@export var art: Art = Art.HANF:
	set(v):
		art = v
		_aufbauen()
@export var farbe: Farbe = Farbe.ROT:
	set(v):
		farbe = v
		_aufbauen()
## Was der Spieler bekommt. Leer = Standard ("Hanf", "Beeren (rot)", "Kraut (weiß)" …). Für regionale Drops hier überschreiben.
@export var drop: String = ""
## Menge pro Ernte – Platzhalter
@export var ertrag: int = 3
## Sekunden bis zum Nachwachsen
@export var respawn_zeit: float = 300.0
## 1–3 = feste Form, 0 = automatisch (abhängig von der Position)
@export_range(0, 3) var variante: int = 0:
	set(v):
		variante = v
		_aufbauen()
## Zufällige Drehung + Größe (0,85–1,15), abhängig von der Position
@export var zufalls_variation: bool = true:
	set(v):
		zufalls_variation = v
		_aufbauen()

var ist_geerntet := false
var _pflanze: Node3D
var _rest: Node3D      # geernteter Zustand (Hanf, Kraut)
var _frucht: Node3D    # Beeren: verschwinden beim Ernten
var _bereich: Area3D
var _timer: Timer


func _ready() -> void:
	_aufbauen()


func sammeln() -> int:
	if ist_geerntet:
		return 0
	ist_geerntet = true
	_setze_zustand()
	gesammelt.emit(drop_name(), ertrag)
	_timer.start(respawn_zeit)
	return ertrag


func drop_name() -> String:
	if drop != "":
		return drop
	match art:
		Art.BEEREN:
			return "Beeren (%s)" % FARB_NAME[farbe]
		Art.KRAEUTER:
			return "Kraut (%s)" % FARB_NAME[farbe]
	return "Hanf"


func nachwachsen() -> void:
	ist_geerntet = false
	_setze_zustand()
	nachgewachsen.emit()


func _setze_zustand() -> void:
	_pflanze.visible = not ist_geerntet or _frucht != null
	if _rest:
		_rest.visible = ist_geerntet
	if _frucht:
		_frucht.visible = not ist_geerntet


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	for n in [_pflanze, _rest, _frucht, _bereich, _timer]:
		if is_instance_valid(n):
			n.queue_free()
	_rest = null
	_frucht = null
	var basis: String = (get_script() as Script).resource_path.get_base_dir()
	var name_: String = ART_DATEI[art]
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(global_position.round()))
	var v: int = variante if variante > 0 else rng.randi_range(1, 3)
	var mats := {}
	for teil in ["rinde", "nadeln", "bluete"]:
		var pfad := basis + "/materialien/%s_%s.tres" % [name_, teil]
		if ResourceLoader.exists(pfad):
			mats[teil] = load(pfad)
	# Farbe: Beeren-Material (Slot "kern") bzw. Blüten-Material (Slot "bluete")
	var f: String = FARB_DATEI[farbe]
	if art == Art.BEEREN:
		mats["kern"] = _lade_farbe(basis + "/materialien/beeren_%s.tres", f, ["rot", "blau", "schwarz", "gelb"])
	elif art == Art.KRAEUTER:
		mats["bluete"] = _lade_farbe(basis + "/materialien/kraut_bluete_%s.tres", f, ["weiss", "gelb", "lila", "rot"])
	_pflanze = _modell(basis + "/modelle/%s_%d.glb" % [name_, v], mats)
	var teile: Array = [_pflanze]
	if ResourceLoader.exists(basis + "/modelle/%s_geerntet.glb" % name_):
		_rest = _modell(basis + "/modelle/%s_geerntet.glb" % name_, mats)
		teile.append(_rest)
	if ResourceLoader.exists(basis + "/modelle/%s_frucht_%d.glb" % [name_, v]):
		_frucht = _modell(basis + "/modelle/%s_frucht_%d.glb" % [name_, v], mats)
		teile.append(_frucht)
	if zufalls_variation:
		var drehung := rng.randf() * TAU
		var groesse := rng.randf_range(0.85, 1.15)
		for n in teile:
			n.rotation.y = drehung
			n.scale = Vector3.ONE * groesse
	_bereich = Area3D.new()
	var form := CollisionShape3D.new()
	var zyl := CylinderShape3D.new()
	zyl.radius = 0.4
	zyl.height = BEREICH_HOEHE[art]
	form.shape = zyl
	form.position.y = BEREICH_HOEHE[art] / 2.0
	_bereich.add_child(form)
	add_child(_bereich)
	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(nachwachsen)
	add_child(_timer)
	_setze_zustand()


func _lade_farbe(muster: String, f: String, erlaubt: Array) -> Material:
	if not f in erlaubt:
		push_warning("Sammelpflanze: Farbe '%s' gibt es hier nicht, nehme '%s'." % [f, erlaubt[0]])
		f = erlaubt[0]
	return load(muster % f)


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
