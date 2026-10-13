shader_type spatial;
// Wasser für Meer, Seen und Flüsse: zwei wandernde Wellen-Normalenkarten, Farbe nach Wassertiefe
// (aus dem Tiefenpuffer: Abstand Wasseroberfläche -> Boden), Schaum am Ufer, durchsichtig im Flachen.
render_mode blend_mix, depth_draw_always, cull_disabled, specular_schlick_ggx;

uniform vec3 farbe_flach : source_color = vec3(0.17, 0.5, 0.52);
uniform vec3 farbe_tief : source_color = vec3(0.03, 0.15, 0.26);
uniform float tiefe_farbe = 7.0;      // Meter bis zur tiefen Farbe
uniform float sichttiefe = 2.5;       // Meter, ab denen das Wasser undurchsichtig ist
uniform vec3 schaum_farbe : source_color = vec3(0.9, 0.95, 0.97);
uniform float schaum_breite = 0.3;    // Meter Wassertiefe, in denen Schaum entsteht
uniform float wellen_skala = 0.045;   // Wiederholungen je Meter
uniform float wellen_staerke = 0.55;
uniform vec2 stroemung = vec2(0.0);   // zusätzliche Fließrichtung (Flüsse), Meter je Sekunde
uniform sampler2D wellen1 : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D wellen2 : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D schaum_muster : filter_linear_mipmap, repeat_enable;
uniform sampler2D tiefe_puffer : hint_depth_texture, filter_linear_mipmap;

varying vec3 welt_pos;

void vertex() {
	welt_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = welt_pos.xz - stroemung * TIME;
	vec3 n1 = texture(wellen1, p * wellen_skala + TIME * vec2(0.013, 0.008)).rgb;
	vec3 n2 = texture(wellen2, p * wellen_skala * 1.9 + TIME * vec2(-0.011, 0.015)).rgb;
	NORMAL_MAP = normalize(n1 + n2 - 1.0);
	NORMAL_MAP_DEPTH = wellen_staerke;

	// Abstand zum Boden hinter dem Wasser (lineare Tiefe aus dem Tiefenpuffer)
	float d = textureLod(tiefe_puffer, SCREEN_UV, 0.0).r;
	vec4 sicht = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, d, 1.0);
	sicht.xyz /= sicht.w;
	float tiefe = max(VERTEX.z - sicht.z, 0.0);
	// schräger Blick: senkrechte Tiefe ungefähr aus dem Blickwinkel
	tiefe *= clamp(abs(dot(VIEW, normalize(mat3(VIEW_MATRIX) * vec3(0.0, 1.0, 0.0)))), 0.15, 1.0);

	vec3 farbe = mix(farbe_flach, farbe_tief, smoothstep(0.0, tiefe_farbe, tiefe));
	// Schaum: schmaler, unterbrochener Saum an der Wasserlinie
	float nah = 1.0 - smoothstep(0.0, schaum_breite, tiefe);
	float muster = texture(schaum_muster, p * 0.15 + TIME * 0.02).r;
	float schaum = smoothstep(0.55, 0.8, muster + 0.35 * nah * nah) * nah * nah * 0.85;
	schaum *= 1.0 - smoothstep(80.0, 300.0, -VERTEX.z); // aus der Ferne kein weißer Rand
	ALBEDO = mix(farbe, schaum_farbe, schaum);
	ALPHA = clamp(max(tiefe / sichttiefe, schaum), 0.25, 0.97);
	ROUGHNESS = mix(0.04, 0.6, schaum);
	SPECULAR = 0.6;
}
