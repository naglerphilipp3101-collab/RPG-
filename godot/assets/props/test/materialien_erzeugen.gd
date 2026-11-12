extends SceneTree
## Legt die Prop-Materialien als .tres an (assets/props/materialien/). Nur nötig, wenn neue Materialien dazukommen
## oder die Grundwerte neu gesetzt werden sollen: vorhandene Dateien werden überschrieben.
## Aufruf: Godot --headless --path godot -s res://assets/props/test/materialien_erzeugen.gd

const ORDNER := "res://assets/props/"
## Kachelgröße in Metern (u, v) wie in blender/texturen.py: die Modell-UVs sind schon in Kacheln gerechnet
const MIT_TEXTUR := ["holz", "holz_alt", "holz_verkohlt", "eisen", "stoff", "seil", "stein", "putz", "schindeln", "dielen", "glut"]


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
	var asche := StandardMaterial3D.new()
	asche.resource_name = "asche"
	asche.albedo_color = Color(0.24, 0.23, 0.22)
	asche.normal_enabled = true
	asche.normal_texture = load(ORDNER + "texturen/holz_verkohlt_normal.jpg")
	asche.roughness = 1.0
	_speichern(asche, "asche")
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
