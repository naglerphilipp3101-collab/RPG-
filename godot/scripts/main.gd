extends Node3D
## Testgebiet: baut Welt, Rohstoffe, Teich, Spieler, Gegnerlager und HUD per Code auf.

const PlayerScript := preload("res://scripts/player.gd")
const EnemyScript := preload("res://scripts/enemy.gd")
const HudScript := preload("res://scripts/hud.gd")
const MeshUtil := preload("res://scripts/mesh_util.gd")
const ResourceNodeScript := preload("res://scripts/resource_node.gd")
const StationScript := preload("res://scripts/crafting_station.gd")
const SaveGame := preload("res://scripts/save_game.gd")
const VILLAGE_CENTER := Vector3(0, 0, 24)
const VILLAGE_RADIUS := 9.0

const WORLD_SIZE := 300.0
const NORTH_ZONE_Z := -80.0 # nördlich davon: Tier-2-Rohstoffe
const POND_CENTER := Vector3(-45, 0, 25)
const POND_RADIUS := 9.0

var rng := RandomNumberGenerator.new()
var clear_spots: Array[Vector3] = []


func _ready() -> void:
	rng.seed = 7
	var camps := [
		{"type": "wolf", "pos": Vector3(20, 0, -14), "count": 3, "style": "den"},
		{"type": "bandit", "pos": Vector3(-24, 0, -30), "count": 3, "style": "camp"},
		{"type": "brute", "pos": Vector3(6, 0, -58), "count": 1, "style": "lair"},
	]
	clear_spots.append(Vector3(0, 0, 6))
	clear_spots.append(Vector3(0, 0, 14))
	clear_spots.append(VILLAGE_CENTER)
	for i in 8:
		var angle := TAU * i / 8.0
		clear_spots.append(VILLAGE_CENTER + Vector3(cos(angle), 0, sin(angle)) * VILLAGE_RADIUS)
	for camp in camps:
		clear_spots.append(camp["pos"])
	# Teich: mehrere Punkte, damit nichts im Wasser wächst
	clear_spots.append(POND_CENTER)
	for i in 8:
		var angle := TAU * i / 8.0
		clear_spots.append(POND_CENTER + Vector3(cos(angle), 0, sin(angle)) * POND_RADIUS * 0.6)

	_build_environment()
	_build_ground()
	_build_pond()
	_build_village()
	_scatter_nature()
	for camp in camps:
		_build_camp(camp)

	var player: Node3D = PlayerScript.new()
	player.name = "Player"
	player.position = Vector3(0, 0.5, 6)
	add_child(player)

	var hud = HudScript.new()
	hud.name = "HUD"
	add_child(hud)
	hud.bind_player(player)

	for camp in camps:
		for i in int(camp["count"]):
			var enemy = EnemyScript.new()
			enemy.setup(camp["type"], camp["pos"])
			enemy.position = camp["pos"] + Vector3(rng.randf_range(-4, 4), 0.5, rng.randf_range(-4, 4))
			add_child(enemy)

	if OS.get_cmdline_user_args().has("--autotest"):
		Game.saving_enabled = false # Tests dürfen den echten Spielstand nicht anfassen
		add_child(load("res://tests/autotest.gd").new())
	elif SaveGame.load_into(get_tree(), Game.SAVE_PATH):
		hud.show_message("Spielstand geladen")

	var autosave := Timer.new()
	autosave.wait_time = Game.AUTOSAVE_INTERVAL
	autosave.autostart = true
	autosave.timeout.connect(_autosave)
	add_child(autosave)


func _autosave() -> void:
	if Game.saving_enabled and SaveGame.save(get_tree(), Game.SAVE_PATH):
		var player = get_tree().get_first_node_in_group("player")
		player.notify.emit("Automatisch gespeichert", Color(0.7, 0.7, 0.7))


func _notification(what: int) -> void:
	# Beim Schließen des Fensters speichern
	if what == NOTIFICATION_WM_CLOSE_REQUEST and Game.saving_enabled:
		SaveGame.save(get_tree(), Game.SAVE_PATH)


func _build_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.3, 0.48, 0.78)
	sky_mat.sky_horizon_color = Color(0.72, 0.8, 0.88)
	sky_mat.ground_horizon_color = Color(0.6, 0.65, 0.6)
	sky_mat.ground_bottom_color = Color(0.2, 0.24, 0.2)
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.7, 0.78, 0.86)
	env.fog_density = 0.006
	env.ssao_enabled = true
	env.glow_enabled = true
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 80.0
	add_child(sun)


func _build_ground() -> void:
	var noise := FastNoiseLite.new()
	noise.frequency = 0.02
	var gradient := Gradient.new()
	gradient.set_color(0, Color(0.24, 0.38, 0.17))
	gradient.set_color(1, Color(0.42, 0.55, 0.26))
	var tex := NoiseTexture2D.new()
	tex.noise = noise
	tex.width = 512
	tex.height = 512
	tex.seamless = true
	tex.color_ramp = gradient
	var ground_mat := MeshUtil.mat(Color.WHITE, 0.0, 1.0)
	ground_mat.albedo_texture = tex
	ground_mat.uv1_scale = Vector3(25, 25, 1)

	var plane := PlaneMesh.new()
	plane.size = Vector2(WORLD_SIZE, WORLD_SIZE)
	var ground := StaticBody3D.new()
	add_child(ground)
	MeshUtil.part(ground, plane, ground_mat)
	_add_box_collision(ground, Vector3(WORLD_SIZE, 2, WORLD_SIZE), Vector3(0, -1, 0))

	# Unsichtbare Weltgrenze
	var half := WORLD_SIZE / 2.0
	for wall: Array in [
		[Vector3(WORLD_SIZE, 20, 1), Vector3(0, 10, -half)],
		[Vector3(WORLD_SIZE, 20, 1), Vector3(0, 10, half)],
		[Vector3(1, 20, WORLD_SIZE), Vector3(-half, 10, 0)],
		[Vector3(1, 20, WORLD_SIZE), Vector3(half, 10, 0)],
	]:
		_add_box_collision(ground, wall[0], wall[1])


func _add_box_collision(body: Node3D, size: Vector3, pos: Vector3) -> void:
	var shape := BoxShape3D.new()
	shape.size = size
	var col := CollisionShape3D.new()
	col.shape = shape
	col.position = pos
	body.add_child(col)


func _is_clear(pos: Vector3, distance: float) -> bool:
	for spot in clear_spots:
		if pos.distance_to(spot) < distance:
			return false
	return true


## Zufälliger freier Punkt. Ohne Angabe von z-Grenzen auf der ganzen Karte.
func _random_spot(margin: float, z_min := -INF, z_max := INF) -> Vector3:
	var half := WORLD_SIZE * 0.47
	var lo := maxf(-half, z_min)
	var hi := minf(half, z_max)
	while true:
		var pos := Vector3(rng.randf_range(-half, half), 0.0, rng.randf_range(lo, hi))
		if _is_clear(pos, margin):
			return pos
	return Vector3.ZERO


func _add_resource(id: String, pos: Vector3, scale_factor := 1.0, rock_size := Vector3.ONE) -> Node3D:
	var node = ResourceNodeScript.new()
	node.setup(id)
	node.size_scale = scale_factor
	node.rock_size = rock_size
	node.position = pos
	node.rotation.y = rng.randf() * TAU
	add_child(node)
	return node


func _scatter_nature() -> void:
	# Tier 1 überall im Süden, Tier 2 im Norden hinter dem Oger (z < NORTH_ZONE_Z)
	for i in 230:
		_add_resource("pine", _random_spot(10.0, NORTH_ZONE_Z + 5.0), rng.randf_range(0.8, 1.5))
	for i in 40:
		_add_resource("pine", _random_spot(10.0, -INF, NORTH_ZONE_Z), rng.randf_range(1.0, 1.6))
	for i in 45:
		_add_resource("oak", _random_spot(10.0, -INF, NORTH_ZONE_Z), rng.randf_range(0.9, 1.3))

	for i in 70:
		var size := Vector3(rng.randf_range(0.8, 2.6), rng.randf_range(0.6, 1.8), rng.randf_range(0.8, 2.6))
		_add_resource("stone", _random_spot(8.0) + Vector3(0, size.y * 0.35, 0), 1.0, size)
	for i in 28:
		var size := Vector3(rng.randf_range(1.2, 2.0), rng.randf_range(0.9, 1.4), rng.randf_range(1.2, 2.0))
		_add_resource("copper_vein", _random_spot(8.0, NORTH_ZONE_Z + 5.0) + Vector3(0, size.y * 0.35, 0), 1.0, size)
	for i in 18:
		var size := Vector3(rng.randf_range(1.2, 2.0), rng.randf_range(0.9, 1.4), rng.randf_range(1.2, 2.0))
		_add_resource("iron_vein", _random_spot(8.0, -INF, NORTH_ZONE_Z) + Vector3(0, size.y * 0.35, 0), 1.0, size)

	for i in 55:
		_add_resource("hemp", _random_spot(6.0, NORTH_ZONE_Z + 5.0))
	for i in 40:
		_add_resource("healing_herb", _random_spot(6.0))
	for i in 25:
		_add_resource("silverleaf", _random_spot(6.0, -INF, NORTH_ZONE_Z))

	var bush_mesh := SphereMesh.new()
	bush_mesh.radius = 0.7
	bush_mesh.height = 1.0
	var bush_mat := MeshUtil.mat(Color(0.22, 0.42, 0.18))
	for i in 200:
		var bush := MeshUtil.part(self, bush_mesh, bush_mat, _random_spot(5.0) + Vector3(0, 0.3, 0))
		bush.scale = Vector3.ONE * rng.randf_range(0.6, 1.4)


## Handwerksdorf: alle Werkstätten im Halbkreis um einen Platz, offen Richtung Startpunkt.
func _build_village() -> void:
	var plaza := CylinderMesh.new()
	plaza.top_radius = VILLAGE_RADIUS + 3.0
	plaza.bottom_radius = plaza.top_radius
	plaza.height = 0.04
	MeshUtil.part(self, plaza, MeshUtil.mat(Color(0.55, 0.47, 0.36), 0.0, 1.0), VILLAGE_CENTER + Vector3(0, 0.02, 0))
	_add_campfire(VILLAGE_CENTER)

	var ids: Array = Game.stations.keys()
	var spread := deg_to_rad(300.0)
	for i in ids.size():
		# Winkel ab Norden gemessen; die Lücke im Norden zeigt zum Startpunkt
		var angle := deg_to_rad(30.0) + spread * i / maxf(ids.size() - 1, 1)
		var pos := VILLAGE_CENTER + Vector3(sin(angle), 0, -cos(angle)) * VILLAGE_RADIUS
		var station = StationScript.new()
		station.setup(ids[i])
		station.position = pos
		var to_center := VILLAGE_CENTER - pos
		station.rotation.y = atan2(-to_center.x, -to_center.z)
		add_child(station)


func _build_pond() -> void:
	var sand := CylinderMesh.new()
	sand.top_radius = POND_RADIUS + 1.5
	sand.bottom_radius = sand.top_radius
	sand.height = 0.03
	MeshUtil.part(self, sand, MeshUtil.mat(Color(0.7, 0.64, 0.45), 0.0, 1.0), POND_CENTER + Vector3(0, 0.015, 0))
	var water := CylinderMesh.new()
	water.top_radius = POND_RADIUS
	water.bottom_radius = POND_RADIUS
	water.height = 0.03
	var water_mat := StandardMaterial3D.new()
	water_mat.albedo_color = Color(0.2, 0.42, 0.6, 0.85)
	water_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	water_mat.metallic = 0.3
	water_mat.roughness = 0.05
	MeshUtil.part(self, water, water_mat, POND_CENTER + Vector3(0, 0.03, 0))
	for i in 4:
		var angle := TAU * i / 4.0 + 0.4
		_add_resource("fishing_spot", POND_CENTER + Vector3(cos(angle), 0, sin(angle)) * (POND_RADIUS - 2.0))


func _build_camp(camp: Dictionary) -> void:
	var center: Vector3 = camp["pos"]
	var style: String = camp["style"]
	var dirt := CylinderMesh.new()
	dirt.top_radius = 10.0 if style == "lair" else 7.0
	dirt.bottom_radius = dirt.top_radius
	dirt.height = 0.04
	MeshUtil.part(self, dirt, MeshUtil.mat(Color(0.38, 0.3, 0.2), 0.0, 1.0), center + Vector3(0, 0.02, 0))

	match style:
		"camp":
			_add_campfire(center)
			var cloth := MeshUtil.mat(Color(0.55, 0.45, 0.3))
			var tent_mesh := PrismMesh.new()
			tent_mesh.size = Vector3(2.4, 1.8, 3.0)
			for i in 3:
				var angle := TAU * i / 3.0 + 0.4
				var tent := StaticBody3D.new()
				tent.position = center + Vector3(cos(angle), 0, sin(angle)) * 5.0
				tent.rotation.y = -angle
				add_child(tent)
				MeshUtil.part(tent, tent_mesh, cloth, Vector3(0, 0.9, 0))
				_add_box_collision(tent, Vector3(2.0, 1.8, 3.0), Vector3(0, 0.9, 0))
			var crate_mat := MeshUtil.mat(Color(0.5, 0.36, 0.2))
			for offset: Vector3 in [Vector3(2.5, 0.4, 3.5), Vector3(3.3, 0.4, 3.0)]:
				var crate := StaticBody3D.new()
				crate.position = center + offset
				add_child(crate)
				MeshUtil.part(crate, MeshUtil.box(Vector3(0.8, 0.8, 0.8)), crate_mat)
				_add_box_collision(crate, Vector3(0.8, 0.8, 0.8), Vector3.ZERO)
		"den":
			var bone_mat := MeshUtil.mat(Color(0.9, 0.88, 0.8))
			for i in 6:
				var bone := MeshUtil.part(self, MeshUtil.box(Vector3(0.08, 0.08, 0.5)), bone_mat,
					center + Vector3(rng.randf_range(-4, 4), 0.05, rng.randf_range(-4, 4)))
				bone.rotation.y = rng.randf() * TAU
		"lair":
			_add_campfire(center + Vector3(0, 0, 4))
			var stone_mat := MeshUtil.mat(Color(0.4, 0.4, 0.42))
			for i in 7:
				var angle := TAU * i / 7.0
				var stone := StaticBody3D.new()
				stone.position = center + Vector3(cos(angle), 0, sin(angle)) * 9.0 + Vector3(0, 1.5, 0)
				stone.rotation = Vector3(rng.randf_range(-0.1, 0.1), rng.randf() * TAU, rng.randf_range(-0.1, 0.1))
				add_child(stone)
				var size := Vector3(1.2, 3.0, 0.8)
				MeshUtil.part(stone, MeshUtil.box(size), stone_mat)
				_add_box_collision(stone, size, Vector3.ZERO)


func _add_campfire(pos: Vector3) -> void:
	var stone_mat := MeshUtil.mat(Color(0.35, 0.35, 0.35))
	for i in 8:
		var angle := TAU * i / 8.0
		MeshUtil.part(self, MeshUtil.box(Vector3(0.25, 0.18, 0.25)), stone_mat,
			pos + Vector3(cos(angle) * 0.55, 0.09, sin(angle) * 0.55))
	var flame_mesh := CylinderMesh.new()
	flame_mesh.top_radius = 0.0
	flame_mesh.bottom_radius = 0.35
	flame_mesh.height = 0.8
	var flame_mat := StandardMaterial3D.new()
	flame_mat.albedo_color = Color(1.0, 0.5, 0.1)
	flame_mat.emission_enabled = true
	flame_mat.emission = Color(1.0, 0.45, 0.1)
	flame_mat.emission_energy_multiplier = 4.0
	MeshUtil.part(self, flame_mesh, flame_mat, pos + Vector3(0, 0.4, 0))
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.6, 0.3)
	light.light_energy = 2.0
	light.omni_range = 7.0
	light.position = pos + Vector3(0, 1.0, 0)
	add_child(light)
