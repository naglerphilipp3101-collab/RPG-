extends Node
## Quests in der Welt: baut NPCs, Quest-Orte und Platzhalter-Gebäude aus data/npcs.json ins Startgebiet,
## lässt Quest-Gegner erscheinen, prüft „besuchen“-Ziele und liefert das Ziel der verfolgten Quest für den Kompass.
## Positionen sind lokal zum Startgebiet (main.area), die Höhe kommt vom Gelände (main._g).

const NpcScript := preload("res://scripts/npc.gd")
const OrtScript := preload("res://scripts/quest_ort.gd")
const EnemyScript := preload("res://scripts/enemy.gd")
const MeshUtil := preload("res://scripts/mesh_util.gd")
const PRUEF_TAKT := 0.25

var main = null
var player = null
var npc_knoten: Dictionary = {}  # npc-id -> NPC
var ort_knoten: Dictionary = {}  # ort-id -> QuestOrt
var _erschienen: Dictionary = {} # "quest:ziel" -> [Gegner]
var _takt := 0.0


func setup(main_node, p) -> void:
	main = main_node
	player = p


## Lokale Mittelpunkte aller Orte und NPCs (damit dort keine Bäume und Rohstoffe stehen).
static func freie_stellen() -> Array:
	var liste: Array = []
	for id in Game.quest_orte:
		var o: Dictionary = Game.quest_orte[id]
		if String(o.get("bau", "")) != "hinweis":
			liste.append([_vec(o.get("pos", [0, 0, 0])), float(o.get("radius", 4.0)) + 2.0])
	for id in Game.npcs:
		if Game.npcs[id].has("pos"):
			liste.append([_vec(Game.npcs[id]["pos"]), 2.0])
	return liste


static func _vec(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


func _ready() -> void:
	add_to_group("quest_welt")
	for id in Game.quest_orte:
		var o: Dictionary = Game.quest_orte[id]
		var lokal := _vec(o.get("pos", [0, 0, 0]))
		_bauen(String(o.get("bau", "")), lokal)
		var ort = OrtScript.new()
		ort.setup(id)
		ort.position = main._g(lokal)
		main.area.add_child(ort)
		ort_knoten[id] = ort
	for id in Game.npcs:
		var npc = NpcScript.new()
		npc.setup(id)
		var d: Dictionary = Game.npcs[id]
		var lokal := _vec(d.get("pos", [0, 0, 0]))
		var blick := Vector3.ZERO
		if d.has("bei_werkstatt"):
			for station in get_tree().get_nodes_in_group("werkstatt"):
				if station.get("station_id") == d["bei_werkstatt"]:
					var zur_mitte: Vector3 = main.VILLAGE_CENTER - station.position
					zur_mitte.y = 0.0
					lokal = Vector3(station.position.x, 0, station.position.z) + zur_mitte.normalized() * 2.2 \
						+ zur_mitte.normalized().cross(Vector3.UP) * 1.2
					blick = zur_mitte
		npc.position = main._g(lokal)
		if blick == Vector3.ZERO:
			blick = main.VILLAGE_CENTER - lokal
		npc.rotation.y = atan2(-blick.x, -blick.z) if blick.length() > 0.1 else 0.0
		main.area.add_child(npc)
		npc_knoten[id] = npc
	player.quests.geaendert.connect(_aktualisieren)
	# Nach dem Laden des Spielstands: selbststartende Quests (z. B. der Prolog) annehmen, Zeichen setzen
	player.quests._pruefen.call_deferred()
	_aktualisieren.call_deferred()


func _process(delta: float) -> void:
	_takt -= delta
	if _takt > 0.0 or player == null:
		return
	_takt = PRUEF_TAKT
	# Besuchen: Spieler im Umkreis des Orts (die Quest prüft Tag/Nacht selbst)
	for eintrag in player.quests.offene_ziele():
		var ziel: Dictionary = eintrag["ziel"]
		if String(ziel.get("art", "")) == "besuchen" and ort_knoten.has(ziel.get("ort", "")):
			var ort = ort_knoten[ziel["ort"]]
			var r := float(Game.quest_orte[ziel["ort"]].get("radius", 6.0))
			var to: Vector3 = ort.global_position - player.global_position
			to.y = 0.0
			if to.length() <= r:
				player.quests.ereignis("besuchen", String(ziel["ort"]))
	_gegner_erscheinen()


## Sichtbarkeit der NPCs, ihre Zeichen und welche Orte gerade untersucht werden können.
func _aktualisieren() -> void:
	var q = player.quests
	var offen: Array = q.offene_ziele()
	for id in npc_knoten:
		var npc = npc_knoten[id]
		npc.sichtbar_setzen(q.bedingungen_ok(Game.npcs[id].get("sichtbar", {})))
		var zeichen := ""
		for e in offen:
			if String(e["ziel"].get("art", "")) in ["reden", "abgeben"] and String(e["ziel"].get("npc", "")) == id:
				zeichen = "…"
		if not q.angebote(id).is_empty():
			zeichen = "!"
		for qid in q.aktiv:
			if q.bereit(qid) and q.abgabe_npc(qid) == id:
				zeichen = "?"
		npc.zeichen_setzen(zeichen)
	var gesucht := {}
	for e in offen:
		if String(e["ziel"].get("art", "")) == "untersuchen":
			gesucht[String(e["ziel"].get("ort", ""))] = true
	for id in ort_knoten:
		ort_knoten[id].aktiv_setzen(gesucht.has(id))


## Ziele mit "erscheinen": so viele Gegner am Ort, wie noch fehlen.
func _gegner_erscheinen() -> void:
	var noch_gebraucht := {}
	for e in player.quests.offene_ziele():
		var ziel: Dictionary = e["ziel"]
		if String(ziel.get("art", "")) != "toeten" or not ziel.has("erscheinen"):
			continue
		var schluessel := "%s:%d" % [e["quest"], e["index"]]
		noch_gebraucht[schluessel] = true
		var liste: Array = _erschienen.get(schluessel, []).filter(func(g): return is_instance_valid(g) and g.is_alive())
		var fehlt: int = player.quests.ziel_menge(ziel) - player.quests.fortschritt(e["quest"], e["index"]) - liste.size()
		var ort_id := String(ziel["erscheinen"].get("ort", ""))
		if fehlt > 0 and Game.quest_orte.has(ort_id):
			var mitte := _vec(Game.quest_orte[ort_id].get("pos", [0, 0, 0]))
			for k in fehlt:
				var gegner = EnemyScript.new()
				var spot := mitte + Vector3(randf_range(-3, 3), 0, randf_range(-3, 3))
				gegner.setup(String(ziel.get("gegner", "")), main.area.position + main._g(mitte))
				gegner.einmalig = true
				gegner.position = main.area.position + main._g(spot) + Vector3(0, 0.5, 0)
				main.add_child(gegner)
				liste.append(gegner)
		_erschienen[schluessel] = liste
	# Ziel erledigt oder Quest abgebrochen: übrige Quest-Gegner verschwinden
	for schluessel in _erschienen.keys():
		if not noch_gebraucht.has(schluessel):
			for g in _erschienen[schluessel]:
				if is_instance_valid(g) and g.is_alive():
					g.queue_free()
			_erschienen.erase(schluessel)


## Weltposition des nächsten Ziels der verfolgten Quest (null = keins), für Kompass und Anzeige.
func ziel_position():
	var q = player.quests
	if q.verfolgt == "" or not q.aktiv.has(q.verfolgt):
		return null
	var id: String = q.verfolgt
	if q.bereit(id):
		var npc: String = q.abgabe_npc(id)
		return npc_knoten[npc].global_position if npc_knoten.has(npc) else null
	for i in q.ziele(id).size():
		if not q.ziel_offen(id, i):
			continue
		var ziel: Dictionary = q.ziele(id)[i]
		match String(ziel.get("art", "")):
			"reden", "abgeben":
				if npc_knoten.has(ziel.get("npc", "")):
					return npc_knoten[ziel["npc"]].global_position
			"besuchen", "untersuchen":
				if ort_knoten.has(ziel.get("ort", "")):
					return ort_knoten[ziel["ort"]].global_position
			"toeten":
				if ziel.has("erscheinen") and ort_knoten.has(ziel["erscheinen"].get("ort", "")):
					return ort_knoten[ziel["erscheinen"]["ort"]].global_position
				var beste = null
				var beste_d := INF
				for g in get_tree().get_nodes_in_group("enemies"):
					if g.get("type_id") == ziel.get("gegner", "") and g.is_alive():
						var d: float = g.global_position.distance_to(player.global_position)
						if d < beste_d:
							beste_d = d
							beste = g.global_position
				return beste
			"herstellen":
				var rezept: Dictionary = Game.recipes.get(ziel.get("item", ""), {})
				for station in get_tree().get_nodes_in_group("werkstatt"):
					if station.get("station_id") == rezept.get("station", ""):
						return station.global_position
	return null


# --- Platzhalter-Gebäude ------------------------------------------------------

func _bauen(bau: String, lokal: Vector3) -> void:
	var area: Node3D = main.area
	var kohle := MeshUtil.mat(Color(0.16, 0.14, 0.13))
	var holz := MeshUtil.mat(Color(0.42, 0.3, 0.18))
	var stein := MeshUtil.mat(Color(0.5, 0.49, 0.47))
	match bau:
		"muehle", "ruine":
			# verkohlte Mauerreste mit Lücken, ein paar umgestürzte Balken
			var mauern := [[Vector3(0, 0, -4), Vector3(8, 0, 0.4)], [Vector3(-4, 0, 0), Vector3(0.4, 0, 8)],
				[Vector3(4, 0, 1.5), Vector3(0.4, 0, 5)], [Vector3(-1.5, 0, 4), Vector3(5, 0, 0.4)]]
			for i in mauern.size():
				var m: Array = mauern[i]
				var hoehe := 2.6 - i * 0.5 if bau == "muehle" else 1.2 - i * 0.2
				var groesse := Vector3(maxf(m[1].x, 0.4), hoehe, maxf(m[1].z, 0.4))
				var koerper := StaticBody3D.new()
				koerper.position = main._g(lokal + m[0])
				area.add_child(koerper)
				MeshUtil.part(koerper, MeshUtil.box(groesse), stein if bau == "muehle" else kohle, Vector3(0, hoehe * 0.5, 0))
				main._add_box_collision(koerper, groesse, Vector3(0, hoehe * 0.5, 0))
			for k in 3:
				var balken := MeshUtil.part(area, MeshUtil.box(Vector3(0.25, 0.25, 3.2)), kohle,
					main._g(lokal + Vector3(-2 + k * 1.6, 0.13, -1 + k)))
				balken.rotation.y = 0.5 + k * 0.9
			if bau == "muehle":
				var rad := CylinderMesh.new()
				rad.top_radius = 2.2
				rad.bottom_radius = 2.2
				rad.height = 0.35
				var r := MeshUtil.part(area, rad, holz, main._g(lokal + Vector3(5.2, 2.0, -1.5)))
				r.rotation = Vector3(0, 0, PI / 2 + 0.25)
		"turm":
			var turm := CylinderMesh.new()
			turm.top_radius = 2.4
			turm.bottom_radius = 2.8
			turm.height = 10.0
			var koerper := StaticBody3D.new()
			koerper.position = main._g(lokal)
			area.add_child(koerper)
			MeshUtil.part(koerper, turm, stein, Vector3(0, 5.0, 0))
			var form := CylinderShape3D.new()
			form.radius = 2.7
			form.height = 10.0
			var col := CollisionShape3D.new()
			col.shape = form
			col.position.y = 5.0
			koerper.add_child(col)
		"haus":
			var koerper := StaticBody3D.new()
			koerper.position = main._g(lokal)
			area.add_child(koerper)
			MeshUtil.part(koerper, MeshUtil.box(Vector3(5, 3, 4)), MeshUtil.mat(Color(0.75, 0.7, 0.6)), Vector3(0, 1.5, 0))
			var dach := PrismMesh.new()
			dach.size = Vector3(5.6, 1.8, 4.6)
			MeshUtil.part(koerper, dach, MeshUtil.mat(Color(0.45, 0.2, 0.15)), Vector3(0, 3.9, 0))
			main._add_box_collision(koerper, Vector3(5, 3, 4), Vector3(0, 1.5, 0))
		"truhe":
			var koerper := StaticBody3D.new()
			koerper.position = main._g(lokal)
			area.add_child(koerper)
			MeshUtil.part(koerper, MeshUtil.box(Vector3(0.9, 0.55, 0.55)), holz, Vector3(0, 0.28, 0))
			MeshUtil.part(koerper, MeshUtil.box(Vector3(0.95, 0.08, 0.6)), MeshUtil.mat(Color(0.3, 0.3, 0.32), 0.8, 0.4), Vector3(0, 0.5, 0))
			main._add_box_collision(koerper, Vector3(0.9, 0.55, 0.55), Vector3(0, 0.28, 0))
