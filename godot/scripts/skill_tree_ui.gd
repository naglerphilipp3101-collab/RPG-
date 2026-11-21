extends Control
## Skillbaum-Fenster (K) wie in New World: zwei Seiten pro Waffe. Fähigkeiten sind Sechsecke mit Bild,
## ihre Verbesserungen und die kleinen Passiven Kreise, die große Passive ein großer Kreis mit Bild, die Ultimative unten.
## Punkte aus der Waffenmeisterschaft; 3 Fähigkeiten auf Q/E/R, eine Ultimative auf X, eine große Passive aktiv.
## Rechts eine Übersicht aller Meisterschaften.

const ZELLE := Vector2(120, 78) # Abstand der Rasterpunkte
const RAND := Vector2(52, 62) # Lage von Spalte 0 / Zeile 0 in einer Seite
const RADIUS := {"active": 29.0, "passive": 31.0, "ultimate": 34.0, "upgrade": 13.0, "minor": 13.0}
const GOLD := Color(1.0, 0.82, 0.4)

var player = null
var view_type := "" # angezeigter Waffentyp (Standard: aktive Waffe)

var title_label: Label
var role_label: Label
var level_label: Label
var level_bar: ProgressBar
var points_label: Label
var trees: Array[Control] = [] # je Seite eine Zeichenfläche mit den Knoten
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
	panel.offset_top = -340
	panel.offset_bottom = 340
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
		var tree := Control.new()
		tree.custom_minimum_size = Vector2(RAND.x * 2 + ZELLE.x * 3, RAND.y + ZELLE.y * 5 + 44)
		tree.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		tree.draw.connect(_draw_lines.bind(tree))
		body.add_child(tree)
		trees.append(tree)

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
	root.add_child(_label("Klick: freischalten (1 Punkt)   ·   Klick auf Freigeschaltetes: Fähigkeit auf Q / E / R legen oder entfernen, "
		+ "große Passive aktivieren, Ultimative auf X legen\nGroße Passive ab %d Punkten in der Seite, untere Fähigkeiten ab %d, Ultimative ab %d   ·   K / Esc: schließen"
		% [Game.TREE_POINTS_PASSIVE, Game.TREE_POINTS_LOWER, Game.TREE_POINTS_ULTIMATE], 12, Color(0.6, 0.6, 0.6)))


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
	for i in trees.size():
		var tree := trees[i]
		for child in tree.get_children():
			tree.remove_child(child)
			child.queue_free()
		tree.set_meta("nodes", [])
		if i >= sides.size():
			continue
		var head := _label("%s   ·   %d Punkte" % [sides[i]["name"], player.side_points(view_type, i)], 20, Color(1.0, 0.85, 0.5))
		head.position = Vector2(8, 0)
		tree.add_child(head)
		tree.set_meta("nodes", sides[i]["nodes"])
		for node in sides[i]["nodes"]:
			tree.add_child(_make_knot(node, m))
		tree.queue_redraw()
	_refresh_masteries()


func _knot_pos(node: Dictionary) -> Vector2:
	var pos: Vector2 = node.get("pos", Vector2.ZERO)
	return RAND + pos * ZELLE


## Verbindungslinien: golden, wenn beide Enden freigeschaltet sind.
func _draw_lines(tree: Control) -> void:
	if player == null:
		return
	if tree == trees[0]: # Trennlinie zwischen den beiden Seiten
		tree.draw_line(Vector2(tree.size.x + 2, 36), Vector2(tree.size.x + 2, tree.size.y - 10), Color(0.75, 0.62, 0.35, 0.35), 1.0)
	var m: Dictionary = player._mastery(view_type)
	for node in tree.get_meta("nodes", []):
		var req: String = node.get("req", "")
		if req == "":
			continue
		var from := Game.tree_node(view_type, req)
		var lit: bool = m["unlocked"].has(req) and m["unlocked"].has(node["id"])
		var a := _knot_pos(from)
		var b := _knot_pos(node)
		var dir := (b - a).normalized()
		a += dir * float(RADIUS.get(from.get("type", ""), 13.0))
		b -= dir * float(RADIUS.get(node.get("type", ""), 13.0))
		tree.draw_line(a, b, GOLD if lit else Color(0.35, 0.33, 0.3), 3.0 if lit else 2.0, true)


func _make_knot(node: Dictionary, m: Dictionary) -> Control:
	var node_id: String = node["id"]
	var kind: String = node.get("type", "active")
	var unlocked: bool = m["unlocked"].has(node_id)
	var error: String = player.unlock_check(view_type, node_id)
	var knot := Knoten.new()
	knot.node = node
	knot.kind = kind
	knot.radius = float(RADIUS.get(kind, 13.0))
	knot.state = "unlocked" if unlocked else ("available" if error == "" else "locked")
	match kind:
		"passive":
			knot.badge = "aktiv" if m["passive"] == node_id else ""
		"ultimate":
			knot.badge = Game.ULTIMATE_KEY if m["ultimate"] == node_id else ""
		"active":
			var index: int = m["equipped"].find(node_id)
			knot.badge = Game.SKILL_KEYS[index] if index >= 0 else ""
	knot.size = Vector2.ONE * (knot.radius * 2.0 + 8.0)
	knot.position = _knot_pos(node) - knot.size / 2.0
	var hint := error
	if unlocked:
		match kind:
			"passive": hint = "Klick: diese große Passive aktivieren (nur eine wirkt)"
			"ultimate": hint = "Klick: als Ultimative auf %s legen (nur eine wirkt)" % Game.ULTIMATE_KEY
			"active": hint = "Klick: auf Q/E/R legen oder entfernen"
			_: hint = "Freigeschaltet, wirkt immer"
	elif error == "":
		hint = "Klick: freischalten (1 Punkt)"
	knot.tooltip_text = Game.describe_node(node) + "\n\n" + hint
	knot.clicked.connect(func() -> void:
		var result := ""
		if unlocked:
			result = player.toggle_skill(view_type, node_id)
		else:
			result = player.unlock_node(view_type, node_id)
		status_label.text = result
		_refresh.call_deferred()) # verzögert, weil _refresh diesen Knoten entfernt
	return knot


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


## Ein Knoten im Baum: Sechseck (Fähigkeit), großer Kreis (große Passive), Achteck (Ultimative), kleiner Kreis (Rest).
class Knoten extends Control:
	signal clicked
	var node: Dictionary
	var kind := ""
	var radius := 13.0
	var state := "locked" # locked / available / unlocked
	var badge := "" # Q/E/R, X oder "aktiv"
	var hover := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		mouse_entered.connect(func() -> void:
			hover = true
			queue_redraw())
		mouse_exited.connect(func() -> void:
			hover = false
			queue_redraw())

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			clicked.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return point.distance_to(size / 2.0) <= radius + 3.0

	func _draw() -> void:
		var c := size / 2.0
		var fill := Color(0.11, 0.11, 0.12)
		var rim := Color(0.33, 0.32, 0.3)
		var icon := Color(0.42, 0.41, 0.4)
		match state:
			"available":
				fill = Color(0.17, 0.16, 0.15)
				rim = Color(0.92, 0.9, 0.85)
				icon = Color(0.85, 0.83, 0.78)
			"unlocked":
				fill = Color(0.36, 0.26, 0.1)
				rim = GOLD
				icon = Color(1.0, 0.95, 0.85)
		if hover:
			rim = rim.lightened(0.3)
		var width := 3.0 if badge != "" else 2.0
		var shape := _shape(c)
		if badge != "": # ausgerüstet/aktiv: leuchtender Rand
			draw_colored_polygon(_shape(c, 5.0), Color(GOLD, 0.35))
		if shape.is_empty():
			draw_circle(c, radius, fill)
			draw_arc(c, radius, 0, TAU, 32, rim, width, true)
			if kind == "passive":
				draw_arc(c, radius - 5.0, 0, TAU, 32, Color(rim, 0.5), 1.5, true)
		else:
			draw_colored_polygon(shape, fill)
			shape.append(shape[0])
			draw_polyline(shape, rim, width, true)
		if kind in ["active", "passive", "ultimate"]:
			SkillIcons.zeichnen(self, node, c, radius * 0.55, icon)
		elif state == "unlocked":
			draw_circle(c, radius * 0.4, GOLD)
		if badge != "":
			var font := get_theme_default_font()
			var text_size := font.get_string_size(badge, HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
			var box := Rect2(c + Vector2(radius * 0.55, radius * 0.45), text_size + Vector2(8, 2))
			draw_rect(box, Color(0.08, 0.07, 0.05))
			draw_rect(box, GOLD, false, 1.0)
			draw_string(font, box.position + Vector2(4, text_size.y - 2), badge, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, GOLD)

	## Umriss: Sechseck für Fähigkeiten, Achteck für die Ultimative, sonst leer (= Kreis).
	func _shape(c: Vector2, grow := 0.0) -> PackedVector2Array:
		var ecken: int = {"active": 6, "ultimate": 8}.get(kind, 0)
		var points := PackedVector2Array()
		if ecken == 0:
			for i in 32:
				points.append(c + Vector2.from_angle(TAU * i / 32.0) * (radius + grow))
			return points if grow > 0.0 else PackedVector2Array()
		for i in ecken:
			var a := TAU * i / float(ecken) + (PI / float(ecken) if ecken == 8 else 0.0)
			points.append(c + Vector2.from_angle(a) * (radius + grow))
		return points
