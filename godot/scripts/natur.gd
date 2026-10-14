extends Node3D
## Natur auf der ganzen Insel: Bäume (Fichte, Kiefer, Eiche), Äste-Büsche und Sammelpflanzen (Hanf, Beeren, Kräuter).
##
## Wo etwas wächst, wird aus der Biomkarte des Weltgenerators, dem Gelände und Rauschen berechnet – in Kacheln
## von 64 m, jede mit eigenem festen Zufall. Dadurch steht bei jedem Laden alles an derselben Stelle, ohne dass
## Millionen Objekte gespeichert werden müssen. Frei bleiben Meer, Seen, steile Hänge, Siedlungen, Felder, Wege
## sowie Dorfplatz und Lager des Startgebiets.
##
## Nah (NAH_RADIUS): echte Blender-Modelle, die man fällen/ernten kann (scripts/natur_quelle.gd).
## Fern (bis FERN_RADIUS): nur Bäume, als einfache Formen in MultiMeshes je 256-m-Kachel.

const QuelleScript := preload("res://scripts/natur_quelle.gd")
const BaumSzene := preload("res://assets/baeume/baum.tscn")
const BuschSzene := preload("res://assets/baeume/aeste_busch.tscn")
const PflanzeSzene := preload("res://assets/sammeln/sammelpflanze.tscn")
const SteinSzene := preload("res://assets/erz/felsbrocken.tscn")
const SteinMaterial := preload("res://assets/erz/materialien/stein.tres")
const FernShader := preload("res://scripts/natur_fern.gdshader")

const KACHEL := 64.0
const FERN_KACHEL := 256.0
const NAH_RADIUS := 110.0
const FERN_RADIUS := 950.0
const NEU_ZENTRIEREN := 8.0      # Meter Bewegung, ab der der Nahbereich neu sortiert wird
const BUDGET_US := 4000          # Zeit je Frame für neue Nah-Objekte (ein Modell braucht ~2 ms)

# Biome des Weltgenerators
enum { STRAND, WIESE, LAUBWALD, NADELWALD, SUMPF, STEPPE, FELS, SCHNEE }
enum { BAUM, BUSCH, PFLANZE, STEIN }
## Baum-Arten wie in assets/baeume/baum.gd: 0 Fichte, 1 Kiefer, 2 Eiche · Größe (Breite, Höhe) je Alter [jung, alt, uralt]
const BAUM_GROESSE := [[Vector2(2.7, 5.8), Vector2(5.0, 12.9), Vector2(6.6, 20.5)], [Vector2(2.9, 5.2), Vector2(6.8, 11.8), Vector2(8.4, 18.5)],
	[Vector2(2.9, 5.0), Vector2(7.5, 10.7), Vector2(10.5, 16.8)]]
const ALTER_ID := ["jung", "alt", "uralt"]
## Anteil uralter Bäume (untere 2/3 kahl, geben Gereiftes Holz): im Wald und einzeln auf Wiesen
const URALT_WALD := 0.06
const URALT_SONST := 0.04
const BAUM_ID := ["fichte", "kiefer", "eiche"]

var terrain                       # Terrain3D (Höhen)
var ziel: Node3D                  # Spieler
var welt_m := 8192.0
var raster := 0
var zelle := 4.0
var welt_seed := 0
var biome := PackedByteArray()
var seen := PackedByteArray()
var frei: Array = []              # freie Kreise im Startgebiet [Vector2 Mitte, Radius] (Dorfplatz, Lager), von main.gd
var sperr := {}                   # Vector2i (32-m-Feld) -> Array von Sperrflächen, die das Feld berühren:
                                  #   ["k", Mitte, Radius] · ["f", Mitte, halbe Größe, Winkel] · ["w", a, b, halbe Breite]
var rauschen := FastNoiseLite.new()

var _daten := {}                  # Vector2i (64-m-Kachel) -> Array der Einträge
var _nah := {}                    # Vector3i (Kachel x, y, Index) -> Node3D
var _nah_mitte := Vector2(INF, INF)
var _warteschlange: Array = []    # [Vector3i, Eintrag]
var _fern := {}                   # Vector2i (256-m-Kachel) -> Node3D
var _fern_offen: Array = []       # noch zu bauende Fernkacheln
var _fern_material := ShaderMaterial.new()
var _fern_meshes: Array = []      # je Baumart ein ArrayMesh
var _wurzel_nah: Node3D
var _mono_cache := {}              # Vector2i (256-m-Kachel) -> Monolithen (siehe _monolithen)
var _mono_modelle := {}            # Modellname -> [Mesh, Kollisionsform]


## main = Spielszene (liefert terrain und das Startgebiet), spieler = Mittelpunkt des Streamings
func setup(main, spieler: Node3D, daten_ordner: String) -> void:
	terrain = main.terrain
	ziel = spieler
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(daten_ordner.path_join("welt.json")))
	welt_m = float(meta["welt_m"])
	raster = int(meta["raster"])
	zelle = float(meta["zelle_m"])
	welt_seed = int(meta.get("params", {}).get("seed", 1))
	biome = FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["biome"]["datei"]))
	if meta.get("seen") != null:
		seen = FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["seen"]["datei"]))
	_marker_laden(daten_ordner.path_join("marker.json"))
	_wege_laden(daten_ordner.path_join("wege.json"))
	_fluesse_laden(daten_ordner.path_join("fluesse.json"))
	rauschen.seed = welt_seed
	rauschen.frequency = 1.0 / 230.0
	rauschen.fractal_octaves = 3
	_fern_material.shader = FernShader
	_fern_meshes = [_fichte_mesh(), _kiefer_mesh(), _eiche_mesh(), _uralt_mesh(0), _uralt_mesh(1), _uralt_mesh(2)]
	_wurzel_nah = Node3D.new()
	_wurzel_nah.name = "Nah"
	add_child(_wurzel_nah)


func _marker_laden(pfad: String) -> void:
	if not FileAccess.file_exists(pfad):
		return
	# Wie viel vom Radius um einen Marker frei bleibt (wie im Weltgenerator)
	var frei := {"stadt": 1.15, "dorf": 1.3, "mine": 0.6, "dungeon": 0.6, "poi": 0.5}
	for m in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var typ: String = m["typ"]
		var mitte := Vector2(float(m["x"]), float(m["z"]))
		if typ == "feld":
			var halb := Vector2(float(m["breite"]), float(m["laenge"])) / 2.0 + Vector2(2, 2)
			_sperre_eintragen(["f", mitte, halb, float(m["winkel"])], mitte - Vector2.ONE * halb.length(), mitte + Vector2.ONE * halb.length())
		elif frei.has(typ):
			var r := float(m.get("radius", 30)) * float(frei[typ]) + 4.0
			_sperre_eintragen(["k", mitte, r], mitte - Vector2(r, r), mitte + Vector2(r, r))


func _wege_laden(pfad: String) -> void:
	if not FileAccess.file_exists(pfad):
		return
	for w in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var halb: float = float(w["breite"]) / 2.0 + 2.5
		var punkte: Array = w["punkte"]
		for i in range(1, punkte.size()):
			var a := Vector2(float(punkte[i - 1][0]), float(punkte[i - 1][2]))
			var b := Vector2(float(punkte[i][0]), float(punkte[i][2]))
			_sperre_eintragen(["w", a, b, halb], a.min(b) - Vector2(halb, halb), a.max(b) + Vector2(halb, halb))


## Flussläufe wie Wege sperren (kein Baum, keine Pflanze, kein Gras im Flussbett)
func _fluesse_laden(pfad: String) -> void:
	if not FileAccess.file_exists(pfad):
		return
	for f in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var punkte: Array = f["punkte"]
		for i in range(1, punkte.size()):
			var a := Vector2(float(punkte[i - 1][0]), float(punkte[i - 1][2]))
			var b := Vector2(float(punkte[i][0]), float(punkte[i][2]))
			var halb: float = float(punkte[i][3]) / 2.0 + 1.0
			_sperre_eintragen(["w", a, b, halb], a.min(b) - Vector2(halb, halb), a.max(b) + Vector2(halb, halb))


## Sperrfläche in alle 32-m-Felder eintragen, die ihr Rechteck (von … bis) berührt
func _sperre_eintragen(eintrag: Array, von: Vector2, bis: Vector2) -> void:
	for fy in range(floori(von.y / 32.0), floori(bis.y / 32.0) + 1):
		for fx in range(floori(von.x / 32.0), floori(bis.x / 32.0) + 1):
			var k := Vector2i(fx, fy)
			if not sperr.has(k):
				sperr[k] = []
			sperr[k].append(eintrag)


# --- Wo darf etwas wachsen? ------------------------------------------------

## Biom an einer Weltposition, -1 außerhalb der Karte oder im See
func _biom(x: float, z: float) -> int:
	var cx := int((x + welt_m / 2.0) / zelle)
	var cz := int((z + welt_m / 2.0) / zelle)
	if cx < 0 or cz < 0 or cx >= raster or cz >= raster:
		return -1
	var i := cz * raster + cx
	if not seen.is_empty() and seen[i] != 0:
		return -1
	return biome[i]


func _gesperrt(x: float, z: float) -> bool:
	return _gesperrt_flaechen(x, z) or _an_monolith(x, z)


## Steht hier schon ein Felsmonolith? (Bäume, Pflanzen und Steine halten Abstand)
func _an_monolith(x: float, z: float) -> bool:
	var k := Vector2i(floori(x / FERN_KACHEL), floori(z / FERN_KACHEL))
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			for m in _monolithen(k + Vector2i(dx, dz)):
				if Vector2(x, z).distance_to(Vector2(m[0], m[2])) < float(m[6]):
					return true
	return false


## Felsmonolithen einer 256-m-Kachel (fest je Kachel): [x, Höhe, z, Typ (0 Turm, 1 Gruppe), Variante, Drehung, Freiraum]
## Häufig auf Fels, seltener auf Wiese/Steppe/im Wald. Werden mit den fernen Bäumen gebaut, sind also weit sichtbar.
func _monolithen(k: Vector2i) -> Array:
	if _mono_cache.has(k):
		return _mono_cache[k]
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(k.x, k.y, welt_seed + 991))
	for versuch in 3:
		var x := (k.x + 0.1 + 0.8 * rng.randf()) * FERN_KACHEL
		var z := (k.y + 0.1 + 0.8 * rng.randf()) * FERN_KACHEL
		var r := rng.randf()
		var typ := 0 if rng.randf() < 0.45 else 1 # 0 Felsturm, 1 Felsgruppe
		var variante := rng.randi_range(1, 3)
		var dreh := rng.randf() * TAU
		var b := _biom(x, z)
		var chance := 0.0
		match b:
			FELS:
				chance = 0.3
			WIESE, STEPPE:
				chance = 0.07
			LAUBWALD, NADELWALD:
				chance = 0.05
			SCHNEE:
				chance = 0.05
		if r > chance or _gesperrt_flaechen(x, z):
			continue
		var h := _boden(x, z, 0.9)
		if is_nan(h):
			continue
		var frei := 11.0 if typ == 0 else 13.0
		var zu_nah := false
		for m in out:
			if Vector2(x, z).distance_to(Vector2(m[0], m[2])) < 40.0:
				zu_nah = true
		if not zu_nah:
			out.append([x, h, z, typ, variante, dreh, frei])
	_mono_cache[k] = out
	return out


func _gesperrt_flaechen(x: float, z: float) -> bool:
	var p := Vector2(x, z)
	for f in frei:
		if p.distance_to(f[0]) < f[1]:
			return true
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if not sperr.has(feld):
		return false
	for s in sperr[feld]:
		match s[0]:
			"k":
				if p.distance_to(s[1]) < s[2]:
					return true
			"f":
				var d: Vector2 = p - s[1]
				var c := cos(float(s[3]))
				var sn := sin(float(s[3]))
				if absf(d.x * c + d.y * sn) <= s[2].x and absf(-d.x * sn + d.y * c) <= s[2].y:
					return true
			"w":
				if Geometry2D.get_closest_point_to_segment(p, s[1], s[2]).distance_to(p) < s[3]:
					return true
	return false


## Liegt der Punkt in einem Feld (für das Gras)?
func _im_feld(x: float, z: float) -> bool:
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if not sperr.has(feld):
		return false
	var p := Vector2(x, z)
	for s in sperr[feld]:
		if s[0] == "f":
			var d: Vector2 = p - s[1]
			var c := cos(float(s[3]))
			var sn := sin(float(s[3]))
			if absf(d.x * c + d.y * sn) <= s[2].x - 2.0 and absf(-d.x * sn + d.y * c) <= s[2].y - 2.0:
				return true
	return false


## Liegt der Punkt auf einer Straße / einem Weg (für das Gras)?
func _auf_weg(x: float, z: float) -> bool:
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if not sperr.has(feld):
		return false
	var p := Vector2(x, z)
	for s in sperr[feld]:
		if s[0] == "w" and Geometry2D.get_closest_point_to_segment(p, s[1], s[2]).distance_to(p) < float(s[3]) - 1.5:
			return true
	return false


func _hoehe(x: float, z: float) -> float:
	var h: float = terrain.get("data").get_height(Vector3(x, 0, z))
	return -100.0 if is_nan(h) else h


## Höhe, wenn der Platz geeignet ist (Land, nicht zu steil), sonst NAN
func _boden(x: float, z: float, max_steigung: float) -> float:
	var h := _hoehe(x, z)
	if h < 0.6:
		return NAN
	var st := maxf(absf(_hoehe(x + 2.0, z) - h), absf(_hoehe(x, z + 2.0) - h)) / 2.0
	return NAN if st > max_steigung else h


# --- Kacheln erzeugen -------------------------------------------------------

## Einträge einer 64-m-Kachel: [Art (BAUM/BUSCH/PFLANZE), x, y, z, a, b, Drehung]
## Bäume: a = Baumart, b = Alter · Pflanzen: a = Art (Hanf/Beeren/Kraut), b = Farbe · Steine: a = Größe 1–5
func _kachel(k: Vector2i) -> Array:
	if _daten.has(k):
		return _daten[k]
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(k.x, k.y, welt_seed))
	var x0 := k.x * KACHEL
	var z0 := k.y * KACHEL
	# Bäume: gestreutes 7-m-Raster
	var n := 9
	var s := KACHEL / n
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r_art := rng.randf()
			var r_chance := rng.randf()
			var r_alter := rng.randf()
			var r_dreh := rng.randf() * TAU
			var b := _biom(x, z)
			if b < 0:
				continue
			var d := 0.5 + 0.5 * rauschen.get_noise_2d(x, z) # Lichtungen und dichte Stellen
			var chance := 0.0
			var art := 0
			match b:
				LAUBWALD:
					chance = 0.55 + 0.45 * d
					art = 2 if r_art < 0.7 else 1
				NADELWALD:
					chance = 0.6 + 0.4 * d
					art = 0 if r_art < 0.65 else 1
				WIESE:
					chance = 0.025 * d
					art = 2 if r_art < 0.6 else 1
				SUMPF:
					chance = 0.08
					art = 1
				STEPPE:
					chance = 0.01
					art = 1
			if r_chance > chance or _gesperrt(x, z):
				continue
			var h := _boden(x, z, 0.7)
			if is_nan(h):
				continue
			var uralt := URALT_WALD if b == LAUBWALD or b == NADELWALD else URALT_SONST
			var alter := 2 if r_alter < uralt else (1 if r_alter < 0.62 else 0)
			out.append([BAUM, x, h, z, art, alter, r_dreh])
	# Äste-Büsche: 16-m-Raster, an Waldrändern, in Wäldern und auf Wiesen
	n = 4
	s = KACHEL / n
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r := rng.randf()
			var r_dreh := rng.randf() * TAU
			var b := _biom(x, z)
			var chance := 0.0
			match b:
				LAUBWALD, NADELWALD:
					chance = 0.35
				WIESE:
					chance = 0.12
				SUMPF, STEPPE:
					chance = 0.06
			if r > chance or _gesperrt(x, z):
				continue
			var h := _boden(x, z, 0.6)
			if not is_nan(h):
				out.append([BUSCH, x, h, z, 0, 0, r_dreh])
	# Sammelpflanzen: 16-m-Raster. Hanf in kleinen Gruppen auf Wiese/Steppe, Beeren in Wiese/Laubwald, Kräuter überall im Grünen
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r := rng.randf()
			var r_farbe := rng.randi_range(0, 3)
			var r_anzahl := rng.randi_range(3, 6)
			var b := _biom(x, z)
			if b < 0 or b == STRAND or b == FELS or b == SCHNEE or r >= 0.42 or _gesperrt(x, z):
				continue
			if (b == WIESE or b == STEPPE) and r < 0.06 + 0.12 * (0.5 + 0.5 * rauschen.get_noise_2d(x * 3.0, z * 3.0)):
				for i in r_anzahl:
					var hx := x + rng.randf_range(-3.0, 3.0)
					var hz := z + rng.randf_range(-3.0, 3.0)
					var h := _boden(hx, hz, 0.5)
					if not is_nan(h):
						out.append([PFLANZE, hx, h, hz, 0, 0, rng.randf() * TAU])
			elif (b == WIESE or b == LAUBWALD) and r < 0.2:
				var h := _boden(x, z, 0.5)
				if not is_nan(h):
					out.append([PFLANZE, x, h, z, 1, r_farbe, 0.0])            # Beeren: rot/blau/schwarz/gelb
			elif (b == WIESE or b == SUMPF or b == LAUBWALD or b == NADELWALD) and r < 0.42:
				var h := _boden(x, z, 0.5)
				if not is_nan(h):
					out.append([PFLANZE, x, h, z, 2, [4, 3, 5, 0][r_farbe], 0.0]) # Kräuter: weiß/gelb/lila/rot
	# Felsbrocken (Stein, Feuerstein): 16-m-Raster, vor allem auf Fels und an Hängen, sonst vereinzelt
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r := rng.randf()
			var r_groesse := rng.randf()
			var b := _biom(x, z)
			var chance := 0.0
			match b:
				FELS:
					chance = 0.3
				SCHNEE:
					chance = 0.06
				STEPPE:
					chance = 0.07
				WIESE, LAUBWALD, NADELWALD:
					chance = 0.025
				STRAND, SUMPF:
					chance = 0.012
			if r > chance * 2.0 or _gesperrt(x, z):
				continue
			var h := _hoehe(x, z)
			if h < 0.6:
				continue
			var st := maxf(absf(_hoehe(x + 2.0, z) - h), absf(_hoehe(x, z + 2.0) - h)) / 2.0
			# an Hängen doppelt so viele Brocken, an Steilwänden keine
			if st > 1.2 or r > chance * (1.0 + minf(st / 0.4, 1.0)):
				continue
			# meist mittelgroß, große vor allem auf Fels, ganz kleine selten
			var groesse := 2 + int(r_groesse * r_groesse * (4.0 if b == FELS else 2.5))
			if r_groesse < 0.08:
				groesse = 1
			out.append([STEIN, x, h, z, mini(groesse, 5), 0, 0.0])
	_daten[k] = out
	return out


# --- Streaming --------------------------------------------------------------

func _process(_delta: float) -> void:
	if ziel == null or terrain == null:
		return
	var p := Vector2(ziel.global_position.x, ziel.global_position.z)
	if p.distance_to(_nah_mitte) > NEU_ZENTRIEREN:
		_nah_zentrieren(p)
	if Engine.get_process_frames() % 15 == 0:
		_fern_aktualisieren(p)
	var ende := Time.get_ticks_usec() + BUDGET_US
	while Time.get_ticks_usec() < ende and not _warteschlange.is_empty():
		var job: Array = _warteschlange.pop_front()
		var e: Array = job[1]
		if _nah.has(job[0]) or Vector2(e[1], e[3]).distance_to(_nah_mitte) >= NAH_RADIUS:
			continue
		_nah[job[0]] = _nah_erzeugen(e)
	# Ferne Bäume nur dort ausblenden, wo die echten schon stehen (die Warteschlange ist nach Abstand sortiert)
	var gefuellt := NAH_RADIUS
	if not _warteschlange.is_empty():
		var e: Array = _warteschlange[0][1]
		gefuellt = Vector2(e[1], e[3]).distance_to(_nah_mitte) - 0.5
	_fern_material.set_shader_parameter("nah_radius", gefuellt)
	# höchstens eine Fernkachel je Frame bauen (die nächste zuerst)
	if not _fern_offen.is_empty():
		_fern_bauen(_fern_offen.pop_front())


## Alles im Nahbereich sofort erzeugen (z. B. für Tests oder nach einem Sprung)
func sofort_laden() -> void:
	var p := Vector2(ziel.global_position.x, ziel.global_position.z)
	_nah_zentrieren(p)
	for job in _warteschlange:
		if not _nah.has(job[0]):
			_nah[job[0]] = _nah_erzeugen(job[1])
	_warteschlange.clear()


func _nah_zentrieren(p: Vector2) -> void:
	_nah_mitte = p
	_fern_material.set_shader_parameter("nah_mitte", p)
	# zu weit entfernte Objekte entfernen
	for key in _nah.keys():
		var n: Node3D = _nah[key]
		if Vector2(n.position.x, n.position.z).distance_to(p) >= NAH_RADIUS:
			n.queue_free()
			_nah.erase(key)
	# neue Objekte im Radius einreihen (die nächsten zuerst)
	var neu: Array = []
	var r := int(ceil(NAH_RADIUS / KACHEL))
	var mitte := Vector2i(floori(p.x / KACHEL), floori(p.y / KACHEL))
	for dz in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var k := mitte + Vector2i(dx, dz)
			var daten := _kachel(k)
			for i in daten.size():
				var key := Vector3i(k.x, k.y, i)
				if _nah.has(key):
					continue
				var d := Vector2(daten[i][1], daten[i][3]).distance_to(p)
				if d < NAH_RADIUS:
					neu.append([d, key, daten[i]])
	neu.sort_custom(func(a, b): return a[0] < b[0])
	_warteschlange.clear()
	for e in neu:
		_warteschlange.append([e[1], e[2]])


func _nah_erzeugen(e: Array) -> Node3D:
	var q = QuelleScript.new()
	q.position = Vector3(e[1], e[2], e[3])
	var modell: Node3D
	match int(e[0]):
		BAUM:
			modell = BaumSzene.instantiate()
			modell.set("art", int(e[4]))
			modell.set("alter", int(e[5]))
			q.setup("%s_%s" % [BAUM_ID[int(e[4])], ALTER_ID[int(e[5])]], modell, [1.8, 2.4, 3.2][int(e[5])])
		BUSCH:
			modell = BuschSzene.instantiate()
			q.setup("aeste_busch", modell, 1.5)
		STEIN:
			modell = SteinSzene.instantiate()
			var g := int(e[4])
			modell.set("groesse", g)
			q.setup(["felsbrocken_klein", "felsbrocken_klein", "felsbrocken", "felsbrocken_gross", "felsbrocken_gross"][g - 1], modell, 1.3 + 0.55 * g)
		_:
			modell = PflanzeSzene.instantiate()
			modell.set("art", int(e[4]))
			modell.set("farbe", int(e[5]))
			var id := ["hanf", "beeren", "kraut"][int(e[4])] as String
			if int(e[4]) == 2 and int(e[5]) in [4, 5]:
				id = "kraut_selten" # weiße und lila Kräuter sind Silberblatt
			q.setup(id, modell, 1.5)
	_wurzel_nah.add_child(q)
	return q


func _fern_aktualisieren(p: Vector2) -> void:
	var r := int(ceil(FERN_RADIUS / FERN_KACHEL))
	var mitte := Vector2i(floori(p.x / FERN_KACHEL), floori(p.y / FERN_KACHEL))
	var noetig := {}
	var neu: Array = []
	for dz in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var k := mitte + Vector2i(dx, dz)
			var c := (Vector2(k) + Vector2(0.5, 0.5)) * FERN_KACHEL
			var d := c.distance_to(p)
			if d > FERN_RADIUS + FERN_KACHEL * 0.75 or absf(c.x) > welt_m / 2.0 + FERN_KACHEL or absf(c.y) > welt_m / 2.0 + FERN_KACHEL:
				continue
			noetig[k] = true
			if not _fern.has(k) and not _fern_offen.has(k):
				neu.append([d, k])
	neu.sort_custom(func(a, b): return a[0] < b[0])
	for e in neu:
		_fern_offen.append(e[1])
	# Kacheln weit außerhalb entfernen (mit Puffer gegen Flackern), zugehörige Daten freigeben
	for k in _fern.keys():
		var c := (Vector2(k) + Vector2(0.5, 0.5)) * FERN_KACHEL
		if not noetig.has(k) and c.distance_to(p) > FERN_RADIUS + FERN_KACHEL * 1.5:
			_fern[k].queue_free()
			_fern.erase(k)
			for sz in 4:
				for sx in 4:
					var sk := Vector2i(k.x * 4 + sx, k.y * 4 + sz)
					if Vector2(sk).distance_to(p / KACHEL) > NAH_RADIUS / KACHEL + 3:
						_daten.erase(sk)
	_fern_offen = _fern_offen.filter(func(k): return noetig.has(k))


func _fern_bauen(k: Vector2i) -> void:
	if _fern.has(k):
		return
	# je Form ein MultiMesh: 0–2 Fichte/Kiefer/Eiche, 3–5 dieselben uralt (Krone nur im oberen Drittel)
	var je_art: Array = [[], [], [], [], [], []]
	for sz in 4:
		for sx in 4:
			for e in _kachel(Vector2i(k.x * 4 + sx, k.y * 4 + sz)):
				if int(e[0]) == BAUM:
					je_art[int(e[4]) + (3 if int(e[5]) == 2 else 0)].append(e)
	var knoten := Node3D.new()
	knoten.name = "Fern_%d_%d" % [k.x, k.y]
	add_child(knoten)
	for m in _monolithen(k):
		knoten.add_child(_monolith_bauen(m))
	_fern[k] = knoten
	for form in 6:
		var liste: Array = je_art[form]
		if liste.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = _fern_meshes[form]
		mm.instance_count = liste.size()
		for i in liste.size():
			var e: Array = liste[i]
			var g: Vector2 = BAUM_GROESSE[int(e[4])][int(e[5])]
			var faktor := 0.85 + 0.3 * fposmod(float(e[1]) * 0.731 + float(e[3]) * 0.377, 1.0)
			var basis := Basis(Vector3.UP, float(e[6])).scaled(Vector3(g.x, g.y, g.x) * faktor)
			mm.set_instance_transform(i, Transform3D(basis, Vector3(e[1], float(e[2]) - 0.2, e[3])))
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _fern_material
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		knoten.add_child(mmi)


## Felsmonolith mit Kollision (Dreiecksnetz, je Modell einmal berechnet), leicht eingesunken
func _monolith_bauen(m: Array) -> Node3D:
	var name_ := "monolith_%s_%d" % ["turm" if int(m[3]) == 0 else "gruppe", int(m[4])]
	if not _mono_modelle.has(name_):
		var szene: PackedScene = load("res://assets/erz/modelle/%s.glb" % name_)
		var probe := szene.instantiate()
		var mesh: Mesh = (probe.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
		probe.free()
		_mono_modelle[name_] = [mesh, mesh.create_trimesh_shape()]
	var daten: Array = _mono_modelle[name_]
	var koerper := StaticBody3D.new()
	koerper.position = Vector3(m[0], float(m[1]) - 0.4, m[2])
	koerper.rotation.y = float(m[5])
	var mi := MeshInstance3D.new()
	mi.mesh = daten[0]
	mi.material_override = _fels_material()
	koerper.add_child(mi)
	var form := CollisionShape3D.new()
	form.shape = daten[1]
	koerper.add_child(form)
	return koerper


## Material der Felstürme/-gruppen: Fels-Scan triplanar, wenn die Scans da sind, sonst das alte Steinmaterial
var _fels_mat: Material
func _fels_material() -> Material:
	if _fels_mat:
		return _fels_mat
	var basis := "res://assets/scans/rock_face_03/rock_face_03_"
	if ResourceLoader.exists(basis + "diffuse_2k.jpg"):
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://scripts/fels_triplanar.gdshader")
		mat.set_shader_parameter("farbe", load(basis + "diffuse_2k.jpg"))
		mat.set_shader_parameter("normale", load(basis + "nor_gl_2k.jpg"))
		mat.set_shader_parameter("rauheit", load(basis + "rough_2k.jpg"))
		mat.set_shader_parameter("groesse", 4.0)
		_fels_mat = mat
	else:
		_fels_mat = SteinMaterial
	return _fels_mat


# --- einfache Baumformen für die Ferne (Höhe 1, Breite 1, Fuß bei y = 0) ----

const RINDE := Color(0.33, 0.24, 0.17)

func _form(st: SurfaceTool, mesh: PrimitiveMesh, xf: Transform3D, farbe: Color) -> void:
	var arr := mesh.get_mesh_arrays()
	var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var nrm: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
	var idx: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
	for i in idx:
		# Farbe in den UVs (UV = Rot/Grün, UV2.x = Blau): Vertexfarben kommen beim MultiMesh nicht im Shader an
		st.set_uv(Vector2(farbe.r, farbe.g))
		st.set_uv2(Vector2(farbe.b, 0.0))
		st.set_normal((xf.basis * nrm[i]).normalized())
		st.add_vertex(xf * v[i])


func _zylinder(oben: float, unten: float, hoehe: float) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = oben
	m.bottom_radius = unten
	m.height = hoehe
	m.radial_segments = 7
	m.rings = 1
	return m


func _kugel() -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = 0.5
	m.height = 1.0
	m.radial_segments = 8
	m.rings = 5
	return m


func _fichte_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var gruen := Color(0.12, 0.25, 0.14)
	_form(st, _zylinder(0.04, 0.06, 0.3), Transform3D(Basis(), Vector3(0, 0.15, 0)), RINDE)
	_form(st, _zylinder(0.0, 0.5, 0.6), Transform3D(Basis(), Vector3(0, 0.42, 0)), gruen)
	_form(st, _zylinder(0.0, 0.36, 0.5), Transform3D(Basis(), Vector3(0, 0.72, 0)), gruen)
	return st.commit()


func _kiefer_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_form(st, _zylinder(0.03, 0.05, 0.7), Transform3D(Basis(), Vector3(0, 0.35, 0)), RINDE)
	_form(st, _kugel(), Transform3D(Basis().scaled(Vector3(1.0, 0.5, 1.0)), Vector3(0, 0.75, 0)), Color(0.13, 0.24, 0.12))
	return st.commit()


## Uralter Baum aus der Ferne: hoher kahler Stamm, Krone nur im oberen Drittel
func _uralt_mesh(art: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_form(st, _zylinder(0.02, 0.05, 0.8), Transform3D(Basis(), Vector3(0, 0.4, 0)), RINDE)
	match art:
		0:
			_form(st, _zylinder(0.0, 0.45, 0.4), Transform3D(Basis(), Vector3(0, 0.82, 0)), Color(0.12, 0.25, 0.14))
		1:
			_form(st, _kugel(), Transform3D(Basis().scaled(Vector3(1.0, 0.28, 1.0)), Vector3(0, 0.84, 0)), Color(0.13, 0.24, 0.12))
		_:
			_form(st, _kugel(), Transform3D(Basis().scaled(Vector3(1.0, 0.36, 1.0)), Vector3(0, 0.8, 0)), Color(0.16, 0.27, 0.11))
	return st.commit()


func _eiche_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_form(st, _zylinder(0.05, 0.08, 0.45), Transform3D(Basis(), Vector3(0, 0.22, 0)), RINDE)
	_form(st, _kugel(), Transform3D(Basis().scaled(Vector3(1.0, 0.7, 1.0)), Vector3(0, 0.62, 0)), Color(0.16, 0.27, 0.11))
	return st.commit()
