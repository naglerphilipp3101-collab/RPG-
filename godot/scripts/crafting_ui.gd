extends Control
## Herstellungsfenster einer Werkstatt: Rezeptliste links, Details, Zusatzmaterialien und Herstellen rechts.

var player = null
var station_id := ""
var selected := ""

var title_label: Label
var level_label: Label
var level_bar: ProgressBar
var recipe_list: VBoxContainer
var name_label: Label
var info_label: Label
var stats_label: Label
var ingredients_box: VBoxContainer
var modifier_header: Label
var modifier_box: VBoxContainer
var amount_row: HBoxContainer
var amount_spin: SpinBox
var craft_button: Button
var result_label: Label
var modifier_pickers: Array[OptionButton] = []


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
	panel.offset_left = -560
	panel.offset_right = 560
	panel.offset_top = -320
	panel.offset_bottom = 320
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.96)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(20)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 12)
	panel.add_child(root)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 16)
	root.add_child(header)
	title_label = _label("", 26, Color(1.0, 0.85, 0.5))
	header.add_child(title_label)
	level_label = _label("", 15, Color(0.85, 0.85, 0.85))
	level_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(level_label)
	level_bar = ProgressBar.new()
	level_bar.show_percentage = false
	level_bar.max_value = 1.0
	level_bar.step = 0.001
	level_bar.custom_minimum_size = Vector2(200, 8)
	level_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(level_bar)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	header.add_child(_label("Esc: schließen", 13, Color(0.6, 0.6, 0.6)))

	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 24)
	root.add_child(body)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(380, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(scroll)
	recipe_list = VBoxContainer.new()
	recipe_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	recipe_list.add_theme_constant_override("separation", 4)
	scroll.add_child(recipe_list)

	var details := VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 8)
	body.add_child(details)
	name_label = _label("", 24, Color.WHITE)
	details.add_child(name_label)
	info_label = _label("", 14, Color(0.7, 0.7, 0.7))
	details.add_child(info_label)
	stats_label = _label("", 15, Color(0.75, 0.9, 1.0))
	stats_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(stats_label)
	details.add_child(_label("Zutaten", 17, Color(1.0, 0.85, 0.5)))
	ingredients_box = VBoxContainer.new()
	details.add_child(ingredients_box)
	modifier_header = _label("", 17, Color(1.0, 0.85, 0.5))
	details.add_child(modifier_header)
	modifier_box = VBoxContainer.new()
	modifier_box.add_theme_constant_override("separation", 6)
	details.add_child(modifier_box)

	var filler := Control.new()
	filler.size_flags_vertical = Control.SIZE_EXPAND_FILL
	details.add_child(filler)

	amount_row = HBoxContainer.new()
	amount_row.add_theme_constant_override("separation", 8)
	details.add_child(amount_row)
	amount_row.add_child(_label("Anzahl", 15, Color.WHITE))
	amount_spin = SpinBox.new()
	amount_spin.min_value = 1
	amount_spin.max_value = 99
	amount_spin.value_changed.connect(func(_v: float) -> void: _update_craft_state())
	amount_row.add_child(amount_spin)
	var max_button := Button.new()
	max_button.text = "Max"
	max_button.pressed.connect(_on_max_pressed)
	amount_row.add_child(max_button)

	craft_button = Button.new()
	craft_button.text = "Herstellen"
	craft_button.custom_minimum_size = Vector2(0, 44)
	craft_button.add_theme_font_size_override("font_size", 18)
	craft_button.pressed.connect(_on_craft_pressed)
	details.add_child(craft_button)
	result_label = _label("", 15, Color(1.0, 0.85, 0.5))
	details.add_child(result_label)


func open(p, id: String) -> void:
	player = p
	station_id = id
	var station: Dictionary = Game.stations.get(id, {})
	title_label.text = station.get("name", id)
	result_label.text = ""
	selected = ""
	visible = true
	_refresh()


func close() -> void:
	visible = false


func _station_recipes() -> Array[String]:
	var ids: Array[String] = []
	for rid in Game.recipes:
		if Game.recipes[rid]["station"] == station_id:
			ids.append(rid)
	ids.sort_custom(func(a: String, b: String) -> bool:
		return int(Game.recipes[a].get("level", 1)) < int(Game.recipes[b].get("level", 1)))
	return ids


func _refresh() -> void:
	var profession: String = Game.stations[station_id]["profession"]
	var level: int = player.get_profession_level(profession)
	var xp: int = player.professions[profession]["xp"]
	level_label.text = "%s  Stufe %d   (%d / %d EP)" % [Game.profession_name(profession), level, xp, Game.xp_to_next(level)]
	level_bar.value = float(xp) / Game.xp_to_next(level)

	for child in recipe_list.get_children():
		recipe_list.remove_child(child)
		child.queue_free()
	var ids := _station_recipes()
	if selected == "" and not ids.is_empty():
		selected = ids[0]
	for rid in ids:
		recipe_list.add_child(_make_recipe_button(rid, level))
	_show_details()


func _make_recipe_button(rid: String, level: int) -> Button:
	var recipe: Dictionary = Game.recipes[rid]
	var output: String = recipe["output"]
	var tier := int(Game.item(output).get("tier", 1))
	var button := Button.new()
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	button.toggle_mode = true
	button.button_pressed = rid == selected
	button.text = "  %s   ·   Tier %s   ·   Stufe %d" % [Game.item_name(output), Game.tier_name(tier), int(recipe.get("level", 1))]
	var color := Color.WHITE
	if level < int(recipe.get("level", 1)):
		color = Color(0.5, 0.5, 0.5)
	elif player.craft_check(rid) != "":
		color = Color(1.0, 0.55, 0.5)
	else:
		color = Game.tier_color(tier).lightened(0.4)
	button.add_theme_color_override("font_color", color)
	button.add_theme_color_override("font_pressed_color", color)
	button.add_theme_color_override("font_hover_color", color.lightened(0.2))
	button.pressed.connect(func() -> void:
		selected = rid
		result_label.text = ""
		_refresh.call_deferred()) # verzögert, weil _refresh diesen Button entfernt
	return button


func _show_details() -> void:
	for child in ingredients_box.get_children():
		ingredients_box.remove_child(child)
		child.queue_free()
	for child in modifier_box.get_children():
		modifier_box.remove_child(child)
		child.queue_free()
	modifier_pickers.clear()
	if selected == "":
		return
	var recipe: Dictionary = Game.recipes[selected]
	var output: String = recipe["output"]
	var def := Game.item(output)
	var tier := int(def.get("tier", 1))
	var gear := Game.is_gear(output)

	name_label.text = String(def.get("name", output))
	name_label.add_theme_color_override("font_color", Game.tier_color(tier).lightened(0.3))
	info_label.text = "Tier %s  ·  %s  ·  benötigt %s Stufe %d  ·  +%d EP" % [Game.tier_name(tier), def.get("category", ""),
		Game.profession_name(Game.stations[station_id]["profession"]), int(recipe.get("level", 1)), int(recipe.get("xp", 0))]
	stats_label.text = _describe_output(output)

	var ingredients: Dictionary = recipe["ingredients"]
	for id in ingredients:
		var have: int = player.inventory.count(id)
		var need := int(ingredients[id])
		var line := _label("%s     %d / %d" % [Game.item_name(id), have, need], 15,
			Color(0.6, 0.95, 0.6) if have >= need else Color(1.0, 0.5, 0.45))
		ingredients_box.add_child(line)

	amount_row.visible = not gear
	modifier_header.visible = gear
	if gear:
		var slots := Game.modifier_slots(output)
		modifier_header.text = "Zusatzmaterialien  (%d %s)" % [slots, "Platz" if slots == 1 else "Plätze"]
		for i in slots:
			modifier_box.add_child(_make_modifier_picker(output))
	_update_craft_state()


func _describe_output(output: String) -> String:
	var def := Game.item(output)
	var lines: Array[String] = []
	var ranges: Dictionary = def.get("stats", {})
	for stat in ranges:
		var r: Array = ranges[stat]
		lines.append("%s  %d – %d" % [Game.STAT_NAMES.get(stat, stat), int(r[0]), int(r[1])])
	var mod: Dictionary = def.get("modifier", {})
	if not mod.is_empty():
		var slot_names: Array[String] = []
		for s in mod.get("slots", []):
			slot_names.append(Game.SLOT_NAMES.get(s, s))
		lines.append("Zusatzmaterial für %s:  %s" % [", ".join(slot_names), Game.format_stat(mod["stat"], mod["value"])])
	lines.append(String(def.get("description", "")))
	return "\n".join(lines)


func _make_modifier_picker(output: String) -> OptionButton:
	var picker := OptionButton.new()
	picker.add_item("— leer —")
	picker.set_item_metadata(0, "")
	for id in player.inventory.items:
		if Game.modifier_fits(id, output):
			var mod: Dictionary = Game.item(id)["modifier"]
			picker.add_item("%s  (×%d)   %s" % [Game.item_name(id), player.inventory.count(id), Game.format_stat(mod["stat"], mod["value"])])
			picker.set_item_metadata(picker.item_count - 1, id)
	picker.item_selected.connect(func(_i: int) -> void: _update_craft_state())
	modifier_pickers.append(picker)
	return picker


func _selected_modifiers() -> Array:
	var mods: Array = []
	for picker in modifier_pickers:
		var id: String = picker.get_item_metadata(picker.selected)
		if id != "":
			mods.append(id)
	return mods


func _amount() -> int:
	return 1 if Game.is_gear(Game.recipes[selected]["output"]) else int(amount_spin.value)


func _update_craft_state() -> void:
	if selected == "":
		craft_button.disabled = true
		return
	var error: String = player.craft_check(selected, _amount(), _selected_modifiers())
	craft_button.disabled = error != ""
	craft_button.tooltip_text = error
	if error != "" and result_label.text == "":
		result_label.text = error
		result_label.add_theme_color_override("font_color", Color(1.0, 0.5, 0.45))
	elif error == "" and result_label.get_theme_color("font_color") == Color(1.0, 0.5, 0.45):
		result_label.text = ""


func _on_max_pressed() -> void:
	var ingredients: Dictionary = Game.recipes[selected]["ingredients"]
	var most := 99
	for id in ingredients:
		most = mini(most, int(player.inventory.count(id) / int(ingredients[id])))
	amount_spin.value = maxi(most, 1)


func _on_craft_pressed() -> void:
	var error: String = player.craft(selected, _amount(), _selected_modifiers())
	if error == "":
		result_label.text = "Hergestellt: %s" % Game.item_name(Game.recipes[selected]["output"])
		result_label.add_theme_color_override("font_color", Color(0.6, 0.95, 0.6))
	else:
		result_label.text = error
		result_label.add_theme_color_override("font_color", Color(1.0, 0.5, 0.45))
	_refresh()


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
