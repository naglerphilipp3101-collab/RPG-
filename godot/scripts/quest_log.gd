extends RefCounted
## Questbuch des Spielers: laufende und erledigte Quests, Merker aus Entscheidungen, verfolgte Quest.
## Alle Quests stehen in data/quests/*.json (geladen von Game.quests); hier steckt nur die Logik.
##
## Ziel-Arten: toeten (Gegnertyp), sammeln (Item in der Tasche), abgeben (Item an NPC), besuchen (Ort),
## untersuchen (Ort mit F), reden (NPC), herstellen (Rezept-Ergebnis, optional mit Form).
## Ziele laufen nacheinander ab, außer die Quest hat "reihenfolge": "beliebig".
## Eine Quest ohne Geber ("geber": "") startet von selbst, sobald ihre Bedingungen erfüllt sind.

signal geaendert
signal wahl_noetig(quest_id: String) # Quest ohne Abgabe-NPC mit Entscheidung: Fenster öffnen

const ARTEN := {
	"haupt": "Hauptquest", "stimme": "Stimme des Splitters", "lore": "Questreihe", "fraktion": "Fraktion",
	"blaupause": "Blaupause", "neben": "Nebenaufgabe",
}
const ART_REIHENFOLGE := ["haupt", "stimme", "lore", "fraktion", "blaupause", "neben"]
const ART_FARBEN := {
	"haupt": Color(1.0, 0.8, 0.35), "stimme": Color(0.75, 0.55, 1.0), "lore": Color(0.55, 0.8, 1.0),
	"fraktion": Color(1.0, 0.5, 0.45), "blaupause": Color(0.95, 0.65, 0.35), "neben": Color(0.85, 0.85, 0.85),
}

var player = null
var aktiv: Dictionary = {}     # Quest-id -> {"fortschritt": [int je Ziel]}
var erledigt: Dictionary = {}  # Quest-id -> gewählte Option (-1 = keine Wahl)
var merker: Dictionary = {}    # Name -> true
var verfolgt := ""             # Quest, deren Ziel Kompass und Anzeige zeigen


func _init(p) -> void:
	player = p


# --- Abfragen ---------------------------------------------------------------

static func quest(id: String) -> Dictionary:
	return Game.quests.get(id, {})


static func art_name(id: String) -> String:
	return ARTEN.get(String(quest(id).get("art", "neben")), "Quest")


func ist_aktiv(id: String) -> bool:
	return aktiv.has(id)


func ist_erledigt(id: String) -> bool:
	return erledigt.has(id)


## Prüft einen Bedingungsblock (Quests, NPC-Sichtbarkeit):
## level, quests (alle erledigt), nicht_quests, merker (alle gesetzt), nicht_merker, aktiv (Quest läuft).
func bedingungen_ok(b: Dictionary) -> bool:
	if player != null and int(player.char_level) < int(b.get("level", 1)):
		return false
	for id in b.get("quests", []):
		if not erledigt.has(id):
			return false
	for id in b.get("nicht_quests", []):
		if erledigt.has(id):
			return false
	for m in b.get("merker", []):
		if not merker.has(m):
			return false
	for m in b.get("nicht_merker", []):
		if merker.has(m):
			return false
	for id in b.get("aktiv", []):
		if not aktiv.has(id):
			return false
	return true


func kann_annehmen(id: String) -> bool:
	var q := quest(id)
	if q.is_empty() or aktiv.has(id) or erledigt.has(id):
		return false
	return bedingungen_ok(q.get("bedingungen", {}))


## Quests, die dieser NPC gerade anbietet.
func angebote(npc_id: String) -> Array:
	var liste: Array = []
	for id in Game.quests:
		if String(quest(id).get("geber", "")) == npc_id and npc_id != "" and kann_annehmen(id):
			liste.append(id)
	return liste


## Wer die Quest entgegennimmt ("" = schließt sich von selbst ab).
static func abgabe_npc(id: String) -> String:
	var q := quest(id)
	return String(q.get("abgabe", q.get("geber", "")))


func ziele(id: String) -> Array:
	return quest(id).get("ziele", [])


func ziel_menge(ziel: Dictionary) -> int:
	return maxi(int(ziel.get("anzahl", 1)), 1)


## Fortschritt eines Ziels (sammeln zählt die Tasche, alles andere ist gespeichert).
func fortschritt(id: String, i: int) -> int:
	var ziel: Dictionary = ziele(id)[i]
	if String(ziel.get("art", "")) == "sammeln" and player != null:
		return mini(player.inventory.count(String(ziel.get("item", ""))), ziel_menge(ziel))
	var f: Array = aktiv.get(id, {}).get("fortschritt", [])
	return int(f[i]) if i < f.size() else 0


func ziel_fertig(id: String, i: int) -> bool:
	return fortschritt(id, i) >= ziel_menge(ziele(id)[i])


## Ist das Ziel gerade dran? (nacheinander: nur das erste offene; beliebig: alle offenen)
func ziel_offen(id: String, i: int) -> bool:
	if not aktiv.has(id) or ziel_fertig(id, i):
		return false
	if String(quest(id).get("reihenfolge", "nacheinander")) == "beliebig":
		return true
	for k in i:
		if not ziel_fertig(id, k):
			return false
	return true


func alle_ziele_fertig(id: String) -> bool:
	for i in ziele(id).size():
		if not ziel_fertig(id, i):
			return false
	return true


## Fertig und wartet auf die Abgabe bei einem NPC.
func bereit(id: String) -> bool:
	return aktiv.has(id) and alle_ziele_fertig(id)


## Alle offenen Ziele aller laufenden Quests: [{quest, index, ziel}]
func offene_ziele() -> Array:
	var liste: Array = []
	for id in aktiv:
		var z := ziele(id)
		for i in z.size():
			if ziel_offen(id, i):
				liste.append({"quest": id, "index": i, "ziel": z[i]})
	return liste


## Anzeigetext eines Ziels mit Fortschritt.
func ziel_text(id: String, i: int) -> String:
	var ziel: Dictionary = ziele(id)[i]
	var text := String(ziel.get("text", ""))
	var menge := ziel_menge(ziel)
	if text == "":
		match String(ziel.get("art", "")):
			"toeten":
				text = "%s besiegen" % String(Game.enemies.get(ziel.get("gegner", ""), {}).get("name", ziel.get("gegner", "")))
			"sammeln":
				text = "%s sammeln" % Game.item_name(String(ziel.get("item", "")))
			"abgeben":
				text = "%s zu %s bringen" % [Game.item_name(String(ziel.get("item", ""))), npc_name(String(ziel.get("npc", "")))]
			"besuchen":
				text = "%s aufsuchen" % ort_name(String(ziel.get("ort", "")))
			"untersuchen":
				text = "%s untersuchen" % ort_name(String(ziel.get("ort", "")))
			"reden":
				text = "Mit %s reden" % npc_name(String(ziel.get("npc", "")))
			"herstellen":
				text = "%s herstellen" % Game.item_name(String(ziel.get("item", "")))
	if menge > 1:
		text += "  %d/%d" % [fortschritt(id, i), menge]
	return text


static func npc_name(npc_id: String) -> String:
	return String(Game.npcs.get(npc_id, {}).get("name", npc_id))


static func ort_name(ort_id: String) -> String:
	return String(Game.quest_orte.get(ort_id, {}).get("name", ort_id))


## Quests, die Folge einer anderen sind (auch je Entscheidung). Ohne Geber starten sie nur über ihre Vorgängerin.
static var _folge: Dictionary = {}


static func folge_ziele() -> Dictionary:
	if _folge.is_empty():
		_folge["_"] = true # auch ohne Folgequests nur einmal rechnen
		for id in Game.quests:
			var q: Dictionary = Game.quests[id]
			if String(q.get("folgequest", "")) != "":
				_folge[String(q["folgequest"])] = true
			for o in q.get("wahl", {}).get("optionen", []):
				if String(o.get("folgequest", "")) != "":
					_folge[String(o["folgequest"])] = true
	return _folge


# --- Annehmen, Fortschritt, Abschluss ---------------------------------------

func annehmen(id: String) -> bool:
	if not kann_annehmen(id):
		return false
	var q := quest(id)
	var f: Array = []
	f.resize(ziele(id).size())
	f.fill(0)
	aktiv[id] = {"fortschritt": f}
	if verfolgt == "" or not aktiv.has(verfolgt) or _wichtiger(id, verfolgt):
		verfolgt = id
	_belohnung_geben(q.get("beim_annehmen", {}), false)
	if player != null:
		player.notify.emit("Neue Quest: " + String(q.get("titel", id)), ART_FARBEN.get(q.get("art", "neben"), Color.WHITE))
	_pruefen()
	return true


## Hauptquest vor Questreihen vor Nebenaufgaben (für die automatische Verfolgung).
func _wichtiger(a: String, b: String) -> bool:
	return ART_REIHENFOLGE.find(String(quest(a).get("art", "neben"))) < ART_REIHENFOLGE.find(String(quest(b).get("art", "neben")))


func abbrechen(id: String) -> bool:
	if not aktiv.has(id) or String(quest(id).get("art", "")) == "haupt":
		return false
	aktiv.erase(id)
	if verfolgt == id:
		verfolgt = _naechste_verfolgung()
	geaendert.emit()
	return true


func _naechste_verfolgung() -> String:
	var beste := ""
	for id in aktiv:
		if beste == "" or _wichtiger(id, beste):
			beste = id
	return beste


## Ein Ereignis zählt für alle offenen Ziele dieser Art mit passendem Wert (Gegner, Item, Ort, NPC).
## extra: zusätzliche Angaben, z. B. {"form": 2} beim Herstellen.
func ereignis(art: String, wert: String, menge := 1, extra: Dictionary = {}) -> Array:
	var gesprochen: Array = [] # Sätze, die NPCs/Orte dabei sagen
	var geaendert_ := false
	for eintrag in offene_ziele():
		var ziel: Dictionary = eintrag["ziel"]
		if String(ziel.get("art", "")) != art:
			continue
		var schluessel: String = {"toeten": "gegner", "abgeben": "npc", "besuchen": "ort", "untersuchen": "ort",
			"reden": "npc", "herstellen": "item", "sammeln": "item"}.get(art, "")
		if String(ziel.get(schluessel, "")) != wert:
			continue
		if art == "herstellen" and int(ziel.get("form", 0)) > int(extra.get("form", 1)):
			continue
		if art == "besuchen" and not _zeit_passt(ziel):
			continue
		var id: String = eintrag["quest"]
		var i: int = eintrag["index"]
		var n := menge
		if art == "untersuchen" and String(ziel.get("braucht", "")) != "":
			if player.inventory.count(String(ziel["braucht"])) <= 0:
				gesprochen.append("Dafür brauchst du: " + Game.item_name(String(ziel["braucht"])))
				continue
			player.inventory.remove(String(ziel["braucht"]), 1)
		if art == "abgeben":
			var item := String(ziel.get("item", ""))
			var fehlt := ziel_menge(ziel) - fortschritt(id, i)
			var hat: int = player.inventory.count(item)
			if hat <= 0:
				continue
			n = mini(hat, fehlt)
			player.inventory.remove(item, n)
		var f: Array = aktiv[id]["fortschritt"]
		f[i] = mini(int(f[i]) + n, ziel_menge(ziel))
		geaendert_ = true
		if ziel_fertig(id, i):
			_ziel_erreicht(id, i, gesprochen)
	if geaendert_:
		_pruefen()
	return gesprochen


func _zeit_passt(ziel: Dictionary) -> bool:
	match String(ziel.get("zeit", "")):
		"nacht":
			return Game.time_of_day >= 20.0 or Game.time_of_day < 5.0
		"tag":
			return Game.time_of_day >= 6.0 and Game.time_of_day < 20.0
	return true


func _ziel_erreicht(id: String, i: int, gesprochen: Array) -> void:
	var ziel: Dictionary = ziele(id)[i]
	if ziel.has("sagt"):
		gesprochen.append(String(ziel["sagt"]))
	if String(ziel.get("merker", "")) != "":
		merker[String(ziel["merker"])] = true
	var b := {}
	if ziel.has("gibt"):
		b["items"] = ziel["gibt"]
	if ziel.has("gold"):
		b["gold"] = ziel["gold"]
	_belohnung_geben(b, false)
	if player != null and String(ziel.get("art", "")) != "reden":
		player.notify.emit("Ziel erreicht: " + ziel_text(id, i).split("  ")[0], Color(0.75, 0.9, 0.6))


## Nach jeder Änderung: Quests ohne Abgabe-NPC abschließen, selbststartende Quests annehmen.
func _pruefen() -> void:
	for id in aktiv.keys():
		if bereit(id) and abgabe_npc(id) == "":
			if quest(id).has("wahl"):
				if not aktiv[id].get("wahl_offen", false):
					aktiv[id]["wahl_offen"] = true
					wahl_noetig.emit(id)
			else:
				abschliessen(id)
				return # abschliessen ruft _pruefen erneut auf
	for id in Game.quests:
		if String(quest(id).get("geber", "x")) == "" and not folge_ziele().has(id) and kann_annehmen(id):
			annehmen(id)
			return
	geaendert.emit()


## Gibt die Quest ab. option = gewählte Antwort bei Quests mit "wahl" (-1 sonst).
func abschliessen(id: String, option := -1) -> String:
	if not bereit(id):
		return ""
	var q := quest(id)
	var optionen: Array = q.get("wahl", {}).get("optionen", [])
	if not optionen.is_empty() and (option < 0 or option >= optionen.size()):
		return ""
	aktiv.erase(id)
	erledigt[id] = option
	var ergebnis := ""
	var folge := String(q.get("folgequest", ""))
	if option >= 0:
		var o: Dictionary = optionen[option]
		for m in o.get("merker", []):
			merker[String(m)] = true
		_belohnung_geben(o.get("belohnung", {}), true, String(q.get("region", "")))
		ergebnis = String(o.get("ergebnis", ""))
		folge = String(o.get("folgequest", folge))
	_belohnung_geben(q.get("belohnung", {}), true, String(q.get("region", "")))
	if player != null:
		player.notify.emit("Quest abgeschlossen: " + String(q.get("titel", id)), Color(1.0, 0.85, 0.4))
	if verfolgt == id:
		verfolgt = ""
	# Folgequest mit Geber erscheint dort; ohne Geber startet sie in _pruefen von selbst
	if folge != "" and String(quest(folge).get("geber", "")) == "" and kann_annehmen(folge):
		annehmen(folge)
	if verfolgt == "":
		verfolgt = _naechste_verfolgung()
	_pruefen()
	return ergebnis


## Belohnung: ep, gold, region_ansehen, fraktion_ansehen {fraktion: n}, items {id: n}, blaupausen [..], freischalten [..]
func _belohnung_geben(b: Dictionary, quest_abschluss: bool, region := "") -> void:
	if player == null or b.is_empty():
		return
	player.quest_belohnung(b, region if quest_abschluss else String(b.get("region", "")))


## Text der Belohnung für Questlog und Gesprächsfenster.
static func belohnung_text(b: Dictionary) -> String:
	var teile: Array = []
	if int(b.get("ep", 0)) > 0:
		teile.append("%d EP" % int(b["ep"]))
	if int(b.get("gold", 0)) > 0:
		teile.append("%d Gold" % int(b["gold"]))
	if int(b.get("region_ansehen", 0)) > 0:
		teile.append("%d Regionsansehen" % int(b["region_ansehen"]))
	var fa: Dictionary = b.get("fraktion_ansehen", {})
	for f in fa:
		teile.append("%d Ansehen (%s)" % [int(fa[f]), f])
	var items: Dictionary = b.get("items", {})
	for id in items:
		teile.append("%d× %s" % [int(items[id]), Game.item_name(id)])
	for bp in b.get("blaupausen", []):
		teile.append("Blaupause: " + blaupause_name(String(bp)))
	return ", ".join(teile)


## "parierstange_t1_f2" -> "Parierstange (Iron, Form 2)", "*_t1_f3" -> "alle Iron-Teile in Form 3"
static func blaupause_name(bp: String) -> String:
	var teile := bp.split("_")
	if teile.size() < 3:
		return bp
	var form := teile[teile.size() - 1].trim_prefix("f")
	var tier := clampi(int(teile[teile.size() - 2].trim_prefix("t")), 1, 6)
	var art := "_".join(teile.slice(0, teile.size() - 2))
	var tier_name: String = WaffenModell.TIER_NAMEN[tier - 1]
	if art == "*":
		return "alle %s-Teile in Form %s" % [tier_name, form]
	return "%s (%s, Form %s)" % [art.capitalize(), tier_name, form]


# --- Speichern ----------------------------------------------------------------

func to_save() -> Dictionary:
	return {"aktiv": aktiv.duplicate(true), "erledigt": erledigt.duplicate(), "merker": merker.keys(), "verfolgt": verfolgt}


func from_save(data: Dictionary) -> void:
	aktiv.clear()
	erledigt.clear()
	merker.clear()
	var gespeichert: Dictionary = data.get("aktiv", {})
	for id in gespeichert:
		if not Game.quests.has(id):
			continue # Quest gibt es nicht mehr
		var f: Array = []
		var alt: Array = gespeichert[id].get("fortschritt", [])
		for i in ziele(id).size():
			f.append(int(alt[i]) if i < alt.size() else 0)
		aktiv[id] = {"fortschritt": f}
	var fertig: Dictionary = data.get("erledigt", {})
	for id in fertig:
		erledigt[id] = int(fertig[id])
	for m in data.get("merker", []):
		merker[String(m)] = true
	verfolgt = String(data.get("verfolgt", ""))
	if not aktiv.has(verfolgt):
		verfolgt = _naechste_verfolgung()
	_pruefen()
