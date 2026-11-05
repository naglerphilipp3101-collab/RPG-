class_name WaffenModell
extends RefCounted
## Modulare Waffen: jede Waffe besteht aus Teilen (Schwert: Klinge, Parierstange, Griff, Knauf).
## Jedes Tier bringt eigene Module in seinem Stil mit (modelle/<waffe>/<teil>_t<tier>_<form>.glb, erzeugt von
## blender/waffen.py): Iron schlicht, Palladium verziert, Mithril gerade und kantig, Glacialore aus Eis geschlagen,
## Sungold mit Flügeln und Gold, Darksteel zackig in Schwarz und Rot. Ein Modul trägt immer das Metall seines Tiers.
## Alle Teile liegen im selben Koordinatensystem, darum passt jedes Modul auf jedes andere, auch über Tiers hinweg.
## Die Klinge zeigt nach -Z, der Griff liegt am Ursprung. Die Teile sind nur Aussehen; die Werte der Waffe kommen
## weiter aus Rezept und Zufallswerten.

const ORDNER := "res://assets/waffen/modelle/"
const TIER_NAMEN := ["Iron", "Palladium", "Mithril", "Glacialore", "Sungold", "Darksteel"]

# Waffe -> Teile in Bau-Reihenfolge, mit deutschem Namen für die Oberfläche
const TEILE := {
	"schwert": {"klinge": "Klinge", "parier": "Parierstange", "griff": "Griff", "knauf": "Knauf"},
}

# Je Tier: Klingenmetall und Beschläge [Farbe, metallic, Rauheit], Leder, Leuchtfarbe, Edelstein
const TIERS := [
	{"klinge": [Color(0.5, 0.5, 0.5), 1.0, 0.45], "beschlag": [Color(0.22, 0.21, 0.2), 0.9, 0.6],
		"leder": Color(0.26, 0.15, 0.08), "leucht": Color(1.0, 0.5, 0.2), "stein": Color(0.5, 0.1, 0.05)},
	{"klinge": [Color(0.82, 0.82, 0.84), 1.0, 0.18], "beschlag": [Color(0.72, 0.6, 0.38), 1.0, 0.28],
		"leder": Color(0.16, 0.08, 0.05), "leucht": Color(1.0, 0.85, 0.6), "stein": Color(0.15, 0.3, 0.85)},
	{"klinge": [Color(0.68, 0.75, 0.86), 1.0, 0.24], "beschlag": [Color(0.42, 0.48, 0.58), 1.0, 0.35],
		"leder": Color(0.1, 0.12, 0.18), "leucht": Color(0.35, 0.65, 1.0), "stein": Color(0.3, 0.6, 1.0)},
	{"klinge": [Color(0.75, 0.85, 0.9), 1.0, 0.12], "beschlag": [Color(0.55, 0.66, 0.74), 1.0, 0.25],
		"leder": Color(0.45, 0.42, 0.38), "leucht": Color(0.3, 0.85, 1.0), "stein": Color(0.55, 0.88, 1.0),
		"eis": Color(0.55, 0.85, 0.85)},
	{"klinge": [Color(0.88, 0.86, 0.8), 1.0, 0.16], "beschlag": [Color(1.0, 0.72, 0.3), 1.0, 0.2],
		"leder": Color(0.86, 0.82, 0.72), "leucht": Color(1.0, 0.8, 0.4), "stein": Color(0.95, 0.55, 0.1)},
	{"klinge": [Color(0.05, 0.035, 0.035), 0.85, 0.3], "beschlag": [Color(0.22, 0.03, 0.03), 0.9, 0.35],
		"leder": Color(0.04, 0.03, 0.03), "leucht": Color(1.0, 0.08, 0.02), "stein": Color(0.85, 0.03, 0.02)},
]

static var _cache := {}


## Baut die Waffe aus Teilen als Kind von parent.
## auswahl: {teil: {"tier": int, "form": int}} wählt je Teil ein Modul; fehlende Teile bekommen das
## erste Modul von standard_tier.
## element_farbe färbt Leuchten und Kristall der Magiewaffen. Gibt false zurück, wenn es die Waffe nicht gibt.
static func zusammenbauen(waffe: String, auswahl: Dictionary, parent: Node3D, standard_tier := 1,
		element_farbe: Variant = null) -> bool:
	if not TEILE.has(waffe):
		return false
	var wurzel := Node3D.new()
	wurzel.name = waffe
	parent.add_child(wurzel)
	for teil: String in TEILE[waffe]:
		var w: Dictionary = auswahl.get(teil, {})
		var tier: int = clampi(int(w.get("tier", standard_tier)), 1, 6)
		var form: int = clampi(int(w.get("form", 1)), 1, formen(waffe, teil, tier))
		var pfad := "%s%s/%s_t%d_%d.glb" % [ORDNER, waffe, teil, tier, form]
		if not ResourceLoader.exists(pfad):
			continue
		var modell := (load(pfad) as PackedScene).instantiate() as Node3D
		modell.name = teil
		wurzel.add_child(modell)
		_materialien(modell, tier, element_farbe)
	return true


## Ganze Waffe aus den ersten Modulen eines Tiers.
static func erzeugen(waffe: String, tier: int, parent: Node3D, element_farbe: Variant = null) -> bool:
	return zusammenbauen(waffe, {}, parent, tier, element_farbe)


## Anzahl der Module eines Teils in einem Tier (zählt die Dateien einmal und merkt sie sich).
static func formen(waffe: String, teil: String, tier: int) -> int:
	var schluessel := "_n_%s_%s_%d" % [waffe, teil, tier]
	if not _cache.has(schluessel):
		var n := 0
		while ResourceLoader.exists("%s%s/%s_t%d_%d.glb" % [ORDNER, waffe, teil, tier, n + 1]):
			n += 1
		_cache[schluessel] = maxi(n, 1)
	return _cache[schluessel]


static func _materialien(knoten: Node, tier: int, element_farbe: Variant) -> void:
	if knoten is MeshInstance3D:
		var mi := knoten as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i)
			var name := m.resource_name if m else ""
			mi.set_surface_override_material(i, material(name, tier, element_farbe))
	for k in knoten.get_children():
		_materialien(k, tier, element_farbe)


static func material(name: String, tier: int, element_farbe: Variant = null) -> Material:
	var schluessel := "%s_%d_%s" % [name, tier, str(element_farbe)]
	if _cache.has(schluessel):
		return _cache[schluessel]
	var t: Dictionary = TIERS[tier - 1]
	var m := StandardMaterial3D.new()
	m.resource_name = name
	match name:
		"klinge", "beschlag":
			var w: Array = t[name]
			m.albedo_color = w[0]
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
		"sehne", "stoff":
			m.albedo_color = Color(0.82, 0.78, 0.66) if name == "sehne" else Color(0.6, 0.55, 0.45)
			m.roughness = 0.9
		"dunkel":
			m.albedo_color = Color(0.1, 0.1, 0.11)
			m.metallic = 0.6
			m.roughness = 0.5
		"leucht":
			var c: Color = element_farbe if element_farbe != null else t["leucht"]
			m.albedo_color = c
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 3.0
		"stein":
			var c: Color = t["stein"]
			m.albedo_color = c
			m.metallic = 0.2
			m.roughness = 0.05
			m.emission_enabled = true
			m.emission = c
			m.emission_energy_multiplier = 0.6
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
