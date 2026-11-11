shader_type spatial;
// Augen aus der MakeHuman-Textur; die Iris wird in der gewählten Augenfarbe eingefärbt.
render_mode blend_mix, depth_prepass_alpha, cull_back;

uniform sampler2D textur : source_color, filter_linear_mipmap;
uniform vec3 iris_farbe : source_color = vec3(0.42, 0.25, 0.12);
// Mittelpunkte der beiden Augen in der Textur und Iris-/Pupillenradius
const vec2 MITTE_A = vec2(0.293, 0.707);
const vec2 MITTE_B = vec2(0.707, 0.297);
const float IRIS = 0.112;
const float PUPILLE = 0.04;

void fragment() {
	vec4 t = texture(textur, UV);
	float d = min(distance(UV, MITTE_A), distance(UV, MITTE_B));
	float iris = 1.0 - smoothstep(IRIS - 0.008, IRIS + 0.004, d);
	float pupille = 1.0 - smoothstep(PUPILLE - 0.006, PUPILLE + 0.004, d);
	float hell = dot(t.rgb, vec3(0.3, 0.55, 0.15));
	// Struktur der Originaliris behalten, Farbe tauschen; außen dunkler Ring
	vec3 iris_rgb = iris_farbe * (0.45 + hell * 2.2) * mix(0.55, 1.0, smoothstep(IRIS, IRIS * 0.7, d));
	vec3 farbe = mix(t.rgb, iris_rgb, iris * (1.0 - pupille));
	ALBEDO = farbe;
	ALPHA = t.a;
	ROUGHNESS = 0.06;
	SPECULAR = 0.6;
}
