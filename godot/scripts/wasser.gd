extends RefCounted
## Wasser-Materialien (Shader scripts/wasser.gdshader) mit erzeugten Wellen- und Schaumtexturen.

const WasserShader := preload("res://scripts/wasser.gdshader")

static var _texturen := {}


static func _rauschen(name: String, frequenz: float, normal: bool) -> NoiseTexture2D:
	if _texturen.has(name):
		return _texturen[name]
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = frequenz
	noise.fractal_octaves = 4
	noise.seed = name.hash()
	var t := NoiseTexture2D.new()
	t.width = 512
	t.height = 512
	t.seamless = true
	t.as_normal_map = normal
	t.bump_strength = 6.0
	t.generate_mipmaps = true
	t.noise = noise
	_texturen[name] = t
	return t


## art: "meer", "see" oder "fluss"
static func material(art: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = WasserShader
	m.set_shader_parameter("wellen1", _rauschen("wellen1", 0.012, true))
	m.set_shader_parameter("wellen2", _rauschen("wellen2", 0.02, true))
	m.set_shader_parameter("schaum_muster", _rauschen("schaum", 0.03, false))
	match art:
		"see":
			m.set_shader_parameter("farbe_flach", Color(0.2, 0.42, 0.36))
			m.set_shader_parameter("farbe_tief", Color(0.04, 0.16, 0.18))
			m.set_shader_parameter("tiefe_farbe", 6.0)
			m.set_shader_parameter("wellen_staerke", 0.3)
			m.set_shader_parameter("schaum_breite", 0.4)
		"fluss":
			m.set_shader_parameter("farbe_flach", Color(0.22, 0.42, 0.38))
			m.set_shader_parameter("farbe_tief", Color(0.06, 0.2, 0.22))
			m.set_shader_parameter("tiefe_farbe", 2.5)
			m.set_shader_parameter("sichttiefe", 1.2)
			m.set_shader_parameter("wellen_staerke", 0.45)
			m.set_shader_parameter("schaum_breite", 0.35)
			m.set_shader_parameter("wellen_skala", 0.12)
	return m
