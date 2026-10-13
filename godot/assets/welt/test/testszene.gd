extends Node3D
## Importiert die Welt zur Laufzeit und zeigt sie (nur zum Testen; im Projekt importierst du im Editor).

func _ready() -> void:
	var env := Environment.new()
	var himmel := Sky.new()
	himmel.sky_material = ProceduralSkyMaterial.new()
	env.background_mode = Environment.BG_SKY
	env.sky = himmel
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_density = 0.0004
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sonne := DirectionalLight3D.new()
	sonne.rotation_degrees = Vector3(-40, -40, 0)
	sonne.shadow_enabled = true
	add_child(sonne)
	var welt: WeltImport = load("res://assets/welt/welt.tscn").instantiate()
	add_child(welt)
	var ordner := "res://welt_daten"
	var ansicht := "weit"
	var ziel := Vector3.ZERO
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--daten="):
			ordner = a.split("=")[1]
		if a.begins_with("--ansicht="):
			ansicht = a.split("=")[1]
		if a.begins_with("--ziel="):
			var t := a.split("=")[1].split(",")
			ziel = Vector3(float(t[0]), 0, float(t[1]))
	welt.daten_ordner = ordner
	welt.importieren()
	var kam := Camera3D.new()
	kam.far = 20000
	add_child(kam)
	match ansicht:
		"mittel":
			kam.position = Vector3(-900, 380, 1400)
			kam.look_at(Vector3(-300, 80, 200))
		"nah":
			kam.position = Vector3(-500, 0, 900)
			kam.position.y = welt.hoehe_bei(kam.position) + 45
			kam.look_at(Vector3(-650, 90, 300))
		"boden":
			kam.position = Vector3(-300, 0, 600)
			kam.position.y = welt.hoehe_bei(kam.position) + 1.8
			kam.look_at(Vector3(-600, 120, -300))
		"spieler":
			# Blick auf ein Ziel aus 3. Person (60 m zurück, 35 m hoch)
			ziel.y = welt.hoehe_bei(ziel)
			kam.position = ziel + Vector3(45, 0, 60)
			kam.position.y = maxf(welt.hoehe_bei(kam.position), ziel.y) + 32
			kam.look_at(ziel + Vector3(0, 6, 0))
		"bruecke":
			# auf die erste Brücke schauen
			var idx := 0
			for a in OS.get_cmdline_user_args():
				if a.begins_with("--bruecke="):
					idx = int(a.split("=")[1])
			print("Brücken: ", welt.get_node("Wege/Bruecken").get_child_count())
			var br: Node3D = welt.get_node("Wege/Bruecken").get_child(idx)
			ziel = br.position
			kam.position = ziel + Vector3(28, 14, 34)
			kam.look_at(ziel)
		_:
			kam.position = Vector3(0.63, 0.54, 0.83) * welt.welt_groesse
			env.fog_density = 0.4 / maxf(welt.welt_groesse, 1.0) * 0.1
			kam.look_at(Vector3(0, 0, 0))
	if "--ressourcen" in OS.get_cmdline_user_args():
		var res := WeltRessourcen.new()
		res.welt = welt
		res.ziel = kam
		res.radius = 180
		welt.add_child(res)
		res.sofort_laden()
		var z := 0
		for c in res.get_children():
			z += c.get_child_count()
		print("Ressourcen geladen: ", z)
	if "--screenshot" in OS.get_cmdline_user_args():
		for i in 60:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(OS.get_user_data_dir() + "/screenshot.png")
		get_tree().quit()
