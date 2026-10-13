extends Node3D
## Verbindet ein Blender-Modell aus assets/ (Baum, AesteBusch, Sammelpflanze, Felsbrocken) mit dem Sammelsystem des Spielers.
## Werte (Name, Beruf, Lebenspunkte, Beute, Nachwachszeit) kommen aus data/gathering.json.
## Das Modell kümmert sich um Aussehen, Stumpf/abgeerntet und das Nachwachsen.

var node_id := ""
var data: Dictionary = {}
var modell: Node3D
var interact_radius := 2.0


## id = Eintrag in gathering.json; m = Modell (noch nicht im Baum), r = Interaktionsradius in Metern
func setup(id: String, m: Node3D, r: float) -> void:
	node_id = id
	data = Game.gathering.get(id, {})
	modell = m
	interact_radius = r
	modell.set("respawn_zeit", float(data.get("respawn", 300.0)))
	add_child(modell)


func _ready() -> void:
	add_to_group("interactable")
	# Die Interaktionsbereiche der Modelle braucht das Spiel nicht (Abstandssuche) – spart Physik-Arbeit
	for a in find_children("*", "Area3D", true, false):
		(a as Area3D).monitoring = false
		(a as Area3D).monitorable = false


func is_interactable() -> bool:
	for zustand in ["ist_gefaellt", "ist_geerntet", "ist_abgebaut"]:
		var weg = modell.get(zustand)
		if weg != null:
			return not bool(weg)
	return true


func is_fishing() -> bool:
	return false


func get_prompt() -> String:
	return "%s %s   (Tier %s)" % [data.get("name", node_id), data.get("action", "sammeln"),
		Game.tier_name(int(data.get("tier", 1)))]


func get_profession() -> String:
	return data.get("profession", "")


func get_required_level() -> int:
	return int(data.get("level", 1))


func get_gather_hp() -> float:
	return float(data.get("hp", 20.0))


func harvest(player) -> void:
	var profession := get_profession()
	var level: int = player.get_profession_level(profession)
	var drops := Game.roll_drops(data.get("drops", []), level, bool(data.get("pick_one", false)))
	# Höhere Berufsstufe: Chance auf ein zusätzliches Stück
	if not drops.is_empty() and randf() < level * 0.02:
		var first: String = drops.keys()[0]
		drops[first] = int(drops[first]) + 1
	player.receive_items(drops)
	player.add_profession_xp(profession, int(data.get("xp", 10)))
	for methode in ["faellen", "ernten", "sammeln", "abbauen"]:
		if modell.has_method(methode):
			modell.call(methode)
			break
