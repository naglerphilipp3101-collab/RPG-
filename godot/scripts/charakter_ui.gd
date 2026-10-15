extends Control
## Charakterfenster (P): Level und Erfahrung, Attributspunkte verteilen, Schwellenboni des gewählten Attributs.

var player = null
var selected := "strength" # Attribut, dessen Schwellen rechts angezeigt werden

var level_label: Label
var level_bar: ProgressBar
var points_label: Label
var attribute_box: VBoxContainer
var detail_title: Label
var detail_text: Label
var threshold_box: VBoxContainer
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
	panel.offset_left = -600
	panel.offset_right = 600
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
	header.add_child(_label("Charakter", 26, Color(1.0, 0.85, 0.5)))
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
	points_label = _label("", 17, Color(0.6, 1.0, 0.6))
	points_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(points_label)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	var reset := Button.new()
	reset.text = "Punkte zurücksetzen"
	reset.pressed.connect(func() -> void:
		player.reset_attributes()
		status_label.text = ""
		_refresh.call_deferred())
	header.add_child(reset)

	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 28)
	root.add_child(body)
	attribute_box = VBoxContainer.new()
	attribute_box.custom_minimum_size = Vector2(470, 0)
	attribute_box.add_theme_constant_override("separation", 10)
	body.add_child(attribute_box)

	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_theme_constant_override("separation", 6)
	body.add_child(right)
	detail_title = _label("", 20, Color(1.0, 0.85, 0.5))
	right.add_child(detail_title)
	detail_text = _label("", 13, Color(0.75, 0.75, 0.75))
	detail_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(detail_text)
	threshold_box = VBoxContainer.new()
	threshold_box.add_theme_constant_override("separation", 3)
	right.add_child(threshold_box)

	status_label = _label("", 14, Color(1.0, 0.85, 0.5))
	root.add_child(status_label)
	root.add_child(_label("+ : 1 Punkt   ·   +5 : fünf Punkte   ·   Klick auf ein Attribut: Schwellen anzeigen   ·   P / Esc: schließen",
		12, Color(0.6, 0.6, 0.6)))


func open(p) -> void:
	if player != p:
		player = p
		player.equipment_changed.connect(_on_player_changed, CONNECT_DEFERRED)
	status_label.text = ""
	visible = true
	_refresh()


func close() -> void:
	visible = false


func _on_player_changed() -> void:
	if visible:
		_refresh()


func _refresh() -> void:
	var level: int = player.char_level
	if level >= Game.MAX_CHAR_LEVEL:
		level_label.text = "Level %d (max.)" % level
		level_bar.value = 1.0
	else:
		level_label.text = "Level %d   (%d / %d EP)" % [level, player.char_xp, Game.char_xp_to_next(level)]
		level_bar.value = float(player.char_xp) / Game.char_xp_to_next(level)
	points_label.text = "Freie Punkte: %d" % player.attribute_points_free()

	for child in attribute_box.get_children():
		attribute_box.remove_child(child)
		child.queue_free()
	for id in Game.attribute_ids():
		attribute_box.add_child(_make_attribute_row(id))
	_show_thresholds()


func _make_attribute_row(id: String) -> Control:
	var def := Game.attribute_def(id)
	var value: int = player.attribute_value(id)
	var c: Array = def.get("color", [1, 1, 1])
	var color := Color(float(c[0]), float(c[1]), float(c[2]))
	var row := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.14, 0.14, 0.17) if id != selected else Color(0.2, 0.18, 0.13)
	style.border_color = color if id == selected else Color(0.25, 0.25, 0.28)
	style.set_border_width_all(2)
	style.set_corner_radius_all(5)
	style.set_content_margin_all(8)
	row.add_theme_stylebox_override("panel", style)
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 10)
	row.add_child(line)

	var name_button := Button.new()
	name_button.flat = true
	name_button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	name_button.custom_minimum_size = Vector2(190, 0)
	name_button.text = String(def.get("name", id))
	name_button.add_theme_font_size_override("font_size", 18)
	name_button.add_theme_color_override("font_color", color)
	name_button.add_theme_color_override("font_hover_color", color.lightened(0.3))
	name_button.tooltip_text = String(def.get("per_point_text", ""))
	name_button.pressed.connect(func() -> void:
		selected = id
		_refresh.call_deferred())
	line.add_child(name_button)

	var value_label := _label(str(value), 20, Color.WHITE)
	value_label.custom_minimum_size = Vector2(46, 0)
	value_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	line.add_child(value_label)
	var next := _next_threshold(def, value)
	var next_label := _label("nächste Schwelle %d" % next if next > 0 else "alle Schwellen", 12, Color(0.6, 0.6, 0.6))
	next_label.custom_minimum_size = Vector2(130, 0)
	next_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	line.add_child(next_label)

	for amount in [1, 5]:
		var plus := Button.new()
		plus.text = "+" if amount == 1 else "+5"
		plus.custom_minimum_size = Vector2(42, 0)
		plus.disabled = player.attribute_points_free() <= 0
		plus.pressed.connect(func() -> void:
			status_label.text = player.add_attribute_points(id, amount)
			selected = id
			_refresh.call_deferred()) # verzögert, weil _refresh diesen Button entfernt
		line.add_child(plus)
	return row


func _next_threshold(def: Dictionary, value: int) -> int:
	for t in def.get("thresholds", []):
		if int(t["at"]) > value:
			return int(t["at"])
	return 0


func _show_thresholds() -> void:
	var def := Game.attribute_def(selected)
	var value: int = player.attribute_value(selected)
	detail_title.text = "%s  %d" % [def.get("name", selected), value]
	detail_text.text = "Je Punkt: %s\nBeruf: %s" % [def.get("per_point_text", ""),
		Game.profession_name(String(def.get("profession", "")))]
	for child in threshold_box.get_children():
		threshold_box.remove_child(child)
		child.queue_free()
	var next := _next_threshold(def, value)
	for t in def.get("thresholds", []):
		var threshold: Dictionary = t
		var at := int(threshold["at"])
		var text := "%3d   " % at
		if threshold.has("name"):
			text += String(threshold["name"]) + ": "
		text += String(threshold["text"])
		if threshold.has("ab"):
			text += "   (wirkt ab: %s)" % threshold["ab"]
		elif threshold.has("ab_teilweise"):
			text += "   (%s)" % threshold["ab_teilweise"]
		var color := Color(0.45, 0.45, 0.45)
		if value >= at:
			color = Color(0.55, 0.95, 0.55) if not threshold.has("ab") else Color(0.6, 0.7, 0.6)
		elif at == next:
			color = Color.WHITE
		var label := _label(text, 14 if threshold.has("name") else 13, color)
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		threshold_box.add_child(label)


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
