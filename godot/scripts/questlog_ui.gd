extends Control
## Questbuch (J): laufende und erledigte Quests nach Art, Ziele mit Fortschritt, Belohnung, Verfolgen.

signal wahl_angefordert(quest_id: String)

const GOLD := Color(1.0, 0.85, 0.5)
const QuestLog := preload("res://scripts/quest_log.gd")

var player = null
var zeige_erledigt := false
var gewaehlt := ""
var kopf_label: Label
var liste: VBoxContainer
var titel_label: Label
var art_label: Label
var text_label: Label
var ziele_box: VBoxContainer
var belohnung_label: Label
var verfolgen_knopf: Button
var abbrechen_knopf: Button
var wahl_knopf: Button
var tab_laufend: Button
var tab_erledigt: Button


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
	panel.offset_left = -560
	panel.offset_right = 560
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
	kopf.add_theme_constant_override("separation", 16)
	root.add_child(kopf)
	kopf.add_child(_label("Questbuch", 26, GOLD))
	tab_laufend = _tab("Laufend", false)
	kopf.add_child(tab_laufend)
	tab_erledigt = _tab("Erledigt", true)
	kopf.add_child(tab_erledigt)
	var platz := Control.new()
	platz.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	kopf.add_child(platz)
	kopf_label = _label("", 15, Color(0.85, 0.85, 0.85))
	kopf_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	kopf.add_child(kopf_label)

	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 24)
	root.add_child(body)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(360, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(scroll)
	liste = VBoxContainer.new()
	liste.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	liste.add_theme_constant_override("separation", 3)
	scroll.add_child(liste)

	var details := VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 10)
	body.add_child(details)
	titel_label = _label("", 24, GOLD)
	details.add_child(titel_label)
	art_label = _label("", 14, Color(0.7, 0.7, 0.75))
	details.add_child(art_label)
	text_label = _label("", 16, Color(0.9, 0.9, 0.88))
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(text_label)
	details.add_child(_label("Ziele", 17, GOLD))
	ziele_box = VBoxContainer.new()
	details.add_child(ziele_box)
	belohnung_label = _label("", 15, Color(0.75, 0.9, 0.6))
	belohnung_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(belohnung_label)
	var platz2 := Control.new()
	platz2.size_flags_vertical = Control.SIZE_EXPAND_FILL
	details.add_child(platz2)
	var reihe := HBoxContainer.new()
	reihe.add_theme_constant_override("separation", 10)
	details.add_child(reihe)
	wahl_knopf = Button.new()
	wahl_knopf.text = "Entscheidung treffen"
	wahl_knopf.pressed.connect(func() -> void: wahl_angefordert.emit(gewaehlt), CONNECT_DEFERRED)
	reihe.add_child(wahl_knopf)
	verfolgen_knopf = Button.new()
	verfolgen_knopf.text = "Verfolgen"
	verfolgen_knopf.pressed.connect(func() -> void:
		player.quests.verfolgt = gewaehlt
		player.quests.geaendert.emit()
		_refresh())
	reihe.add_child(verfolgen_knopf)
	abbrechen_knopf = Button.new()
	abbrechen_knopf.text = "Abbrechen"
	abbrechen_knopf.pressed.connect(func() -> void:
		player.quests.abbrechen(gewaehlt)
		gewaehlt = ""
		_refresh.call_deferred())
	reihe.add_child(abbrechen_knopf)


func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


func _tab(text: String, erledigt: bool) -> Button:
	var b := Button.new()
	b.text = text
	b.toggle_mode = true
	b.button_pressed = erledigt == zeige_erledigt
	b.pressed.connect(func() -> void:
		zeige_erledigt = erledigt
		gewaehlt = ""
		_refresh.call_deferred())
	return b


func open(p) -> void:
	player = p
	visible = true
	if gewaehlt == "" or not (player.quests.aktiv.has(gewaehlt) or player.quests.erledigt.has(gewaehlt)):
		gewaehlt = player.quests.verfolgt
	_refresh()


func close() -> void:
	visible = false


func _refresh() -> void:
	if player == null:
		return
	var q = player.quests
	tab_laufend.button_pressed = not zeige_erledigt
	tab_erledigt.button_pressed = zeige_erledigt
	var ansehen := 0
	for r in player.ansehen_region:
		ansehen += int(player.ansehen_region[r])
	kopf_label.text = "%d Gold   ·   %d Regionsansehen" % [player.gold, ansehen]
	for c in liste.get_children():
		liste.remove_child(c)
		c.queue_free()
	var ids: Array = q.erledigt.keys() if zeige_erledigt else q.aktiv.keys()
	if gewaehlt == "" or not ids.has(gewaehlt):
		gewaehlt = ids[0] if not ids.is_empty() else ""
	for art in QuestLog.ART_REIHENFOLGE:
		var passend := ids.filter(func(id): return String(QuestLog.quest(id).get("art", "neben")) == art)
		if passend.is_empty():
			continue
		liste.add_child(_label(String(QuestLog.ARTEN[art]), 14, QuestLog.ART_FARBEN[art]))
		for id in passend:
			var b := Button.new()
			var name := String(QuestLog.quest(id).get("titel", id))
			if id == q.verfolgt:
				name = "»  " + name
			if q.bereit(id):
				name += "   (fertig)"
			b.text = name
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.toggle_mode = true
			b.button_pressed = id == gewaehlt
			b.pressed.connect(func() -> void:
				gewaehlt = id
				_refresh.call_deferred())
			liste.add_child(b)
	if ids.is_empty():
		liste.add_child(_label("Keine Quests." if not zeige_erledigt else "Noch nichts erledigt.", 15, Color(0.6, 0.6, 0.6)))
	_details()


func _details() -> void:
	var q = player.quests
	for c in ziele_box.get_children():
		ziele_box.remove_child(c)
		c.queue_free()
	var leer := gewaehlt == ""
	verfolgen_knopf.visible = not leer and q.aktiv.has(gewaehlt) and q.verfolgt != gewaehlt
	abbrechen_knopf.visible = not leer and q.aktiv.has(gewaehlt) and String(QuestLog.quest(gewaehlt).get("art", "")) != "haupt"
	wahl_knopf.visible = not leer and q.bereit(gewaehlt) and q.abgabe_npc(gewaehlt) == "" and QuestLog.quest(gewaehlt).has("wahl")
	if leer:
		titel_label.text = ""
		art_label.text = ""
		text_label.text = ""
		belohnung_label.text = ""
		return
	var quest := QuestLog.quest(gewaehlt)
	titel_label.text = String(quest.get("titel", gewaehlt))
	var region := String(quest.get("region", ""))
	art_label.text = QuestLog.art_name(gewaehlt) + ("   ·   Region: " + region.capitalize() if region != "" else "")
	var texte: Dictionary = quest.get("texte", {})
	if q.erledigt.has(gewaehlt):
		text_label.text = String(texte.get("abschluss", texte.get("angebot", "")))
		var option := int(q.erledigt[gewaehlt])
		var optionen: Array = quest.get("wahl", {}).get("optionen", [])
		if option >= 0 and option < optionen.size():
			text_label.text += "\n\nDeine Wahl: " + String(optionen[option].get("text", ""))
	else:
		text_label.text = String(texte.get("laufend", texte.get("angebot", "")))
	var ziele: Array = quest.get("ziele", [])
	for i in ziele.size():
		var fertig: bool = q.erledigt.has(gewaehlt) or q.ziel_fertig(gewaehlt, i)
		var offen: bool = q.ziel_offen(gewaehlt, i)
		if not fertig and not offen:
			ziele_box.add_child(_label("○  ???", 15, Color(0.45, 0.45, 0.45))) # spätere Schritte bleiben verborgen
			continue
		ziele_box.add_child(_label(("✓  " if fertig else "○  ") + q.ziel_text(gewaehlt, i), 15,
			Color(0.55, 0.8, 0.5) if fertig else Color(0.95, 0.95, 0.95)))
	if q.bereit(gewaehlt):
		var npc: String = q.abgabe_npc(gewaehlt)
		ziele_box.add_child(_label("»  Bei %s abgeben" % QuestLog.npc_name(npc) if npc != "" else "»  Entscheidung treffen", 15, GOLD))
	var b := QuestLog.belohnung_text(quest.get("belohnung", {}))
	belohnung_label.text = "Belohnung: " + b if b != "" else ""
