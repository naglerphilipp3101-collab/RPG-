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
const MAX_EQUIPPED_SKILLS := 3
const WEAPON_SLOTS := ["weapon", "weapon2", "weapon3"] # der dritte Platz kommt mit der Level-40-Quest (M8)
const HEADSHOT_MULT := 1.5
const POISON_DPS_FACTOR := 0.06 # Giftschaden je Stapel und Sekunde, relativ zum Waffenschaden
const ULT_PER_HIT := 3.0 # Ladung der Ultimativen je Treffer
const ULT_PER_DAMAGE_TAKEN := 50.0 # Ladung, wenn man Schaden in Höhe der max. LP nimmt
const HEAVY_COST := 12.0 # Ausdauer für einen schweren Angriff
const SECONDARY_ATTRIBUTE_FACTOR := 0.5 # zweites Attribut einer Waffe zählt halb für den Schaden

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
	"cast": [Vector3(80, 0, 0), Vector3(-10, 0, 0)], # Zauber: Stab hochreißen und nach vorn stoßen
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
const BASE_MAX_HEALTH := 150.0 # dazu 10 je Punkt Vitalität (Start 5 → 200)
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
var weapon_slots := 2 # freigeschaltete Waffenplätze (2, später 3)
var quick_slots := 2 # freigeschaltete Schnellplätze für Tränke und Essen (2, später 4)
var ultimate_charge := 0.0 # eine Leiste für alle Waffen, 0 … Game.ULTIMATE_CHARGE
var stealth_time := 0.0 # Tarnung: Gegner bemerken einen nicht
var crit_ready := false # nächster Treffer ist kritisch (Riposte)
# Zustand der aktiven Waffen-Passiven
var passive_node: Dictionary = {}
var passive_mech := ""
var trotz := 0
var rhythm_stacks := 0
var rhythm_timer := 0.0
var momentum := 0.0
var sprint_time := 0.0
var charge_ready_time := 0.0 # Ansturm: so lange trifft der nächste Schlag verstärkt
var dodge_shot_ready := false # Plänkler
var magazine := 0 # Repetierer
var aim_time := 0.0 # Scharfschütze
var block_start := -10.0 # Zeitpunkt (s), an dem der Block begonnen hat (Parade)
var _skill_ctx: Dictionary = {} # Zusatzwerte der gerade ausgelösten Fähigkeit

# Magie (M7): Hitze (Feuer), Ladungen (Blitz), Beschwörungen (Leere); Frost und Brennen liegen auf den Gegnern
const HEAT_BASIC := 6.0
const HEAT_SKILL := 15.0
const HEAT_ULTIMATE := 25.0
const HEAT_DECAY := 12.0 # pro Sekunde, nach 1,5 s ohne Feuerzauber
const OVERHEAT_SILENCE := 3.0
const OVERHEAT_DAMAGE := 0.08 # Überhitzung ohne Glutherz kostet 8 % LP
const MAX_CHARGES := 5
const CHARGE_TIME := 6.0
const CHARGE_BONUS := 0.1 # je Ladung, die eine Fähigkeit verbraucht
const BURN_DPS_FACTOR := 0.25 # Brandschaden je Sekunde, relativ zum Waffenschaden
const FROST_TIME := 4.0
const SummonScript := preload("res://scripts/beschwoerung.gd")
var heat := 0.0
var heat_idle := 0.0
var overheat_ready := false # Glutherz: der nächste Zauber ist doppelt, danach Stille
var silence_time := 0.0
var charges := 0
var charge_time := 0.0
var cast_cooldown := 0.0
var summons: Array = []
var dodge_speed_mult := 1.0
var _dodge_start := Vector3.ZERO
var _winter_tick := 0.0
var damage_dealt_total := 0.0 # nur für Tests/Statistik

# Charakter: Level 1–100, Attribute mit Schwellenboni (data/attributes.json)
var char_level := 1
var char_xp := 0 # Erfahrung im aktuellen Level
var attribute_points: Dictionary = {} # Attribut-id -> verteilte Punkte
var attr_stats: Dictionary = {} # Werte aus Attributen (je Punkt und Schwellen), fließen in bonus()
var attr_mechanics: Dictionary = {} # freigeschaltete Schwellen-Mechaniken: id -> Wert (Chance, Stärke …)
var shield_hp := 0.0 # Schild aus Überheilung (Spiritual 200)
var still_time := 0.0 # Sekunden ohne Bewegung (Zielruhe)
var melee_hit_count := 0 # für Erdbeben (jeder 5. Treffer)
var skill_use_count := 0 # für Zahrfluss (jede 4. Fähigkeit)
var recent_skills: Array = [] # für Arkane Resonanz
var resonance_ready := false
var unbeugsam_cooldown := 0.0
var lebensquell_cooldown := 0.0
var heal_over_time := 0.0 # verbleibende Heilung pro Sekunde (Lebensquell)
var heal_over_time_left := 0.0
var _harvesting_neighbor := false
var _skill_resonance := false # gerade ausgelöste Fähigkeit ist durch Arkane Resonanz verstärkt

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
		professions[id] = {"level": 0, "xp": 0}
		tool_tiers[id] = 1
	for id in Game.attribute_ids():
		attribute_points[id] = 0

	_build_model()
	_build_tools()
	_build_camera()
	# Startausrüstung für ein neues Spiel (ein geladener Spielstand ersetzt sie)
	equipment["weapon"] = Game.roll_gear("training_sword_shield", [])
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
	return int(professions.get(id, {}).get("level", 0))


## Höchstes Tier, das mit dem aktuellen Skill abgebaut bzw. hergestellt werden kann.
func profession_tier(id: String) -> int:
	return mini(1 + get_profession_level(id) / Game.SKILL_PER_TIER, Game.TIER_NAMES.size())


## Höchstes Tier, das auf dem Kompass aufgespürt wird (0 = noch keins, erst ab Skill 25).
func track_tier(id: String) -> int:
	var level := get_profession_level(id)
	if level < Game.TRACK_OFFSET:
		return 0
	return mini(1 + (level - Game.TRACK_OFFSET) / Game.SKILL_PER_TIER, Game.TIER_NAMES.size())


## Chance auf ein zusätzliches Erzeugnis beim Verarbeiten: +1 % je 15 Skillpunkte (20 % bei 300).
func refining_bonus_chance(id: String) -> float:
	if Game.professions.get(id, {}).get("type", "") != "refining":
		return 0.0
	return floorf(get_profession_level(id) / 15.0) * 0.01


## Würfelt die Ausbeute einer Quelle mit allen Boni: Skill (bis 30 % ein Stück mehr), seltene Funde
## und doppelte Ausbeute aus den Attributsschwellen.
func gather_drops(profession: String, entries: Array, pick_one := false) -> Dictionary:
	var level := get_profession_level(profession)
	var drops := Game.roll_drops(entries, level, pick_one, 1.0 + bonus("rare:" + profession))
	if drops.is_empty():
		return drops
	if randf() < level * 0.001:
		var first: String = drops.keys()[0]
		drops[first] = int(drops[first]) + 1
	if randf() < bonus("double:" + profession):
		for id in drops:
			drops[id] = int(drops[id]) * 2
		notify.emit("Doppelte Ausbeute!", Color(1.0, 0.9, 0.4))
	return drops


## Zahrfluss (Intelligenz 500): Eine geerntete Pflanze wächst mit kleiner Chance sofort nach.
func regrows_instantly(profession: String) -> bool:
	if profession != "harvesting" or randf() >= float(attr_mechanics.get("nachwachsen", 0.0)):
		return false
	notify.emit("Die Pflanze wächst sofort nach", Color(0.6, 1.0, 0.6))
	return true


## Intelligenz 450: Ernte nimmt eine gleiche Pflanze im Umkreis mit.
func harvest_neighbor(source) -> void:
	if _harvesting_neighbor or not attr_mechanics.has("ernte_umkreis") or source.get_profession() != "harvesting":
		return
	var reach := float(attr_mechanics["ernte_umkreis"])
	for node in get_tree().get_nodes_in_group("interactable"):
		var other = node
		if other == source or other.get("node_id") != source.get("node_id") or not other.is_interactable():
			continue
		if other.global_position.distance_to(source.global_position) <= reach:
			_harvesting_neighbor = true
			other.harvest(self)
			_harvesting_neighbor = false
			return


func add_profession_xp(id: String, amount: int) -> void:
	if not professions.has(id) or amount <= 0:
		return
	var p: Dictionary = professions[id]
	p["xp"] = int(p["xp"]) + amount
	notify.emit("+%d EP %s" % [amount, Game.profession_name(id)], Color(0.6, 0.85, 1.0))
	var before := int(p["level"])
	while int(p["level"]) < Game.MAX_PROFESSION_LEVEL and int(p["xp"]) >= Game.xp_to_next(int(p["level"])):
		p["xp"] = int(p["xp"]) - Game.xp_to_next(int(p["level"]))
		p["level"] = int(p["level"]) + 1
	if int(p["level"]) >= Game.MAX_PROFESSION_LEVEL:
		p["xp"] = 0
	var after := int(p["level"])
	if after == before:
		return
	FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "%s %d" % [Game.profession_name(id), after], Color(0.5, 0.9, 1.0), 60)
	# Meldung nur bei neuen Tiers und Aufspür-Stufen, sonst wäre bei 300 Punkten ständig eine da
	for level in range(before + 1, after + 1):
		if level % Game.SKILL_PER_TIER == 0:
			message.emit("%s %d: Tier %s freigeschaltet!" % [Game.profession_name(id), level,
				Game.tier_name(1 + level / Game.SKILL_PER_TIER)])
		elif level % Game.SKILL_PER_TIER == Game.TRACK_OFFSET and Game.professions[id].get("type", "") == "gathering":
			message.emit("%s %d: Tier %s wird jetzt aufgespürt (Kompass)" % [Game.profession_name(id), level,
				Game.tier_name(1 + level / Game.SKILL_PER_TIER)])


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


# --- Charakterlevel & Attribute -----------------------------------------

func add_char_xp(amount: int) -> void:
	if amount <= 0 or char_level >= Game.MAX_CHAR_LEVEL:
		return
	char_xp += amount
	notify.emit("+%d EP" % amount, Color(0.75, 0.6, 1.0))
	var before := char_level
	while char_level < Game.MAX_CHAR_LEVEL and char_xp >= Game.char_xp_to_next(char_level):
		char_xp -= Game.char_xp_to_next(char_level)
		char_level += 1
	if char_level >= Game.MAX_CHAR_LEVEL:
		char_xp = 0
	if char_level > before:
		var points := Game.attribute_points_total(char_level) - Game.attribute_points_total(before)
		message.emit("Level %d!  +%d Attributspunkte (P)" % [char_level, points])
		FX.popup(get_tree(), global_position + Vector3(0, 2.5, 0), "Level %d!" % char_level, Color(0.8, 0.65, 1.0), 90)
		health = max_health
		equipment_changed.emit()


## Tod: 20 % der Erfahrung im aktuellen Level gehen verloren, ein Level kann man nicht verlieren.
func _apply_death_penalty() -> void:
	var loss := int(char_xp * Game.DEATH_XP_LOSS)
	if loss > 0:
		char_xp -= loss
		notify.emit("−%d EP (Tod)" % loss, Color(1.0, 0.45, 0.4))


## Gesamtwert eines Attributs: Grundwert + verteilte Punkte (später auch Ausrüstung und Essen).
func attribute_value(id: String) -> int:
	return Game.attribute_base() + int(attribute_points.get(id, 0))


func attribute_points_spent() -> int:
	var spent := 0
	for id in attribute_points:
		spent += int(attribute_points[id])
	return spent


func attribute_points_free() -> int:
	return Game.attribute_points_total(char_level) - attribute_points_spent()


func add_attribute_points(id: String, amount := 1) -> String:
	if not attribute_points.has(id):
		return "Unbekanntes Attribut"
	amount = mini(amount, attribute_points_free())
	if amount <= 0:
		return "Keine freien Punkte"
	attribute_points[id] = int(attribute_points[id]) + amount
	_recalc_stats()
	return ""


func reset_attributes() -> void:
	for id in attribute_points:
		attribute_points[id] = 0
	_recalc_stats()


func has_mechanic(id: String) -> bool:
	return attr_mechanics.has(id)


## Rechnet die Werte aller Attribute zusammen: Boni je Punkt, Schwellen und den Schadensbonus der Waffe
## (erstes Attribut der Waffe voll, zweites halb). Schwellen mit "ab" sind noch nicht im Spiel.
func _recalc_attributes() -> void:
	attr_stats = {}
	attr_mechanics = {}
	var scaling: Array = weapon_def.get("attributes", [])
	for id in Game.attribute_ids():
		var def := Game.attribute_def(id)
		var value := attribute_value(id)
		var per_point: Dictionary = def.get("per_point", {})
		var stats: Dictionary = per_point.get("stats", {})
		for stat in stats:
			_add_attr_stat(stat, float(stats[stat]) * value)
		var index := scaling.find(id)
		if index >= 0:
			var factor := 1.0 if index == 0 else SECONDARY_ATTRIBUTE_FACTOR
			_add_attr_stat("damage_pct", float(per_point.get("weapon_damage", 0.0)) * value * factor)
		for t in def.get("thresholds", []):
			var threshold: Dictionary = t
			if value < int(threshold["at"]) or threshold.has("ab"):
				continue
			var t_stats: Dictionary = threshold.get("stats", {})
			for stat in t_stats:
				_add_attr_stat(stat, float(t_stats[stat]))
			var mechanics: Dictionary = threshold.get("mechanics", {})
			for m in mechanics:
				attr_mechanics[m] = float(mechanics[m])
	var factors := {}
	for stat in attr_stats:
		if String(stat).begins_with("weight:"):
			factors[String(stat).substr(7)] = maxf(1.0 - float(attr_stats[stat]), 0.1)
	inventory.weight_factors = factors


func _add_attr_stat(stat: String, value: float) -> void:
	attr_stats[stat] = float(attr_stats.get(stat, 0.0)) + value


## Wird vom Gegner beim Tod aufgerufen: Charakter-EP voll, Waffen-EP nach Schadensanteil jeder Waffenart.
func on_enemy_killed(enemy, xp: int, damage_by_source: Dictionary) -> void:
	var total := 0.0
	for source in damage_by_source:
		total += float(damage_by_source[source])
	if total <= 0.0:
		return
	add_char_xp(xp)
	for source in damage_by_source:
		if Game.weapons.has(source):
			add_mastery_xp(source, xp * float(damage_by_source[source]) / total)
	if passive_mech == "inferno" and enemy.burn_time > 0.0:
		_inferno_explosion(enemy.global_position)
	if passive_mech == "beschwoerer":
		for summon in summons:
			if is_instance_valid(summon) and summon.kind == "wesen":
				summon.time_left += _pp("kill_extend")
	if has_mechanic("siegesrausch") and not is_ranged():
		buffs.append({"stats": {"damage_pct": float(attr_mechanics["siegesrausch"])}, "time": 5.0})
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Siegesrausch", Color(1.0, 0.5, 0.3), 48)


## Heilung mit Spiritual-Boni; Überheilung wird mit „Überfluss“ zum Schild.
func heal(amount: float, on_self := true) -> float:
	var factor := 1.0 + bonus("healing_pct")
	if health < max_health * 0.5:
		factor += bonus("heal_low_pct")
	if on_self:
		factor += bonus("self_heal_pct")
	if passive_mech == "heiler": # je weniger Leben, desto stärker
		factor += (1.0 - health / max_health) * _pp("max")
	amount *= factor
	if passive_mech == "segner" and amount >= 1.0:
		_bless()
	var missing := max_health - health
	health = minf(health + amount, max_health)
	if amount > missing and has_mechanic("ueberfluss"):
		shield_hp = minf(shield_hp + amount - missing, max_health * float(attr_mechanics["ueberfluss"]))
	return amount


# --- Ausrüstung & Werte -------------------------------------------------

func equip(uid: int) -> void:
	var g: Dictionary = inventory.take_gear(uid)
	if g.is_empty():
		return
	var key := Game.equip_key(g["id"])
	# Waffen füllen zuerst einen freien Waffenplatz
	if key == "weapon":
		for slot in active_weapon_slots():
			if not equipment.has(slot):
				key = slot
				break
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


func active_weapon_slots() -> Array:
	return WEAPON_SLOTS.slice(0, weapon_slots)


## Wechselt reihum zur nächsten angelegten Waffe (T, Mausrad). `step` −1 = rückwärts.
func swap_weapons(step := 1) -> void:
	var filled: Array = []
	for slot in active_weapon_slots():
		if equipment.has(slot):
			filled.append(equipment[slot])
	if filled.size() < 2:
		message.emit("Keine Zweitwaffe angelegt")
		return
	var shift := posmod(step, filled.size())
	for slot in active_weapon_slots():
		equipment.erase(slot)
	for i in filled.size():
		equipment[WEAPON_SLOTS[i]] = filled[(i + shift) % filled.size()]
	_recalc_stats()
	message.emit(Game.item_name(equipment["weapon"]["id"]))


func _stat(key: String, stat: String, fallback := 0.0) -> float:
	if not equipment.has(key):
		return fallback
	return float(equipment[key]["stats"].get(stat, fallback))


## Bonus aus passiven Skillknoten, Attributen und laufenden Buffs.
func bonus(stat: String) -> float:
	var value := float(passive.get(stat, 0.0)) + float(attr_stats.get(stat, 0.0))
	if stat == "attack_speed" and passive_mech == "rhythmus":
		value += minf(rhythm_stacks * _pp("per_hit"), _pp("max"))
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
	_recalc_attributes()

	damage_mult = _stat("weapon", "damage", BASE_WEAPON_DAMAGE) / BASE_WEAPON_DAMAGE \
		* (1.0 + _stat("weapon", "damage_pct") + float(passive.get("damage_pct", 0.0)) + float(attr_stats.get("damage_pct", 0.0)))
	crit_chance = 0.05 + _stat("weapon", "crit") + float(passive.get("crit", 0.0)) + float(attr_stats.get("crit", 0.0))
	bleed_chance = _stat("weapon", "bleed") + float(passive.get("bleed", 0.0))
	block_power = _stat("shield", "block") if shield_active() else 0.0
	armor = 0.0
	for key in ["head", "chest", "legs"]:
		armor += _stat(key, "armor")
	if shield_active():
		armor += _stat("shield", "armor")
	armor *= 1.0 + float(attr_stats.get("armor_pct", 0.0)) + float(passive.get("armor_pct", 0.0))
	var old_max := max_health
	max_health = BASE_MAX_HEALTH + _stat("ring", "health") + float(passive.get("health", 0.0)) \
		+ float(attr_stats.get("health", 0.0))
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

## Meisterschaftsdaten eines Waffentyps; beim ersten Mal geht der Punkt von Stufe 1 in die erste Fähigkeit der ersten Seite.
func _mastery(type: String) -> Dictionary:
	if not masteries.has(type):
		masteries[type] = {"level": 1, "xp": 0.0, "unlocked": [], "equipped": [], "passive": "", "ultimate": ""}
		var start := start_node(type)
		if start != "":
			masteries[type]["unlocked"].append(start)
			masteries[type]["equipped"].append(start)
	return masteries[type]


## Erste Fähigkeit der ersten Seite: von Anfang an freigeschaltet (kostet den Punkt von Stufe 1).
func start_node(type: String) -> String:
	var sides := Game.weapon_sides(type)
	if sides.is_empty() or sides[0]["skills"].is_empty():
		return ""
	return String(sides[0]["skills"][0]["id"])


## Punkte: Meisterschaft Stufe n gibt n Punkte, jeder Knoten kostet Game.node_cost (1).
func mastery_points_free(type: String) -> int:
	var m := _mastery(type)
	var spent := 0
	for node_id in m["unlocked"]:
		spent += Game.node_cost(Game.tree_node(type, node_id))
	return int(m["level"]) - spent


## Punkte, die in einer Seite stecken (für große Passive, untere Fähigkeiten und Ultimative).
func side_points(type: String, side: int) -> int:
	var m := _mastery(type)
	var spent := 0
	for node_id in m["unlocked"]:
		var node := Game.tree_node(type, node_id)
		if int(node.get("side", -1)) == side:
			spent += Game.node_cost(node)
	return spent


## Prüft, ob ein Knoten freigeschaltet werden kann. Gibt eine Fehlermeldung oder "" zurück.
## Ein Knoten braucht seinen Vorgänger ("req") und genug Punkte in seiner Seite ("points").
func unlock_check(type: String, node_id: String) -> String:
	var m := _mastery(type)
	if m["unlocked"].has(node_id):
		return "Bereits freigeschaltet"
	var node := Game.tree_node(type, node_id)
	if node.is_empty():
		return "Unbekannter Knoten"
	var req: String = node.get("req", "")
	if req != "" and not m["unlocked"].has(req):
		return "Zuerst „%s“ freischalten" % Game.tree_node(type, req).get("name", req)
	var need := int(node.get("points", 0))
	if side_points(type, int(node["side"])) < need:
		return "Braucht %d Punkte in dieser Seite" % need
	if Game.node_cost(node) > mastery_points_free(type):
		return "Nicht genug Punkte"
	return ""


## Alle freigeschalteten Knoten erfüllen ihre Bedingungen (nach dem Laden geprüft).
func tree_valid(type: String) -> bool:
	var m := _mastery(type)
	for node_id in m["unlocked"]:
		var node := Game.tree_node(type, node_id)
		var req: String = node.get("req", "")
		if (req != "" and not m["unlocked"].has(req)) or side_points(type, int(node["side"])) < int(node.get("points", 0)):
			return false
	return true


func unlock_node(type: String, node_id: String) -> String:
	var error := unlock_check(type, node_id)
	if error != "":
		return error
	var m := _mastery(type)
	m["unlocked"].append(node_id)
	var node := Game.tree_node(type, node_id)
	match String(node["type"]):
		"active":
			if m["equipped"].size() < MAX_EQUIPPED_SKILLS:
				m["equipped"].append(node_id)
		"passive":
			if m["passive"] == "":
				m["passive"] = node_id
		"ultimate":
			if m["ultimate"] == "":
				m["ultimate"] = node_id
	_recalc_stats()
	return ""


## Fähigkeit auf Q/E/R legen oder herunternehmen; bei Passiven und Ultimativen: diese aktiv setzen.
func toggle_skill(type: String, node_id: String) -> String:
	var m := _mastery(type)
	if not m["unlocked"].has(node_id):
		return "Noch nicht freigeschaltet"
	var node := Game.tree_node(type, node_id)
	match String(node.get("type", "")):
		"passive":
			m["passive"] = node_id
			_recalc_stats()
			return ""
		"ultimate":
			m["ultimate"] = node_id
			equipment_changed.emit()
			return ""
		"upgrade", "minor":
			return "" # wirken immer, sobald freigeschaltet
	if m["equipped"].has(node_id):
		m["equipped"].erase(node_id)
	elif m["equipped"].size() >= MAX_EQUIPPED_SKILLS:
		return "Höchstens %d Fähigkeiten gleichzeitig" % MAX_EQUIPPED_SKILLS
	else:
		m["equipped"].append(node_id)
	equipment_changed.emit()
	return ""


func reset_tree(type: String) -> void:
	_mastery(type)
	masteries[type]["unlocked"] = []
	masteries[type]["equipped"] = []
	masteries[type]["passive"] = ""
	masteries[type]["ultimate"] = ""
	var start := start_node(type)
	if start != "":
		masteries[type]["unlocked"].append(start)
		masteries[type]["equipped"].append(start)
	_recalc_stats()


## Von der aktiven Waffe wirken die gewählte große Passive (Werte und Mechanik) und alle kleinen Passiven.
func _recalc_passives() -> void:
	passive = {}
	var m := _mastery(weapon_type)
	var node := Game.tree_node(weapon_type, String(m.get("passive", ""))) if m.get("passive", "") != "" else {}
	if node.get("mechanic", "") != passive_mech:
		trotz = 0
		rhythm_stacks = 0
		momentum = 0.0
		magazine = 0
	passive_node = node
	passive_mech = String(node.get("mechanic", ""))
	var sources: Array = [node]
	for node_id in m["unlocked"]: # kleine Passiven wirken alle, solange die Waffe in der Hand ist
		var minor := Game.tree_node(weapon_type, node_id)
		if minor.get("type", "") == "minor":
			sources.append(minor)
	for source in sources:
		var stats: Dictionary = source.get("stats", {})
		for stat in stats:
			passive[stat] = float(passive.get(stat, 0.0)) + float(stats[stat])
	if passive_mech == "repetierer" and magazine <= 0:
		magazine = int(_pp("magazine"))


## Parameter der aktiven Passiven.
func _pp(key: String, fallback := 0.0) -> float:
	return Game.passive_param(passive_node, key, fallback)


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


## Info für die Fähigkeitenleiste: Name, Taste, Abklingzeit. Index 3 = Ultimative (Ladung statt Abklingzeit).
func get_skill_info(index: int) -> Dictionary:
	var m := _mastery(weapon_type)
	if index >= MAX_EQUIPPED_SKILLS:
		var ult := Game.tree_node(weapon_type, String(m["ultimate"])) if m["ultimate"] != "" else {}
		return {"name": ult.get("name", ""), "key": Game.ULTIMATE_KEY, "cooldown": Game.ULTIMATE_CHARGE,
			"remaining": Game.ULTIMATE_CHARGE - ultimate_charge, "ultimate": true}
	var equipped: Array = m["equipped"]
	if index >= equipped.size():
		return {"name": "", "key": Game.SKILL_KEYS[index], "cooldown": 1.0, "remaining": 0.0}
	var node := Game.tree_node(weapon_type, equipped[index])
	return {
		"name": node.get("name", ""), "key": Game.SKILL_KEYS[index],
		"cooldown": _skill_cooldown(node), "remaining": float(skill_cooldowns.get(node["id"], 0.0)),
	}


## Fähigkeit samt freigeschalteter Verbesserungen.
func skill_def(node: Dictionary) -> Dictionary:
	return Game.effective_skill(node, _mastery(weapon_type)["unlocked"])


func _skill_cooldown(node: Dictionary) -> float:
	var cd := float(skill_def(node).get("cooldown", 10.0)) * (1.0 - clampf(bonus("cooldown_pct"), 0.0, 0.6))
	if passive_mech == "berserker":
		cd *= _pp("cooldown_mult", 1.0)
	if is_magic():
		cd *= 1.0 - clampf(bonus("magic_cooldown_pct"), 0.0, 0.5)
	return cd


func ultimate_ready() -> bool:
	return ultimate_charge >= Game.ULTIMATE_CHARGE


func add_ultimate_charge(amount: float) -> void:
	var was_ready := ultimate_ready()
	ultimate_charge = clampf(ultimate_charge + amount, 0.0, Game.ULTIMATE_CHARGE)
	if not was_ready and ultimate_ready():
		notify.emit("Ultimative bereit  [%s]" % Game.ULTIMATE_KEY, Color(1.0, 0.75, 0.3))


func is_stealthed() -> bool:
	return stealth_time > 0.0


func _set_stealth(duration: float) -> void:
	if duration <= 0.0:
		return
	if stealth_time <= 0.0:
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Getarnt", Color(0.6, 0.6, 0.8), 48)
	stealth_time = maxf(stealth_time, duration)
	_stealth_look(true)


func _break_stealth() -> void:
	if stealth_time > 0.0:
		stealth_time = 0.0
		_stealth_look(false)


## Tarnung: Spielfigur halb durchsichtig.
func _stealth_look(on: bool) -> void:
	for child in model.find_children("*", "GeometryInstance3D", true, false):
		(child as GeometryInstance3D).transparency = 0.65 if on else 0.0


# --- Herstellen ---------------------------------------------------------

## Prüft ein Rezept. Gibt eine Fehlermeldung zurück oder "" wenn es möglich ist.
func craft_check(recipe_id: String, amount := 1, modifiers: Array = []) -> String:
	var recipe: Dictionary = Game.recipes.get(recipe_id, {})
	if recipe.is_empty():
		return "Unbekanntes Rezept"
	var profession: String = Game.stations[recipe["station"]]["profession"]
	if get_profession_level(profession) < int(recipe.get("level", 0)):
		return "Benötigt %s Skill %d" % [Game.profession_name(profession), int(recipe.get("level", 0))]
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
		# Verarbeiten: Chance auf ein zusätzliches Erzeugnis je Durchgang
		var extra := 0
		var chance := refining_bonus_chance(Game.stations[recipe["station"]]["profession"])
		for i in amount:
			if randf() < chance:
				extra += 1
		if inventory.space_for(output) >= count:
			inventory.add(output, count + mini(extra, inventory.space_for(output) - count))
			made = "%d× %s" % [count, Game.item_name(output)]
			if extra > 0:
				made += "  (+%d Bonus)" % extra
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

## Schnellplätze 1–4 (Game.QUICK_SLOTS): 1 Trank, 2 Essen; 3 und 4 kommen später über Level-Quests.
func use_quick_slot(index: int) -> void:
	var slot: Dictionary = Game.QUICK_SLOTS[index]
	if index >= quick_slots:
		message.emit("Platz %d (%s) ist noch gesperrt: %s" % [index + 1, slot["name"], slot.get("unlock", "")])
		return
	use_consumable(String(slot["kind"]))


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
		var healed := heal(float(effect.get("heal", 50)))
		potion_cooldown = POTION_COOLDOWN
		FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(healed), Color(0.4, 1.0, 0.4), 64)
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
		"char_level": char_level,
		"char_xp": char_xp,
		"attributes": attribute_points.duplicate(),
		"weapon_slots": weapon_slots,
		"quick_slots": quick_slots,
		"ultimate_charge": ultimate_charge,
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
	# Gegenstände aus der Zeit vor M6 (Einhand/Zweihand getrennt) bekommen ihre heutige ID
	inventory.items.clear()
	var saved_items: Dictionary = data.get("items", {})
	for id in saved_items:
		var new_id: String = Game.OLD_ITEM_IDS.get(id, id)
		if Game.items.has(new_id):
			inventory.items[new_id] = int(inventory.items.get(new_id, 0)) + int(saved_items[id])
	inventory.gear.clear()
	for g in data.get("gear", []):
		var gear: Dictionary = g
		gear["id"] = Game.OLD_ITEM_IDS.get(gear.get("id", ""), gear.get("id", ""))
		if Game.items.has(gear["id"]):
			gear["uid"] = int(gear["uid"])
			inventory.gear.append(gear)
	weapon_slots = clampi(int(data.get("weapon_slots", 2)), 2, WEAPON_SLOTS.size())
	quick_slots = clampi(int(data.get("quick_slots", 2)), 2, Game.QUICK_SLOTS.size())
	ultimate_charge = clampf(float(data.get("ultimate_charge", 0.0)), 0.0, Game.ULTIMATE_CHARGE)
	equipment.clear()
	var saved_equipment: Dictionary = data.get("equipment", {})
	for key in saved_equipment:
		var gear: Dictionary = saved_equipment[key]
		gear["id"] = Game.OLD_ITEM_IDS.get(gear.get("id", ""), gear.get("id", ""))
		if not Game.items.has(gear["id"]):
			continue
		gear["uid"] = int(gear["uid"])
		if key in WEAPON_SLOTS and not key in active_weapon_slots():
			inventory.gear.append(gear) # Waffenplatz noch gesperrt: zurück in die Tasche
		else:
			equipment[key] = gear
	# Spielstände vor Version 2 hatten Berufsstufen 1–50: Stufe 1/2/3 entspricht Skill 0/25/50
	var old_scale := int(data.get("_version", 2)) < 2
	var saved_professions: Dictionary = data.get("professions", {})
	for id in saved_professions:
		if professions.has(id):
			var level := int(saved_professions[id]["level"])
			var xp := int(saved_professions[id]["xp"])
			if old_scale:
				level = mini((level - 1) * 25, Game.MAX_PROFESSION_LEVEL)
				xp = 0
			professions[id] = {"level": clampi(level, 0, Game.MAX_PROFESSION_LEVEL), "xp": xp}
	char_level = clampi(int(data.get("char_level", 1)), 1, Game.MAX_CHAR_LEVEL)
	char_xp = int(data.get("char_xp", 0))
	var saved_attributes: Dictionary = data.get("attributes", {})
	for id in attribute_points:
		attribute_points[id] = maxi(int(saved_attributes.get(id, 0)), 0)
	if attribute_points_free() < 0: # sollte nicht vorkommen; sonst Punkte neu verteilen lassen
		reset_attributes()
	masteries.clear()
	var saved_masteries: Dictionary = data.get("masteries", {})
	var old_trees := int(data.get("_version", 4)) < 4 # 4: Skillbäume wie New World (1 Punkt je Knoten)
	for saved_type in saved_masteries:
		var m: Dictionary = saved_masteries[saved_type]
		var type: String = Game.OLD_WEAPON_TYPES.get(saved_type, saved_type)
		if not Game.weapons.has(type):
			continue
		var level := clampi(int(m.get("level", 1)), 1, Game.MAX_MASTERY_LEVEL)
		var xp := float(m.get("xp", 0.0))
		if masteries.has(type) and int(masteries[type]["level"]) >= level:
			continue # zusammengelegte Waffen: die höhere Meisterschaft zählt
		masteries.erase(type)
		var fresh := _mastery(type)
		fresh["level"] = level
		fresh["xp"] = xp
		if old_trees:
			continue # alte Skillbäume passen nicht mehr: Punkte werden erstattet
		for node_id in m.get("unlocked", []):
			if not Game.tree_node(type, node_id).is_empty() and not fresh["unlocked"].has(node_id):
				fresh["unlocked"].append(node_id)
		var equipped: Array = []
		for node_id in m.get("equipped", []):
			var node := Game.tree_node(type, node_id)
			if fresh["unlocked"].has(node_id) and node.get("type", "") == "active" and equipped.size() < MAX_EQUIPPED_SKILLS:
				equipped.append(node_id)
		fresh["equipped"] = equipped
		for key in ["passive", "ultimate"]:
			var id: String = m.get(key, "")
			fresh[key] = id if fresh["unlocked"].has(id) and Game.tree_node(type, id).get("type", "") == key else ""
		if mastery_points_free(type) < 0 or not tree_valid(type):
			reset_tree(type)
	if old_trees and not saved_masteries.is_empty():
		notify.emit("Skillbäume wurden überarbeitet: Skillpunkte erstattet (K)", Color(1.0, 0.85, 0.5))

	weapon_def = {} # erzwingt Neuaufbau der Waffe
	_recalc_stats()
	health = clampf(float(data.get("health", max_health)), 1.0, max_health)
	inventory.changed.emit()


# --- Interaktion --------------------------------------------------------

## Anzeigetext für das Objekt, mit dem man gerade interagieren kann (leer = keins).
func get_focus_prompt() -> String:
	if state != State.NORMAL or not _focus_valid():
		return ""
	var text := "[F]  %s" % focus.get_prompt()
	if focus_blocked():
		text += "   (benötigt %s Skill %d)" % [Game.profession_name(focus.get_profession()), focus.get_required_level()]
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
	WeaponModels.build(weapon_def.get("model", "sword"), weapon_pivot, Game.element_color(element()))
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
	elif captured and not ui_open and state == State.NORMAL and (event.is_action_pressed("weapon_next") \
			or event.is_action_pressed("weapon_prev")):
		swap_weapons(1 if event.is_action_pressed("weapon_next") else -1)
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
	var flat_speed := Vector2(velocity.x, velocity.z).length()
	still_time = still_time + delta if flat_speed < 0.3 else 0.0
	aim_time = aim_time + delta if aiming else 0.0
	if passive_mech == "momentum": # Schwung: Bewegung lädt, Stillstand baut langsam ab
		momentum = clampf(momentum + (delta / _pp("fill_time", 3.0) if flat_speed > 2.0 else -delta / 6.0), 0.0, 1.0)
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
	if stealth_time > 0.0:
		stealth_time -= delta
		if stealth_time <= 0.0:
			_stealth_look(false)
	if rhythm_stacks > 0:
		rhythm_timer -= delta
		if rhythm_timer <= 0.0:
			rhythm_stacks = 0
	charge_ready_time = maxf(charge_ready_time - delta, 0.0)
	_update_magic(delta)
	if state == State.DEAD:
		return
	if stamina_delay > 0.0:
		stamina_delay -= delta
	elif not blocking:
		stamina = minf(stamina + STAMINA_REGEN * (1.0 + bonus("stamina_regen_pct")) * delta, max_stamina)
	combat_timer -= delta
	var tough := has_mechanic("zaeh")
	if combat_timer <= 0.0:
		health = minf(health + HEALTH_REGEN * (2.0 if tough else 1.0) * delta, max_health)
	elif tough: # Zäh: im Kampf 1 % LP alle 5 s
		health = minf(health + max_health * float(attr_mechanics["zaeh"]) / 5.0 * delta, max_health)
	unbeugsam_cooldown = maxf(unbeugsam_cooldown - delta, 0.0)
	lebensquell_cooldown = maxf(lebensquell_cooldown - delta, 0.0)
	if has_mechanic("lebensquell") and lebensquell_cooldown <= 0.0 and health < max_health * 0.2:
		# Lebensquell: starke Heilung über 5 s, alle 60 s
		lebensquell_cooldown = 60.0
		heal_over_time = max_health * float(attr_mechanics["lebensquell"]) / 5.0
		heal_over_time_left = 5.0
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Lebensquell", Color(0.5, 1.0, 0.6), 56)
	if heal_over_time_left > 0.0:
		heal_over_time_left -= delta
		heal(heal_over_time * delta)
	potion_cooldown = maxf(potion_cooldown - delta, 0.0)
	if food_time > 0.0:
		food_time -= delta
		health = minf(health + food_regen * delta, max_health)


func _now() -> float:
	return Time.get_ticks_msec() / 1000.0


func _move_speed_factor() -> float:
	return float(weapon_def.get("move_speed", 1.0)) * (1.0 + bonus("move_speed_pct"))


func _state_normal(delta: float, move_dir: Vector3, captured: bool) -> void:
	var was_blocking := blocking
	blocking = captured and not is_ranged() and Input.is_action_pressed("block") and stamina > 0.0 and is_on_floor()
	if blocking and not was_blocking:
		block_start = _now()
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
		sprint_time += delta
		if passive_mech == "ansturm" and sprint_time >= _pp("sprint_time", 1.0):
			if charge_ready_time <= 0.0:
				FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Ansturm", Color(1.0, 0.8, 0.4), 40)
			charge_ready_time = 1.5
	else:
		sprint_time = 0.0
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
	for i in MAX_EQUIPPED_SKILLS:
		if Input.is_action_just_pressed("skill_%d" % (i + 1)):
			_try_skill(i)
			return
	if Input.is_action_just_pressed("ultimate"):
		_try_ultimate()
		return
	if Input.is_action_just_pressed("swap_weapon"):
		swap_weapons()
	if Input.is_action_just_pressed("interact") and _focus_valid() and is_on_floor():
		_start_interaction(focus)
	for i in Game.QUICK_SLOTS.size():
		if Input.is_action_just_pressed("quick_%d" % (i + 1)):
			use_quick_slot(i)


# --- Sammeln, Häuten, Angeln --------------------------------------------

func _start_interaction(target) -> void:
	if target.has_method("get_station_id"):
		station_opened.emit(target.get_station_id())
		return
	var profession: String = target.get_profession()
	var required: int = target.get_required_level()
	if get_profession_level(profession) < required:
		message.emit("Benötigt %s Skill %d" % [Game.profession_name(profession), required])
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
	# Skill bis 30 % schneller, dazu die Attribute (je Punkt und Schwellen)
	var level_factor := 1.0 - minf(get_profession_level(profession), Game.MAX_PROFESSION_LEVEL) * 0.001
	gather_total = gather_hp / get_tool_power(profession) * level_factor / (1.0 + bonus("gather_speed:" + profession))
	if randf() < float(attr_mechanics.get("sofort:" + profession, 0.0)):
		gather_total = 0.15 # mit einem Schlag (Erdbeben, Schwachstelle, Unbeugsam)
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
	fish_timer = randf_range(FISH_WAIT_MIN, FISH_WAIT_MAX) * Game.BASE_TOOL_POWER / get_tool_power("fishing") \
		/ (1.0 + bonus("gather_speed:fishing"))


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
			fish_timer = (FISH_BITE_WINDOW * get_tool_power("fishing") / Game.BASE_TOOL_POWER \
				+ get_profession_level("fishing") * 0.002) * (1.0 + bonus("fish_escape_pct"))
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
	if heavy.is_empty():
		return
	var cost := HEAVY_COST * (1.0 - clampf(bonus("heavy_cost_pct"), 0.0, 0.7))
	if stamina < cost * 0.5:
		message.emit("Zu wenig Ausdauer")
		return
	_use_stamina(cost, 0.4)
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
	if r.get("kind", "") == "magic": # Zauberstab: gedrückt halten zaubert fortlaufend
		if state == State.NORMAL and Input.is_action_pressed("attack") and cast_cooldown <= 0.0:
			if silence_time <= 0.0:
				_fire_ranged(1.0)
			elif Input.is_action_just_pressed("attack"):
				_can_cast()
		return
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
	var mult := float(r.get("mult", 1.0)) * charge * _shot_bonus()
	var magic: bool = r.get("kind", "") == "magic"
	if magic:
		mult *= _cast_heat(HEAT_BASIC)
		cast_cooldown = float(r.get("cast", 0.5)) / (1.0 + bonus("attack_speed"))
	if passive_mech == "repetierer":
		magazine -= 1
		if magazine <= 0: # der letzte Bolzen im Magazin trifft doppelt
			mult *= 2.0
	_spawn_projectiles({
		"mult": mult, "speed": float(r.get("speed", 60)) * (0.6 + 0.4 * charge),
		"gravity": float(r.get("gravity", 0.0)), "projectile": r.get("projectile", "arrow"),
		"kb": float(r.get("kb", 1.0)), "stag": float(r.get("stag", 0.3)), "aim_bonus": _aim_bonus(),
		"effects": r.get("effects", {}), "heal_on_hit": float(r.get("heal_on_hit", 0.0)),
	})
	if r.get("kind", "") != "bow" and not magic:
		ranged_loaded = false
		shake = maxf(shake, 0.15)
	_begin_action({"kind": "fire", "duration": 0.25 if r.get("kind", "") in ["bow", "magic"] else 0.35, "hits": []})
	_kill_anim(false)
	anim_tween = create_tween()
	anim_tween.tween_property(weapon_pivot, "rotation_degrees:x", 12.0, 0.06)
	anim_tween.tween_property(weapon_pivot, "rotation_degrees", _weapon_rest_rot(), 0.15)
	anim_tween.parallel().tween_property(weapon_pivot, "position", _weapon_rest_pos(), 0.15)


func _start_reload() -> void:
	var r: Dictionary = weapon_def.get("ranged", {})
	var duration := float(r.get("reload", 1.0))
	if passive_mech == "repetierer": # Magazin: schnell nachladen, leer dauert es doppelt so lang
		duration = _pp("quick", 0.3) if magazine > 0 else duration * 2.0
	duration /= 1.0 + bonus("reload_pct")
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
		p.color = Game.element_color(element())
		p.life = float(shot.get("life", 3.0))
		p.velocity = dir.rotated(Vector3.UP, angle) * speed
		p.gravity = gravity
		p.hit_data = {
			"mult": float(shot.get("mult", 1.0)), "kb": float(shot.get("kb", 1.0)), "stag": float(shot.get("stag", 0.3)),
			"effects": shot.get("effects", {}), "explode": float(shot.get("explode", 0.0)),
			"pierce": shot.get("pierce", false) or (passive_mech == "belagerer" and is_ranged()),
			"source": weapon_type, "resonance": _skill_resonance, "skill": shot.get("skill", false),
			"always_crit": shot.get("always_crit", false), "aim_bonus": float(shot.get("aim_bonus", 0.0)),
			"chain": int(shot.get("chain", 0)), "heal_on_hit": float(shot.get("heal_on_hit", 0.0)),
		}
		p.position = muzzle
		get_tree().current_scene.add_child(p)


## Plänkler: nach dem Ausweichen macht der nächste Schuss mehr Schaden.
func _shot_bonus() -> float:
	if passive_mech == "plaenkler" and dodge_shot_ready:
		dodge_shot_ready = false
		return 1.0 + _pp("bonus")
	return 1.0


## Scharfschütze: Bonus auf Kopftreffer je Sekunde Zielen.
func _aim_bonus() -> float:
	if passive_mech != "scharfschuetze":
		return 0.0
	return minf(aim_time * _pp("per_second"), _pp("max"))


## Wird von Geschossen und Flächenangriffen aufgerufen.
func on_projectile_hit(enemy, hit_data: Dictionary, from_pos: Vector3) -> void:
	var mult := float(hit_data.get("mult", 1.0)) * (1.0 + float(attr_mechanics.get("arkane_resonanz", 0.0)) \
		if hit_data.get("resonance", false) else 1.0)
	var ctx := {"skill": hit_data.get("skill", false), "always_crit": hit_data.get("always_crit", false),
		"headshot": hit_data.get("headshot", false), "aim_bonus": float(hit_data.get("aim_bonus", 0.0)),
		"trap": hit_data.get("trap", false), "chain": int(hit_data.get("chain", 0)),
		"heal_on_hit": float(hit_data.get("heal_on_hit", 0.0))}
	_deal_damage(enemy, mult, float(hit_data.get("kb", 1.0)),
		float(hit_data.get("stag", 0.3)), hit_data.get("effects", {}), false, from_pos, String(hit_data.get("source", "")), ctx)
	combat_timer = 6.0
	shake = maxf(shake, 0.06)


# --- Fähigkeiten --------------------------------------------------------

func _try_skill(index: int) -> void:
	var equipped: Array = _mastery(weapon_type)["equipped"]
	if index >= equipped.size():
		message.emit("Keine Fähigkeit auf %s  (K: Skillbaum)" % Game.SKILL_KEYS[index])
		return
	var node := Game.tree_node(weapon_type, equipped[index])
	if float(skill_cooldowns.get(node["id"], 0.0)) > 0.0:
		message.emit("%s ist noch nicht bereit" % node.get("name", ""))
		return
	if not _can_cast():
		return
	if passive_mech == "berserker": # Fähigkeiten kosten Leben, töten aber nie
		health = maxf(health - max_health * _pp("hp_cost"), 1.0)
	skill_cooldowns[node["id"]] = _skill_cooldown(node)
	_skill_resonance = _skill_mechanics(node)
	_cast_skill(node)
	_skill_resonance = false


## Ultimative (X): braucht eine volle Ladung, keine Abklingzeit.
func _try_ultimate() -> void:
	var m := _mastery(weapon_type)
	if m["ultimate"] == "":
		message.emit("Keine Ultimative gewählt  (K: Skillbaum)")
		return
	if not ultimate_ready():
		message.emit("Ultimative lädt noch (%d %%)" % roundi(ultimate_charge / Game.ULTIMATE_CHARGE * 100.0))
		return
	if not _can_cast():
		return
	ultimate_charge = 0.0
	var node := Game.tree_node(weapon_type, String(m["ultimate"]))
	FX.popup(get_tree(), global_position + Vector3(0, 2.4, 0), String(node.get("name", "")), Color(1.0, 0.7, 0.25), 72)
	shake = maxf(shake, 0.2)
	_cast_skill(node, true)


## Führt eine Fähigkeit oder Ultimative nach ihrer Vorlage (template) aus.
func _cast_skill(node: Dictionary, ultimate := false) -> void:
	var skill := skill_def(node)
	var effects: Dictionary = skill.get("effects", {}).duplicate()
	var mult_factor := _cast_heat(HEAT_ULTIMATE if ultimate else HEAT_SKILL)
	if element() == "lightning" and charges > 0: # Fähigkeiten entladen alle Ladungen
		mult_factor += charges * float(skill.get("charge_mult", CHARGE_BONUS))
		FX.popup(get_tree(), global_position + Vector3(0, 2.2, 0), "Entladen ×%d" % charges, Color(0.65, 0.8, 1.0), 44)
		charges = 0
	if passive_mech == "trotz" and trotz >= int(_pp("max", 5.0)): # voller Trotz: diese Fähigkeit betäubt
		trotz = 0
		effects["stun"] = maxf(float(effects.get("stun", 0.0)), _pp("stun", 2.0))
	if passive_mech == "momentum" and momentum > 0.0: # Schwung verbrauchen
		mult_factor += momentum * _pp("max_bonus")
		momentum = 0.0
	var ctx := {"skill": true, "always_crit": bool(skill.get("always_crit", false)),
		"execute": float(skill.get("execute", 0.0)), "ks_left": _pp("max"), "chain": int(skill.get("chain", 0)),
		"heal_per_hit": float(skill.get("heal_per_hit", 0.0))}
	var speed := 1.0 + bonus("attack_speed")
	match String(skill.get("template", "")):
		"strike":
			var windup := float(skill.get("windup", 0.3)) / speed
			var hits: Array = []
			for i in int(skill.get("hits", 1)):
				hits.append(windup + i * float(skill.get("interval", 0.15)) / speed)
			_begin_action({
				"kind": "strike", "duration": maxf(float(skill.get("duration", 0.6)) / speed, hits[-1] + 0.15),
				"hits": hits, "mult": float(skill.get("mult", 1.0)) * mult_factor, "range": float(skill.get("range", 2.5)),
				"arc": float(skill.get("arc", 120)), "kb": float(skill.get("kb", 2)), "stag": float(skill.get("stag", 0.5)),
				"effects": effects, "dash": float(skill.get("dash", 0.0)), "lunge": 0.0,
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
				"mult": float(skill.get("mult", 1.0)) * mult_factor, "kb": float(skill.get("kb", 6)), "stag": float(skill.get("stag", 1.0)),
				"effects": effects, "hit_list": [],
			})
			_set_block_pose(true)
		"leap":
			var t := float(skill.get("time", 0.6))
			_begin_action({
				"kind": "leap", "duration": t + 0.25, "hits": [t], "time_move": t,
				"distance": float(skill.get("distance", 6)), "mult": float(skill.get("mult", 1.5)) * mult_factor,
				"range": float(skill.get("radius", 3.0)), "arc": 360.0, "kb": float(skill.get("kb", 5)),
				"stag": float(skill.get("stag", 1.0)), "effects": effects, "shockwave": true,
			})
			velocity.y = GRAVITY * t * 0.5 # so hoch, dass man nach `t` Sekunden wieder landet
			_play_style("big_overhead", t)
		"buff":
			_begin_action({"kind": "buff", "duration": 0.35, "hits": []})
			_apply_buff(skill)
			_set_stealth(float(skill.get("stealth", 0.0)))
			if float(skill.get("taunt_radius", 0.0)) > 0.0:
				FX.shockwave(get_tree(), global_position, float(skill["taunt_radius"]), Color(1.0, 0.55, 0.3, 0.5))
				for e in get_tree().get_nodes_in_group("enemies"):
					var enemy = e
					if enemy.is_alive() and enemy.global_position.distance_to(global_position) <= float(skill["taunt_radius"]):
						enemy.apply_taunt(_taunt_time(float(effects.get("taunt", 6.0))))
		"evade":
			var back: bool = skill.get("back", false)
			var dir := -_cam_forward() if back else _cam_forward()
			_begin_action({
				"kind": "evade", "duration": float(skill.get("time", 0.3)) + 0.1, "hits": [],
				"time_move": float(skill.get("time", 0.3)), "distance": float(skill.get("distance", 5)), "dir": dir,
				"keep_facing": true,
			})
			iframes = maxf(iframes, float(skill.get("iframes", 0.4)))
			if passive_mech == "plaenkler":
				dodge_shot_ready = true
			if float(skill.get("duration", 0.0)) > 0.0:
				_apply_buff(skill)
		"shot":
			_begin_action({"kind": "fire", "duration": 0.4, "hits": []})
			var shot := skill.duplicate()
			shot["mult"] = float(skill.get("mult", 1.0)) * mult_factor * _shot_bonus()
			shot["effects"] = effects
			shot["skill"] = true
			shot["aim_bonus"] = _aim_bonus()
			_spawn_projectiles(shot)
			if not is_ranged():
				_play_style("overhead", 0.15)
		"zone":
			_begin_action({"kind": "fire", "duration": 0.5, "hits": []})
			var zone = ZoneScript.new()
			zone.shooter = self
			zone.radius = float(skill.get("radius", 4.0))
			zone.ticks = int(skill.get("ticks", 5))
			zone.interval = float(skill.get("interval", 0.4))
			zone.once = bool(skill.get("once", false))
			zone.delay = float(skill.get("delay", 0.0))
			zone.heal = float(skill.get("heal", 0.0))
			zone.color = Game.element_color(element()) if is_magic() else Color(1.0, 0.8, 0.35)
			zone.hit_data = {"mult": float(skill.get("mult", 0.5)) * mult_factor, "kb": 0.5, "stag": 0.2, "effects": effects,
				"source": weapon_type, "skill": true, "trap": zone.once, "chain": int(skill.get("chain", 0))}
			# Fallen liegen vor den Füßen, andere Flächen am Zielpunkt (höchstens 30 m entfernt)
			var target := _aim_point()
			if zone.once or skill.get("at_self", false):
				target = global_position + (Vector3.ZERO if skill.get("at_self", false) else _cam_forward() * 2.0)
			elif target.distance_to(global_position) > 30.0:
				target = global_position + (target - global_position).normalized() * 30.0
			zone.line = float(skill.get("line", 0.0))
			if zone.line > 0.0: # Linie: quer zur Blickrichtung am Ziel oder vom Spieler aus nach vorn
				var fwd := _cam_forward()
				zone.direction = fwd.cross(Vector3.UP) if skill.get("across", false) else fwd
				if not skill.get("across", false):
					target = global_position + fwd * (zone.line * 0.5 + 1.0)
			zone.position = target
			get_tree().current_scene.add_child(zone)
		"beam":
			var interval := float(skill.get("interval", 0.15))
			var beam_hits: Array = []
			for i in int(float(skill.get("duration", 1.5)) / interval):
				beam_hits.append(0.1 + i * interval)
			_begin_action({"kind": "beam", "duration": float(beam_hits[-1]) + 0.15, "hits": beam_hits,
				"mult": float(skill.get("mult", 0.3)) * mult_factor, "range": float(skill.get("range", 20.0)), "effects": effects})
		"detonate":
			_begin_action({"kind": "buff", "duration": 0.35, "hits": []})
			_detonate_burns(float(skill.get("radius", 15.0)), float(skill.get("mult", 1.5)) * mult_factor)
		"wall":
			_begin_action({"kind": "fire", "duration": 0.4, "hits": []})
			_spawn_ice_wall(float(skill.get("length", 7.0)), float(skill.get("time", 6.0)))
		"summon":
			_begin_action({"kind": "buff", "duration": 0.4, "hits": []})
			_summon(String(skill.get("kind", "wesen")), int(skill.get("count", 1)), float(skill.get("time", 15.0)),
				float(skill.get("mult", 0.5)) * mult_factor, bool(skill.get("big", false)))
		"sacrifice":
			_begin_action({"kind": "buff", "duration": 0.35, "hits": []})
			_sacrifice_summons(float(skill.get("radius", 3.0)), float(skill.get("mult", 2.0)) * mult_factor)
	if not action.is_empty():
		action["ctx"] = ctx
		if _skill_resonance:
			action["resonance"] = true
		if float(skill.get("stealth", 0.0)) > 0.0 and skill.get("template", "") != "buff":
			action["stealth_after"] = float(skill["stealth"]) # Tarnung erst nach den Treffern
	if float(skill.get("buff_time", 0.0)) > 0.0:
		_apply_buff({"buffs": skill.get("buffs", {}), "duration": float(skill["buff_time"])})


## Zahrfluss (jede 4. Fähigkeit ohne Abklingzeit) und Arkane Resonanz (nach drei verschiedenen Fähigkeiten
## macht die nächste mehr Schaden). Gibt zurück, ob diese Fähigkeit verstärkt ist.
func _skill_mechanics(node: Dictionary) -> bool:
	var id: String = node["id"]
	skill_use_count += 1
	if has_mechanic("zahrfluss") and skill_use_count % int(attr_mechanics["zahrfluss"]) == 0:
		skill_cooldowns[id] = 0.0
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Zahrfluss", Color(0.5, 0.8, 1.0), 48)
	if not has_mechanic("arkane_resonanz"):
		return false
	if resonance_ready:
		resonance_ready = false
		recent_skills.clear()
		return true
	recent_skills.append(id)
	if recent_skills.size() > 3:
		recent_skills.pop_front()
	if recent_skills.size() == 3 and recent_skills[0] != recent_skills[1] and recent_skills[1] != recent_skills[2] \
			and recent_skills[0] != recent_skills[2]:
		resonance_ready = true
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Arkane Resonanz", Color(0.6, 0.6, 1.0), 48)
	return false


func _apply_buff(skill: Dictionary) -> void:
	var stats: Dictionary = skill.get("buffs", {}).duplicate()
	if skill.has("hot"):
		stats["hot"] = float(skill["hot"]) # Heilung je Sekunde in Anteilen der max. LP
	var duration := float(skill.get("duration", 5.0))
	if passive_mech == "segner":
		duration *= 1.0 + _pp("duration")
	if not stats.is_empty():
		buffs.append({"stats": stats, "time": duration})
	var amount := float(skill.get("heal_pct", 0.0)) * max_health
	if amount > 0.0:
		amount = heal(amount)
		FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(amount), Color(0.4, 1.0, 0.4), 64)
	if skill.has("shield_pct"):
		_add_shield(max_health * float(skill["shield_pct"]))
	if skill.has("heat_to_shield"): # Abkühlen: Hitze wird zum Schild
		_add_shield(max_health * float(skill["heat_to_shield"]) * heat / 100.0)
		heat = 0.0
		overheat_ready = false
	if float(skill.get("invuln", 0.0)) > 0.0: # Eisblock: unverwundbar, aber festgefroren
		iframes = maxf(iframes, float(skill["invuln"]))
		_begin_action({"kind": "buff", "duration": float(skill["invuln"]), "hits": [], "keep_facing": true})
		FX.popup(get_tree(), global_position + Vector3(0, 2.3, 0), "Eisblock", Color(0.6, 0.85, 1.0), 52)


func _add_shield(amount: float) -> void:
	if amount <= 0.0:
		return
	shield_hp = minf(shield_hp + amount, max_health)
	FX.popup(get_tree(), global_position + Vector3(0, 2.2, 0), "+%d Schild" % roundi(amount), Color(0.7, 0.85, 1.0), 52)


func _cam_forward() -> Vector3:
	return Basis(Vector3.UP, cam_yaw) * Vector3.FORWARD


# --- Magie (M7) -----------------------------------------------------------

func is_magic() -> bool:
	return bool(weapon_def.get("magic", false))


func element() -> String:
	return String(weapon_def.get("element", ""))


## Elementarmeister (Intelligenz 300): Brennen, Frost und Ladung halten länger.
func _elemental_time(duration: float) -> float:
	return duration * (1.0 + float(attr_mechanics.get("elementarmeister", 0.0)))


func _burn_dps() -> float:
	return _stat("weapon", "damage", BASE_WEAPON_DAMAGE) * BURN_DPS_FACTOR * (1.0 + bonus("damage_pct"))


## Nach einer Überhitzung kann man kurz nicht zaubern.
func _can_cast() -> bool:
	if silence_time > 0.0:
		message.emit("Überhitzt: noch %d s" % ceili(silence_time))
		return false
	return true


## Feuerzauber erhitzen dich. Gibt den Schadensfaktor dieses Zaubers zurück (Glutherz: doppelt bei voller Hitze).
func _cast_heat(amount: float) -> float:
	if element() != "fire":
		return 1.0
	heat_idle = 0.0
	if overheat_ready:
		overheat_ready = false
		_overheat(false)
		return 2.0
	heat = minf(heat + amount, 100.0)
	if heat >= 100.0:
		if passive_mech == "glutherz":
			overheat_ready = true
			FX.popup(get_tree(), global_position + Vector3(0, 2.4, 0), "Glut!", Color(1.0, 0.45, 0.1), 56)
		else:
			_overheat(true)
	return 1.0


func _overheat(hurt: bool) -> void:
	heat = 0.0
	silence_time = OVERHEAT_SILENCE
	FX.popup(get_tree(), global_position + Vector3(0, 2.4, 0), "Überhitzt!", Color(1.0, 0.3, 0.1), 60)
	if hurt:
		health = maxf(health - max_health * OVERHEAT_DAMAGE, 1.0)


func _add_charge() -> void:
	charges = mini(charges + 1, MAX_CHARGES)
	charge_time = _elemental_time(CHARGE_TIME)


func _update_magic(delta: float) -> void:
	silence_time = maxf(silence_time - delta, 0.0)
	cast_cooldown = maxf(cast_cooldown - delta, 0.0)
	heat_idle += delta
	if heat_idle > 1.5 and not overheat_ready:
		heat = maxf(heat - HEAT_DECAY * delta, 0.0)
	if charges > 0:
		charge_time -= delta
		if charge_time <= 0.0:
			charges = 0
	if state == State.DEAD:
		return
	var hot := bonus("hot")
	if hot > 0.0:
		heal(max_health * hot * delta)
	_winter_tick -= delta
	if bonus("winter_aura") > 0.0 and _winter_tick <= 0.0: # Ewiger Winter: jede Sekunde Frost in 6 m
		_winter_tick = 1.0
		FX.shockwave(get_tree(), global_position, 6.0, Color(0.6, 0.85, 1.0, 0.35))
		for node in get_tree().get_nodes_in_group("enemies"):
			var enemy = node
			if enemy.is_alive() and enemy.global_position.distance_to(global_position) <= 6.0:
				enemy.add_frost(1, _elemental_time(FROST_TIME))
	if not summons.is_empty():
		summons = summons.filter(func(x): return is_instance_valid(x) and not x.is_queued_for_deletion())


## Segner: jede Heilung gibt kurz mehr Schaden (ein Segen, der sich erneuert).
func _bless() -> void:
	for b in buffs:
		if b.get("id", "") == "segen":
			b["time"] = _pp("time", 5.0)
			return
	buffs.append({"id": "segen", "stats": {"damage_pct": _pp("damage")}, "time": _pp("time", 5.0)})


## Blitze springen vom getroffenen Gegner auf weitere (je Sprung weniger Schaden). Leiter-Ziele bekommen immer einen Sprung.
func _chain_lightning(first, jumps: int, mult: float, source: String, is_skill: bool) -> void:
	var hit: Array = [first]
	var from: Vector3 = first.get_center()
	var marked: Array = []
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy != first and enemy.is_alive() and float(enemy.get_meta("conductor_until", 0.0)) > _now() \
				and enemy.global_position.distance_to(from) <= 15.0:
			marked.append(enemy)
	var reach := _pp("range", 6.0) if passive_mech == "sturmrufer" else 6.0
	var falloff := _pp("falloff", 0.3) if passive_mech == "sturmrufer" else 0.3
	var factor := 1.0
	for i in jumps + marked.size():
		var target = null
		if not marked.is_empty():
			target = marked.pop_front()
		else:
			var best := reach
			for node in get_tree().get_nodes_in_group("enemies"):
				var enemy = node
				if hit.has(enemy) or not enemy.is_alive():
					continue
				var d: float = enemy.get_center().distance_to(from)
				if d <= best:
					best = d
					target = enemy
		if target == null:
			break
		factor *= 1.0 - falloff
		hit.append(target)
		FX.beam(get_tree(), from, target.get_center(), Color(0.65, 0.8, 1.0), 0.18)
		_deal_damage(target, mult * factor, 0.5, 0.2, {}, false, from, source, {"chained": true, "skill": is_skill})
		from = target.get_center()


## Glutlanze: ein Strahlenstück auf den Gegner im Fadenkreuz.
func _beam_hit() -> void:
	var reach := float(action.get("range", 20.0))
	var from := global_position + Vector3(0, 1.4, 0) + _forward() * 0.5
	var target = _beam_target(reach)
	var color := Game.element_color(element())
	if target == null:
		FX.beam(get_tree(), from, from + _cam_forward() * reach, color, 0.16)
		return
	FX.beam(get_tree(), from, target.get_center(), color, 0.16)
	_deal_damage(target, float(action["mult"]), 0.3, 0.15, action.get("effects", {}), false, global_position, weapon_type,
		action.get("ctx", {}))


func _beam_target(reach: float):
	var origin := camera.global_position
	var dir := -camera.global_transform.basis.z
	var best = null
	var best_t := INF
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive() or enemy.global_position.distance_to(global_position) > reach:
			continue
		var center: Vector3 = enemy.get_center()
		var t := (center - origin).dot(dir)
		if t > 0.0 and t < best_t and (origin + dir * t).distance_to(center) < float(enemy.radius) + 0.6:
			best_t = t
			best = enemy
	return best


## Zündung: alle Brände in Reichweite lösen sofort aus.
func _detonate_burns(radius: float, mult: float) -> void:
	FX.shockwave(get_tree(), global_position, radius, Color(1.0, 0.5, 0.15, 0.5))
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_burning() or enemy.global_position.distance_to(global_position) > radius:
			continue
		var amount: float = enemy.consume_burn() * mult
		FX.shockwave(get_tree(), enemy.global_position, 2.0, Color(1.0, 0.45, 0.1, 0.7))
		enemy.take_damage(amount, enemy.global_position, 2.0, 0.6, false, weapon_type)
		damage_dealt_total += amount
		add_ultimate_charge(ULT_PER_HIT)


## Inferno: ein brennender Gegner explodiert beim Tod und entzündet alles in der Nähe.
func _inferno_explosion(center: Vector3) -> void:
	var radius := _pp("radius", 3.0)
	FX.shockwave(get_tree(), center, radius, Color(1.0, 0.45, 0.1, 0.75))
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy.is_alive() and enemy.global_position.distance_to(center) <= radius + float(enemy.radius):
			_deal_damage(enemy, _pp("mult", 0.8), 3.0, 0.5, {"burn": _pp("burn", 4.0)}, false, center, weapon_type,
				{"chained": true})


## Funkenläufer: Schaden entlang der Strecke des Blitzsprungs.
func _spark_line(from: Vector3, to: Vector3) -> void:
	if from.distance_to(to) < 0.5:
		return
	FX.beam(get_tree(), from + Vector3(0, 1.0, 0), to + Vector3(0, 1.0, 0), Color(0.65, 0.8, 1.0), 0.3)
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive():
			continue
		var p := Geometry3D.get_closest_point_to_segment(enemy.global_position, from, to)
		if p.distance_to(enemy.global_position) <= float(enemy.radius) + 1.0:
			_deal_damage(enemy, _pp("mult", 0.6), 2.0, 0.4, {}, false, from, weapon_type, {"chained": true})


## Eiswand quer zur Blickrichtung am Ziel (höchstens 20 m entfernt); hält Gegner auf.
func _spawn_ice_wall(length: float, duration: float) -> void:
	var target := _aim_point()
	if target.distance_to(global_position) > 20.0:
		target = global_position + (target - global_position).normalized() * 20.0
	target.y = global_position.y
	var wall := StaticBody3D.new()
	wall.collision_layer = 1
	wall.collision_mask = 0
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(length, 2.6, 0.7)
	shape.shape = box
	shape.position.y = 1.3
	wall.add_child(shape)
	var ice := MeshUtil.mat(Color(0.65, 0.88, 1.0, 0.7), 0.0, 0.1)
	ice.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	MeshUtil.part(wall, MeshUtil.box(box.size), ice, Vector3(0, 1.3, 0))
	get_tree().current_scene.add_child(wall)
	wall.global_position = target
	wall.rotation.y = cam_yaw
	wall.add_to_group("eiswand")
	var tw := wall.create_tween()
	tw.tween_interval(duration)
	tw.tween_callback(wall.queue_free)


## Beschwörungen: Leerenwesen (greifen den nächsten Gegner an) oder Klingen (kreisen um dich).
func _summon(kind: String, count: int, duration: float, mult: float, big: bool) -> void:
	if kind == "klinge": # neue Klingen ersetzen die alten
		for summon in summons:
			if is_instance_valid(summon) and summon.kind == "klinge":
				summon.queue_free()
		summons = summons.filter(func(x): return is_instance_valid(x) and x.kind != "klinge")
	for i in count:
		var summon = SummonScript.new()
		summon.shooter = self
		summon.kind = kind
		summon.time_left = duration
		summon.mult = mult
		summon.big = big
		summon.index = i
		summon.count = count
		summon.source = weapon_type
		summon.color = Game.element_color(element())
		get_tree().current_scene.add_child(summon)
		summon.global_position = global_position + Vector3(randf_range(-1.0, 1.0), 1.2, randf_range(-1.0, 1.0))
		summons.append(summon)
	# Ohne Beschwörer höchstens 1 Leerenwesen, mit Beschwörer 2 (eine Ultimative darf mehr rufen)
	var limit := maxi(int(_pp("max", 1.0)) if passive_mech == "beschwoerer" else 1, count if kind == "wesen" else 0)
	var beings: Array = summons.filter(func(x): return x.kind == "wesen")
	while beings.size() > limit:
		var oldest = beings.pop_front()
		summons.erase(oldest)
		oldest.queue_free()
	FX.shockwave(get_tree(), global_position, 2.5, Color(0.65, 0.3, 0.95, 0.6))


## Opfer: alle Beschwörungen explodieren.
func _sacrifice_summons(radius: float, mult: float) -> void:
	if summons.is_empty():
		message.emit("Keine Beschwörung zum Opfern")
		return
	for summon in summons:
		if not is_instance_valid(summon):
			continue
		var center: Vector3 = summon.global_position
		FX.shockwave(get_tree(), center, radius, Color(0.65, 0.3, 0.95, 0.75))
		for node in get_tree().get_nodes_in_group("enemies"):
			var enemy = node
			if enemy.is_alive() and enemy.get_center().distance_to(center) <= radius + float(enemy.radius):
				_deal_damage(enemy, mult, 4.0, 0.6, {}, false, center, summon.source, {"summon": true, "skill": true})
		summon.queue_free()
	summons.clear()


## Treffer einer Beschwörung (zählt für die Waffe, mit der sie gerufen wurde).
func summon_hit(enemy, mult: float, from: Vector3, source: String) -> void:
	_deal_damage(enemy, mult, 1.0, 0.2, {}, false, from, source, {"summon": true})


## Kurztext für die Anzeige: Hitze, Ladungen oder Beschwörungen der aktiven Magiewaffe.
func element_status() -> String:
	match element():
		"fire":
			if silence_time > 0.0:
				return "Überhitzt: %d s" % ceili(silence_time)
			return "Hitze %d %%" % roundi(heat) + ("  ·  Glut bereit" if overheat_ready else "")
		"lightning":
			return "Ladung " + "●".repeat(charges) + "○".repeat(MAX_CHARGES - charges)
		"void":
			return "Beschwörungen %d" % summons.size() if not summons.is_empty() else ""
	return ""


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
			if passive_mech == "repetierer" and magazine <= 0:
				magazine = int(_pp("magazine", 4.0))
		_end_action(true)


func _resolve_hit() -> void:
	if action.get("kind") == "beam":
		_beam_hit()
		return
	if action.get("shockwave", false):
		FX.shockwave(get_tree(), global_position + _forward() * 0.5, float(action["range"]), Color(0.75, 0.65, 0.5, 0.6))
	var mult := float(action["mult"])
	if action.get("resonance", false):
		mult *= 1.0 + float(attr_mechanics.get("arkane_resonanz", 0.0))
	_hit_arc(float(action["range"]), float(action["arc"]), mult, float(action["kb"]),
		float(action["stag"]), action.get("effects", {}), action.get("heavy", false), action.get("ctx", {}))


func _end_action(allow_combo: bool) -> void:
	if allow_combo and action.get("kind") == "light":
		combo_timer = COMBO_WINDOW
	if action.has("stealth_after"):
		_set_stealth(float(action["stealth_after"]))
	action = {}
	state = State.NORMAL


func _hit_arc(reach: float, arc: float, mult: float, knockback: float, stagger: float, effects: Dictionary, heavy: bool,
		ctx: Dictionary = {}) -> void:
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
		ctx["reach_frac"] = dist / (reach + float(enemy.radius)) # Phalanx: Treffer mit der Speerspitze
		_deal_damage(enemy, mult, knockback, stagger, effects, heavy, global_position, "", ctx)
		hits += 1
	if hits > 0:
		_on_hit_landed()
		if float(ctx.get("heal_per_hit", 0.0)) > 0.0:
			var healed := heal(max_health * float(ctx["heal_per_hit"]) * hits)
			FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(healed), Color(0.4, 1.0, 0.4), 56)
	if hits > 1 and passive_mech == "klingensturm" and ctx.get("skill", false):
		# Klingensturm: jeder weitere getroffene Gegner verkürzt alle Abklingzeiten (begrenzt je Fähigkeit)
		var cut := minf((hits - 1) * _pp("per_enemy"), float(ctx.get("ks_left", 0.0)))
		ctx["ks_left"] = float(ctx.get("ks_left", 0.0)) - cut
		for id in skill_cooldowns:
			skill_cooldowns[id] = maxf(float(skill_cooldowns[id]) - cut, 0.0)


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
			false, global_position, "", action.get("ctx", {}))
		_on_hit_landed()


## Schaden aus Waffenwert × Angriffsfaktor, mit Boni, Krit, Blutung und Effekten der Fähigkeit.
## `source` = Waffenart, der der Schaden zählt (Geschosse merken sich die Waffe beim Abschuss).
## `ctx`: skill (Fähigkeit statt normalem Angriff), always_crit, execute, headshot, aim_bonus, trap, reach_frac.
func _deal_damage(enemy, mult: float, knockback: float, stagger: float, effects: Dictionary, heavy: bool, from_pos: Vector3,
		source := "", ctx: Dictionary = {}) -> void:
	var ranged_hit := source != ""
	if source == "":
		source = weapon_type
	var is_skill: bool = ctx.get("skill", false)
	var weapon_damage := _stat("weapon", "damage", BASE_WEAPON_DAMAGE)
	var amount := weapon_damage * mult * (1.0 + _stat("weapon", "damage_pct") + bonus("damage_pct")) * randf_range(0.9, 1.1)
	if heavy:
		amount *= 1.0 + _stat("weapon", "heavy") + bonus("heavy")
	if ranged_hit and is_ranged() and still_time >= 1.0:
		amount *= 1.0 + float(attr_mechanics.get("zielruhe", 0.0))
	if ctx.get("headshot", false):
		amount *= HEADSHOT_MULT + float(attr_mechanics.get("schwachstelle", 0.0)) + float(ctx.get("aim_bonus", 0.0))
	var elem := Game.element_of(source)
	if Game.weapon_def(source).get("magic", false):
		amount *= 1.0 + bonus("magic_damage_pct")
	if elem == "fire" and heat > 0.0: # Hitze: +1 % je 10 Hitze, mit Glutherz +3 %
		amount *= 1.0 + heat / 10.0 * (_pp("per_10") if passive_mech == "glutherz" else 0.01)
	var shatter: bool = passive_mech == "zerschmettern" and enemy.is_frozen()
	if shatter:
		amount *= 1.0 + _pp("bonus")
	var execute: float = ctx.get("execute", 0.0)
	if execute > 0.0 and enemy.health < enemy.max_health * execute:
		amount *= 2.0
	var charged := passive_mech == "ansturm" and charge_ready_time > 0.0
	if charged:
		charge_ready_time = 0.0
	amount *= _passive_damage_mult(enemy, is_skill, charged, ctx)
	if passive_mech == "zertruemmerer" and is_skill: # Prozent der max. LP je Rüstungsbruch-Stapel
		amount += enemy.max_health * _pp("pct_per_stack") * int(enemy.sunder_stacks)
	var crit: bool = ctx.get("always_crit", false) or crit_ready or (passive_mech == "schatten" and is_stealthed()) \
		or randf() < 0.05 + _stat("weapon", "crit") + bonus("crit")
	crit_ready = false
	if crit:
		amount *= 1.5 + bonus("crit_damage")
		if has_mechanic("schneller_finger"):
			for id in skill_cooldowns:
				skill_cooldowns[id] = maxf(float(skill_cooldowns[id]) - float(attr_mechanics["schneller_finger"]), 0.0)
	enemy.take_damage(amount, from_pos, knockback, stagger, crit, source)
	damage_dealt_total += amount
	add_ultimate_charge(ULT_PER_HIT)
	_break_stealth() # Angreifen beendet die Tarnung
	if bonus("lifesteal") > 0.0:
		heal(amount * bonus("lifesteal"))
	if float(ctx.get("heal_on_hit", 0.0)) > 0.0:
		heal(amount * float(ctx["heal_on_hit"]))
	if shatter:
		enemy.break_ice()
		FX.popup(get_tree(), enemy.global_position + Vector3(0, 2.6, 0), "Zerschmettert", Color(0.7, 0.9, 1.0), 48)
	var own_hit: bool = not ctx.get("chained", false) and not ctx.get("summon", false)
	if elem == "lightning" and own_hit:
		_add_charge()
	if passive_mech == "klingenbinder" and own_hit:
		for summon in summons:
			if is_instance_valid(summon) and summon.kind == "klinge" and enemy.is_alive():
				summon.strike(enemy)
	if elem == "lightning" and not ctx.get("chained", false):
		var jumps := int(ctx.get("chain", 0)) + (int(_pp("jumps")) if passive_mech == "sturmrufer" else 0)
		_chain_lightning(enemy, jumps, mult, source, ctx.get("skill", false))
	if not ranged_hit and has_mechanic("erdbeben"):
		melee_hit_count += 1
		if melee_hit_count % 5 == 0:
			_earthquake(enemy, amount * float(attr_mechanics["erdbeben"]))
	if not enemy.is_alive():
		if passive_mech == "schatten":
			_set_stealth(_pp("kill_stealth", 2.0))
		return
	_passive_on_hit(enemy, is_skill, heavy, ranged_hit, charged, source, ctx)
	if enemy.is_alive():
		_apply_effects(enemy, effects, source, ranged_hit)


## Schadensfaktor der aktiven Passiven für einen Treffer.
func _passive_damage_mult(enemy, is_skill: bool, charged: bool, ctx: Dictionary) -> float:
	var m := 1.0
	match passive_mech:
		"berserker":
			m += (1.0 - health / max_health) * 10.0 * _pp("per_10pct")
		"erschuetterung":
			if enemy.is_stunned():
				m += _pp("stunned_bonus")
		"gifte":
			if is_skill:
				m += int(enemy.poison_stacks) * _pp("per_stack")
		"ansturm":
			if charged:
				m += _pp("bonus")
		"phalanx":
			if float(ctx.get("reach_frac", 0.0)) >= _pp("outer", 0.75):
				m += _pp("bonus")
		"fallensteller":
			if float(enemy.get_meta("mark_until", 0.0)) > _now():
				m += _pp("mark")
	return m


## Wirkung der aktiven Passiven nach einem Treffer (vor den Effekten der Fähigkeit).
func _passive_on_hit(enemy, is_skill: bool, heavy: bool, ranged_hit: bool, charged: bool, source: String,
		ctx: Dictionary) -> void:
	match passive_mech:
		"blutrausch":
			if is_skill: # Blutung verbrauchen: Rest trifft sofort, die Hälfte heilt
				var rest: float = enemy.consume_bleed()
				if rest > 0.0:
					enemy.take_damage(rest, global_position, 0.0, 0.0, false, source)
					damage_dealt_total += rest
					var healed := heal(rest * _pp("heal"))
					FX.popup(get_tree(), global_position + Vector3(0, 2.1, 0), "+%d" % roundi(healed), Color(0.4, 1.0, 0.4), 56)
			elif not ranged_hit:
				enemy.apply_bleed(_bleed_dps(), 4.0, source)
		"zertruemmerer":
			enemy.add_sunder(1)
		"belagerer":
			if ranged_hit:
				enemy.add_sunder(1)
		"erschuetterung":
			if heavy or is_skill:
				enemy.add_stun_meter(_pp("fill"), _pp("stun", 2.0))
		"rhythmus":
			if not ranged_hit:
				rhythm_stacks = mini(rhythm_stacks + 1, roundi(_pp("max") / maxf(_pp("per_hit"), 0.01)))
				rhythm_timer = _pp("window", 1.5)
		"gifte":
			enemy.add_poison(1, _poison_dps(enemy, ranged_hit), source)
		"pirschjaeger":
			if ranged_hit:
				enemy.add_poison(1, _poison_dps(enemy, ranged_hit), source)
		"ansturm":
			if charged:
				enemy.apply_stun(_pp("stun", 1.0))
		"fallensteller":
			enemy.set_meta("mark_until", _now() + _pp("mark_time", 5.0))
			if ctx.get("trap", false):
				enemy.apply_debuff("slow", 0.5, 3.0)
	if bonus("poison_extra") > 0.0 and enemy.is_alive():
		enemy.add_poison(int(bonus("poison_extra")), _poison_dps(enemy, ranged_hit), source)


func _apply_effects(enemy, effects: Dictionary, source: String, ranged_hit: bool) -> void:
	if effects.has("bleed"):
		enemy.apply_bleed(_bleed_dps(), float(effects["bleed"]), source)
	elif randf() < _stat("weapon", "bleed") + bonus("bleed"):
		enemy.apply_bleed(_bleed_dps(), 4.0, source)
	for kind in ["slow", "expose"]:
		if effects.has(kind):
			var e: Array = effects[kind]
			enemy.apply_debuff(kind, float(e[0]), float(e[1]))
	if effects.has("sunder"):
		enemy.add_sunder(int(effects["sunder"]))
	if effects.has("poison"):
		enemy.add_poison(int(effects["poison"]), _poison_dps(enemy, ranged_hit), source)
	if effects.has("taunt"):
		enemy.apply_taunt(_taunt_time(float(effects["taunt"])))
	if effects.has("stun"):
		enemy.apply_stun(float(effects["stun"]))
	if effects.has("burn"):
		enemy.apply_burn(_burn_dps(), _elemental_time(float(effects["burn"])), source)
	if effects.has("frost"):
		enemy.add_frost(int(effects["frost"]), _elemental_time(FROST_TIME))
	if effects.has("conductor"):
		enemy.set_meta("conductor_until", _now() + float(effects["conductor"]))
		FX.popup(get_tree(), enemy.global_position + Vector3(0, 2.6, 0), "Leiter", Color(0.65, 0.8, 1.0), 40)


func _bleed_dps() -> float:
	return _stat("weapon", "damage", BASE_WEAPON_DAMAGE) * 0.2 * (1.0 + bonus("damage_pct"))


## Giftschaden je Stapel; Pirschjäger: auf Distanz stärker (+1 % je Meter über 10 m).
func _poison_dps(enemy, ranged_hit: bool) -> float:
	var dps := _stat("weapon", "damage", BASE_WEAPON_DAMAGE) * POISON_DPS_FACTOR * (1.0 + bonus("damage_pct"))
	if passive_mech == "pirschjaeger" and ranged_hit:
		var dist: float = enemy.global_position.distance_to(global_position)
		dps *= 1.0 + clampf((dist - _pp("from_m", 10.0)) * _pp("per_meter"), 0.0, _pp("max"))
	return dps


## Spott hält mit Vitalität 400 (Einschüchternd) 25 % länger.
func _taunt_time(duration: float) -> float:
	return duration * (1.25 if has_mechanic("einschuechternd") else 1.0)


## Erdbeben (Stärke 500): Schockwelle um das getroffene Ziel, trifft alle Gegner in 3 m.
func _earthquake(center_enemy, amount: float) -> void:
	var center: Vector3 = center_enemy.global_position
	FX.shockwave(get_tree(), center, 3.0, Color(0.75, 0.6, 0.4, 0.6))
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy.is_alive() and enemy.global_position.distance_to(center) <= 3.0:
			enemy.take_damage(amount, center, 3.0, 0.4, false, weapon_type)
			damage_dealt_total += amount


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
	if bonus("dodge_free") > 0.0:
		cost = 0.0
	_use_stamina(cost, 0.6)
	if passive_mech == "plaenkler":
		dodge_shot_ready = true
	dodge_speed_mult = _pp("distance", 1.0) if passive_mech == "funkenlaeufer" else 1.0
	_dodge_start = global_position
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
	var speed := DODGE_SPEED * (0.35 + 0.65 * t) * dodge_speed_mult
	velocity.x = dodge_dir.x * speed
	velocity.z = dodge_dir.z * speed
	if state_timer <= 0.0:
		state = State.NORMAL
		if passive_mech == "funkenlaeufer": # Blitzsprung hinterlässt eine Schadenslinie
			_spark_line(_dodge_start, global_position)


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


## `attacker`: der angreifende Gegner (für Paraden), darf fehlen.
func take_damage(amount: float, from_pos: Vector3, unblockable := false, attacker = null) -> void:
	if state == State.DEAD or debug_fly:
		return
	if state == State.GATHER or state == State.FISH:
		_end_gather()
	combat_timer = 6.0
	var head := global_position + Vector3(0, 2.1, 0)
	if iframes > 0.0:
		FX.popup(get_tree(), head, "Ausgewichen", Color(0.7, 0.9, 1.0), 44)
		if passive_mech == "riposte" and not crit_ready: # perfektes Ausweichen
			crit_ready = true
			FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Riposte!", Color(1.0, 0.85, 0.4), 52)
		return
	var to_attacker := from_pos - global_position
	to_attacker.y = 0.0
	var away := -to_attacker.normalized()
	var in_front := to_attacker.length() < 0.01 or _forward().angle_to(to_attacker.normalized()) < deg_to_rad(75.0)

	# Parade: Fähigkeit "Parade" oder (Riposte) ein Block, der gerade erst begonnen hat
	var early_block := blocking and passive_mech == "riposte" and _now() - block_start <= _pp("early_block", 0.3)
	if in_front and not unblockable and (bonus("parry") > 0.0 or early_block):
		for i in range(buffs.size() - 1, -1, -1):
			if buffs[i]["stats"].has("parry"):
				buffs.remove_at(i)
		FX.popup(get_tree(), head, "Pariert", Color(1.0, 0.95, 0.6), 52)
		if attacker != null and is_instance_valid(attacker):
			attacker.apply_stun(1.0)
		if passive_mech == "riposte":
			crit_ready = true
		return

	if blocking and in_front and state == State.NORMAL and unblockable:
		FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Nicht blockbar!", Color(1.0, 0.35, 0.3), 44)
	elif blocking and in_front and state == State.NORMAL:
		# Schild: besserer Schild = weniger Ausdauer. Ohne Schild blockt die Waffe schlechter.
		var factor := BLOCK_STAMINA_FACTOR * 30.0 / (30.0 + block_power) if shield_active() \
			else float(weapon_def.get("block", 1.5))
		factor *= 1.0 - clampf(bonus("block_pct"), 0.0, 0.7)
		if bonus("block_free") > 0.0:
			factor = 0.0
		_use_stamina(amount * factor, 0.8)
		if passive_mech == "trotz" and trotz < int(_pp("max", 5.0)):
			trotz += 1
			if trotz == int(_pp("max", 5.0)):
				FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Trotz voll", Color(1.0, 0.8, 0.3), 48)
		if stamina <= 0.0:
			message.emit("Deckung gebrochen!")
			_stagger(1.1, away * 4.0)
		else:
			FX.popup(get_tree(), head, "Geblockt", Color(0.8, 0.8, 0.8), 44)
			velocity += away * 2.5
		return

	amount *= 1.0 - clampf(bonus("damage_reduction"), 0.0, 0.75)
	amount *= 100.0 / (100.0 + armor) # Rüstung verringert den Schaden
	if has_mechanic("standhaft") and health < max_health * 0.3:
		amount *= 1.0 - float(attr_mechanics["standhaft"])
	if has_mechanic("einschuechternd") and to_attacker.length() <= 4.0:
		amount *= 1.0 - float(attr_mechanics["einschuechternd"])
	if attacker != null and is_instance_valid(attacker):
		if passive_mech == "eispanzer": # je Froststapel des Angreifers weniger Schaden
			amount *= 1.0 - int(attacker.frost_stacks) * _pp("per_stack")
		if bonus("winter_aura") > 0.0 and attacker.global_position.distance_to(global_position) <= 6.0:
			amount *= 0.7
		if bonus("frost_armor") > 0.0:
			attacker.add_frost(1, _elemental_time(FROST_TIME))
	if passive_mech == "herausforderer": # weniger Schaden je verspottetem Gegner
		var taunted := 0
		for e in get_tree().get_nodes_in_group("enemies"):
			var enemy = e
			if enemy.is_taunted() and enemy.global_position.distance_to(global_position) <= 20.0:
				taunted += 1
		amount *= 1.0 - mini(taunted, int(_pp("max", 5.0))) * _pp("per_enemy")
	if shield_hp > 0.0: # Schild aus Überheilung fängt zuerst ab
		var absorbed := minf(shield_hp, amount)
		shield_hp -= absorbed
		amount -= absorbed
	health = maxf(health - amount, 0.0)
	add_ultimate_charge(amount / max_health * ULT_PER_DAMAGE_TAKEN)
	FX.popup(get_tree(), head, str(roundi(amount)), Color(1.0, 0.3, 0.25), 64)
	shake = 0.25
	hurt.emit()
	if health <= 0.0 and bonus("phoenix") > 0.0: # Phönix: mit einem Teil der LP wieder aufstehen
		health = max_health * bonus("phoenix")
		iframes = 1.5
		for i in range(buffs.size() - 1, -1, -1):
			if buffs[i]["stats"].has("phoenix"):
				buffs.remove_at(i)
		FX.shockwave(get_tree(), global_position, 4.0, Color(1.0, 0.55, 0.15, 0.7))
		FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Phönix!", Color(1.0, 0.6, 0.2), 72)
		return
	if health <= 0.0 and has_mechanic("unbeugsam") and unbeugsam_cooldown <= 0.0:
		# Unbeugsam: mit 1 LP und 3 s Unverwundbarkeit überleben
		health = 1.0
		iframes = 3.0
		unbeugsam_cooldown = float(attr_mechanics["unbeugsam"])
		FX.popup(get_tree(), head + Vector3(0, 0.4, 0), "Unbeugsam!", Color(1.0, 0.85, 0.3), 64)
		return
	var unstoppable: bool = has_mechanic("unaufhaltsam") and state == State.ACTION and action.get("heavy", false)
	if health <= 0.0:
		_die()
	elif amount >= 25.0 and bonus("stagger_immune") <= 0.0 and state != State.DODGE and not unstoppable:
		_stagger(0.45, away * 5.0)


func _die() -> void:
	_end_gather()
	state = State.DEAD
	state_timer = RESPAWN_TIME
	blocking = false
	action = {}
	buffs.clear()
	shield_hp = 0.0
	heal_over_time_left = 0.0
	ultimate_charge = 0.0
	trotz = 0
	momentum = 0.0
	crit_ready = false
	_break_stealth()
	heat = 0.0
	charges = 0
	overheat_ready = false
	silence_time = 0.0
	for summon in summons:
		if is_instance_valid(summon):
			summon.queue_free()
	summons.clear()
	_apply_death_penalty()
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
