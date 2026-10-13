extends Node3D
## Zeigt alle 6 Tiers x 5 Größen. Leertaste = alles abbauen (Respawn nach 5 s).
## Mausrad = Zoom, Pfeiltasten = Kamera drehen.

const VORKOMMEN := preload("../erz_vorkommen.tscn")
var _alle: Array = []
var _kamera: Camera3D
var _winkel := 0.0
var _abstand := 18.0


func _ready() -> void:
	var umgebung := WorldEnvironment.new()
	var env := Environment.new()
	var himmel := Sky.new()
	himmel.sky_material = ProceduralSkyMaterial.new()
	env.background_mode = Environment.BG_SKY
	env.sky = himmel
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_bloom = 0.1
	env.ssao_enabled = true
	umgebung.environment = env
	add_child(umgebung)

	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-50, -35, 0)
	sonne.shadow_enabled = true
	sonne.light_energy = 1.2
	add_child(sonne)

	var boden := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(80, 80)
	boden.mesh = ebene
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.16, 0.14, 0.11)
	bm.roughness = 0.95
	boden.material_override = bm
	add_child(boden)

	# Zeilen = Tiers, Spalten = Größe 1..5 + abgebaut
	for t in 6:
		for g in 6:
			var v: ErzVorkommen = VORKOMMEN.instantiate()
			v.respawn_zeit = 5.0
			v.position = Vector3((g - 2.5) * 3.6, 0, (t - 2.5) * 3.6)
			v.rotation.y = 0.6
			add_child(v)
			v.tier = t
			v.groesse = mini(g + 1, 5)
			if g == 5:
				v.groesse = 3
				v.abbauen()
			_alle.append(v)

	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera_setzen()

	var hilfe := Label.new()
	hilfe.text = "Leertaste: abbauen  |  Pfeiltasten: drehen  |  Mausrad: Zoom\nZeilen: Iron, Palladium, Mithril, Glacialore, Sungold, Darksteel  |  Spalten: Größe 1-5, abgebaut"
	hilfe.position = Vector2(12, 8)
	add_child(hilfe)

	if "--screenshot" in OS.get_cmdline_user_args():
		_screenshot()


var ziel := Vector3.ZERO


func _kamera_setzen() -> void:
	_kamera.position = ziel + Vector3(sin(_winkel), 0.85, cos(_winkel)).normalized() * _abstand
	_kamera.look_at(ziel)


func _process(delta: float) -> void:
	var d := Input.get_axis("ui_left", "ui_right")
	if d != 0.0:
		_winkel += d * delta * 1.5
		_kamera_setzen()


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("ui_accept"):
		for v in _alle:
			v.abbauen()
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_abstand = maxf(6.0, _abstand - 1.5)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_abstand = minf(60.0, _abstand + 1.5)
		_kamera_setzen()


func _screenshot() -> void:
	for args in OS.get_cmdline_user_args():
		if args.begins_with("--abstand="):
			_abstand = float(args.split("=")[1])
		if args.begins_with("--ziel="):   # --ziel=x,z
			var xz := args.split("=")[1].split(",")
			ziel = Vector3(float(xz[0]), 0, float(xz[1]))
	_kamera_setzen()
	for i in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(OS.get_user_data_dir() + "/screenshot.png")
	print("SCREENSHOT ", OS.get_user_data_dir() + "/screenshot.png")
	get_tree().quit()
