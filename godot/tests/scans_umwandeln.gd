extends SceneTree
## Wandelt die Poly-Haven-Bodenscans (assets/scans/<id>/, geladen mit scans_laden.ps1) in Terrain3D-Texturen um:
## <name>_albedo_hoehe.png (RGB Farbe, A Höhe) und <name>_normal_rauheit.png (RGB Normale OpenGL, A Rauheit), 1024².
## Ergebnis in assets/welt/texturen_scan/. Aufruf: Godot --headless --path godot -s res://tests/scans_umwandeln.gd

const GROESSE := 1024
## Bodenname (wie in welt_import.gd) -> Poly-Haven-Scan
const ZUORDNUNG := {
	"sand": "sand_01", "wiese": "leafy_grass", "laubboden": "forest_leaves_02", "nadelboden": "forest_ground_04",
	"sumpf": "brown_mud_03", "steppe": "dry_ground_01", "fels": "rock_face_03", "schnee": "snow_02",
	"kies": "river_small_rocks",
}
## Ersatz, wenn ein Scan nicht geladen wurde
const ERSATZ := {"kies": "rocky_trail_02", "sand": "coast_sand_01"}


func _process(_delta: float) -> bool:
	var ziel := "res://assets/welt/texturen_scan"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(ziel))
	for name_ in ZUORDNUNG:
		var id: String = ZUORDNUNG[name_]
		if not FileAccess.file_exists(ProjectSettings.globalize_path("res://assets/scans/%s/%s_diffuse_2k.jpg" % [id, id])):
			id = ERSATZ.get(name_, id)
		var basis := ProjectSettings.globalize_path("res://assets/scans/%s/%s_" % [id, id])
		var farbe := _laden(basis + "diffuse_2k.jpg")
		var hoehe := _laden(basis + "displacement_2k.jpg")
		var normal := _laden(basis + "nor_gl_2k.jpg")
		var rau := _laden(basis + "rough_2k.jpg")
		if farbe == null or normal == null:
			push_error("Scan fehlt: " + id)
			continue
		var a := Image.create(GROESSE, GROESSE, false, Image.FORMAT_RGBA8)
		var n := Image.create(GROESSE, GROESSE, false, Image.FORMAT_RGBA8)
		for y in GROESSE:
			for x in GROESSE:
				var c := farbe.get_pixel(x, y)
				c.a = hoehe.get_pixel(x, y).r if hoehe else 0.5
				a.set_pixel(x, y, c)
				var m := normal.get_pixel(x, y)
				m.a = rau.get_pixel(x, y).r if rau else 0.8
				n.set_pixel(x, y, m)
		a.save_png(ProjectSettings.globalize_path("%s/%s_albedo_hoehe.png" % [ziel, name_]))
		n.save_png(ProjectSettings.globalize_path("%s/%s_normal_rauheit.png" % [ziel, name_]))
		print("SCAN %s <- %s" % [name_, id])
	return true


func _laden(pfad: String) -> Image:
	if not FileAccess.file_exists(pfad):
		return null
	var img := Image.load_from_file(pfad)
	img.convert(Image.FORMAT_RGBA8)
	img.resize(GROESSE, GROESSE, Image.INTERPOLATE_LANCZOS)
	return img
