shader_type spatial;
// Vorschau-Gelände für tests/biom_3d.gd: mischt die 9 Bodentexturen nach Gewichten je Vertex
// (COLOR = Textur 0–3, UV = 4–5, UV2 = 6–7, Rest = 8), Kachelgröße je Textur in Metern.
uniform sampler2D farbe[9] : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normale[9] : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float groesse[9];
varying vec3 wpos;
varying float w8;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	w8 = max(0.0, 1.0 - COLOR.r - COLOR.g - COLOR.b - COLOR.a - UV.x - UV.y - UV2.x - UV2.y);
}

void fragment() {
	float w[9] = float[](COLOR.r, COLOR.g, COLOR.b, COLOR.a, UV.x, UV.y, UV2.x, UV2.y, w8);
	vec3 alb = vec3(0.0);
	vec3 nrm = vec3(0.0);
	float summe = 0.0;
	// Höhe im Alpha schärft die Übergänge (wie blend_sharpness in Terrain3D); Sampler-Arrays nur mit festen Indizes (GLES3)
	if (w[0] > 0.002) {
		vec2 uv = wpos.xz / groesse[0];
		vec4 a = texture(farbe[0], uv);
		float g = w[0] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[0], uv).rgb * g;
		summe += g;
	}
	if (w[1] > 0.002) {
		vec2 uv = wpos.xz / groesse[1];
		vec4 a = texture(farbe[1], uv);
		float g = w[1] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[1], uv).rgb * g;
		summe += g;
	}
	if (w[2] > 0.002) {
		vec2 uv = wpos.xz / groesse[2];
		vec4 a = texture(farbe[2], uv);
		float g = w[2] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[2], uv).rgb * g;
		summe += g;
	}
	if (w[3] > 0.002) {
		vec2 uv = wpos.xz / groesse[3];
		vec4 a = texture(farbe[3], uv);
		float g = w[3] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[3], uv).rgb * g;
		summe += g;
	}
	if (w[4] > 0.002) {
		vec2 uv = wpos.xz / groesse[4];
		vec4 a = texture(farbe[4], uv);
		float g = w[4] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[4], uv).rgb * g;
		summe += g;
	}
	if (w[5] > 0.002) {
		vec2 uv = wpos.xz / groesse[5];
		vec4 a = texture(farbe[5], uv);
		float g = w[5] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[5], uv).rgb * g;
		summe += g;
	}
	if (w[6] > 0.002) {
		vec2 uv = wpos.xz / groesse[6];
		vec4 a = texture(farbe[6], uv);
		float g = w[6] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[6], uv).rgb * g;
		summe += g;
	}
	if (w[7] > 0.002) {
		vec2 uv = wpos.xz / groesse[7];
		vec4 a = texture(farbe[7], uv);
		float g = w[7] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[7], uv).rgb * g;
		summe += g;
	}
	if (w[8] > 0.002) {
		vec2 uv = wpos.xz / groesse[8];
		vec4 a = texture(farbe[8], uv);
		float g = w[8] * (0.3 + a.a);
		alb += a.rgb * g;
		nrm += texture(normale[8], uv).rgb * g;
		summe += g;
	}
	ALBEDO = alb / max(summe, 0.0001);
	NORMAL_MAP = nrm / max(summe, 0.0001);
	ROUGHNESS = 0.9;
}
