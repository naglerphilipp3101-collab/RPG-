extends SceneTree
## Legt die Prop-Materialien als .tres an (assets/props/materialien/). Nur nötig, wenn neue Materialien dazukommen
## oder die Grundwerte neu gesetzt werden sollen: vorhandene Dateien werden überschrieben.
## Aufruf: Godot --headless --path godot -s res://assets/props/test/materialien_erzeugen.gd

const ORDNER := "res://assets/props/"
## Kachelgröße in Metern (u, v) wie in blender/texturen.py: die Modell-UVs sind schon in Kacheln gerechnet
const MIT_TEXTUR := ["holz", "holz_alt", "holz_verkohlt", "eisen", "stoff", "seil", "stein", "putz", "schindeln", "dielen", "glut", "weide", "ton", "stroh", "leder", "teppich"]


func _init() -> void:
	for name in MIT_TEXTUR:
		var m := StandardMaterial3D.new()
		m.resource_name = name
		m.albedo_texture = load(ORDNER + "texturen/%s_farbe.jpg" % name)
		m.normal_enabled = true
		m.normal_texture = load(ORDNER + "texturen/%s_normal.jpg" % name)
		m.roughness_texture = load(ORDNER + "texturen/%s_rauheit.jpg" % name)
		m.roughness = 1.0
		m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		match name:
			"eisen":
				m.metallic = 0.6
			"stoff":
				m.cull_mode = BaseMaterial3D.CULL_DISABLED
			"glut":
				m.emission_enabled = true
				m.emission_texture = m.albedo_texture
				m.emission_energy_multiplier = 3.0
		_speichern(m, name)
	var glas := StandardMaterial3D.new()
	glas.resource_name = "glas"
	glas.albedo_color = Color(0.78, 0.66, 0.42, 0.3)
	glas.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glas.roughness = 0.08
	glas.metallic_specular = 0.7
	glas.cull_mode = BaseMaterial3D.CULL_DISABLED
	_speichern(glas, "glas")
	var gg: StandardMaterial3D = glas.duplicate()
	gg.resource_name = "glas_gruen"
	gg.albedo_color = Color(0.2, 0.38, 0.16, 0.45)
	_speichern(gg, "glas_gruen")
	var wasser: StandardMaterial3D = glas.duplicate()
	wasser.resource_name = "wasser"
	wasser.albedo_color = Color(0.1, 0.17, 0.19, 0.78)
	wasser.roughness = 0.03
	_speichern(wasser, "wasser")
	var asche := StandardMaterial3D.new()
	asche.resource_name = "asche"
	asche.albedo_color = Color(0.24, 0.23, 0.22)
	asche.normal_enabled = true
	asche.normal_texture = load(ORDNER + "texturen/holz_verkohlt_normal.jpg")
	asche.roughness = 1.0
	_speichern(asche, "asche")
	# Erde für Grab- und Knochenhügel (krümelige Struktur über die Asche-Normalkarte)
	var erde := StandardMaterial3D.new()
	erde.resource_name = "erde"
	erde.albedo_color = Color(0.2, 0.145, 0.1)
	erde.normal_enabled = true
	erde.normal_texture = load(ORDNER + "texturen/holz_verkohlt_normal.jpg")
	erde.roughness = 1.0
	_speichern(erde, "erde")
	var obst := StandardMaterial3D.new()
	obst.resource_name = "obst"
	obst.albedo_color = Color(0.62, 0.1, 0.07)
	obst.roughness = 0.45
	_speichern(obst, "obst")
	# Farbe auf der Zielscheibe (gemalte Ringe)
	for paar in [["farbe_rot", Color(0.6, 0.08, 0.06)], ["farbe_weiss", Color(0.86, 0.83, 0.76)],
			["wolle_rot", Color(0.4, 0.11, 0.09)], ["knochen", Color(0.76, 0.7, 0.57)],
			# Küche und Vorrat
			["papier", Color(0.82, 0.75, 0.58)],
			["fahne_gold", Color(0.8, 0.62, 0.22)],
			["fahne_gelb", Color(0.88, 0.68, 0.12)],
			["fahne_rot", Color(0.58, 0.07, 0.06)],
			["fahne_gruen", Color(0.15, 0.38, 0.14)],
			["fahne_schwarz", Color(0.06, 0.06, 0.07)],
			["fahne_blau", Color(0.12, 0.22, 0.55)],
			["fahne_weiss", Color(0.86, 0.84, 0.78)],
			["haut", Color(0.66, 0.52, 0.36)],
			["brot", Color(0.56, 0.33, 0.13)],
			["brot_innen", Color(0.86, 0.76, 0.56)],
			["kaese", Color(0.8, 0.6, 0.22)],
			["kaese_innen", Color(0.95, 0.83, 0.48)],
			["wurst", Color(0.36, 0.11, 0.08)],
			["kraut_trocken", Color(0.34, 0.4, 0.17)],
			["kraut_welk", Color(0.36, 0.28, 0.15)],
			["lavendel", Color(0.45, 0.38, 0.62)],
			["knoblauch", Color(0.88, 0.84, 0.76)],
			["mehl", Color(0.84, 0.82, 0.77)],
			["karotte", Color(0.86, 0.4, 0.09)],
			["kohl", Color(0.45, 0.62, 0.3)],
			["zwiebel", Color(0.7, 0.47, 0.22)],
			["faul", Color(0.22, 0.17, 0.09)],
			["schimmel", Color(0.62, 0.68, 0.55)]]:
		var f := StandardMaterial3D.new()
		f.resource_name = paar[0]
		f.albedo_color = paar[1]
		f.roughness = 0.85
		_speichern(f, paar[0])
	# Baukasten: Holz mit Vorrang bei Überlappung (balken.gdshader), je für Balken (entlang x) und Strebe (schräg)
	for name in ["holz", "holz_verkohlt"]:
		for teil in ["balken", "strebe"]:
			var v := ShaderMaterial.new()
			v.resource_name = name + "_" + teil
			v.shader = load(ORDNER + "materialien/balken.gdshader")
			v.set_shader_parameter("farbe", load(ORDNER + "texturen/%s_farbe.jpg" % name))
			v.set_shader_parameter("normal_karte", load(ORDNER + "texturen/%s_normal.jpg" % name))
			v.set_shader_parameter("rauheit", load(ORDNER + "texturen/%s_rauheit.jpg" % name))
			v.set_shader_parameter("achse", Vector3(1, 0, 0) if teil == "balken" else Vector3(1, 1, 0).normalized())
			_speichern(v, name + "_" + teil)
	quit()


func _speichern(m: Material, name: String) -> void:
	var fehler := ResourceSaver.save(m, ORDNER + "materialien/%s.tres" % name)
	print("Material ", name, ": ", "ok" if fehler == OK else str(fehler))
