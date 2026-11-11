extends Node
## Test der Charaktererstellung.
## Start: Godot --path godot res://assets/charakter/test/erstellung.tscn -- [--bild pfad.png] [--zufall 5] [--gruppe Augen] [--zoom 1]

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var ui = preload("res://scripts/charakter_erstellung.gd").new()
	var bild := ""
	var saat := -1
	var gruppe := ""
	var zoom := -1.0
	for i in args.size():
		var n: String = args[i + 1] if i + 1 < args.size() else ""
		match args[i]:
			"--bild": bild = n
			"--zufall": saat = int(n)
			"--gruppe": gruppe = n
			"--zoom": zoom = float(n)
	add_child(ui)
	ui.fertig.connect(func(a): print("Fertig: ", JSON.stringify(a)); get_tree().quit())
	ui.abgebrochen.connect(func(): get_tree().quit())
	if saat >= 0:
		ui.rng.seed = saat
		ui._zufall(false)
	if gruppe != "":
		ui._gruppe_zeigen(gruppe)
	if zoom >= 0.0:
		ui._zoom = zoom
	if bild != "":
		for i in 30:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(bild)
		get_tree().quit()
