extends Node
## Test des Quest-Systems: Godot --headless --path godot -- --autotest --quests
## Spielt Prolog, Nebenaufgaben, die Skizzenbuch-Reihe und beide Enden von „Der Geist der Mühle“ durch,
## prüft Belohnungen, Blaupausen, Speichern/Laden und alte Spielstände. Mit --bild bleibt das Questbuch offen
## (für --write-movie), sonst endet der Test von selbst.

const SaveGame := preload("res://scripts/save_game.gd")
const PATH := "user://test_quests.json"

var player
var hud
var welt
var fehler := 0


func _ready() -> void:
	player = get_tree().get_first_node_in_group("player")
	hud = get_tree().current_scene.get_node("HUD")
	welt = get_tree().get_first_node_in_group("quest_welt")
	hud.help_panel.visible = false
	_lauf()


func _check(name: String, ok: bool, detail := "") -> void:
	if not ok:
		fehler += 1
	print("AUTOTEST %s %s%s" % ["OK    " if ok else "FEHLER", name, ("   (" + detail + ")") if detail != "" else ""])


## Mit --bild <ordner>: Bildschirmfoto (nur mit Fenster, z. B. xvfb-run … --rendering-method gl_compatibility)
func _foto(name: String) -> void:
	var args := OS.get_cmdline_user_args()
	if not args.has("--bild") or DisplayServer.get_name() == "headless":
		return
	await _warte(0.6)
	var ordner: String = args[args.find("--bild") + 1]
	get_viewport().get_texture().get_image().save_png(ordner.path_join(name + ".png"))


func _warte(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _reden(npc: String) -> void:
	hud._gespraech_oeffnen(npc)
	hud.close_all_windows()


func _hin(ort: String) -> void:
	var o = welt.ort_knoten[ort]
	player.global_position = o.global_position + Vector3(0.8, 0.5, 0.8)
	await _warte(0.4)


func _untersuchen(ort: String) -> void:
	await _hin(ort)
	player._start_interaction(welt.ort_knoten[ort])
	hud.close_all_windows()


## Besiegt alle lebenden Gegner dieses Typs (über den echten Tod, damit EP, Gold und Quest-Hooks laufen).
func _besiegen(typ: String, anzahl := 99) -> int:
	var n := 0
	for g in get_tree().get_nodes_in_group("enemies"):
		if n < anzahl and g.type_id == typ and g.is_alive():
			g.damage_by_source = {"sword_shield": 100.0}
			g._die()
			n += 1
	return n


func _lauf() -> void:
	var q = player.quests
	await _warte(0.2)
	# --- Prolog: startet von selbst, Dorfältester -------------------------------
	_check("Prolog startet von selbst", q.ist_aktiv("haupt_prolog_1"))
	_check("Kompass hat ein Ziel", welt.ziel_position() != null)
	_reden("aeltester")
	_check("Reden schließt den Prolog ab", q.ist_erledigt("haupt_prolog_1"))
	_check("Ältester bietet die nächste Quest an (!)", q.angebote("aeltester").has("haupt_prolog_2")
		and welt.npc_knoten["aeltester"]._zeichen.text == "!")
	q.annehmen("haupt_prolog_2")
	player.inventory.add("green_wood", 5)
	_reden("aeltester")
	_check("Abgeben nimmt das Holz", player.inventory.count("green_wood") == 0 and q.bereit("haupt_prolog_2"))
	var gold_vorher: int = player.gold
	q.abschliessen("haupt_prolog_2")
	_check("Belohnung Gold und Regionsansehen", player.gold == gold_vorher + 20 and int(player.ansehen_region.get("startgebiet", 0)) == 50,
		"Gold %d, Ansehen %s" % [player.gold, player.ansehen_region])

	# --- Nebenaufgabe: Wölfe ---------------------------------------------------------
	q.annehmen("neben_wolfsplage")
	var gold_wolf: int = player.gold
	_besiegen("wolf", 3)
	_check("Drei Wölfe zählen", q.bereit("neben_wolfsplage"), q.ziel_text("neben_wolfsplage", 0))
	_check("Wölfe geben kein Gold", player.gold == gold_wolf)
	_reden("jaegerin")
	_check("Jägerin zeigt ? zum Abgeben", welt.npc_knoten["jaegerin"]._zeichen.text == "?")
	q.abschliessen("neben_wolfsplage")
	q.annehmen("neben_banditen")
	_besiegen("bandit", 1)
	_check("Banditen haben Gold", player.gold > gold_wolf + 10)
	_check("Abbrechen geht bei Nebenaufgaben", q.abbrechen("neben_banditen") and not q.ist_aktiv("neben_banditen"))

	# --- Skizzenbuch: Blaupausen-Tutorial ---------------------------------------
	_check("Neues Spiel: Aussehen gesperrt, Form 2 ohne Blaupause", not player.freischaltungen.has("skizzenbuch")
		and not player.hat_blaupause("parierstange", 1, 2) and player.hat_blaupause("parierstange", 1, 1))
	q.annehmen("skizze_1")
	player.inventory.add("copper_ore", 32)
	player.inventory.add("timber", 6)
	player.inventory.add("coarse_leather", 4)
	player.craft("copper_ingot", 4)
	_check("Herstellen zählt (Barren)", q.ziel_fertig("skizze_1", 0), q.ziel_text("skizze_1", 0))
	player.craft("copper_sword", 1)
	_check("Herstellen zählt (Schwert)", q.ziel_fertig("skizze_1", 1))
	_reden("hedda")
	q.abschliessen("skizze_1")
	_check("Hedda bietet Teil 2 an", q.angebote("hedda").has("skizze_2"))
	if OS.get_cmdline_user_args().has("--bild"):
		hud._gespraech_oeffnen("hedda")
		hud.dialog_ui._zeige_angebot("skizze_2")
		await _foto("quest_gespraech")
		hud.close_all_windows()
	q.annehmen("skizze_2")
	await _hin("alte_schmiede")
	_check("Besuchen erkannt", q.ziel_fertig("skizze_2", 0))
	await _warte(0.4)
	var quest_banditen := get_tree().get_nodes_in_group("enemies").filter(func(g): return g.einmalig and g.is_alive())
	_check("Drei Quest-Banditen erscheinen", quest_banditen.size() == 3, str(quest_banditen.map(func(g): return g.type_id)))
	for g in quest_banditen:
		g.damage_by_source = {"sword_shield": 100.0}
		g._die()
	_check("Esse ist jetzt untersuchbar", welt.ort_knoten["alte_esse"].is_interactable())
	await _untersuchen("alte_esse")
	_check("Untersuchen gibt das Skizzenbuch", player.inventory.count("altes_skizzenbuch") == 1)
	_reden("hedda")
	_check("Skizzenbuch abgegeben", player.inventory.count("altes_skizzenbuch") == 0 and q.bereit("skizze_2"))
	q.abschliessen("skizze_2")
	q.annehmen("skizze_3")
	_check("Formen lesen: Aussehen frei, Form 2 frei, Form 3 nicht", player.freischaltungen.has("skizzenbuch")
		and player.hat_blaupause("parierstange", 1, 2) and not player.hat_blaupause("parierstange", 1, 3))
	var modul := {"klinge": {"tier": 1, "form": 1}, "parier": {"tier": 1, "form": 3}, "griff": {"tier": 1, "form": 1}, "knauf": {"tier": 1, "form": 1}}
	_check("Schmieden mit fehlender Blaupause wird abgelehnt", player.module_check("copper_sword", modul) != "")
	player.craft("copper_sword", 1)
	_check("Schwert ohne neue Form zählt nicht", not q.ziel_fertig("skizze_3", 0))
	player.craft("copper_ingot", 4)
	modul["parier"]["form"] = 2
	var err: String = player.craft("copper_sword", 1, [], modul)
	_check("Schwert mit Form 2 zählt", err == "" and q.ziel_fertig("skizze_3", 0), err)
	_reden("hedda")
	q.abschliessen("skizze_3")
	q.annehmen("skizze_4")
	_reden("faerber")
	_reden("hedda")
	q.abschliessen("skizze_4")
	_check("Skizzenbuch-Reihe fertig, Form 3 frei", q.ist_erledigt("skizze_4") and player.hat_blaupause("knauf", 1, 3))

	# --- Der Geist der Mühle ------------------------------------------------------
	q.annehmen("muehle_1")
	Game.time_of_day = 12.0
	await _hin("muehle")
	_check("Mühle am Tag zählt nicht", not q.ist_erledigt("muehle_1"))
	Game.time_of_day = 23.0
	await _warte(0.5)
	_check("Mühle bei Nacht", q.ist_erledigt("muehle_1") and q.ist_aktiv("muehle_2"))
	await _warte(0.4)
	_check("Geist erscheint", _besiegen("geist") == 1)
	if OS.get_cmdline_user_args().has("--bild"):
		var geist = welt.npc_knoten["geist_elric"]
		player.global_position = geist.global_position + Vector3(-1.5, 0.5, 4.5)
		player.cam_yaw = 0.25
		player.cam_pitch = -0.2
		Game.time_of_day = 20.3 # Dämmerung, damit man etwas sieht
		await _foto("quest_geist")
		Game.time_of_day = 23.0
	_check("Geist-NPC sichtbar", welt.npc_knoten["geist_elric"].is_interactable() and q.ist_aktiv("muehle_3"))
	_reden("geist_elric")
	_check("Untersuchung beginnt", q.ist_aktiv("muehle_4"))
	if OS.get_cmdline_user_args().has("--bild"):
		q.annehmen("neben_fische")
		q.annehmen("neben_banditen")
		hud.set_questlog_open(true)
		await _foto("quest_questbuch")
		hud.close_all_windows()
	for ort in ["hinweis_ring", "hinweis_oelkrug", "hinweis_schuldbuch"]: # beliebige Reihenfolge
		await _untersuchen(ort)
	_check("Drei Hinweise, Ring und Schuldbuch", q.ist_aktiv("muehle_5") and player.inventory.count("halber_siegelring") == 1
		and player.inventory.count("schuldbuch") == 1)
	for npc in ["wache", "witwe", "wirt"]:
		_reden(npc)
	_check("Befragung fertig, Vogt sichtbar", q.ist_aktiv("muehle_6") and welt.npc_knoten["vogt"].is_interactable())
	_reden("vogt")
	await _warte(0.4)
	_check("Vogt entlarvt: NPC weg, Gegner da", not welt.npc_knoten["vogt"].is_interactable() and _besiegen("vogt") == 1)
	await _warte(0.1)
	_check("Entscheidungsfenster offen", hud.dialog_ui.visible and q.bereit("muehle_6"))
	await _foto("quest_entscheidung")
	# Stand vor der Wahl merken, um beide Enden zu prüfen
	var vorher: Dictionary = q.to_save()
	var items_vorher: Dictionary = player.inventory.items.duplicate()
	var gold_vorher_wahl: int = player.gold
	var ansehen_vorher := int(player.ansehen_region.get("startgebiet", 0))
	q.abschliessen("muehle_6", 1) # töten
	hud.close_all_windows()
	_check("Töten: Schlüssel und Truhen-Quest", player.inventory.count("schluessel_vogt") == 1 and q.ist_aktiv("muehle_7b"))
	await _untersuchen("truhe_vogt")
	_check("Truhe: Gold und Ring", player.gold >= gold_vorher_wahl + 150 and player.inventory.count("schluessel_vogt") == 0)
	_reden("geist_elric")
	_check("Ende 1: Geist erlöst, Blaupause Hammerkopf", q.ist_erledigt("muehle_7b") and q.merker.has("geist_erloest")
		and player.hat_blaupause("hammerkopf", 1, 4) and not welt.npc_knoten["geist_elric"].is_interactable())
	q.from_save(vorher)
	player.inventory.items = items_vorher
	await _warte(0.1)
	hud.close_all_windows()
	q.abschliessen("muehle_6", 0) # Gefängnis
	_reden("wache")
	_reden("geist_elric")
	_check("Ende 2: Gefängnis gibt viel Regionsansehen", q.ist_erledigt("muehle_7a") and q.merker.has("vogt_gefangen")
		and int(player.ansehen_region.get("startgebiet", 0)) >= ansehen_vorher + 300)

	# --- Speichern und Laden, alte Spielstände -------------------------------------
	q.annehmen("neben_wachturm")
	await _hin("wachturm")
	var stand: Dictionary = player.to_save()
	SaveGame.save(get_tree(), PATH)
	q.from_save({})
	player.gold = 0
	player.blaupausen.clear()
	SaveGame.load_into(get_tree(), PATH)
	var neu: Dictionary = player.to_save()
	for key in ["quests", "gold", "blaupausen", "freischaltungen", "ansehen_region"]:
		_check("Speichern: %s gleich" % key, JSON.stringify(stand[key]) == JSON.stringify(neu[key]), "%s / %s" % [JSON.stringify(stand[key]), JSON.stringify(neu[key])] if JSON.stringify(stand[key]) != JSON.stringify(neu[key]) else "")
	_check("Laden: Fortschritt der laufenden Quest", q.ziel_fertig("neben_wachturm", 0) and not q.ziel_fertig("neben_wachturm", 1))
	SaveGame.delete(PATH)
	var alt: Dictionary = stand.duplicate(true)
	alt.erase("quests")
	alt.erase("blaupausen")
	alt.erase("freischaltungen")
	alt.erase("gold")
	alt["_version"] = 4
	player.from_save(alt)
	_check("Alter Spielstand behält Aussehen und alle Formen", player.freischaltungen.has("skizzenbuch") and player.hat_blaupause("schwertklinge", 2, 5))
	await _warte(0.1)
	_check("Alter Spielstand bekommt den Prolog", q.ist_aktiv("haupt_prolog_1"))

	print("AUTOTEST Quests: %d Fehler, Gold %d, Level %d, erledigt %d" % [fehler, player.gold, player.char_level, q.erledigt.size()])
	q.from_save(stand["quests"])
	get_tree().quit()
