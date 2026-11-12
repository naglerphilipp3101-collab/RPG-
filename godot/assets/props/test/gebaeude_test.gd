extends Node3D
## Zeigt ein gespeichertes Gebäude aus dem Baukasten. F6 im Editor (Beispielhaus) oder:
## Godot --path godot res://assets/props/test/gebaeude_test.tscn -- [--datei res://data/gebaeude/x.json] [--kaputt]
##   [--screenshot] [--winkel=grad] [--hoehe=grad] [--abstand=m]   (Bild: user://gebaeude.png)
## Pfeiltasten drehen, Mausrad Zoom.

var _kamera: Camera3D
var _ziel := Vector3.ZERO
var _winkel := 0.6
var _hoehe := 0.45
var _abstand := 14.0


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var umgebung := WorldEnvironment.new()
	var env := Environment.new()
	var himmel := Sky.new()
	himmel.sky_material = ProceduralSkyMaterial.new()
	env.background_mode = Environment.BG_SKY
	env.sky = himmel
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	umgebung.environment = env
	add_child(umgebung)
	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-50, -30, 0)
	sonne.shadow_enabled = true
	add_child(sonne)
	var boden := MeshInstance3D.new()
	var ebene := PlaneMesh.new()
	ebene.size = Vector2(80, 80)
	boden.mesh = ebene
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.3, 0.33, 0.22)
	boden.material_override = bm
	add_child(boden)

	var g := Gebaeude.new()
	g.alles_kaputt = "--kaputt" in args
	var pfad := "res://data/gebaeude/beispiel_haus.json"
	for i in args.size():
		if args[i] == "--datei" and i + 1 < args.size():
			pfad = args[i + 1]
		elif args[i].begins_with("--winkel="):
			_winkel = deg_to_rad(float(args[i].split("=")[1]))
		elif args[i].begins_with("--hoehe="):
			_hoehe = deg_to_rad(float(args[i].split("=")[1]))
		elif args[i].begins_with("--abstand="):
			_abstand = float(args[i].split("=")[1])
	add_child(g)
	g.datei = pfad
	var box := g.grenzen()
	_ziel = box.get_center()
	_kamera = Camera3D.new()
	add_child(_kamera)
	_kamera_setzen()
	print("Gebäude ", g.daten.get("name", "?"), ": ", g.daten.get("teile", []).size(), " Teile")
	if "--screenshot" in args:
		for i in 20:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var datei := OS.get_user_data_dir() + "/gebaeude.png"
		get_viewport().get_texture().get_image().save_png(datei)
		print("SCREENSHOT ", datei)
		get_tree().quit()


func _kamera_setzen() -> void:
	_kamera.position = _ziel + Vector3(sin(_winkel) * cos(_hoehe), sin(_hoehe), cos(_winkel) * cos(_hoehe)) * _abstand
	_kamera.look_at(_ziel)


func _process(delta: float) -> void:
	var d := Input.get_axis("ui_left", "ui_right")
	var h := Input.get_axis("ui_down", "ui_up")
	if d != 0.0 or h != 0.0:
		_winkel += d * delta * 1.5
		_hoehe = clampf(_hoehe + h * delta, -0.2, 1.4)
		_kamera_setzen()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_abstand = maxf(2.0, _abstand - 1.0)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_abstand = minf(80.0, _abstand + 1.0)
		_kamera_setzen()
