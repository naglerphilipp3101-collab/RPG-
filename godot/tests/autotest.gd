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
		player.equipment["weapon2"] = Game.roll_gear("training_sword_2h", [])
		player._recalc_stats()
		player.global_position = Vector3(-24, 0.5, -18)
		player.cam_yaw = 0.0
		player.cam_pitch = -0.1
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


func _next_weapon() -> void:
	if weapon_index >= 0:
		var type: String = weapon_types[weapon_index]
		weapon_results.append("%-10s Schaden gesamt: %d" % [type, roundi(player.damage_dealt_total - weapon_damage_start)])
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
	for node in Game.tree_nodes(type):
		if node["type"] == "active":
			weapon_steps.append("skill:" + String(node["id"]))
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
	elif step_name.begins_with("skill:"):
		var node_id := step_name.substr(6)
		player._mastery(player.weapon_type)["equipped"] = [node_id]
		player.skill_cooldowns.erase(node_id)
		player._try_skill(0)
		if player.state != player.State.ACTION:
			log_lines.append("FEHLER: %s startet keine Aktion" % node_id)


func _save_test() -> void:
	const SaveGame := preload("res://scripts/save_game.gd")
	const PATH := "user://test_save.json"
	_craft_test()
	player.global_position = Vector3(12, 0.5, -3)
	player.health = 123.0
	var before: Dictionary = player.to_save()
	var ok := SaveGame.save(get_tree(), PATH)
	# Zustand verändern, dann laden und vergleichen
	player.inventory.items.clear()
	player.inventory.gear.clear()
	player.equipment.clear()
	player.professions["smelting"] = {"level": 1, "xp": 0}
	player.global_position = Vector3.ZERO
	var loaded := SaveGame.load_into(get_tree(), PATH)
	var after: Dictionary = player.to_save()
	print("AUTOTEST Speichern=%s Laden=%s" % [ok, loaded])
	for key in ["items", "professions", "health"]:
		print("AUTOTEST %s gleich: %s" % [key, JSON.stringify(before[key]) == JSON.stringify(after[key])])
	var p0: Array = before["position"]
	var p1: Array = after["position"]
	print("AUTOTEST position gleich: %s" % (Vector3(p0[0], p0[1], p0[2]).distance_to(Vector3(p1[0], p1[1], p1[2])) < 0.2))
	print("AUTOTEST Ausrüstung vorher %d / nachher %d, Schadensfaktor %.2f" % [
		before["equipment"].size(), after["equipment"].size(), player.damage_mult])
	print("AUTOTEST angelegte Waffe: ", Game.item_name(player.equipment.get("weapon", {"id": "?"})["id"]))
	SaveGame.delete(PATH)
	print("AUTOTEST Testdatei gelöscht: ", not SaveGame.has_save(PATH))


func _craft_test() -> void:
	player.inventory.capacity = 500.0
	player.receive_items({"copper_ore": 40, "green_wood": 20, "raw_hide": 9, "fiber": 12, "stone": 12, "flint": 3,
		"healing_herb": 6, "wolf_fang": 2, "perch": 4})
	player.add_profession_xp("stonecutting", 50) # Schleifstein braucht Steinmetz Stufe 2
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


func _physics_process(delta: float) -> void:
	time += delta
	match phase:
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
				var m: Dictionary = player._mastery("sword_2h")
				m["level"] = 6
				player.unlock_node("sword_2h", "gs_p1")
				player.unlock_node("sword_2h", "gs_p2")
				player.unlock_node("sword_2h", "gs_whirl")
			elif time > 2.5 and time < 2.6 and player.state == player.State.NORMAL:
				var enemy = _find(func(n): return n.has_method("take_damage") and n.is_alive())
				player.global_position = enemy.global_position + Vector3(0, 0.3, 2)
				player.cam_yaw = 0.0
				player._mastery("sword_2h")["equipped"] = ["gs_whirl"]
				player._try_skill(0)
			elif time > 3.4 and time < 3.5:
				get_tree().current_scene.get_node("HUD").set_skill_tree_open(true)
		"weapons":
			if time >= next_action:
				next_action = time + 0.25
				_weapon_step()
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
	print("AUTOTEST Beutebeutel in der Welt: ", get_tree().current_scene.get_children().filter(
		func(c): return c.get("items") != null and c.has_method("_process") and c.get("life") != null).size())
	get_tree().quit()
