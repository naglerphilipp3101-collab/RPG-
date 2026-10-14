extends SceneTree
## Schneidet aus den Zweig-Atlanten der Poly-Haven-Bäume (assets/scans/, geladen mit scans_laden.ps1) je einen Zweig aus
## und legt ihn im Format der eigenen Laubtexturen ab: 1024 × 512, Zweigansatz links, Spitze rechts, Alpha = Blatt.
## Ergebnis: assets/baeume/texturen_scan/<art>_nadeln.png (nicht im Repo).
## Aufruf: Godot --headless --path godot -s res://tests/baum_scans_umwandeln.gd

## Art -> [Scan-ID, Teil, Ausschnitt im 2048er-Atlas (x, y, b, h), Zweigansatz unten im Ausschnitt]
const ZWEIGE := {
	"fichte": ["fir_tree_01", "twig", Rect2i(600, 795, 640, 735)],
	"kiefer": ["pine_tree_01", "twig", Rect2i(66, 82, 370, 795)],
	"eiche": ["tree_small_02", "leaves", Rect2i(1100, 70, 600, 1260)],
}


func _process(_delta: float) -> bool:
	var ziel := "res://assets/baeume/texturen_scan"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(ziel))
	for art in ZWEIGE:
		var z: Array = ZWEIGE[art]
		var basis := "res://assets/scans/%s/%s_%s_" % [z[0], z[0], z[1]]
		var farbe := Image.load_from_file(ProjectSettings.globalize_path(basis + "diff_2k.jpg"))
		var alpha := Image.load_from_file(ProjectSettings.globalize_path(basis + "alpha_2k.png"))
		if farbe == null or alpha == null:
			push_error("Zweig-Scan fehlt: " + art)
			continue
		farbe.convert(Image.FORMAT_RGBA8)
		alpha.convert(Image.FORMAT_RGBA8)
		var r: Rect2i = z[2]
		var stueck := Image.create(r.size.x, r.size.y, false, Image.FORMAT_RGBA8)
		for y in r.size.y:
			for x in r.size.x:
				var c := farbe.get_pixel(r.position.x + x, r.position.y + y)
				c.a = alpha.get_pixel(r.position.x + x, r.position.y + y).r
				stueck.set_pixel(x, y, c)
		# Zweigansatz liegt unten -> 90° im Uhrzeigersinn drehen, dann ist er links
		stueck.rotate_90(CLOCKWISE)
		_nur_hauptteil(stueck)
		# in 1024 × 512 einpassen, mittig; in der Länge darf um bis zu 50 % gestreckt werden
		var sh := minf(1024.0 / stueck.get_width(), 512.0 / stueck.get_height())
		var sw := minf(1024.0 / stueck.get_width(), sh * 1.5)
		stueck.resize(int(stueck.get_width() * sw), int(stueck.get_height() * sh), Image.INTERPOLATE_LANCZOS)
		var aus := Image.create(1024, 512, false, Image.FORMAT_RGBA8)
		aus.fill(Color(0.2, 0.3, 0.15, 0.0))
		aus.blit_rect(stueck, Rect2i(Vector2i.ZERO, stueck.get_size()), Vector2i(0, (512 - stueck.get_height()) / 2))
		aus.save_png(ProjectSettings.globalize_path("%s/%s_nadeln.png" % [ziel, art]))
		print("ZWEIG %s <- %s (%d × %d)" % [art, z[0], stueck.get_width(), stueck.get_height()])
	return true


## Im Atlas liegen Stücke benachbarter Zweige mit im Ausschnitt: nur das größte zusammenhängende Stück behalten
func _nur_hauptteil(img: Image) -> void:
	var w := img.get_width()
	var h := img.get_height()
	var marke := PackedInt32Array()
	marke.resize(w * h)
	var groessen: Array[int] = [0]
	for start in w * h:
		if marke[start] != 0 or img.get_pixel(start % w, start / w).a < 0.5:
			continue
		var id := groessen.size()
		var n := 0
		var stapel: Array[int] = [start]
		marke[start] = id
		while not stapel.is_empty():
			var i: int = stapel.pop_back()
			n += 1
			var x := i % w
			var y := i / w
			for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				var nx := x + d.x
				var ny := y + d.y
				if nx < 0 or ny < 0 or nx >= w or ny >= h:
					continue
				var j := ny * w + nx
				if marke[j] == 0 and img.get_pixel(nx, ny).a >= 0.5:
					marke[j] = id
					stapel.append(j)
		groessen.append(n)
	var groesste := groessen.find(groessen.max())
	for i in w * h:
		if marke[i] != groesste:
			var c := img.get_pixel(i % w, i / w)
			c.a = 0.0
			img.set_pixel(i % w, i / w, c)
