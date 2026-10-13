extends CharacterBody3D
## Spielfigur: Third-Person-Steuerung, Kamera, Kampf mit allen Waffentypen (Nah- und Fernkampf),
## Skillbäume & Waffenmeisterschaft, Inventar, Berufe, Sammeln, Herstellen und Spielstand.

signal message(text: String)
signal notify(text: String, color: Color)
signal hurt
signal died
signal respawned
signal station_opened(station_id: String)
signal equipment_changed

const FX := preload("res://scripts/fx.gd")
const MeshUtil := preload("res://scripts/mesh_util.gd")
const InventoryScript := preload("res://scripts/inventory.gd")
const WeaponModels := preload("res://scripts/weapon_models.gd")
const ProjectileScript := preload("res://scripts/projectile.gd")
const ZoneScript := preload("res://scripts/zone.gd")

const WALK_SPEED := 5.0
const SPRINT_SPEED := 8.0
const BLOCK_SPEED := 2.0
const AIM_SPEED := 2.6
const ACTION_SPEED := 1.2
const ACCELERATION := 14.0
const AIR_ACCELERATION := 3.0
const GRAVITY := 18.0
const JUMP_VELOCITY := 7.0
const DODGE_SPEED := 12.0
const DODGE_TIME := 0.45
const DODGE_IFRAMES := 0.35
const DODGE_COST := 25.0
const SPRINT_COST := 10.0 # pro Sekunde
const STAMINA_REGEN := 32.0 # pro Sekunde
const HEALTH_REGEN := 12.0 # pro Sekunde außerhalb des Kampfes
const BLOCK_STAMINA_FACTOR := 1.3
const HEAVY_HOLD_TIME := 0.3
const COMBO_WINDOW := 0.6
const MOUSE_SENSITIVITY := 0.0025
const RESPAWN_TIME := 4.0
const FOCUS_INTERVAL := 0.1
const FISH_WAIT_MIN := 2.5
const FISH_WAIT_MAX := 6.0
const FISH_BITE_WINDOW := 1.1
const MASTERY_XP_PER_DAMAGE := 0.5
const MAX_EQUIPPED_SKILLS := 3

const SHIELD_REST_POS := Vector3(-0.45, 0.0, 0.0)
const SHIELD_REST_ROT := Vector3(0, 80, 0)
const SHIELD_BLOCK_POS := Vector3(-0.12, 0.25, -0.5)
const SHIELD_BLOCK_ROT := Vector3(0, 8, 0)
const WEAPON_BLOCK_ROT := Vector3(15, 80, 0) # Waffe quer vor dem Körper
const SWING_STYLES := {
	"h_right": [Vector3(5, -95, 0), Vector3(5, 95, 0)],
	"h_left": [Vector3(5, 95, 0), Vector3(5, -95, 0)],
	"overhead": [Vector3(110, 0, 0), Vector3(-45, 0, 0)],
	"big_overhead": [Vector3(130, 0, 0), Vector3(-60, 0, 0)],
	"diag": [Vector3(80, -70, 0), Vector3(-30, 60, 0)],
}

enum State { NORMAL, ACTION, DODGE, STAGGER, DEAD, GATHER, FISH }

var max_health := 200.0
var health := 200.0
var max_stamina := 100.0
var stamina := 100.0

var state: State = State.NORMAL
var state_timer := 0.0
var spawn_point := Vector3.ZERO

# Laufende Aktion (Angriff, Fähigkeit, Spannen, Nachladen), wird pro Physik-Frame abgespielt.
var action: Dictionary = {}
var combo_index := 0
var combo_timer := 0.0
var buffered_light := false
var attack_held := false
var attack_hold_time := 0.0
var swallow_click := false

var blocking := false
var shield_raised := false
var aiming := false
var iframes := 0.0
var stamina_delay := 0.0
var combat_timer := 0.0
var dodge_dir := Vector3.ZERO
var shake := 0.0

var cam_yaw := 0.0
var cam_pitch := -0.3
var camera_pivot: Node3D
var camera_pitch_node: Node3D
var spring_arm: SpringArm3D
var camera: Camera3D

var model: Node3D
var body_root: Node3D
var weapon_pivot: Node3D
var offhand_pivot: Node3D
var shield_pivot: Node3D
var aura: MeshInstance3D
var anim_tween: Tween
var shield_tween: Tween

# Inventar & Berufe
var inventory = InventoryScript.new()
var professions: Dictionary = {} # id -> {"level": int, "xp": int}
var tool_tiers: Dictionary = {} # Berufs-id -> Werkzeug-Tier
var ui_open := false

# Sammeln
var focus = null # nächstgelegenes interagierbares Objekt
var focus_timer := 0.0
var gather_target = null
var gather_time := 0.0
var gather_total := 1.0
var fish_phase := "" # "wait" oder "bite"
var fish_timer := 0.0
var tool_pivot: Node3D
var tools: Dictionary = {} # Werkzeug-id -> Node3D
var gather_hp := 0.0

# Ausrüstung: Slot ("weapon", "weapon2", "shield", "head", "chest", "legs", "ring", "tool:<beruf>") -> Ausrüstungsstück
var equipment: Dictionary = {}
const BASE_MAX_HEALTH := 200.0
const BASE_WEAPON_DAMAGE := 20.0 # Schaden ohne Waffe; Angriffe skalieren relativ zum Waffenschaden
var damage_mult := 1.0 # nur für die Anzeige (ohne zeitliche Buffs)
var crit_chance := 0.05
var bleed_chance := 0.0
var block_power := 0.0
var armor := 0.0

# Waffen, Skillbäume, Meisterschaft
var weapon_type := Game.DEFAULT_WEAPON_TYPE
var weapon_def: Dictionary = {}
var masteries: Dictionary = {} # Waffentyp -> {"level", "xp", "unlocked": [], "equipped": []}
var passive: Dictionary = {} # Werte aus freigeschalteten passiven Knoten der aktiven Waffe
var buffs: Array[Dictionary] = [] # {"stats": {...}, "time": float}
var skill_cooldowns: Dictionary = {} # Knoten-id -> verbleibende Sekunden
var ranged_loaded := true
var damage_dealt_total := 0.0 # nur für Tests/Statistik

# Debug-Flug (F3): fliegen ohne Kollision, mit Sprinten 30-fache Geschwindigkeit, unverwundbar
const FLY_SPEED := 12.0
const FLY_SPRINT_FACTOR := 30.0
var debug_fly := false

# Verbrauchsgüter
const POTION_COOLDOWN := 15.0
var potion_cooldown := 0.0
var food_regen := 0.0
var food_time := 0.0


func _ready() -> void:
	add_to_group("player")
	collision_layer = 2
	collision_mask = 1 | 4
	spawn_point = global_position

	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.4
	capsule.height = 1.8
	shape.shape = capsule
	shape.position.y = 0.9
	add_child(shape)

	for id in Game.professions:
		professions[id] = {"level": 1, "xp": 0}
		tool_tiers[id] = 1

	_build_model()
	_build_tools()
	_build_camera()
	# Startausrüstung für ein neues Spiel (ein geladener Spielstand ersetzt sie)
	equipment["weapon"] = Game.roll_gear("training_sword_1h", [])
	equipment["shield"] = Game.roll_gear("training_shield", [])
	_recalc_stats()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func is_alive() -> bool:
	return state != State.DEAD


# --- Debug-Flug ---------------------------------------------------------

func set_debug_fly(on: bool) -> void:
	debug_fly = on
	if on:
		if state == State.GATHER or state == State.FISH:
			_end_gather()
		elif state == State.ACTION:
			_end_action(false)
		if state != State.DEAD:
			state = State.NORMAL
		blocking = false
		_set_block_pose(false)
		_kill_anim(true)
	collision_layer = 0 if on else 2
	collision_mask = 0 if on else 1 | 4
	velocity = Vector3.ZERO
	message.emit("Debug-Flug AN  (Leertaste hoch · C runter · Strg ×30)" if on else "Debug-Flug AUS")


## Springt an eine Weltposition (x/z); die Höhe bestimmt der Aufrufer (z. B. Gelände + Abstand).
func teleport(pos: Vector3) -> void:
	global_position = pos
	velocity = Vector3.ZERO
	camera_pivot.global_position = pos + Vector3(0, 1.55, 0)


func _fly(delta: float, captured: bool) -> void:
	health = max_health
	stamina = max_stamina
	var input_dir := Vector2.ZERO
	var vertical := 0.0
	var fast := false
	if captured:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		vertical = (1.0 if Input.is_action_pressed("jump") else 0.0) - (1.0 if Input.is_action_pressed("fly_down") else 0.0)
		fast = Input.is_action_pressed("sprint")
	# Vorwärts folgt der Kamera, auch nach oben/unten geneigt
	var fly_basis := Basis(Vector3.UP, cam_yaw) * Basis(Vector3.RIGHT, cam_pitch)
	var dir := fly_basis * Vector3(input_dir.x, 0.0, input_dir.y) + Vector3.UP * vertical
	if dir.length() > 1.0:
		dir = dir.normalized()
	var speed := FLY_SPEED * (FLY_SPRINT_FACTOR if fast else 1.0)
	global_position += dir * speed * delta
	if input_dir.length() > 0.1:
		_face_angle(cam_yaw, delta, 10.0)


func is_ranged() -> bool:
	return weapon_def.get("class", "melee") == "ranged"


# --- Inventar & Berufe --------------------------------------------------

func get_profession_level(id: String) -> int:
	return int(professions.get(id, {}).get("level", 1))


func add_profession_xp(id: String, amount: int) -> void:
	if not professions.has(id) or amount <= 0:
		return
	var p: Dictionary = professions[id]
	p["xp"] = int(p["xp"]) + amount
	notify.emit("+%d EP %s" % [amount, Game.profession_name(id)], Color(0.6, 0.85, 1.0))
	while int(p["level"]) < Game.MAX_PROFESSION_LEVEL and int(p["xp"]) >= Game.xp_to_next(int(p["level"])):
		p["xp"] = int(p["xp"]) - Game.xp_to_next(int(p["level"]))
		p["level"] = int(p["level"]) + 1
		message.emit("%s: Stufe %d erreicht!" % [Game.profession_name(id), p["level"]])
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Stufe %d!" % p["level"], Color(0.5, 0.9, 1.0), 72)


## Legt Gegenstände ins Inventar. Gibt zurück, was nicht mehr hineingepasst hat.
func receive_items(drops: Dictionary) -> Dictionary:
	var leftover := {}
	for id in drops:
		var amount := int(drops[id])
		var added: int = inventory.add(id, amount)
		if added > 0:
			var tier := int(Game.item(id).get("tier", 1))
			notify.emit("+%d %s" % [added, Game.item_name(id)], Game.tier_color(tier).lightened(0.3))
		if added < amount:
			leftover[id] = amount - added
	if not leftover.is_empty():
		message.emit("Tasche voll!")
	return leftover


# --- Ausrüstung & Werte -------------------------------------------------

func equip(uid: int) -> void:
	var g: Dictionary = inventory.take_gear(uid)
	if g.is_empty():
		return
	var key := Game.equip_key(g["id"])
	# Waffen füllen zuerst den freien der beiden Waffenplätze
	if key == "weapon" and equipment.has("weapon") and not equipment.has("weapon2"):
		key = "weapon2"
	if equipment.has(key):
		inventory.gear.append(equipment[key]) # altes Stück zurück in die Tasche
	equipment[key] = g
	_recalc_stats()
	inventory.changed.emit()


func unequip(key: String) -> void:
	if not equipment.has(key):
		return
	var g: Dictionary = equipment[key]
	if not inventory.add_gear(g):
		message.emit("Tasche voll!")
		return
	equipment.erase(key)
	_recalc_stats()


## Wechselt zwischen Haupt- und Zweitwaffe (Taste X).
func swap_weapons() -> void:
	if not equipment.has("weapon2"):
		message.emit("Keine Zweitwaffe angelegt")
		return
	var first = equipment.get("weapon")
	equipment["weapon"] = equipment["weapon2"]
	if first == null:
		equipment.erase("weapon2")
	else:
		equipment["weapon2"] = first
	_recalc_stats()
	message.emit(Game.item_name(equipment["weapon"]["id"]))


func _stat(key: String, stat: String, fallback := 0.0) -> float:
	if not equipment.has(key):
		return fallback
	return float(equipment[key]["stats"].get(stat, fallback))


## Bonus aus passiven Skillknoten und laufenden Buffs.
func bonus(stat: String) -> float:
	var value := float(passive.get(stat, 0.0))
	for b in buffs:
		value += float(b["stats"].get(stat, 0.0))
	return value


func shield_active() -> bool:
	return equipment.has("shield") and bool(weapon_def.get("allows_shield", false))


func _recalc_stats() -> void:
	var new_type := Game.DEFAULT_WEAPON_TYPE
	if equipment.has("weapon"):
		var t := Game.weapon_type_of(equipment["weapon"]["id"])
		if t != "":
			new_type = t
	var type_changed := new_type != weapon_type or weapon_def.is_empty()
	weapon_type = new_type
	weapon_def = Game.weapon_def(weapon_type)
	_mastery(weapon_type)
	_recalc_passives()

	damage_mult = _stat("weapon", "damage", BASE_WEAPON_DAMAGE) / BASE_WEAPON_DAMAGE \
		* (1.0 + _stat("weapon", "damage_pct") + float(passive.get("damage_pct", 0.0)))
	crit_chance = 0.05 + _stat("weapon", "crit") + float(passive.get("crit", 0.0))
	bleed_chance = _stat("weapon", "bleed") + float(passive.get("bleed", 0.0))
	block_power = _stat("shield", "block") if shield_active() else 0.0
	armor = 0.0
	for key in ["head", "chest", "legs"]:
		armor += _stat(key, "armor")
	if shield_active():
		armor += _stat("shield", "armor")
	var old_max := max_health
	max_health = BASE_MAX_HEALTH + _stat("ring", "health") + float(passive.get("health", 0.0))
	health = clampf(health + maxf(max_health - old_max, 0.0), 0.0, max_health)
	for id in Game.professions:
		var key: String = "tool:" + String(id)
		tool_tiers[id] = int(Game.item(equipment[key]["id"]).get("tier", 1)) if equipment.has(key) else 1
	if type_changed:
		ranged_loaded = true
		combo_index = 0
		if state == State.ACTION:
			_end_action(false)
	_build_weapon_visual()
	equipment_changed.emit()


## Abbaukraft für einen Sammelberuf (Startwerkzeug = 10).
func get_tool_power(profession: String) -> float:
	var key := "tool:" + profession
	return _stat(key, "power", Game.BASE_TOOL_POWER) * (1.0 + _stat(key, "gather"))


# --- Meisterschaft & Skillbaum ------------------------------------------

## Meisterschaftsdaten eines Waffentyps; beim ersten Mal wird die erste Fähigkeit freigeschaltet.
func _mastery(type: String) -> Dictionary:
	if not masteries.has(type):
		masteries[type] = {"level": 1, "xp": 0.0, "unlocked": [], "equipped": []}
		var tree: Array = Game.weapon_def(type).get("tree", [])
		if not tree.is_empty():
			var first: Dictionary = tree[0]["nodes"][0]
			masteries[type]["unlocked"].append(first["id"])
			if first.get("type", "") == "active":
				masteries[type]["equipped"].append(first["id"])
	return masteries[type]


func mastery_points_free(type: String) -> int:
	var m := _mastery(type)
	var spent := 0
	for node_id in m["unlocked"]:
		spent += Game.node_cost(Game.tree_node(type, node_id))
	return int(m["level"]) - spent


## Prüft, ob ein Knoten freigeschaltet werden kann. Gibt eine Fehlermeldung oder "" zurück.
func unlock_check(type: String, node_id: String) -> String:
	var m := _mastery(type)
	if m["unlocked"].has(node_id):
		return "Bereits freigeschaltet"
	for branch in Game.weapon_def(type).get("tree", []):
		var nodes: Array = branch["nodes"]
		for i in nodes.size():
			if nodes[i]["id"] != node_id:
				continue
			if i > 0 and not m["unlocked"].has(nodes[i - 1]["id"]):
				return "Zuerst den vorherigen Knoten freischalten"
			if Game.node_cost(nodes[i]) > mastery_points_free(type):
				return "Nicht genug Punkte"
			return ""
	return "Unbekannter Knoten"


func unlock_node(type: String, node_id: String) -> String:
	var error := unlock_check(type, node_id)
	if error != "":
		return error
	var m := _mastery(type)
	m["unlocked"].append(node_id)
	var node := Game.tree_node(type, node_id)
	if node.get("type", "") == "active" and m["equipped"].size() < MAX_EQUIPPED_SKILLS:
		m["equipped"].append(node_id)
	_recalc_stats()
	return ""


## Legt eine freigeschaltete aktive Fähigkeit auf Q/R/F oder nimmt sie herunter.
func toggle_skill(type: String, node_id: String) -> String:
	var m := _mastery(type)
	if not m["unlocked"].has(node_id):
		return "Noch nicht freigeschaltet"
	if m["equipped"].has(node_id):
		m["equipped"].erase(node_id)
	elif m["equipped"].size() >= MAX_EQUIPPED_SKILLS:
		return "Höchstens %d Fähigkeiten gleichzeitig" % MAX_EQUIPPED_SKILLS
	else:
		m["equipped"].append(node_id)
	equipment_changed.emit()
	return ""


func reset_tree(type: String) -> void:
	var m := _mastery(type)
	m["unlocked"] = []
	m["equipped"] = []
	_recalc_stats()


func _recalc_passives() -> void:
	passive = {}
	var m := _mastery(weapon_type)
	for node_id in m["unlocked"]:
		var node := Game.tree_node(weapon_type, node_id)
		if node.get("type", "") != "passive":
			continue
		var stats: Dictionary = node.get("stats", {})
		for stat in stats:
			passive[stat] = float(passive.get(stat, 0.0)) + float(stats[stat])


func add_mastery_xp(type: String, amount: float) -> void:
	var m := _mastery(type)
	if int(m["level"]) >= Game.MAX_MASTERY_LEVEL:
		return
	m["xp"] = float(m["xp"]) + amount
	while int(m["level"]) < Game.MAX_MASTERY_LEVEL and float(m["xp"]) >= Game.mastery_xp_to_next(int(m["level"])):
		m["xp"] = float(m["xp"]) - Game.mastery_xp_to_next(int(m["level"]))
		m["level"] = int(m["level"]) + 1
		var name: String = Game.weapon_def(type).get("name", type)
		message.emit("%s-Meisterschaft Stufe %d!  Neuer Skillpunkt (K)" % [name, m["level"]])
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Meisterschaft %d!" % m["level"], Color(1.0, 0.8, 0.3), 72)


## Info für die Fähigkeitenleiste: Name, Taste, Abklingzeit.
func get_skill_info(index: int) -> Dictionary:
	var equipped: Array = _mastery(weapon_type)["equipped"]
	if index >= equipped.size():
		return {"name": "", "key": Game.SKILL_KEYS[index], "cooldown": 1.0, "remaining": 0.0}
	var node := Game.tree_node(weapon_type, equipped[index])
	return {
		"name": node.get("name", ""), "key": Game.SKILL_KEYS[index],
		"cooldown": _skill_cooldown(node), "remaining": float(skill_cooldowns.get(node["id"], 0.0)),
	}


func _skill_cooldown(node: Dictionary) -> float:
	return float(node.get("skill", {}).get("cooldown", 10.0)) * (1.0 - clampf(bonus("cooldown_pct"), 0.0, 0.6))


# --- Herstellen ---------------------------------------------------------

## Prüft ein Rezept. Gibt eine Fehlermeldung zurück oder "" wenn es möglich ist.
func craft_check(recipe_id: String, amount := 1, modifiers: Array = []) -> String:
	var recipe: Dictionary = Game.recipes.get(recipe_id, {})
	if recipe.is_empty():
		return "Unbekanntes Rezept"
	var profession: String = Game.stations[recipe["station"]]["profession"]
	if get_profession_level(profession) < int(recipe.get("level", 1)):
		return "Benötigt %s Stufe %d" % [Game.profession_name(profession), int(recipe.get("level", 1))]
	var needed: Dictionary = {}
	var ingredients: Dictionary = recipe["ingredients"]
	for id in ingredients:
		needed[id] = int(ingredients[id]) * amount
	for mod_id in modifiers:
		needed[mod_id] = int(needed.get(mod_id, 0)) + 1
	for id in needed:
		if inventory.count(id) < int(needed[id]):
			return "Nicht genug %s" % Game.item_name(id)
	return ""


func craft(recipe_id: String, amount := 1, modifiers: Array = []) -> String:
	var error := craft_check(recipe_id, amount, modifiers)
	if error != "":
		return error
	var recipe: Dictionary = Game.recipes[recipe_id]
	var output: String = recipe["output"]
	var gear := Game.is_gear(output)
	if gear:
		amount = 1
	# Erst Zutaten abziehen, dann prüfen ob das Ergebnis passt (sonst zurückgeben)
	var ingredients: Dictionary = recipe["ingredients"]
	for id in ingredients:
		inventory.remove(id, int(ingredients[id]) * amount)
	for mod_id in modifiers:
		inventory.remove(mod_id, 1)
	var made := ""
	if gear:
		var g := Game.roll_gear(output, modifiers)
		if inventory.add_gear(g):
			made = Game.item_name(output)
	else:
		var count := int(recipe.get("count", 1)) * amount
		if inventory.space_for(output) >= count:
			inventory.add(output, count)
			made = "%d× %s" % [count, Game.item_name(output)]
	if made == "":
		for id in ingredients:
			inventory.add(id, int(ingredients[id]) * amount)
		for mod_id in modifiers:
			inventory.add(mod_id, 1)
		return "Tasche voll!"
	var profession: String = Game.stations[recipe["station"]]["profession"]
	notify.emit("Hergestellt: " + made, Color(1.0, 0.85, 0.5))
	add_profession_xp(profession, int(recipe.get("xp", 10)) * amount)
	return ""


# --- Verbrauchsgüter ----------------------------------------------------

## Benutzt das beste Verbrauchsgut des Typs "potion" oder "food".
func use_consumable(kind: String) -> void:
	if state == State.DEAD:
		return
	var best := ""
	var best_tier := 0
	for id in inventory.items:
		var c: Dictionary = Game.item(id).get("consumable", {})
		var tier := int(Game.item(id).get("tier", 1))
		if c.get("type", "") == kind and tier > best_tier:
			best = id
			best_tier = tier
	if best == "":
		message.emit("Kein Heiltrank im Inventar" if kind == "potion" else "Kein Essen im Inventar")
		return
	var effect: Dictionary = Game.item(best)["consumable"]
	if kind == "potion":
		if potion_cooldown > 0.0:
			message.emit("Heiltrank noch %d s gesperrt" % ceili(potion_cooldown))
			return
		var heal := float(effect.get("heal", 50))
		health = minf(health + heal, max_health)
		potion_cooldown = POTION_COOLDOWN
		FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(heal), Color(0.4, 1.0, 0.4), 64)
	else:
		food_regen = float(effect.get("regen", 2))
		food_time = float(effect.get("duration", 60))
		message.emit("%s: +%d Leben/s für %d s" % [Game.item_name(best), roundi(food_regen), roundi(food_time)])
	inventory.remove(best, 1)


# --- Spielstand ---------------------------------------------------------

func to_save() -> Dictionary:
	var pos := spawn_point if state == State.DEAD else global_position
	return {
		"world": Game.world_id,
		"position": [pos.x, pos.y, pos.z],
		"cam_yaw": cam_yaw,
		"health": health,
		"food_regen": food_regen,
		"food_time": food_time,
		"items": inventory.items.duplicate(),
		"gear": inventory.gear.duplicate(true),
		"equipment": equipment.duplicate(true),
		"professions": professions.duplicate(true),
		"masteries": masteries.duplicate(true),
	}


func from_save(data: Dictionary) -> void:
	# Position nur übernehmen, wenn der Spielstand aus derselben Welt stammt (sonst am Startpunkt bleiben)
	if data.get("world", "testwiese") == Game.world_id:
		var p: Array = data.get("position", [spawn_point.x, spawn_point.y, spawn_point.z])
		global_position = Vector3(float(p[0]), float(p[1]) + 0.1, float(p[2])) # etwas höher, damit man nicht im Boden steckt
		cam_yaw = float(data.get("cam_yaw", 0.0))
	velocity = Vector3.ZERO
	camera_pivot.global_position = global_position + Vector3(0, 1.55, 0)
	food_regen = float(data.get("food_regen", 0.0))
	food_time = float(data.get("food_time", 0.0))

	# JSON kennt nur Kommazahlen: Anzahlen und IDs wieder zu ganzen Zahlen machen
	inventory.items.clear()
	var saved_items: Dictionary = data.get("items", {})
	for id in saved_items:
		if Game.items.has(id):
			inventory.items[id] = int(saved_items[id])
	inventory.gear.clear()
	for g in data.get("gear", []):
		var gear: Dictionary = g
		if Game.items.has(gear.get("id", "")):
			gear["uid"] = int(gear["uid"])
			inventory.gear.append(gear)
	equipment.clear()
	var saved_equipment: Dictionary = data.get("equipment", {})
	for key in saved_equipment:
		var gear: Dictionary = saved_equipment[key]
		if Game.items.has(gear.get("id", "")):
			gear["uid"] = int(gear["uid"])
			equipment[key] = gear
	var saved_professions: Dictionary = data.get("professions", {})
	for id in saved_professions:
		if professions.has(id):
			professions[id] = {"level": int(saved_professions[id]["level"]), "xp": int(saved_professions[id]["xp"])}
	masteries.clear()
	var saved_masteries: Dictionary = data.get("masteries", {})
	for type in saved_masteries:
		if not Game.weapons.has(type):
			continue
		var m: Dictionary = saved_masteries[type]
		var unlocked: Array = []
		for node_id in m.get("unlocked", []):
			if not Game.tree_node(type, node_id).is_empty():
				unlocked.append(node_id)
		var equipped: Array = []
		for node_id in m.get("equipped", []):
			if unlocked.has(node_id):
				equipped.append(node_id)
		masteries[type] = {"level": int(m.get("level", 1)), "xp": float(m.get("xp", 0.0)),
			"unlocked": unlocked, "equipped": equipped}

	weapon_def = {} # erzwingt Neuaufbau der Waffe
	_recalc_stats()
	health = clampf(float(data.get("health", max_health)), 1.0, max_health)
	inventory.changed.emit()


# --- Interaktion --------------------------------------------------------

## Anzeigetext für das Objekt, mit dem man gerade interagieren kann (leer = keins).
func get_focus_prompt() -> String:
	if state != State.NORMAL or not _focus_valid():
		return ""
	var text := "[E]  %s" % focus.get_prompt()
	if focus_blocked():
		text += "   (benötigt %s %d)" % [Game.profession_name(focus.get_profession()), focus.get_required_level()]
	return text


func focus_blocked() -> bool:
	return _focus_valid() and get_profession_level(focus.get_profession()) < int(focus.get_required_level())


func _focus_valid() -> bool:
	return focus != null and is_instance_valid(focus) and focus.is_interactable()


func _update_focus() -> void:
	var best = null
	var best_dist := INF
	for node in get_tree().get_nodes_in_group("interactable"):
		var candidate = node
		if not candidate.is_interactable():
			continue
		var to: Vector3 = candidate.global_position - global_position
		to.y = 0.0
		var dist := to.length()
		if dist < float(candidate.interact_radius) and dist < best_dist:
			best_dist = dist
			best = candidate
	focus = best


# --- Aufbau -------------------------------------------------------------

func _build_model() -> void:
	model = Node3D.new()
	add_child(model)
	body_root = Node3D.new()
	body_root.position.y = 0.9
	model.add_child(body_root)

	var cloth := MeshUtil.mat(Color(0.22, 0.32, 0.52))
	var leather := MeshUtil.mat(Color(0.35, 0.22, 0.12))
	var skin := MeshUtil.mat(Color(0.86, 0.68, 0.55))
	var metal := MeshUtil.mat(Color(0.75, 0.77, 0.8), 0.8, 0.3)
	var wood := MeshUtil.mat(Color(0.45, 0.3, 0.16))

	var torso := CapsuleMesh.new()
	torso.radius = 0.32
	torso.height = 1.3
	MeshUtil.part(body_root, torso, cloth, Vector3(0, -0.05, 0))
	var belt := CylinderMesh.new()
	belt.top_radius = 0.335
	belt.bottom_radius = 0.335
	belt.height = 0.1
	MeshUtil.part(body_root, belt, leather, Vector3(0, -0.15, 0))
	var head := SphereMesh.new()
	head.radius = 0.2
	head.height = 0.4
	MeshUtil.part(body_root, head, skin, Vector3(0, 0.78, 0))
	# Stirnband zeigt, wohin die Figur schaut
	MeshUtil.part(body_root, MeshUtil.box(Vector3(0.26, 0.06, 0.06)), leather, Vector3(0, 0.8, -0.18))

	weapon_pivot = Node3D.new()
	body_root.add_child(weapon_pivot)
	offhand_pivot = Node3D.new()
	offhand_pivot.position = Vector3(-0.42, 0.05, -0.15)
	offhand_pivot.rotation_degrees = Vector3(15, -10, 0)
	body_root.add_child(offhand_pivot)

	shield_pivot = Node3D.new()
	shield_pivot.position = SHIELD_REST_POS
	shield_pivot.rotation_degrees = SHIELD_REST_ROT
	body_root.add_child(shield_pivot)
	MeshUtil.part(shield_pivot, MeshUtil.box(Vector3(0.62, 0.74, 0.07)), wood)
	MeshUtil.part(shield_pivot, MeshUtil.box(Vector3(0.66, 0.08, 0.08)), metal, Vector3(0, 0.33, 0))
	MeshUtil.part(shield_pivot, MeshUtil.box(Vector3(0.66, 0.08, 0.08)), metal, Vector3(0, -0.33, 0))
	var boss := SphereMesh.new()
	boss.radius = 0.09
	boss.height = 0.12
	MeshUtil.part(shield_pivot, boss, metal, Vector3(0, 0, -0.05))

	var aura_mesh := SphereMesh.new()
	aura_mesh.radius = 1.0
	aura_mesh.height = 2.0
	var aura_mat := StandardMaterial3D.new()
	aura_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	aura_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	aura_mat.albedo_color = Color(1.0, 0.8, 0.3, 0.15)
	aura_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	aura = MeshUtil.part(body_root, aura_mesh, aura_mat)
	aura.visible = false


func _weapon_rest_pos() -> Vector3:
	if is_ranged():
		return Vector3(0.22, 0.3, -0.3)
	if int(weapon_def.get("hands", 1)) == 2 and not weapon_def.get("dual", false):
		return Vector3(0.3, 0.1, -0.25)
	return Vector3(0.42, 0.05, -0.15)


func _weapon_rest_rot() -> Vector3:
	var r: Array = weapon_def.get("rest", [20, 15, 0])
	return Vector3(float(r[0]), float(r[1]), float(r[2]))


func _build_weapon_visual() -> void:
	for child in weapon_pivot.get_children():
		child.queue_free()
	for child in offhand_pivot.get_children():
		child.queue_free()
	WeaponModels.build(weapon_def.get("model", "sword"), weapon_pivot)
	if weapon_def.get("dual", false):
		WeaponModels.build(weapon_def.get("model", "dagger"), offhand_pivot)
	weapon_pivot.position = _weapon_rest_pos()
	weapon_pivot.rotation_degrees = _weapon_rest_rot()
	shield_pivot.visible = shield_active()
	shield_raised = false
	shield_pivot.position = SHIELD_REST_POS
	shield_pivot.rotation_degrees = SHIELD_REST_ROT


func _build_tools() -> void:
	tool_pivot = Node3D.new()
	tool_pivot.position = Vector3(0.42, 0.05, -0.15)
	body_root.add_child(tool_pivot)
	var wood := MeshUtil.mat(Color(0.5, 0.34, 0.18))
	var metal := MeshUtil.mat(Color(0.7, 0.72, 0.75), 0.8, 0.35)
	var string_mat := MeshUtil.mat(Color(0.9, 0.9, 0.9))

	var axe := _new_tool("axe")
	MeshUtil.part(axe, MeshUtil.box(Vector3(0.045, 0.045, 0.75)), wood, Vector3(0, 0, -0.3))
	MeshUtil.part(axe, MeshUtil.box(Vector3(0.04, 0.24, 0.2)), metal, Vector3(0, 0.08, -0.62))

	var pickaxe := _new_tool("pickaxe")
	MeshUtil.part(pickaxe, MeshUtil.box(Vector3(0.045, 0.045, 0.75)), wood, Vector3(0, 0, -0.3))
	MeshUtil.part(pickaxe, MeshUtil.box(Vector3(0.05, 0.55, 0.06)), metal, Vector3(0, 0.0, -0.66))

	var sickle := _new_tool("sickle")
	MeshUtil.part(sickle, MeshUtil.box(Vector3(0.04, 0.04, 0.28)), wood, Vector3(0, 0, -0.08))
	var blade := MeshUtil.part(sickle, MeshUtil.box(Vector3(0.015, 0.05, 0.4)), metal, Vector3(0.12, 0, -0.32))
	blade.rotation_degrees.y = -50.0

	var knife := _new_tool("knife")
	MeshUtil.part(knife, MeshUtil.box(Vector3(0.04, 0.04, 0.12)), wood, Vector3(0, 0, 0))
	MeshUtil.part(knife, MeshUtil.box(Vector3(0.012, 0.05, 0.24)), metal, Vector3(0, 0, -0.18))

	var rod := _new_tool("rod")
	MeshUtil.part(rod, MeshUtil.box(Vector3(0.03, 0.03, 1.9)), wood, Vector3(0, 0, -0.9))
	MeshUtil.part(rod, MeshUtil.box(Vector3(0.008, 1.4, 0.008)), string_mat, Vector3(0, -0.7, -1.85))


func _new_tool(id: String) -> Node3D:
	var t := Node3D.new()
	t.visible = false
	tool_pivot.add_child(t)
	tools[id] = t
	return t


func _show_tool(profession: String) -> void:
	var tool_id: String = Game.professions.get(profession, {}).get("tool", "")
	for id in tools:
		tools[id].visible = id == tool_id
	weapon_pivot.visible = tool_id == ""
	offhand_pivot.visible = tool_id == ""
	tool_pivot.rotation_degrees = Vector3.ZERO


func _hide_tool() -> void:
	for id in tools:
		tools[id].visible = false
	weapon_pivot.visible = true
	offhand_pivot.visible = true


func _build_camera() -> void:
	camera_pivot = Node3D.new()
	camera_pivot.top_level = true
	add_child(camera_pivot)
	camera_pivot.global_position = global_position + Vector3(0, 1.55, 0)
	camera_pitch_node = Node3D.new()
	camera_pivot.add_child(camera_pitch_node)
	spring_arm = SpringArm3D.new()
	spring_arm.spring_length = 4.2
	spring_arm.collision_mask = 1 | 8 # Welt + Baumkronen
	spring_arm.margin = 0.2
	spring_arm.position = Vector3(0.55, 0, 0)
	var probe := SphereShape3D.new()
	probe.radius = 0.2
	spring_arm.shape = probe
	camera_pitch_node.add_child(spring_arm)
	camera = Camera3D.new()
	camera.fov = 70.0
	spring_arm.add_child(camera)
	camera.current = true


# --- Eingabe & Kamera ---------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	var captured := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if event is InputEventMouseMotion and captured:
		var motion := event as InputEventMouseMotion
		var sens := MOUSE_SENSITIVITY * (0.6 if aiming else 1.0)
		cam_yaw -= motion.relative.x * sens
		cam_pitch = clampf(cam_pitch - motion.relative.y * sens, -1.2, 0.6)
	elif event is InputEventMouseButton and event.pressed and not captured and not ui_open:
		# Der Klick zum Einfangen der Maus soll keinen Angriff auslösen
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		swallow_click = true


func _process(delta: float) -> void:
	var target := global_position + Vector3(0, 1.55, 0)
	camera_pivot.global_position = camera_pivot.global_position.lerp(target, clampf(delta * 18.0, 0.0, 1.0))
	camera_pivot.rotation.y = cam_yaw
	camera_pitch_node.rotation.x = cam_pitch
	# Zielen: Kamera rückt näher an die Schulter
	var w := clampf(delta * 10.0, 0.0, 1.0)
	spring_arm.spring_length = lerpf(spring_arm.spring_length, 2.6 if aiming else 4.2, w)
	spring_arm.position.x = lerpf(spring_arm.position.x, 1.0 if aiming else 0.55, w)
	camera.fov = lerpf(camera.fov, 52.0 if aiming else 70.0, w)
	camera.h_offset = randf_range(-1.0, 1.0) * shake * 0.25
	camera.v_offset = randf_range(-1.0, 1.0) * shake * 0.25


# --- Hauptschleife ------------------------------------------------------

func _physics_process(delta: float) -> void:
	_update_timers(delta)
	var captured := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and not ui_open
	if captured and Input.is_action_just_pressed("debug_fly") and state != State.DEAD:
		set_debug_fly(not debug_fly)
	if debug_fly:
		_fly(delta, captured)
		return
	var input_dir := Vector2.ZERO
	if not ui_open:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var move_dir := Basis(Vector3.UP, cam_yaw) * Vector3(input_dir.x, 0.0, input_dir.y)

	if not is_on_floor():
		velocity.y -= GRAVITY * delta

	focus_timer -= delta
	if focus_timer <= 0.0:
		focus_timer = FOCUS_INTERVAL
		_update_focus()

	aiming = captured and is_ranged() and Input.is_action_pressed("block") \
		and (state == State.NORMAL or state == State.ACTION)

	if captured and (state == State.NORMAL or state == State.ACTION):
		if is_ranged():
			_handle_ranged_input()
		else:
			_handle_attack_input(delta)

	match state:
		State.NORMAL:
			_state_normal(delta, move_dir, captured)
		State.ACTION:
			_state_action(delta, move_dir, captured)
		State.DODGE:
			_state_dodge(delta)
		State.STAGGER:
			_state_stagger(delta)
		State.DEAD:
			_state_dead(delta)
		State.GATHER:
			_state_gather(delta, move_dir, captured)
		State.FISH:
			_state_fish(delta, move_dir, captured)

	move_and_slide()
	if global_position.y < -80.0: # tiefster Meeresboden der Insel liegt bei etwa −41 m
		_respawn()


func _update_timers(delta: float) -> void:
	iframes = maxf(iframes - delta, 0.0)
	combo_timer = maxf(combo_timer - delta, 0.0)
	shake = maxf(shake - delta, 0.0)
	for id in skill_cooldowns.keys():
		skill_cooldowns[id] = maxf(float(skill_cooldowns[id]) - delta, 0.0)
	for i in range(buffs.size() - 1, -1, -1):
		buffs[i]["time"] = float(buffs[i]["time"]) - delta
		if float(buffs[i]["time"]) <= 0.0:
			buffs.remove_at(i)
	aura.visible = not buffs.is_empty()
	if state == State.DEAD:
		return
	if stamina_delay > 0.0:
		stamina_delay -= delta
	elif not blocking:
		stamina = minf(stamina + STAMINA_REGEN * (1.0 + bonus("stamina_regen_pct")) * delta, max_stamina)
	combat_timer -= delta
	if combat_timer <= 0.0:
		health = minf(health + HEALTH_REGEN * delta, max_health)
	potion_cooldown = maxf(potion_cooldown - delta, 0.0)
	if food_time > 0.0:
		food_time -= delta
		health = minf(health + food_regen * delta, max_health)


func _move_speed_factor() -> float:
	return float(weapon_def.get("move_speed", 1.0)) * (1.0 + bonus("move_speed_pct"))


func _state_normal(delta: float, move_dir: Vector3, captured: bool) -> void:
	blocking = captured and not is_ranged() and Input.is_action_pressed("block") and stamina > 0.0 and is_on_floor()
	_set_block_pose(blocking)
	var moving := move_dir.length() > 0.1
	var speed := WALK_SPEED
	if blocking:
		speed = BLOCK_SPEED
	elif aiming:
		speed = AIM_SPEED
	elif captured and Input.is_action_pressed("sprint") and moving and stamina > 0.0:
		speed = SPRINT_SPEED
		_use_stamina(SPRINT_COST * delta, 0.3)
	_apply_horizontal(move_dir * speed * _move_speed_factor(), delta)

	if blocking or aiming:
		_face_angle(cam_yaw, delta, 20.0)
	elif moving:
		_face_angle(atan2(-move_dir.x, -move_dir.z), delta, 12.0)

	# Flinte/Armbrust laden automatisch nach
	if is_ranged() and not ranged_loaded:
		_start_reload()
		return

	if not captured:
		return
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY
	if Input.is_action_just_pressed("dodge") and is_on_floor():
		_start_dodge(move_dir)
		return
	for i in 3:
		if Input.is_action_just_pressed("skill_%d" % (i + 1)):
			_try_skill(i)
			return
	if Input.is_action_just_pressed("swap_weapon"):
		swap_weapons()
	if Input.is_action_just_pressed("interact") and _focus_valid() and is_on_floor():
		_start_interaction(focus)
	if Input.is_action_just_pressed("use_potion"):
		use_consumable("potion")
	if Input.is_action_just_pressed("use_food"):
		use_consumable("food")


# --- Sammeln, Häuten, Angeln --------------------------------------------

func _start_interaction(target) -> void:
	if target.has_method("get_station_id"):
		station_opened.emit(target.get_station_id())
		return
	var profession: String = target.get_profession()
	var required: int = target.get_required_level()
	if get_profession_level(profession) < required:
		message.emit("Benötigt %s Stufe %d" % [Game.profession_name(profession), required])
		return
	gather_target = target
	blocking = false
	_set_block_pose(false)
	_kill_anim(true)
	_show_tool(profession)
	var to: Vector3 = target.global_position - global_position
	model.rotation.y = atan2(-to.x, -to.z)
	velocity.x = 0.0
	velocity.z = 0.0

	if target.is_fishing():
		state = State.FISH
		_begin_fish_wait()
		tool_pivot.rotation_degrees = Vector3(35, 0, 0)
		return

	state = State.GATHER
	gather_time = 0.0
	# Abbauzeit = Lebenspunkte der Quelle / Abbaukraft des Werkzeugs; höhere Stufe macht etwas schneller
	gather_hp = float(target.get_gather_hp())
	var level_factor := 1.0 - minf(get_profession_level(profession), 50) * 0.006
	gather_total = gather_hp / get_tool_power(profession) * level_factor
	anim_tween = create_tween().set_loops()
	match profession:
		"harvesting":
			body_root.position.y = 0.7
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(-30, -70, 0), 0.25)
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(-30, 60, 0), 0.2)
		"skinning":
			body_root.position.y = 0.6
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(-20, 0, 0), 0.2)
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(-60, 10, 0), 0.15)
		_:
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(80, 10, 0), 0.3)
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(-35, -10, 0), 0.15)


func _wants_to_cancel(move_dir: Vector3, captured: bool) -> bool:
	if move_dir.length() > 0.1:
		return true
	return captured and (Input.is_action_just_pressed("attack") or Input.is_action_just_pressed("dodge") \
		or Input.is_action_just_pressed("jump"))


func _state_gather(delta: float, move_dir: Vector3, captured: bool) -> void:
	_apply_horizontal(Vector3.ZERO, delta)
	if _wants_to_cancel(move_dir, captured):
		_end_gather()
		return
	if gather_target == null or not is_instance_valid(gather_target) or not gather_target.is_interactable():
		_end_gather()
		return
	gather_time += delta
	if gather_time >= gather_total:
		var target = gather_target
		_end_gather()
		target.harvest(self)


func _begin_fish_wait() -> void:
	fish_phase = "wait"
	# Bessere Angel = kürzere Wartezeit
	fish_timer = randf_range(FISH_WAIT_MIN, FISH_WAIT_MAX) * Game.BASE_TOOL_POWER / get_tool_power("fishing")


func _state_fish(delta: float, move_dir: Vector3, captured: bool) -> void:
	_apply_horizontal(Vector3.ZERO, delta)
	if _wants_to_cancel(move_dir, captured) or gather_target == null or not is_instance_valid(gather_target) \
			or not gather_target.is_interactable():
		_end_gather()
		return
	var pressed := captured and Input.is_action_just_pressed("interact")
	fish_timer -= delta
	if fish_phase == "wait":
		if pressed:
			_end_gather() # Angel wieder einholen
		elif fish_timer <= 0.0:
			fish_phase = "bite"
			fish_timer = FISH_BITE_WINDOW * get_tool_power("fishing") / Game.BASE_TOOL_POWER \
				+ get_profession_level("fishing") * 0.02
			FX.popup(get_tree(), gather_target.global_position + Vector3(0, 0.8, 0), "!", Color(1.0, 0.9, 0.3), 120)
			_kill_anim(false)
			anim_tween = create_tween().set_loops()
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(20, 0, 0), 0.08)
			anim_tween.tween_property(tool_pivot, "rotation_degrees", Vector3(35, 0, 0), 0.08)
	elif pressed:
		var target = gather_target
		_end_gather()
		target.harvest(self)
	elif fish_timer <= 0.0:
		message.emit("Der Fisch ist entkommen …")
		_kill_anim(false)
		tool_pivot.rotation_degrees = Vector3(35, 0, 0)
		_begin_fish_wait()


func _end_gather() -> void:
	gather_target = null
	fish_phase = ""
	if state == State.GATHER or state == State.FISH:
		state = State.NORMAL
	_kill_anim(true)
	_hide_tool()


func _apply_horizontal(target: Vector3, delta: float) -> void:
	var accel := ACCELERATION if is_on_floor() else AIR_ACCELERATION
	var h := Vector3(velocity.x, 0.0, velocity.z).lerp(target, clampf(accel * delta, 0.0, 1.0))
	velocity.x = h.x
	velocity.z = h.z


func _face_angle(angle: float, delta: float, rate: float) -> void:
	model.rotation.y = lerp_angle(model.rotation.y, angle, clampf(rate * delta, 0.0, 1.0))


func _forward() -> Vector3:
	var f := -model.global_transform.basis.z
	f.y = 0.0
	return f.normalized()


func _use_stamina(amount: float, delay: float) -> void:
	stamina = maxf(stamina - amount, 0.0)
	stamina_delay = maxf(stamina_delay, delay)


# --- Nahkampf -----------------------------------------------------------

func _handle_attack_input(delta: float) -> void:
	if swallow_click:
		if not Input.is_action_pressed("attack"):
			swallow_click = false
		return
	if Input.is_action_just_pressed("attack"):
		attack_held = true
		attack_hold_time = 0.0
	if not attack_held:
		return
	if Input.is_action_pressed("attack"):
		attack_hold_time += delta
		if attack_hold_time >= HEAVY_HOLD_TIME and state == State.NORMAL:
			attack_held = false
			_start_heavy()
	else:
		attack_held = false
		if state == State.NORMAL:
			_start_light()
		elif state == State.ACTION and action.get("kind") == "light":
			buffered_light = true


func _start_light() -> void:
	var light: Array = weapon_def.get("light", [])
	if light.is_empty():
		return
	if combo_timer <= 0.0:
		combo_index = 0
	var idx := combo_index % light.size()
	_begin_melee(light[idx], "light")
	combo_index = idx + 1


func _start_heavy() -> void:
	var heavy: Dictionary = weapon_def.get("heavy", {})
	if not heavy.is_empty():
		_begin_melee(heavy, "heavy")


## Startet einen Nahkampfschlag aus den Moveset-Daten (data/weapons.json).
func _begin_melee(swing: Dictionary, kind: String) -> void:
	var speed := 1.0 + bonus("attack_speed")
	var hit := float(swing.get("hit", 0.2)) / speed
	_begin_action({
		"kind": kind,
		"duration": float(swing.get("dur", 0.5)) / speed,
		"hits": [hit],
		"mult": float(swing.get("mult", 1.0)),
		"range": float(swing.get("range", weapon_def.get("range", 2.3))),
		"arc": float(swing.get("arc", weapon_def.get("arc", 120))),
		"kb": float(swing.get("kb", 2.0)),
		"stag": float(swing.get("stag", 0.4)),
		"lunge": float(swing.get("lunge", 2.0)),
		"heavy": kind == "heavy",
	})
	_play_style(String(swing.get("style", "h_right")), hit)


# --- Fernkampf ----------------------------------------------------------

func _handle_ranged_input() -> void:
	if swallow_click:
		if not Input.is_action_pressed("attack"):
			swallow_click = false
		return
	var r: Dictionary = weapon_def.get("ranged", {})
	if state == State.NORMAL and Input.is_action_just_pressed("attack"):
		if r.get("kind", "") == "bow":
			_begin_action({"kind": "draw", "duration": INF, "hits": []})
			_kill_anim(false)
			anim_tween = create_tween()
			anim_tween.tween_property(weapon_pivot, "position:z", _weapon_rest_pos().z + 0.15, 0.3)
		elif ranged_loaded:
			_fire_ranged(1.0)
	elif state == State.ACTION and action.get("kind") == "draw" and not Input.is_action_pressed("attack"):
		var draw_time := float(r.get("draw_time", 0.9)) / (1.0 + bonus("reload_pct"))
		var charge := clampf(float(action["time"]) / draw_time, 0.25, 1.0)
		_fire_ranged(charge)


func _fire_ranged(charge: float) -> void:
	var r: Dictionary = weapon_def.get("ranged", {})
	model.rotation.y = cam_yaw
	_spawn_projectiles({
		"mult": float(r.get("mult", 1.0)) * charge, "speed": float(r.get("speed", 60)) * (0.6 + 0.4 * charge),
		"gravity": float(r.get("gravity", 0.0)), "projectile": r.get("projectile", "arrow"),
		"kb": float(r.get("kb", 1.0)), "stag": float(r.get("stag", 0.3)),
	})
	if r.get("kind", "") != "bow":
		ranged_loaded = false
		shake = maxf(shake, 0.15)
	_begin_action({"kind": "fire", "duration": 0.25 if r.get("kind", "") == "bow" else 0.35, "hits": []})
	_kill_anim(false)
	anim_tween = create_tween()
	anim_tween.tween_property(weapon_pivot, "rotation_degrees:x", 12.0, 0.06)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", _weapon_rest_rot(), 0.15)
	anim_tween.parallel().tween_property(weapon_pivot, "position", _weapon_rest_pos(), 0.15)


func _start_reload() -> void:
	var r: Dictionary = weapon_def.get("ranged", {})
	var duration := float(r.get("reload", 1.0)) / (1.0 + bonus("reload_pct"))
	_begin_action({"kind": "reload", "duration": duration, "hits": [], "keep_facing": true})
	_kill_anim(false)
	anim_tween = create_tween()
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", Vector3(-40, 20, 0), duration * 0.4)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", _weapon_rest_rot(), duration * 0.4)


## Zielpunkt in der Mitte des Bildschirms: erster Gegner oder Weltpunkt entlang des Kamerastrahls.
func _aim_point() -> Vector3:
	var origin := camera.global_position
	var dir := -camera.global_transform.basis.z
	var far := 150.0
	var query := PhysicsRayQueryParameters3D.create(origin, origin + dir * far, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	var best_t: float = far if hit.is_empty() else origin.distance_to(hit["position"])
	var point: Vector3 = origin + dir * best_t
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive():
			continue
		var center: Vector3 = enemy.get_center()
		var t := (center - origin).dot(dir)
		if t <= 0.0 or t >= best_t:
			continue
		if (origin + dir * t).distance_to(center) < float(enemy.radius) + 0.4:
			best_t = t
			point = center
	return point


func _spawn_projectiles(shot: Dictionary) -> void:
	var muzzle := global_position + Vector3(0, 1.45, 0) + _forward() * 0.6 \
		+ Basis(Vector3.UP, cam_yaw) * Vector3(0.3, 0, 0)
	var target := _aim_point()
	var dir := (target - muzzle).normalized()
	var speed := float(shot.get("speed", 60))
	var gravity := float(shot.get("gravity", 0.0))
	# Fallausgleich: etwas höher zielen, damit das Geschoss am Zielpunkt ankommt
	var dist := muzzle.distance_to(target)
	dir = (dir + Vector3.UP * gravity * dist / (2.0 * speed * speed)).normalized()
	var count := int(shot.get("count", 1))
	var spread := float(shot.get("spread", 0.0))
	for i in count:
		var angle := 0.0
		if count > 1:
			angle = deg_to_rad(-spread * 0.5 + spread * i / (count - 1))
		var p = ProjectileScript.new()
		p.shooter = self
		p.kind = shot.get("projectile", "arrow")
		p.velocity = dir.rotated(Vector3.UP, angle) * speed
		p.gravity = gravity
		p.hit_data = {
			"mult": float(shot.get("mult", 1.0)), "kb": float(shot.get("kb", 1.0)), "stag": float(shot.get("stag", 0.3)),
			"effects": shot.get("effects", {}), "pierce": shot.get("pierce", false), "explode": float(shot.get("explode", 0.0)),
		}
		p.position = muzzle
		get_tree().current_scene.add_child(p)


## Wird von Geschossen und Flächenangriffen aufgerufen.
func on_projectile_hit(enemy, hit_data: Dictionary, from_pos: Vector3) -> void:
	_deal_damage(enemy, float(hit_data.get("mult", 1.0)), float(hit_data.get("kb", 1.0)),
		float(hit_data.get("stag", 0.3)), hit_data.get("effects", {}), false, from_pos)
	combat_timer = 6.0
	shake = maxf(shake, 0.06)


# --- Fähigkeiten --------------------------------------------------------

func _try_skill(index: int) -> void:
	var equipped: Array = _mastery(weapon_type)["equipped"]
	if index >= equipped.size():
		message.emit("Keine Fähigkeit auf %s  (K: Skillbaum)" % Game.SKILL_KEYS[index])
		return
	var node := Game.tree_node(weapon_type, equipped[index])
	var skill: Dictionary = node.get("skill", {})
	if float(skill_cooldowns.get(node["id"], 0.0)) > 0.0:
		message.emit("%s ist noch nicht bereit" % node.get("name", ""))
		return
	skill_cooldowns[node["id"]] = _skill_cooldown(node)
	var speed := 1.0 + bonus("attack_speed")
	match String(skill.get("template", "")):
		"strike":
			var windup := float(skill.get("windup", 0.3)) / speed
			var hits: Array = []
			for i in int(skill.get("hits", 1)):
				hits.append(windup + i * float(skill.get("interval", 0.15)) / speed)
			_begin_action({
				"kind": "strike", "duration": maxf(float(skill.get("duration", 0.6)) / speed, hits[-1] + 0.15),
				"hits": hits, "mult": float(skill.get("mult", 1.0)), "range": float(skill.get("range", 2.5)),
				"arc": float(skill.get("arc", 120)), "kb": float(skill.get("kb", 2)), "stag": float(skill.get("stag", 0.5)),
				"effects": skill.get("effects", {}), "dash": float(skill.get("dash", 0.0)), "lunge": 0.0,
				"shockwave": skill.get("shockwave", false),
			})
			if skill.get("spin", false):
				_play_spin(hits[-1] + 0.1)
			else:
				_play_style(String(skill.get("style", "overhead")), windup)
		"dash":
			_begin_action({
				"kind": "dash", "duration": float(skill.get("time", 0.35)) + 0.2, "hits": [],
				"time_move": float(skill.get("time", 0.35)), "distance": float(skill.get("distance", 6)),
				"mult": float(skill.get("mult", 1.0)), "kb": float(skill.get("kb", 6)), "stag": float(skill.get("stag", 1.0)),
				"effects": skill.get("effects", {}), "hit_list": [],
			})
			_set_block_pose(true)
		"leap":
			var t := float(skill.get("time", 0.6))
			_begin_action({
				"kind": "leap", "duration": t + 0.25, "hits": [t], "time_move": t,
				"distance": float(skill.get("distance", 6)), "mult": float(skill.get("mult", 1.5)),
				"range": float(skill.get("radius", 3.0)), "arc": 360.0, "kb": float(skill.get("kb", 5)),
				"stag": float(skill.get("stag", 1.0)), "effects": skill.get("effects", {}), "shockwave": true,
			})
			velocity.y = GRAVITY * t * 0.5 # so hoch, dass man nach `t` Sekunden wieder landet
			_play_style("big_overhead", t)
		"buff":
			_begin_action({"kind": "buff", "duration": 0.35, "hits": []})
			_apply_buff(skill)
		"evade":
			var back: bool = skill.get("back", false)
			var dir := -_cam_forward() if back else _cam_forward()
			_begin_action({
				"kind": "evade", "duration": float(skill.get("time", 0.3)) + 0.1, "hits": [],
				"time_move": float(skill.get("time", 0.3)), "distance": float(skill.get("distance", 5)), "dir": dir,
				"keep_facing": true,
			})
			iframes = maxf(iframes, float(skill.get("iframes", 0.4)))
			if float(skill.get("duration", 0.0)) > 0.0:
				_apply_buff(skill)
		"shot":
			_begin_action({"kind": "fire", "duration": 0.4, "hits": []})
			_spawn_projectiles(skill)
			if not is_ranged():
				_play_style("overhead", 0.15)
		"zone":
			_begin_action({"kind": "fire", "duration": 0.5, "hits": []})
			var zone = ZoneScript.new()
			zone.shooter = self
			zone.radius = float(skill.get("radius", 4.0))
			zone.ticks = int(skill.get("ticks", 5))
			zone.interval = float(skill.get("interval", 0.4))
			zone.hit_data = {"mult": float(skill.get("mult", 0.5)), "kb": 0.5, "stag": 0.2, "effects": skill.get("effects", {})}
			zone.position = _aim_point()
			get_tree().current_scene.add_child(zone)


func _apply_buff(skill: Dictionary) -> void:
	var stats: Dictionary = skill.get("buffs", {})
	if not stats.is_empty():
		buffs.append({"stats": stats.duplicate(), "time": float(skill.get("duration", 5.0))})
	var heal := float(skill.get("heal_pct", 0.0)) * max_health
	if heal > 0.0:
		health = minf(health + heal, max_health)
		FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(heal), Color(0.4, 1.0, 0.4), 64)


func _cam_forward() -> Vector3:
	return Basis(Vector3.UP, cam_yaw) * Vector3.FORWARD


# --- Aktionen abspielen -------------------------------------------------

func _begin_action(data: Dictionary) -> void:
	action = data
	action["time"] = 0.0
	action["next_hit"] = 0
	state = State.ACTION
	blocking = false
	buffered_light = false
	if not data.get("keep_facing", false):
		model.rotation.y = cam_yaw # Angriffe gehen in Kamerarichtung
	if data["kind"] != "dash":
		_set_block_pose(false)


func _state_action(delta: float, move_dir: Vector3, captured: bool) -> void:
	action["time"] = float(action["time"]) + delta
	var t: float = action["time"]
	var kind: String = action["kind"]
	if not action.get("keep_facing", false):
		_face_angle(cam_yaw, delta, 10.0)
	var fwd := _forward()

	var vel := move_dir * ACTION_SPEED
	var hits: Array = action["hits"]
	if not hits.is_empty() and t < float(hits[0]):
		vel += fwd * (float(action.get("lunge", 0.0)) + float(action.get("dash", 0.0)) / float(hits[0]))
	match kind:
		"dash":
			if t < float(action["time_move"]):
				vel = fwd * (float(action["distance"]) / float(action["time_move"]))
				_path_hits()
			else:
				vel = Vector3.ZERO
		"leap":
			vel = fwd * (float(action["distance"]) / float(action["time_move"])) if t < float(action["time_move"]) else Vector3.ZERO
		"evade":
			var dir: Vector3 = action["dir"]
			vel = dir * (float(action["distance"]) / float(action["time_move"])) if t < float(action["time_move"]) else Vector3.ZERO
		"reload", "draw":
			vel = move_dir * AIM_SPEED * _move_speed_factor()
			if kind == "reload" and captured and Input.is_action_just_pressed("dodge") and is_on_floor():
				_end_action(false) # Ausweichen bricht das Nachladen ab
				_start_dodge(move_dir)
				return
	if kind in ["dash", "leap", "evade"]:
		velocity.x = vel.x
		velocity.z = vel.z
	else:
		_apply_horizontal(vel, delta * 2.0)

	var next := int(action["next_hit"])
	if next < hits.size() and t >= float(hits[next]):
		action["next_hit"] = next + 1
		_resolve_hit()

	if kind == "light" and buffered_light and t >= float(action["duration"]) * 0.55:
		buffered_light = false
		combo_timer = COMBO_WINDOW
		_start_light()
		return
	if t >= float(action["duration"]):
		if kind == "reload":
			ranged_loaded = true
		_end_action(true)


func _resolve_hit() -> void:
	if action.get("shockwave", false):
		FX.shockwave(get_tree(), global_position + _forward() * 0.5, float(action["range"]), Color(0.75, 0.65, 0.5, 0.6))
	_hit_arc(float(action["range"]), float(action["arc"]), float(action["mult"]), float(action["kb"]),
		float(action["stag"]), action.get("effects", {}), action.get("heavy", false))


func _end_action(allow_combo: bool) -> void:
	if allow_combo and action.get("kind") == "light":
		combo_timer = COMBO_WINDOW
	action = {}
	state = State.NORMAL


func _hit_arc(reach: float, arc: float, mult: float, knockback: float, stagger: float, effects: Dictionary, heavy: bool) -> void:
	var fwd := _forward()
	var hits := 0
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive():
			continue
		var to: Vector3 = enemy.global_position - global_position
		to.y = 0.0
		var dist := to.length()
		if dist > reach + float(enemy.radius):
			continue
		if arc < 360.0 and dist > 0.3 and rad_to_deg(fwd.angle_to(to / dist)) > arc * 0.5:
			continue
		_deal_damage(enemy, mult, knockback, stagger, effects, heavy, global_position)
		hits += 1
	if hits > 0:
		_on_hit_landed()


## Treffer entlang eines Ansturms (jeder Gegner nur einmal).
func _path_hits() -> void:
	var hit_list: Array = action["hit_list"]
	var fwd := _forward()
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if hit_list.has(enemy) or not enemy.is_alive():
			continue
		var to: Vector3 = enemy.global_position - global_position
		to.y = 0.0
		if to.length() > 1.4 + float(enemy.radius):
			continue
		if to.length() > 0.3 and rad_to_deg(fwd.angle_to(to.normalized())) > 70.0:
			continue
		hit_list.append(enemy)
		_deal_damage(enemy, float(action["mult"]), float(action["kb"]), float(action["stag"]), action.get("effects", {}),
			false, global_position)
		_on_hit_landed()


## Schaden aus Waffenwert × Angriffsfaktor, mit Boni, Krit, Blutung und Effekten der Fähigkeit.
func _deal_damage(enemy, mult: float, knockback: float, stagger: float, effects: Dictionary, heavy: bool, from_pos: Vector3) -> void:
	var weapon_damage := _stat("weapon", "damage", BASE_WEAPON_DAMAGE)
	var amount := weapon_damage * mult * (1.0 + _stat("weapon", "damage_pct") + bonus("damage_pct")) * randf_range(0.9, 1.1)
	if heavy:
		amount *= 1.0 + _stat("weapon", "heavy") + bonus("heavy")
	var crit := randf() < 0.05 + _stat("weapon", "crit") + bonus("crit")
	if crit:
		amount *= 1.5 + bonus("crit_damage")
	enemy.take_damage(amount, from_pos, knockback, stagger, crit)
	damage_dealt_total += amount
	add_mastery_xp(weapon_type, amount * MASTERY_XP_PER_DAMAGE)
	if not enemy.is_alive():
		return
	var bleed_dps := weapon_damage * 0.2 * (1.0 + bonus("damage_pct"))
	if effects.has("bleed"):
		enemy.apply_bleed(bleed_dps, float(effects["bleed"]))
	elif randf() < _stat("weapon", "bleed") + bonus("bleed"):
		enemy.apply_bleed(bleed_dps, 4.0)
	for kind in ["slow", "expose"]:
		if effects.has(kind):
			var e: Array = effects[kind]
			enemy.apply_debuff(kind, float(e[0]), float(e[1]))


func _on_hit_landed() -> void:
	combat_timer = 6.0
	shake = maxf(shake, 0.12)
	# Kurzer Hitstop für mehr Wucht
	Engine.time_scale = 0.1
	await get_tree().create_timer(0.05, true, false, true).timeout
	Engine.time_scale = 1.0


# --- Animationen (Platzhalter per Tween) ---------------------------------

func _kill_anim(reset_pose: bool) -> void:
	if anim_tween and anim_tween.is_valid():
		anim_tween.kill()
	if reset_pose:
		body_root.rotation = Vector3.ZERO
		body_root.position = Vector3(0, 0.9, 0)
		weapon_pivot.rotation_degrees = _weapon_rest_rot()
		weapon_pivot.position = _weapon_rest_pos()
	else:
		body_root.rotation.y = 0.0


func _play_style(style: String, hit_time: float) -> void:
	_kill_anim(false)
	var rest_rot := _weapon_rest_rot()
	var rest_pos := _weapon_rest_pos()
	anim_tween = create_tween()
	if style == "thrust":
		# Stoß: Waffe zeigt nach vorn, wird zurückgezogen und nach vorn gestoßen
		anim_tween.tween_property(weapon_pivot, "rotation_degrees", Vector3.ZERO, hit_time * 0.3)
		anim_tween.parallel().tween_property(weapon_pivot, "position", rest_pos + Vector3(0, 0.1, 0.25), hit_time * 0.6)
		anim_tween.tween_property(weapon_pivot, "position", rest_pos + Vector3(-0.1, 0.1, -0.5), hit_time * 0.4 + 0.03) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		anim_tween.tween_interval(0.06)
		anim_tween.tween_property(weapon_pivot, "position", rest_pos, 0.18)
		anim_tween.parallel().tween_property(weapon_pivot, "rotation_degrees", rest_rot, 0.18)
		return
	var poses: Array = SWING_STYLES.get(style, SWING_STYLES["h_right"])
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", poses[0], hit_time * 0.6) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", poses[1], hit_time * 0.4 + 0.04) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	anim_tween.tween_interval(0.08)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", rest_rot, 0.22).set_trans(Tween.TRANS_SINE)


func _play_spin(duration: float) -> void:
	_kill_anim(false)
	anim_tween = create_tween()
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", Vector3(0, -90, 0), 0.08)
	anim_tween.tween_property(body_root, "rotation:y", -TAU * maxf(1.0, roundf(duration / 0.45)), duration)
	anim_tween.tween_callback(func() -> void: body_root.rotation.y = 0.0)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", _weapon_rest_rot(), 0.15)


## Blockhaltung: mit Schild der Schild, sonst die Waffe quer vor dem Körper.
func _set_block_pose(raised: bool) -> void:
	if raised == shield_raised:
		return
	shield_raised = raised
	if shield_tween and shield_tween.is_valid():
		shield_tween.kill()
	shield_tween = create_tween().set_parallel(true)
	if shield_active():
		shield_tween.tween_property(shield_pivot, "position", SHIELD_BLOCK_POS if raised else SHIELD_REST_POS, 0.12)
		shield_tween.tween_property(shield_pivot, "rotation_degrees", SHIELD_BLOCK_ROT if raised else SHIELD_REST_ROT, 0.12)
	elif not is_ranged():
		shield_tween.tween_property(weapon_pivot, "rotation_degrees", WEAPON_BLOCK_ROT if raised else _weapon_rest_rot(), 0.12)


# --- Ausweichen, Taumeln, Tod -------------------------------------------

func _start_dodge(move_dir: Vector3) -> void:
	var cost := DODGE_COST * (1.0 - clampf(bonus("dodge_cost_pct"), 0.0, 0.7))
	if stamina < cost * 0.5:
		message.emit("Zu wenig Ausdauer")
		return
	_use_stamina(cost, 0.6)
	if move_dir.length() > 0.1:
		dodge_dir = move_dir.normalized()
	else:
		dodge_dir = Basis(Vector3.UP, cam_yaw) * Vector3.BACK
	model.rotation.y = atan2(-dodge_dir.x, -dodge_dir.z)
	state = State.DODGE
	state_timer = DODGE_TIME
	iframes = DODGE_IFRAMES
	blocking = false
	_set_block_pose(false)
	_kill_anim(true)
	anim_tween = create_tween()
	anim_tween.tween_property(body_root, "rotation:x", -TAU, DODGE_TIME * 0.9)
	anim_tween.tween_callback(func() -> void: body_root.rotation.x = 0.0)


func _state_dodge(delta: float) -> void:
	state_timer -= delta
	var t := clampf(state_timer / DODGE_TIME, 0.0, 1.0)
	var speed := DODGE_SPEED * (0.35 + 0.65 * t)
	velocity.x = dodge_dir.x * speed
	velocity.z = dodge_dir.z * speed
	if state_timer <= 0.0:
		state = State.NORMAL


func _stagger(duration: float, push: Vector3) -> void:
	if state == State.ACTION:
		_end_action(false)
	state = State.STAGGER
	state_timer = duration
	blocking = false
	_set_block_pose(false)
	velocity.x = push.x
	velocity.z = push.z
	_kill_anim(true)
	anim_tween = create_tween()
	anim_tween.tween_property(body_root, "rotation:x", 0.35, 0.1)
	anim_tween.tween_property(body_root, "rotation:x", 0.0, duration)


func _state_stagger(delta: float) -> void:
	state_timer -= delta
	_apply_horizontal(Vector3.ZERO, delta * 0.5)
	if state_timer <= 0.0:
		state = State.NORMAL


func take_damage(amount: float, from_pos: Vector3, unblockable := false) -> void:
	if state == State.DEAD or debug_fly:
		return
	if state == State.GATHER or state == State.FISH:
		_end_gather()
	combat_timer = 6.0
	var head := global_position + Vector3(0, 2.1, 0)
	if iframes > 0.0:
		FX.popup(get_tree(), head, "Ausgewichen", Color(0.7, 0.9, 1.0), 44)
		return
	var to_attacker := from_pos - global_position
	to_attacker.y = 0.0
	var away := -to_attacker.normalized()
	var in_front := to_attacker.length() < 0.01 or _forward().angle_to(to_attacker.normalized()) < deg_to_rad(75.0)

	if blocking and in_front and state == State.NORMAL and unblockable:
		FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Nicht blockbar!", Color(1.0, 0.35, 0.3), 44)
	elif blocking and in_front and state == State.NORMAL:
		# Schild: besserer Schild = weniger Ausdauer. Ohne Schild blockt die Waffe schlechter.
		var factor := BLOCK_STAMINA_FACTOR * 30.0 / (30.0 + block_power) if shield_active() \
			else float(weapon_def.get("block", 1.5))
		factor *= 1.0 - clampf(bonus("block_pct"), 0.0, 0.7)
		_use_stamina(amount * factor, 0.8)
		if stamina <= 0.0:
			message.emit("Deckung gebrochen!")
			_stagger(1.1, away * 4.0)
		else:
			FX.popup(get_tree(), head, "Geblockt", Color(0.8, 0.8, 0.8), 44)
			velocity += away * 2.5
		return

	amount *= 1.0 - clampf(bonus("damage_reduction"), 0.0, 0.75)
	amount *= 100.0 / (100.0 + armor) # Rüstung verringert den Schaden
	health = maxf(health - amount, 0.0)
	FX.popup(get_tree(), head, str(roundi(amount)), Color(1.0, 0.3, 0.25), 64)
	shake = 0.25
	hurt.emit()
	if health <= 0.0:
		_die()
	elif amount >= 25.0 and bonus("stagger_immune") <= 0.0 and state != State.DODGE:
		_stagger(0.45, away * 5.0)


func _die() -> void:
	_end_gather()
	state = State.DEAD
	state_timer = RESPAWN_TIME
	blocking = false
	action = {}
	buffs.clear()
	_set_block_pose(false)
	_kill_anim(true)
	anim_tween = create_tween().set_parallel(true)
	anim_tween.tween_property(body_root, "rotation:x", -PI / 2.0, 0.5).set_trans(Tween.TRANS_QUAD)
	anim_tween.tween_property(body_root, "position:y", 0.3, 0.5)
	died.emit()


func _state_dead(delta: float) -> void:
	state_timer -= delta
	_apply_horizontal(Vector3.ZERO, delta)
	if state_timer <= 0.0:
		_respawn()


func _respawn() -> void:
	global_position = spawn_point
	velocity = Vector3.ZERO
	health = max_health
	stamina = max_stamina
	state = State.NORMAL
	action = {}
	ranged_loaded = true
	_kill_anim(true)
	respawned.emit()
