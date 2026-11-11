class_name CharakterAussehen
extends RefCounted
## Aussehen eines Menschen als Dictionary: Standardwerte, Zufall in festen Grenzen,
## gespeicherte NPC-Gesichter. Regeln in data/charakter.json.

const DATEI := "res://data/charakter.json"
const NPC_DATEI := "res://data/npc_aussehen.json"
const NPC_DATEI_NUTZER := "user://npc_aussehen.json"

static var _daten: Dictionary


static func daten() -> Dictionary:
	if _daten.is_empty():
		_daten = JSON.parse_string(FileAccess.get_file_as_string(DATEI))
	return _daten


static func standard(mann := true) -> Dictionary:
	var a := {}
	for r in daten()["grundregler"]:
		a[r["id"]] = float(r["standard"])
	a["geschlecht"] = 1.0 if mann else 0.0
	a["herkunft"] = (daten()["herkunft"]["standard"] as Array).duplicate()
	a["regler"] = {}
	a["haut"] = daten()["hautfarben"][1]["farbe"]
	a["augen"] = daten()["augenfarben"][1]["farbe"]
	a["haar"] = "kurz" if mann else "lang"
	a["haar_farbe"] = daten()["haarfarben"][2]["farbe"]
	a["brauen"] = "normal"
	a["bart"] = "keiner"
	return a


static func ist_frau(a: Dictionary) -> bool:
	return float(a.get("geschlecht", 1.0)) < 0.5


## Zufälliges Aussehen in den Grenzen aus charakter.json.
## nur_gesicht: Körper (Geschlecht, Größe …) bleibt wie in basis.
static func zufall(rng: RandomNumberGenerator, basis: Dictionary = {}, nur_gesicht := false) -> Dictionary:
	var d := daten()
	var a := standard() if basis.is_empty() else basis.duplicate(true)
	if not nur_gesicht:
		for r in d["grundregler"]:
			var z = r["zufall"]
			if z is String and z == "geschlecht":
				if basis.is_empty():
					a["geschlecht"] = 1.0 if rng.randf() < 0.5 else 0.0
				continue
			a[r["id"]] = rng.randf_range(float(z[0]), float(z[1]))
	# Gesichtszüge: meist ein vorherrschender Typ mit etwas Beimischung
	var h := [rng.randf() * 0.35, rng.randf() * 0.35, rng.randf() * 0.35]
	h[rng.randi_range(0, 2)] += 0.7 + rng.randf() * 0.3
	a["herkunft"] = h
	var ez: Dictionary = d["einzelregler_zufall"]
	var regler := {}
	MenschDaten.laden()
	for r in MenschDaten.meta["regler"]:
		var id: String = r["id"]
		if id in ez["ohne"]:
			continue
		var streu: float = ez.get(r["gruppe"], ez["standard"])
		var v := (rng.randf() + rng.randf() + rng.randf() - 1.5) / 1.5 * streu * 2.0
		if float(r["min"]) >= 0.0:
			v = absf(v) * 0.6
		regler[id] = clampf(v, -float(ez["grenze"]), float(ez["grenze"]))
	a["regler"] = regler
	a["haut"] = _wahl(rng, d["hautfarben"])
	a["augen"] = _wahl(rng, d["augenfarben"])
	a["haar_farbe"] = _wahl(rng, d["haarfarben"])
	if float(a.get("alter", 0.0)) > 0.45 and rng.randf() < 0.6:
		a["haar_farbe"] = d["haarfarben"][9 + rng.randi_range(0, 1)]["farbe"]
	var frisuren := Mensch.frisuren(not ist_frau(a))
	if not frisuren.is_empty():
		a["haar"] = frisuren[rng.randi_range(0, frisuren.size() - 1)]
	var baerte := Mensch.baerte()
	a["bart"] = "keiner" if ist_frau(a) or baerte.is_empty() or rng.randf() < 0.45 else baerte[rng.randi_range(0, baerte.size() - 1)]
	return a


static func _wahl(rng: RandomNumberGenerator, liste: Array) -> String:
	return liste[rng.randi_range(0, liste.size() - 1)]["farbe"]


## Gespeicherte NPC-Gesichter: Liste aus {name, aussehen}.
static func npc_liste() -> Array:
	for pfad in [NPC_DATEI_NUTZER, NPC_DATEI]:
		if FileAccess.file_exists(pfad):
			var l = JSON.parse_string(FileAccess.get_file_as_string(pfad))
			if l is Array:
				return l
	return []


## Speichert ins Projekt (res://data, wenn aus dem Projektordner gestartet), sonst nach user://.
static func npc_speichern(name: String, a: Dictionary) -> String:
	var liste := npc_liste()
	liste.append({"name": name, "aussehen": a})
	var text := JSON.stringify(liste, "\t")
	for pfad in [NPC_DATEI, NPC_DATEI_NUTZER]:
		var f := FileAccess.open(pfad, FileAccess.WRITE)
		if f:
			f.store_string(text)
			f.close()
			return pfad
	return ""


## Ungefähre Körpergröße in cm (für die Anzeige).
static func groesse_cm(m: Mensch) -> int:
	if m.pos.is_empty():
		return 0
	var oben := -INF
	for k in MenschDaten.teil("koerper")["mh_index"]:
		oben = maxf(oben, m.pos[k].y)
	return roundi(oben * 100.0)
