class_name WeltRessourcen
extends Node3D
## Spawnt die Ressourcen aus ressourcen.json (Bäume, Äste-Büsche, Erze, Sammelpflanzen) nur im Umkreis
## des Spielers und entfernt sie wieder, wenn er sich entfernt. So bleiben auch ~70.000 Objekte flüssig.
##
## Benötigt die Asset-Pakete aus dem Chat (Erze, Bäume, Sammeln). Pfade unten anpassen, falls sie woanders liegen.
## Fehlt ein Paket, wird diese Ressourcen-Art einfach übersprungen.

## Der Weltknoten (welt.tscn) – liefert die Bodenhöhe
@export var welt: WeltImport
## Spieler bzw. Kamera, um den herum geladen wird
@export var ziel: Node3D
## Lade-Radius in Metern
@export var radius: float = 220.0
## Maximal neu erzeugte Objekte pro Frame (verhindert Ruckler)
@export var pro_frame: int = 150
@export_group("Szenen")
@export_file("*.tscn") var baum_szene: String = "res://assets/baeume/baum.tscn"
@export_file("*.tscn") var busch_szene: String = "res://assets/baeume/aeste_busch.tscn"
@export_file("*.tscn") var erz_szene: String = "res://assets/erz/erz_vorkommen.tscn"
@export_file("*.tscn") var pflanze_szene: String = "res://assets/sammeln/sammelpflanze.tscn"

const CHUNK := 64.0
var _chunks := {}          # Vector2i -> Array von Einträgen [art, daten]
var _geladen := {}         # Vector2i -> Node3D
var _warteschlange: Array = []
var _szenen := {}
var _bereit := false


func _ready() -> void:
	if welt == null:
		welt = get_parent() as WeltImport
	var pfad := welt.daten_ordner.path_join("ressourcen.json") if welt else ""
	if pfad == "" or not FileAccess.file_exists(pfad):
		push_warning("WeltRessourcen: ressourcen.json nicht gefunden – im Editor 'Ressourcen verteilen' und neu exportieren.")
		return
	var r: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(pfad))
	for art in ["baeume", "buesche", "erze", "pflanzen"]:
		var szene_pfad: String = {"baeume": baum_szene, "buesche": busch_szene, "erze": erz_szene, "pflanzen": pflanze_szene}[art]
		if not ResourceLoader.exists(szene_pfad):
			push_warning("WeltRessourcen: %s fehlt (%s) – wird übersprungen." % [art, szene_pfad])
			continue
		_szenen[art] = load(szene_pfad)
		for e in r.get(art, []):
			var k := Vector2i(floori(e[0] / CHUNK), floori(e[1] / CHUNK))
			if not _chunks.has(k):
				_chunks[k] = []
			_chunks[k].append([art, e])
	_bereit = true


## Alles im Radius sofort laden (z. B. nach dem Teleport oder für Screenshots)
func sofort_laden() -> void:
	_aktualisieren()
	while not _warteschlange.is_empty():
		_abarbeiten(1 << 30)


func _process(_delta: float) -> void:
	if not _bereit or ziel == null:
		return
	if Engine.get_process_frames() % 10 == 0:
		_aktualisieren()
	_abarbeiten(pro_frame)


func _aktualisieren() -> void:
	var p := ziel.global_position
	var mitte := Vector2i(floori(p.x / CHUNK), floori(p.z / CHUNK))
	var r := int(ceil(radius / CHUNK))
	var noetig := {}
	for dz in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var k := mitte + Vector2i(dx, dz)
			var c := (Vector2(k) + Vector2(0.5, 0.5)) * CHUNK
			if c.distance_to(Vector2(p.x, p.z)) <= radius + CHUNK and _chunks.has(k):
				noetig[k] = true
				if not _geladen.has(k):
					var knoten := Node3D.new()
					knoten.name = "Chunk_%d_%d" % [k.x, k.y]
					add_child(knoten)
					_geladen[k] = knoten
					for e in _chunks[k]:
						_warteschlange.append([knoten, e])
	# entfernen, was zu weit weg ist (mit Puffer, damit es an der Grenze nicht flackert)
	for k in _geladen.keys():
		if not noetig.has(k):
			var c := (Vector2(k) + Vector2(0.5, 0.5)) * CHUNK
			if c.distance_to(Vector2(p.x, p.z)) > radius + CHUNK * 2:
				_geladen[k].queue_free()
				_geladen.erase(k)


func _abarbeiten(anzahl: int) -> void:
	while anzahl > 0 and not _warteschlange.is_empty():
		var job: Array = _warteschlange.pop_front()
		var knoten: Node3D = job[0]
		if not is_instance_valid(knoten):
			continue
		_erzeugen(knoten, job[1][0], job[1][1])
		anzahl -= 1


func _erzeugen(eltern: Node3D, art: String, e: Array) -> void:
	var n: Node3D = _szenen[art].instantiate()
	var pos := Vector3(e[0], 0, e[1])
	pos.y = welt.hoehe_bei(pos)
	n.position = pos
	match art:
		"baeume":
			n.set("art", int(e[2]))
			n.set("alter", int(e[3]))
		"erze":
			n.set("tier", int(e[2]))
			n.set("groesse", int(e[3]))
			n.rotation.y = fmod(e[0] * 12.9898 + e[1] * 78.233, TAU)
			pos.y -= 0.15
			n.position = pos
		"pflanzen":
			n.set("art", int(e[2]))
			n.set("farbe", int(e[3]))
	eltern.add_child(n)
