shader_type spatial;
// Fotogescannter Bodenbewuchs (Poly Haven: Gras, Farn, Scharbockskraut, Löwenzahn) als MultiMesh.
// Texturen aus dem Scan, dazu Wind (stärker oben), Farbton je Biom (INSTANCE_CUSTOM.rgb) und zum Rand des
// Bewuchsbereichs flacher werdend, damit kein harter Rand entsteht.
render_mode cull_disabled;

uniform sampler2D farbe : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normale : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D orm : filter_linear_mipmap, repeat_enable;   // R Verdeckung, G Rauheit, B Metall
uniform sampler2D alpha_map : filter_linear_mipmap, repeat_enable;   // Transparenz (weiß = Blatt)
uniform bool mit_alpha = false;
uniform float hoehe = 0.3;          // Höhe des Modells (lokal) – für die Windstärke
uniform float wind_staerke = 0.07;
uniform float wind_tempo = 1.6;
uniform vec2 mitte;
uniform float radius = 35.0;

varying vec3 tint;

void vertex() {
	tint = INSTANCE_CUSTOM.rgb;
	vec3 welt = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float h = clamp(VERTEX.y / hoehe, 0.0, 1.0);
	float rand = 1.0 - smoothstep(radius * 0.7, radius, distance(welt.xz, mitte));
	VERTEX.y *= rand;
	float welle = sin(TIME * wind_tempo + welt.x * 0.35 + welt.z * 0.22) + 0.5 * sin(TIME * wind_tempo * 2.3 + welt.x * 1.1);
	VERTEX.x += welle * wind_staerke * h * h;
	VERTEX.z += welle * wind_staerke * 0.6 * h * h;
}

void fragment() {
	vec3 c = texture(farbe, UV).rgb;
	vec3 o = texture(orm, UV).rgb;
	ALBEDO = c * tint;
	NORMAL_MAP = texture(normale, UV).rgb;
	ROUGHNESS = o.g;
	AO = o.r;
	AO_LIGHT_AFFECT = 0.4;
	BACKLIGHT = c * 0.25;   // Licht scheint durch die Blätter
	if (mit_alpha) {
		ALPHA = texture(alpha_map, UV).r;
		ALPHA_SCISSOR_THRESHOLD = 0.5;
	}
}
