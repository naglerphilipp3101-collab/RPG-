extends Control
## Charaktererstellung: Mensch in einer eigenen 3D-Vorschau, Regler je Gruppe, Farben,
## Frisur und Bart, Zufall in festen Grenzen und "Als NPC speichern".
## Signal fertig(aussehen) beim Bestätigen, abgebrochen() beim Abbrechen.

signal fertig(aussehen: Dictionary)
signal abgebrochen

const GRUPPEN := ["Körper", "Kopf", "Augen", "Nase", "Mund", "Kinn und Wangen", "Ohren", "Haare und Farben"]
const GOLD := Color(1.0, 0.85, 0.5)

var aussehen: Dictionary
var abbrechen_erlaubt := true
var rng := RandomNumberGenerator.new()

var mensch: Mensch
var _vorschau: SubViewport
var _kamera: Camera3D
var _drehpunkt: Node3D
var _gier := 0.0
var _zoom := 0.0          # 0 = ganzer Körper, 1 = Gesicht
var _ziehen := false
var _neu_bauen := false
var _seit_bau := 0.0

var _gruppen_knoepfe := {}
var _regler_box: VBoxContainer
var _gruppe := "Körper"
var _info: Label
var _npc_name: LineEdit
var _geschlecht_knoepfe := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	process_mode = Node.PROCESS_MODE_ALWAYS
	rng.randomize()
	if aussehen.is_empty():
		aussehen = CharakterAussehen.standard()
	_vorschau_bauen()
	_oberflaeche_bauen()
	_gruppe_zeigen("Körper")


func _process(delta: float) -> void:
	_seit_bau += delta
	if _neu_bauen and _seit_bau > 0.06:
		_neu_bauen = false
		_seit_bau = 0.0
		mensch.aussehen_setzen(aussehen)
		_info_aktualisieren()
	_drehpunkt.rotation.y = lerp_angle(_drehpunkt.rotation.y, _gier, minf(1.0, delta * 12.0))
	var kopf_hoehe := 1.62
	if mensch and mensch.skelett:
		var k := mensch.skelett.find_bone("Head")
		if k >= 0:
			kopf_hoehe = mensch.skelett.get_bone_global_rest(k).origin.y + 0.1
	var ziel := Vector3(0, lerpf(0.95, kopf_hoehe, _zoom), 0)
	var abstand := lerpf(3.6, 0.75, _zoom)
	var soll := ziel + Vector3(0, lerpf(0.15, 0.02, _zoom), abstand)
	_kamera.position = _kamera.position.lerp(soll, minf(1.0, delta * 10.0))
	_kamera.look_at(ziel)


# ------------------------------------------------------------------ 3D-Vorschau
func _vorschau_bauen() -> void:
	var container := SubViewportContainer.new()
	container.stretch = true
	container.anchor_left = 0.36
	container.anchor_right = 1.0
	container.anchor_bottom = 1.0
	container.offset_bottom = -70
	container.mouse_filter = Control.MOUSE_FILTER_STOP
	container.gui_input.connect(_vorschau_eingabe)
	add_child(container)
	_vorschau = SubViewport.new()
	_vorschau.own_world_3d = true
	_vorschau.msaa_3d = Viewport.MSAA_4X
	container.add_child(_vorschau)
	var umgebung := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.11, 0.115, 0.13)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.64, 0.7)
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	umgebung.environment = env
	_vorschau.add_child(umgebung)
	for r in [[Vector3(-30, -35, 0), 1.0, true], [Vector3(-15, 140, 0), 0.5, false], [Vector3(25, 70, 0), 0.25, false]]:
		var licht := DirectionalLight3D.new()
		licht.rotation_degrees = r[0]
		licht.light_energy = r[1]
		licht.shadow_enabled = r[2]
		_vorschau.add_child(licht)
	var boden := MeshInstance3D.new()
	var scheibe := CylinderMesh.new()
	scheibe.top_radius = 0.8
	scheibe.bottom_radius = 0.8
	scheibe.height = 0.04
	boden.mesh = scheibe
	boden.position.y = -0.02
	var bmat := StandardMaterial3D.new()
	bmat.albedo_color = Color(0.2, 0.19, 0.18)
	bmat.roughness = 0.9
	boden.material_override = bmat
	_vorschau.add_child(boden)
	_drehpunkt = Node3D.new()
	_vorschau.add_child(_drehpunkt)
	mensch = Mensch.new()
	mensch.aussehen = aussehen
	_drehpunkt.add_child(mensch)
	mensch.ruhe_a_pose(true)
	_kamera = Camera3D.new()
	_kamera.fov = 32
	_kamera.position = Vector3(0, 1.1, 3.6)
	_vorschau.add_child(_kamera)


func _vorschau_eingabe(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		if e.button_index == MOUSE_BUTTON_LEFT or e.button_index == MOUSE_BUTTON_RIGHT:
			_ziehen = e.pressed
		elif e.button_index == MOUSE_BUTTON_WHEEL_UP and e.pressed:
			_zoom = clampf(_zoom + 0.12, 0.0, 1.0)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN and e.pressed:
			_zoom = clampf(_zoom - 0.12, 0.0, 1.0)
	elif e is InputEventMouseMotion and _ziehen:
		_gier += e.relative.x * 0.012


# ------------------------------------------------------------------ Oberfläche
func _oberflaeche_bauen() -> void:
	var hintergrund := ColorRect.new()
	hintergrund.color = Color(0.07, 0.07, 0.085)
	hintergrund.anchor_right = 0.36
	hintergrund.anchor_bottom = 1.0
	add_child(hintergrund)
	move_child(hintergrund, 0)

	var links := VBoxContainer.new()
	links.anchor_right = 0.36
	links.anchor_bottom = 1.0
	links.offset_left = 18
	links.offset_right = -12
	links.offset_top = 14
	links.offset_bottom = -80
	links.add_theme_constant_override("separation", 8)
	add_child(links)

	var titel := Label.new()
	titel.text = "Charaktererstellung"
	titel.add_theme_font_size_override("font_size", 28)
	titel.add_theme_color_override("font_color", GOLD)
	links.add_child(titel)

	var geschlecht := HBoxContainer.new()
	geschlecht.add_theme_constant_override("separation", 8)
	links.add_child(geschlecht)
	for g in [["Mann", 1.0], ["Frau", 0.0]]:
		var b := _knopf(g[0], _geschlecht_waehlen.bind(g[1]))
		b.toggle_mode = true
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		geschlecht.add_child(b)
		_geschlecht_knoepfe[g[1]] = b

	var gruppen := HFlowContainer.new()
	gruppen.add_theme_constant_override("h_separation", 4)
	gruppen.add_theme_constant_override("v_separation", 4)
	links.add_child(gruppen)
	for g in GRUPPEN:
		var b := _knopf(g, _gruppe_zeigen.bind(g))
		b.toggle_mode = true
		gruppen.add_child(b)
		_gruppen_knoepfe[g] = b

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	links.add_child(scroll)
	_regler_box = VBoxContainer.new()
	_regler_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_regler_box.add_theme_constant_override("separation", 2)
	scroll.add_child(_regler_box)

	_info = Label.new()
	_info.add_theme_color_override("font_color", Color(0.75, 0.75, 0.78))
	links.add_child(_info)

	# Untere Leiste
	var leiste := HBoxContainer.new()
	leiste.anchor_top = 1.0
	leiste.anchor_right = 1.0
	leiste.anchor_bottom = 1.0
	leiste.offset_top = -62
	leiste.offset_left = 18
	leiste.offset_right = -18
	leiste.offset_bottom = -14
	leiste.add_theme_constant_override("separation", 8)
	add_child(leiste)
	leiste.add_child(_knopf("Zufall", _zufall.bind(false)))
	leiste.add_child(_knopf("Nur Gesicht zufällig", _zufall.bind(true)))
	leiste.add_child(_knopf("Zurücksetzen", _zuruecksetzen))
	var luecke := Control.new()
	luecke.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	leiste.add_child(luecke)
	_npc_name = LineEdit.new()
	_npc_name.placeholder_text = "Name für NPC"
	_npc_name.custom_minimum_size.x = 170
	leiste.add_child(_npc_name)
	leiste.add_child(_knopf("Als NPC speichern", _als_npc))
	var luecke2 := Control.new()
	luecke2.custom_minimum_size.x = 24
	leiste.add_child(luecke2)
	if abbrechen_erlaubt:
		leiste.add_child(_knopf("Abbrechen", func() -> void: abgebrochen.emit()))
	var ok := _knopf("Fertig", func() -> void: fertig.emit(aussehen.duplicate(true)))
	ok.add_theme_color_override("font_color", GOLD)
	leiste.add_child(ok)

	var hinweis := Label.new()
	hinweis.text = "Ziehen: drehen   Mausrad: Gesicht / Körper"
	hinweis.add_theme_color_override("font_color", Color(0.6, 0.6, 0.65))
	hinweis.anchor_left = 0.36
	hinweis.offset_left = 16
	hinweis.offset_top = 12
	add_child(hinweis)
	_geschlecht_knoepfe_setzen()


func _knopf(text: String, aktion: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(aktion)
	return b


func _gruppe_zeigen(g: String) -> void:
	_gruppe = g
	for k in _gruppen_knoepfe:
		_gruppen_knoepfe[k].button_pressed = k == g
	for c in _regler_box.get_children():
		c.queue_free()
	_zoom = 0.0 if g == "Körper" else 1.0
	if g == "Haare und Farben":
		_farben_zeigen()
		return
	if g == "Körper":
		var frau := CharakterAussehen.ist_frau(aussehen)
		for r in CharakterAussehen.daten()["grundregler"]:
			if r["id"] == "geschlecht" or (r.get("nur", "") == "frau" and not frau):
				continue
			_regler(r["name"], float(aussehen.get(r["id"], r["standard"])), float(r["min"]), float(r["max"]),
				_grund_setzen.bind(r["id"]))
		var namen: Array = CharakterAussehen.daten()["herkunft"]["namen"]
		var herk: Array = aussehen.get("herkunft", [0.0, 0.0, 1.0])
		_ueberschrift("Gesichtszüge (Mischung)")
		for i in 3:
			_regler(namen[i], float(herk[i]), 0.0, 1.0, _herkunft_setzen.bind(i))
		_ueberschrift("Körperform")
	var regler: Dictionary = aussehen.get("regler", {})
	for r in MenschDaten.meta["regler"] if _daten_bereit() else []:
		if r["gruppe"] != g:
			continue
		_regler(r["name"], float(regler.get(r["id"], 0.0)), float(r["min"]), 1.0, _einzel_setzen.bind(r["id"]))


func _daten_bereit() -> bool:
	MenschDaten.laden()
	return true


func _ueberschrift(text: String) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", GOLD)
	_regler_box.add_child(l)


func _regler(name: String, wert: float, von: float, bis: float, setzen: Callable) -> void:
	var zeile := HBoxContainer.new()
	var l := Label.new()
	l.text = name
	l.custom_minimum_size.x = 170
	l.clip_text = true
	zeile.add_child(l)
	var s := HSlider.new()
	s.min_value = von
	s.max_value = bis
	s.step = 0.01
	s.value = wert
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	s.focus_mode = Control.FOCUS_NONE
	s.value_changed.connect(func(v: float) -> void:
		setzen.call(v)
		_neu_bauen = true)
	zeile.add_child(s)
	_regler_box.add_child(zeile)


func _farben_zeigen() -> void:
	var d := CharakterAussehen.daten()
	_ueberschrift("Hautfarbe")
	_farbfelder(d["hautfarben"], "haut")
	_ueberschrift("Augenfarbe")
	_farbfelder(d["augenfarben"], "augen")
	_ueberschrift("Haarfarbe")
	_farbfelder(d["haarfarben"], "haar_farbe")
	var mann := not CharakterAussehen.ist_frau(aussehen)
	_auswahl("Frisur", ["glatze"] + Mensch.frisuren(mann), "haar")
	if mann:
		_auswahl("Bart", ["keiner"] + Mensch.baerte(), "bart")


func _farbfelder(liste: Array, schluessel: String) -> void:
	var fluss := HFlowContainer.new()
	fluss.add_theme_constant_override("h_separation", 4)
	fluss.add_theme_constant_override("v_separation", 4)
	for e in liste:
		var b := Button.new()
		b.custom_minimum_size = Vector2(34, 34)
		b.tooltip_text = e["name"]
		b.focus_mode = Control.FOCUS_NONE
		var st := StyleBoxFlat.new()
		st.bg_color = Color.html(e["farbe"])
		st.set_corner_radius_all(4)
		var gewaehlt: bool = String(aussehen.get(schluessel, "")).to_lower() == String(e["farbe"]).to_lower()
		st.border_color = GOLD if gewaehlt else Color(0, 0, 0, 0.6)
		st.set_border_width_all(3 if gewaehlt else 1)
		for zustand in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(zustand, st)
		b.pressed.connect(func() -> void:
			aussehen[schluessel] = e["farbe"]
			_neu_bauen = true
			_gruppe_zeigen.call_deferred(_gruppe))
		fluss.add_child(b)
	_regler_box.add_child(fluss)


func _auswahl(name: String, ids: Array, schluessel: String) -> void:
	_ueberschrift(name)
	var fluss := HFlowContainer.new()
	fluss.add_theme_constant_override("h_separation", 4)
	fluss.add_theme_constant_override("v_separation", 4)
	for id in ids:
		var b := _knopf(Mensch.anzeige_name(id), func() -> void:
			aussehen[schluessel] = id
			_neu_bauen = true
			_gruppe_zeigen.call_deferred(_gruppe))
		b.toggle_mode = true
		b.button_pressed = aussehen.get(schluessel, "") == id
		fluss.add_child(b)
	_regler_box.add_child(fluss)


# ------------------------------------------------------------------ Werte setzen
func _grund_setzen(v: float, id: String) -> void:
	aussehen[id] = v


func _herkunft_setzen(v: float, i: int) -> void:
	var h: Array = aussehen.get("herkunft", [0.0, 0.0, 1.0])
	h[i] = v
	aussehen["herkunft"] = h


func _einzel_setzen(v: float, id: String) -> void:
	var r: Dictionary = aussehen.get("regler", {})
	if absf(v) < 0.005:
		r.erase(id)
	else:
		r[id] = v
	aussehen["regler"] = r


func _geschlecht_waehlen(g: float) -> void:
	if float(aussehen.get("geschlecht", 1.0)) == g:
		_geschlecht_knoepfe_setzen()
		return
	aussehen["geschlecht"] = g
	var mann := g > 0.5
	var frisuren := Mensch.frisuren(mann)
	if not aussehen.get("haar", "") in frisuren and not frisuren.is_empty():
		aussehen["haar"] = frisuren[0]
	if not mann:
		aussehen["bart"] = "keiner"
	_geschlecht_knoepfe_setzen()
	_neu_bauen = true
	_gruppe_zeigen(_gruppe)


func _geschlecht_knoepfe_setzen() -> void:
	for g in _geschlecht_knoepfe:
		_geschlecht_knoepfe[g].button_pressed = float(aussehen.get("geschlecht", 1.0)) == g


func _zufall(nur_gesicht: bool) -> void:
	aussehen = CharakterAussehen.zufall(rng, aussehen, nur_gesicht)
	_geschlecht_knoepfe_setzen()
	_neu_bauen = true
	_gruppe_zeigen(_gruppe)


func _zuruecksetzen() -> void:
	aussehen = CharakterAussehen.standard(not CharakterAussehen.ist_frau(aussehen))
	_neu_bauen = true
	_gruppe_zeigen(_gruppe)


func _als_npc() -> void:
	var name := _npc_name.text.strip_edges()
	if name == "":
		name = "NPC %d" % (CharakterAussehen.npc_liste().size() + 1)
	var pfad := CharakterAussehen.npc_speichern(name, aussehen.duplicate(true))
	_info.text = "„%s“ gespeichert (%s)" % [name, pfad] if pfad != "" else "Speichern fehlgeschlagen"
	_npc_name.text = ""


func _info_aktualisieren() -> void:
	var jahre := roundi(25.0 + float(aussehen.get("alter", 0.1)) * 52.0)
	_info.text = "Größe %d cm   Alter etwa %d Jahre" % [CharakterAussehen.groesse_cm(mensch), jahre]
