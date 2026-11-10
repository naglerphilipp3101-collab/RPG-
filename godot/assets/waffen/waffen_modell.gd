class_name WaffenModell
extends RefCounted
## Modulare Waffen: jede Waffe besteht aus Plätzen (Schwert: Klinge, Parierstange, Griff, Knauf), auf jeden Platz
## kommt ein Modul einer Modulart. Jedes Tier bringt eigene Module in seinem Stil mit
## (modelle/<modulart>/t<tier>_<form>.glb, erzeugt von blender/waffen.py): Iron schlicht, Palladium verziert,
## Mithril gerade und kantig, Glacialore aus Eis geschlagen, Sungold mit Flügeln und Gold, Darksteel zackig in Schwarz
## und Rot. Ein Modul trägt immer das Metall seines Tiers; Tiers dürfen gemischt werden.
## Geteilte Modularten (Knauf, Parierstange, Einhandgriff …) sind einmal modelliert und werden je Waffe verschoben
## und skaliert (WAFFEN). Die Klinge zeigt nach -Z, die Griffmitte liegt am Ursprung.
## Die Module sind nur Aussehen. Tier, Schaden und Name der Waffe kommen vom Hauptmodul (erster Platz).

const ORDNER := "res://assets/waffen/modelle/"
const TIER_NAMEN := ["Iron", "Palladium", "Mithril", "Glacialore", "Sungold", "Darksteel"]

# Waffe -> Platz -> [Modulart, Name des Platzes, Skalierung, Anker im Modell, Ziel in der Waffe, Drehung].
# Anker/Ziel als Zahl: Höhe in Metern entlang der Klinge (positiv = Richtung Spitze), sonst als Vector3 in Godot.
# Skalierung um den Anker, dann (optional) Drehung in Grad (Euler XYZ), dann zum Ziel verschoben.
# Der erste Platz ist das Hauptmodul. Fernkampfwaffen: oben +Y, Schussrichtung -Z, Hand am Ursprung.
const WAFFEN := {
	"schwert": {
		"klinge": ["schwertklinge", "Klinge"],
		"parier": ["parierstange", "Parierstange"],
		"griff": ["einhandgriff", "Griff"],
		"knauf": ["knauf", "Knauf"],
	},
	"grossschwert": {
		"klinge": ["grossschwertklinge", "Klinge"],
		"parier": ["parierstange", "Parierstange", Vector3(1.3, 1.2, 1.2), 0.09, 0.175],
		"griff": ["zweihandgriff", "Griff"],
		"knauf": ["knauf", "Knauf", Vector3(1.2, 1.2, 1.2), -0.076, -0.126],
	},
	"degen": {
		"klinge": ["degenklinge", "Klinge"],
		"korb": ["korb", "Korb"],
		"griff": ["einhandgriff", "Griff"],
		"knauf": ["knauf", "Knauf"],
	},
	"messer": {
		"klinge": ["messerklinge", "Klinge"],
		"parier": ["parierstange", "Parierstange", Vector3(0.6, 0.7, 0.6), 0.09, 0.072],
		"griff": ["einhandgriff", "Griff", Vector3(0.92, 0.92, 0.8), 0.0, 0.0],
		"knauf": ["knauf", "Knauf", Vector3(0.8, 0.8, 0.8), -0.076, -0.058],
	},
	"axt": {
		"kopf": ["axtkopf", "Axtkopf"],
		"stiel": ["stiel", "Stiel"],
		"ende": ["schaftende", "Schaftende", Vector3(1, 1, 1), 0.0, -0.3],
	},
	"hammer": {
		"kopf": ["hammerkopf", "Hammerkopf"],
		"stiel": ["stiel", "Stiel"],
		"ende": ["schaftende", "Schaftende", Vector3(1, 1, 1), 0.0, -0.3],
	},
	"speer": {
		"spitze": ["speerspitze", "Speerspitze"],
		"schaft": ["speerschaft", "Schaft"],
		"ende": ["schaftende", "Schaftende", Vector3(0.85, 0.85, 0.85), 0.0, -0.7],
	},
	"schild": {
		"koerper": ["schildkoerper", "Schildkörper"],
		"buckel": ["schildbuckel", "Schildbuckel"],
	},
	"bogen": {
		"arme": ["wurfarme", "Wurfarme"],
		"griff": ["bogengriff", "Griff"],
		"sehne": ["sehne", "Sehne"],
	},
	"armbrust": {
		"bogen": ["armbrustbogen", "Bogen"],
		"schaft": ["armbrustschaft", "Schaft"],
		# Bogensehne: liegt quer, ist kürzer (Enden bei ±0,4 statt ±0,68)
		"sehne": ["sehne", "Sehne", Vector3(1, 0.59, 1), Vector3(0, 0, 0.16), Vector3(0, 0.03, -0.33), Vector3(0, 0, 90)],
	},
	"muskete": {
		"lauf": ["musketenlauf", "Lauf"],
		"schaft": ["musketenschaft", "Schaft"],
		"schloss": ["schloss", "Schloss"],
	},
	"feuerstab": {
		"kopf": ["feuerkopf", "Flammenkopf"],
		"schaft": ["stabschaft", "Schaft"],
		"fokus": ["fokus", "Fokus"],
		"ende": ["schaftende", "Schaftende", Vector3(0.85, 0.85, 0.85), 0.0, -0.75],
	},
	"eisstab": {
		"kopf": ["eiskopf", "Eiskopf"],
		"schaft": ["stabschaft", "Schaft"],
		"fokus": ["fokus", "Fokus"],
		"ende": ["schaftende", "Schaftende", Vector3(0.85, 0.85, 0.85), 0.0, -0.75],
	},
	"blitzstab": {
		"kopf": ["blitzkopf", "Blitzkopf"],
		"schaft": ["stabschaft", "Schaft"],
		"fokus": ["fokus", "Fokus"],
		"ende": ["schaftende", "Schaftende", Vector3(0.85, 0.85, 0.85), 0.0, -0.75],
	},
	"lebensstab": {
		"kopf": ["lebenskopf", "Rankenkopf"],
		"schaft": ["stabschaft", "Schaft"],
		"fokus": ["fokus", "Fokus"],
		"ende": ["schaftende", "Schaftende", Vector3(0.85, 0.85, 0.85), 0.0, -0.75],
	},
	"leerenhandschuh": {
		# Panzerhandschuh: die Faust umschließt die Griffachse, Unterarm nach -X, Handrücken nach +Y (Godot)
		"handschuh": ["handschuh", "Handschuh"],
		# Klinge aus Magie, wächst per Fähigkeit vor den Knöcheln aus der Faust (+X), flache Seite nach oben (Handrücken)
		"klinge": ["magieklinge", "Magieklinge", Vector3.ONE, Vector3.ZERO, Vector3(0.03, 0.015, 0.0), Basis(Vector3(0, 0, 1), Vector3(0, 1, 0), Vector3(-1, 0, 0))],
		# Fokus in der Fassung auf dem Handrücken, längs zum Unterarm
		"fokus": ["fokus", "Fokus", Vector3(0.6, 0.6, 0.6), 0.97, Vector3(-0.022, 0.084, 0.0), Basis(Vector3(0, 1, 0), Vector3(0, 0, -1), Vector3(-1, 0, 0))],
	},
}

# Magiewaffen nach Element (weapons.json: model "staff"/"orb" + element)
const AUS_ELEMENT := {"fire": "feuerstab", "ice": "eisstab", "lightning": "blitzstab", "life": "lebensstab", "void": "leerenhandschuh"}

# Geschosse sind nicht modular: ein Modell je Tier (Spitze nach -Z, Mitte am Ursprung). Kugeln sind Hitscan.
const GESCHOSSE := ["pfeil", "bolzen"]

# Modellnamen aus weapons.json -> modulare Waffe
const AUS_SPIEL := {"sword": "schwert", "greatsword": "grossschwert", "rapier": "degen", "dagger": "messer",
	"greataxe": "axt", "warhammer": "hammer", "spear": "speer", "bow": "bogen", "crossbow": "armbrust", "musket": "muskete"}

# Je Material (Iron … Darksteel): Akzentfarbe, Klingenmetall und Beschläge [Farbe, metallic, Rauheit], Leder, Leuchtfarbe, Edelstein.
# Die Form eines Moduls (Tier seines Stils) und sein Material sind getrennt: jedes Modul lässt sich in jedem Material herstellen.
# Farbzonen (Philipp, 10.11.): "klinge" = Hauptfläche und "akzent" (Hohlkehlen, Zierlinien, Steine, Glimmen) lassen sich
# einfärben; Glanz, Rauheit und Schliffspuren des Materials bleiben. "beschlag" (Griff, Knauf, Parierstange, Rücken),
# Leder und Holz behalten immer die Grundfarbe des Materials.
const TIERS := [
	{"akzent": Color(0.28, 0.28, 0.3), "klinge": [Color(0.5, 0.5, 0.5), 1.0, 0.45], "beschlag": [Color(0.22, 0.21, 0.2), 0.9, 0.6],
		"leder": Color(0.26, 0.15, 0.08), "leucht": Color(1.0, 0.5, 0.2), "stein": Color(0.5, 0.1, 0.05), "wappen": Color(0.42, 0.3, 0.18)},
	{"akzent": Color(0.78, 0.62, 0.32), "klinge": [Color(0.82, 0.82, 0.84), 1.0, 0.18], "beschlag": [Color(0.72, 0.6, 0.38), 1.0, 0.28],
		"leder": Color(0.16, 0.08, 0.05), "leucht": Color(1.0, 0.85, 0.6), "stein": Color(0.15, 0.3, 0.85), "wappen": Color(0.1, 0.16, 0.42)},
	{"akzent": Color(0.32, 0.48, 0.78), "klinge": [Color(0.68, 0.75, 0.86), 1.0, 0.24], "beschlag": [Color(0.42, 0.48, 0.58), 1.0, 0.35],
		"leder": Color(0.1, 0.12, 0.18), "leucht": Color(0.35, 0.65, 1.0), "stein": Color(0.3, 0.6, 1.0), "wappen": Color(0.36, 0.42, 0.5)},
	{"akzent": Color(0.55, 0.88, 1.0), "klinge": [Color(0.75, 0.85, 0.9), 1.0, 0.12], "beschlag": [Color(0.72, 0.84, 0.92), 1.0, 0.22],
		"leder": Color(0.45, 0.42, 0.38), "leucht": Color(0.3, 0.85, 1.0), "stein": Color(0.55, 0.88, 1.0),
		"eis": Color(0.55, 0.85, 0.85)},
	{"akzent": Color(1.0, 0.7, 0.28), "klinge": [Color(0.88, 0.86, 0.8), 1.0, 0.16], "beschlag": [Color(1.0, 0.72, 0.3), 1.0, 0.2],
		"leder": Color(0.86, 0.82, 0.72), "leucht": Color(1.0, 0.8, 0.4), "stein": Color(0.95, 0.55, 0.1), "wappen": Color(0.88, 0.86, 0.8)},
	{"akzent": Color(0.6, 0.02, 0.02), "klinge": [Color(0.05, 0.035, 0.035), 0.85, 0.3], "beschlag": [Color(0.075, 0.055, 0.055), 0.9, 0.35],
		"leder": Color(0.04, 0.03, 0.03), "leucht": Color(1.0, 0.08, 0.02), "stein": Color(0.85, 0.03, 0.02), "wappen": Color(0.25, 0.03, 0.03)},
]

static var _cache := {}


## Baut die Waffe aus Modulen als Kind von parent.
## auswahl: {platz: {"tier": int, "form": int, "material": int, "farbe": Color, "akzent": Color}}; fehlende Plätze
## bekommen das erste Modul von standard_tier. "tier" wählt die Form (Stil), "material" das Metall (Standard: wie die Form),
## "farbe"/"akzent" färben Hauptfläche und Akzente (ohne Angabe: Farbe des Materials).
## element_farbe färbt Leuchten und Kristall der Magiewaffen. Gibt false zurück, wenn es die Waffe nicht gibt.
static func zusammenbauen(waffe: String, auswahl: Dictionary, parent: Node3D, standard_tier := 1,
		element_farbe: Variant = null) -> bool:
	if not WAFFEN.has(waffe):
		return false
	var wurzel := Node3D.new()
	wurzel.name = waffe
	parent.add_child(wurzel)
	for platz: String in WAFFEN[waffe]:
		var def: Array = WAFFEN[waffe][platz]
		var art: String = def[0]
		var w: Dictionary = auswahl.get(platz, {})
		var tier: int = clampi(int(w.get("tier", standard_tier)), 1, 6)
		var form: int = clampi(int(w.get("form", 1)), 1, formen(art, tier))
		var pfad := "%s%s/t%d_%d.glb" % [ORDNER, art, tier, form]
		if not ResourceLoader.exists(pfad):
			continue
		var modell := (load(pfad) as PackedScene).instantiate() as Node3D
		modell.name = platz
		if def.size() >= 5:
			var s: Vector3 = def[2]
			var anker := _punkt(def[3])
			var ziel := _punkt(def[4])
			var drehung := Basis.IDENTITY
			if def.size() >= 6:
				if def[5] is Basis:
					drehung = def[5]
				else:
					var g: Vector3 = def[5]
					drehung = Basis.from_euler(Vector3(deg_to_rad(g.x), deg_to_rad(g.y), deg_to_rad(g.z)))
			var b := drehung * Basis.from_scale(s)
			modell.transform = Transform3D(b, ziel - b * anker)
		wurzel.add_child(modell)
		var mat: int = clampi(int(w.get("material", tier)), 1, 6)
		_materialien(modell, mat, element_farbe, w.get("farbe"), w.get("akzent"))
	return true


## Höhe entlang der Klinge (Zahl, liegt in Godot bei z = -h) oder Punkt (Vector3).
static func _punkt(wert: Variant) -> Vector3:
	if wert is Vector3:
		return wert
	return Vector3(0, 0, -float(wert))


## Pfeil oder Bolzen eines Tiers als Kind von parent (für Geschosse, die stecken bleiben).
static func geschoss(art: String, tier: int, parent: Node3D) -> Node3D:
	tier = clampi(tier, 1, 6)
	var pfad := "%s%s/t%d_1.glb" % [ORDNER, art, tier]
	if not ResourceLoader.exists(pfad):
		return null
	var modell := (load(pfad) as PackedScene).instantiate() as Node3D
	parent.add_child(modell)
	_materialien(modell, tier, null)
	return modell


## Ganze Waffe aus den ersten Modulen eines Tiers.
static func erzeugen(waffe: String, tier: int, parent: Node3D, element_farbe: Variant = null) -> bool:
	return zusammenbauen(waffe, {}, parent, tier, element_farbe)


## Anzahl der Module einer Modulart in einem Tier (zählt die Dateien einmal und merkt sie sich).
static func formen(art: String, tier: int) -> int:
	var schluessel := "_n_%s_%d" % [art, tier]
	if not _cache.has(schluessel):
		var n := 0
		while ResourceLoader.exists("%s%s/t%d_%d.glb" % [ORDNER, art, tier, n + 1]):
			n += 1
		_cache[schluessel] = maxi(n, 1)
	return _cache[schluessel]


## Modulart eines Platzes.
static func modulart(waffe: String, platz: String) -> String:
	return WAFFEN[waffe][platz][0]


static func _materialien(knoten: Node, tier: int, element_farbe: Variant, farbe: Variant = null, akzent: Variant = null) -> void:
	if knoten is MeshInstance3D:
		var mi := knoten as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i)
			var name := m.resource_name if m else ""
			mi.set_surface_override_material(i, material(name, tier, element_farbe, farbe, akzent))
	for k in knoten.get_children():
		_materialien(k, tier, element_farbe, farbe, akzent)


## Material einer Fläche. tier = Material (1 Iron … 6 Darksteel); farbe/akzent = Spielerfarben (Color oder "#rrggbb").
static func material(name: String, tier: int, element_farbe: Variant = null, farbe: Variant = null, akzent: Variant = null) -> Material:
	if farbe is String:
		farbe = Color.html(farbe)
	if akzent is String:
		akzent = Color.html(akzent)
	if name == "eis" and tier != 4: # Eisbrocken der Glacialore-Formen sind in anderen Materialien aus Metall
		name = "beschlag"
	var schluessel := "%s_%d_%s_%s_%s" % [name, tier, str(element_farbe), str(farbe), str(akzent)]
	if _cache.has(schluessel):
		return _cache[schluessel]
	var t: Dictionary = TIERS[tier - 1]
	var m := StandardMaterial3D.new()
	m.resource_name = name
	match name:
		"klinge", "beschlag":
			var w: Array = t[name]
			m.albedo_color = farbe if name == "klinge" and farbe != null else w[0]
			m.metallic = w[1]
			m.roughness = w[2]
			m.roughness_texture = _rausch("geschliffen")
			m.uv1_triplanar = true
			m.uv1_scale = Vector3(3, 3, 40) if name == "klinge" else Vector3(12, 12, 12)
		"leder":
			m.albedo_color = t["leder"]
			m.roughness = 0.8
			m.albedo_texture = _rausch("leder")
			m.uv1_triplanar = true
			m.uv1_scale = Vector3(18, 18, 18)
		"holz":
			m.albedo_color = Color(0.5, 0.32, 0.17)
			m.roughness = 0.7
			m.albedo_texture = _rausch("holz")
			m.uv1_triplanar = true
			m.uv1_scale = Vector3(8, 8, 1.2)
		"eis": # Glacialore: durchscheinend wie Eis, leicht leuchtend
			var c: Color = t.get("eis", Color(0.55, 0.85, 0.85))
			m.albedo_color = Color(c.r, c.g, c.b, 0.82)
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_DEPTH_PRE_PASS
			m.roughness = 0.12
			m.metallic_specular = 0.9
			m.emission_enabled = true
			m.emission = c * 0.5
			m.emission_energy_multiplier = 0.5
			m.rim_enabled = true
			m.rim = 0.7
			m.rim_tint = 0.6
			m.normal_enabled = false
		"wappen": # Vorderseite des Schilds; später kommt hier die Bemalung der Fraktion hin
			m.albedo_color = t.get("wappen", Color(0.5, 0.5, 0.5))
			m.roughness = 0.65
			m.albedo_texture = _rausch("holz")
			m.uv1_triplanar = true
			m.uv1_scale = Vector3(3, 3, 3)
		"sehne", "stoff":
			m.albedo_color = Color(0.82, 0.78, 0.66) if name == "sehne" else Color(0.6, 0.55, 0.45)
			m.roughness = 0.9
		"dunkel":
			m.albedo_color = Color(0.1, 0.1, 0.11)
			m.metallic = 0.6
			m.roughness = 0.5
		"akzent": # Einlage aus poliertem Metall in der Akzentfarbe
			var c: Color = akzent if akzent != null else t["akzent"]
			m.albedo_color = c
			m.metallic = 0.85
			m.roughness = 0.22
			if tier == 6 or tier == 4: # Darksteel glimmt, Glacialore schimmert
				m.emission_enabled = true
				m.emission = c
				m.emission_energy_multiplier = 0.8 if tier == 6 else 0.3
		"leucht":
			var c: Color = element_farbe if element_farbe != null else (akzent if akzent != null else t["leucht"])
			m.albedo_color = c
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 3.0
		"stein":
			var c: Color = akzent if akzent != null else t["stein"]
			m.albedo_color = c
			m.metallic = 0.2
			m.roughness = 0.05
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 0.6
		"magie": # Klinge aus reiner Magie: durchscheinend, leuchtet stark in der Elementfarbe (sonst Akzentfarbe)
			var c: Color = element_farbe if element_farbe != null else (akzent if akzent != null else t["leucht"])
			m.albedo_color = Color(c.r, c.g, c.b, 0.7)
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 2.5
			m.cull_mode = BaseMaterial3D.CULL_DISABLED
		"kristall":
			var c: Color = element_farbe if element_farbe != null else t["stein"]
			m.albedo_color = Color(c.r, c.g, c.b, 0.75)
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_DEPTH_PRE_PASS
			m.roughness = 0.05
			m.metallic_specular = 1.0
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 1.2
			m.rim_enabled = true
			m.rim = 0.6
		_:
			m.albedo_color = Color(1, 0, 1)
	_cache[schluessel] = m
	return m


## Graustufen-Rauschen für Schliffspuren, Lederporen und Holzmaserung (einmal erzeugt, dann geteilt).
static func _rausch(art: String) -> Texture2D:
	var schluessel := "_tex_" + art
	if _cache.has(schluessel):
		return _cache[schluessel]
	var n := FastNoiseLite.new()
	var tex := NoiseTexture2D.new()
	tex.width = 256
	tex.height = 256
	tex.seamless = true
	tex.noise = n
	var verlauf := Gradient.new()
	match art:
		"geschliffen":
			n.frequency = 0.05
			n.fractal_octaves = 3
			verlauf.set_color(0, Color(0.75, 0.75, 0.75))
			verlauf.set_color(1, Color(1.25, 1.25, 1.25))
		"leder":
			n.noise_type = FastNoiseLite.TYPE_CELLULAR
			n.frequency = 0.08
			verlauf.set_color(0, Color(0.7, 0.7, 0.7))
			verlauf.set_color(1, Color(1.1, 1.1, 1.1))
		"holz":
			n.frequency = 0.02
			n.fractal_type = FastNoiseLite.FRACTAL_RIDGED
			verlauf.set_color(0, Color(0.65, 0.65, 0.65))
			verlauf.set_color(1, Color(1.1, 1.1, 1.1))
	tex.color_ramp = verlauf
	_cache[schluessel] = tex
	return tex
