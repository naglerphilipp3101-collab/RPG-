extends Control
## Inventarfenster (Tab / I): Ausrüstung, Gegenstände im Raster, Gewicht und Berufsstufen.

const COLUMNS := 8
const MIN_SLOTS := 40
const EQUIP_ORDER := ["weapon", "weapon2", "weapon3", "shield", "head", "chest", "legs", "ring"]
const PROFESSION_GROUPS := {"gathering": "Sammeln", "refining": "Veredeln", "crafting": "Herstellen"}

var player = null
var grid: GridContainer
var weight_bar: ProgressBar
var weight_label: Label
var equip_box: VBoxContainer
var stats_label: Label
var professions_box: VBoxContainer


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false

	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.45)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)

	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = -660
	panel.offset_right = 660
	panel.offset_top = -330
	panel.offset_bottom = 330
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.95)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(20)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 26)
	panel.add_child(columns)

	# Links: Ausrüstung
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(270, 0)
	left.add_theme_constant_override("separation", 6)
	columns.add_child(left)
	left.add_child(_label("Ausrüstung", 24, Color(1.0, 0.85, 0.5)))
	equip_box = VBoxContainer.new()
	equip_box.add_theme_constant_override("separation", 4)
	left.add_child(equip_box)
	stats_label = _label("", 13, Color(0.75, 0.9, 1.0))
	left.add_child(stats_label)

	# Mitte: Gegenstände
	var middle := VBoxContainer.new()
	middle.add_theme_constant_override("separation", 10)
	columns.add_child(middle)
	middle.add_child(_label("Inventar", 24, Color(1.0, 0.85, 0.5)))
	var weight_row := HBoxContainer.new()
	weight_row.add_theme_constant_override("separation", 10)
	middle.add_child(weight_row)
	weight_label = _label("", 14, Color(0.85, 0.85, 0.85))
	weight_row.add_child(weight_label)
	weight_bar = ProgressBar.new()
	weight_bar.show_percentage = false
	weight_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	weight_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	weight_bar.custom_minimum_size = Vector2(0, 10)
	weight_bar.max_value = 1.0
	weight_bar.step = 0.001
	weight_row.add_child(weight_bar)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size = Vector2(COLUMNS * 72, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	middle.add_child(scroll)
	grid = GridContainer.new()
	grid.columns = COLUMNS
	grid.add_theme_constant_override("h_separation", 6)
	grid.add_theme_constant_override("v_separation", 6)
	scroll.add_child(grid)
	var hint := _label("Linksklick: ausrüsten / benutzen   ·   Rechtsklick: 1 wegwerfen   ·   Shift + Rechtsklick: alles wegwerfen",
		12, Color(0.6, 0.6, 0.6))
	middle.add_child(hint)

	# Rechts: Berufe
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_theme_constant_override("separation", 6)
	columns.add_child(right)
	right.add_child(_label("Berufe", 24, Color(1.0, 0.85, 0.5)))
	var prof_scroll := ScrollContainer.new()
	prof_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	prof_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	right.add_child(prof_scroll)
	professions_box = VBoxContainer.new()
	professions_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	professions_box.add_theme_constant_override("separation", 5)
	prof_scroll.add_child(professions_box)


func open(p) -> void:
	if player != p:
		player = p
		# Verzögert, damit ein Slot sich nicht während seines eigenen Klicks entfernt
		player.inventory.changed.connect(refresh, CONNECT_DEFERRED)
		player.equipment_changed.connect(refresh, CONNECT_DEFERRED)
	visible = true
	refresh()


func close() -> void:
	visible = false


func refresh() -> void:
	if not visible or player == null:
		return
	_clear(grid)
	var inv = player.inventory
	var shown := 0
	for id in inv.items:
		grid.add_child(_make_item_slot(id, inv.count(id)))
		shown += 1
	for g in inv.gear:
		grid.add_child(_make_gear_slot(g))
		shown += 1
	while shown < MIN_SLOTS or shown % COLUMNS != 0:
		grid.add_child(_make_empty_slot())
		shown += 1
	var w: float = inv.weight()
	weight_label.text = "Gewicht  %.1f / %.0f" % [w, inv.capacity]
	weight_bar.value = w / inv.capacity
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(0.85, 0.3, 0.2) if w / inv.capacity > 0.9 else Color(0.75, 0.62, 0.35)
	weight_bar.add_theme_stylebox_override("fill", fill)
	_refresh_equipment()
	_refresh_professions()


func _clear(box: Node) -> void:
	for child in box.get_children():
		box.remove_child(child)
		child.queue_free()


# --- Ausrüstung ---------------------------------------------------------

func _refresh_equipment() -> void:
	_clear(equip_box)
	for key in EQUIP_ORDER:
		if key in player.WEAPON_SLOTS and not key in player.active_weapon_slots():
			continue # dritter Waffenplatz erst nach der Level-40-Quest
		equip_box.add_child(_make_equip_row(key, Game.SLOT_NAMES[key]))
	equip_box.add_child(_label("Werkzeuge", 15, Color(1.0, 0.85, 0.5)))
	for id in Game.professions:
		var info: Dictionary = Game.professions[id]
		if info.get("type", "") == "gathering":
			equip_box.add_child(_make_equip_row("tool:" + String(id), info.get("tool_name", id)))
	stats_label.text = "Schaden ×%.2f   ·   Krit %d %%   ·   Blutung %d %%\nRüstung %d   ·   Block %d   ·   Leben %d" % [
		player.damage_mult, roundi(player.crit_chance * 100.0), roundi(player.bleed_chance * 100.0),
		roundi(player.armor), roundi(player.block_power), roundi(player.max_health)]


func _make_equip_row(key: String, slot_name: String) -> Control:
	var row := Panel.new()
	row.custom_minimum_size = Vector2(0, 30)
	var text := "%s:  —" % slot_name
	var border := Color(0.22, 0.22, 0.25)
	if player.equipment.has(key):
		var g: Dictionary = player.equipment[key]
		var tier := int(Game.item(g["id"]).get("tier", 1))
		text = "%s:  %s" % [slot_name, Game.item_name(g["id"])]
		border = Game.tier_color(tier)
		row.tooltip_text = Game.gear_tooltip(g) + "\n\nLinksklick: ablegen"
		row.gui_input.connect(func(event: InputEvent) -> void:
			var mb := event as InputEventMouseButton
			if mb and mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
				player.unequip(key))
	row.add_theme_stylebox_override("panel", _slot_style(border))
	var label := _label(text, 13, Color.WHITE if player.equipment.has(key) else Color(0.5, 0.5, 0.5))
	label.position = Vector2(8, 6)
	row.add_child(label)
	return row


# --- Berufe -------------------------------------------------------------

func _refresh_professions() -> void:
	_clear(professions_box)
	for group in PROFESSION_GROUPS:
		professions_box.add_child(_label(PROFESSION_GROUPS[group], 15, Color(1.0, 0.85, 0.5)))
		for id in Game.professions:
			var info: Dictionary = Game.professions[id]
			if info.get("type", "") != group:
				continue
			var level: int = player.get_profession_level(id)
			var xp: int = player.professions[id]["xp"]
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 6)
			var name_label := _label(info.get("name", id), 13, Color.WHITE)
			name_label.custom_minimum_size = Vector2(120, 0)
			row.add_child(name_label)
			var bar := ProgressBar.new()
			bar.show_percentage = false
			bar.custom_minimum_size = Vector2(60, 6)
			bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			bar.max_value = 1.0
			bar.step = 0.001
			var maxed := level >= Game.MAX_PROFESSION_LEVEL
			bar.value = 1.0 if maxed else float(xp) / Game.xp_to_next(level)
			row.add_child(bar)
			row.add_child(_label("%d / %d" % [level, Game.MAX_PROFESSION_LEVEL], 13, Color(1.0, 0.85, 0.5)))
			row.tooltip_text = "Skill %d (max.)" % level if maxed else "Skill %d  ·  %d / %d EP bis zum nächsten Punkt" % [
				level, xp, Game.xp_to_next(level)]
			row.tooltip_text += "\nTier %s freigeschaltet" % Game.tier_name(player.profession_tier(id))
			if group == "gathering":
				row.tooltip_text += "  ·  Aufspüren bis Tier %s" % Game.tier_name(player.track_tier(id)) \
					if player.track_tier(id) > 0 else "  ·  Aufspüren ab Skill %d" % Game.TRACK_OFFSET
				row.tooltip_text += "\nAbbaukraft: %d" % roundi(player.get_tool_power(id))
			elif group == "refining":
				row.tooltip_text += "\nBonus-Ausbeute: %d %%" % roundi(player.refining_bonus_chance(id) * 100.0)
			professions_box.add_child(row)


# --- Slots --------------------------------------------------------------

func _slot_style(border: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.13, 0.13, 0.15)
	style.border_color = border
	style.set_border_width_all(2)
	style.set_corner_radius_all(5)
	return style


func _make_empty_slot() -> Control:
	var slot := Panel.new()
	slot.custom_minimum_size = Vector2(66, 66)
	slot.add_theme_stylebox_override("panel", _slot_style(Color(0.22, 0.22, 0.25)))
	slot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return slot


func _make_base_slot(id: String, corner_text: String, square_icon: bool) -> Panel:
	var data := Game.item(id)
	var tier := int(data.get("tier", 1))
	var slot := Panel.new()
	slot.custom_minimum_size = Vector2(66, 66)
	slot.add_theme_stylebox_override("panel", _slot_style(Game.tier_color(tier)))

	var icon := Panel.new()
	icon.position = Vector2(13, 11)
	icon.size = Vector2(40, 40)
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var icon_style := StyleBoxFlat.new()
	icon_style.bg_color = Game.item_color(id)
	icon_style.set_corner_radius_all(4 if square_icon else 20)
	icon.add_theme_stylebox_override("panel", icon_style)
	slot.add_child(icon)

	var letter := _label(String(data.get("name", "?")).left(1), 20, Color(0, 0, 0, 0.6))
	letter.position = Vector2(13, 11)
	letter.size = Vector2(40, 40)
	letter.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	letter.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	slot.add_child(letter)

	var tier_label := _label(Game.tier_name(tier), 11, Game.tier_color(tier))
	tier_label.position = Vector2(5, 1)
	slot.add_child(tier_label)

	var corner := _label(corner_text, 14, Color.WHITE)
	corner.anchor_left = 1.0
	corner.anchor_right = 1.0
	corner.anchor_top = 1.0
	corner.anchor_bottom = 1.0
	corner.offset_left = -50
	corner.offset_right = -5
	corner.offset_top = -21
	corner.offset_bottom = -2
	corner.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	slot.add_child(corner)
	return slot


func _make_item_slot(id: String, amount: int) -> Control:
	var data := Game.item(id)
	var slot := _make_base_slot(id, str(amount), false)
	var weight: float = player.inventory.item_weight(id)
	slot.tooltip_text = "%s\nTier %s  ·  %s\nGewicht %.1f  (gesamt %.1f)\n\n%s" % [
		data.get("name", id), Game.tier_name(int(data.get("tier", 1))), data.get("category", ""),
		weight, weight * amount, data.get("description", "")]
	if data.has("consumable"):
		slot.tooltip_text += "\n\nLinksklick: benutzen"
	slot.gui_input.connect(_on_item_input.bind(id))
	return slot


func _make_gear_slot(g: Dictionary) -> Control:
	# Kennzeichnet bessere Stücke als die aktuell angelegten mit ▲
	var slot := _make_base_slot(g["id"], "▲" if _is_upgrade(g) else "", true)
	slot.tooltip_text = Game.gear_tooltip(g) + "\n\nLinksklick: ausrüsten   ·   Shift + Rechtsklick: wegwerfen"
	slot.gui_input.connect(_on_gear_input.bind(int(g["uid"])))
	return slot


func _is_upgrade(g: Dictionary) -> bool:
	var key := Game.equip_key(g["id"])
	if not player.equipment.has(key):
		return true
	var current: Dictionary = player.equipment[key]
	var score := func(gear: Dictionary) -> float:
		var total := 0.0
		for stat in gear["stats"]:
			total += float(gear["stats"][stat]) * (100.0 if Game.PERCENT_STATS.has(stat) else 1.0)
		return total
	return score.call(g) > score.call(current)


func _on_item_input(event: InputEvent, id: String) -> void:
	var mb := event as InputEventMouseButton
	if mb == null or not mb.pressed:
		return
	if mb.button_index == MOUSE_BUTTON_LEFT and Game.item(id).has("consumable"):
		player.use_consumable(Game.item(id)["consumable"]["type"])
	elif mb.button_index == MOUSE_BUTTON_RIGHT:
		var amount: int = player.inventory.count(id) if mb.shift_pressed else 1
		player.inventory.remove(id, amount)


func _on_gear_input(event: InputEvent, uid: int) -> void:
	var mb := event as InputEventMouseButton
	if mb == null or not mb.pressed:
		return
	if mb.button_index == MOUSE_BUTTON_LEFT:
		player.equip(uid)
	elif mb.button_index == MOUSE_BUTTON_RIGHT and mb.shift_pressed:
		player.inventory.take_gear(uid)


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
