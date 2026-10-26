extends Node3D
## Alle Props nebeneinander: vorne heil, dahinter kaputt. F6 im Editor.
## Pfeiltasten links/rechts: drehen, hoch/runter: an der Reihe entlangfahren, Mausrad: Zoom, N: Tag/Nacht.
## Bildschirmfoto: -- --screenshot [--ziel=x,z|<modell>|haus] [--abstand=m] [--winkel=grad] [--nacht]
## (speichert user://galerie.png)

var _kamera: Camera3D
var _sonne: DirectionalLight3D
var _env: Environment
var _winkel := 0.5
var _abstand := 9.0
var ziel := Vector3.ZERO
var _haus_mitte := Vector3.ZERO
var _positionen := {}


func _ready() -> void:
	var umgebung := WorldEnvironment.new()
	_env = Environment.new()
	var himmel := Sky.new()
	himmel.sky_material = ProceduralSkyMaterial.new()
	_env.background_mode = Environment.BG_SKY
	_env.sky = himmel
	_env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	_env.glow_enabled = true
	_env.ssao_enabled = true
	umgebung.environment = _env
	add_child(umgebung)
	_sonne = DirectionalLight3D.new()
	_sonne.rotation_degrees = Vector3(-45, -35, 0)
	_sonne.shadow_enabled = true
	_sonne.light_energy = 1.2
	add_child(_sonne)
	var boden := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(400, 100)
	boden.mesh = ebene
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.2, 0.19, 0.15)
	bm.roughness = 0.95
	boden.material_override = bm
	add_child(boden)

	var x := 0.0
	var namen := Prop.alle_modelle()
	for name in namen:
		var breite := 2.0 if name in Prop.KONVEX else 4.5
		x += breite * 0.5
		for k in 2:
			var p := Prop.new()
			p.modell = name
			p.kaputt = k == 1
			p.position = Vector3(x, 0, -k * 5.0)
			_positionen[name] = Vector3(x, 0.5, -2.5)
			add_child(p)
		var schild := Label3D.new()
		schild.text = name
		schild.font_size = 48
		schild.position = Vector3(x, 0.05, 1.6)
		schild.rotation_degrees.x = -70
		add_child(schild)
		x += breite * 0.5 + 0.8
	_haus_mitte = Vector3(x + 4.0, 0, -2.0)
	_haus(_haus_mitte)
	ziel = Vector3(x * 0.5, 0.5, -2.5)

	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera_setzen()
	if "--screenshot" in OS.get_cmdline_user_args():
		_screenshot()


## Kleines Haus aus dem Baukasten (4 x 4 m, ein Geschoss, Satteldach) als Beispiel, wie die Teile zusammenpassen
func _haus(mitte: Vector3) -> void:
	var teile := [
		["wand_tuer", Vector3(-1, 0, 2), 0], ["wand_fenster", Vector3(1, 0, 2), 0],
		["wand", Vector3(-1, 0, -2), 180], ["wand_fenster", Vector3(1, 0, -2), 180],
		["wand", Vector3(-2, 0, -1), 90], ["wand_fenster", Vector3(-2, 0, 1), 90],
		["wand", Vector3(2, 0, -1), -90], ["wand", Vector3(2, 0, 1), -90],
		["tuer", Vector3(-1.5, 0, 2), 0],
		["giebel", Vector3(-2, 3, 0), 90], ["giebel", Vector3(2, 3, 0), -90],
	]
	for x in [-1, 1]:
		teile.append(["dach", Vector3(x, 3, 2), 0])
		teile.append(["dach", Vector3(x, 3, -2), 180])
		teile.append(["dach_first", Vector3(x, 5, 0), 0])
		for z in [-1, 1]:
			teile.append(["boden", Vector3(x, 0, z), 0])
	for t in teile:
		var p := Prop.new()
		p.modell = t[0]
		p.position = mitte + t[1]
		p.rotation_degrees.y = t[2]
		add_child(p)


func _kamera_setzen() -> void:
	_kamera.position = ziel + Vector3(sin(_winkel), 0.55, cos(_winkel)).normalized() * _abstand
	_kamera.look_at(ziel)


func _process(delta: float) -> void:
	var d := Input.get_axis("ui_left", "ui_right")
	var f := Input.get_axis("ui_down", "ui_up")
	if d != 0.0 or f != 0.0:
		_winkel += d * delta * 1.5
		ziel.x += f * delta * 8.0
		_kamera_setzen()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and (e as InputEventKey).keycode == KEY_N:
		_nacht(_sonne.light_energy > 0.5)
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_abstand = maxf(2.0, _abstand - 1.0)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_abstand = minf(80.0, _abstand + 1.0)
		_kamera_setzen()


func _nacht(an: bool) -> void:
	_sonne.light_energy = 0.04 if an else 1.2
	_env.background_energy_multiplier = 0.03 if an else 1.0
	_env.ambient_light_energy = 0.1 if an else 1.0


func _screenshot() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--abstand="):
			_abstand = float(a.split("=")[1])
		elif a.begins_with("--winkel="):
			_winkel = deg_to_rad(float(a.split("=")[1]))
		elif a.begins_with("--ziel="):   # x,z oder ein Modellname oder "haus"
			var w := a.split("=")[1]
			if w == "haus":
				ziel = _haus_mitte + Vector3(0, 2.0, 0)
			elif _positionen.has(w):
				ziel = _positionen[w]
			else:
				var xz := w.split(",")
				ziel = Vector3(float(xz[0]), 0.5, float(xz[1]))
		elif a == "--nacht":
			_nacht(true)
	_kamera_setzen()
	for i in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var pfad := OS.get_user_data_dir() + "/galerie.png"
	get_viewport().get_texture().get_image().save_png(pfad)
	print("SCREENSHOT ", pfad)
	get_tree().quit()
