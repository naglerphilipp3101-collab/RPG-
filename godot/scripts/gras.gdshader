shader_type spatial;
// Grasbüschel (MultiMesh). UV.y: 0 = Halmfuß, 1 = Spitze. Instanzfarbe = Farbton des Bioms.
// Wind biegt die Spitzen, zum Rand des Grasbereichs hin werden die Halme flacher (kein harter Rand).
render_mode cull_disabled, specular_disabled;

uniform vec3 fuss_farbe : source_color = vec3(0.16, 0.22, 0.08);
uniform float wind_staerke = 0.12;
uniform float wind_tempo = 1.6;
uniform vec2 mitte;          // Spieler (x, z)
uniform float radius = 45.0; // Grasbereich

varying vec3 tint;

void vertex() {
	tint = INSTANCE_CUSTOM.rgb;
	vec3 welt = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float hoehe = UV.y;
	// zum Rand hin flacher werden
	float rand = 1.0 - smoothstep(radius * 0.7, radius, distance(welt.xz, mitte));
	VERTEX.y *= rand;
	// Wind: Wellen über die Welt, stärker an der Spitze
	float welle = sin(TIME * wind_tempo + welt.x * 0.35 + welt.z * 0.22) + 0.5 * sin(TIME * wind_tempo * 2.3 + welt.x * 1.1);
	VERTEX.x += welle * wind_staerke * hoehe * hoehe;
	VERTEX.z += welle * wind_staerke * 0.6 * hoehe * hoehe;
	// Normale halb nach oben gekippt: gleichmäßiger wie dichter Rasen, aber nicht vom ganzen Himmel angestrahlt
	NORMAL = normalize(mix(NORMAL, vec3(0.0, 1.0, 0.0), 0.5));
}

void fragment() {
	float h = UV.y;
	ALBEDO = mix(fuss_farbe * tint * 2.0, tint * 0.85, smoothstep(0.0, 0.9, h));
	AO = mix(0.35, 0.9, h);          // unten im Büschel weniger Himmelslicht
	AO_LIGHT_AFFECT = 0.3;
	ROUGHNESS = 0.95;
	BACKLIGHT = vec3(0.1, 0.14, 0.03) * h;
}
