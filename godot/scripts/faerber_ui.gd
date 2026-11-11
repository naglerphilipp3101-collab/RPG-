extends Control
## Färber (Philipp, 11.11.): Hauptfläche und Akzente jedes Moduls einer Waffe oder eines Schilds jederzeit umfärben.
## Glanz, Rauheit und Kratzer bleiben, nur die Farbe ändert sich. Bis zu 20 Farben lassen sich speichern (player.farbpalette).
## Die Farben stehen am Gegenstand unter gear["module"][platz]["farbe"|"akzent"] als "#rrggbb".
const WeaponModels := preload("res://scripts/weapon_models.gd")
const MAX_FARBEN := 20

var player = null
var liste: VBoxContainer
var titel: Label
var zeilen: VBoxContainer
var palette: HFlowContainer
var vorschau: SubViewport
var halter: Node3D
var auswahl: Dictionary = {} # der Gegenstand, der gerade gefärbt wird
var zuletzt := "" # zuletzt gewählte Farbe, für "Farbe speichern"


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
	var kopf := HBoxContainer.new()
	root.add_child(kopf)
	kopf.add_child(_label("Färber", 26, Color(1.0, 0.85, 0.5)))
	var platz := Control.new()
	platz.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	kopf.add_child(platz)
	kopf.add_child(_label("Esc: schließen", 13, Color(0.6, 0.6, 0.6)))

	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 24)
	root.add_child(body)

	var links := VBoxContainer.new()
	links.custom_minimum_size = Vector2(300, 0)
	body.add_child(links)
	links.add_child(_label("Waffen und Schilde", 17, Color(1.0, 0.85, 0.5)))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	links.add_child(scroll)
	liste = VBoxContainer.new()
	liste.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(liste)

	var mitte := VBoxContainer.new()
	mitte.add_theme_constant_override("separation", 8)
	body.add_child(mitte)
	titel = _label("", 22, Color.WHITE)
	mitte.add_child(titel)
	var container := SubViewportContainer.new()
	container.custom_minimum_size = Vector2(360, 360)
	container.stretch = true
	mitte.add_child(container)
	vorschau = SubViewport.new()
	vorschau.own_world_3d = true
	container.add_child(vorschau)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.13, 0.13, 0.16)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.6, 0.65)
	# Himmel nur für Spiegelungen, sonst wirkt Metall vor dem dunklen Hintergrund schwarz
	var himmel := ProceduralSkyMaterial.new()
	himmel.sky_top_color = Color(0.55, 0.6, 0.7)
	himmel.sky_horizon_color = Color(0.8, 0.8, 0.82)
	himmel.ground_bottom_color = Color(0.2, 0.18, 0.16)
	himmel.ground_horizon_color = Color(0.5, 0.48, 0.45)
	env.environment.sky = Sky.new()
	env.environment.sky.sky_material = himmel
	env.environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	vorschau.add_child(env)
	for r in [Vector3(-50, -30, 0), Vector3(-20, 150, 0)]:
		var licht := DirectionalLight3D.new()
		licht.rotation_degrees = r
		vorschau.add_child(licht)
	var cam := Camera3D.new()
	cam.name = "Kamera"
	cam.fov = 35
	vorschau.add_child(cam)
	halter = Node3D.new()
	vorschau.add_child(halter)
	mitte.add_child(_label("Färbbar sind Hauptfläche und Akzente. Griff, Knauf, Beschläge, Leder und Holz\nbehalten die Farbe des Materials.", 13, Color(0.7, 0.7, 0.7)))

	var rechts := VBoxContainer.new()
	rechts.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rechts.add_theme_constant_override("separation", 8)
	body.add_child(rechts)
	rechts.add_child(_label("Farben je Modul", 17, Color(1.0, 0.85, 0.5)))
	zeilen = VBoxContainer.new()
	zeilen.add_theme_constant_override("separation", 6)
	rechts.add_child(zeilen)
	var abstand := Control.new()
	abstand.custom_minimum_size = Vector2(0, 10)
	rechts.add_child(abstand)
	var pkopf := HBoxContainer.new()
	rechts.add_child(pkopf)
	pkopf.add_child(_label("Gespeicherte Farben", 15, Color(1.0, 0.85, 0.5)))
	var speichern := Button.new()
	speichern.text = "Letzte Farbe speichern"
	speichern.pressed.connect(_farbe_speichern)
	pkopf.add_child(speichern)
	palette = HFlowContainer.new()
	palette.add_theme_constant_override("h_separation", 4)
	palette.add_theme_constant_override("v_separation", 4)
	rechts.add_child(palette)


func open(p) -> void:
	player = p
	visible = true
	auswahl = {}
	_liste_fuellen()


func close() -> void:
	visible = false


func _process(delta: float) -> void:
	if visible:
		halter.rotate_y(delta * 0.5)


## Angelegte Waffen und Schild zuerst, dann die Tasche.
func _gegenstaende() -> Array:
	var out: Array = []
	for key in ["weapon", "weapon2", "weapon3", "shield"]:
		if player.equipment.has(key):
			out.append(player.equipment[key])
	for g in player.inventory.gear:
		if not out.has(g):
			out.append(g)
	return out.filter(func(g: Dictionary) -> bool: return _waffe_von(g) != "")


func _waffe_von(gear: Dictionary) -> String:
	var def := Game.item(String(gear.get("id", "")))
	if def.get("slot", "") == "shield":
		return "schild"
	var type := String(def.get("weapon_type", ""))
	return WeaponModels.modular_name(Game.weapon_def(type)) if type != "" else ""


func _liste_fuellen() -> void:
	for c in liste.get_children():
		liste.remove_child(c)
		c.queue_free()
	var alle := _gegenstaende()
	if auswahl.is_empty() and not alle.is_empty():
		auswahl = alle[0]
	for g: Dictionary in alle:
		var b := Button.new()
		b.toggle_mode = true
		b.button_pressed = g == auswahl
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		var angelegt: bool = player.equipment.values().has(g)
		b.text = "  %s%s" % [Game.item_name(String(g["id"])), "   (angelegt)" if angelegt else ""]
		b.pressed.connect(func() -> void:
			auswahl = g
			_liste_fuellen.call_deferred())
		liste.add_child(b)
	_zeilen_fuellen()
	_palette_fuellen()


func _zeilen_fuellen() -> void:
	for c in zeilen.get_children():
		zeilen.remove_child(c)
		c.queue_free()
	if auswahl.is_empty():
		titel.text = "Keine Waffe in der Tasche"
		_vorschau()
		return
	titel.text = Game.item_name(String(auswahl["id"]))
	var waffe := _waffe_von(auswahl)
	for platz: String in WaffenModell.WAFFEN[waffe]:
		var def: Array = WaffenModell.WAFFEN[waffe][platz]
		var zeile := HBoxContainer.new()
		zeile.add_theme_constant_override("separation", 8)
		var name_label := _label(String(def[1]), 15, Color.WHITE)
		name_label.custom_minimum_size = Vector2(120, 0)
		zeile.add_child(name_label)
		for art in ["farbe", "akzent"]:
			zeile.add_child(_label("Haupt" if art == "farbe" else "Akzent", 13, Color(0.7, 0.7, 0.7)))
			var knopf := ColorPickerButton.new()
			knopf.custom_minimum_size = Vector2(44, 28)
			knopf.edit_alpha = false
			var wert = _modul(platz).get(art)
			knopf.color = Color.html(wert) if wert is String else Color(0.5, 0.5, 0.5)
			var picker := knopf.get_picker()
			picker.presets_visible = true
			for c in player.farbpalette:
				picker.add_preset(Color.html(c))
			knopf.color_changed.connect(func(c: Color) -> void: _setzen(platz, art, c))
			zeile.add_child(knopf)
		var zurueck := Button.new()
		zurueck.text = "Material"
		zurueck.tooltip_text = "Farbe des Materials wiederherstellen"
		zurueck.pressed.connect(func() -> void:
			_modul(platz).erase("farbe")
			_modul(platz).erase("akzent")
			_geaendert()
			_zeilen_fuellen.call_deferred())
		zeile.add_child(zurueck)
		zeilen.add_child(zeile)
	_vorschau()


## Moduleintrag des Platzes am Gegenstand (wird mit dem Standard angelegt, falls er noch fehlt).
func _modul(platz: String) -> Dictionary:
	if not auswahl.has("module"):
		auswahl["module"] = {}
	var module: Dictionary = auswahl["module"]
	if not module.has(platz):
		var tier := clampi(int(Game.item(String(auswahl["id"])).get("tier", 1)), 1, 6)
		module[platz] = {"tier": tier, "form": 1}
	return module[platz]


func _setzen(platz: String, art: String, c: Color) -> void:
	zuletzt = "#" + c.to_html(false)
	_modul(platz)[art] = zuletzt
	_geaendert()


func _geaendert() -> void:
	_vorschau()
	if player.equipment.values().has(auswahl):
		player._build_weapon_visual()


func _vorschau() -> void:
	for c in halter.get_children():
		halter.remove_child(c)
		c.queue_free()
	if auswahl.is_empty():
		return
	var waffe := _waffe_von(auswahl)
	var tier := clampi(int(Game.item(String(auswahl["id"])).get("tier", 1)), 1, 6)
	var teil := Node3D.new()
	halter.add_child(teil)
	var farbe: Variant = null
	if waffe != "schild":
		var def := Game.weapon_def(String(Game.item(String(auswahl["id"])).get("weapon_type", "")))
		if bool(def.get("magic", false)):
			farbe = Game.element_color(String(def.get("element", "")))
	WaffenModell.zusammenbauen(waffe, WeaponModels.auswahl(waffe, auswahl, tier), teil, tier, farbe)
	WeaponModels.vorschau_einpassen(teil, vorschau.get_node("Kamera") as Camera3D)


func _palette_fuellen() -> void:
	for c in palette.get_children():
		palette.remove_child(c)
		c.queue_free()
	for i in MAX_FARBEN:
		var feld := Button.new()
		feld.custom_minimum_size = Vector2(26, 26)
		var box := StyleBoxFlat.new()
		box.set_corner_radius_all(4)
		box.set_border_width_all(1)
		box.border_color = Color(0.4, 0.4, 0.45)
		if i < player.farbpalette.size():
			var hex: String = player.farbpalette[i]
			box.bg_color = Color.html(hex)
			feld.tooltip_text = "%s (Rechtsklick: entfernen)" % hex
			feld.gui_input.connect(func(e: InputEvent) -> void:
				if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_RIGHT:
					player.farbpalette.erase(hex)
					_liste_fuellen.call_deferred())
		else:
			box.bg_color = Color(0.12, 0.12, 0.14)
			feld.disabled = true
		for s in ["normal", "hover", "pressed", "disabled"]:
			feld.add_theme_stylebox_override(s, box)
		palette.add_child(feld)


func _farbe_speichern() -> void:
	if zuletzt == "" or player.farbpalette.has(zuletzt) or player.farbpalette.size() >= MAX_FARBEN:
		return
	player.farbpalette.append(zuletzt)
	_liste_fuellen()


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
