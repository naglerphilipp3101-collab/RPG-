class_name ScanModelle
extends RefCounted
## Liest die Poly-Haven-Scans (assets/scans/<id>/<id>_2k.gltf, geladen mit scans_laden.ps1) einmal ein und liefert
## ihre Einzelteile: je Teil Mesh (mit eigenen Materialien), Transform aus der Datei und Begrenzung (AABB im Transform).
## Fehlen die Scans, kommt eine leere Liste zurück – die Aufrufer nehmen dann ihre eigenen Modelle.

static var _cache := {}


static func vorhanden(id: String) -> bool:
	return ResourceLoader.exists("res://assets/scans/%s/%s_2k.gltf" % [id, id])


## Teile eines Scans; filter = nur Teile, deren Name das enthält (z. B. "tall")
static func teile(id: String, filter := "") -> Array:
	var key := id + "|" + filter
	if _cache.has(key):
		return _cache[key]
	var liste: Array = []
	if vorhanden(id):
		var wurzel: Node3D = load("res://assets/scans/%s/%s_2k.gltf" % [id, id]).instantiate()
		for mi in wurzel.find_children("*", "MeshInstance3D", true, false):
			if filter != "" and not String(mi.name).contains(filter):
				continue
			# Transform relativ zur Datei-Wurzel (Skalierung/Drehung aus dem Scan übernehmen)
			var xf := Transform3D.IDENTITY
			var n: Node = mi
			while n != wurzel and n is Node3D:
				xf = (n as Node3D).transform * xf
				n = n.get_parent()
			var mesh: Mesh = (mi as MeshInstance3D).mesh
			liste.append({"mesh": mesh, "xf": xf, "aabb": xf * mesh.get_aabb(), "name": String(mi.name)})
		wurzel.free()
	_cache[key] = liste
	return liste
