extends StaticBody3D
## Abbaubare Rohstoffquelle (Baum, Felsen, Erzader, Pflanze, Fischgrund).
## Werte kommen aus data/gathering.json. Nach dem Abbau wächst die Quelle nach einiger Zeit nach.

const MeshUtil := preload("res://scripts/mesh_util.gd")

static var _cache: Dictionary = {}

var node_id := ""
var data: Dictionary = {}
var size_scale := 1.0
var rock_size := Vector3.ONE
var interact_radius := 2.0
var depleted := false
var catches_left := 0

var visual: Node3D
var stump: Node3D
var solid_shapes: Array[CollisionShape3D] = []
var crown_shape: CollisionShape3D


func setup(id: String) -> void:
	node_id = id
	data = Game.gathering.get(id, {})


func _ready() -> void:
	add_to_group("interactable")
	collision_layer = 1
	collision_mask = 0
	catches_left = int(data.get("catches", 1))
	visual = Node3D.new()
	add_child(visual)
	match String(data.get("visual", "rock")):
		"pine":
			_build_pine()
		"oak":
			_build_oak()
		"rock":
			_build_rock(false)
		"vein":
			_build_rock(true)
		"stalks":
			_build_stalks()
		"herb":
			_build_herb()
		"fishing":
			_build_fishing()


# --- Schnittstelle für den Spieler --------------------------------------

func is_interactable() -> bool:
	return not depleted


func is_fishing() -> bool:
	return data.get("visual", "") == "fishing"


func get_prompt() -> String:
	return "%s %s   (Tier %s)" % [data.get("name", node_id), data.get("action", "abbauen"),
		Game.tier_name(int(data.get("tier", 1)))]


func get_profession() -> String:
	return data.get("profession", "")


func get_required_level() -> int:
	return int(data.get("level", 0))


func get_gather_hp() -> float:
	return float(data.get("hp", 20.0))


func harvest(player) -> void:
	var profession := get_profession()
	player.receive_items(player.gather_drops(profession, data.get("drops", []), bool(data.get("pick_one", false))))
	player.add_profession_xp(profession, int(data.get("xp", 10)))
	if is_fishing():
		catches_left -= 1
		if catches_left > 0:
			return
	if player.regrows_instantly(profession):
		return
	_deplete()
	player.harvest_neighbor(self)


# --- Abbau & Nachwachsen ------------------------------------------------

func _deplete() -> void:
	depleted = true
	var tw := create_tween()
	match String(data.get("visual", "")):
		"pine", "oak":
			# Baum kippt um, der Stumpf bleibt stehen
			if crown_shape:
				crown_shape.set_deferred("disabled", true)
			tw.tween_property(visual, "rotation_degrees:x", 85.0, 1.2).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
			tw.tween_property(visual, "scale", Vector3.ONE * 0.01, 0.3)
			stump.visible = true
		_:
			for shape in solid_shapes:
				shape.set_deferred("disabled", true)
			tw.tween_property(visual, "scale", Vector3.ONE * 0.01, 0.3)
	tw.tween_callback(func() -> void: visual.visible = false)
	get_tree().create_timer(float(data.get("respawn", 120.0))).timeout.connect(_regrow)


func _regrow() -> void:
	depleted = false
	catches_left = int(data.get("catches", 1))
	visual.rotation = Vector3.ZERO
	visual.visible = true
	visual.scale = Vector3.ONE * 0.2
	if stump:
		stump.visible = false
	for shape in solid_shapes:
		shape.set_deferred("disabled", false)
	if crown_shape:
		crown_shape.set_deferred("disabled", false)
	create_tween().tween_property(visual, "scale", Vector3.ONE, 1.0).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


# --- Modelle ------------------------------------------------------------

static func _shared(key: String, maker: Callable):
	if not _cache.has(key):
		_cache[key] = maker.call()
	return _cache[key]


func _cone(radius: float, height: float) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = 0.0
	m.bottom_radius = radius
	m.height = height
	return m


func _cylinder(top: float, bottom: float, height: float) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = top
	m.bottom_radius = bottom
	m.height = height
	return m


func _sphere(radius: float) -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = radius
	m.height = radius * 2.0
	return m


func _add_solid(shape: Shape3D, pos: Vector3) -> CollisionShape3D:
	var col := CollisionShape3D.new()
	col.shape = shape
	col.position = pos
	add_child(col)
	solid_shapes.append(col)
	return col


func _add_crown(radius: float, height: float, y: float) -> void:
	# Krone blockiert nur die Kamera (Ebene 4), nicht den Spieler
	var crown := StaticBody3D.new()
	crown.collision_layer = 8
	crown.collision_mask = 0
	add_child(crown)
	var shape := CylinderShape3D.new()
	shape.radius = radius
	shape.height = height
	crown_shape = CollisionShape3D.new()
	crown_shape.shape = shape
	crown_shape.position.y = y
	crown.add_child(crown_shape)


func _build_stump(radius: float, color: Color) -> void:
	stump = Node3D.new()
	stump.visible = false
	add_child(stump)
	MeshUtil.part(stump, _cylinder(radius, radius * 1.15, 0.4), MeshUtil.mat(color), Vector3(0, 0.2, 0))


## Unterknoten mit der Baumgröße, damit `visual` frei animiert werden kann.
func _scaled_body() -> Node3D:
	var body := Node3D.new()
	body.scale = Vector3.ONE * size_scale
	visual.add_child(body)
	return body


func _build_pine() -> void:
	var s := size_scale
	var body := _scaled_body()
	var trunk_mat: Material = _shared("pine_trunk_mat", func(): return MeshUtil.mat(Color(0.36, 0.24, 0.14)))
	var leaves_mat: Material = _shared("pine_leaves_mat", func(): return MeshUtil.mat(Color(0.16, 0.34, 0.16)))
	MeshUtil.part(body, _shared("pine_trunk", func(): return _cylinder(0.16, 0.26, 2.0)), trunk_mat, Vector3(0, 1.0, 0))
	MeshUtil.part(body, _shared("pine_low", func(): return _cone(1.6, 2.6)), leaves_mat, Vector3(0, 2.8, 0))
	MeshUtil.part(body, _shared("pine_high", func(): return _cone(1.1, 2.0)), leaves_mat, Vector3(0, 4.0, 0))
	var trunk := CylinderShape3D.new()
	trunk.radius = 0.3 * s
	trunk.height = 3.0 * s
	_add_solid(trunk, Vector3(0, 1.5 * s, 0))
	_add_crown(0.7 * s, 2.6 * s, 3.6 * s)
	_build_stump(0.22 * s, Color(0.36, 0.24, 0.14))
	interact_radius = 1.8 + 0.3 * s


func _build_oak() -> void:
	var s := size_scale
	var body := _scaled_body()
	var trunk_mat: Material = _shared("oak_trunk_mat", func(): return MeshUtil.mat(Color(0.3, 0.2, 0.12)))
	var leaves_mat: Material = _shared("oak_leaves_mat", func(): return MeshUtil.mat(Color(0.2, 0.3, 0.12)))
	MeshUtil.part(body, _shared("oak_trunk", func(): return _cylinder(0.3, 0.45, 2.6)), trunk_mat, Vector3(0, 1.3, 0))
	var leaves_mesh: Mesh = _shared("oak_leaves", func(): return _sphere(1.5))
	for offset: Vector3 in [Vector3(0, 3.6, 0), Vector3(1.0, 3.1, 0.3), Vector3(-0.9, 3.2, -0.4), Vector3(0.2, 3.0, 1.0)]:
		MeshUtil.part(body, leaves_mesh, leaves_mat, offset)
	var trunk := CylinderShape3D.new()
	trunk.radius = 0.5 * s
	trunk.height = 3.0 * s
	_add_solid(trunk, Vector3(0, 1.5 * s, 0))
	_add_crown(1.2 * s, 2.4 * s, 3.6 * s)
	_build_stump(0.4 * s, Color(0.3, 0.2, 0.12))
	interact_radius = 2.1 + 0.4 * s


func _build_rock(with_vein: bool) -> void:
	var rock_mat: Material
	if with_vein:
		rock_mat = _shared("vein_rock_mat", func(): return MeshUtil.mat(Color(0.36, 0.35, 0.36)))
	else:
		rock_mat = _shared("rock_mat", func(): return MeshUtil.mat(Color(0.48, 0.48, 0.46)))
	var unit_box: Mesh = _shared("unit_box", func(): return MeshUtil.box(Vector3.ONE))
	var mi := MeshUtil.part(visual, unit_box, rock_mat)
	mi.scale = rock_size
	var shape := BoxShape3D.new()
	shape.size = rock_size
	_add_solid(shape, Vector3.ZERO)
	interact_radius = maxf(rock_size.x, rock_size.z) * 0.6 + 1.3
	if not with_vein:
		return
	var c: Array = data.get("color", [0.8, 0.5, 0.2])
	var ore_mat := MeshUtil.mat(Color(float(c[0]), float(c[1]), float(c[2])), 0.6, 0.35)
	ore_mat.emission_enabled = true
	ore_mat.emission = Color(float(c[0]), float(c[1]), float(c[2]))
	ore_mat.emission_energy_multiplier = 0.3
	var crystal := MeshUtil.box(Vector3(0.22, 0.4, 0.22))
	for i in 6:
		var dir := Vector3(randf_range(-1, 1), randf_range(0.2, 1.0), randf_range(-1, 1)).normalized()
		var piece := MeshUtil.part(visual, crystal, ore_mat, dir * rock_size * 0.5)
		piece.rotation = Vector3(randf_range(-0.6, 0.6), randf() * TAU, randf_range(-0.6, 0.6))


func _plant_material() -> StandardMaterial3D:
	var key := "plant_mat_" + node_id
	if _cache.has(key):
		return _cache[key]
	var c: Array = data.get("color", [0.5, 0.7, 0.3])
	var col := Color(float(c[0]), float(c[1]), float(c[2]))
	var m := MeshUtil.mat(col)
	if data.get("glow", false):
		m.emission_enabled = true
		m.emission = col
		m.emission_energy_multiplier = 0.8
	_cache[key] = m
	return m


func _build_stalks() -> void:
	var mat := _plant_material()
	var stalk := MeshUtil.box(Vector3(0.05, 1.0, 0.05))
	for i in 7:
		var piece := MeshUtil.part(visual, stalk, mat, Vector3(randf_range(-0.3, 0.3), 0.5, randf_range(-0.3, 0.3)))
		piece.rotation = Vector3(randf_range(-0.2, 0.2), 0, randf_range(-0.2, 0.2))
		piece.scale.y = randf_range(0.7, 1.3)
	interact_radius = 1.6


func _build_herb() -> void:
	var leaf_mat: Material = _shared("herb_leaf_mat", func(): return MeshUtil.mat(Color(0.2, 0.45, 0.18)))
	var base := MeshUtil.part(visual, _shared("herb_base", func(): return _sphere(0.3)), leaf_mat, Vector3(0, 0.15, 0))
	base.scale = Vector3(1, 0.6, 1)
	var flower: Mesh = _shared("herb_flower", func(): return _sphere(0.08))
	var mat := _plant_material()
	for i in 5:
		var angle := TAU * i / 5.0
		MeshUtil.part(visual, flower, mat, Vector3(cos(angle) * 0.18, 0.38, sin(angle) * 0.18))
	interact_radius = 1.6


func _build_fishing() -> void:
	var ring := TorusMesh.new()
	ring.inner_radius = 0.6
	ring.outer_radius = 0.75
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(0.85, 0.95, 1.0, 0.6)
	var mi := MeshUtil.part(visual, ring, mat, Vector3(0, 0.06, 0))
	var tw := mi.create_tween().set_loops()
	tw.tween_property(mi, "scale", Vector3(1.5, 1, 1.5), 1.2)
	tw.tween_property(mi, "scale", Vector3.ONE, 1.2)
	interact_radius = 3.0
