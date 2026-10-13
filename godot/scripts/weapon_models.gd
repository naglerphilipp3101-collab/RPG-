extends RefCounted
## Platzhalter-Modelle für Waffen und Geschosse. Die Klinge zeigt jeweils entlang -Z.

const MeshUtil := preload("res://scripts/mesh_util.gd")


static func build(model: String, parent: Node3D) -> void:
	var metal := MeshUtil.mat(Color(0.75, 0.77, 0.8), 0.8, 0.3)
	var dark_metal := MeshUtil.mat(Color(0.4, 0.4, 0.43), 0.8, 0.4)
	var wood := MeshUtil.mat(Color(0.48, 0.32, 0.17))
	var leather := MeshUtil.mat(Color(0.35, 0.22, 0.12))
	var string_mat := MeshUtil.mat(Color(0.92, 0.9, 0.85))
	match model:
		"sword":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 0.22)), leather, Vector3(0, 0, 0.02))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.3, 0.05, 0.06)), metal, Vector3(0, 0, -0.1))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.07, 0.02, 0.9)), metal, Vector3(0, 0, -0.58))
		"axe":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.045, 0.045, 0.7)), wood, Vector3(0, 0, -0.27))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.26, 0.22)), metal, Vector3(0, 0.1, -0.56))
		"mace":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 0.6)), wood, Vector3(0, 0, -0.22))
			MeshUtil.part(parent, _sphere(0.13), dark_metal, Vector3(0, 0, -0.6))
			for dir: Vector3 in [Vector3.UP, Vector3.DOWN, Vector3.LEFT, Vector3.RIGHT, Vector3.FORWARD]:
				MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 0.05)), metal, Vector3(0, 0, -0.6) + dir * 0.15)
		"greatsword":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 0.4)), leather, Vector3(0, 0, 0.08))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.42, 0.06, 0.07)), metal, Vector3(0, 0, -0.14))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.1, 0.025, 1.4)), metal, Vector3(0, 0, -0.88))
		"greataxe":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 1.4)), wood, Vector3(0, 0, -0.5))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.48, 0.36)), metal, Vector3(0, 0.14, -1.08))
		"warhammer":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.06, 0.06, 1.3)), wood, Vector3(0, 0, -0.45))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.22, 0.44, 0.24)), dark_metal, Vector3(0, 0, -1.08))
		"spear":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.04, 2.2)), wood, Vector3(0, 0, -0.65))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.07, 0.02, 0.32)), metal, Vector3(0, 0, -1.9))
		"rapier":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.04, 0.18)), leather, Vector3(0, 0, 0.03))
			MeshUtil.part(parent, _sphere(0.07), metal, Vector3(0, 0, -0.08))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.025, 0.015, 1.0)), metal, Vector3(0, 0, -0.6))
		"dagger":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.04, 0.12)), leather, Vector3(0, 0, 0.02))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.12, 0.03, 0.04)), metal, Vector3(0, 0, -0.05))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.015, 0.34)), metal, Vector3(0, 0, -0.24))
		"bow":
			var upper := MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.65, 0.05)), wood, Vector3(0, 0.3, -0.28))
			upper.rotation_degrees.x = -15.0
			var lower := MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.65, 0.05)), wood, Vector3(0, -0.3, -0.28))
			lower.rotation_degrees.x = 15.0
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.01, 1.2, 0.01)), string_mat, Vector3(0, 0, -0.12))
		"musket":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.08, 0.14, 0.4)), wood, Vector3(0, -0.03, 0.08))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.06, 0.06, 0.5)), wood, Vector3(0, 0, -0.35))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.045, 0.045, 1.0)), dark_metal, Vector3(0, 0.03, -0.6))
		"crossbow":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.07, 0.08, 0.7)), wood, Vector3(0, 0, -0.2))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.9, 0.04, 0.05)), wood, Vector3(0, 0.02, -0.5))
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.85, 0.01, 0.01)), string_mat, Vector3(0, 0.03, -0.3))


static func build_projectile(kind: String, parent: Node3D) -> void:
	var wood := MeshUtil.mat(Color(0.55, 0.4, 0.25))
	var metal := MeshUtil.mat(Color(0.8, 0.8, 0.85), 0.8, 0.3)
	match kind:
		"arrow":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.025, 0.025, 0.7)), wood)
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.04, 0.04, 0.08)), metal, Vector3(0, 0, -0.38))
		"bolt":
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.035, 0.035, 0.45)), wood)
			MeshUtil.part(parent, MeshUtil.box(Vector3(0.05, 0.05, 0.07)), metal, Vector3(0, 0, -0.25))
		"bullet":
			var glow := MeshUtil.mat(Color(1.0, 0.85, 0.5))
			glow.emission_enabled = true
			glow.emission = Color(1.0, 0.7, 0.3)
			glow.emission_energy_multiplier = 3.0
			MeshUtil.part(parent, _sphere(0.05), glow)
		"axe":
			build("axe", parent)


static func _sphere(radius: float) -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = radius
	m.height = radius * 2.0
	return m
