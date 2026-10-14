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


## Natur auf der Insel: Spieler in einen Wald nahe dem Startgebiet setzen, alles laden, zählen,
## einen Baum fällen und eine Pflanze ernten. Mit --write-movie entstehen Bilder vom Waldrand.
func _natur_test() -> void:
	var natur = get_tree().current_scene.natur
	var start := Vector2(player.global_position.x, player.global_position.z)
	var ort := Vector2.INF
	var biome: Array = [natur.FELS] if OS.get_cmdline_user_args().has("--fels") else [natur.LAUBWALD, natur.NADELWALD]
	for r in range(260, 4000, 20):
		for i in 24:
			var p := start + Vector2.from_angle(TAU * i / 24.0) * r
			if natur._biom(p.x, p.y) in biome and not natur._gesperrt(p.x, p.y):
				ort = p
				break
		if ort != Vector2.INF:
			break
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
		zahl[n.node_id] = int(zahl.get(n.node_id, 0)) + 1
	print("AUTOTEST Natur: Ort %s (Höhe %.0f m), %d Objekte im Nahbereich in %d ms, Fernkachel in %d ms" % [ort.round(), h, natur._nah.size(), t_nah, t_fern])
	print("AUTOTEST Natur Arten: ", zahl)
	# nächsten Baum und nächste Pflanze ernten
	for gruppe in [["fichte", "kiefer", "eiche"], ["hanf", "beeren", "kraut"], ["felsbrocken"]]:
		var best = null
		var best_d := INF
		for n in natur._nah.values():
			if String(n.node_id).get_slice("_", 0) in gruppe:
				var d: float = n.global_position.distance_to(player.global_position)
				if d < best_d:
					best_d = d
					best = n
		if best:
			best.harvest(player)
			print("AUTOTEST Natur geerntet: %s (%.0f m entfernt), danach abbaubar: %s" % [best.node_id, best_d, best.is_interactable()])
	# nächsten uralten Baum fällen (gibt Gereiftes Holz) – vorher Holzfällerstufe 3, sonst ist er gesperrt
	var uralt = null
	for n in natur._nah.values():
		if String(n.node_id).ends_with("_uralt") and (uralt == null or n.global_position.distance_to(player.global_position) < uralt.global_position.distance_to(player.global_position)):
			uralt = n
	if uralt:
		uralt.harvest(player)
		print("AUTOTEST Natur uralter Baum: %s (%.0f m entfernt), danach abbaubar: %s" % [uralt.node_id, uralt.global_position.distance_to(player.global_position), uralt.is_interactable()])
	var monolithen := 0
	for mk_ in natur._mono_cache:
		monolithen += natur._mono_cache[mk_].size()
	print("AUTOTEST Natur Monolithen in %d geladenen Fernkacheln: %d" % [natur._mono_cache.size(), monolithen])
	print("AUTOTEST Natur Inventar: ", player.inventory.items)
	player.cam_yaw = 0.3
	player.cam_pitch = -0.12
	if OS.get_cmdline_user_args().has("--uralt"):
		# vor den nächsten noch stehenden uralten Baum stellen, leicht nach oben schauen
		var baum = null
		for n in natur._nah.values():
			if String(n.node_id).ends_with("_uralt") and n.is_interactable() \
					and (baum == null or n.global_position.distance_to(player.global_position) < baum.global_position.distance_to(player.global_position)):
				baum = n
		if baum:
			var p: Vector3 = baum.global_position + Vector3(24, 0, 0)
			player.global_position = Vector3(p.x, natur._hoehe(p.x, p.z) + 1.0, p.z)
			player.cam_yaw = PI / 2.0
			player.cam_pitch = 0.18
	if OS.get_cmdline_user_args().has("--monolith"):
		# zum nächsten Felsmonolithen (sucht in den Kacheln rund um den Spieler)
		var best := []
		var best_d := INF
		var mk := Vector2i(floori(player.global_position.x / 256.0), floori(player.global_position.z / 256.0))
		for dz in range(-6, 7):
			for dx in range(-6, 7):
				for m in natur._monolithen(mk + Vector2i(dx, dz)):
					var d := Vector2(m[0], m[2]).distance_to(Vector2(player.global_position.x, player.global_position.z))
					if d < best_d:
						best_d = d
						best = m
		if not best.is_empty():
			var p := Vector3(best[0] + 22.0, 0, best[2] + 8.0)
			player.global_position = Vector3(p.x, natur._hoehe(p.x, p.z) + 1.0, p.z)
			var blick := Vector3(best[0], 0, best[2]) - p
			player.cam_yaw = atan2(-blick.x, -blick.z)
			player.cam_pitch = 0.1
			natur._fern_bauen(Vector2i(floori(best[0] / 256.0), floori(best[2] / 256.0)))
			print("AUTOTEST Monolith: %s bei %s, %.0f m entfernt" % ["Turm" if int(best[3]) == 0 else "Gruppe", Vector2(best[0], best[2]).round(), best_d])
	if OS.get_cmdline_user_args().has("--fels"):
		# vor den nächsten noch stehenden Felsbrocken stellen und hinsehen
		var stein = null
		for n in natur._nah.values():
			if String(n.node_id).begins_with("felsbrocken") and n.is_interactable() \
					and (stein == null or n.global_position.distance_to(player.global_position) < stein.global_position.distance_to(player.global_position)):
				stein = n
		if stein:
			# Richtung mit dem geringsten Höhenunterschied (sonst drückt der Hang die Kamera weg)
			var best_dir := Vector3.FORWARD
			var best_dh := INF
			for i in 12:
				var d := Vector3(cos(TAU * i / 12.0), 0, sin(TAU * i / 12.0))
				var q: Vector3 = stein.global_position + d * 6.0
				var dh := absf(natur._hoehe(q.x, q.z) - stein.global_position.y)
				if dh < best_dh:
					best_dh = dh
					best_dir = d
			var p: Vector3 = stein.global_position + best_dir * 6.0
			player.global_position = Vector3(p.x, natur._hoehe(p.x, p.z) + 1.0, p.z)
			player.cam_yaw = atan2(best_dir.x, best_dir.z)
			player.cam_pitch = -0.35
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
