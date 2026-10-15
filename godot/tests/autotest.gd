extends Node
## Automatischer Test. Start: Godot --headless --path "Spiel RPG" -- --autotest
## Phase 1: Kampf gegen die Wölfe. Phase 2: Häuten, Holzfällen, Bergbau, Angeln. Danach Ausgabe des Zustands.

var player
var time := 0.0
var next_action := 1.0
var step := 0
var phase := "combat"
var log_lines: Array[String] = []


func _ready() -> void:
	player = get_tree().get_first_node_in_group("player")
	# Mit --island: Blick über das Startgebiet der Insel (für Bilder mit --write-movie)
	if Game.world_id.begins_with("insel"):
		phase = "island_view"
		player.cam_yaw = PI # Richtung Dorf (Süden)
		player.cam_pitch = -0.25
		if OS.get_cmdline_user_args().has("--flytest"):
			# Debug-Flug testen: einschalten, 2 s mit 30-facher Geschwindigkeit nach Norden fliegen (simuliert)
			phase = "flytest"
			player.set_debug_fly(true)
			return
		if OS.get_cmdline_user_args().has("--wasser") or OS.get_cmdline_user_args().has("--see"):
			_wasser_ansicht(OS.get_cmdline_user_args().has("--see"))
			return
		if OS.get_cmdline_user_args().has("--natur"):
			_natur_test()
			return
		if OS.get_cmdline_user_args().has("--weg"):
			_weg_ansicht()
			return
		if OS.get_cmdline_user_args().has("--fluss"):
			_fluss_ansicht()
			return
		if OS.get_cmdline_user_args().has("--baeume"):
			# Fichte, Kiefer, Eiche (alt) nebeneinander vor dem Spieler
			var main = get_tree().current_scene
			for a in 3:
				var baum = load("res://assets/baeume/baum.tscn").instantiate()
				baum.set("art", a)
				baum.set("alter", 1)
				var p: Vector3 = player.global_position + Vector3(-7.0 + a * 7.0, 0, -11.0)
				p.y = main.terrain.get("data").get_height(p)
				main.add_child(baum)
				baum.global_position = p
			player.cam_yaw = 0.0
			player.cam_pitch = 0.3
			return
		if OS.get_cmdline_user_args().has("--aerial"):
			# Luftbild: eigene Kamera hoch über dem Startgebiet, Blick nach Norden über die Insel
			var cam := Camera3D.new()
			cam.far = 12000.0
			get_tree().current_scene.add_child(cam)
			cam.global_position = player.global_position + Vector3(0, 450, 900)
			cam.look_at(player.global_position + Vector3(0, 0, -1200))
			cam.current = true
			var terrain = get_tree().current_scene.terrain
			if terrain:
				terrain.set_camera(cam)
			for node in get_tree().current_scene.get_children():
				if node is WorldEnvironment:
					node.environment.fog_enabled = false
			get_tree().current_scene.get_node("HUD").visible = false
		return
	player.global_position = Vector3(20, 0.5, -6)
	player.message.connect(func(t: String) -> void: log_lines.append("Meldung: " + t))
	# Mit --ui nur das Inventarfenster mit Testgegenständen anzeigen
	if OS.get_cmdline_user_args().has("--ui"):
		player.receive_items({"green_wood": 24, "aged_wood": 6, "copper_ore": 12, "iron_ore": 3, "fiber": 30,
			"silverleaf": 2, "raw_hide": 5, "thick_hide": 2, "wolf_fang": 4, "perch": 3, "trout": 1})
		player.add_profession_xp("woodcutting", 260)
		phase = "inventory"
		time = 34.5
		get_tree().current_scene.get_node("HUD").set_inventory_open.call_deferred(true)
	# Mit --village: Blick auf das Handwerksdorf
	if OS.get_cmdline_user_args().has("--village"):
		player.global_position = Vector3(0, 0.5, 8)
		player.cam_yaw = PI
		player.cam_pitch = -0.35
		phase = "idle"
	# Mit --pause: Pausenmenü anzeigen (zusammen mit --quit-after verwenden)
	if OS.get_cmdline_user_args().has("--pause"):
		get_tree().current_scene.get_node("HUD").set_paused.call_deferred(true)
	# Mit --savetest: Speichern und Laden in eine separate Testdatei prüfen
	if OS.get_cmdline_user_args().has("--savetest"):
		_save_test()
		get_tree().quit()
		return
	# Mit --craft: Herstellungskette testen und Werkstattfenster anzeigen
	if OS.get_cmdline_user_args().has("--craft"):
		_craft_test()
		phase = "craft_ui"
	# Mit --showcase: Bilder für Zielen mit dem Bogen, Wirbelwind und Skillbaum (mit --write-movie)
	if OS.get_cmdline_user_args().has("--showcase"):
		phase = "showcase"
		player.equipment["weapon"] = Game.roll_gear("training_bow", [])
		player.equipment["weapon2"] = Game.roll_gear("training_greatsword", [])
		player._recalc_stats()
		player.global_position = Vector3(-24, 0.5, -18)
		player.cam_yaw = 0.0
		player.cam_pitch = -0.1
	# Mit --character: Charakterlevel, Attribute, Waffen-EP, Berufe 0–300, Aufspüren, Tag/Nacht (M5)
	if OS.get_cmdline_user_args().has("--character"):
		_character_test()
		phase = "character_ui"
		get_tree().current_scene.get_node("HUD").set_character_open.call_deferred(true)
	# Mit --m6: Waffen mit 2 Seiten, Passive, Ultimative, Effekte, Tasten, alte Spielstände (M6)
	if OS.get_cmdline_user_args().has("--m6"):
		_m6_test()
		phase = "character_ui" # beendet nach 1,5 s; mit --write-movie entsteht ein Bild vom Skillbaum
		get_tree().current_scene.get_node("HUD").set_skill_tree_open.call_deferred(true)
	# Mit --m7: Magie (Hitze, Ladung, Frost, Brennen, Beschwörungen, Heilung, Arkanes Sanktum)
	if OS.get_cmdline_user_args().has("--m7"):
		_m7_test()
		phase = "character_ui" # beendet nach 1,5 s; mit --write-movie entsteht ein Bild (Skillbaum oder mit --hud die Leiste)
		if not OS.get_cmdline_user_args().has("--hud"):
			get_tree().current_scene.get_node("HUD").set_skill_tree_open.call_deferred(true)
	# Mit --weapons: alle Waffentypen mit Angriffen und allen Fähigkeiten durchprobieren
	if OS.get_cmdline_user_args().has("--weapons"):
		weapon_types = Game.weapons.keys()
		phase = "weapons"
		_next_weapon()


# --- Waffentest ---------------------------------------------------------

var weapon_types: Array = []
var weapon_index := -1
var weapon_steps: Array = []
var weapon_damage_start := 0.0
var weapon_results: Array[String] = []


var side_damage_start := 0.0
var side_passive := ""


func _side_result() -> void:
	if side_passive != "":
		weapon_results.append("    Seite mit %-15s %d Schaden" % [side_passive + ":", roundi(player.damage_dealt_total - side_damage_start)])
	side_passive = ""


func _next_weapon() -> void:
	if weapon_index >= 0:
		_side_result()
		var type: String = weapon_types[weapon_index]
		weapon_results.append("%-12s Schaden gesamt: %d" % [type, roundi(player.damage_dealt_total - weapon_damage_start)])
	weapon_index += 1
	if weapon_index >= weapon_types.size():
		for line in weapon_results:
			print("AUTOTEST ", line)
		for line in log_lines:
			if line.begins_with("FEHLER"):
				print("AUTOTEST ", line)
		get_tree().quit()
		return
	var type: String = weapon_types[weapon_index]
	player.equipment["weapon"] = Game.roll_gear("training_" + type, [])
	player._recalc_stats()
	var m: Dictionary = player._mastery(type)
	m["level"] = Game.MAX_MASTERY_LEVEL
	for node in Game.tree_nodes(type):
		if not m["unlocked"].has(node["id"]):
			m["unlocked"].append(node["id"])
	player._recalc_stats()
	weapon_damage_start = player.damage_dealt_total
	weapon_steps = []
	if player.is_ranged():
		weapon_steps.append_array(["fire", "fire", "fire"])
	else:
		weapon_steps.append_array(["light", "light", "light", "heavy"])
	# Beide Seiten: Passive aktivieren, normale Angriffe, 4 Fähigkeiten und die Ultimative
	for side in Game.weapon_sides(type):
		weapon_steps.append("passive:" + String(side["passive"]["id"]))
		if player.is_ranged():
			weapon_steps.append_array(["fire", "fire"])
		else:
			weapon_steps.append_array(["light", "light", "heavy"])
		for node in side["skills"]:
			weapon_steps.append("skill:" + String(node["id"]))
		weapon_steps.append("ult:" + String(side["ultimate"]["id"]))
	weapon_steps.append("end")


func _weapon_step() -> void:
	# Spieler unverwundbar halten und vor den nächsten Gegner stellen
	player.health = player.max_health
	player.stamina = player.max_stamina
	if player.state != player.State.NORMAL:
		return
	var enemy = _find(func(n): return n.has_method("take_damage") and n.is_alive())
	if enemy == null:
		return
	var away: Vector3 = player.global_position - enemy.global_position
	away.y = 0.0
	if away.length() < 0.1:
		away = Vector3.BACK
	var distance := 7.0 if player.is_ranged() else 1.6
	player.global_position = enemy.global_position + away.normalized() * distance + Vector3(0, 0.3, 0)
	var to: Vector3 = enemy.global_position - player.global_position
	player.cam_yaw = atan2(-to.x, -to.z)
	player.cam_pitch = -0.12
	player.model.rotation.y = player.cam_yaw
	var step_name: String = weapon_steps.pop_front()
	if step_name == "end":
		_next_weapon()
		return
	if step_name == "light":
		player._start_light()
	elif step_name == "heavy":
		player._start_heavy()
	elif step_name == "fire":
		if player.weapon_def["ranged"]["kind"] == "bow":
			player._fire_ranged(1.0)
		else:
			player.ranged_loaded = true
			player._fire_ranged(1.0)
	elif step_name.begins_with("passive:"):
		_side_result()
		player.toggle_skill(player.weapon_type, step_name.substr(8))
		if player.passive_mech == "":
			log_lines.append("FEHLER: Passive %s ohne Mechanik" % step_name.substr(8))
		side_damage_start = player.damage_dealt_total
		side_passive = player.passive_mech
	elif step_name.begins_with("ult:"):
		var ult_id := step_name.substr(4)
		_magie_zuruecksetzen()
		player.toggle_skill(player.weapon_type, ult_id)
		player.ultimate_charge = Game.ULTIMATE_CHARGE
		player._try_ultimate()
		if player.state != player.State.ACTION or player.ultimate_charge > 0.0:
			log_lines.append("FEHLER: Ultimative %s startet nicht" % ult_id)
	elif step_name.begins_with("skill:"):
		var node_id := step_name.substr(6)
		player._mastery(player.weapon_type)["equipped"] = [node_id]
		player.skill_cooldowns.erase(node_id)
		_magie_zuruecksetzen()
		player._try_skill(0)
		if player.state != player.State.ACTION:
			log_lines.append("FEHLER: %s startet keine Aktion" % node_id)


func _save_test() -> void:
	const SaveGame := preload("res://scripts/save_game.gd")
	const PATH := "user://test_save.json"
	_craft_test()
	player.global_position = Vector3(12, 0.5, -3)
	player.add_char_xp(1000)
	player.add_attribute_points("strength", 3)
	player.health = 123.0
	var before: Dictionary = player.to_save()
	var ok := SaveGame.save(get_tree(), PATH)
	# Zustand verändern, dann laden und vergleichen
	player.inventory.items.clear()
	player.inventory.gear.clear()
	player.equipment.clear()
	player.professions["smelting"] = {"level": 1, "xp": 0}
	player.char_level = 1
	player.char_xp = 0
	player.reset_attributes()
	player.global_position = Vector3.ZERO
	var loaded := SaveGame.load_into(get_tree(), PATH)
	var after: Dictionary = player.to_save()
	print("AUTOTEST Speichern=%s Laden=%s" % [ok, loaded])
	for key in ["items", "professions", "health", "char_level", "char_xp", "attributes", "masteries", "ultimate_charge"]:
		print("AUTOTEST %s gleich: %s" % [key, JSON.stringify(before[key]) == JSON.stringify(after[key])])
	var p0: Array = before["position"]
	var p1: Array = after["position"]
	print("AUTOTEST position gleich: %s" % (Vector3(p0[0], p0[1], p0[2]).distance_to(Vector3(p1[0], p1[1], p1[2])) < 0.2))
	print("AUTOTEST Ausrüstung vorher %d / nachher %d, Schadensfaktor %.2f" % [
		before["equipment"].size(), after["equipment"].size(), player.damage_mult])
	print("AUTOTEST angelegte Waffe: ", Game.item_name(player.equipment.get("weapon", {"id": "?"})["id"]))
	SaveGame.delete(PATH)
	print("AUTOTEST Testdatei gelöscht: ", not SaveGame.has_save(PATH))


# --- Charaktertest (M5) ---------------------------------------------------

var check_failed := 0


func _check(name: String, ok: bool, detail := "") -> void:
	if not ok:
		check_failed += 1
	print("AUTOTEST %s %s%s" % ["OK    " if ok else "FEHLER", name, ("   (" + detail + ")") if detail != "" else ""])


func _near(a: float, b: float, eps := 0.001) -> bool:
	return absf(a - b) <= eps


func _character_test() -> void:
	# Punkte pro Level: 48 / 123 / 223 / 348
	var totals := [Game.attribute_points_total(25), Game.attribute_points_total(50), Game.attribute_points_total(75),
		Game.attribute_points_total(100)]
	_check("Attributspunkte bis Level 25/50/75/100", totals == [48, 123, 223, 348], str(totals))

	# Level-Aufstieg
	player.add_char_xp(Game.char_xp_to_next(1) + Game.char_xp_to_next(2) + 10)
	_check("Level 3 nach genug EP", player.char_level == 3 and player.char_xp == 10, "Level %d, %d EP" % [player.char_level, player.char_xp])
	_check("4 freie Attributspunkte auf Level 3", player.attribute_points_free() == 4, str(player.attribute_points_free()))

	# Tod: −20 % der EP im Level, kein Levelverlust
	player.char_xp = 100
	player._die()
	_check("Tod kostet 20 % EP im Level", player.char_xp == 80 and player.char_level == 3, "%d EP, Level %d" % [player.char_xp, player.char_level])
	player._respawn()
	player.char_xp = 0
	player.char_level = 1

	# Waffen-EP nach Schadensanteil: 35 Schaden Schwert + 35 Kriegsaxt an einem Wolf (70 LP, 30 EP)
	var wolf = _find(func(n): return n.get("type_id") == "wolf" and n.is_alive())
	var sword_before := float(player._mastery("sword_shield")["xp"])
	var axe_before := float(player._mastery("axe")["xp"])
	wolf.take_damage(35.0, wolf.global_position, 0.0, 0.0, false, "sword_shield")
	wolf.take_damage(35.0, wolf.global_position, 0.0, 0.0, false, "axe")
	var sword_gain := float(player._mastery("sword_shield")["xp"]) - sword_before
	var axe_gain := float(player._mastery("axe")["xp"]) - axe_before
	_check("Wolf tot, Charakter +30 EP", not wolf.is_alive() and player.char_xp == 30, "%d EP" % player.char_xp)
	_check("Waffen-EP je zur Hälfte (15/15)", _near(sword_gain, 15.0) and _near(axe_gain, 15.0), "%.1f / %.1f" % [sword_gain, axe_gain])

	# Attribute: Level 100 = 348 Punkte
	player.char_level = 100
	player._recalc_stats()
	_check("348 freie Punkte auf Level 100", player.attribute_points_free() == 348)
	player.add_attribute_points("strength", 20)
	_check("Stärke 25: schwere Angriffe +5 %", _near(player.bonus("heavy"), 0.05), str(player.bonus("heavy")))
	player.add_attribute_points("vitality", 195)
	_check("Vitalität 200: Leben 150 + 2000", _near(player.max_health, 2150.0), str(player.max_health))
	_check("Vitalität 200: Standhaft, noch nicht Zäh", player.has_mechanic("standhaft") and not player.has_mechanic("zaeh"))
	player.add_attribute_points("strength", 125)
	var expected_damage := 200 * 0.002 + 150 * 0.002 * 0.5 + float(player.passive.get("damage_pct", 0.0))
	_check("Schadensbonus Schwert und Schild (VIT voll, STÄ halb)", _near(player.bonus("damage_pct"), expected_damage),
		"%.3f statt %.3f" % [player.bonus("damage_pct"), expected_damage])
	_check("Stärke 150: Erz wiegt 10 % weniger", _near(player.inventory.item_weight("stone"), 0.36), str(player.inventory.item_weight("stone")))
	_check("Bergbau schneller (150 × 0,1 % + 10 %)", _near(player.bonus("gather_speed:mining"), 0.25), str(player.bonus("gather_speed:mining")))
	_check("Punkte verbraucht (8 übrig)", player.attribute_points_free() == 8, str(player.attribute_points_free()))
	_check("Mehr Punkte als frei geht nicht", player.add_attribute_points("dexterity", 50) == "" and player.attribute_points_free() == 0)
	player.reset_attributes()
	_check("Zurücksetzen gibt alle Punkte frei", player.attribute_points_free() == 348 and _near(player.max_health, 200.0))
	player.add_attribute_points("intelligence", 24 - player.attribute_value("intelligence"))
	var below: float = player.bonus("magic_damage_pct")
	player.add_attribute_points("intelligence", 1)
	_check("Intelligenz 25: Magieschaden-Schwelle wirkt (M7)", below < player.bonus("magic_damage_pct"),
		"%.3f → %.3f" % [below, player.bonus("magic_damage_pct")])
	player.reset_attributes()

	# Schwelle 500 (nur mit Ausrüstung erreichbar, hier direkt gesetzt): Unbeugsam
	player.attribute_points["vitality"] = 495
	player._recalc_stats()
	player.health = 50.0
	player.iframes = 0.0
	player.take_damage(100000.0, player.global_position + Vector3(0, 0, -2))
	_check("Vitalität 500: Unbeugsam überlebt tödlichen Treffer", player.health == 1.0 and player.is_alive())
	player.attribute_points["vitality"] = 0
	player._recalc_stats()
	player.iframes = 0.0
	player.health = player.max_health

	# Überfluss: Überheilung wird zum Schild
	player.attribute_points["spirit"] = 195
	player._recalc_stats()
	player.health = player.max_health - 10.0
	player.heal(100.0)
	_check("Spiritual 200: Überheilung wird Schild", player.shield_hp > 0.0 and player.shield_hp <= player.max_health * 0.1 + 0.01,
		"Schild %.1f" % player.shield_hp)
	player.attribute_points["spirit"] = 0
	player.shield_hp = 0.0
	player._recalc_stats()

	# Berufe: Skill 0–300, Tiers und Aufspüren
	var tiers: Array = []
	for level in [0, 25, 50, 75, 249, 250, 300]:
		player.professions["mining"]["level"] = level
		tiers.append("%d:%d/%d" % [level, player.profession_tier("mining"), player.track_tier("mining")])
	_check("Tier/Aufspüren je Skill", tiers == ["0:1/0", "25:1/1", "50:2/1", "75:2/2", "249:5/5", "250:6/5", "300:6/6"], str(tiers))
	var xp_sum := 0
	for level in Game.MAX_PROFESSION_LEVEL:
		xp_sum += Game.xp_to_next(level)
	print("AUTOTEST Berufs-EP von 0 bis 300 insgesamt: %d (bis Tier 2: %d)" % [xp_sum, _xp_until(50)])
	var iron = _nearest_resource("iron_vein")
	if iron == null:
		iron = _find(func(n): return n.get("data") is Dictionary and int(n.get("data").get("tier", 1)) == 2)
	_check("Tier-2-Vorkommen braucht Skill 50", iron != null and iron.get_required_level() == 50,
		str(iron.get_required_level()) if iron else "kein Tier-2-Vorkommen")
	var stone = _nearest_resource("stone")
	player.global_position = stone.global_position + Vector3(3, 0.5, 0)
	const Kompass := preload("res://scripts/kompass.gd")
	player.professions["mining"]["level"] = 0
	var none := Kompass.scan(player).filter(func(t): return t["profession"] == "mining").size()
	player.professions["mining"]["level"] = 25
	var some := Kompass.scan(player).filter(func(t): return t["profession"] == "mining").size()
	_check("Aufspüren erst ab Skill 25", none == 0 and some > 0, "%d bei 0, %d bei 25" % [none, some])
	player.professions["mining"]["level"] = 0

	# Bonus-Ausbeute beim Verarbeiten: 20 % bei Skill 300
	player.inventory.capacity = 1000.0
	player.professions["smelting"]["level"] = 300
	player.receive_items({"copper_ore": 400})
	var before: int = player.inventory.count("copper_ingot")
	var result: String = player.craft("copper_ingot", 100)
	var made: int = player.inventory.count("copper_ingot") - before
	_check("Schmelzen 300: Bonus-Ausbeute ~20 %", result == "" and made > 105 and made < 140, "%d Barren aus 100" % made)
	player.professions["smelting"]["level"] = 0

	# Spielstand von Version 1: Berufsstufe 3 wird Skill 50
	var old_save: Dictionary = player.to_save()
	old_save["_version"] = 1
	old_save["professions"] = {"mining": {"level": 3, "xp": 20}}
	player.from_save(old_save)
	_check("Alter Spielstand: Stufe 3 → Skill 50", player.get_profession_level("mining") == 50)
	player.professions["mining"] = {"level": 0, "xp": 0}

	# Tag/Nacht
	var main = get_tree().current_scene
	main.tageszeit.paused = true
	Game.time_of_day = 12.0
	main.tageszeit.apply()
	var sun: DirectionalLight3D = main.tageszeit.sun
	var noon_energy := sun.light_energy
	var noon_down := (-sun.global_basis.z).y
	Game.time_of_day = 0.5
	main.tageszeit.apply()
	_check("Mittags helle Sonne von oben", noon_energy > 1.1 and noon_down < -0.6, "Energie %.2f, Richtung y %.2f" % [noon_energy, noon_down])
	_check("Nachts schwaches Mondlicht", sun.light_energy < 0.3 and main.tageszeit.is_night(), "Energie %.2f" % sun.light_energy)
	Game.time_of_day = 10.0
	main.tageszeit.apply()
	main.tageszeit.paused = false

	# Fürs Bild: Level 12 mit verteilten Punkten
	player.char_level = 12
	player.char_xp = Game.char_xp_to_next(12) / 3
	player.add_attribute_points("strength", 14)
	player.add_attribute_points("vitality", 6)
	player.health = player.max_health
	print("AUTOTEST Charaktertest: %d Fehler" % check_failed)


func _m6_test() -> void:
	# Daten: 10 Waffen, je 2 Seiten mit Passive (Mechanik), 4 Fähigkeiten und Ultimative
	var bad: Array[String] = []
	for type in Game.weapons:
		var sides := Game.weapon_sides(type)
		if sides.size() != 2:
			bad.append(type)
		for side in sides:
			if side["skills"].size() != 4 or String(side["passive"].get("mechanic", "")) == "" or not side.has("ultimate"):
				bad.append(type + "/" + String(side["id"]))
	_check("15 Waffen mit je 2 vollständigen Seiten", Game.weapons.size() == 15 and bad.is_empty(), str(bad))

	# Tasten
	var keys := {}
	for action in ["skill_1", "skill_2", "skill_3", "ultimate", "interact", "swap_weapon", "quick_1", "quick_4"]:
		var ev: InputEventKey = InputMap.action_get_events(action)[0]
		keys[action] = OS.get_keycode_string(ev.physical_keycode)
	_check("Tasten Q/E/R, X, F, T, 1–4", keys == {"skill_1": "Q", "skill_2": "E", "skill_3": "R", "ultimate": "X",
		"interact": "F", "swap_weapon": "T", "quick_1": "1", "quick_4": "4"}, str(keys))

	# Meisterschaft: Stufe n = n + 1 Punkte, Startfähigkeit kostenlos auf Q
	player.equipment["weapon"] = Game.roll_gear("training_axe", [])
	player._recalc_stats()
	player.masteries.erase("axe")
	var m: Dictionary = player._mastery("axe")
	_check("Stufe 1: 1 Punkt frei, Startfähigkeit auf Q", player.mastery_points_free("axe") == 1 and m["equipped"] == ["ax_split"],
		"%d Punkte, %s" % [player.mastery_points_free("axe"), str(m["equipped"])])
	m["level"] = Game.MAX_MASTERY_LEVEL
	var ult_error: String = player.unlock_node("axe", "ax_feast")
	player.unlock_node("axe", "ax_blutrausch")
	player.unlock_node("axe", "ax_rend")
	var ult_ok: String = player.unlock_node("axe", "ax_feast")
	_check("Ultimative erst nach Passive + 2 Fähigkeiten", ult_error != "" and ult_ok == "" and m["ultimate"] == "ax_feast",
		"%s / %s" % [ult_error, ult_ok])
	player.unlock_node("axe", "ax_throw")
	player.unlock_node("axe", "ax_frenzy")
	_check("Stufe 20: ganze Seite kostet 11, 9 bleiben", player.mastery_points_free("axe") == 9, str(player.mastery_points_free("axe")))
	_check("Höchstens 3 Fähigkeiten auf Q/E/R", m["equipped"].size() == 3, str(m["equipped"]))
	player.unlock_node("axe", "ax_berserker")
	var first_mech: String = player.passive_mech
	player.toggle_skill("axe", "ax_berserker")
	_check("Nur eine Passive aktiv, umschaltbar", first_mech == "blutrausch" and player.passive_mech == "berserker",
		"%s → %s" % [first_mech, player.passive_mech])

	# Berserker: Fähigkeit kostet 6 % LP, halbe Abklingzeit
	player.health = player.max_health
	player.skill_cooldowns.clear()
	player._try_skill(0)
	var cost: float = player.max_health - player.health
	_check("Berserker: Fähigkeit kostet 6 % LP, halbe Abklingzeit", _near(cost, player.max_health * 0.06, 0.5)
		and _near(float(player.skill_cooldowns["ax_split"]), 5.0, 0.01), "%.1f LP, %.1f s" % [cost, player.skill_cooldowns["ax_split"]])
	player._end_action(false)

	# Ultimative: lädt durch Treffer, X löst bei voller Leiste aus
	var wolf = _find(func(n): return n.get("type_id") == "wolf" and n.is_alive())
	player.ultimate_charge = 0.0
	wolf.health = 10000.0
	wolf.max_health = 10000.0
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position)
	var charged: float = player.ultimate_charge
	player._try_ultimate()
	var blocked: bool = player.state == player.State.NORMAL
	player.ultimate_charge = Game.ULTIMATE_CHARGE
	player._try_ultimate()
	_check("Ultimative lädt durch Treffer und startet nur voll", charged > 0.0 and blocked and player.state == player.State.ACTION
		and player.ultimate_charge == 0.0, "Ladung %.1f" % charged)
	player._end_action(false)

	# Effekte: Betäubung, Spott, Rüstungsbruch, Gift
	player._apply_effects(wolf, {"stun": 1.0, "taunt": 4.0, "sunder": 3, "poison": 2}, "axe", false)
	_check("Betäubung, Spott, Rüstungsbruch 3, Gift 2", wolf.is_stunned() and wolf.is_taunted() and wolf.sunder_stacks == 3
		and wolf.poison_stacks == 2, "%s %s %d %d" % [wolf.is_stunned(), wolf.is_taunted(), wolf.sunder_stacks, wolf.poison_stacks])
	player.buffs.clear()
	player.health = player.max_health
	seed(7)
	var hp: float = wolf.health
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position)
	var hit_sundered: float = hp - wolf.health
	wolf.sunder_stacks = 0
	player.health = player.max_health
	seed(7)
	hp = wolf.health
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position)
	var hit_plain: float = hp - wolf.health
	_check("Rüstungsbruch: +3 % Schaden je Stapel", _near(hit_sundered / hit_plain, 1.09, 0.005), "%.3f" % (hit_sundered / hit_plain))

	# Kopftreffer ×1,5 (Muskete)
	player.equipment["weapon"] = Game.roll_gear("training_musket", [])
	player._recalc_stats()
	seed(3)
	hp = wolf.health
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position, "musket", {"headshot": true})
	var head_hit: float = hp - wolf.health
	seed(3)
	hp = wolf.health
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position, "musket", {})
	var body_hit: float = hp - wolf.health
	_check("Kopftreffer ×1,5", _near(head_hit / body_hit, 1.5, 0.005), "%.3f" % (head_hit / body_hit))

	# Tarnung: Treffer beendet sie; Schatten: Angriff aus der Tarnung ist kritisch
	player._set_stealth(3.0)
	var hidden: bool = player.is_stealthed()
	player._deal_damage(wolf, 1.0, 0.0, 0.0, {}, false, player.global_position)
	_check("Tarnung bis zum ersten Treffer", hidden and not player.is_stealthed())

	# Repetierer: Magazin mit 4 Bolzen, schnelles Nachladen
	player.equipment["weapon"] = Game.roll_gear("training_crossbow", [])
	player._recalc_stats()
	player._mastery("crossbow")["level"] = Game.MAX_MASTERY_LEVEL
	player.unlock_node("crossbow", "cb_repetierer")
	player.toggle_skill("crossbow", "cb_repetierer")
	var full: int = player.magazine
	player.state = player.State.NORMAL
	player._fire_ranged(1.0)
	player._end_action(false)
	player._start_reload()
	var quick: float = player.action["duration"]
	player._end_action(false)
	_check("Repetierer: 4 Bolzen, 0,3 s Nachladen", full == 4 and player.magazine == 3 and _near(quick, 0.3, 0.01),
		"%d → %d, %.2f s" % [full, player.magazine, quick])

	# Riposte: Treffer während des Ausweichens macht den nächsten Angriff kritisch
	player.equipment["weapon"] = Game.roll_gear("training_rapier", [])
	player._recalc_stats()
	player._mastery("rapier")["level"] = Game.MAX_MASTERY_LEVEL
	player.unlock_node("rapier", "ra_riposte_p")
	player.iframes = 0.3
	player.take_damage(20.0, wolf.global_position)
	_check("Riposte nach perfektem Ausweichen", player.crit_ready)
	player.iframes = 0.0
	player.crit_ready = false

	# Trotz (Schwert und Schild): 5 geblockte Treffer, dann betäubt die nächste Fähigkeit
	player.equipment["weapon"] = Game.roll_gear("training_sword_shield", [])
	player._recalc_stats()
	player._mastery("sword_shield")["level"] = Game.MAX_MASTERY_LEVEL
	player.unlock_node("sword_shield", "ss_trotz")
	player.blocking = true
	player.state = player.State.NORMAL
	var front: Vector3 = player.global_position + player._forward() * 2.0
	for i in 5:
		player.stamina = player.max_stamina
		player.take_damage(10.0, front)
	player.blocking = false
	_check("Trotz lädt durch Blocken", player.trotz == 5, str(player.trotz))

	# Drei Waffenplätze reihum wechseln (dritter Platz später per Quest)
	player.weapon_slots = 3
	player.equipment["weapon"] = Game.roll_gear("training_axe", [])
	player.equipment["weapon2"] = Game.roll_gear("training_bow", [])
	player.equipment["weapon3"] = Game.roll_gear("training_spear", [])
	player.swap_weapons()
	var after_next: String = player.weapon_type
	player.swap_weapons(-1)
	player.swap_weapons(-1)
	_check("3 Waffenplätze: vor und zurück", after_next == "bow" and player.weapon_type == "spear",
		"%s, %s" % [after_next, player.weapon_type])
	player.equipment.erase("weapon3")
	player.weapon_slots = 2

	# Schnellplatz 3 ist noch gesperrt
	var messages: Array[String] = []
	var collect := func(t: String) -> void: messages.append(t)
	player.message.connect(collect)
	player.use_quick_slot(2)
	player.message.disconnect(collect)
	_check("Schnellplatz 3 gesperrt", not messages.is_empty() and messages[0].contains("gesperrt"), str(messages))

	# Alter Spielstand (Version 2, Einhand/Zweihand getrennt)
	var old_save: Dictionary = player.to_save()
	old_save["_version"] = 2
	old_save["masteries"] = {"sword_1h": {"level": 5, "xp": 10.0, "unlocked": ["s1_a"], "equipped": ["s1_a"]},
		"sword_2h": {"level": 7, "xp": 0.0, "unlocked": [], "equipped": []},
		"axe_1h": {"level": 3, "xp": 0.0, "unlocked": [], "equipped": []},
		"axe_2h": {"level": 9, "xp": 0.0, "unlocked": [], "equipped": []}}
	old_save["equipment"] = {"weapon": {"id": "copper_hatchet", "uid": 9001, "stats": {"damage": 25}},
		"weapon2": {"id": "training_daggers", "uid": 9002, "stats": {"damage": 18}}}
	old_save["gear"] = []
	player.from_save(old_save)
	var ms: Dictionary = player.masteries
	_check("Alter Spielstand: Waffen und Meisterschaften übernommen",
		player.equipment["weapon"]["id"] == "copper_greataxe" and player.equipment["weapon2"]["id"] == "training_knife"
		and int(ms["sword_shield"]["level"]) == 5 and int(ms["greatsword"]["level"]) == 7 and int(ms["axe"]["level"]) == 9
		and ms["sword_shield"]["unlocked"] == ["ss_bash"],
		"%s %s, Stufen %s/%s/%s" % [player.equipment["weapon"]["id"], player.equipment["weapon2"]["id"],
		ms.get("sword_shield", {}).get("level"), ms.get("greatsword", {}).get("level"), ms.get("axe", {}).get("level")])

	# Fürs Bild: Axt mit Blutrausch-Seite, beide Passiven und eine Ultimative
	player.equipment["weapon"] = Game.roll_gear("training_axe", [])
	player._recalc_stats()
	var am: Dictionary = player._mastery("axe")
	am["level"] = 14
	for id in ["ax_blutrausch", "ax_rend", "ax_throw", "ax_feast", "ax_berserker", "ax_maelstrom"]:
		player.unlock_node("axe", id)
	player.ultimate_charge = 64.0
	player.health = player.max_health
	print("AUTOTEST M6-Test: %d Fehler" % check_failed)


func _xp_until(level: int) -> int:
	var total := 0
	for l in level:
		total += Game.xp_to_next(l)
	return total


func _craft_test() -> void:
	player.inventory.capacity = 500.0
	player.receive_items({"copper_ore": 40, "green_wood": 20, "raw_hide": 9, "fiber": 12, "stone": 12, "flint": 3,
		"healing_herb": 6, "wolf_fang": 2, "perch": 4})
	player.professions["stonecutting"]["level"] = 25 # Schleifstein braucht Steinmetz Skill 25
	var steps := [
		["copper_ingot", 10, []], ["timber", 5, []], ["coarse_leather", 3, []], ["linen", 3, []],
		["stone_block", 3, []], ["whetstone", 1, []], ["copper_sword", 1, ["whetstone"]],
		["copper_axe", 1, []], ["small_potion", 2, []], ["grilled_perch", 1, []], ["iron_sword", 1, []],
	]
	for s in steps:
		var result: String = player.craft(s[0], s[1], s[2])
		log_lines.append("craft %s x%d %s -> %s" % [s[0], s[1], str(s[2]), "OK" if result == "" else result])
	log_lines.append("Ausrüstung im Inventar: %d Stück" % player.inventory.gear.size())
	var power_before: float = player.get_tool_power("woodcutting")
	for g in player.inventory.gear.duplicate():
		log_lines.append("  " + Game.gear_tooltip(g).replace("\n", " | "))
		player.equip(int(g["uid"]))
	log_lines.append("Schadensfaktor=%.2f Blutung=%.2f Krit=%.2f Abbaukraft Holz %.0f -> %.0f" % [
		player.damage_mult, player.bleed_chance, player.crit_chance, power_before, player.get_tool_power("woodcutting")])
	player.health = 100.0
	player.use_consumable("potion")
	player.use_consumable("potion")
	player.use_consumable("food")
	log_lines.append("Leben nach Trank: %.0f, Essen-Regeneration %.0f/s" % [player.health, player.food_regen])
	log_lines.append("Berufe: smelting=%d weaponsmithing=%d" % [player.get_profession_level("smelting"),
		player.get_profession_level("weaponsmithing")])
	time = 34.0
	get_tree().current_scene.get_node("HUD").open_station.call_deferred("weaponsmith")


## Ans Ufer des nächsten größeren Flusses (Breite ab 14 m) stellen und flussabwärts schauen
func _fluss_ansicht() -> void:
	var main = get_tree().current_scene
	var best := Vector3.ZERO
	var richtung := Vector3.FORWARD
	var breite := 0.0
	var best_d := INF
	var liste: Array = JSON.parse_string(FileAccess.get_file_as_string("res://welt_daten/fluesse.json"))
	var anzahl := 0
	var km := 0.0
	for f in liste:
		var p: Array = f["punkte"]
		anzahl += 1
		for i in range(1, p.size()):
			km += Vector2(p[i][0] - p[i - 1][0], p[i][2] - p[i - 1][2]).length() / 1000.0
		for i in range(3, p.size() - 3):
			if float(p[i][3]) < 14.0:
				continue
			var q := Vector3(p[i][0], p[i][1], p[i][2])
			var d := q.distance_to(player.global_position)
			if d < best_d:
				best_d = d
				best = q
				breite = float(p[i][3])
				richtung = (Vector3(p[i + 3][0], 0, p[i + 3][2]) - Vector3(p[i - 3][0], 0, p[i - 3][2])).normalized()
	var quer := Vector3(-richtung.z, 0, richtung.x)
	var ufer := best + quer * (breite / 2.0 + 6.0) - richtung * 10.0
	ufer.y = main.terrain.get("data").get_height(ufer) + 1.0
	player.global_position = ufer
	var blick := best + richtung * 15.0 - ufer
	player.cam_yaw = atan2(-blick.x, -blick.z)
	player.cam_pitch = -0.3
	print("AUTOTEST Fluss: %d Flussläufe, %.0f km, Blick auf %s (Breite %.0f m, Wasser %.1f m, Boden dort %.1f m)" % [
		anzahl, km, best.round(), breite, best.y, main.terrain.get("data").get_height(best)])


## Auf die nächste Straße stellen und an ihr entlang schauen
func _weg_ansicht() -> void:
	var best := Vector3.ZERO
	var richtung := Vector3.FORWARD
	var best_d := INF
	for pf in get_tree().get_nodes_in_group("welt_wege"):
		if pf.get_meta("typ", "") != "strasse":
			continue
		var c: Curve3D = pf.curve
		for i in range(2, c.point_count - 2):
			var q := c.get_point_position(i)
			var d := q.distance_to(player.global_position)
			if d > 60.0 and d < best_d:
				best_d = d
				best = q
				richtung = (c.get_point_position(i + 2) - c.get_point_position(i - 2)).normalized()
	player.global_position = best + Vector3(0, 1.0, 0) - richtung * 4.0
	player.cam_yaw = atan2(-richtung.x, -richtung.z)
	player.cam_pitch = -0.22
	print("AUTOTEST Weg: Blick bei %s" % best.round())


## Blick aufs Wasser: an die Küste beim Fischgrund (Meer) oder ans Ufer des ersten Sees (--see)
func _wasser_ansicht(see: bool) -> void:
	var main = get_tree().current_scene
	var ziel := Vector3.ZERO
	var ufer := Vector3.ZERO
	if see:
		var flaeche = get_tree().get_first_node_in_group("welt_seen")
		# Schwerpunkt der Seefläche (aus welt.json), von dort nach Süden bis ans Ufer
		ziel = Vector3(float(flaeche.get_meta("x")), flaeche.global_position.y, float(flaeche.get_meta("z")))
		ufer = ziel
		while main.terrain.get("data").get_height(ufer) < ziel.y + 0.3 and ufer.z - ziel.z < 800.0:
			ufer.z += 2.0
		ufer.z += 6.0
	else:
		for n in get_tree().get_nodes_in_group("interactable"):
			if n.get("node_id") == "fishing_spot":
				ziel = n.global_position
				break
		var weg := Vector3(player.global_position.x - ziel.x, 0, player.global_position.z - ziel.z).normalized()
		ufer = ziel + weg * 18.0
	ufer.y = main.terrain.get("data").get_height(ufer) + 1.0
	player.global_position = ufer
	var blick := ziel - ufer
	player.cam_yaw = atan2(-blick.x, -blick.z)
	player.cam_pitch = -0.18
	print("AUTOTEST Wasser: Blick von %s auf %s" % [ufer.round(), ziel.round()])


## Natur auf der Insel: Spieler in ein Biom nahe dem Startgebiet setzen (--biom <name>, Standard wald; siehe
## data/biome.json), alles laden, zählen, einen Baum fällen und eine Pflanze ernten. Mit --write-movie entstehen Bilder.
func _natur_test() -> void:
	var natur = get_tree().current_scene.natur
	var args := OS.get_cmdline_user_args()
	var gesucht := "wald"
	if args.has("--biom") and args.find("--biom") + 1 < args.size():
		gesucht = args[args.find("--biom") + 1]
	var start := Vector2(player.global_position.x, player.global_position.z)
	var ort := Vector2.INF
	for r in range(260, 4000, 20):
		for i in 24:
			var p := start + Vector2.from_angle(TAU * i / 24.0) * r
			# ganz im Biom: auch 12 m ringsum (sonst steht man am Rand)
			var drin: bool = natur.biom_name(p.x, p.y) == gesucht and (gesucht == "fluss" or not natur._gesperrt(p.x, p.y))
			for j in 4:
				var q := p + Vector2.from_angle(TAU * j / 4.0) * (3.0 if gesucht == "fluss" else 12.0)
				drin = drin and natur.biom_name(q.x, q.y) == gesucht
			if drin:
				ort = p
				break
		if ort != Vector2.INF:
			break
	if ort == Vector2.INF:
		print("AUTOTEST Natur: kein Ort im Biom %s gefunden" % gesucht)
		ort = start
	var h: float = natur._hoehe(ort.x, ort.y)
	player.global_position = Vector3(ort.x, h + 1.0, ort.y)
	var t0 := Time.get_ticks_msec()
	natur.sofort_laden()
	var t_nah := Time.get_ticks_msec() - t0
	t0 = Time.get_ticks_msec()
	var k := Vector2i(floori(ort.x / 256.0) + 2, floori(ort.y / 256.0))
	natur._fern_bauen(k)
	var t_fern := Time.get_ticks_msec() - t0
	var zahl := {}
	for n in natur._nah.values():
		var id: String = _natur_id(n)
		zahl[id] = int(zahl.get(id, 0)) + 1
	print("AUTOTEST Natur: Biom %s, Ort %s (Höhe %.0f m), %d Objekte im Nahbereich in %d ms, Fernkachel in %d ms" % [
		gesucht, ort.round(), h, natur._nah.size(), t_nah, t_fern])
	print("AUTOTEST Natur Arten: ", zahl)
	# nächsten Baum und nächste Pflanze ernten
	for gruppe in [["fichte", "kiefer", "eiche"], ["hanf", "beeren", "kraut"]]:
		var best = null
		var best_d := INF
		for n in natur._nah.values():
			if n.get("node_id") != null and String(n.node_id).get_slice("_", 0) in gruppe:
				var d: float = n.global_position.distance_to(player.global_position)
				if d < best_d:
					best_d = d
					best = n
		if best:
			best.harvest(player)
			print("AUTOTEST Natur geerntet: %s (%.0f m entfernt), danach abbaubar: %s" % [best.node_id, best_d, best.is_interactable()])
	print("AUTOTEST Natur Inventar: ", player.inventory.items)
	player.cam_yaw = 0.3
	player.cam_pitch = -0.12
	if args.has("--uralt"):
		# vor den nächsten noch stehenden uralten Baum stellen, leicht nach oben schauen
		var baum = null
		for n in natur._nah.values():
			if n.get("node_id") != null and String(n.node_id).ends_with("_uralt") and n.is_interactable() \
					and (baum == null or n.global_position.distance_to(player.global_position) < baum.global_position.distance_to(player.global_position)):
				baum = n
		if baum:
			var p: Vector3 = baum.global_position + Vector3(24, 0, 0)
			player.global_position = Vector3(p.x, natur._hoehe(p.x, p.z) + 1.0, p.z)
			player.cam_yaw = PI / 2.0
			player.cam_pitch = 0.18
	phase = "natur"


func _physics_process(delta: float) -> void:
	time += delta
	match phase:
		"natur":
			# Bildrate im Wald messen (ohne --write-movie aussagekräftig), danach ein Stück durch den Wald laufen
			if time > 5.0 and time - delta <= 5.0:
				print("AUTOTEST Natur FPS stehend: %d, Nah-Objekte %d, Fernkacheln %d" % [Engine.get_frames_per_second(),
					get_tree().current_scene.natur._nah.size(), get_tree().current_scene.natur._fern.size()])
				Input.action_press("move_forward")
				Input.action_press("sprint")
			elif time > 11.0 and time - delta <= 11.0:
				Input.action_release("move_forward")
				Input.action_release("sprint")
				print("AUTOTEST Natur FPS laufend: %d, Nah-Objekte %d" % [Engine.get_frames_per_second(), get_tree().current_scene.natur._nah.size()])
				get_tree().quit()
		"flytest":
			if time < 2.0:
				player.cam_yaw = 0.0 # Maus im Testfenster darf die Richtung nicht verfälschen
				player.cam_pitch = 0.0
			if time < 0.05:
				set_meta("start", player.global_position)
				player.cam_yaw = 0.0 # nach Norden
				player.cam_pitch = 0.0
				Input.action_press("move_forward")
				Input.action_press("sprint")
			elif time > 2.0 and time < 2.05:
				Input.action_release("move_forward")
				Input.action_release("sprint")
				var start: Vector3 = get_meta("start")
				var weg: Vector3 = player.global_position - start
				print("AUTOTEST Flug: %.0f m in 2 s (Ziel: ~720 m), Richtung x %.0f / y %.0f / z %.0f, Leben %d, Kollision aus: %s" % [
					weg.length(), weg.x, weg.y, weg.z, player.health, player.collision_mask == 0])
			elif time > 2.5 and time < 2.55:
				var hud = get_tree().current_scene.get_node("HUD")
				hud.minimap.big_zoom = 4.0 # große Karte mit Zoom um den Spieler
				hud.set_world_map_open(true)
		"showcase":
			player.health = player.max_health
			if time < 2.0:
				player.aiming = true # Zielansicht mit Bogen (Rechtsklick wird im Test simuliert)
				if time > 1.0 and player.state == player.State.NORMAL:
					player._fire_ranged(1.0)
			elif time < 2.1 and player.weapon_type == "bow":
				player.swap_weapons()
				var m: Dictionary = player._mastery("greatsword")
				m["level"] = 6
				player.unlock_node("greatsword", "gs_klingensturm")
				player.unlock_node("greatsword", "gs_whirl")
				player.ultimate_charge = 70.0
			elif time > 2.5 and time < 2.6 and player.state == player.State.NORMAL:
				var enemy = _find(func(n): return n.has_method("take_damage") and n.is_alive())
				player.global_position = enemy.global_position + Vector3(0, 0.3, 2)
				player.cam_yaw = 0.0
				player._mastery("greatsword")["equipped"] = ["gs_whirl", "gs_wide"]
				player._try_skill(0)
			elif time > 3.4 and time < 3.5:
				get_tree().current_scene.get_node("HUD").set_skill_tree_open(true)
		"weapons":
			if time >= next_action:
				next_action = time + 0.25
				_weapon_step()
		"character_ui":
			if time > 1.5:
				get_tree().quit()
		"craft_ui":
			if time > 34.6:
				phase = "inventory"
				get_tree().current_scene.get_node("HUD").set_inventory_open(true)
		"combat":
			_combat()
			if time > 9.0:
				phase = "skin"
				_go_interact(_find(func(n): return n.has_method("take_damage") and n.is_interactable()), "skin")
		"skin":
			if _idle_after(13.0):
				phase = "wood"
				_go_interact(_nearest_resource("pine"), "wood")
		"wood":
			if _idle_after(18.0):
				phase = "mine"
				_go_interact(_nearest_resource("stone"), "mine")
		"mine":
			if _idle_after(23.0):
				phase = "fish"
				_go_interact(_nearest_resource("fishing_spot"), "fish")
		"fish":
			# Beim Biss automatisch E "drücken"
			if player.state == player.State.FISH and player.fish_phase == "bite":
				var target = player.gather_target
				player._end_gather()
				target.harvest(player)
			if time > 34.0:
				phase = "inventory"
				get_tree().current_scene.get_node("HUD").set_inventory_open(true)
		"inventory":
			if time > 35.0:
				_finish()


func _combat() -> void:
	if time >= next_action and player.state == player.State.NORMAL:
		next_action = time + 0.7
		step += 1
		match step % 6:
			1, 2, 3:
				player._start_light()
			4:
				player._start_heavy()
			5:
				player._try_skill(0)
			0:
				player._try_skill(1)
	var nearest = _find(func(n): return n.has_method("take_damage") and n.is_alive())
	if nearest:
		var to: Vector3 = nearest.global_position - player.global_position
		player.cam_yaw = atan2(-to.x, -to.z)


func _idle_after(t: float) -> bool:
	return time > t and player.state == player.State.NORMAL


func _go_interact(target, label: String) -> void:
	if target == null:
		log_lines.append("FEHLER: kein Ziel für " + label)
		return
	var dir: Vector3 = (player.global_position - target.global_position)
	dir.y = 0.0
	player.global_position = target.global_position + dir.normalized() * 1.2 + Vector3(0, 0.5, 0)
	player._start_interaction(target)
	log_lines.append("Start %s: Zustand=%d" % [label, player.state])


func _find(pred: Callable):
	var best = null
	var best_d := INF
	for n in get_tree().get_nodes_in_group("interactable"):
		if pred.call(n):
			var d: float = n.global_position.distance_to(player.global_position)
			if d < best_d:
				best_d = d
				best = n
	return best


func _nearest_resource(id: String):
	return _find(func(n): return n.get("node_id") == id and n.is_interactable())


func _finish() -> void:
	for line in log_lines:
		print("AUTOTEST ", line)
	print("AUTOTEST Spieler HP=%.0f Zustand=%d" % [player.health, player.state])
	print("AUTOTEST Inventar: ", player.inventory.items, "  Gewicht=%.1f" % player.inventory.weight())
	print("AUTOTEST Berufe: ", player.professions)
	print("AUTOTEST Charakter: Level %d, %d EP, Meisterschaft Schwert und Schild %s" % [player.char_level, player.char_xp,
		str(player.masteries.get("sword_shield", {}).get("xp", 0))])
	print("AUTOTEST Beutebeutel in der Welt: ", get_tree().current_scene.get_children().filter(
		func(c): return c.get("items") != null and c.has_method("_process") and c.get("life") != null).size())
	get_tree().quit()


## Hitze/Stille aus vorigen Schritten löschen, damit jede Fähigkeit einzeln geprüft wird.
func _magie_zuruecksetzen() -> void:
	player.heat = 0.0
	player.silence_time = 0.0
	player.overheat_ready = false


# --- M7: Magie ------------------------------------------------------------

## Magiewaffe anlegen und eine Passive aktivieren.
func _magie_waffe(type: String, passive_id: String) -> void:
	player.equipment["weapon"] = Game.roll_gear("training_" + type, [])
	player._recalc_stats()
	player._mastery(type)["level"] = Game.MAX_MASTERY_LEVEL
	player.unlock_node(type, passive_id)
	if player._mastery(type).get("passive", "") != passive_id:
		player.toggle_skill(type, passive_id)
	player.buffs.clear()
	player.heat = 0.0
	player.silence_time = 0.0
	player.overheat_ready = false
	player.health = player.max_health


## Schaden eines Treffers mit festem Zufall.
func _treffer(enemy, ctx := {}) -> float:
	seed(11)
	var hp: float = enemy.health
	player._deal_damage(enemy, 1.0, 0.0, 0.0, {}, false, player.global_position, "", ctx)
	return hp - enemy.health


func _m7_test() -> void:
	# Daten: 5 Magiewaffen, hergestellt im Arkanen Sanktum
	var magic: Array[String] = []
	for type in Game.weapons:
		if Game.weapons[type].get("magic", false):
			magic.append(type)
	var stations: Array = []
	for id in ["ember_staff", "frost_staff", "spark_staff", "life_staff", "void_orb", "blaze_staff", "abyss_orb"]:
		stations.append(Game.recipes.get(id, {}).get("station", "?"))
	_check("5 Magiewaffen aus dem Arkanen Sanktum", magic.size() == 5 and stations.count("arcana") == 7, "%s %s" % [magic, stations])

	var wolf = _find(func(n): return n.get("type_id") == "wolf" and n.is_alive())
	wolf.max_health = 100000.0
	wolf.health = wolf.max_health
	wolf.global_position = player.global_position + Vector3(3, 0, 0)

	# Feuer: Hitze steigt, bei 100 Überhitzung (3 s Stille, 8 % LP)
	_magie_waffe("fire_magic", "fi_inferno")
	player._cast_heat(15.0)
	var heat_after: float = player.heat
	player.heat = 95.0
	player._cast_heat(15.0)
	var lost: float = player.max_health - player.health
	_check("Hitze steigt, Überhitzung: 3 s Stille und 8 % LP", heat_after == 15.0 and player.heat == 0.0
		and player.silence_time == 3.0 and _near(lost, player.max_health * 0.08, 0.5) and not player._can_cast(),
		"Hitze %.0f, Stille %.1f, %.1f LP" % [heat_after, player.silence_time, lost])

	# Hitze gibt Schaden: +1 % je 10 Hitze, mit Glutherz +3 %
	_magie_waffe("fire_magic", "fi_glutherz")
	var cold: float = _treffer(wolf)
	player.heat = 50.0
	var hot: float = _treffer(wolf)
	_check("Glutherz: 50 Hitze = +15 % Schaden", _near(hot / cold, 1.15, 0.005), "%.3f" % (hot / cold))
	player.heat = 95.0
	player._cast_heat(15.0)
	var ready: bool = player.overheat_ready and player.silence_time == 0.0
	var doubled: float = player._cast_heat(15.0)
	_check("Glutherz: bei 100 Hitze nächster Zauber doppelt, dann Stille", ready and doubled == 2.0 and player.silence_time == 3.0)
	player.silence_time = 0.0

	# Brennen und Zündung (Rest des Brands × 150 %)
	player._apply_effects(wolf, {"burn": 4.0}, "fire_magic", false)
	var rest: float = wolf.burn_dps * ceilf(wolf.burn_time)
	var hp: float = wolf.health
	player._detonate_burns(15.0, 1.5)
	_check("Brennen, Zündung löst den Rest mit 150 % aus", rest > 0.0 and not wolf.is_burning()
		and _near(hp - wolf.health, rest * 1.5, 0.5), "Rest %.1f, Schaden %.1f" % [rest, hp - wolf.health])

	# Eis: 5 Froststapel frieren ein, Zerschmettern +30 % und löst das Eis
	_magie_waffe("ice_magic", "ic_frostwaechter")
	player._apply_effects(wolf, {"frost": 3}, "ice_magic", false)
	var slowed: int = wolf.frost_stacks
	player._apply_effects(wolf, {"frost": 2}, "ice_magic", false)
	var frozen: bool = wolf.is_frozen()
	var shatter_hit: float = _treffer(wolf)
	var thawed: bool = not wolf.is_frozen()
	var plain_hit: float = _treffer(wolf)
	_check("Frost: 5 Stapel frieren ein", slowed == 3 and frozen and thawed, "%d Stapel" % slowed)
	_check("Zerschmettern: +30 % auf gefrorene Gegner", _near(shatter_hit / plain_hit, 1.3, 0.005), "%.3f" % (shatter_hit / plain_hit))

	# Eispanzer: je Froststapel des Angreifers 2 % weniger Schaden
	_magie_waffe("ice_magic", "ic_eispanzer")
	player.iframes = 0.0
	player.blocking = false
	player.shield_hp = 0.0
	wolf.frost_stacks = 0
	player.take_damage(100.0, wolf.global_position, false, wolf)
	var full_dmg: float = player.max_health - player.health
	player.health = player.max_health
	wolf.frost_stacks = 3
	player.take_damage(100.0, wolf.global_position, false, wolf)
	var armored: float = player.max_health - player.health
	_check("Eispanzer: 3 Stapel = 6 % weniger Schaden", _near(armored / full_dmg, 0.94, 0.005), "%.3f" % (armored / full_dmg))
	wolf.frost_stacks = 0

	# Phönix: tödlicher Treffer lässt dich mit 30 % LP aufstehen
	player.health = 10.0
	player.iframes = 0.0
	player.buffs.append({"id": "fi_phoenix", "stats": {"phoenix": 0.3}, "time": 10.0})
	player.take_damage(500.0, wolf.global_position, true)
	_check("Phönix: mit 30 % LP wieder auf", player.is_alive() and _near(player.health, player.max_health * 0.3, 0.5)
		and player.bonus("phoenix") == 0.0, "%.0f LP" % player.health)
	player.health = player.max_health
	player.iframes = 0.0

	# Blitz: Treffer geben Ladungen, Fähigkeiten entladen sie; Ketten springen über
	_magie_waffe("lightning_magic", "li_funkenlaeufer")
	player.charges = 0
	_treffer(wolf)
	_treffer(wolf)
	var two: int = player.charges
	var other = _find(func(n): return n != wolf and n.is_in_group("enemies") and n.is_alive())
	other.max_health = 100000.0
	other.health = other.max_health
	other.global_position = wolf.global_position + Vector3(2, 0, 0)
	_treffer(wolf, {"chain": 1})
	var jumped: bool = other.health < other.max_health
	_check("Blitz: Ladung je Treffer, Kette springt über", two == 2 and jumped, "%d Ladungen" % two)
	player.charges = 5
	player._cast_skill(Game.tree_node("lightning_magic", "li_discharge"))
	var discharge_mult: float = player.action.get("mult", 0.0)
	_check("Entladung verbraucht alle Ladungen (+40 % je Ladung)", player.charges == 0 and _near(discharge_mult, 1.0 * (1.0 + 5 * 0.4), 0.01),
		"Faktor %.2f" % discharge_mult)
	player._end_action(false)

	# Leben: Heiler heilt stärker bei wenig LP, Segner gibt nach jeder Heilung mehr Schaden
	_magie_waffe("life_magic", "lf_heiler")
	player.health = player.max_health * 0.25
	var base_factor: float = 1.0 + player.bonus("healing_pct") + player.bonus("heal_low_pct") + player.bonus("self_heal_pct")
	var healed: float = player.heal(100.0)
	_check("Heiler: bei 25 % LP +37,5 % Heilung", _near(healed, 100.0 * (base_factor + 0.375), 0.01), "%.1f" % healed)
	_magie_waffe("life_magic", "lf_segner")
	player.health = player.max_health * 0.5
	var before: float = player.bonus("damage_pct")
	player.heal(50.0)
	var gained: float = player.bonus("damage_pct") - before
	_check("Segner: Heilung gibt +10 % Schaden", _near(gained, 0.1, 0.001), "%.2f" % gained)

	# Leere: ohne Beschwörer 1 Wesen, mit Beschwörer 2, die Ultimative ruft 3; Opfer sprengt alle
	_magie_waffe("void_magic", "vo_klingenbinder")
	player._summon("wesen", 1, 20.0, 0.5, false)
	player._summon("wesen", 1, 20.0, 0.5, false)
	var alone: int = player.summons.size()
	_magie_waffe("void_magic", "vo_beschwoerer")
	for i in 3:
		player._summon("wesen", 1, 20.0, 0.5, false)
	var two_beings: int = player.summons.size()
	player._summon("wesen", 3, 15.0, 0.8, true)
	_check("Leerenwesen: 1, mit Beschwörer 2, Tor der Leere 3", alone == 1 and two_beings == 2 and player.summons.size() == 3,
		"%d / %d / %d" % [alone, two_beings, player.summons.size()])
	player._sacrifice_summons(3.0, 2.0)
	_check("Opfer sprengt alle Beschwörungen", player.summons.is_empty())

	# Intelligenz 25: +Magieschaden
	_magie_waffe("void_magic", "vo_beschwoerer")
	var plain: float = _treffer(wolf)
	player.buffs.append({"id": "test", "stats": {"magic_damage_pct": 0.1}, "time": 10.0})
	var smart: float = _treffer(wolf)
	_check("Magieschaden-Bonus wirkt auf Magiewaffen", _near(smart / plain, 1.1, 0.005), "%.3f" % (smart / plain))

	# Fürs Bild: Feuerstab mit Glutherz-Seite und etwas Hitze
	_magie_waffe("fire_magic", "fi_glutherz")
	for id in ["fi_lance", "fi_blast", "fi_ignite", "fi_phoenix", "fi_fireball"]:
		player.unlock_node("fire_magic", id)
	player.heat = 64.0
	player.ultimate_charge = 70.0


## Kennung eines Natur-Objekts zum Zählen (abbaubare Quellen: node_id, sonst Modellname)
func _natur_id(n) -> String:
	if n.get("node_id") != null:
		return String(n.node_id)
	if n is MeshInstance3D:
		return "pfuetze"
	for c in n.get_children():
		if not c is CollisionShape3D:
			return String(c.name).rstrip("0123456789_").to_lower()
	return n.get_class()
