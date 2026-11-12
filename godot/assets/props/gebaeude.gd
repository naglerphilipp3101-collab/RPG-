@tool
class_name Gebaeude
extends Node3D
## Ein Gebäude aus dem Gebäude-Baukasten (baukasten_editor/gebaeude_baukasten.html): lädt die gespeicherte
## JSON-Datei und setzt jedes Teil als Prop an seine Stelle. Vorläufer der Blueprints im Karten-Editor.
##
## Format (Version 1), alle Maße in Metern, Godot-Koordinaten (y oben, Vorderseite der Teile +z):
## { "format": "rpg_gebaeude", "version": 1, "name": "...", "raster": 1.0,
##   "teile": [ { "modell": "wand", "kaputt": false, "pos": [x, y, z], "dreh": [x, y, z] } ] }
## "dreh" sind Grad in Godots Reihenfolge YXZ (wie rotation_degrees).

const ORDNER := "res://data/gebaeude/"

## JSON-Datei des Gebäudes, z. B. res://data/gebaeude/beispiel_haus.json
@export_file("*.json") var datei: String = "":
	set(v):
		datei = v
		_aufbauen()
## Alle Teile kaputt zeigen (Ruine), unabhängig von der Datei
@export var alles_kaputt: bool = false:
	set(v):
		alles_kaputt = v
		_aufbauen()
@export var kollision: bool = true:
	set(v):
		kollision = v
		_aufbauen()

var daten: Dictionary = {}


func _ready() -> void:
	_aufbauen()


## Liest eine Gebäude-Datei. Leeres Dictionary, wenn sie fehlt oder kaputt ist.
static func laden(pfad: String) -> Dictionary:
	if not FileAccess.file_exists(pfad):
		push_warning("Gebaeude: Datei fehlt: " + pfad)
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(pfad))
	if not d is Dictionary or d.get("format", "") != "rpg_gebaeude":
		push_warning("Gebaeude: keine Gebäude-Datei: " + pfad)
		return {}
	return d


## Alle Gebäude-Dateien in data/gebaeude/
static func alle_dateien() -> PackedStringArray:
	var liste := PackedStringArray()
	for f in DirAccess.get_files_at(ORDNER):
		if f.ends_with(".json"):
			liste.append(ORDNER + f)
	return liste


## Baut ein Gebäude direkt aus Daten (z. B. später aus dem Karten-Editor)
func aus_daten(d: Dictionary) -> void:
	daten = d
	_teile_setzen()


func _aufbauen() -> void:
	if not is_inside_tree() or datei == "":
		return
	daten = laden(datei)
	_teile_setzen()


func _teile_setzen() -> void:
	for k in get_children():
		if k is Prop:
			k.queue_free()
	for t in daten.get("teile", []):
		var p := Prop.new()
		p.modell = str(t.get("modell", "wand"))
		p.kaputt = alles_kaputt or bool(t.get("kaputt", false))
		p.kollision = kollision
		var pos: Array = t.get("pos", [0, 0, 0])
		var dreh: Array = t.get("dreh", [0, 0, 0])
		p.position = Vector3(float(pos[0]), float(pos[1]), float(pos[2]))
		p.rotation_degrees = Vector3(float(dreh[0]), float(dreh[1]), float(dreh[2]))
		add_child(p)


## Größe des Gebäudes (Ursprünge der Teile), z. B. für die Kamera
func grenzen() -> AABB:
	var box := AABB()
	var erst := true
	for t in daten.get("teile", []):
		var pos: Array = t.get("pos", [0, 0, 0])
		var v := Vector3(float(pos[0]), float(pos[1]), float(pos[2]))
		if erst:
			box = AABB(v, Vector3.ZERO)
			erst = false
		else:
			box = box.expand(v)
	return box
