shader_type spatial;
// Fotogescannte Felstextur ohne UVs: von drei Seiten projiziert (Triplanar, Weltkoordinaten), mit Normalen und Rauheit.
// Für die Felsmonolithen (Blender-Formen haben keine UVs). Flächen, die nach oben zeigen, bekommen etwas Moos.

uniform sampler2D farbe : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normale : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rauheit : hint_roughness_r, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float groesse = 3.0;          // Meter je Texturkachel
uniform vec3 moos_farbe : source_color = vec3(0.24, 0.3, 0.14);
uniform float moos = 0.45;

varying vec3 welt_pos;
varying vec3 welt_normale;

void vertex() {
	welt_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	welt_normale = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec3 gewichte(vec3 n) {
	vec3 w = pow(abs(n), vec3(4.0));
	return w / (w.x + w.y + w.z);
}

void fragment() {
	vec3 w = gewichte(welt_normale);
	vec2 uv_x = welt_pos.zy / groesse;
	vec2 uv_y = welt_pos.xz / groesse;
	vec2 uv_z = welt_pos.xy / groesse;
	vec3 c = texture(farbe, uv_x).rgb * w.x + texture(farbe, uv_y).rgb * w.y + texture(farbe, uv_z).rgb * w.z;
	float r = texture(rauheit, uv_x).r * w.x + texture(rauheit, uv_y).r * w.y + texture(rauheit, uv_z).r * w.z;
	vec3 nm = texture(normale, uv_x).rgb * w.x + texture(normale, uv_y).rgb * w.y + texture(normale, uv_z).rgb * w.z;
	// Moos auf nach oben zeigenden Flächen, mit der Textur gemischt
	float oben = smoothstep(0.55, 0.9, welt_normale.y) * moos;
	ALBEDO = mix(c, c * moos_farbe * 3.0, oben);
	ROUGHNESS = mix(r, 0.95, oben);
	NORMAL_MAP = nm;
	NORMAL_MAP_DEPTH = 1.2;
}
