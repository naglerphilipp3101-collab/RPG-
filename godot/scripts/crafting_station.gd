extends StaticBody3D
## Werkstatt (Schmelze, Tischlerei, Schmiede …). Mit E öffnet sich das Herstellungsfenster.
## Werte kommen aus data/stations.json.

const MeshUtil := preload("res://scripts/mesh_util.gd")
const WeaponModels := preload("res://scripts/weapon_models.gd")

var station_id := ""
var data: Dictionary = {}
var interact_radius := 2.8


func setup(id: String) -> void:
	station_id = id
	data = Game.stations.get(id, {})


func _ready() -> void:
	add_to_group("interactable")
	collision_layer = 1
	collision_mask = 0
	_build_model()
	var shape := BoxShape3D.new()
	shape.size = Vector3(1.8, 1.2, 1.2)
	var col := CollisionShape3D.new()
	col.shape = shape
	col.position.y = 0.6
	add_child(col)

	var label := Label3D.new()
	label.text = data.get("name", station_id)
	label.position.y = 2.6
	label.font_size = 48
	label.outline_size = 12
	label.pixel_size = 0.005
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color(1.0, 0.9, 0.65)
	add_child(label)


# --- Schnittstelle für den Spieler (wie Rohstoffquellen) ------------------

func get_station_id() -> String:
	return station_id


func is_interactable() -> bool:
	return true


func is_fishing() -> bool:
	return false


func get_prompt() -> String:
	return "%s benutzen" % data.get("name", station_id)


func get_profession() -> String:
	return data.get("profession", "")


func get_required_level() -> int:
	return 0


# --- Modell -------------------------------------------------------------

func _build_model() -> void:
	var wood := MeshUtil.mat(Color(0.5, 0.34, 0.18))
	var dark_wood := MeshUtil.mat(Color(0.35, 0.23, 0.12))
	var metal := MeshUtil.mat(Color(0.3, 0.3, 0.33), 0.8, 0.4)
	var stone := MeshUtil.mat(Color(0.5, 0.5, 0.5))

	match String(data.get("visual", "")):
		"furnace":
			MeshUtil.part(self, MeshUtil.box(Vector3(1.6, 1.4, 1.2)), stone, Vector3(0, 0.7, 0))
			var chimney := CylinderMesh.new()
			chimney.top_radius = 0.25
			chimney.bottom_radius = 0.35
			chimney.height = 1.4
			MeshUtil.part(self, chimney, stone, Vector3(0, 2.1, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(0.7, 0.5, 0.05)), _glow(Color(1.0, 0.45, 0.1)), Vector3(0, 0.5, -0.61))
			_add_light(Color(1.0, 0.55, 0.2), Vector3(0, 0.6, -1.0))
		"saw":
			_table(wood)
			var log_mesh := CylinderMesh.new()
			log_mesh.top_radius = 0.18
			log_mesh.bottom_radius = 0.18
			log_mesh.height = 1.4
			var log_part := MeshUtil.part(self, log_mesh, dark_wood, Vector3(0, 1.1, 0))
			log_part.rotation_degrees.z = 90.0
			MeshUtil.part(self, MeshUtil.box(Vector3(0.02, 0.5, 0.6)), metal, Vector3(0.2, 1.3, 0))
		"rack":
			for x: float in [-0.8, 0.8]:
				MeshUtil.part(self, MeshUtil.box(Vector3(0.1, 1.8, 0.1)), dark_wood, Vector3(x, 0.9, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(1.7, 0.08, 0.08)), dark_wood, Vector3(0, 1.75, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(1.3, 1.2, 0.03)), MeshUtil.mat(Color(0.6, 0.48, 0.36)), Vector3(0, 1.1, 0))
		"loom":
			for x: float in [-0.7, 0.7]:
				MeshUtil.part(self, MeshUtil.box(Vector3(0.1, 1.6, 0.6)), wood, Vector3(x, 0.8, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(1.5, 0.08, 0.08)), wood, Vector3(0, 1.55, 0))
			var thread := MeshUtil.mat(Color(0.9, 0.86, 0.75))
			for i in 9:
				MeshUtil.part(self, MeshUtil.box(Vector3(0.015, 1.2, 0.015)), thread, Vector3(-0.6 + i * 0.15, 0.95, 0))
		"stone":
			_table(wood)
			MeshUtil.part(self, MeshUtil.box(Vector3(0.6, 0.45, 0.5)), stone, Vector3(-0.3, 1.12, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(0.3, 0.3, 0.3)), stone, Vector3(0.45, 1.05, 0.1))
		"anvil", "armor":
			MeshUtil.part(self, MeshUtil.box(Vector3(0.5, 0.5, 0.5)), dark_wood, Vector3(-0.3, 0.25, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(0.8, 0.25, 0.35)), metal, Vector3(-0.3, 0.62, 0))
			if data.get("visual") == "anvil":
				for i in 3:
					var blade := MeshUtil.part(self, MeshUtil.box(Vector3(0.06, 1.1, 0.02)), MeshUtil.mat(Color(0.7, 0.72, 0.75), 0.8, 0.3),
						Vector3(0.45 + i * 0.18, 0.75, 0.2))
					blade.rotation_degrees.z = -8.0
			else:
				var body := CapsuleMesh.new()
				body.radius = 0.28
				body.height = 1.1
				MeshUtil.part(self, body, MeshUtil.mat(Color(0.55, 0.57, 0.62), 0.6, 0.4), Vector3(0.6, 1.1, 0))
				MeshUtil.part(self, MeshUtil.box(Vector3(0.06, 0.6, 0.06)), dark_wood, Vector3(0.6, 0.3, 0))
			_add_light(Color(1.0, 0.6, 0.3), Vector3(-0.3, 1.0, 0))
		"gears":
			_table(wood)
			for i in 3:
				var gear := CylinderMesh.new()
				gear.top_radius = 0.18 + i * 0.06
				gear.bottom_radius = gear.top_radius
				gear.height = 0.05
				var part := MeshUtil.part(self, gear, metal, Vector3(-0.5 + i * 0.45, 1.2 + i * 0.05, 0))
				part.rotation_degrees.x = 90.0
		"gem":
			_table(dark_wood)
			var gem := SphereMesh.new()
			gem.radius = 0.12
			gem.height = 0.24
			MeshUtil.part(self, gem, _glow(Color(0.4, 0.8, 1.0)), Vector3(0, 1.1, 0))
			_add_light(Color(0.4, 0.8, 1.0), Vector3(0, 1.4, 0))
		"cauldron":
			var pot := CylinderMesh.new()
			pot.top_radius = 0.55
			pot.bottom_radius = 0.4
			pot.height = 0.8
			MeshUtil.part(self, pot, metal, Vector3(0, 0.4, 0))
			var liquid := CylinderMesh.new()
			liquid.top_radius = 0.5
			liquid.bottom_radius = 0.5
			liquid.height = 0.02
			MeshUtil.part(self, liquid, _glow(Color(0.3, 1.0, 0.4)), Vector3(0, 0.78, 0))
			_add_light(Color(0.3, 1.0, 0.4), Vector3(0, 1.2, 0))
		"kitchen":
			_table(wood)
			var pot := CylinderMesh.new()
			pot.top_radius = 0.25
			pot.bottom_radius = 0.22
			pot.height = 0.35
			MeshUtil.part(self, pot, metal, Vector3(-0.4, 1.08, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(0.5, 0.04, 0.35)), wood, Vector3(0.4, 0.92, 0))
		"weapon_rack":
			for x: float in [-0.85, 0.85]:
				MeshUtil.part(self, MeshUtil.box(Vector3(0.1, 1.7, 0.1)), dark_wood, Vector3(x, 0.85, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(1.8, 0.08, 0.1)), dark_wood, Vector3(0, 1.6, 0))
			MeshUtil.part(self, MeshUtil.box(Vector3(1.8, 0.08, 0.1)), dark_wood, Vector3(0, 0.3, 0))
			var models := ["sword", "axe", "spear", "mace", "greatsword"]
			for i in models.size():
				var holder := Node3D.new()
				holder.position = Vector3(-0.6 + i * 0.3, 0.15, 0.08)
				holder.rotation_degrees = Vector3(90, 0, 0) # Klinge nach oben
				add_child(holder)
				WeaponModels.build(models[i], holder)
		_:
			_table(wood)


func _table(mat: Material) -> void:
	MeshUtil.part(self, MeshUtil.box(Vector3(1.8, 0.1, 1.0)), mat, Vector3(0, 0.85, 0))
	for x: float in [-0.8, 0.8]:
		for z: float in [-0.4, 0.4]:
			MeshUtil.part(self, MeshUtil.box(Vector3(0.1, 0.8, 0.1)), mat, Vector3(x, 0.4, z))


func _glow(color: Color) -> StandardMaterial3D:
	var m := MeshUtil.mat(color)
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = 2.5
	return m


func _add_light(color: Color, pos: Vector3) -> void:
	var light := OmniLight3D.new()
	light.light_color = color
	light.light_energy = 1.2
	light.omni_range = 4.0
	light.position = pos
	add_child(light)
