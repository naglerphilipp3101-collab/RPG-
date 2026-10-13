extends Node3D
## Wiese mit Hanf, Beeren und Kräutern. E = alles sammeln (wächst nach 6 s nach). Pfeiltasten = drehen, Mausrad = Zoom.

const PFLANZE := preload("../sammelpflanze.tscn")
var _alle: Array = []
var _kamera: Camera3D
var _winkel := 0.3
var _abstand := 9.0
var ziel := Vector3(0, 0.8, 0)


func _ready() -> void:
	var env := Environment.new()
	var himmel := Sky.new()
	var hm := ProceduralSkyMaterial.new()
	hm.sky_top_color = Color(0.35, 0.5, 0.75)
	himmel.sky_material = hm
	env.background_mode = Environment.BG_SKY
	env.sky = himmel
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-45, -140, 0)
	sonne.shadow_enabled = true
	add_child(sonne)
	var boden := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(60, 60)
	boden.mesh = ebene
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.22, 0.26, 0.13)
	boden.material_override = bm
	add_child(boden)
	var spieler := MeshInstance3D.new()
	var kapsel := CapsuleMesh.new()
	kapsel.radius = 0.25
	kapsel.height = 1.8
	spieler.mesh = kapsel
	spieler.position = Vector3(-1.2, 0.9, 2.2)
	add_child(spieler)

	var args := OS.get_cmdline_user_args()
	if "--beeren" in args or "--kraeuter" in args:
		# 4 Farben nebeneinander + vorne rechts ein geerntetes Exemplar
		var art := Sammelpflanze.Art.BEEREN if "--beeren" in args else Sammelpflanze.Art.KRAEUTER
		var farben := [0, 1, 2, 3] if art == Sammelpflanze.Art.BEEREN else [4, 3, 5, 0]
		var abst := 1.3 if art == Sammelpflanze.Art.BEEREN else 0.8
		for i in 5:
			var p: Sammelpflanze = PFLANZE.instantiate()
			p.zufalls_variation = false
			p.position = Vector3((i - 2) * abst, 0, 0)
			add_child(p)
			p.art = art
			p.variante = i % 3 + 1
			p.farbe = farben[mini(i, 3)]
			if i == 4:
				p.sammeln()
		spieler.position = Vector3(-3.2 * abst, 0.9, 0)
		ziel = Vector3(0, 0.4 if art == Sammelpflanze.Art.BEEREN else 0.25, 0)
		_abstand = 4.6 if art == Sammelpflanze.Art.BEEREN else 3.0
		_winkel = 0.0
	elif "--varianten" in args:
		for i in 4:
			var p: Sammelpflanze = PFLANZE.instantiate()
			p.zufalls_variation = false
			p.position = Vector3(-1.5 + i * 1.3, 0, 0)
			add_child(p)
			if i < 3:
				p.variante = i + 1
			else:
				p.sammeln()
		spieler.position = Vector3(-3.0, 0.9, 0)
		ziel = Vector3(0, 0.8, 0)
		_abstand = 4.2
		_winkel = 0.0
	else:
		# Wiese: Hanf, Beerensträucher, Kräuter in allen Farben
		var rng := RandomNumberGenerator.new()
		rng.seed = 7
		for i in 60:
			var p: Sammelpflanze = PFLANZE.instantiate()
			p.position = Vector3(rng.randf_range(-7, 7), 0, rng.randf_range(-7, 2))
			p.respawn_zeit = 6.0
			var art: int = [0, 1, 2, 2][i % 4]
			add_child(p)
			p.art = art
			if art == 1:
				p.farbe = [0, 1, 2, 3][rng.randi() % 4]
			elif art == 2:
				p.farbe = [4, 3, 5, 0][rng.randi() % 4]
			_alle.append(p)
		_alle[0].sammeln()
		_alle[1].sammeln()

	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera_setzen()
	var hilfe := Label.new()
	hilfe.text = "E: sammeln  |  Pfeiltasten: drehen  |  Mausrad: Zoom"
	hilfe.position = Vector2(12, 8)
	add_child(hilfe)
	if "--screenshot" in OS.get_cmdline_user_args():
		_screenshot()


func _kamera_setzen() -> void:
	_kamera.position = ziel + Vector3(sin(_winkel), 0.32, cos(_winkel)).normalized() * _abstand
	_kamera.look_at(ziel)


func _process(delta: float) -> void:
	var d := Input.get_axis("ui_left", "ui_right")
	if d != 0.0:
		_winkel += d * delta * 1.2
		_kamera_setzen()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and e.keycode == KEY_E:
		for p in _alle:
			p.sammeln()
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_abstand = maxf(2.0, _abstand - 0.5)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_abstand = minf(40.0, _abstand + 0.5)
		_kamera_setzen()


func _screenshot() -> void:
	for i in 40:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(OS.get_user_data_dir() + "/screenshot.png")
	get_tree().quit()
