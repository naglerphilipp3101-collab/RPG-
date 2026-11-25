extends Control
## Animations-Werkstatt (Philipp, 25.11.), erreichbar über den Ausrüstungsschrank.
## Reiter „Griff“: Waffe in der Hand verschieben und drehen, Griffpunkt der linken Hand festlegen (die Hand zieht sich per IK
## dorthin), Pose und Zeitpunkt wählen und anhalten. Speichert nach data/griffe.json.
## Reiter „Animationen“: für jeden Platz (Ruhe, Schläge, Fähigkeiten …) aus allen Animationen wählen, mit Vorschau und Notiz.
## Speichert nach data/animationen_wahl.json. Die Kamera lässt sich mit den Knöpfen oben um die Figur stellen.

const PLAETZE := ["ruhe", "block", "zielen", "spannen", "schuss", "nachladen", "schlaege/h_right", "schlaege/h_left",
	"schlaege/diag", "schlaege/overhead", "schlaege/big_overhead", "schlaege/thrust", "buff", "dash", "leap", "spin",
	"zone", "beschwoeren", "treffer", "tod"]
const PLATZ_NAMEN := {"ruhe": "Ruhe (Kampfhaltung)", "block": "Blocken", "zielen": "Zielen", "spannen": "Spannen (Bogen)",
	"schuss": "Schuss / Zauber", "nachladen": "Nachladen", "schlaege/h_right": "Schlag waagerecht von rechts",
	"schlaege/h_left": "Schlag waagerecht von links", "schlaege/diag": "Schlag schräg", "schlaege/overhead": "Schlag von oben",
	"schlaege/big_overhead": "Schwerer Schlag", "schlaege/thrust": "Stich", "buff": "Stärkung / Schrei", "dash": "Ansturm",
	"leap": "Sprungangriff", "spin": "Wirbel", "zone": "Flächenzauber", "beschwoeren": "Beschwören", "treffer": "Getroffen",
	"tod": "Tod"}
# Fähigkeiten-Vorlage -> Platz (für die Anzeige, welche Fähigkeit welchen Platz nutzt)
const VORLAGE_PLATZ := {"dash": "dash", "leap": "leap", "buff": "buff", "detonate": "buff", "sacrifice": "buff",
	"summon": "beschwoeren", "zone": "zone", "wall": "zone", "beam": "zone", "shot": "schuss"}

var player = null
var typ := ""
var regler := {}            # Name -> HSlider
var zweite_an: CheckBox
var pose_wahl: OptionButton
var pose_zeit: HSlider
var pose_laeuft: CheckButton
var hinweis: Label
var titel: Label
var platz_liste: ItemList
var anim_liste: ItemList
var filter: LineEdit
var notiz: LineEdit
var nutzer: Label
var alle_anims: PackedStringArray = []
var auswahl := {}           # Werkstatt-Auswahl der aktuellen Waffe (Kopie)
var _pose := ""
var _kamera_richtung := "seite"
var _abstand := 2.6
var _laden_laeuft := false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE # die 3D-Ansicht rechts bleibt frei
	visible = false
	var panel := PanelContainer.new()
	panel.anchor_bottom = 1.0
	panel.offset_left = 8
	panel.offset_top = 8
	panel.offset_right = 520
	panel.offset_bottom = -8
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.93)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(12)
	panel.add_theme_stylebox_override("panel", style)
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(panel)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	panel.add_child(root)
	var kopf := HBoxContainer.new()
	root.add_child(kopf)
	titel = _label("Animations-Werkstatt", 22, Color(1.0, 0.85, 0.5))
	kopf.add_child(titel)
	var platz := Control.new()
	platz.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	kopf.add_child(platz)
	kopf.add_child(_knopf("Schließen", close))
	# Kamera
	var kam := HBoxContainer.new()
	root.add_child(kam)
	kam.add_child(_label("Kamera:", 14, Color(0.8, 0.8, 0.8)))
	for r in [["Links", "links"], ["Vorne", "vorne"], ["Rechts", "seite"], ["Hinten", "hinten"], ["Oben", "oben"]]:
		kam.add_child(_knopf(r[0], _kamera_setzen.bind(r[1])))
	kam.add_child(_knopf("+", _naeher.bind(0.8)))
	kam.add_child(_knopf("−", _naeher.bind(1.25)))
	var reiter := TabContainer.new()
	reiter.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(reiter)
	reiter.add_child(_griff_reiter())
	reiter.add_child(_anim_reiter())
	hinweis = _label("", 14, Color(0.6, 0.9, 0.6))
	hinweis.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(hinweis)


func _griff_reiter() -> Control:
	var scroll := ScrollContainer.new()
	scroll.name = "Griff"
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(box)
	box.add_child(_label("Pose zum Einstellen", 16, Color(1.0, 0.85, 0.5)))
	pose_wahl = OptionButton.new()
	pose_wahl.item_selected.connect(func(_i: int) -> void: _pose_spielen())
	box.add_child(pose_wahl)
	pose_zeit = _regler_zeile(box, "Zeitpunkt", 0.0, 1.0, 0.005, func(_v: float) -> void: _pose_zeigen())
	pose_laeuft = CheckButton.new()
	pose_laeuft.text = "Abspielen"
	pose_laeuft.toggled.connect(func(_an: bool) -> void: _pose_zeigen())
	box.add_child(pose_laeuft)
	box.add_child(HSeparator.new())
	box.add_child(_label("Waffe in der Hand", 16, Color(1.0, 0.85, 0.5)))
	for achse in ["x", "y", "z"]:
		regler["pos_" + achse] = _regler_zeile(box, "Verschieben " + achse.to_upper() + " (m)", -0.8, 0.8, 0.002, _geaendert)
	for achse in ["x", "y", "z"]:
		regler["rot_" + achse] = _regler_zeile(box, "Drehen " + achse.to_upper() + " (°)", -180.0, 180.0, 0.5, _geaendert)
	box.add_child(HSeparator.new())
	box.add_child(_label("Linke Hand", 16, Color(1.0, 0.85, 0.5)))
	zweite_an = CheckBox.new()
	zweite_an.text = "Linke Hand greift die Waffe mit"
	zweite_an.toggled.connect(func(_an: bool) -> void: _geaendert(0.0))
	box.add_child(zweite_an)
	box.add_child(_knopf("Griffpunkt = Lage der linken Hand in dieser Pose", _zweite_aus_pose))
	for achse in ["x", "y", "z"]:
		regler["zweite_" + achse] = _regler_zeile(box, "Griffpunkt " + achse.to_upper() + " an der Waffe (m)", -2.0, 2.0, 0.002, _geaendert)
	var info := _label("Z läuft entlang der Waffe: negativ = Richtung Spitze/Mündung, positiv = Richtung Knauf/Schaftende.",
		13, Color(0.7, 0.7, 0.7))
	info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(info)
	var knoepfe := HBoxContainer.new()
	box.add_child(knoepfe)
	knoepfe.add_child(_knopf("Griff speichern", _griff_speichern))
	knoepfe.add_child(_knopf("Verwerfen", _laden))
	return scroll


func _anim_reiter() -> Control:
	var box := VBoxContainer.new()
	box.name = "Animationen"
	box.add_child(_label("1. Platz wählen   2. Animation anklicken (Vorschau)   3. Übernehmen", 13, Color(0.8, 0.8, 0.8)))
	platz_liste = ItemList.new()
	platz_liste.custom_minimum_size.y = 230
	platz_liste.item_selected.connect(func(_i: int) -> void: _platz_gewaehlt())
	box.add_child(platz_liste)
	nutzer = _label("", 13, Color(0.75, 0.75, 0.6))
	nutzer.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(nutzer)
	filter = LineEdit.new()
	filter.placeholder_text = "Suchen (z. B. slash, kick, magic) …"
	filter.text_changed.connect(func(_t: String) -> void: _anims_fuellen())
	box.add_child(filter)
	anim_liste = ItemList.new()
	anim_liste.size_flags_vertical = Control.SIZE_EXPAND_FILL
	anim_liste.custom_minimum_size.y = 180
	anim_liste.item_selected.connect(func(i: int) -> void: _vorschau(anim_liste.get_item_text(i)))
	anim_liste.item_activated.connect(func(_i: int) -> void: _uebernehmen())
	box.add_child(anim_liste)
	var zeile := HBoxContainer.new()
	box.add_child(zeile)
	zeile.add_child(_knopf("Übernehmen", _uebernehmen))
	zeile.add_child(_knopf("Standard", _standard))
	zeile.add_child(_knopf("Nochmal abspielen", _nochmal))
	notiz = LineEdit.new()
	notiz.placeholder_text = "Notiz zu diesem Platz: wie soll es aussehen?"
	notiz.text_changed.connect(_notiz_geaendert)
	box.add_child(notiz)
	box.add_child(_knopf("Animationen speichern", _anim_speichern))
	return box


func open(p) -> void:
	player = p
	typ = player.weapon_type
	visible = true
	hinweis.text = ""
	player.set_freie_kamera(true)
	alle_anims = PackedStringArray()
	for n in player.anim_figur.ap.get_animation_list():
		alle_anims.append(n)
	alle_anims.sort()
	_laden()
	_kamera()


func close() -> void:
	if not visible:
		return
	visible = false
	if player:
		player.anim_figur.zuruecksetzen()
		player.anim_figur.ap.speed_scale = 1.0
		player.anim_figur.ap.play()
		player._build_weapon_visual()
		player.set_freie_kamera(false)


func _process(_delta: float) -> void:
	if visible and player and player.freie_kamera:
		_kamera()


# --- Kamera ---------------------------------------------------------------

func _kamera_setzen(richtung: String) -> void:
	_kamera_richtung = richtung
	_kamera()


func _naeher(faktor: float) -> void:
	_abstand = clampf(_abstand * faktor, 0.6, 8.0)
	_kamera()


func _kamera() -> void:
	var cam = player.freie_kamera
	if cam == null:
		return
	var ziel: Vector3 = player.global_position + Vector3(0, 1.25, 0)
	var b: Basis = player.model.global_transform.basis.orthonormalized()
	var vorn := -b.z
	var rechts := b.x
	var r := {"vorne": vorn, "hinten": -vorn, "seite": rechts, "links": -rechts,
		"oben": (vorn * 0.35 + Vector3.UP).normalized()}[_kamera_richtung] as Vector3
	r = (r + Vector3.UP * 0.12).normalized()
	cam.global_position = ziel + r * _abstand + b.x * 0.0
	var d: Vector3 = (ziel - cam.global_position).normalized()
	cam.gier = atan2(-d.x, -d.z)
	cam.neigung = asin(clampf(d.y, -1.0, 1.0))
	cam.fov = 45.0


# --- Griff ----------------------------------------------------------------

func _laden() -> void:
	_laden_laeuft = true
	typ = player.weapon_type
	titel.text = "Werkstatt: " + String(Game.weapons.get(typ, {}).get("name", typ))
	var g := SpielerAnimation.griff(typ)
	for i in 3:
		regler["pos_" + "xyz"[i]].value = g["pos"][i]
		regler["rot_" + "xyz"[i]].value = g["rot"][i]
	zweite_an.button_pressed = g["zweite"] != null
	var z: Vector3 = g["zweite"] if g["zweite"] != null else Vector3.ZERO
	for i in 3:
		regler["zweite_" + "xyz"[i]].value = z[i]
	# Posen: alle Plätze des Satzes, die eine Animation haben
	pose_wahl.clear()
	var satz: Dictionary = player.anim_figur.satz
	for p in PLAETZE:
		var n := _satz_anim(satz, p)
		if n != "":
			pose_wahl.add_item("%s: %s" % [PLATZ_NAMEN[p], n])
			pose_wahl.set_item_metadata(pose_wahl.item_count - 1, n)
	auswahl = SpielerAnimation.wahl().get(typ, {}).duplicate(true)
	_plaetze_fuellen()
	_anims_fuellen()
	_laden_laeuft = false
	_geaendert(0.0)
	if pose_wahl.item_count > 0:
		_pose_spielen()


func _satz_anim(satz: Dictionary, platz: String) -> String:
	var v = satz.get("schlaege", {}).get(platz.trim_prefix("schlaege/"), "") if platz.begins_with("schlaege/") else satz.get(platz, "")
	if v is Array:
		v = v[0] if not v.is_empty() else ""
	return String(v)


func _geaendert(_v: float) -> void:
	if _laden_laeuft or player == null:
		return
	var pivot: Node3D = player.weapon_pivot
	pivot.position = Vector3(regler["pos_x"].value, regler["pos_y"].value, regler["pos_z"].value)
	pivot.rotation_degrees = Vector3(regler["rot_x"].value, regler["rot_y"].value, regler["rot_z"].value)
	var z: Variant = null
	if zweite_an.button_pressed:
		z = Vector3(regler["zweite_x"].value, regler["zweite_y"].value, regler["zweite_z"].value)
	player.anim_figur.zweite_hand(pivot, z)


func _pose_spielen() -> void:
	var i := pose_wahl.selected
	if i < 0:
		return
	_pose = String(pose_wahl.get_item_metadata(i))
	player.anim_figur.schleife(_pose)
	_pose_zeigen()


func _pose_zeigen() -> void:
	var ap: AnimationPlayer = player.anim_figur.ap
	if _pose == "" or not ap.has_animation(SpielerAnimation._voll(_pose)):
		return
	if pose_laeuft.button_pressed:
		ap.play()
		return
	var laenge := ap.get_animation(SpielerAnimation._voll(_pose)).length
	ap.seek(laenge * pose_zeit.value, true)
	ap.pause()


## Griffpunkt der linken Hand = wo die Animation die linke Hand gerade hat (ohne IK), im Raum der Waffe.
func _zweite_aus_pose() -> void:
	var fig = player.anim_figur
	var pivot: Node3D = player.weapon_pivot
	fig.zweite_hand(pivot, null)
	await get_tree().process_frame
	await get_tree().process_frame
	var sk: Skeleton3D = fig.mensch.skelett
	var links := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("LeftHand")) * SpielerAnimation.griff_transform(sk, true)
	var punkt := pivot.global_transform.affine_inverse() * links.origin
	_laden_laeuft = true
	zweite_an.button_pressed = true
	for i in 3:
		regler["zweite_" + "xyz"[i]].value = punkt[i]
	_laden_laeuft = false
	_geaendert(0.0)
	hinweis.text = "Griffpunkt übernommen. Mit „Griff speichern“ sichern."


func _griff_speichern() -> void:
	var alle: Dictionary = SpielerAnimation.griffe().duplicate(true)
	var alt: Dictionary = alle.get(typ, {})
	var eintrag := {"hand": alt.get("hand", "rechts"),
		"pos": [snappedf(regler["pos_x"].value, 0.001), snappedf(regler["pos_y"].value, 0.001), snappedf(regler["pos_z"].value, 0.001)],
		"rot": [snappedf(regler["rot_x"].value, 0.1), snappedf(regler["rot_y"].value, 0.1), snappedf(regler["rot_z"].value, 0.1)]}
	if zweite_an.button_pressed:
		eintrag["zweite"] = [snappedf(regler["zweite_x"].value, 0.001), snappedf(regler["zweite_y"].value, 0.001),
			snappedf(regler["zweite_z"].value, 0.001)]
	alle[typ] = eintrag
	var ok := SpielerAnimation.griffe_speichern(alle)
	hinweis.text = ("Griff gespeichert (data/griffe.json)." if ok else "Speichern fehlgeschlagen!")


# --- Animationen ------------------------------------------------------------

func _plaetze_fuellen() -> void:
	var alt := platz_liste.get_selected_items()
	platz_liste.clear()
	var satz: Dictionary = player.anim_figur.satz
	for p in PLAETZE:
		var eigen := String(auswahl.get(p, ""))
		var n := eigen if eigen != "" else _satz_anim(satz, p)
		platz_liste.add_item("%s%s:  %s" % ["★ " if eigen != "" else "", PLATZ_NAMEN[p], n if n != "" else "(Ersatz)"])
	if alt.size() > 0:
		platz_liste.select(alt[0])


func _platz() -> String:
	var s := platz_liste.get_selected_items()
	return PLAETZE[s[0]] if s.size() > 0 else ""


func _platz_gewaehlt() -> void:
	var p := _platz()
	notiz.text = String(auswahl.get("notizen", {}).get(p, ""))
	# Welche Angriffe und Fähigkeiten nutzen diesen Platz?
	var namen: Array[String] = []
	var def: Dictionary = Game.weapons.get(typ, {})
	for a in def.get("light", []):
		if "schlaege/" + String(a.get("style", "")) == p:
			namen.append("Leichter Angriff")
	if "schlaege/" + String(def.get("heavy", {}).get("style", "")) == p:
		namen.append("Schwerer Angriff")
	for seite in def.get("sides", []):
		for f in seite.get("skills", []) + [seite.get("ultimate", {})]:
			var s: Dictionary = f.get("skill", {})
			var t := String(s.get("template", ""))
			var ziel := String(VORLAGE_PLATZ.get(t, ""))
			if t == "strike":
				ziel = "spin" if s.get("spin", false) else "schlaege/" + String(s.get("style", ""))
			if ziel == p:
				namen.append(String(f.get("name", "")))
	nutzer.text = "Genutzt von: " + (", ".join(namen) if not namen.is_empty() else "–")


func _anims_fuellen() -> void:
	anim_liste.clear()
	var f := filter.text.strip_edges().to_lower()
	for n in alle_anims:
		if f == "" or n.to_lower().contains(f):
			anim_liste.add_item(n)


func _vorschau(n: String) -> void:
	pose_laeuft.button_pressed = true
	player.anim_figur.ap.speed_scale = 1.0
	player.anim_figur.schleife(n)


func _nochmal() -> void:
	if anim_liste.get_selected_items().size() > 0:
		_vorschau(anim_liste.get_item_text(anim_liste.get_selected_items()[0]))


func _uebernehmen() -> void:
	var p := _platz()
	var s := anim_liste.get_selected_items()
	if p == "" or s.is_empty():
		hinweis.text = "Erst links einen Platz und unten eine Animation wählen."
		return
	auswahl[p] = anim_liste.get_item_text(s[0])
	_auswahl_anwenden()
	hinweis.text = "%s → %s (noch nicht gespeichert)" % [PLATZ_NAMEN[p], auswahl[p]]


func _standard() -> void:
	var p := _platz()
	if p == "":
		return
	auswahl.erase(p)
	_auswahl_anwenden()


func _notiz_geaendert(t: String) -> void:
	var p := _platz()
	if p == "":
		return
	if not auswahl.has("notizen"):
		auswahl["notizen"] = {}
	auswahl["notizen"][p] = t


func _auswahl_anwenden() -> void:
	var alle: Dictionary = SpielerAnimation.wahl().duplicate(true)
	alle[typ] = auswahl.duplicate(true)
	SpielerAnimation._wahl = alle # gilt sofort, gespeichert wird erst mit dem Knopf
	player.anim_figur.waffe_setzen(typ)
	_plaetze_fuellen()


func _anim_speichern() -> void:
	var alle: Dictionary = SpielerAnimation.wahl().duplicate(true)
	alle[typ] = auswahl.duplicate(true)
	var ok := SpielerAnimation.wahl_speichern(alle)
	hinweis.text = ("Animationen gespeichert (data/animationen_wahl.json)." if ok else "Speichern fehlgeschlagen!")


# --- Bausteine --------------------------------------------------------------

func _regler_zeile(box: Control, text: String, von: float, bis: float, schritt: float, bei: Callable) -> HSlider:
	var zeile := HBoxContainer.new()
	box.add_child(zeile)
	var l := _label(text, 13, Color(0.85, 0.85, 0.85))
	l.custom_minimum_size.x = 210
	zeile.add_child(l)
	var r := HSlider.new()
	r.min_value = von
	r.max_value = bis
	r.step = schritt
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	zeile.add_child(r)
	var zahl := SpinBox.new()
	zahl.min_value = von
	zahl.max_value = bis
	zahl.step = schritt
	zahl.custom_minimum_size.x = 90
	zeile.add_child(zahl)
	r.share(zahl)
	r.value_changed.connect(bei)
	return r


func _knopf(text: String, bei: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(bei)
	return b


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
