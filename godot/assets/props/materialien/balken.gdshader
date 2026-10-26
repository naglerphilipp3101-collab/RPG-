shader_type spatial;
// Holz für Balken und Streben des Baukastens mit Vorrang bei Überlappung.
// Balken stehen je Seite 10 cm über den Rasterpunkt; wo sich Teile durchdringen, liegen Flächen genau
// aufeinander. Hier gewinnt immer das Teil mit dem höheren Vorrang, die anderen verlieren an der Stelle ihre Fläche:
//   1. je waagerechter, desto höher (waagerecht > schräg > senkrecht)
//   2. gleich geneigt: entlang der Welt-x-Achse vor entlang z
//   3. gleiche Richtung (zwei Balken stoßen aneinander): fester Wechsel nach der Rasterposition
// Umgesetzt als winziger Tiefenversatz zur Kamera hin (Position im Bild bleibt gleich, nichts verschiebt sich sichtbar).

uniform sampler2D farbe : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_karte : hint_normal, filter_linear_mipmap_anisotropic;
uniform sampler2D rauheit : hint_default_white, filter_linear_mipmap_anisotropic;
// Richtung des Teils im eigenen Modell (Balken entlang x, Strebe schräg nach oben)
uniform vec3 achse = vec3(1.0, 0.0, 0.0);
// Tiefenversatz je Vorrang-Stufe (Anteil der Entfernung)
uniform float schritt = 0.00002;

varying flat float vorrang;

float vorrang_berechnen(mat4 modell) {
	vec3 a = normalize(mat3(modell) * achse);
	float waagerecht = round((1.0 - abs(a.y)) * 2.0);              // 0 senkrecht, 1 schräg, 2 waagerecht
	vec3 b = abs(a);
	float entlang_x = b.x >= b.z ? 1.0 : 0.0;
	// Rasterposition des Ursprungs entlang der Richtung (Vorzeichen egal, damit gedrehte Balken gleich zählen)
	vec3 r = b.x >= b.y && b.x >= b.z ? vec3(1, 0, 0) : (b.y >= b.z ? vec3(0, 1, 0) : vec3(0, 0, 1));
	float lage = mod(round(dot(modell[3].xyz, r)), 4.0);
	return waagerecht * 8.0 + entlang_x * 4.0 + lage;
}

void vertex() {
	vorrang = vorrang_berechnen(MODEL_MATRIX);
	vec4 p = MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	p.xyz *= 1.0 - vorrang * schritt;
	POSITION = PROJECTION_MATRIX * p;
}

void fragment() {
	ALBEDO = texture(farbe, UV).rgb;
	NORMAL_MAP = texture(normal_karte, UV).rgb;
	ROUGHNESS = texture(rauheit, UV).r;
}
