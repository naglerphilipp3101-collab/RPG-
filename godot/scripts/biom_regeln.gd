@tool
class_name BiomRegeln
## Liest data/biome.json: 6 Biome (Wald, Wiese, Fluss, Strand, Berg, Moor) plus Stadt mit ihren Regeln für
## Bodentextur, Bäume, Büsche, Sammelpflanzen, Bodenobjekte und Bodenbewuchs.
## Die Biome des Weltgenerators werden über "generator" auf diese Biome (und eine Variante) abgebildet.
## Genutzt von scripts/natur.gd, scripts/gras.gd und dem Weltimport (Bodentexturen).

const PFAD := "res://data/biome.json"

static var _daten := {}


## Alles vorbereitet: {"texturen": [Namen], "generator": {Generator-ID (int): Regel}, "fluss": Regel, "stadt": Regel}.
## Eine Regel ist das Biom mit seiner Variante zusammengeführt, dazu "biom" (Name) und "textur" (Terrain3D-ID, -1 = nicht ändern).
static func laden() -> Dictionary:
	if not _daten.is_empty():
		return _daten
	var roh: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PFAD))
	var texturen: Array = roh["texturen"]
	var generator := {}
	for k in roh["generator"]:
		if String(k).begins_with("_"):
			continue
		var paar: Array = roh["generator"][k]
		generator[int(k)] = regel(roh, texturen, paar[0], paar[1])
	_daten = {"texturen": texturen, "generator": generator,
		"fluss": regel(roh, texturen, "fluss", ""), "stadt": regel(roh, texturen, "stadt", "")}
	return _daten


static func regel(roh: Dictionary, texturen: Array, biom: String, variante: String) -> Dictionary:
	var b: Dictionary = roh["biome"][biom]
	var r := b.duplicate(true)
	r.erase("varianten")
	if variante != "":
		var v: Dictionary = b.get("varianten", {}).get(variante, {})
		for k in v:
			r[k] = v[k] # Varianten ersetzen ganze Einträge (z. B. die Baumarten)
	r["biom"] = biom
	r["variante"] = variante
	r["textur"] = texturen.find(String(r.get("boden", "")))
	return r


## Terrain3D-ID einer Bodentextur nach Name (-1, wenn es sie nicht gibt)
static func textur_id(name_: String) -> int:
	return (laden()["texturen"] as Array).find(name_)
