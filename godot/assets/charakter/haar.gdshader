shader_type spatial;
// Haarkarten (Haare, Brauen, Wimpern) aus MakeHuman: Form aus dem Alphakanal der Textur,
// Farbe frei wählbar; die Helligkeitsstruktur der Textur bleibt als Strähnen erhalten.
render_mode cull_disabled, depth_draw_opaque;

uniform sampler2D textur : source_color, filter_linear_mipmap_anisotropic;
uniform vec3 farbe : source_color = vec3(0.29, 0.19, 0.13);
uniform float hell = 0.15;          // mittlere Helligkeit der Textur
uniform float struktur = 0.7;       // wie stark die Strähnen der Textur sichtbar sind
uniform float alpha_grenze = 0.4;
uniform float rauheit = 0.5;

void fragment() {
	vec4 t = texture(textur, UV);
	float lum = dot(t.rgb, vec3(0.3, 0.55, 0.15));
	float detail = hell > 0.02 ? clamp(lum / hell, 0.4, 1.45) : 1.0;
	// helle Farben (Grau, Weiß) nicht überstrahlen lassen
	ALBEDO = min(farbe * mix(1.0, detail, struktur), vec3(0.78));
	ALPHA = t.a;
	ALPHA_SCISSOR_THRESHOLD = alpha_grenze;
	ALPHA_ANTIALIASING_EDGE = 0.25;
	ROUGHNESS = rauheit;
	SPECULAR = 0.35;
	BACKLIGHT = farbe * 0.25;
}
