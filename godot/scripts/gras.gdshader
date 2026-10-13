shader_type spatial;
// Bodenbewuchs (MultiMesh): Gras, Farn, Kraut, Blumen. UV.y: 0 = Fuß, 1 = Spitze; UV.x > 0.9 = Blüte.
// INSTANCE_CUSTOM: rgb = Farbton der Blätter (sRGB), a = Blütenfarbe (0 lila, 1/3 weiß, 2/3 gelb, 1 rosa).
// Wind biegt die Spitzen, zum Rand des Bereichs hin wird alles flacher (kein harter Rand).
render_mode cull_disabled, specular_disabled;

uniform vec3 fuss_farbe : source_color = vec3(0.16, 0.22, 0.08);
uniform float wind_staerke = 0.12;
uniform float wind_tempo = 1.6;
uniform vec2 mitte;          // Spieler (x, z)
uniform float radius = 35.0; // Bewuchsbereich

varying vec3 tint;
varying float bluete_wahl;

void vertex() {
	tint = pow(INSTANCE_CUSTOM.rgb, vec3(2.2)) * 1.5; // als sRGB angegeben -> linear
	bluete_wahl = INSTANCE_CUSTOM.a;
	vec3 welt = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float hoehe = UV.y;
	float rand = 1.0 - smoothstep(radius * 0.7, radius, distance(welt.xz, mitte));
	VERTEX.y *= rand;
	float welle = sin(TIME * wind_tempo + welt.x * 0.35 + welt.z * 0.22) + 0.5 * sin(TIME * wind_tempo * 2.3 + welt.x * 1.1);
	VERTEX.x += welle * wind_staerke * hoehe * hoehe;
	VERTEX.z += welle * wind_staerke * 0.6 * hoehe * hoehe;
	// Normale halb nach oben gekippt: gleichmäßiger wie dichter Bewuchs, aber nicht vom ganzen Himmel angestrahlt
	NORMAL = normalize(mix(NORMAL, vec3(0.0, 1.0, 0.0), 0.5));
}

void fragment() {
	float h = UV.y;
	vec3 blatt = mix(fuss_farbe * tint * 2.0, tint, smoothstep(0.0, 0.9, h));
	vec3 bluete = bluete_wahl < 0.15 ? vec3(0.32, 0.12, 0.42) : bluete_wahl < 0.5 ? vec3(0.8, 0.8, 0.75)
		: bluete_wahl < 0.85 ? vec3(0.85, 0.65, 0.08) : vec3(0.75, 0.3, 0.45);
	ALBEDO = UV.x > 0.9 ? bluete : blatt;
	AO = mix(0.35, 0.9, h);          // unten im Bewuchs weniger Himmelslicht
	AO_LIGHT_AFFECT = 0.3;
	ROUGHNESS = 0.95;
	BACKLIGHT = vec3(0.1, 0.14, 0.03) * h;
}
