extends CanvasLayer
## Bildschirmanzeige: Leben, Ausdauer, Fähigkeiten, Meldungen, Sammel-Hinweise, Inventar und Hilfe.

const InventoryUIScript := preload("res://scripts/inventory_ui.gd")
const CraftingUIScript := preload("res://scripts/crafting_ui.gd")
const PauseMenuScript := preload("res://scripts/pause_menu.gd")
const FehlerMeldenScript := preload("res://scripts/fehler_melden.gd")
const SkillTreeUIScript := preload("res://scripts/skill_tree_ui.gd")
const MinimapScript := preload("res://scripts/minimap.gd")
const CharakterUIScript := preload("res://scripts/charakter_ui.gd")
const KompassScript := preload("res://scripts/kompass.gd")
const NOTIFY_TIME := 3.5
const MAX_NOTIFICATIONS := 7
const HELP_TEXT := """Steuerung
WASD  Bewegen          Maus  Kamera
Strg  Sprinten          Leertaste  Springen
Shift  Ausweichrolle
Linke Maustaste  Angriff (halten = schwer)
Rechte Maustaste  Blocken
Q / E / R  Fähigkeiten    X  Ultimative
F  Sammeln / Häuten / Angeln / Werkstatt
1  Heiltrank    2  Essen    (3, 4 später)
Fernkampf: Rechte Maustaste zielen
T / Mausrad  Waffe wechseln
K  Skillbaum    P  Charakter
M  Karte    N  Minimap-Zoom
F3  Debug-Flug (Strg = ×30, Leertaste/C = hoch/runter)
Tab oder I  Inventar
B  Fehler melden (Ort, Bild, Kommentar)
F1  Hilfe ein/aus    Esc  Pause / Speichern"""

var player = null
var prompt_label: Label
var gather_bar: ProgressBar
var notifications: VBoxContainer
var inventory_ui: Control
var crafting_ui: Control
var pause_menu: Control
var fehler_melden: Control # B: Fehler mit Ort, Bild und Kommentar festhalten
var skill_tree_ui: Control
var charakter_ui: Control
var kompass: Control
var xp_bar: ProgressBar
var level_label: Label
var weapon_label: Label
var crosshair: Control
var ranged_label: Label
var minimap: Control
var quick_slots: Array[Dictionary] = []
var hp_bar: ProgressBar
var hp_label: Label
var stamina_bar: ProgressBar
var skill_slots: Array[Dictionary] = []
var message_label: Label
var message_timer := 0.0
var death_label: Label
var help_panel: PanelContainer
var vignette: ColorRect
var fps_label: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS # damit Esc auch im Pausenzustand funktioniert
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	vignette = ColorRect.new()
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.color = Color(0.7, 0.0, 0.0, 0.0)
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vignette)

	var bottom := VBoxContainer.new()
	bottom.anchor_left = 0.5
	bottom.anchor_right = 0.5
	bottom.anchor_top = 1.0
	bottom.anchor_bottom = 1.0
	bottom.offset_left = -270
	bottom.offset_right = 270
	bottom.offset_top = -190
	bottom.offset_bottom = -24
	bottom.alignment = BoxContainer.ALIGNMENT_END
	bottom.add_theme_constant_override("separation", 6)
	bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(bottom)

	var skills_row := HBoxContainer.new()
	skills_row.alignment = BoxContainer.ALIGNMENT_CENTER
	skills_row.add_theme_constant_override("separation", 10)
	bottom.add_child(skills_row)
	# Q/E/R und die Ultimative (X)
	for i in 4:
		skills_row.add_child(_make_skill_slot(i == 3))
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(14, 0)
	skills_row.add_child(gap)
	# Schnellplätze 1–4 für Tränke und Essen (3 und 4 kommen später)
	for i in Game.QUICK_SLOTS.size():
		skills_row.add_child(_make_skill_slot())
	quick_slots = skill_slots.slice(4)
	skill_slots = skill_slots.slice(0, 4)
	for i in quick_slots.size():
		quick_slots[i]["key"].text = str(i + 1)

	hp_bar = _make_bar(Color(0.78, 0.16, 0.14), 24)
	bottom.add_child(hp_bar)
	hp_label = _make_label(14, Color.WHITE)
	hp_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	hp_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hp_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	hp_bar.add_child(hp_label)
	stamina_bar = _make_bar(Color(0.85, 0.7, 0.2), 10)
	bottom.add_child(stamina_bar)
	# Charakterlevel und Erfahrung
	var xp_row := HBoxContainer.new()
	xp_row.add_theme_constant_override("separation", 8)
	xp_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bottom.add_child(xp_row)
	level_label = _make_label(13, Color(0.85, 0.75, 1.0))
	xp_row.add_child(level_label)
	xp_bar = _make_bar(Color(0.6, 0.45, 0.95), 6)
	xp_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	xp_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	xp_bar.value = 0.0
	xp_row.add_child(xp_bar)

	message_label = _make_label(26, Color(1.0, 0.9, 0.6))
	message_label.anchor_left = 0.0
	message_label.anchor_right = 1.0
	message_label.anchor_top = 0.25
	message_label.anchor_bottom = 0.25
	message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message_label.modulate.a = 0.0
	root.add_child(message_label)

	death_label = _make_label(44, Color(0.9, 0.2, 0.15))
	death_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	death_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	death_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	death_label.visible = false
	root.add_child(death_label)

	help_panel = PanelContainer.new()
	help_panel.position = Vector2(16, 16)
	var help_style := StyleBoxFlat.new()
	help_style.bg_color = Color(0, 0, 0, 0.55)
	help_style.set_corner_radius_all(6)
	help_style.set_content_margin_all(12)
	help_panel.add_theme_stylebox_override("panel", help_style)
	help_panel.add_child(_make_label(15, Color(0.92, 0.92, 0.92), HELP_TEXT))
	root.add_child(help_panel)

	fps_label = _make_label(13, Color(1, 1, 1, 0.6))
	fps_label.anchor_left = 1.0
	fps_label.anchor_right = 1.0
	fps_label.offset_left = -90
	fps_label.offset_top = 8
	root.add_child(fps_label)

	# Interaktionshinweis und Sammel-Fortschritt über der Fähigkeitenleiste
	prompt_label = _make_label(20, Color(1.0, 0.95, 0.8))
	prompt_label.anchor_left = 0.0
	prompt_label.anchor_right = 1.0
	prompt_label.anchor_top = 1.0
	prompt_label.anchor_bottom = 1.0
	prompt_label.offset_top = -262
	prompt_label.offset_bottom = -234
	prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(prompt_label)
	gather_bar = _make_bar(Color(0.45, 0.75, 0.95), 12)
	gather_bar.anchor_left = 0.5
	gather_bar.anchor_right = 0.5
	gather_bar.anchor_top = 1.0
	gather_bar.anchor_bottom = 1.0
	gather_bar.offset_left = -150
	gather_bar.offset_right = 150
	gather_bar.offset_top = -228
	gather_bar.offset_bottom = -216
	gather_bar.visible = false
	root.add_child(gather_bar)

	# Meldungen über erhaltene Gegenstände und Erfahrung (rechts)
	notifications = VBoxContainer.new()
	notifications.anchor_left = 1.0
	notifications.anchor_right = 1.0
	notifications.anchor_top = 0.5
	notifications.anchor_bottom = 0.5
	notifications.offset_left = -340
	notifications.offset_right = -24
	notifications.offset_top = 0
	notifications.offset_bottom = 260
	notifications.alignment = BoxContainer.ALIGNMENT_END
	notifications.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(notifications)

	# Aktive Waffe und Meisterschaft über der Fähigkeitenleiste
	weapon_label = _make_label(15, Color(1.0, 0.88, 0.6))
	weapon_label.anchor_left = 0.0
	weapon_label.anchor_right = 1.0
	weapon_label.anchor_top = 1.0
	weapon_label.anchor_bottom = 1.0
	weapon_label.offset_top = -196
	weapon_label.offset_bottom = -174
	weapon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(weapon_label)

	# Fadenkreuz und Spann-/Nachladeanzeige für Fernkampf
	crosshair = Control.new()
	crosshair.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(crosshair)
	for rect: Rect2 in [Rect2(-1, -9, 2, 6), Rect2(-1, 3, 2, 6), Rect2(-9, -1, 6, 2), Rect2(3, -1, 6, 2)]:
		var line := ColorRect.new()
		line.color = Color(1, 1, 1, 0.85)
		line.position = rect.position
		line.size = rect.size
		line.mouse_filter = Control.MOUSE_FILTER_IGNORE
		crosshair.add_child(line)
	ranged_label = _make_label(14, Color(1.0, 0.9, 0.6))
	ranged_label.position = Vector2(-60, 14)
	ranged_label.size = Vector2(120, 20)
	ranged_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	crosshair.add_child(ranged_label)

	minimap = MinimapScript.new()
	minimap.visible = false # wird sichtbar, sobald main.gd eine Karte liefert
	root.add_child(minimap)
	kompass = KompassScript.new()
	root.add_child(kompass)

	inventory_ui = InventoryUIScript.new()
	root.add_child(inventory_ui)
	crafting_ui = CraftingUIScript.new()
	root.add_child(crafting_ui)
	skill_tree_ui = SkillTreeUIScript.new()
	root.add_child(skill_tree_ui)
	charakter_ui = CharakterUIScript.new()
	root.add_child(charakter_ui)
	pause_menu = PauseMenuScript.new()
	pause_menu.resume_requested.connect(func() -> void: set_paused(false))
	root.add_child(pause_menu)
	fehler_melden = FehlerMeldenScript.new()
	fehler_melden.geschlossen.connect(_fehler_geschlossen)
	root.add_child(fehler_melden)


func bind_player(p) -> void:
	player = p
	fehler_melden.player = p
	fehler_melden.main_node = p.get_parent()
	kompass.player = p
	player.message.connect(show_message)
	player.notify.connect(add_notification)
	player.station_opened.connect(open_station)
	player.hurt.connect(func() -> void: vignette.color.a = 0.22)
	player.died.connect(func() -> void: death_label.visible = true)
	player.respawned.connect(func() -> void: death_label.visible = false)


func show_message(text: String) -> void:
	message_label.text = text
	message_label.modulate.a = 1.0
	message_timer = 2.0


func add_notification(text: String, color: Color) -> void:
	var label := _make_label(17, color, text)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	label.set_meta("time", NOTIFY_TIME)
	notifications.add_child(label)
	while notifications.get_child_count() > MAX_NOTIFICATIONS:
		var oldest := notifications.get_child(0)
		notifications.remove_child(oldest)
		oldest.queue_free()


## Öffnet/schließt das Inventar. Andere Fenster werden dabei geschlossen.
func set_inventory_open(open: bool) -> void:
	if player == null:
		return
	crafting_ui.close()
	skill_tree_ui.close()
	charakter_ui.close()
	if open:
		inventory_ui.open(player)
	else:
		inventory_ui.close()
	_apply_ui_mode()


func set_skill_tree_open(open: bool) -> void:
	if player == null:
		return
	crafting_ui.close()
	inventory_ui.close()
	charakter_ui.close()
	if open:
		skill_tree_ui.open(player)
	else:
		skill_tree_ui.close()
	_apply_ui_mode()


func set_character_open(open: bool) -> void:
	if player == null:
		return
	crafting_ui.close()
	inventory_ui.close()
	skill_tree_ui.close()
	if open:
		charakter_ui.open(player)
	else:
		charakter_ui.close()
	_apply_ui_mode()


func open_station(station_id: String) -> void:
	inventory_ui.close()
	skill_tree_ui.close()
	charakter_ui.close()
	crafting_ui.open(player, station_id)
	_apply_ui_mode()


func close_all_windows() -> void:
	inventory_ui.close()
	crafting_ui.close()
	skill_tree_ui.close()
	charakter_ui.close()
	minimap.set_big(false)
	_apply_ui_mode()


func _any_window_open() -> bool:
	return inventory_ui.visible or crafting_ui.visible or skill_tree_ui.visible or charakter_ui.visible or minimap.big


## Wird von main.gd aufgerufen, wenn eine Welt mit Übersichtskarte geladen ist.
func setup_minimap(main_node, texture: Texture2D, world_size: float, marker_nodes: Array) -> void:
	minimap.setup(player, main_node, texture, world_size, marker_nodes)


func set_world_map_open(open: bool) -> void:
	if not minimap.visible:
		return
	inventory_ui.close()
	crafting_ui.close()
	skill_tree_ui.close()
	charakter_ui.close()
	minimap.set_big(open)
	_apply_ui_mode()


func _apply_ui_mode() -> void:
	var open: bool = _any_window_open() or pause_menu.visible or fehler_melden.visible
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if open else Input.MOUSE_MODE_CAPTURED
	player.ui_open = open


func set_paused(paused: bool) -> void:
	if paused:
		inventory_ui.close()
		crafting_ui.close()
		skill_tree_ui.close()
		charakter_ui.close()
		pause_menu.open()
	else:
		pause_menu.close()
	get_tree().paused = paused
	_apply_ui_mode()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_help"):
		help_panel.visible = not help_panel.visible


# In _input statt _unhandled_input, damit die Oberfläche Tab nicht für den Fokuswechsel schluckt
func _input(event: InputEvent) -> void:
	if fehler_melden.visible:
		return # Tasten gehören dem Kommentarfeld (sonst öffnet z. B. „i“ das Inventar)
	if event.is_action_pressed("fehler_melden") and not pause_menu.visible:
		_fehler_oeffnen()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_cancel"):
		# Esc: erst offene Fenster schließen, sonst Pausenmenü öffnen/schließen
		if _any_window_open():
			close_all_windows()
		else:
			set_paused(not pause_menu.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("inventory") and not pause_menu.visible:
		set_inventory_open(not inventory_ui.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("skill_tree") and not pause_menu.visible:
		set_skill_tree_open(not skill_tree_ui.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("character") and not pause_menu.visible:
		set_character_open(not charakter_ui.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("world_map") and not pause_menu.visible:
		set_world_map_open(not minimap.big)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("minimap_zoom") and not pause_menu.visible:
		minimap.cycle_zoom()


func _fehler_oeffnen() -> void:
	fehler_melden.oeffnen()
	get_tree().paused = true
	_apply_ui_mode()


func _fehler_geschlossen() -> void:
	get_tree().paused = false
	_apply_ui_mode()


func _process(delta: float) -> void:
	fps_label.text = "%d FPS" % Engine.get_frames_per_second()
	if message_timer > 0.0:
		message_timer -= delta
		message_label.modulate.a = clampf(message_timer / 0.4, 0.0, 1.0)
	vignette.color.a = move_toward(vignette.color.a, 0.0, delta * 0.8)
	for label in notifications.get_children():
		var t: float = label.get_meta("time") - delta
		label.set_meta("time", t)
		label.modulate.a = clampf(t / 0.6, 0.0, 1.0)
		if t <= 0.0:
			notifications.remove_child(label)
			label.queue_free()
	if player == null:
		return

	_update_gather_display()

	var hp_ratio: float = player.health / player.max_health
	hp_bar.value = lerpf(hp_bar.value, hp_ratio, clampf(delta * 12.0, 0.0, 1.0))
	hp_label.text = "%d / %d" % [ceili(player.health), int(player.max_health)]
	if player.shield_hp > 0.0:
		hp_label.text += "   (+%d Schild)" % ceili(player.shield_hp)
	stamina_bar.value = player.stamina / player.max_stamina
	var level: int = player.char_level
	var free_points: int = player.attribute_points_free()
	level_label.text = "Level %d" % level + ("   ·   %d Punkte frei (P)" % free_points if free_points > 0 else "")
	xp_bar.value = 1.0 if level >= Game.MAX_CHAR_LEVEL else float(player.char_xp) / Game.char_xp_to_next(level)
	for i in skill_slots.size():
		var info: Dictionary = player.get_skill_info(i)
		var max_cd: float = info["cooldown"]
		var cd: float = info["remaining"]
		skill_slots[i]["name"].text = info["name"] if info["name"] != "" or not info.get("ultimate", false) else "Ultimative\n(K)"
		skill_slots[i]["key"].text = info["key"]
		skill_slots[i]["overlay"].anchor_bottom = cd / max_cd if max_cd > 0.0 else 0.0
		if info.get("ultimate", false):
			var charge := 1.0 - cd / max_cd
			skill_slots[i]["cd"].text = "%d%%" % floori(charge * 100.0) if cd > 0.0 else ""
			skill_slots[i]["panel"].modulate = Color(1.3, 1.15, 0.8) if cd <= 0.0 and info["name"] != "" else Color.WHITE
		else:
			skill_slots[i]["cd"].text = str(ceili(cd)) if cd > 0.0 else ""
	_update_weapon_display()
	if death_label.visible:
		death_label.text = "Du bist gestorben\nWiederbelebung in %d …" % ceili(player.state_timer)
	_update_quick_slots()


func _update_weapon_display() -> void:
	var type: String = player.weapon_type
	var m: Dictionary = player.masteries.get(type, {"level": 1})
	var weapon_name: String = Game.item_name(player.equipment["weapon"]["id"]) if player.equipment.has("weapon") \
		else String(player.weapon_def.get("name", ""))
	var text := "%s   ·   Meisterschaft %d" % [weapon_name, int(m["level"])]
	var points: int = player.mastery_points_free(type)
	if points > 0:
		text += "   ·   %d Skillpunkt%s frei (K)" % [points, "" if points == 1 else "e"]
	if player.equipment.has("weapon2"):
		text += "   ·   T: %s" % Game.item_name(player.equipment["weapon2"]["id"])
	var status: String = player.element_status()
	if status != "":
		text += "   ·   " + status
	weapon_label.text = text

	crosshair.visible = player.is_ranged() and not player.ui_open
	ranged_label.text = ""
	if player.state == player.State.ACTION:
		var kind: String = player.action.get("kind", "")
		if kind == "reload":
			ranged_label.text = "Nachladen %d %%" % roundi(100.0 * float(player.action["time"]) / float(player.action["duration"]))
		elif kind == "draw":
			var r: Dictionary = player.weapon_def.get("ranged", {})
			var draw_time: float = float(r.get("draw_time", 0.9)) / (1.0 + player.bonus("reload_pct"))
			ranged_label.text = "Spannen %d %%" % roundi(100.0 * clampf(float(player.action["time"]) / draw_time, 0.0, 1.0))


func _update_quick_slots() -> void:
	var counts := {"potion": 0, "food": 0}
	var names := {"potion": "Kein Trank", "food": "Kein Essen"}
	var best_tier := {"potion": 0, "food": 0}
	for id in player.inventory.items:
		var c: Dictionary = Game.item(id).get("consumable", {})
		var kind: String = c.get("type", "")
		if not counts.has(kind):
			continue
		counts[kind] += player.inventory.count(id)
		var tier := int(Game.item(id).get("tier", 1))
		if tier > int(best_tier[kind]):
			best_tier[kind] = tier
			names[kind] = Game.item_name(id)
	quick_slots[0]["name"].text = "%s\n×%d" % [names["potion"], counts["potion"]]
	quick_slots[0]["overlay"].anchor_bottom = player.potion_cooldown / player.POTION_COOLDOWN
	quick_slots[0]["cd"].text = str(ceili(player.potion_cooldown)) if player.potion_cooldown > 0.0 else ""
	quick_slots[1]["name"].text = "%s\n×%d" % [names["food"], counts["food"]]
	quick_slots[1]["overlay"].anchor_bottom = 0.0
	quick_slots[1]["cd"].text = "%ds" % ceili(player.food_time) if player.food_time > 0.0 else ""
	for i in range(2, quick_slots.size()):
		var slot: Dictionary = Game.QUICK_SLOTS[i]
		var locked: bool = i >= player.quick_slots
		quick_slots[i]["name"].text = "%s\n%s" % [slot["name"], "gesperrt" if locked else ""]
		quick_slots[i]["overlay"].anchor_bottom = 1.0 if locked else 0.0
		quick_slots[i]["cd"].text = ""


func _update_gather_display() -> void:
	gather_bar.visible = false
	prompt_label.add_theme_color_override("font_color", Color(1.0, 0.95, 0.8))
	if player.state == player.State.GATHER:
		gather_bar.visible = true
		var progress := clampf(player.gather_time / player.gather_total, 0.0, 1.0)
		gather_bar.value = 1.0 - progress
		var hp: float = player.gather_hp
		var power := 0.0
		if player.gather_target != null and is_instance_valid(player.gather_target):
			power = player.get_tool_power(player.gather_target.get_profession())
		prompt_label.text = "%d / %d LP   ·   Abbaukraft %d   ·   Bewegen bricht ab" % [
			ceili(hp * (1.0 - progress)), roundi(hp), roundi(power)]
		prompt_label.add_theme_color_override("font_color", Color(0.75, 0.75, 0.75))
	elif player.state == player.State.FISH:
		if player.fish_phase == "bite":
			prompt_label.text = "Biss!  Jetzt [F] drücken!"
			prompt_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
		else:
			prompt_label.text = "Warte auf einen Biss …   ([F] Angel einholen)"
	else:
		prompt_label.text = player.get_focus_prompt()
		if player.focus_blocked():
			prompt_label.add_theme_color_override("font_color", Color(1.0, 0.45, 0.4))


func _make_label(size: int, color: Color, text := "") -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	label.add_theme_constant_override("outline_size", 4)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label


func _make_bar(color: Color, height: float) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.custom_minimum_size = Vector2(0, height)
	bar.show_percentage = false
	bar.max_value = 1.0
	bar.step = 0.001
	bar.value = 1.0
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.05, 0.05, 0.05, 0.75)
	bg.border_color = Color(0, 0, 0, 0.9)
	bg.set_border_width_all(2)
	bg.set_corner_radius_all(3)
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	fill.set_corner_radius_all(3)
	bar.add_theme_stylebox_override("background", bg)
	bar.add_theme_stylebox_override("fill", fill)
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return bar


func _make_skill_slot(ultimate := false) -> Control:
	var panel := Panel.new()
	panel.custom_minimum_size = Vector2(96, 68) if ultimate else Vector2(84, 68)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.16, 0.1, 0.06, 0.9) if ultimate else Color(0.1, 0.1, 0.12, 0.85)
	style.border_color = Color(1.0, 0.6, 0.2) if ultimate else Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(6)
	panel.add_theme_stylebox_override("panel", style)

	var name_label := _make_label(11, Color(0.9, 0.9, 0.9))
	name_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	name_label.offset_top = 14
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	panel.add_child(name_label)

	var overlay := ColorRect.new()
	overlay.color = Color(0, 0, 0, 0.65)
	overlay.anchor_right = 1.0
	overlay.anchor_bottom = 0.0
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(overlay)

	var cd_label := _make_label(24, Color.WHITE)
	cd_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	cd_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cd_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(cd_label)

	var key_label := _make_label(14, Color(1.0, 0.82, 0.4))
	key_label.position = Vector2(6, 2)
	panel.add_child(key_label)

	skill_slots.append({"name": name_label, "overlay": overlay, "cd": cd_label, "key": key_label, "panel": panel})
	return panel
