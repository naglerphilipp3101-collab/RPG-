class_name WaffenModell
extends RefCounted
## Lädt die Blender-Waffenmodelle (modelle/<form>.glb) und vergibt die Materialien nach Tier (gleiche Form in allen Tiers).
## Die Modelle tragen nur Materialnamen (klinge, beschlag, leder, holz, leucht, stein, kristall, sehne, stoff, dunkel);
## Farben und Glanz kommen von hier. Die Klinge zeigt nach -Z, der Griff liegt am Ursprung.

const ORDNER := "res://assets/waffen/modelle/"
const TIER_NAMEN := ["Iron", "Palladium", "Mithril", "Glacialore", "Sungold", "Darksteel"]

# Je Tier: Klingenmetall, Beschläge, Leder, Leuchtfarbe, Edelstein
const TIERS := [
	{"klinge": [Color(0.5, 0.5, 0.5), 1.0, 0.45], "beschlag": [Color(0.2, 0.19, 0.18), 0.9, 0.6],
		"leder": Color(0.26, 0.15, 0.08), "leucht": Color(1.0, 0.5, 0.2), "stein": Color(0.5, 0.1, 0.05)},
	{"klinge": [Color(0.8, 0.8, 0.82), 1.0, 0.2], "beschlag": [Color(0.62, 0.42, 0.24), 1.0, 0.35],
		"leder": Color(0.2, 0.11, 0.06), "leucht": Color(1.0, 0.85, 0.6), "stein": Color(0.2, 0.4, 0.8)},
	{"klinge": [Color(0.7, 0.78, 0.9), 1.0, 0.16], "beschlag": [Color(0.32, 0.42, 0.62), 1.0, 0.3],
		"leder": Color(0.1, 0.12, 0.2), "leucht": Color(0.35, 0.65, 1.0), "stein": Color(0.3, 0.6, 1.0)},
	{"klinge": [Color(0.82, 0.9, 0.95), 1.0, 0.1], "beschlag": [Color(0.55, 0.66, 0.74), 1.0, 0.25],
		"leder": Color(0.85, 0.85, 0.82), "leucht": Color(0.3, 0.85, 1.0), "stein": Color(0.55, 0.88, 1.0)},
	{"klinge": [Color(0.86, 0.83, 0.76), 1.0, 0.18], "beschlag": [Color(1.0, 0.71, 0.29), 1.0, 0.22],
		"leder": Color(0.38, 0.06, 0.04), "leucht": Color(1.0, 0.45, 0.08), "stein": Color(0.9, 0.08, 0.02)},
	{"klinge": [Color(0.07, 0.07, 0.08), 0.85, 0.28], "beschlag": [Color(0.04, 0.04, 0.05), 0.8, 0.4],
		"leder": Color(0.05, 0.04, 0.05), "leucht": Color(0.65, 0.1, 1.0), "stein": Color(0.5, 0.05, 0.9)},
]

static var _cache := {}


## Baut die Waffe als Kind von parent. tier 1–6. element (fire/ice/…) färbt Leuchten und Kristall der Magiewaffen.
## Gibt false zurück, wenn es das Modell nicht gibt (dann bleibt der Platzhalter).
static func erzeugen(form: String, tier: int, parent: Node3D, element_farbe: Variant = null) -> bool:
	tier = clampi(tier, 1, 6)
	var pfad := "%s%s.glb" % [ORDNER, form]
	if not ResourceLoader.exists(pfad):
		return false
	var szene: PackedScene = load(pfad)
	var modell := szene.instantiate() as Node3D
	parent.add_child(modell)
	_materialien(modell, tier, element_farbe)
	return true


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
