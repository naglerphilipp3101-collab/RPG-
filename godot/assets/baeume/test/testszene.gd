extends Node3D
## Kleiner Fichtenwald zum Ansehen. F = alle Bäume fällen (Nachwachsen nach 6 s).
## Pfeiltasten = drehen, Mausrad = Zoom.

const BAUM := preload("../baum.tscn")
const BUSCH := preload("../aeste_busch.tscn")
var _alle: Array = []
var _kamera: Camera3D
var _winkel := 0.4
var _abstand := 26.0
var _hoehe := 0.45
var ziel := Vector3(0, 4, 0)
var _arten: Array = [Baum.Art.FICHTE]


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--art=eiche":
			_arten = [Baum.Art.EICHE]
		elif a == "--art=kiefer":
			_arten = [Baum.Art.KIEFER]
		elif a == "--art=gemischt":
			_arten = [Baum.Art.FICHTE, Baum.Art.KIEFER, Baum.Art.EICHE]
	var env := Environment.new()
	var himmel := Sky.new()
	var hm := ProceduralSkyMaterial.new()
	hm.sky_top_color = Color(0.35, 0.5, 0.75)
	hm.ground_horizon_color = Color(0.55, 0.6, 0.6)
	himmel.sky_material = hm
	env.background_mode = Environment.BG_SKY
	env.sky = himmel
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	env.fog_enabled = true
	env.fog_density = 0.004
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-40, -140, 0)
	sonne.shadow_enabled = true
	sonne.directional_shadow_max_distance = 80.0
	add_child(sonne)

	var boden := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(120, 120)
	boden.mesh = ebene
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.22, 0.26, 0.13)
	bm.roughness = 1.0
	boden.material_override = bm
	add_child(boden)

	var hilfe0 := ""
	if "--buesche" in OS.get_cmdline_user_args():
		for i in 4:
			var bu: AesteBusch = BUSCH.instantiate()
			bu.zufalls_variation = false
			bu.position = Vector3(-2.4 + i * 1.6, 0, 0)
			add_child(bu)
			if i < 3:
				bu.variante = i + 1
			else:
				bu.ernten()
		var sp := MeshInstance3D.new()
		var ka := CapsuleMesh.new()
		ka.radius = 0.25
		ka.height = 1.8
		sp.mesh = ka
		sp.position = Vector3(-4.0, 0.9, 0)
		add_child(sp)
		_kamera = Camera3D.new()
		add_child(_kamera)
		_kamera.position = Vector3(-0.8, 1.8, 5.2)
		_kamera.look_at(Vector3(-0.8, 0.6, 0))
		_screenshot()
		return
	if "--varianten" in OS.get_cmdline_user_args():
		_varianten_reihe()
		return
	# Wald: alte und junge Fichten, leicht zufällig verteilt
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	for i in 34:
		var p := Vector3(rng.randf_range(-22, 22), 0, rng.randf_range(-24, 6))
		if p.length() < 4.0:
			continue
		var b: Baum = BAUM.instantiate()
		b.position = p
		b.art = _arten[rng.randi() % _arten.size()]
		b.alter = Baum.Alter.ALT if rng.randf() < 0.55 else Baum.Alter.JUNG
		b.respawn_zeit = 6.0
		add_child(b)
		_alle.append(b)
	# Äste-Büsche verstreut, vorne rechts einer geerntet
	for i in 26:
		var p := Vector3(rng.randf_range(-16, 16), 0, rng.randf_range(-16, 10))
		var bu: AesteBusch = BUSCH.instantiate()
		bu.position = p
		bu.respawn_zeit = 6.0
		add_child(bu)
		_alle.append(bu)
	for p in [Vector3(1.8, 0, 10.5), Vector3(-1.2, 0, 11.0)]:
		var bu: AesteBusch = BUSCH.instantiate()
		bu.position = p
		bu.respawn_zeit = 6.0
		add_child(bu)
		_alle.append(bu)
	var geerntet: AesteBusch = BUSCH.instantiate()
	geerntet.position = Vector3(3.2, 0, 11.5)
	geerntet.respawn_zeit = 6.0
	add_child(geerntet)
	geerntet.ernten()
	_alle.append(geerntet)
	# vorne: je ein gefällter Baum (Stumpf)
	for a in [Baum.Alter.JUNG, Baum.Alter.ALT]:
		var b: Baum = BAUM.instantiate()
		b.art = _arten[0]
		b.position = Vector3(-2.5 + a * 5.0, 0, 9)
		b.alter = a
		b.respawn_zeit = 6.0
		add_child(b)
		b.faellen()
		_alle.append(b)

	# Spieler-Platzhalter (1,8 m)
	var spieler := MeshInstance3D.new()
	var kapsel := CapsuleMesh.new()
	kapsel.radius = 0.25
	kapsel.height = 1.8
	spieler.mesh = kapsel
	spieler.position = Vector3(0.5, 0.9, 7.5)
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.75, 0.75, 0.85)
	spieler.material_override = sm
	add_child(spieler)

	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera_setzen()
	var hilfe := Label.new()
	hilfe.text = "F: fällen  |  Pfeiltasten: drehen  |  Mausrad: Zoom"
	hilfe.position = Vector2(12, 8)
	add_child(hilfe)
	if "--screenshot" in OS.get_cmdline_user_args():
		_screenshot()


func _varianten_reihe() -> void:
	# alle 6 Modelle nebeneinander, ohne Zufallsdrehung
	var i := 0
	for a in [Baum.Alter.JUNG, Baum.Alter.ALT]:
		for v in [1, 2, 3]:
			var b: Baum = BAUM.instantiate()
			b.zufalls_variation = false
			b.position = Vector3(-11.0 + i * 4.4, 0, 0)
			add_child(b)
			b.art = _arten[0]
			b.alter = a
			b.variante = v
			i += 1
	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera.position = Vector3(0, 5.5, 15.5)
	_kamera.look_at(Vector3(0, 5.3, 0))
	_screenshot()


func _kamera_setzen() -> void:
	_kamera.position = ziel + Vector3(sin(_winkel), _hoehe, cos(_winkel)).normalized() * _abstand
	_kamera.look_at(ziel)


func _process(delta: float) -> void:
	var d := Input.get_axis("ui_left", "ui_right")
	if d != 0.0:
		_winkel += d * delta * 1.2
		_kamera_setzen()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and e.keycode == KEY_F:
		for b in _alle:
			if b is Baum:
				b.faellen()
			else:
				b.ernten()
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_abstand = maxf(4.0, _abstand - 1.5)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_abstand = minf(80.0, _abstand + 1.5)
		_kamera_setzen()


func _screenshot() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--ansicht=auge":      # Spieler-Augenhöhe
			_kamera.position = Vector3(1.5, 1.7, 13)
			_kamera.look_at(Vector3(0, 4.5, -6))
		elif a == "--ansicht=busch":   # Büsche aus Spielerhöhe, leicht nach unten
			_kamera.position = Vector3(0.5, 1.7, 15.5)
			_kamera.look_at(Vector3(0.8, 0.6, 9.5))
		elif a == "--ansicht=nah":     # unter einer alten Fichte nach oben
			var b: Baum = _alle[0]
			for x in _alle:
				if x.alter == Baum.Alter.ALT and not x.ist_gefaellt and x.position.z > b.position.z:
					b = x
			_kamera.position = b.position + Vector3(4.5, 1.7, 5.5)
			_kamera.look_at(b.position + Vector3(0, 5.0, 0))
	for i in 40:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(OS.get_user_data_dir() + "/screenshot.png")
	get_tree().quit()
