extends Node3D
## Vorschau: alle Waffenformen nebeneinander, je Zeile ein Tier.
## Start: Godot --path godot res://assets/waffen/test/galerie.tscn [-- --formen sword,axe --bild pfad.png]
## Ohne --bild bleibt das Fenster offen (Pfeiltasten drehen, Mausrad zoomt).

var formen: Array = []
var bild := ""
var kamera: Camera3D
var drehung := 0.0
var abstand := 2.2


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for i in args.size():
		if args[i] == "--formen" and i + 1 < args.size():
			formen = Array(args[i + 1].split(","))
		elif args[i] == "--bild" and i + 1 < args.size():
			bild = args[i + 1]
	if formen.is_empty():
		for f in DirAccess.get_files_at(WaffenModell.ORDNER):
			if f.ends_with(".glb"):
				formen.append(f.get_basename())
	_umgebung()
	var breite := 0.0
	for spalte in formen.size():
		for tier in range(1, 7):
			var halter := Node3D.new()
			# Klinge nach oben, flache Seite zur Kamera
			halter.rotation_degrees = Vector3(90, 0, 0)
			halter.position = Vector3(spalte * 0.5 + (tier - 1) * 0.16, 0, 0) if formen.size() > 1 else Vector3((tier - 1) * 0.22, 0, 0)
			add_child(halter)
			WaffenModell.erzeugen(formen[spalte], tier, halter)
			breite = maxf(breite, halter.position.x)
	kamera = Camera3D.new()
	kamera.fov = 35
	add_child(kamera)
	abstand = maxf(1.6, breite * 1.9)
	_kamera_setzen(breite)
	if bild != "":
		for i in 8:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()


func _kamera_setzen(breite: float) -> void:
	var mitte := Vector3(breite / 2, 0.45, 0)
	kamera.position = mitte + Vector3(sin(drehung), 0.1, cos(drehung)) * abstand
	kamera.look_at(mitte)


func _process(delta: float) -> void:
	if bild != "":
		return
	var d := Input.get_axis("ui_left", "ui_right")
	if d != 0.0:
		drehung += d * delta * 1.5
		_kamera_setzen(_breite())


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			abstand *= 0.9
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			abstand *= 1.1
		_kamera_setzen(_breite())


func _breite() -> float:
	var b := 0.0
	for k in get_children():
		if k is Node3D and not k is Camera3D:
			b = maxf(b, k.position.x)
	return b


func _umgebung() -> void:
	var umg := Environment.new()
	var himmel := Sky.new()
	var hm := ProceduralSkyMaterial.new()
	hm.sky_top_color = Color(0.35, 0.45, 0.6)
	hm.sky_horizon_color = Color(0.75, 0.75, 0.72)
	hm.ground_bottom_color = Color(0.2, 0.18, 0.16)
	hm.ground_horizon_color = Color(0.5, 0.48, 0.45)
	himmel.sky_material = hm
	umg.background_mode = Environment.BG_COLOR
	umg.background_color = Color(0.16, 0.17, 0.19)
	umg.sky = himmel
	umg.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	umg.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	umg.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	umg.glow_enabled = true
	var we := WorldEnvironment.new()
	we.environment = umg
	add_child(we)
	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-40, 30, 0)
	sonne.light_energy = 1.3
	add_child(sonne)
	var fuell := DirectionalLight3D.new()
	fuell.rotation_degrees = Vector3(-15, -140, 0)
	fuell.light_energy = 0.5
	fuell.light_color = Color(0.8, 0.85, 1.0)
	add_child(fuell)
