extends Control
## Skillbaum-Fenster (K): zwei Seiten pro Waffe mit je einer Passiven, 4 Fähigkeiten und einer Ultimativen.
## Punkte aus der Waffenmeisterschaft; 3 Fähigkeiten auf Q/E/R, eine Ultimative auf X, eine Passive aktiv.
## Rechts eine Übersicht aller Meisterschaften.

var player = null
var view_type := "" # angezeigter Waffentyp (Standard: aktive Waffe)

var title_label: Label
var role_label: Label
var level_label: Label
var level_bar: ProgressBar
var points_label: Label
var branch_boxes: Array[VBoxContainer] = []
var mastery_list: VBoxContainer
var status_label: Label


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false

	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.5)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)

	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = -640
	panel.offset_right = 640
	panel.offset_top = -330
	panel.offset_bottom = 330
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
	role_label = _label("", 13, Color(0.7, 0.7, 0.7))
	role_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(role_label)
	level_label = _label("", 15, Color(0.85, 0.85, 0.85))
	level_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(level_label)
	level_bar = ProgressBar.new()
	level_bar.show_percentage = false
	level_bar.max_value = 1.0
	level_bar.step = 0.001
	level_bar.custom_minimum_size = Vector2(180, 8)
	level_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(level_bar)
	points_label = _label("", 17, Color(0.6, 1.0, 0.6))
	points_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(points_label)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	var reset := Button.new()
	reset.text = "Punkte zurücksetzen"
	reset.pressed.connect(func() -> void:
		player.reset_tree(view_type)
		_refresh.call_deferred())
	header.add_child(reset)

	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 24)
	root.add_child(body)
	for i in 2:
		var column := VBoxContainer.new()
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		column.add_theme_constant_override("separation", 8)
		body.add_child(column)
		branch_boxes.append(column)

	var right := VBoxContainer.new()
	right.custom_minimum_size = Vector2(230, 0)
	right.add_theme_constant_override("separation", 4)
	body.add_child(right)
	right.add_child(_label("Meisterschaften", 18, Color(1.0, 0.85, 0.5)))
	mastery_list = VBoxContainer.new()
	mastery_list.add_theme_constant_override("separation", 2)
	right.add_child(mastery_list)

	status_label = _label("", 14, Color(1.0, 0.85, 0.5))
	root.add_child(status_label)
	root.add_child(_label("Klick: freischalten   ·   Klick auf Freigeschaltetes: Fähigkeit auf Q / E / R legen oder entfernen, "
		+ "Passive aktivieren, Ultimative auf X legen   ·   Ultimative: Passive + 2 Fähigkeiten der Seite   ·   K / Esc: schließen",
		12, Color(0.6, 0.6, 0.6)))


func open(p) -> void:
	if player != p:
		player = p
		player.equipment_changed.connect(_on_equipment_changed, CONNECT_DEFERRED)
	view_type = player.weapon_type
	status_label.text = ""
	visible = true
	_refresh()


func close() -> void:
	visible = false


func _on_equipment_changed() -> void:
	if visible:
		_refresh()


func _refresh() -> void:
	var def := Game.weapon_def(view_type)
	var m: Dictionary = player._mastery(view_type)
	var level := int(m["level"])
	title_label.text = String(def.get("name", view_type))
	if view_type != player.weapon_type:
		title_label.text += "  (nicht angelegt)"
	if level >= Game.MAX_MASTERY_LEVEL:
		level_label.text = "Meisterschaft Stufe %d (max.)" % level
		level_bar.value = 1.0
	else:
		level_label.text = "Meisterschaft Stufe %d   (%d / %d EP)" % [level, int(m["xp"]), Game.mastery_xp_to_next(level)]
		level_bar.value = float(m["xp"]) / Game.mastery_xp_to_next(level)
	points_label.text = "Freie Punkte: %d" % player.mastery_points_free(view_type)

	role_label.text = String(def.get("role", ""))

	var sides: Array = def.get("sides", [])
	for i in branch_boxes.size():
		var box := branch_boxes[i]
		for child in box.get_children():
			box.remove_child(child)
			child.queue_free()
		if i >= sides.size():
			continue
		box.add_child(_label(String(sides[i]["name"]), 20, Color(1.0, 0.85, 0.5)))
		for node in sides[i]["nodes"]:
			box.add_child(_make_node_button(node, m))
	_refresh_masteries()


func _make_node_button(node: Dictionary, m: Dictionary) -> Button:
	var node_id: String = node["id"]
	var kind: String = node.get("type", "active")
	var unlocked: bool = m["unlocked"].has(node_id)
	var error: String = player.unlock_check(view_type, node_id)
	var cost := Game.node_cost(node)
	var free: bool = node_id == player.start_node(view_type)
	var button := Button.new()
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	button.custom_minimum_size = Vector2(0, 52)
	button.add_theme_font_size_override("font_size", 14)
	var text := ""
	var selected := false # aktive Passive, gewählte Ultimative oder ausgerüstete Fähigkeit
	match kind:
		"passive":
			text = "●  Passive: %s" % node["name"]
			selected = m["passive"] == node_id
			if selected:
				text += "   [aktiv]"
		"ultimate":
			text = "★  Ultimative: %s" % node["name"]
			selected = m["ultimate"] == node_id
			if selected:
				text += "   [%s]" % Game.ULTIMATE_KEY
		_:
			text = "◆  %s" % node["name"]
			var equipped_index: int = m["equipped"].find(node_id)
			selected = equipped_index >= 0
			if selected:
				text += "   [%s]" % Game.SKILL_KEYS[equipped_index]
	if not unlocked:
		text += "   (%d Punkte)" % cost
	text += "\n" + String(node.get("desc", ""))
	button.text = text

	var color := Color(0.45, 0.45, 0.45)
	var hint := error
	if unlocked:
		color = Color(1.0, 0.85, 0.4) if selected else Color(0.55, 0.95, 0.55)
		match kind:
			"passive": hint = "Klick: diese Passive aktivieren (nur eine wirkt)"
			"ultimate": hint = "Klick: als Ultimative auf %s legen" % Game.ULTIMATE_KEY
			_: hint = "Klick: auf Q/E/R legen oder entfernen" + ("   (Startfähigkeit, kostenlos)" if free else "")
	elif error == "":
		color = Color.WHITE
		hint = "Klick: freischalten (%d Punkte)" % cost
	if kind == "ultimate" and not unlocked:
		color = color.lerp(Color(1.0, 0.6, 0.25), 0.4)
	button.add_theme_color_override("font_color", color)
	button.add_theme_color_override("font_hover_color", color.lightened(0.2))
	button.tooltip_text = Game.describe_node(node) + "\n\n" + hint
	button.pressed.connect(func() -> void:
		var result := ""
		if unlocked:
			result = player.toggle_skill(view_type, node_id)
		else:
			result = player.unlock_node(view_type, node_id)
		status_label.text = result
		_refresh.call_deferred()) # verzögert, weil _refresh diesen Button entfernt
	return button


func _refresh_masteries() -> void:
	for child in mastery_list.get_children():
		mastery_list.remove_child(child)
		child.queue_free()
	for type in Game.weapons:
		var level := int(player.masteries[type]["level"]) if player.masteries.has(type) else 1
		var button := Button.new()
		button.flat = true
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.text = "%s   %d" % [Game.weapons[type]["name"], level]
		var color := Color(1.0, 0.85, 0.4) if type == view_type else Color(0.8, 0.8, 0.8)
		button.add_theme_color_override("font_color", color)
		button.pressed.connect(func() -> void:
			view_type = type
			status_label.text = ""
			_refresh.call_deferred())
		mastery_list.add_child(button)


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
