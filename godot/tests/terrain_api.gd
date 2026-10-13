extends SceneTree
## Gibt die für das Spiel relevanten Eigenschaften und Methoden von Terrain3D aus (Hilfsskript).


func _initialize() -> void:
	for cls in ["Terrain3D", "Terrain3DCollision"]:
		if not ClassDB.class_exists(cls):
			continue
		for p in ClassDB.class_get_property_list(cls, true):
			var n: String = p["name"]
			if n.contains("collision") or n.contains("camera") or n.contains("target") or n.contains("mode") or n.contains("radius"):
				print(cls, " PROP ", n)
		for m in ClassDB.class_get_method_list(cls, true):
			var n: String = m["name"]
			if n.contains("camera") or n.contains("collision") or n.contains("target"):
				print(cls, " METH ", n)
	quit()
