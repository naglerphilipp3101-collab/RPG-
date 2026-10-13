// Erz-Shader: Gestein + Erzflecken/-adern, berechnet über die Weltposition (Triplanar).
// Dadurch bleibt die Körnung bei jeder Brockengröße gleich fein und man braucht keine UVs.
shader_type spatial;
render_mode blend_mix, cull_back, diffuse_burley, specular_schlick_ggx;

group_uniforms Gestein;
uniform vec3 gestein_dunkel : source_color = vec3(0.1);
uniform vec3 gestein_hell : source_color = vec3(0.35);
uniform float gestein_metall : hint_range(0.0, 1.0) = 0.0;
uniform float gestein_rauheit : hint_range(0.0, 1.0) = 0.85;

group_uniforms Erz;
uniform int muster : hint_enum("Flecken", "Adern") = 0;
uniform float menge : hint_range(0.0, 1.0) = 0.5;        // Flecken: Anteil
uniform float weichheit : hint_range(0.0, 0.5) = 0.06;   // Flecken: Übergangsbreite
uniform float aderbreite : hint_range(0.0, 0.2) = 0.022; // Adern: Breite
uniform bool mit_rand = false;                           // Flecken: farbiger Übergangsrand
uniform vec3 rand_farbe : source_color = vec3(0.3, 0.2, 0.1);
uniform vec3 erz_farbe : source_color = vec3(0.5);
uniform float erz_metall : hint_range(0.0, 1.0) = 1.0;
uniform float erz_rauheit : hint_range(0.0, 1.0) = 0.3;
uniform vec3 leucht_farbe : source_color = vec3(0.0);
uniform float leucht_staerke : hint_range(0.0, 16.0) = 0.0;
uniform float muster_skalierung = 1.0;                   // >1 = feineres Muster (Schutt)

group_uniforms Texturen;
uniform sampler2D noise_fbm : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D noise_zellen : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float blend_schaerfe = 6.0;

varying vec3 w_pos;
varying vec3 w_nrm;

void vertex() {
	w_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	w_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

float tri(sampler2D t, vec3 p, vec3 w) {
	return texture(t, p.zy).r * w.x + texture(t, p.xz).r * w.y + texture(t, p.xy).r * w.z;
}

// Zellmuster mit verzerrten Koordinaten -> unregelmäßige Flecken statt Kreise
float zellen_verzerrt(vec2 uv) {
	vec2 v = vec2(texture(noise_fbm, uv * 0.35).r, texture(noise_fbm, uv * 0.35 + 0.5).r) - 0.5;
	return texture(noise_zellen, uv + v * 0.35).r;
}

float tri_zellen(vec3 p, vec3 w) {
	return zellen_verzerrt(p.zy) * w.x + zellen_verzerrt(p.xz) * w.y + zellen_verzerrt(p.xy) * w.z;
}

void fragment() {
	vec3 w = pow(abs(w_nrm), vec3(blend_schaerfe));
	w /= (w.x + w.y + w.z);
	vec3 p = w_pos;
	vec3 pm = p * muster_skalierung;

	// Gestein: feine Körnung x großflächige Helligkeit
	float korn = tri(noise_fbm, p * 0.8, w);
	vec3 gestein = mix(gestein_dunkel, gestein_hell, smoothstep(0.3, 0.7, korn));
	float ton = mix(0.45, 1.0, smoothstep(0.35, 0.65, tri(noise_fbm, p * 0.18 + 0.37, w)));
	vec3 flaeche = gestein * ton;

	float maske;
	if (muster == 0) {
		float d = tri_zellen(pm * 0.45, w);
		d += (tri(noise_fbm, pm * 2.5 + 0.21, w) - 0.5) * 0.1;   // Rand zerfransen
		maske = 1.0 - smoothstep(menge - weichheit - 0.04, menge - 0.04, d);
		if (mit_rand) {
			float rand = 1.0 - smoothstep(menge - 0.04, menge + 0.12, d);
			flaeche = mix(flaeche, rand_farbe, rand);
		}
	} else {
		float a1 = abs(tri(noise_fbm, pm * 0.45, w) - 0.5);
		float a2 = abs(tri(noise_fbm, pm * 1.0 + 0.53, w) - 0.5);
		maske = max(1.0 - smoothstep(aderbreite * 0.45, aderbreite, a1),
		            1.0 - smoothstep(aderbreite * 0.12, aderbreite * 0.28, a2));
	}

	float var = tri(noise_fbm, pm * 3.0 + 0.71, w);
	vec3 erz = mix(erz_farbe * 0.65, min(erz_farbe * 1.25, vec3(1.0)), var);
	float raus = mix(gestein_rauheit * 0.8, min(gestein_rauheit * 1.25, 1.0), tri(noise_fbm, p * 1.5 + 0.11, w));

	ALBEDO = mix(flaeche, erz, maske);
	METALLIC = mix(gestein_metall, erz_metall, maske);
	ROUGHNESS = mix(raus, erz_rauheit, maske);
	EMISSION = leucht_farbe * leucht_staerke * maske;
}
