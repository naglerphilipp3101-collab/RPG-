extends Node3D
## Vorschau von Menschen (für Bilder und Prüfungen).
## Start: Godot --path godot res://assets/charakter/test/vorschau.tscn -- [--bild pfad.png]
##   --figuren '[{"geschlecht":0}, {"geschlecht":1}]'  (Aussehen je Figur, JSON)
##   --gier 0 --neigung 5 --abstand 3.2 --mitte 0,1,0 --a_pose --zeit (misst die Aufbauzeit)

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var figuren: Array = [{}]
	var gier := 0.0
	var neigung := 5.0
	var abstand := 3.2
	var mitte := Vector3(0, 0.95, 0)
	var bild := ""
	var a_pose := false
	var fov := 35.0
	for i in args.size():
		var naechstes: String = args[i + 1] if i + 1 < args.size() else ""
		match args[i]:
			"--figuren": figuren = JSON.parse_string(naechstes)
			"--gier": gier = float(naechstes)
			"--neigung": neigung = float(naechstes)
			"--abstand": abstand = float(naechstes)
			"--fov": fov = float(naechstes)
			"--mitte":
				var p: PackedStringArray = naechstes.split(",")
				mitte = Vector3(float(p[0]), float(p[1]), float(p[2]))
			"--bild": bild = naechstes
			"--a_pose": a_pose = true
	var umgebung := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.16, 0.17, 0.2)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.6, 0.62, 0.68)
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	umgebung.environment = env
	add_child(umgebung)
	for r in [[Vector3(-35, -30, 0), 1.0, true], [Vector3(-10, 150, 0), 0.45, false], [Vector3(20, 60, 0), 0.25, false]]:
		var licht := DirectionalLight3D.new()
		licht.rotation_degrees = r[0]
		licht.light_energy = r[1]
		licht.shadow_enabled = r[2]
		add_child(licht)
	var breite := (figuren.size() - 1) * 0.9
	for k in figuren.size():
		var m := Mensch.new()
		var a := Mensch.standard_aussehen()
		a.merge(figuren[k], true)
		m.aussehen = a
		m.position = Vector3(k * 0.9 - breite / 2.0, 0, 0)
		var t0 := Time.get_ticks_msec()
		add_child(m)
		if a_pose:
			m.ruhe_a_pose(true)
		print("Mensch %d aufgebaut in %d ms" % [k, Time.get_ticks_msec() - t0])
	var kamera := Camera3D.new()
	kamera.fov = fov
	add_child(kamera)
	var richtung := Basis.from_euler(Vector3(deg_to_rad(-neigung), deg_to_rad(gier), 0)) * Vector3(0, 0, 1)
	kamera.look_at_from_position(mitte + richtung * (abstand + breite * 0.8), mitte)
	if bild != "":
		for i in 8:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()
