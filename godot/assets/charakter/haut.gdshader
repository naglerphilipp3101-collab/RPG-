shader_type spatial;
// Haut: MakeHuman-Hauttextur (Details, Lippen, Brustwarzen …), auf die gewählte Hautfarbe umgefärbt.
// Bart und Stoppeln werden über eine Maske je Punkt (COLOR) und Rauschen aufgemalt.
render_mode cull_back;

uniform sampler2D textur : source_color, filter_linear_mipmap_anisotropic;
// Farben als sRGB-Werte (ohne source_color), damit das Verhältnis wie im Bildprogramm wirkt
uniform vec3 haut_farbe = vec3(0.85, 0.64, 0.52);
uniform vec3 textur_mittel = vec3(0.85, 0.62, 0.5);
uniform vec3 haar_farbe : source_color = vec3(0.2, 0.14, 0.1);
uniform vec4 bart = vec4(0.0);      // Stärke: x Vollbart/Wangen, y Schnurrbart, z Kinn, w Kopfstoppeln
uniform float stoppeln = 0.0;       // 0 = glatt, 1 = dichter Bart
uniform float rauheit = 0.55;
uniform vec3 waesche_farbe : source_color = vec3(0.55, 0.5, 0.43);
uniform float waesche_oben = 0.0;   // Oberteil zeigen (Frauen)

varying vec4 maske;
varying vec2 waesche;
varying vec3 grund;

void vertex() {
	maske = COLOR;
	waesche = UV2;
	grund = VERTEX;
}

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float rauschen(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
		mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

void fragment() {
	vec3 t = texture(textur, UV).rgb;
	vec3 t_srgb = pow(t, vec3(1.0 / 2.2)) * (haut_farbe / max(textur_mittel, vec3(0.02)));
	vec3 farbe = pow(clamp(t_srgb, vec3(0.0), vec3(1.0)), vec3(2.2));
	float bartmaske = max(max(maske.r * bart.x, maske.g * bart.y), max(maske.b * bart.z, maske.a * bart.w));
	if (bartmaske > 0.001) {
		// einzelne Haarpunkte statt glatter Fläche; dichter Bart deckt mehr ab
		float fein = rauschen(vec3(UV * 3300.0, 1.7));
		float grob = rauschen(vec3(UV * 900.0, 0.0));
		float haare = fein * 0.65 + grob * 0.35;
		float rand = smoothstep(0.05, 0.85, bartmaske);
		float schwelle = mix(0.62, 0.3, stoppeln);
		float deckung = smoothstep(schwelle, schwelle + 0.18, haare * rand + rand * 0.25) * mix(0.55, 0.92, stoppeln);
		farbe = mix(farbe, haar_farbe * (0.75 + fein * 0.4), deckung);
	}
	float stoff = max(waesche.x, waesche.y * waesche_oben);
	float r_stoff = rauheit;
	if (stoff > 0.01) {
		float gewebe = rauschen(vec3(UV * 2600.0, 3.1)) * 0.5 + rauschen(vec3(UV * 400.0, 5.3)) * 0.5;
		float s = smoothstep(0.47, 0.53, stoff);
		farbe = mix(farbe, waesche_farbe * (0.8 + gewebe * 0.35), s);
		r_stoff = mix(rauheit, 0.9, s);
	}
	ALBEDO = clamp(farbe, vec3(0.0), vec3(1.0));
	ROUGHNESS = r_stoff;
	SPECULAR = 0.35;
	SSS_STRENGTH = 0.35 * (1.0 - smoothstep(0.47, 0.53, stoff));
}
