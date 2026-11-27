extends Control
## Gesprächsfenster: mit NPCs reden (F), Quests annehmen und abgeben, Entscheidungen treffen,
## dazu Texte beim Untersuchen von Quest-Orten. Die Logik steckt in scripts/quest_log.gd.

signal closed

const GOLD := Color(1.0, 0.85, 0.5)
const QuestLog := preload("res://scripts/quest_log.gd")

var player = null
var npc_id := ""
var titel_label: Label
var text_label: Label
var knoepfe: VBoxContainer


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 1.0
	panel.anchor_bottom = 1.0
	panel.offset_left = -470
	panel.offset_right = 470
	panel.offset_top = -400
	panel.offset_bottom = -40
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.07, 0.07, 0.09, 0.95)
	style.border_color = Color(0.75, 0.62, 0.35)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(18)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)
	titel_label = _label("", 22, GOLD)
	box.add_child(titel_label)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	text_label = _label("", 16, Color(0.92, 0.92, 0.9))
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(text_label)
	knoepfe = VBoxContainer.new()
	knoepfe.add_theme_constant_override("separation", 4)
	box.add_child(knoepfe)


func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


func close() -> void:
	if visible:
		visible = false
		closed.emit()


# --- Gespräch mit einem NPC -----------------------------------------------------

func open_npc(p, id: String) -> void:
	player = p
	npc_id = id
	var def: Dictionary = Game.npcs.get(id, {})
	titel_label.text = "%s, %s" % [String(def.get("name", id)), String(def.get("titel", ""))]
	var vorher: Dictionary = player.quests.erledigt.duplicate()
	var saetze: Array = player.quests.ereignis("reden", id)
	saetze.append_array(player.quests.ereignis("abgeben", id))
	saetze.append_array(_neu_abgeschlossen(vorher))
	text_label.text = "\n\n".join(saetze) if not saetze.is_empty() else String(def.get("gruss", "..."))
	visible = true
	_menue()


## Abschlusstexte von Quests, die sich eben von selbst abgeschlossen haben (ohne Abgabe-NPC).
func _neu_abgeschlossen(vorher: Dictionary) -> Array:
	var texte: Array = []
	for qid in player.quests.erledigt:
		if not vorher.has(qid):
			var q := QuestLog.quest(qid)
			if q.get("texte", {}).has("abschluss"):
				texte.append(String(q["texte"]["abschluss"]))
			var b := QuestLog.belohnung_text(q.get("belohnung", {}))
			if b != "":
				texte.append("Quest abgeschlossen: %s  (%s)" % [String(q.get("titel", qid)), b])
	return texte


func _menue() -> void:
	_knoepfe_leeren()
	var q = player.quests
	for qid in q.aktiv.keys():
		if q.bereit(qid) and q.abgabe_npc(qid) == npc_id:
			_knopf("?  %s abschließen" % String(QuestLog.quest(qid).get("titel", qid)), _zeige_abschluss.bind(qid), GOLD)
	for qid in q.angebote(npc_id):
		_knopf("!  %s" % String(QuestLog.quest(qid).get("titel", qid)), _zeige_angebot.bind(qid), Color(1.0, 0.9, 0.4))
	for qid in q.aktiv.keys():
		if not q.bereit(qid) and String(QuestLog.quest(qid).get("geber", "")) == npc_id:
			_knopf("%s (läuft)" % String(QuestLog.quest(qid).get("titel", qid)), _zeige_laufend.bind(qid), Color(0.8, 0.8, 0.8))
	_knopf("Auf Wiedersehen", close, Color(0.7, 0.7, 0.7))


func _zeige_angebot(qid: String) -> void:
	var quest := QuestLog.quest(qid)
	titel_label.text = "%s  ·  %s" % [String(quest.get("titel", qid)), QuestLog.art_name(qid)]
	var b := QuestLog.belohnung_text(quest.get("belohnung", {}))
	text_label.text = String(quest.get("texte", {}).get("angebot", "")) + ("\n\nBelohnung: " + b if b != "" else "")
	_knoepfe_leeren()
	_knopf("Annehmen", func() -> void:
		player.quests.annehmen(qid)
		var nachher: Array = player.quests.ereignis("reden", npc_id) # falls das erste Ziel dieses Gespräch ist
		text_label.text = String(quest.get("texte", {}).get("laufend", "Quest angenommen."))
		if not nachher.is_empty():
			text_label.text += "\n\n" + "\n\n".join(nachher)
		_titel_npc()
		_menue(), GOLD)
	_knopf("Später", func() -> void:
		_titel_npc()
		text_label.text = String(Game.npcs.get(npc_id, {}).get("gruss", ""))
		_menue(), Color(0.7, 0.7, 0.7))


func _zeige_laufend(qid: String) -> void:
	text_label.text = String(QuestLog.quest(qid).get("texte", {}).get("laufend", "Noch nicht erledigt."))
	_menue()


func _zeige_abschluss(qid: String) -> void:
	var quest := QuestLog.quest(qid)
	titel_label.text = String(quest.get("titel", qid))
	var b := QuestLog.belohnung_text(quest.get("belohnung", {}))
	text_label.text = String(quest.get("texte", {}).get("abschluss", "Danke dir.")) + ("\n\nBelohnung: " + b if b != "" else "")
	_knoepfe_leeren()
	if quest.has("wahl"):
		_wahl_knoepfe(qid)
	else:
		_knopf("Belohnung annehmen", func() -> void:
			var vorher: Dictionary = player.quests.erledigt.duplicate()
			player.quests.abschliessen(qid)
			vorher[qid] = -1
			var weitere := _neu_abgeschlossen(vorher)
			_titel_npc()
			text_label.text = "\n\n".join(weitere) if not weitere.is_empty() else String(quest.get("titel", qid)) + " abgeschlossen."
			_menue(), GOLD)


func _titel_npc() -> void:
	var def: Dictionary = Game.npcs.get(npc_id, {})
	titel_label.text = "%s, %s" % [String(def.get("name", npc_id)), String(def.get("titel", ""))] if npc_id != "" else "Entscheidung"


# --- Entscheidungen und Hinweise ------------------------------------------------

## Quest ohne Abgabe-NPC mit Entscheidung (z. B. der besiegte Vogt).
func open_wahl(p, qid: String) -> void:
	player = p
	npc_id = ""
	var quest := QuestLog.quest(qid)
	titel_label.text = "%s  ·  Entscheidung" % String(quest.get("titel", qid))
	text_label.text = String(quest.get("texte", {}).get("abschluss", ""))
	visible = true
	_knoepfe_leeren()
	_wahl_knoepfe(qid)


func _wahl_knoepfe(qid: String) -> void:
	var wahl: Dictionary = QuestLog.quest(qid).get("wahl", {})
	if wahl.has("frage"):
		text_label.text += "\n\n" + String(wahl["frage"])
	var optionen: Array = wahl.get("optionen", [])
	for i in optionen.size():
		var o: Dictionary = optionen[i]
		var b := QuestLog.belohnung_text(o.get("belohnung", {}))
		_knopf(String(o.get("text", "?")) + ("   (" + b + ")" if b != "" else ""), func() -> void:
			var ergebnis: String = player.quests.abschliessen(qid, i)
			text_label.text = ergebnis if ergebnis != "" else "Entschieden."
			_knoepfe_leeren()
			if npc_id != "":
				_menue()
			else:
				_knopf("Weiter", close, GOLD), GOLD)


## Text beim Untersuchen eines Quest-Orts.
func open_hinweis(p, titel: String, saetze: Array) -> void:
	player = p
	npc_id = ""
	titel_label.text = titel
	text_label.text = "\n\n".join(saetze) if not saetze.is_empty() else "Hier ist nichts Besonderes."
	visible = true
	_knoepfe_leeren()
	_knopf("Weiter", close, GOLD)


func _knoepfe_leeren() -> void:
	for c in knoepfe.get_children():
		knoepfe.remove_child(c)
		c.queue_free()


func _knopf(text: String, aktion: Callable, farbe: Color) -> void:
	var b := Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.add_theme_font_size_override("font_size", 16)
	b.add_theme_color_override("font_color", farbe)
	b.pressed.connect(aktion, CONNECT_DEFERRED)
	knoepfe.add_child(b)
