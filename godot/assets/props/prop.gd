@tool
class_name Prop
extends Node3D
## Ein Prop aus assets/props/modelle (Blender-Skript blender/props.py bzw. blender/baukasten.py), heil oder kaputt.
## Die Modelle bringen nur Material-Namen mit (holz, eisen, stoff, ...). Hier werden dafür die Materialien
## aus materialien/<name>.tres eingesetzt; die lassen sich im Inspector anpassen und gelten für alle Props.
## Glut (Lagerfeuer, Kerzen) bekommt ein flackerndes Licht. Kollision: statischer Körper aus dem Modell.

const ORDNER := "res://assets/props/"
## Kleine Props bekommen eine konvexe Hülle (schnell), alle anderen die genaue Form (Zelt, Bogen, Mauer ...)
const KONVEX := ["kiste", "fass", "stuhl", "hocker", "tisch", "bank", "laterne"]

## Name des Modells ohne _kaputt, z. B. "kiste", "zelt", "wand_fenster"
@export var modell: String = "kiste":
	set(v):
		modell = v
		_aufbauen()
@export var kaputt: bool = false:
	set(v):
		kaputt = v
		_aufbauen()
@export var kollision: bool = true:
	set(v):
		kollision = v
		_aufbauen()
## Licht an Glut und Kerzen (nur bei heilen Modellen)
@export var licht: bool = true:
	set(v):
		licht = v
		_aufbauen()

static var _materialien := {}
static var _formen := {}
var _inhalt: Node3D
var _lichter: Array[OmniLight3D] = []
var _zeit := 0.0


func _ready() -> void:
	_aufbauen()


## Alle verfügbaren Modelle (ohne _kaputt), alphabetisch
static func alle_modelle() -> PackedStringArray:
	var namen := PackedStringArray()
	for datei in DirAccess.get_files_at(ORDNER + "modelle"):
		datei = datei.trim_suffix(".remap").trim_suffix(".import")
		if datei.ends_with(".glb") and not datei.ends_with("_kaputt.glb") and not namen.has(datei.get_basename()):
			namen.append(datei.get_basename())
	namen.sort()
	return namen


static func material(name: String) -> Material:
	if not _materialien.has(name):
		var pfad := ORDNER + "materialien/" + name + ".tres"
		_materialien[name] = load(pfad) if ResourceLoader.exists(pfad) else null
	return _materialien[name]


func _aufbauen() -> void:
	if not is_inside_tree():
		return
	if is_instance_valid(_inhalt):
		_inhalt.queue_free()
	_lichter.clear()
	var pfad := ORDNER + "modelle/" + modell + ("_kaputt" if kaputt else "") + ".glb"
	if not ResourceLoader.exists(pfad):
		push_warning("Prop: Modell fehlt: " + pfad)
		return
	_inhalt = Node3D.new()
	add_child(_inhalt)
	var szene := (load(pfad) as PackedScene).instantiate() as Node3D
	_inhalt.add_child(szene)
	var meshes := szene.find_children("*", "MeshInstance3D", true, false)
	for n in meshes:
		var mi := n as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var alt := mi.mesh.surface_get_material(i)
			var name := alt.resource_name if alt else ""
			var neu := material(name)
			if neu:
				mi.set_surface_override_material(i, neu)
			if name == "glut" and licht and not kaputt:
				_licht_an_glut(mi, i)
	if kollision and meshes.size() > 0:
		var koerper := StaticBody3D.new()
		_inhalt.add_child(koerper)
		var form := CollisionShape3D.new()
		var mesh := (meshes[0] as MeshInstance3D).mesh
		if not _formen.has(pfad):
			_formen[pfad] = mesh.create_convex_shape(true, true) if modell in KONVEX else mesh.create_trimesh_shape()
		form.shape = _formen[pfad]
		form.transform = (meshes[0] as MeshInstance3D).transform
		koerper.add_child(form)


func _licht_an_glut(mi: MeshInstance3D, flaeche: int) -> void:
	var arrays := mi.mesh.surface_get_arrays(flaeche)
	var punkte: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	if punkte.is_empty():
		return
	var mitte := Vector3.ZERO
	for p in punkte:
		mitte += p
	mitte /= punkte.size()
	var l := OmniLight3D.new()
	var gross := modell == "lagerfeuer"
	l.light_color = Color(1.0, 0.55, 0.22)
	l.light_energy = 2.2 if gross else 0.6
	l.omni_range = 9.0 if gross else 3.5
	l.shadow_enabled = gross
	l.position = mi.transform * mitte + Vector3(0, 1.0 if gross else 0.02, 0)
	_inhalt.add_child(l)
	_lichter.append(l)
	set_process(true)


func _process(delta: float) -> void:
	if _lichter.is_empty() or Engine.is_editor_hint():
		return
	_zeit += delta
	for i in _lichter.size():
		var l := _lichter[i]
		var basis := 2.2 if modell == "lagerfeuer" else 0.6
		l.light_energy = basis * (0.85 + 0.1 * sin(_zeit * 11.0 + i) + 0.05 * sin(_zeit * 23.0 + i * 2.0))
