extends Node3D
## Nahansicht einer Waffe aus allen Modulen eines Tiers (perspektivisch, für Detailprüfungen).
## Start: Godot --path godot res://assets/waffen/test/nahansicht.tscn -- --waffe leerenhandschuh --tier 6 --form 1
##        [--gier 35] [--neigung 25] [--abstand 0.6] [--mitte x,y,z] [--bild pfad.png]
## Mehrere Tiers nebeneinander: --tier 1,3,6 (dann in einer Reihe entlang X).

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var waffe := "schwert"
	var tiers: Array = [1]
	var form := 1
	var gier := 35.0
	var neigung := 25.0
	var abstand := 0.6
	var mitte := Vector3.ZERO
	var bild := ""
	for i in args.size() - 1:
		match args[i]:
			"--waffe": waffe = args[i + 1]
			"--tier": tiers = Array(args[i + 1].split(",")).map(func(s): return int(s))
			"--form": form = int(args[i + 1])
			"--gier": gier = float(args[i + 1])
			"--neigung": neigung = float(args[i + 1])
			"--abstand": abstand = float(args[i + 1])
			"--mitte":
				var p: PackedStringArray = args[i + 1].split(",")
				mitte = Vector3(float(p[0]), float(p[1]), float(p[2]))
			"--bild": bild = args[i + 1]
	var umgebung := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.12, 0.13, 0.16)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.57, 0.62)
	env.ambient_light_energy = 0.7
	env.reflected_light_source = Environment.REFLECTION_SOURCE_BG
	umgebung.environment = env
	add_child(umgebung)
	for r in [[Vector3(-50, -30, 0), 1.3], [Vector3(-20, 150, 0), 0.6], [Vector3(30, 60, 0), 0.4]]:
		var licht := DirectionalLight3D.new()
		licht.rotation_degrees = r[0]
		licht.light_energy = r[1]
		add_child(licht)
	var breite := 0.0
	for k in tiers.size():
		var halter := Node3D.new()
		halter.position = Vector3(k * abstand * 0.9, 0, 0)
		add_child(halter)
		var auswahl := {}
		for teil: String in WaffenModell.WAFFEN[waffe]:
			auswahl[teil] = {"tier": tiers[k], "form": form}
		WaffenModell.zusammenbauen(waffe, auswahl, halter, tiers[k], Color(0.65, 0.3, 0.95))
		breite = k * abstand * 0.9
	var kamera := Camera3D.new()
	kamera.fov = 35
	add_child(kamera)
	var ziel := mitte + Vector3(breite / 2, 0, 0)
	var richtung := Basis.from_euler(Vector3(deg_to_rad(-neigung), deg_to_rad(gier), 0)) * Vector3(0, 0, 1)
	kamera.look_at_from_position(ziel + richtung * (abstand + breite * 0.9), ziel)
	if bild != "":
		for i in 8:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()
