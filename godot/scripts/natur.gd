extends Node3D
## Natur auf der ganzen Insel nach den Biom-Regeln aus data/biome.json (scripts/biom_regeln.gd):
## Bäume (Fichte, Kiefer, Eiche, tote Bäume), Äste-Büsche, Sammelpflanzen (Hanf, Beeren, Kräuter) und
## Bodenobjekte (Stöcke, liegende Stämme, Treibholz, Algen, Pfützen).
##
## Wo etwas wächst, bestimmt das Biom an der Stelle (Biomkarte des Weltgenerators, Flüsse aus fluesse.json,
## Städte/Dörfer aus marker.json), dazu Gelände und Rauschen – in Kacheln von 64 m, jede mit eigenem festen
## Zufall. Dadurch steht bei jedem Laden alles an derselben Stelle, ohne dass etwas gespeichert werden muss.
## In Städten und Dörfern, auf Feldern, an Minen/Dungeons/POIs, im Startgebiet, im Meer und in Seen wächst nichts.
##
## Nah (NAH_RADIUS): echte Blender-Modelle, Bäume und Pflanzen kann man fällen/ernten (scripts/natur_quelle.gd).
## Fern (bis FERN_RADIUS): nur Bäume, als einfache Formen in MultiMeshes je 256-m-Kachel.

const QuelleScript := preload("res://scripts/natur_quelle.gd")
const BaumSzene := preload("res://assets/baeume/baum.tscn")
const BuschSzene := preload("res://assets/baeume/aeste_busch.tscn")
const PflanzeSzene := preload("res://assets/sammeln/sammelpflanze.tscn")
const FernShader := preload("res://scripts/natur_fern.gdshader")
const Wasser := preload("res://scripts/wasser.gd")

const KACHEL := 64.0
const FERN_KACHEL := 256.0
const NAH_RADIUS := 110.0
const FERN_RADIUS := 950.0
const NEU_ZENTRIEREN := 8.0      # Meter Bewegung, ab der der Nahbereich neu sortiert wird
const BUDGET_US := 4000          # Zeit je Frame für neue Nah-Objekte (ein Modell braucht ~2 ms)

enum { BAUM, BUSCH, PFLANZE, TOTBAUM, BODEN }
## Baum-Arten wie in assets/baeume/baum.gd: 0 Fichte, 1 Kiefer, 2 Eiche · Größe (Breite, Höhe) je Alter [jung, alt, uralt]
const BAUM_GROESSE := [[Vector2(2.7, 5.8), Vector2(5.0, 12.9), Vector2(6.6, 20.5)], [Vector2(2.9, 5.2), Vector2(6.8, 11.8), Vector2(8.4, 18.5)],
	[Vector2(2.9, 5.0), Vector2(7.5, 10.7), Vector2(10.5, 16.8)]]
const ALTER_ID := ["jung", "alt", "uralt"]
const BAUM_ID := ["fichte", "kiefer", "eiche"]
## Bodenobjekte (Modelle assets/natur/modelle/<name>_<n>.glb, Pfützen werden im Code gebaut):
## Name -> [Rastergröße der Prüfung in Metern, Kollision (Stämme), Ausrichtung am Hang]
const BODENOBJEKTE := {
	"stock": [8.0, false, true], "baumstamm": [16.0, true, true], "treibholz": [16.0, false, true],
	"alge": [4.0, false, false], "pfuetze": [8.0, false, false],
}
const MODELL_ORDNER := "res://assets/natur/modelle/"

var terrain                       # Terrain3D (Höhen)
var ziel: Node3D                  # Spieler
var welt_m := 8192.0
var raster := 0
var zelle := 4.0
var welt_seed := 0
var biome := PackedByteArray()
var seen := PackedByteArray()
var regeln := {}                  # BiomRegeln.laden()
var frei: Array = []              # freie Kreise im Startgebiet [Vector2 Mitte, Radius] (Dorfplatz, Lager), von main.gd
var sperr := {}                   # Vector2i (32-m-Feld) -> Array von Flächen, die das Feld berühren:
                                  #   ["k", Mitte, Radius] frei (Mine, Dungeon, POI) · ["s", Mitte, Radius] Stadt/Dorf
                                  #   ["f", Mitte, halbe Größe, Winkel] Feld · ["w", a, b, halbe Breite] Fluss
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
var _modelle := {}                # Name -> Array von PackedScene (Bodenobjekte, tote Bäume)
var _pfuetzen: Array = []         # 3 unregelmäßige Wasserflächen


## main = Spielszene (liefert terrain und das Startgebiet), spieler = Mittelpunkt des Streamings
func setup(main, spieler: Node3D, daten_ordner: String) -> void:
	terrain = main.terrain
	ziel = spieler
	regeln = BiomRegeln.laden()
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(daten_ordner.path_join("welt.json")))
	welt_m = float(meta["welt_m"])
	raster = int(meta["raster"])
	zelle = float(meta["zelle_m"])
	welt_seed = int(meta.get("params", {}).get("seed", 1))
	biome = FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["biome"]["datei"]))
	if meta.get("seen") != null:
		seen = FileAccess.get_file_as_bytes(daten_ordner.path_join(meta["seen"]["datei"]))
	_marker_laden(daten_ordner.path_join("marker.json"))
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
	var faktor := {"stadt": 1.15, "dorf": 1.3, "mine": 0.6, "dungeon": 0.6, "poi": 0.5}
	for m in JSON.parse_string(FileAccess.get_file_as_string(pfad)):
		var typ: String = m["typ"]
		var mitte := Vector2(float(m["x"]), float(m["z"]))
		if typ == "feld":
			var halb := Vector2(float(m["breite"]), float(m["laenge"])) / 2.0 + Vector2(2, 2)
			_sperre_eintragen(["f", mitte, halb, float(m["winkel"])], mitte - Vector2.ONE * halb.length(), mitte + Vector2.ONE * halb.length())
		elif faktor.has(typ):
			var r := float(m.get("radius", 30)) * float(faktor[typ]) + 4.0
			_sperre_eintragen(["s" if typ in ["stadt", "dorf"] else "k", mitte, r], mitte - Vector2(r, r), mitte + Vector2(r, r))


## Flussläufe (Biom Fluss: Kiesbett, Algen, kein Gras) – bis 1 m über das Wasser hinaus
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


## Fläche in alle 32-m-Felder eintragen, die ihr Rechteck (von … bis) berührt
func _sperre_eintragen(eintrag: Array, von: Vector2, bis: Vector2) -> void:
	for fy in range(floori(von.y / 32.0), floori(bis.y / 32.0) + 1):
		for fx in range(floori(von.x / 32.0), floori(bis.x / 32.0) + 1):
			var k := Vector2i(fx, fy)
			if not sperr.has(k):
				sperr[k] = []
			sperr[k].append(eintrag)


# --- Wo darf etwas wachsen? ------------------------------------------------

const LEER := {}

## Biom-Regel an einer Weltposition (siehe data/biome.json); leer außerhalb der Karte, im Meer und in Seen.
## Vorrang: Stadt/Dorf, dann Fluss, dann das Biom des Weltgenerators.
func _regel(x: float, z: float) -> Dictionary:
	var cx := int((x + welt_m / 2.0) / zelle)
	var cz := int((z + welt_m / 2.0) / zelle)
	if cx < 0 or cz < 0 or cx >= raster or cz >= raster:
		return LEER
	var i := cz * raster + cx
	if not seen.is_empty() and seen[i] != 0:
		return LEER
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if sperr.has(feld):
		var p := Vector2(x, z)
		var fluss := false
		for s in sperr[feld]:
			if s[0] == "s" and p.distance_to(s[1]) < s[2]:
				return regeln["stadt"]
			if s[0] == "w" and not fluss and Geometry2D.get_closest_point_to_segment(p, s[1], s[2]).distance_to(p) < s[3]:
				fluss = true
		if fluss:
			return regeln["fluss"]
	return regeln["generator"].get(int(biome[i]), LEER)


## Name des Bioms an einer Stelle ("" = Wasser/außerhalb)
func biom_name(x: float, z: float) -> String:
	return String(_regel(x, z).get("biom", ""))


func _gesperrt(x: float, z: float) -> bool:
	var p := Vector2(x, z)
	for f in frei:
		if p.distance_to(f[0]) < f[1]:
			return true
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if not sperr.has(feld):
		return false
	for s in sperr[feld]:
		match s[0]:
			"k", "s":
				if p.distance_to(s[1]) < s[2]:
					return true
			"f":
				if _in_feld(p, s, 0.0):
					return true
	return false


func _in_feld(p: Vector2, s: Array, rand: float) -> bool:
	var d: Vector2 = p - s[1]
	var c := cos(float(s[3]))
	var sn := sin(float(s[3]))
	return absf(d.x * c + d.y * sn) <= s[2].x - rand and absf(-d.x * sn + d.y * c) <= s[2].y - rand


## Liegt der Punkt in einem Feld (für das Gras)?
func _im_feld(x: float, z: float) -> bool:
	var feld := Vector2i(floori(x / 32.0), floori(z / 32.0))
	if not sperr.has(feld):
		return false
	var p := Vector2(x, z)
	for s in sperr[feld]:
		if s[0] == "f" and _in_feld(p, s, 2.0):
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


## Eintrag aus einer Chancen-Tabelle {Name: Anteil} nach r (0–1, auf die Summe bezogen)
func _wahl(tabelle: Dictionary, r: float) -> String:
	var summe := 0.0
	for k in tabelle:
		summe += float(tabelle[k])
	var t := r * summe
	for k in tabelle:
		t -= float(tabelle[k])
		if t <= 0.0:
			return k
	return tabelle.keys()[-1] if not tabelle.is_empty() else ""


## Vorhandene Modelle eines Bodenobjekts bzw. toten Baums (<name>_1.glb, _2.glb …), einmal gesucht
func _modell_liste(name_: String) -> Array:
	if not _modelle.has(name_):
		var liste: Array = []
		for n in range(1, 7):
			var pfad := MODELL_ORDNER + "%s_%d.glb" % [name_, n]
			if ResourceLoader.exists(pfad):
				liste.append(load(pfad))
		_modelle[name_] = liste
	return _modelle[name_]


# --- Kacheln erzeugen -------------------------------------------------------

## Einträge einer 64-m-Kachel: [Art, x, y, z, a, b, Drehung]
## Bäume: a = Baumart, b = Alter · Pflanzen: a = Art (Hanf/Beeren/Kraut), b = Farbe · tote Bäume: a = Variante
## Bodenobjekte: a = Name (String), b = Variante
func _kachel(k: Vector2i) -> Array:
	if _daten.has(k):
		return _daten[k]
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(k.x, k.y, welt_seed))
	var x0 := k.x * KACHEL
	var z0 := k.y * KACHEL
	# Bäume und tote Bäume: gestreutes 7-m-Raster
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
			var regel := _regel(x, z)
			if regel.is_empty():
				continue
			var bm: Dictionary = regel.get("baeume", {})
			var d := 0.5 + 0.5 * rauschen.get_noise_2d(x, z) # Lichtungen und dichte Stellen
			var chance: float = float(bm.get("dichte", 0.0)) + float(bm.get("rauschen", 0.0)) * d
			var tot: float = float(regel.get("totbaeume", 0.0))
			if r_chance >= chance + tot or _gesperrt(x, z):
				continue
			var h := _boden(x, z, 0.7)
			if is_nan(h):
				continue
			if r_chance < chance:
				var art := BAUM_ID.find(_wahl(bm.get("arten", {}), r_art))
				if art < 0:
					continue
				var uralt: float = float(bm.get("uralt", 0.0))
				var alter := 2 if r_alter < uralt else (1 if r_alter < 0.62 else 0)
				out.append([BAUM, x, h, z, art, alter, r_dreh])
			elif not _modell_liste("totbaum").is_empty():
				out.append([TOTBAUM, x, h, z, int(r_art * 1000.0), 0, r_dreh])
	# Äste-Büsche: 16-m-Raster
	n = 4
	s = KACHEL / n
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r := rng.randf()
			var r_dreh := rng.randf() * TAU
			var regel := _regel(x, z)
			if regel.is_empty() or r >= float(regel.get("buesche", 0.0)) or _gesperrt(x, z):
				continue
			var h := _boden(x, z, 0.6)
			if not is_nan(h):
				out.append([BUSCH, x, h, z, 0, 0, r_dreh])
	# Sammelpflanzen: 16-m-Raster. Hanf in kleinen Gruppen (gehäuft, wo das Rauschen hoch ist), Beeren und Kräuter einzeln
	for gz in n:
		for gx in n:
			var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * s
			var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * s
			var r := rng.randf()
			var r_farbe := rng.randi_range(0, 3)
			var r_anzahl := rng.randi_range(3, 6)
			var regel := _regel(x, z)
			if regel.is_empty() or _gesperrt(x, z):
				continue
			var pf: Dictionary = regel.get("pflanzen", {})
			var hanf: float = float(pf.get("hanf", 0.0)) * (0.5 + 0.5 * rauschen.get_noise_2d(x * 3.0, z * 3.0) + 0.5)
			var beeren: float = float(pf.get("beeren", 0.0))
			var kraut: float = float(pf.get("kraut", 0.0))
			if r < hanf:
				for i in r_anzahl:
					var hx := x + rng.randf_range(-3.0, 3.0)
					var hz := z + rng.randf_range(-3.0, 3.0)
					var h := _boden(hx, hz, 0.5)
					if not is_nan(h) and _regel(hx, hz) == regel:
						out.append([PFLANZE, hx, h, hz, 0, 0, rng.randf() * TAU])
			elif r < hanf + beeren:
				var h := _boden(x, z, 0.5)
				if not is_nan(h):
					out.append([PFLANZE, x, h, z, 1, r_farbe, 0.0])            # Beeren: rot/blau/schwarz/gelb
			elif r < hanf + beeren + kraut:
				var h := _boden(x, z, 0.5)
				if not is_nan(h):
					out.append([PFLANZE, x, h, z, 2, [4, 3, 5, 0][r_farbe], 0.0]) # Kräuter: weiß/gelb/lila/rot
	# Bodenobjekte: je Art ein eigenes Raster (Stöcke dicht, Stämme selten)
	for name_ in BODENOBJEKTE:
		var raster_m: float = BODENOBJEKTE[name_][0]
		var m := int(KACHEL / raster_m)
		var hat_modell: bool = name_ == "pfuetze" or not _modell_liste(name_).is_empty()
		for gz in m:
			for gx in m:
				var x := x0 + (gx + 0.1 + 0.8 * rng.randf()) * raster_m
				var z := z0 + (gz + 0.1 + 0.8 * rng.randf()) * raster_m
				var r := rng.randf()
				var r_var := rng.randi_range(0, 999)
				var r_dreh := rng.randf() * TAU
				if not hat_modell:
					continue
				var regel := _regel(x, z)
				if regel.is_empty() or r >= float(regel.get("bodenobjekte", {}).get(name_, 0.0)) or _gesperrt(x, z):
					continue
				var h := _boden(x, z, 0.12 if name_ == "pfuetze" else 0.6)
				if not is_nan(h):
					out.append([BODEN, x, h, z, name_, r_var, r_dreh])
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
	match int(e[0]):
		TOTBAUM:
			return _totbaum(e)
		BODEN:
			return _bodenobjekt(e)
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


## Toter Baum (Moor): kahler Stamm mit Ästen, mit Kollision, nicht fällbar
func _totbaum(e: Array) -> Node3D:
	var liste := _modell_liste("totbaum")
	var koerper := StaticBody3D.new()
	koerper.name = "Totbaum"
	koerper.position = Vector3(e[1], float(e[2]) - 0.15, e[3])
	koerper.rotation.y = float(e[6])
	koerper.add_child(_mit_materialien((liste[int(e[4]) % liste.size()] as PackedScene).instantiate(), true))
	var form := CollisionShape3D.new()
	var zyl := CylinderShape3D.new()
	zyl.radius = 0.35
	zyl.height = 6.0
	form.shape = zyl
	form.position.y = 3.0
	koerper.add_child(form)
	_wurzel_nah.add_child(koerper)
	return koerper


## Bodenobjekt: Modell flach auf den Boden gelegt (am Hang mitgeneigt); liegende Stämme mit Kollision
func _bodenobjekt(e: Array) -> Node3D:
	var name_: String = e[4]
	var x: float = e[1]
	var z: float = e[3]
	var h: float = e[2]
	var knoten: Node3D
	if name_ == "pfuetze":
		knoten = MeshInstance3D.new()
		(knoten as MeshInstance3D).mesh = _pfuetze_mesh(int(e[5]) % 3)
		(knoten as MeshInstance3D).material_override = _pfuetzen_material()
		knoten.position = Vector3(x, _tiefster_punkt(x, z, 1.6) + 0.06, z)
		knoten.rotation.y = float(e[6])
		knoten.scale = Vector3.ONE * (0.9 + 0.9 * (int(e[5]) % 7) / 6.0)
		_wurzel_nah.add_child(knoten)
		return knoten
	var liste := _modell_liste(name_)
	var modell: Node3D = _mit_materialien((liste[int(e[5]) % liste.size()] as PackedScene).instantiate(), false)
	var info: Array = BODENOBJEKTE[name_]
	if info[1]:
		knoten = StaticBody3D.new()
		var aabb := _aabb(modell)
		var form := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = aabb.size * Vector3(1.0, 0.8, 0.8)
		form.shape = box
		form.position = aabb.get_center()
		knoten.add_child(form)
	else:
		knoten = Node3D.new()
	knoten.add_child(modell)
	var basis := Basis(Vector3.UP, float(e[6]))
	if info[2]: # am Hang mitneigen
		var nx := _hoehe(x + 1.0, z) - _hoehe(x - 1.0, z)
		var nz := _hoehe(x, z + 1.0) - _hoehe(x, z - 1.0)
		var normale := Vector3(-nx, 2.0, -nz).normalized()
		basis = Basis(Quaternion(Vector3.UP, normale)) * basis
	knoten.transform = Transform3D(basis, Vector3(x, h - 0.04, z))
	_wurzel_nah.add_child(knoten)
	return knoten


## Material-Slots der Modelle (assets/natur/blender/natur_modelle.py) durch die Spielmaterialien ersetzen:
## Rinde (Scan, wenn vorhanden), Schnittfläche, Moos, ausgebleichtes Treibholz, Algen. Tote Bäume: graue Rinde.
var _mats := {}
func _mit_materialien(n: Node3D, tot: bool) -> Node3D:
	if _mats.is_empty():
		var rinde: Material = Baum._scan_rinde("bark_brown_02")
		if rinde == null:
			rinde = load("res://assets/baeume/materialien/eiche_rinde.tres")
		var grau: Material = Baum._scan_rinde("knotted_pine_bark", Color(0.78, 0.76, 0.72))
		if grau == null:
			grau = (load("res://assets/baeume/materialien/kiefer_rinde.tres") as StandardMaterial3D).duplicate()
			grau.albedo_color = Color(0.7, 0.68, 0.64)
		var moos := StandardMaterial3D.new()
		moos.albedo_color = Color(0.26, 0.36, 0.13)
		moos.roughness = 1.0
		moos.normal_enabled = true
		moos.normal_texture = load("res://assets/baeume/texturen/eiche_rinde_normal.png")
		var bleich := (rinde as StandardMaterial3D).duplicate()
		bleich.albedo_color = Color(1.55, 1.45, 1.3)
		var alge := StandardMaterial3D.new()
		alge.albedo_color = Color(0.17, 0.32, 0.1)
		alge.roughness = 0.5
		alge.cull_mode = BaseMaterial3D.CULL_DISABLED
		_mats = {"rinde": rinde, "rinde_tot": grau, "schnitt": load("res://assets/baeume/materialien/schnitt.tres"),
			"moos": moos, "treibholz": bleich, "alge": alge}
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = (mi as MeshInstance3D).mesh
		for i in mesh.get_surface_count():
			var m := mesh.surface_get_material(i)
			if m == null:
				continue
			var name_ := m.resource_name
			if tot and name_ == "rinde":
				name_ = "rinde_tot"
			if _mats.has(name_):
				(mi as MeshInstance3D).set_surface_override_material(i, _mats[name_])
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF if not tot and n.name.begins_with("alge") \
			else GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return n


func _aabb(n: Node3D) -> AABB:
	var box := AABB()
	var erste := true
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var b: AABB = (mi as MeshInstance3D).get_aabb()
		box = b if erste else box.merge(b)
		erste = false
	return box


## Tiefste Geländehöhe im Umkreis (Pfützen liegen in Mulden und sollen nirgends schweben)
func _tiefster_punkt(x: float, z: float, r: float) -> float:
	var h := _hoehe(x, z)
	for i in 8:
		var p := Vector2.from_angle(TAU * i / 8.0) * r
		h = minf(h, _hoehe(x + p.x, z + p.y))
	return h


## Dunkles, spiegelndes Moorwasser (leicht durchsichtig, damit der Schlamm durchscheint)
var _pfuetzen_mat: StandardMaterial3D
func _pfuetzen_material() -> StandardMaterial3D:
	if _pfuetzen_mat == null:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.07, 0.08, 0.06, 0.88)
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.roughness = 0.04
		m.metallic_specular = 0.9
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		_pfuetzen_mat = m
	return _pfuetzen_mat


## Unregelmäßige flache Wasserfläche (etwa 2–4 m), drei Formen
func _pfuetze_mesh(v: int) -> ArrayMesh:
	if _pfuetzen.is_empty():
		for form in 3:
			var st := SurfaceTool.new()
			st.begin(Mesh.PRIMITIVE_TRIANGLES)
			var rand: Array[Vector3] = []
			var stufen := 14
			for i in stufen:
				var a := TAU * i / stufen
				var r := 1.4 + 0.45 * sin(a * 2.0 + form * 1.7) + 0.3 * sin(a * 3.0 + form * 0.9)
				rand.append(Vector3(cos(a) * r * (1.3 if form == 1 else 1.0), 0.0, sin(a) * r))
			for i in stufen:
				for p in [Vector3.ZERO, rand[i], rand[(i + 1) % stufen]]:
					st.set_normal(Vector3.UP)
					st.set_uv(Vector2(p.x, p.z))
					st.add_vertex(p)
			_pfuetzen.append(st.commit())
	return _pfuetzen[v]


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
