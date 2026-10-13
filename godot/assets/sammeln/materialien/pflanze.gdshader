// Blätter/Blüten: Alpha-Scissor, beidseitig, Wind, Durchleuchtung.
shader_type spatial;
render_mode cull_disabled, depth_draw_opaque, diffuse_burley;

uniform sampler2D textur : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 farbe : source_color = vec3(1.0);
uniform float alpha_schwelle : hint_range(0.0, 1.0) = 0.4;
uniform vec3 durchleuchtung : source_color = vec3(0.07, 0.12, 0.05);
uniform float rauheit : hint_range(0.0, 1.0) = 0.85;
group_uniforms Wind;
uniform float wind_staerke = 0.05;
uniform float wind_tempo = 1.1;
// 0 = echte Kartennormalen, 1 = Normalen zeigen von der Stammachse weg (weichere, buschige Beleuchtung)
uniform float runde_normalen : hint_range(0.0, 1.0) = 0.6;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float hebel = length(VERTEX.xz) * 0.7 + max(VERTEX.y, 0.0) * 0.04;
	float phase = TIME * wind_tempo + wp.x * 0.35 + wp.z * 0.25;
	VERTEX.x += sin(phase) * wind_staerke * hebel;
	VERTEX.z += cos(phase * 0.83) * wind_staerke * hebel * 0.6;
	VERTEX.y += sin(phase * 1.7 + VERTEX.x * 2.0) * wind_staerke * hebel * 0.4;
	vec3 rund = normalize(vec3(VERTEX.x, 0.35, VERTEX.z) + vec3(0.0001));
	NORMAL = normalize(mix(NORMAL, rund, runde_normalen));
}

void fragment() {
	vec4 t = texture(textur, UV);
	// Godot dreht bei Rückseiten die Normale um; bei runden Normalen soll beide Seiten gleich beleuchtet sein
	if (!FRONT_FACING) {
		NORMAL = mix(NORMAL, -NORMAL, runde_normalen);
	}
	ALBEDO = t.rgb * farbe;
	ALPHA = t.a;
	ALPHA_SCISSOR_THRESHOLD = alpha_schwelle;
	ROUGHNESS = rauheit;
	BACKLIGHT = durchleuchtung;
}
