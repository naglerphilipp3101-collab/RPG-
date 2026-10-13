extends Node3D
## Baut die Spielwelt per Code auf: Insel (Terrain3D, aus dem Weltgenerator) oder flache Testwiese,
## darauf Startgebiet mit Handwerksdorf, Rohstoffen, Gegnerlagern, dazu Spieler und HUD.
##
## Die Inhalte des Startgebiets sind in lokalen Koordinaten um `area` angelegt; _g() setzt sie auf die Geländehöhe.
## Auf der flachen Testwiese (automatische Tests) ist die Höhe überall 0.

const PlayerScript := preload("res://scripts/player.gd")
const EnemyScript := preload("res://scripts/enemy.gd")
const HudScript := preload("res://scripts/hud.gd")
const MeshUtil := preload("res://scripts/mesh_util.gd")
const ResourceNodeScript := preload("res://scripts/resource_node.gd")
const StationScript := preload("res://scripts/crafting_station.gd")
const SaveGame := preload("res://scripts/save_game.gd")
const NaturScript := preload("res://scripts/natur.gd")

const ISLAND_DATA := "res://welt_daten"
const ISLAND_TERRAIN := "res://welt_daten/terrain3d"
## Mitte des Startgebiets auf der Insel: der Marker „Startdorf“ aus marker.json; das hier gilt nur, falls er fehlt
const ISLAND_START := Vector3(-1026.6, 0, 2569.5)

const VILLAGE_CENTER := Vector3(0, 0, 24)
const VILLAGE_RADIUS := 9.0
const AREA_SIZE := 300.0 # Seitenlänge des Startgebiets mit Rohstoffen
const NORTH_ZONE_Z := -80.0 # nördlich davon (lokal): Tier-2-Rohstoffe
const POND_CENTER := Vector3(-45, 0, 25)
const POND_RADIUS := 9.0

var rng := RandomNumberGenerator.new()
var clear_spots: Array[Vector3] = []
var area: Node3D # Wurzel des Startgebiets (lokale Koordinaten)
var terrain = null # Terrain3D, wenn die Insel geladen ist
var natur = null # Natur-Streamer (scripts/natur.gd), nur auf der Insel
var island := false
var world_size := 8192.0 # Seitenlänge der Insel in Metern (aus welt.json)


func _ready() -> void:
	rng.seed = 7
	var args := OS.get_cmdline_user_args()
	var autotest := args.has("--autotest")
	# Insel nur, wenn Terrain3D und importierte Weltdaten vorhanden sind; Tests laufen auf der flachen Wiese
	island = ClassDB.class_exists("Terrain3D") and DirAccess.dir_exists_absolute(ISLAND_TERRAIN) \
		and (not autotest or args.has("--island"))
	Game.world_id = "insel" if island else "testwiese"

	area = Node3D.new()
	area.name = "Startgebiet"
	add_child(area)
	_build_environment()
	if island:
		await _build_island()
	else:
		_build_ground()

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
	if not island:
		# Teich: mehrere Punkte, damit nichts im Wasser wächst
		clear_spots.append(POND_CENTER)
		for i in 8:
			var angle := TAU * i / 8.0
			clear_spots.append(POND_CENTER + Vector3(cos(angle), 0, sin(angle)) * POND_RADIUS * 0.6)

	if island:
		_build_coast_fishing()
	else:
		_build_pond()
	_build_village()
	_scatter_nature()
	for camp in camps:
		_build_camp(camp)

	var player: Node3D = PlayerScript.new()
	player.name = "Player"
	player.position = area.position + _g(Vector3(0, 0, 6)) + Vector3(0, 1.0, 0)
	add_child(player)
	if terrain:
		terrain.set_camera(player.camera)
	if island:
		# Bäume, Büsche und Sammelpflanzen auf der ganzen Insel (rund um den Spieler nachgeladen)
		natur = NaturScript.new()
		natur.name = "Natur"
		natur.setup(self, player, ISLAND_DATA)
		add_child(natur)

	var hud = HudScript.new()
	hud.name = "HUD"
	add_child(hud)
	hud.bind_player(player)
	if island:
		var map_path := ProjectSettings.globalize_path(ISLAND_DATA.path_join("uebersicht.png"))
		if FileAccess.file_exists(map_path):
			var map_texture := ImageTexture.create_from_image(Image.load_from_file(map_path))
			hud.setup_minimap(self, map_texture, world_size, get_tree().get_nodes_in_group("welt_marker"))

	for camp in camps:
		var home: Vector3 = area.position + _g(camp["pos"])
		for i in int(camp["count"]):
			var enemy = EnemyScript.new()
			enemy.setup(camp["type"], home)
			var spot := Vector3(camp["pos"]) + Vector3(rng.randf_range(-4, 4), 0, rng.randf_range(-4, 4))
			enemy.position = area.position + _g(spot) + Vector3(0, 0.5, 0)
			add_child(enemy)

	if autotest:
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


# --- Gelände ------------------------------------------------------------

## Geländehöhe an einer lokalen Position im Startgebiet (Wasser/außerhalb: 0).
func _ground(local: Vector3) -> float:
	if terrain == null:
		return 0.0
	var h: float = terrain.get("data").get_height(area.position + Vector3(local.x, 0, local.z))
	return 0.0 if is_nan(h) else h


## Lokale Position auf die Geländehöhe setzen (die y-Angabe bleibt als Versatz erhalten).
func _g(local: Vector3) -> Vector3:
	return Vector3(local.x, local.y + _ground(local), local.z)


## Lädt die importierte Insel (siehe tests/welt_importieren.gd) mit Bodentexturen, Meer und Siedlungsmarkern.
func _build_island() -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ISLAND_DATA.path_join("welt.json")))
	area.position = _island_start()
	# Jede generierte Welt hat ihren eigenen Spielstand-Ort (Positionen aus einer anderen Welt passen nicht)
	Game.world_id = "insel_%d" % int(meta.get("params", {}).get("seed", 0))
	# Vorläufige Kamera, bis der Spieler existiert (Terrain3D braucht eine aktive Kamera)
	var temp_camera := Camera3D.new()
	add_child(temp_camera)
	temp_camera.position = area.position + Vector3(0, 80, 0)

	var welt = load("res://assets/welt/welt_import.gd").new()
	welt.name = "Insel"
	welt.daten_ordner = ISLAND_DATA
	add_child(welt)
	terrain = ClassDB.instantiate("Terrain3D")
	terrain.name = "Terrain3D"
	terrain.set("data_directory", ISLAND_TERRAIN)
	terrain.set("collision_radius", 192)
	terrain.set("vertex_spacing", float(meta.get("meter_pro_pixel", 1.0))) # z. B. 2 m bei der 16-km-Welt
	welt.add_child(terrain)
	welt._texturen_einrichten(terrain)
	terrain.get("material").set("world_background", 0)

	var size: float = float(meta.get("welt_m", 8192))
	world_size = size
	var sea := PlaneMesh.new()
	sea.size = Vector2(size * 3, size * 3)
	var sea_mat := StandardMaterial3D.new()
	sea_mat.albedo_color = Color(0.12, 0.32, 0.5, 0.85)
	sea_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sea_mat.roughness = 0.08
	sea_mat.metallic_specular = 0.8
	MeshUtil.part(self, sea, sea_mat)
	var seabed := MeshUtil.part(self, sea, MeshUtil.mat(Color(0.32, 0.3, 0.24), 0.0, 1.0))
	seabed.position.y = float(meta["hoehe"]["min"]) + 0.3
	welt._marker_importieren()
	welt._seen_importieren(sea_mat)
	welt._wege_importieren() # Wegverläufe und Brücken (das Gelände unter den Wegen ist schon eingeebnet)
	welt._hoehe_bild = null # Höhendaten wurden nur für die Brückenpfeiler gebraucht

	# Terrain3D lädt seine Regionen erst in den nächsten Frames
	for i in 3:
		await get_tree().process_frame
	temp_camera.queue_free()


## Position des Markers „Startdorf“ (x/z) aus marker.json, sonst ISLAND_START.
func _island_start() -> Vector3:
	var path := ISLAND_DATA.path_join("marker.json")
	if FileAccess.file_exists(path):
		for m in JSON.parse_string(FileAccess.get_file_as_string(path)):
			if m.get("name", "") == "Startdorf":
				return Vector3(float(m["x"]), 0, float(m["z"]))
	return ISLAND_START


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
	plane.size = Vector2(AREA_SIZE, AREA_SIZE)
	var ground := StaticBody3D.new()
	area.add_child(ground)
	MeshUtil.part(ground, plane, ground_mat)
	_add_box_collision(ground, Vector3(AREA_SIZE, 2, AREA_SIZE), Vector3(0, -1, 0))

	# Unsichtbare Weltgrenze
	var half := AREA_SIZE / 2.0
	for wall: Array in [
		[Vector3(AREA_SIZE, 20, 1), Vector3(0, 10, -half)],
		[Vector3(AREA_SIZE, 20, 1), Vector3(0, 10, half)],
		[Vector3(1, 20, AREA_SIZE), Vector3(-half, 10, 0)],
		[Vector3(1, 20, AREA_SIZE), Vector3(half, 10, 0)],
	]:
		_add_box_collision(ground, wall[0], wall[1])


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
	env.fog_density = 0.0007 if island else 0.006 # auf der Insel weiter sehen
	env.ssao_enabled = true
	env.glow_enabled = true
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 120.0 if island else 80.0
	add_child(sun)


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


## Zufälliger freier Punkt im Startgebiet (lokal, Höhe 0). Auf der Insel nur an Land.
func _random_spot(margin: float, z_min := -INF, z_max := INF) -> Vector3:
	var half := AREA_SIZE * 0.47
	var lo := maxf(-half, z_min)
	var hi := minf(half, z_max)
	for attempt in 200:
		var pos := Vector3(rng.randf_range(-half, half), 0.0, rng.randf_range(lo, hi))
		if _is_clear(pos, margin) and (not island or _ground(pos) > 1.0):
			return pos
	return Vector3.ZERO


func _add_resource(id: String, pos: Vector3, scale_factor := 1.0, rock_size := Vector3.ONE) -> Node3D:
	var node = ResourceNodeScript.new()
	node.setup(id)
	node.size_scale = scale_factor
	node.rock_size = rock_size
	node.position = _g(pos)
	node.rotation.y = rng.randf() * TAU
	area.add_child(node)
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
		var bush := MeshUtil.part(area, bush_mesh, bush_mat, _g(_random_spot(5.0) + Vector3(0, 0.3, 0)))
		bush.scale = Vector3.ONE * rng.randf_range(0.6, 1.4)


## Handwerksdorf: alle Werkstätten im Halbkreis um einen Platz, offen Richtung Startpunkt.
func _build_village() -> void:
	var plaza := CylinderMesh.new()
	plaza.top_radius = VILLAGE_RADIUS + 3.0
	plaza.bottom_radius = plaza.top_radius
	plaza.height = 0.6 if island else 0.04 # auf der Insel etwas dicker, damit leichte Hänge abgedeckt sind
	MeshUtil.part(area, plaza, MeshUtil.mat(Color(0.55, 0.47, 0.36), 0.0, 1.0), _g(VILLAGE_CENTER + Vector3(0, 0.02, 0)))
	_add_campfire(VILLAGE_CENTER)

	var ids: Array = Game.stations.keys()
	var spread := deg_to_rad(300.0)
	for i in ids.size():
		# Winkel ab Norden gemessen; die Lücke im Norden zeigt zum Startpunkt
		var angle := deg_to_rad(30.0) + spread * i / maxf(ids.size() - 1, 1)
		var pos := VILLAGE_CENTER + Vector3(sin(angle), 0, -cos(angle)) * VILLAGE_RADIUS
		var station = StationScript.new()
		station.setup(ids[i])
		station.position = _g(pos)
		var to_center := VILLAGE_CENTER - pos
		station.rotation.y = atan2(-to_center.x, -to_center.z)
		area.add_child(station)


func _build_pond() -> void:
	var sand := CylinderMesh.new()
	sand.top_radius = POND_RADIUS + 1.5
	sand.bottom_radius = sand.top_radius
	sand.height = 0.03
	MeshUtil.part(area, sand, MeshUtil.mat(Color(0.7, 0.64, 0.45), 0.0, 1.0), POND_CENTER + Vector3(0, 0.015, 0))
	var water := CylinderMesh.new()
	water.top_radius = POND_RADIUS
	water.bottom_radius = POND_RADIUS
	water.height = 0.03
	var water_mat := StandardMaterial3D.new()
	water_mat.albedo_color = Color(0.2, 0.42, 0.6, 0.85)
	water_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	water_mat.metallic = 0.3
	water_mat.roughness = 0.05
	MeshUtil.part(area, water, water_mat, POND_CENTER + Vector3(0, 0.03, 0))
	for i in 4:
		var angle := TAU * i / 4.0 + 0.4
		_add_resource("fishing_spot", POND_CENTER + Vector3(cos(angle), 0, sin(angle)) * (POND_RADIUS - 2.0))


## Auf der Insel: Fischgründe an der nächstgelegenen Küste statt eines Teichs.
func _build_coast_fishing() -> void:
	var best := Vector3.ZERO
	var best_dist := INF
	for i in 32:
		var dir := Vector3(cos(TAU * i / 32.0), 0, sin(TAU * i / 32.0))
		var d := 8.0
		while d < 1500.0:
			if _ground(dir * d) < -0.5:
				if d < best_dist:
					best_dist = d
					best = dir * d
				break
			d += 4.0
	if best_dist == INF:
		return
	var along := Vector3(-best.z, 0, best.x).normalized()
	for i in 4:
		var spot := best + best.normalized() * 2.0 + along * (i - 1.5) * 9.0
		var node := _add_resource("fishing_spot", spot)
		node.position.y = 0.0 # Ringe liegen auf dem Meeresspiegel


func _build_camp(camp: Dictionary) -> void:
	var center: Vector3 = camp["pos"]
	var style: String = camp["style"]
	var dirt := CylinderMesh.new()
	dirt.top_radius = 10.0 if style == "lair" else 7.0
	dirt.bottom_radius = dirt.top_radius
	dirt.height = 0.6 if island else 0.04
	MeshUtil.part(area, dirt, MeshUtil.mat(Color(0.38, 0.3, 0.2), 0.0, 1.0), _g(center + Vector3(0, 0.02, 0)))

	match style:
		"camp":
			_add_campfire(center)
			var cloth := MeshUtil.mat(Color(0.55, 0.45, 0.3))
			var tent_mesh := PrismMesh.new()
			tent_mesh.size = Vector3(2.4, 1.8, 3.0)
			for i in 3:
				var angle := TAU * i / 3.0 + 0.4
				var tent := StaticBody3D.new()
				tent.position = _g(center + Vector3(cos(angle), 0, sin(angle)) * 5.0)
				tent.rotation.y = -angle
				area.add_child(tent)
				MeshUtil.part(tent, tent_mesh, cloth, Vector3(0, 0.9, 0))
				_add_box_collision(tent, Vector3(2.0, 1.8, 3.0), Vector3(0, 0.9, 0))
			var crate_mat := MeshUtil.mat(Color(0.5, 0.36, 0.2))
			for offset: Vector3 in [Vector3(2.5, 0.4, 3.5), Vector3(3.3, 0.4, 3.0)]:
				var crate := StaticBody3D.new()
				crate.position = _g(center + offset)
				area.add_child(crate)
				MeshUtil.part(crate, MeshUtil.box(Vector3(0.8, 0.8, 0.8)), crate_mat)
				_add_box_collision(crate, Vector3(0.8, 0.8, 0.8), Vector3.ZERO)
		"den":
			var bone_mat := MeshUtil.mat(Color(0.9, 0.88, 0.8))
			for i in 6:
				var bone := MeshUtil.part(area, MeshUtil.box(Vector3(0.08, 0.08, 0.5)), bone_mat,
					_g(center + Vector3(rng.randf_range(-4, 4), 0.05, rng.randf_range(-4, 4))))
				bone.rotation.y = rng.randf() * TAU
		"lair":
			_add_campfire(center + Vector3(0, 0, 4))
			var stone_mat := MeshUtil.mat(Color(0.4, 0.4, 0.42))
			for i in 7:
				var angle := TAU * i / 7.0
				var stone := StaticBody3D.new()
				stone.position = _g(center + Vector3(cos(angle), 0, sin(angle)) * 9.0 + Vector3(0, 1.5, 0))
				stone.rotation = Vector3(rng.randf_range(-0.1, 0.1), rng.randf() * TAU, rng.randf_range(-0.1, 0.1))
				area.add_child(stone)
				var size := Vector3(1.2, 3.0, 0.8)
				MeshUtil.part(stone, MeshUtil.box(size), stone_mat)
				_add_box_collision(stone, size, Vector3.ZERO)


func _add_campfire(local: Vector3) -> void:
	var pos := _g(local)
	var stone_mat := MeshUtil.mat(Color(0.35, 0.35, 0.35))
	for i in 8:
		var angle := TAU * i / 8.0
		MeshUtil.part(area, MeshUtil.box(Vector3(0.25, 0.18, 0.25)), stone_mat,
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
	MeshUtil.part(area, flame_mesh, flame_mat, pos + Vector3(0, 0.4, 0))
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.6, 0.3)
	light.light_energy = 2.0
	light.omni_range = 7.0
	light.position = pos + Vector3(0, 1.0, 0)
	area.add_child(light)
