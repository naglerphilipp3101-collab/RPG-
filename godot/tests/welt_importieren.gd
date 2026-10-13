extends SceneTree
## Wandelt den Weltgenerator-Export (res://welt_daten) einmalig in Terrain3D-Daten um (res://welt_daten/terrain3d).
## Aufruf: Godot --headless --path godot -s res://tests/welt_importieren.gd
## Danach lädt das Spiel die Insel direkt aus diesen Daten.

var importer
var frames := 0


func _initialize() -> void:
	if not ClassDB.class_exists("Terrain3D"):
		push_error("Terrain3D ist nicht installiert (godot/addons/terrain_3d).")
		quit(1)
		return
	var camera := Camera3D.new() # Terrain3D erwartet eine aktive Kamera
	root.add_child(camera)
	importer = load("res://assets/welt/welt_import.gd").new()
	importer.daten_ordner = "res://welt_daten"
	root.add_child(importer)
	var terrain = ClassDB.instantiate("Terrain3D")
	terrain.name = "Terrain3D"
	terrain.set("data_directory", "res://welt_daten/terrain3d")
	importer.add_child(terrain)


func _process(_delta: float) -> bool:
	frames += 1
	if frames < 3:
		return false # Terrain3D initialisiert seine Daten erst nach dem ersten Frame
	var start := Time.get_ticks_msec()
	importer.importieren()
	var terrain = importer.get_node("Terrain3D")
	var ziel := "res://welt_daten/terrain3d"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(ziel))
	terrain.get("data").save_directory(ziel)
	print("WELTIMPORT fertig in %.1f s, Regionen: %d, Regionsgröße: %d" % [
		(Time.get_ticks_msec() - start) / 1000.0, terrain.get("data").get_region_count(), terrain.get("region_size")])
	return true
