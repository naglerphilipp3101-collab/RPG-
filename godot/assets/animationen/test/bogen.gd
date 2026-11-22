extends Node3D

const MeshUtil := preload("res://scripts/mesh_util.gd")
const WeaponModels := preload("res://scripts/weapon_models.gd")
const Spieler := preload("res://scripts/player.gd")
## Bilderbogen von Animationen: je Zeile eine Animation, je Spalte ein Zeitpunkt.
## --waffe sword|greataxe|bow … hängt ein Platzhalter-Modell in die rechte Hand (sword: dazu ein Schild links).
## --quelle zeigt die Quaternius-Puppe statt des Menschen (Vergleich).
## Start: Godot --path godot res://assets/animationen/test/bogen.tscn -- --anims Walk_Loop,Roll [--schritte 6]
##   [--bild pfad.png] [--gier 90] (Blickwinkel, 90 = von der Seite) [--liste] (Namen ausgeben)

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var anims: PackedStringArray = ["Idle", "Walk", "Jog_Fwd", "Sprint"]
	var schritte := 6
	var bild := ""
	var gier := 90.0
	var quelle := false
	var waffe := ""
	for i in args.size():
		var n: String = args[i + 1] if i + 1 < args.size() else ""
		match args[i]:
			"--anims": anims = n.split(",")
			"--schritte": schritte = int(n)
			"--bild": bild = n
			"--gier": gier = float(n)
			"--quelle": quelle = true
			"--waffe": waffe = n
			"--liste":
				print(MenschAnimationen.bibliothek().get_animation_list())
				get_tree().quit()
				return
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.16, 0.17, 0.2)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.65, 0.66, 0.7)
	env.ambient_light_energy = 0.4
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var licht := DirectionalLight3D.new()
	licht.rotation_degrees = Vector3(-40, gier - 30, 0)
	add_child(licht)
	var abst_x := 1.3
	var abst_y := 2.3
	var schrift := Label3D.new()
	var figuren := []
	for z in anims.size():
		var name: String = anims[z]
		for s in schritte:
			var m: Node3D
			if quelle:
				m = load(MenschAnimationen.QUELLEN[0]).instantiate()
			else:
				m = Mensch.new()
			add_child(m)
			# Figur dreht sich so, dass die Kamera sie im gewünschten Winkel sieht
			m.rotation_degrees.y = gier
			m.position = Vector3(s * abst_x, -z * abst_y, 0)
			figuren.append([m, name, s])
		var l := Label3D.new()
		l.text = name
		l.font_size = 48
		l.pixel_size = 0.004
		l.position = Vector3(-1.2, -z * abst_y + 1.0, 0)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		add_child(l)
	await get_tree().process_frame
	for f in figuren:
		var m: Node3D = f[0]
		var ap: AnimationPlayer
		var voll: String = MenschAnimationen.BIBLIOTHEK + "/" + String(f[1])
		if quelle:
			ap = m.get_node("AnimationPlayer")
			voll = String(f[1])
		else:
			ap = MenschAnimationen.spieler_anhaengen(m)
		if waffe != "" and not quelle:
			var fig := SpielerAnimation.new(m)
			var rechts := Node3D.new()
			fig.an_hand(rechts, false)
			WeaponModels.build(waffe, rechts)
			if waffe == "sword":
				var links := Node3D.new()
				fig.an_hand(links, true)
				var schild := Node3D.new()
				links.add_child(schild)
				schild.position = Spieler.SCHILD_HAND_POS
				schild.rotation_degrees = Spieler.SCHILD_HAND_ROT
				MeshUtil.part(schild, MeshUtil.box(Vector3(0.62, 0.74, 0.07)), MeshUtil.mat(Color(0.45, 0.3, 0.16)))
				var buckel := SphereMesh.new()
				buckel.radius = 0.09
				buckel.height = 0.12
				MeshUtil.part(schild, buckel, MeshUtil.mat(Color(0.8, 0.8, 0.85)), Vector3(0, 0, -0.05))
		if String(f[1]) == "RUHE":
			continue
		if not ap.has_animation(voll):
			push_error("Animation fehlt: " + f[1])
			continue
		var laenge := ap.get_animation(voll).length
		ap.play(voll)
		ap.seek(laenge * float(f[2]) / float(schritte), true)
		ap.pause()
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	var breite := schritte * abst_x + 2.0
	var hoehe := anims.size() * abst_y
	cam.size = hoehe
	cam.position = Vector3((schritte - 1) * abst_x * 0.5 - 0.6, -(anims.size() - 1) * abst_y * 0.5 + 0.95, 10)
	add_child(cam)
	get_viewport().size = Vector2i(int(240 * breite / abst_x * 0.75), int(240 * hoehe / abst_y))
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	for i in 10:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	if bild != "":
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()
