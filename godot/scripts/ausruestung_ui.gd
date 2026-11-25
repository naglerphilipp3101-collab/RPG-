extends Control
## Ausrüstungsschrank (Philipp, 25.11.): ein Knopf je Waffe legt die Waffe der Stufe 1 an, dazu passende
## Ausrüstung (Schild, wo die Waffe einen erlaubt, und die Lederrüstung der Stufe 1). Die Meisterschaft der Waffe
## springt auf die höchste Stufe, damit sich im Skillbaum (K) alle Fähigkeiten freischalten und ansehen lassen.
## Gedacht zum Ausprobieren der Animationen; die alte Waffe kommt in die Tasche.

const RUESTUNG := {"head": "leather_cap", "chest": "leather_jerkin", "legs": "leather_pants"}
const SCHILD := "wooden_shield"

signal werkstatt_gewuenscht

var player = null
var raster: GridContainer
var hinweis: Label


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
	panel.offset_left = -430
	panel.offset_right = 430
	panel.offset_top = -230
	panel.offset_bottom = 230
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.96)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(20)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 14)
	panel.add_child(root)
	var kopf := HBoxContainer.new()
	root.add_child(kopf)
	kopf.add_child(_label("Ausrüstungsschrank", 26, Color(1.0, 0.85, 0.5)))
	var platz := Control.new()
	platz.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	kopf.add_child(platz)
	kopf.add_child(_label("Esc: schließen", 13, Color(0.6, 0.6, 0.6)))
	var text := _label("Waffe der Stufe 1 und passende Ausrüstung anlegen. Die Meisterschaft geht auf die höchste Stufe (Skillbaum mit K).",
		14, Color(0.8, 0.8, 0.8))
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.custom_minimum_size.x = 800
	root.add_child(text)

	raster = GridContainer.new()
	raster.columns = 3
	raster.add_theme_constant_override("h_separation", 10)
	raster.add_theme_constant_override("v_separation", 10)
	root.add_child(raster)
	for typ in Game.weapons:
		var knopf := Button.new()
		knopf.text = String(Game.weapons[typ].get("name", typ))
		knopf.custom_minimum_size = Vector2(260, 44)
		knopf.add_theme_font_size_override("font_size", 17)
		knopf.pressed.connect(_waehlen.bind(typ))
		raster.add_child(knopf)

	hinweis = _label("", 15, Color(0.6, 0.9, 0.6))
	root.add_child(hinweis)
	var werkstatt := Button.new()
	werkstatt.text = "Animations-Werkstatt: Griffe und Animationen der angelegten Waffe einstellen"
	werkstatt.custom_minimum_size = Vector2(0, 44)
	werkstatt.add_theme_font_size_override("font_size", 17)
	werkstatt.pressed.connect(func() -> void: werkstatt_gewuenscht.emit())
	root.add_child(werkstatt)


func open(p) -> void:
	player = p
	hinweis.text = ""
	visible = true


func close() -> void:
	visible = false


func _waehlen(typ: String) -> void:
	if player == null:
		return
	var name: String = player.ausruestung_anlegen(typ)
	hinweis.text = "Angelegt: " + name if name != "" else "Für diese Waffe gibt es keine Stufe 1."


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
