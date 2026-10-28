shader_type spatial;
// Felstextur ohne UVs: von drei Seiten projiziert (Triplanar, Weltkoordinaten), mit Normalen und Rauheit.
// Für die Steine aus assets/erz/blender/steine.py. Texturen wie beim Gelände gepackt:
// farbe = RGB Farbe (A Höhe), normale = RGB Normale (OpenGL), A Rauheit.
// Die Vertexfarbe dunkelt Spalten ab, Flächen, die nach oben zeigen, bekommen etwas Moos.

uniform sampler2D farbe : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
// ohne hint_normal, damit Godot die Textur nicht als Normalenkarte neu komprimiert (der Alphakanal trägt die Rauheit)
uniform sampler2D normale : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float groesse = 2.5;          // Meter je Texturkachel
uniform vec3 ton : source_color = vec3(1.0);
uniform float hoehlen = 1.0;          // Stärke der Abdunklung aus der Vertexfarbe
uniform vec3 moos_farbe : source_color = vec3(0.24, 0.3, 0.14);
uniform float moos = 0.3;
uniform float glanz = 0.0;            // Feuerstein: etwas glatter

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
	vec2 uv_y = welt_pos.xz / groesse + 0.37;
	vec2 uv_z = welt_pos.xy / groesse + 0.71;
	vec3 c = texture(farbe, uv_x).rgb * w.x + texture(farbe, uv_y).rgb * w.y + texture(farbe, uv_z).rgb * w.z;
	vec4 nr = texture(normale, uv_x) * w.x + texture(normale, uv_y) * w.y + texture(normale, uv_z) * w.z;
	float ao = mix(1.0, COLOR.r / 0.72, hoehlen);
	c *= ton * clamp(ao, 0.25, 1.25);
	float oben = smoothstep(0.6, 0.92, welt_normale.y) * moos * smoothstep(0.5, 0.9, COLOR.r);
	ALBEDO = mix(c, c * moos_farbe * 3.0, oben);
	ROUGHNESS = mix(mix(nr.a, 0.95, oben), 0.35, glanz);
	NORMAL_MAP = nr.rgb;
	NORMAL_MAP_DEPTH = 1.2;
	AO = clamp(ao, 0.0, 1.0);
}
