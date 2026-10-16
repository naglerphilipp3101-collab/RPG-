extends Control
## Fehler melden (F9): hält das Spiel an, macht ein Bildschirmfoto und fragt nach einem Kommentar.
## Gespeichert wird in user://fehler/ (Windows: %APPDATA%\Godot\app_userdata\RPG\fehler\):
##   fehler.json – Liste aller Meldungen (Nummer, Zeit, Welt, Position, Blickrichtung, Biom, Kommentar)
##   fehler_001.jpg … – Bildschirmfoto zur Meldung
## Enter speichert, Esc bricht ab. Mit `-- --fehler <nr>` startet das Spiel an der Stelle einer Meldung.

const ORDNER := "user://fehler"
const LISTE := "user://fehler/fehler.json"

signal geschlossen

var player = null
var main_node = null
var eingabe: LineEdit
var info: Label
var vorschau: TextureRect
var _bild: Image
var _eintrag := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	process_mode = Node.PROCESS_MODE_ALWAYS
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
	panel.offset_left = -330
	panel.offset_right = 330
	panel.offset_top = -220
	panel.offset_bottom = 200
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.96)
	style.border_color = Color(0.85, 0.4, 0.3)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(20)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)
	var titel := Label.new()
	titel.text = "Fehler melden"
	titel.add_theme_font_size_override("font_size", 24)
	titel.add_theme_color_override("font_color", Color(1.0, 0.7, 0.55))
	box.add_child(titel)

	vorschau = TextureRect.new()
	vorschau.custom_minimum_size = Vector2(620, 250)
	vorschau.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vorschau.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	box.add_child(vorschau)

	info = Label.new()
	info.add_theme_font_size_override("font_size", 13)
	info.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	box.add_child(info)

	eingabe = LineEdit.new()
	eingabe.placeholder_text = "Was ist hier falsch? (z. B. Gras schwebt über dem Bach)"
	eingabe.custom_minimum_size = Vector2(0, 40)
	eingabe.text_submitted.connect(func(_t: String) -> void: speichern())
	box.add_child(eingabe)

	var knoepfe := HBoxContainer.new()
	knoepfe.add_theme_constant_override("separation", 10)
	knoepfe.alignment = BoxContainer.ALIGNMENT_END
	box.add_child(knoepfe)
	var abbrechen := Button.new()
	abbrechen.text = "Abbrechen (Esc)"
	abbrechen.pressed.connect(schliessen)
	knoepfe.add_child(abbrechen)
	var ok := Button.new()
	ok.text = "Speichern (Enter)"
	ok.pressed.connect(speichern)
	knoepfe.add_child(ok)


## Bildschirmfoto vom letzten Bild nehmen (vor dem Öffnen, damit das Fenster nicht mit drauf ist) und Ort festhalten
func oeffnen() -> void:
	var tex := get_viewport().get_texture()
	_bild = tex.get_image() if tex and DisplayServer.get_name() != "headless" else null
	if _bild and _bild.is_empty():
		_bild = null
	vorschau.texture = ImageTexture.create_from_image(_bild) if _bild else null
	var p: Vector3 = player.global_position
	var biom := ""
	if main_node and main_node.get("natur") != null:
		biom = main_node.natur.biom_name(p.x, p.z)
	_eintrag = {
		"nr": _liste().size() + 1,
		"zeit": Time.get_datetime_string_from_system(false, true),
		"welt": Game.world_id,
		"position": [snappedf(p.x, 0.01), snappedf(p.y, 0.01), snappedf(p.z, 0.01)],
		"kamera": [snappedf(player.cam_yaw, 0.001), snappedf(player.cam_pitch, 0.001)],
		"flug": player.debug_fly,
		"biom": biom,
		"uhrzeit": snappedf(Game.time_of_day, 0.01),
	}
	info.text = "Nr. %d   Position %.1f / %.1f / %.1f   %s" % [_eintrag["nr"], p.x, p.y, p.z,
		("Biom " + biom) if biom != "" else Game.world_id]
	eingabe.text = ""
	visible = true
	eingabe.grab_focus()


func schliessen() -> void:
	visible = false
	eingabe.release_focus()
	geschlossen.emit()


func speichern() -> void:
	if not visible:
		return
	DirAccess.make_dir_recursive_absolute(ORDNER)
	var nr: int = _eintrag["nr"]
	var bild_datei := "fehler_%03d.jpg" % nr
	_eintrag["kommentar"] = eingabe.text.strip_edges()
	_eintrag["bild"] = bild_datei
	if _bild:
		_bild.save_jpg(ORDNER.path_join(bild_datei), 0.85)
	var liste := _liste()
	liste.append(_eintrag)
	var f := FileAccess.open(LISTE, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(liste, "\t"))
		f.close()
	if player:
		player.notify.emit("Fehler %d gespeichert" % nr, Color(1.0, 0.7, 0.55))
	schliessen()


func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		schliessen()
		get_viewport().set_input_as_handled()


static func _liste() -> Array:
	if not FileAccess.file_exists(LISTE):
		return []
	var daten = JSON.parse_string(FileAccess.get_file_as_string(LISTE))
	return daten if daten is Array else []


## Spieler an die Stelle einer Meldung setzen (Startschalter --fehler <nr>)
static func hinspringen(spieler, nr: int) -> bool:
	for e in _liste():
		if int(e.get("nr", 0)) == nr:
			var p: Array = e["position"]
			spieler.global_position = Vector3(float(p[0]), float(p[1]), float(p[2]))
			spieler.velocity = Vector3.ZERO
			var k: Array = e.get("kamera", [0.0, 0.0])
			spieler.cam_yaw = float(k[0])
			spieler.cam_pitch = float(k[1])
			if bool(e.get("flug", false)):
				spieler.set_debug_fly(true)
			if e.has("uhrzeit"):
				Game.time_of_day = float(e["uhrzeit"])
			return true
	return false
