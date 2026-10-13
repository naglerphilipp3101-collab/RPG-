extends Node
## Globale Spieldaten (aus data/*.json), Hilfsfunktionen und Tastenbelegung.

const MAX_PROFESSION_LEVEL := 50
const TIER_NAMES := ["I", "II", "III", "IV", "V"]
const TIER_COLORS := [
	Color(0.65, 0.65, 0.65),
	Color(0.4, 0.78, 0.4),
	Color(0.35, 0.6, 1.0),
	Color(0.7, 0.45, 0.95),
	Color(1.0, 0.62, 0.2),
]

## Anzeigenamen der Ausrüstungswerte; Prozentwerte werden als % dargestellt.
const STAT_NAMES := {
	"damage": "Schaden", "damage_pct": "Schaden", "crit": "Kritische Trefferchance", "bleed": "Blutungschance",
	"heavy": "Schwerer Angriff", "block": "Blockstärke", "armor": "Rüstung", "health": "Leben",
	"power": "Abbaukraft", "gather": "Abbaukraft",
	"attack_speed": "Angriffstempo", "cooldown_pct": "kürzere Abklingzeiten", "stamina_regen_pct": "Ausdauer-Regeneration",
	"damage_reduction": "Schadensreduktion", "move_speed_pct": "Laufgeschwindigkeit", "block_pct": "weniger Blockkosten",
	"dodge_cost_pct": "weniger Ausweichkosten", "reload_pct": "schneller Nachladen/Spannen", "crit_damage": "Kritischer Schaden",
	"stagger_immune": "Kein Taumeln",
}
const PERCENT_STATS := ["damage_pct", "crit", "bleed", "heavy", "gather", "attack_speed", "cooldown_pct",
	"stamina_regen_pct", "damage_reduction", "move_speed_pct", "block_pct", "dodge_cost_pct", "reload_pct", "crit_damage"]
const SLOT_NAMES := {
	"weapon": "Waffe", "weapon2": "Zweitwaffe", "shield": "Schild", "head": "Kopf", "chest": "Brust", "legs": "Beine",
	"ring": "Ring", "tool": "Werkzeug",
}
const MAX_MASTERY_LEVEL := 20
const DEFAULT_WEAPON_TYPE := "sword_1h" # ohne angelegte Waffe kämpft man mit einem einfachen Schwert
const WEAPON_DAMAGE_BY_TIER := {1: [22, 27], 2: [30, 36]}
const SKILL_KEYS := ["Q", "R", "F"]
const BASE_TOOL_POWER := 10.0
const SAVE_PATH := "user://savegame.json"
const AUTOSAVE_INTERVAL := 60.0

## Wird bei automatischen Tests abgeschaltet, damit der echte Spielstand unangetastet bleibt.
var saving_enabled := true

var weapons: Dictionary = {}
var enemies: Dictionary = {}
var items: Dictionary = {}
var gathering: Dictionary = {}
var professions: Dictionary = {}
var recipes: Dictionary = {}
var stations: Dictionary = {}
var _next_uid := 1


func _enter_tree() -> void:
	_setup_input()
	weapons = _load_json("res://data/weapons.json")
	enemies = _load_json("res://data/enemies.json")
	items = _load_json("res://data/items.json")
	gathering = _load_json("res://data/gathering.json")
	professions = _load_json("res://data/professions.json")
	recipes = _load_json("res://data/recipes.json")
	stations = _load_json("res://data/stations.json")
	_generate_weapon_items()


## Erzeugt aus data/weapons.json die Waffen-Gegenstände, ihre Rezepte und die Übungswaffen.
func _generate_weapon_items() -> void:
	for type in weapons:
		var w: Dictionary = weapons[type]
		var ranged: bool = w.get("class", "melee") == "ranged"
		var base_weight := 2.5 if ranged else (2.0 if int(w.get("hands", 1)) == 1 else 4.0)
		for entry in w.get("items", []):
			var def: Dictionary = entry
			var tier := int(def.get("tier", 1))
			var id: String = def["id"]
			items[id] = {
				"name": def["name"], "tier": tier, "weight": base_weight + 0.5 * (tier - 1),
				"category": w["name"], "slot": "weapon", "weapon_type": type,
				"color": [0.9, 0.55, 0.3] if tier == 1 else [0.6, 0.62, 0.68],
				"stats": {"damage": WEAPON_DAMAGE_BY_TIER.get(tier, [22, 27])},
				"description": "%s der Stufe %s." % [w["name"], tier_name(tier)],
			}
			recipes[id] = {
				"station": "engineer" if ranged else "weaponsmith", "level": 1 if tier == 1 else 3,
				"xp": 40 if tier == 1 else 90, "output": id, "ingredients": def.get("ingredients", {}),
			}
		var training_id: String = "training_" + type
		items[training_id] = {
			"name": "Übungs-" + String(w["name"]), "tier": 1, "weight": 1.0, "category": w["name"],
			"slot": "weapon", "weapon_type": type, "color": [0.7, 0.6, 0.45], "stats": {"damage": [18, 18]},
			"description": "Kostenlose Übungswaffe vom Waffenständer im Dorf.",
		}
		recipes[training_id] = {"station": "armory", "level": 1, "xp": 0, "output": training_id, "ingredients": {}}


# --- Waffen & Skillbäume ------------------------------------------------

func weapon_type_of(item_id: String) -> String:
	return item(item_id).get("weapon_type", "")


func weapon_def(type: String) -> Dictionary:
	return weapons.get(type, weapons.get(DEFAULT_WEAPON_TYPE, {}))


func mastery_xp_to_next(level: int) -> int:
	return int(80.0 * pow(level, 1.4))


## Alle Knoten eines Skillbaums als flache Liste (beide Äste).
func tree_nodes(type: String) -> Array:
	var result: Array = []
	for branch in weapon_def(type).get("tree", []):
		result.append_array(branch.get("nodes", []))
	return result


func tree_node(type: String, node_id: String) -> Dictionary:
	for node in tree_nodes(type):
		if node["id"] == node_id:
			return node
	return {}


func node_cost(node: Dictionary) -> int:
	return int(node.get("cost", 1))


## Beschreibung eines Skillbaum-Knotens für Tooltips und Anzeige.
func describe_node(node: Dictionary) -> String:
	if node.get("type", "") == "active":
		var skill: Dictionary = node.get("skill", {})
		return "%s\n%s\nAbklingzeit %d s" % [node.get("name", ""), node.get("desc", ""), int(skill.get("cooldown", 10))]
	var parts: Array[String] = []
	var stats: Dictionary = node.get("stats", {})
	for stat in stats:
		parts.append(format_stat(stat, stats[stat]))
	var title: String = node.get("name", "Passiv")
	return title + "\n" + "\n".join(parts)


func node_short_name(node: Dictionary) -> String:
	if node.has("name"):
		return node["name"]
	var parts: Array[String] = []
	var stats: Dictionary = node.get("stats", {})
	for stat in stats:
		parts.append(format_stat(stat, stats[stat]))
	return ", ".join(parts)


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Konnte %s nicht öffnen" % path)
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed
	push_error("Ungültiges JSON in %s" % path)
	return {}


# --- Gegenstände & Berufe -----------------------------------------------

func item(id: String) -> Dictionary:
	return items.get(id, {"name": id, "tier": 1, "weight": 0.0})


func item_name(id: String) -> String:
	return item(id).get("name", id)


func item_color(id: String) -> Color:
	var c: Array = item(id).get("color", [0.5, 0.5, 0.5])
	return Color(float(c[0]), float(c[1]), float(c[2]))


func tier_color(tier: int) -> Color:
	return TIER_COLORS[clampi(tier - 1, 0, TIER_COLORS.size() - 1)]


func tier_name(tier: int) -> String:
	return TIER_NAMES[clampi(tier - 1, 0, TIER_NAMES.size() - 1)]


func profession_name(id: String) -> String:
	return professions.get(id, {}).get("name", id)


# --- Ausrüstung ---------------------------------------------------------

func is_gear(id: String) -> bool:
	return item(id).has("slot")


## Ausrüstungsslot im Inventar des Spielers, z. B. "weapon" oder "tool:mining".
func equip_key(id: String) -> String:
	var def := item(id)
	if def.get("slot", "") == "tool":
		return "tool:" + String(def.get("profession", ""))
	return def.get("slot", "")


## Anzahl der Plätze für Zusatzmaterialien: höheres Tier = mehr Plätze.
func modifier_slots(id: String) -> int:
	return int(item(id).get("tier", 1))


## Darf das Zusatzmaterial `mod_id` in die Ausrüstung `gear_id`?
func modifier_fits(mod_id: String, gear_id: String) -> bool:
	var mod: Dictionary = item(mod_id).get("modifier", {})
	return mod.get("slots", []).has(item(gear_id).get("slot", ""))


## Erzeugt ein Ausrüstungsstück mit zufälligen Werten innerhalb der Spanne aus items.json.
func roll_gear(id: String, modifiers: Array) -> Dictionary:
	var def := item(id)
	var quality := randf()
	var stats := {}
	var ranges: Dictionary = def.get("stats", {})
	for stat in ranges:
		var r: Array = ranges[stat]
		stats[stat] = roundi(lerpf(float(r[0]), float(r[1]), quality))
	for mod_id in modifiers:
		var mod: Dictionary = item(mod_id).get("modifier", {})
		var stat: String = mod.get("stat", "")
		stats[stat] = stats.get(stat, 0) + mod.get("value", 0)
	var gear := {"uid": _next_uid, "id": id, "stats": stats, "quality": quality, "mods": modifiers.duplicate()}
	_next_uid += 1
	return gear


func format_stat(stat: String, value) -> String:
	var label: String = STAT_NAMES.get(stat, stat)
	if PERCENT_STATS.has(stat):
		return "+%d %% %s" % [roundi(float(value) * 100.0), label]
	return "%s  %d" % [label, int(value)]


func gear_tooltip(gear: Dictionary) -> String:
	var def := item(gear["id"])
	var tier := int(def.get("tier", 1))
	var lines: Array[String] = [
		String(def.get("name", gear["id"])),
		"Tier %s  ·  %s  ·  Qualität %d %%" % [tier_name(tier), def.get("category", ""), roundi(float(gear["quality"]) * 100.0)],
		"",
	]
	var stats: Dictionary = gear["stats"]
	for stat in stats:
		lines.append(format_stat(stat, stats[stat]))
	var mods: Array = gear.get("mods", [])
	if not mods.is_empty():
		lines.append("")
		for mod_id in mods:
			lines.append("Zusatz: " + item_name(mod_id))
	lines.append("")
	lines.append(String(def.get("description", "")))
	return "\n".join(lines)


## Benötigte Erfahrung, um von `level` auf die nächste Stufe zu kommen.
func xp_to_next(level: int) -> int:
	return int(50.0 * pow(level, 1.6))


## Würfelt Beute aus einer Liste von {item, min, max, chance, level}.
## Mit pick_one wird genau ein Eintrag gewichtet nach chance gewählt.
func roll_drops(entries: Array, level := 1, pick_one := false) -> Dictionary:
	var eligible: Array[Dictionary] = []
	for e in entries:
		var entry: Dictionary = e
		if level >= int(entry.get("level", 1)):
			eligible.append(entry)
	var result := {}
	if pick_one:
		var total := 0.0
		for entry in eligible:
			total += float(entry.get("chance", 1.0))
		var roll := randf() * total
		for entry in eligible:
			roll -= float(entry.get("chance", 1.0))
			if roll <= 0.0:
				_add_drop(result, entry)
				break
		return result
	for entry in eligible:
		if randf() <= float(entry.get("chance", 1.0)):
			_add_drop(result, entry)
	return result


func _add_drop(result: Dictionary, entry: Dictionary) -> void:
	var amount := randi_range(int(entry.get("min", 1)), int(entry.get("max", 1)))
	if amount > 0:
		var id: String = entry["item"]
		result[id] = int(result.get(id, 0)) + amount


# --- Eingabe ------------------------------------------------------------

func _setup_input() -> void:
	_add_key("move_forward", KEY_W)
	_add_key("move_back", KEY_S)
	_add_key("move_left", KEY_A)
	_add_key("move_right", KEY_D)
	_add_key("jump", KEY_SPACE)
	_add_key("dodge", KEY_SHIFT)
	_add_key("sprint", KEY_CTRL)
	_add_key("skill_1", KEY_Q)
	_add_key("skill_2", KEY_R)
	_add_key("skill_3", KEY_F)
	_add_key("interact", KEY_E)
	_add_key("use_potion", KEY_1)
	_add_key("use_food", KEY_2)
	_add_key("swap_weapon", KEY_X)
	_add_key("skill_tree", KEY_K)
	_add_key("inventory", KEY_TAB)
	_add_key("inventory", KEY_I)
	_add_key("toggle_help", KEY_F1)
	_add_mouse("attack", MOUSE_BUTTON_LEFT)
	_add_mouse("block", MOUSE_BUTTON_RIGHT)


func _ensure_action(action: String) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)


func _add_key(action: String, key: Key) -> void:
	_ensure_action(action)
	var event := InputEventKey.new()
	event.physical_keycode = key
	InputMap.action_add_event(action, event)


func _add_mouse(action: String, button: MouseButton) -> void:
	_ensure_action(action)
	var event := InputEventMouseButton.new()
	event.button_index = button
	InputMap.action_add_event(action, event)
