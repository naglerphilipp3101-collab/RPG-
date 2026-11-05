extends Node3D
## Vorschau der modularen Waffen. Die Waffen liegen waagerecht, Klinge nach rechts.
## Start: Godot --path godot res://assets/waffen/test/galerie.tscn [-- --waffe schwert --modus module|kombis --bild pfad.png]
##   module: je Zeile ein Tier mit all seinen Modulen
##   kombis: zufällige Kombinationen aus Modulen aller Tiers
## Ohne --bild bleibt das Fenster offen (Mausrad zoomt, Leertaste würfelt neue Kombinationen).

var waffe := "schwert"
var modus := "module"
var bild := ""
var kamera: Camera3D
var inhalt: Node3D
var saat := 7
var spalte_x := 1.25 # Abstand der Spalten, nach Waffenlänge


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for i in args.size() - 1:
		match args[i]:
			"--waffe": waffe = args[i + 1]
			"--modus": modus = args[i + 1]
			"--bild": bild = args[i + 1]
			"--saat": saat = int(args[i + 1])
	spalte_x = {"grossschwert": 1.8, "messer": 0.55, "degen": 1.35}.get(waffe, 1.25)
	_umgebung()
	kamera = Camera3D.new()
	kamera.projection = Camera3D.PROJECTION_ORTHOGONAL
	add_child(kamera)
	_aufbauen()
	if bild != "":
		for i in 8:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()


func _aufbauen() -> void:
	if inhalt:
		inhalt.queue_free()
	inhalt = Node3D.new()
	add_child(inhalt)
	var plaetze: Array = [] # [spalte, zeile, auswahl, standard_tier, beschriftung]
	var teile: Array = WaffenModell.WAFFEN[waffe].keys()
	match modus:
		"module": # je Zeile ein Tier, nach rechts die Module dieses Tiers (Spalte k nimmt Modul k jedes Teils)
			for tier in range(1, 7):
				var n := 1
				for teil: String in teile:
					n = maxi(n, WaffenModell.formen(WaffenModell.modulart(waffe, teil), tier))
				for k in n:
					var auswahl := {}
					for teil: String in teile:
						auswahl[teil] = {"tier": tier, "form": mini(k + 1, WaffenModell.formen(WaffenModell.modulart(waffe, teil), tier))}
					plaetze.append([k, tier - 1, auswahl, tier, "%s %d" % [WaffenModell.TIER_NAMEN[tier - 1], k + 1]])
		"kombis": # zufällige Module aus allen Tiers
			var rng := RandomNumberGenerator.new()
			rng.seed = saat
			for i in 12:
				var auswahl := {}
				for teil: String in teile:
					var tier := rng.randi_range(1, 6)
					auswahl[teil] = {"tier": tier, "form": rng.randi_range(1, WaffenModell.formen(WaffenModell.modulart(waffe, teil), tier))}
				plaetze.append([i % 3, i / 3, auswahl, 1, ""])
	var spalten := 0
	var zeilen := 0
	for p: Array in plaetze:
		var halter := Node3D.new()
		# Klinge (-Z) nach rechts, flache Seite zur Kamera
		halter.basis = Basis(Vector3(0, 1, 0), Vector3(0, 0, -1), Vector3(-1, 0, 0))
		halter.position = Vector3(p[0] * spalte_x, -p[1] * 0.38, 0)
		inhalt.add_child(halter)
		WaffenModell.zusammenbauen(waffe, p[2], halter, p[3])
		if p[4] != "":
			var l := Label3D.new()
			l.text = p[4]
			l.font_size = 40
			l.pixel_size = 0.0012
			l.position = halter.position + Vector3(spalte_x * 0.36, -0.08, 0.05)
			l.modulate = Color(0.9, 0.9, 0.9)
			inhalt.add_child(l)
		spalten = maxi(spalten, int(p[0]) + 1)
		zeilen = maxi(zeilen, int(p[1]) + 1)
	# Inhalt reicht von x = -0,15 (Knauf) bis zur letzten Klingenspitze, y von +0,19 bis zur letzten Zeile
	var links := -0.2
	var rechts := (spalten - 1) * spalte_x + spalte_x - 0.25
	var oben := 0.2
	var unten := -(zeilen - 1) * 0.38 - 0.2
	var fenster := get_viewport().get_visible_rect().size
	kamera.size = maxf(oben - unten, (rechts - links) * fenster.y / fenster.x) * 1.04
	kamera.position = Vector3((links + rechts) / 2, (oben + unten) / 2, 3)


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			kamera.size *= 0.9
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			kamera.size *= 1.1
	elif e is InputEventKey and e.pressed and e.keycode == KEY_SPACE:
		saat += 1
		_aufbauen()


func _umgebung() -> void:
	var umg := Environment.new()
	var himmel := Sky.new()
	var hm := ProceduralSkyMaterial.new()
	hm.sky_top_color = Color(0.35, 0.45, 0.6)
	hm.sky_horizon_color = Color(0.8, 0.78, 0.74)
	hm.ground_bottom_color = Color(0.25, 0.22, 0.2)
	hm.ground_horizon_color = Color(0.6, 0.58, 0.55)
	himmel.sky_material = hm
	umg.background_mode = Environment.BG_COLOR
	umg.background_color = Color(0.13, 0.14, 0.16)
	umg.sky = himmel
	umg.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	umg.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	umg.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	umg.glow_enabled = true
	umg.background_energy_multiplier = 1.0
	# Dunkle Rückwand, damit helle Module (Eis, Silber) sich abheben
	var wand := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(60, 60)
	wand.mesh = q
	var wm := StandardMaterial3D.new()
	wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	wm.albedo_color = Color(0.12, 0.13, 0.15)
	wand.material_override = wm
	wand.position = Vector3(0, 0, -1)
	add_child(wand)
	var we := WorldEnvironment.new()
	we.environment = umg
	add_child(we)
	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-35, 25, 0)
	sonne.light_energy = 1.3
	add_child(sonne)
	var fuell := DirectionalLight3D.new()
	fuell.rotation_degrees = Vector3(-15, -150, 0)
	fuell.light_energy = 0.5
	fuell.light_color = Color(0.8, 0.85, 1.0)
	add_child(fuell)
