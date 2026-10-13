shader_type spatial;
// Ferne Bäume (MultiMesh, einfache Formen mit Vertexfarben). Im Nahbereich stehen die echten Modelle –
// dort werden die fernen Bäume ausgeblendet (Eckpunkte auf den Ursprung zusammenziehen).

uniform vec2 nah_mitte;
uniform float nah_radius = 110.0;

void vertex() {
	vec3 ursprung = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	if (distance(ursprung.xz, nah_mitte) < nah_radius) {
		VERTEX = vec3(0.0);
	}
}

void fragment() {
	// Farbe steckt in den UVs (siehe natur.gd), als sRGB angegeben -> in den linearen Farbraum umrechnen
	ALBEDO = pow(vec3(UV.x, UV.y, UV2.x), vec3(2.2)) * 1.6;
	// weniger Himmelslicht (sonst wirken die fernen Bäume blass bläulich)
	AO = 0.55;
	AO_LIGHT_AFFECT = 0.0;
	ROUGHNESS = 0.95;
}
