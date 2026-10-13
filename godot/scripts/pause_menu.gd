extends Control
## Pausenmenü (Esc): Fortsetzen, Speichern, Neues Spiel, Beenden. Das Spiel steht still, solange es offen ist.

const SaveGame := preload("res://scripts/save_game.gd")

signal resume_requested

var status_label: Label
var new_game_button: Button
var confirm_new_game := false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false

	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.55)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)

	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = -190
	panel.offset_right = 190
	panel.offset_top = -210
	panel.offset_bottom = 210
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.96)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(24)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	panel.add_child(box)
	var title := Label.new()
	title.text = "Pause"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 30)
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.5))
	box.add_child(title)

	box.add_child(_button("Fortsetzen", func() -> void: resume_requested.emit()))
	box.add_child(_button("Speichern", _on_save))
	new_game_button = _button("Neues Spiel", _on_new_game)
	box.add_child(new_game_button)
	box.add_child(_button("Speichern & Beenden", _on_quit))

	status_label = Label.new()
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status_label.add_theme_font_size_override("font_size", 13)
	status_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	box.add_child(status_label)


func open() -> void:
	confirm_new_game = false
	new_game_button.text = "Neues Spiel"
	_update_status()
	visible = true


func close() -> void:
	visible = false


func _button(text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 46)
	b.add_theme_font_size_override("font_size", 18)
	b.pressed.connect(action)
	return b


func _update_status(extra := "") -> void:
	var when := SaveGame.saved_at(Game.SAVE_PATH)
	var text := "Zuletzt gespeichert: %s" % when if when != "" else "Noch kein Spielstand"
	if not Game.saving_enabled:
		text = "Speichern ist im Testmodus aus"
	status_label.text = text if extra == "" else extra + "\n" + text


func _on_save() -> void:
	if not Game.saving_enabled:
		_update_status()
		return
	var ok := SaveGame.save(get_tree(), Game.SAVE_PATH)
	_update_status("Gespeichert!" if ok else "Speichern fehlgeschlagen")


func _on_new_game() -> void:
	# Zweiter Klick zur Bestätigung, damit man den Spielstand nicht aus Versehen löscht
	if not confirm_new_game:
		confirm_new_game = true
		new_game_button.text = "Wirklich? Fortschritt geht verloren!"
		return
	if Game.saving_enabled:
		SaveGame.delete(Game.SAVE_PATH)
	get_tree().paused = false
	get_tree().reload_current_scene()


func _on_quit() -> void:
	if Game.saving_enabled:
		SaveGame.save(get_tree(), Game.SAVE_PATH)
	get_tree().quit()
