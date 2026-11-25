class_name SpielerAnimation
extends Node
## Spielt die Animationen eines Menschen (Spieler, später auch NPCs und menschliche Gegner).
## Zwei Arten: Grundbewegung (Stehen, Gehen, Rennen, Springen, Blocken), die jedes Bild aus dem
## Zustand gewählt wird, und einmalige Bewegungen (Schlag, Rolle, Treffer, Tod), die die Grundbewegung
## für ihre Dauer überdecken. Die Animationen kommen aus MenschAnimationen (Quaternius, CC0) und,
## wenn lokal vorhanden, aus den Mixamo-Bibliotheken je Waffe (SAETZE). Fehlt eine Mixamo-Animation,
## wird die Quaternius-Animation genommen.

const UEBERGANG := 0.15          # Überblendzeit in s
const GEH_TEMPO := 1.4           # m/s, bei dem "Walk" ohne Rutschen läuft
const LAUF_TEMPO := 4.6          # m/s für "Jog_Fwd"
const SPRINT_TEMPO := 7.5        # m/s für "Sprint"

## Schlagarten aus weapons.json -> [Animation, Anteil der Animation bis zum Treffer, Erholung danach]
const SCHLAEGE := {
	"h_right": ["Sword_Regular_A", 0.7, "Sword_Regular_A_Rec"],
	"h_left": ["Sword_Regular_B", 0.7, "Sword_Regular_B_Rec"],
	"diag": ["Sword_Regular_A", 0.7, "Sword_Regular_A_Rec"],
	"overhead": ["Sword_Attack", 0.42, ""],
	"big_overhead": ["Sword_Attack", 0.42, ""],
	"thrust": ["Punch_Jab", 0.35, ""],
	"cast": ["Spell_Simple_Shoot", 0.4, ""],
	"spin": ["Sword_Regular_C", 0.3, ""],
}

## Animationen je Waffe (Mixamo, Namen "<bibliothek>/<animation>"). Richtungen immer [vor, zurück, links, rechts].
## schlaege: Schlagart -> Animation (Treffer am schnellsten Punkt der rechten Hand) oder [Animation, Treffer-Anteil].
const SS := "schwert_schild/sword_and_shield_"
const GS := "grossschwert/great_sword_"
const AX := "axt/standing_"
const BO := "bogen/standing_"
const GW := "gewehr/"
const MA := "magie/standing_"
const BW := "bewegung/"
const EZ := "einzeln/"
const SAETZE := {
	"sword_shield": {
		"ruhe": SS + "idle_4", "gehen": [SS + "walk", SS + "walk_2", SS + "strafe_2", SS + "strafe"],
		"rennen": [SS + "run", SS + "run_2", SS + "strafe_3", SS + "strafe_4"], "block": SS + "block_idle",
		"block_treffer": SS + "block", "schlaege": {"h_right": SS + "slash", "h_left": SS + "slash_3",
			"overhead": SS + "attack_4", "big_overhead": SS + "slash", "thrust": SS + "slash_5"},
		"treffer": SS + "impact", "tod": SS + "death", "buff": SS + "power_up", "dash": SS + "slash_5",
		"spin": GS + "high_spin_attack",
	},
	"greatsword": {
		"ruhe": GS + "idle", "gehen": [GS + "walk", GS + "walk_2", GS + "strafe", GS + "strafe_2"],
		"rennen": [GS + "run_2", GS + "run", GS + "strafe_3", GS + "strafe_4"], "block": GS + "blocking_2",
		"schlaege": {"h_right": GS + "slash", "h_left": GS + "slash_3", "overhead": GS + "attack",
			"big_overhead": GS + "slash", "diag": GS + "slash", "thrust": GS + "attack"},
		"treffer": GS + "impact", "tod": "grossschwert/two_handed_sword_death", "buff": GS + "power_up",
		"dash": GS + "slash_5", "leap": GS + "attack", "spin": GS + "high_spin_attack",
	},
	"axe": {
		"ruhe": AX + "idle", "gehen": [AX + "walk_forward", AX + "walk_back", AX + "walk_left", AX + "walk_right"],
		"rennen": [AX + "run_forward", AX + "run_back", AX + "walk_left", AX + "walk_right"], "block": AX + "block_idle",
		"block_treffer": AX + "block_react_large", "schlaege": {"diag": AX + "melee_attack_horizontal",
			"h_right": AX + "melee_attack_horizontal", "h_left": AX + "melee_attack_backhand",
			"overhead": AX + "melee_attack_downward", "big_overhead": AX + "melee_attack_downward"},
		"treffer": AX + "react_large_gut", "buff": AX + "taunt_battlecry", "spin": AX + "melee_attack_360_high",
		"leap": AX + "melee_attack_downward", "dash": AX + "melee_attack_horizontal",
	},
	"rapier": {
		"ruhe": "Sword_Idle", "gehen": [BW + "walking", "", BW + "left_strafe_walking", BW + "right_strafe_walking"],
		"schlaege": {"thrust": EZ + "stabbing", "h_right": EZ + "stable_sword_outward_slash",
			"h_left": EZ + "stable_sword_inward_slash"},
		"dash": EZ + "stabbing",
	},
	"spear": {
		"ruhe": GW + "idle", "gehen": [GW + "walk_forward", GW + "walk_backward", GW + "walk_left", GW + "walk_right"],
		"rennen": [GW + "run_forward", GW + "run_backward", GW + "run_left", GW + "run_right"],
		"block": GS + "blocking_2", "schlaege": {"thrust": EZ + "bayonet_stab", "h_right": AX + "melee_attack_horizontal"},
		"tod": GW + "death_from_the_front", "leap": GS + "attack", "dash": EZ + "bayonet_stab",
	},
	"knife": {
		"gehen": [BW + "walking", "", BW + "left_strafe_walking", BW + "right_strafe_walking"],
		"schlaege": {"thrust": EZ + "double_dagger_stab"},
	},
	"bow": {
		"ruhe": BO + "idle_01", "gehen": [BO + "walk_forward", BO + "walk_back", BO + "walk_left", BO + "walk_right"],
		"rennen": [BO + "run_forward", BO + "run_back", BO + "run_left", BO + "run_right"],
		"zielen": [BO + "aim_overdraw", 0.3], "ziel_gehen": [BO + "aim_walk_forward", BO + "aim_walk_back",
			BO + "aim_walk_left", BO + "aim_walk_right"], "spannen": BO + "draw_arrow", "schuss": BO + "aim_recoil",
		"treffer": BO + "react_small_from_front", "tod": BO + "death_backward_01",
		"ausweichen": [BO + "dodge_forward", BO + "dodge_backward", BO + "dodge_left", BO + "dodge_right"],
	},
	"musket": {
		"ruhe": GW + "idle", "gehen": [GW + "walk_forward", GW + "walk_backward", GW + "walk_left", GW + "walk_right"],
		"rennen": [GW + "run_forward", GW + "run_backward", GW + "run_left", GW + "run_right"],
		"zielen": GW + "idle_aiming", "ziel_gehen": [GW + "walk_forward", GW + "walk_backward", GW + "walk_left", GW + "walk_right"],
		"schuss": GW + "idle_aiming", "nachladen": GW + "idle_crouching",
		"tod": GW + "death_from_the_front", "ausweichen": [BO + "dodge_forward", BO + "dodge_backward", BO + "dodge_left", BO + "dodge_right"],
	},
	"magic": {
		"ruhe": MA + "idle", "gehen": [MA + "walk_forward", MA + "walk_back", MA + "walk_left", MA + "walk_right"],
		"rennen": [MA + "run_forward", MA + "run_back", MA + "run_left", MA + "run_right"],
		"zielen": MA + "idle", "ziel_gehen": [MA + "walk_forward", MA + "walk_back", MA + "walk_left", MA + "walk_right"],
		"schuss": [MA + "2h_magic_attack_04", MA + "2h_magic_attack_05", MA + "2h_magic_attack_03"],
		"zone": MA + "2h_magic_area_attack_02", "buff": MA + "2h_cast_spell_01", "beschwoeren": MA + "1h_cast_spell_01",
		"treffer": MA + "react_small_from_front", "tod": MA + "react_death_backward", "schlaege": {"overhead": MA + "2h_magic_attack_01"},
	},
}
## Waffen ohne eigenen Satz nehmen den einer verwandten Waffe.
const SATZ_VON := {"hammer": "greatsword", "crossbow": "musket", "fire_magic": "magic", "ice_magic": "magic",
	"lightning_magic": "magic", "life_magic": "magic", "void_magic": "magic"}

var mensch: Mensch
var satz := {}                   # Satz der aktuellen Waffe (nur vorhandene Animationen)
var ap: AnimationPlayer
var _einmal := ""                # laufende einmalige Animation ("" = Grundbewegung)
var _einmal_rest := 0.0          # verbleibende Zeit der einmaligen Animation
var _danach := ""                # folgt auf die einmalige Animation (z. B. Erholung nach dem Schlag)
var _halten := false             # letzte Pose der einmaligen Animation halten (Tod)
var _frei_ab := INF              # ab dieser Restzeit darf Bewegung die einmalige Animation abbrechen
var _schuss_nr := 0
var _waffe := ""
var _in_luft := 0.0
var _landen := 0.0


func _init(m: Mensch) -> void:
	mensch = m
	name = "Animation"


func _ready() -> void:
	ap = MenschAnimationen.spieler_anhaengen(mensch)
	ap.playback_default_blend_time = UEBERGANG
	ap.play(_voll("Idle"))
	if _waffe != "":
		waffe_setzen(_waffe)


static func _voll(n: String) -> String:
	return n if n.contains("/") else MenschAnimationen.BIBLIOTHEK + "/" + n


## Wählt den Animationssatz der Waffe (Waffen-ID aus weapons.json, "" = nur Quaternius).
func waffe_setzen(typ: String) -> void:
	_waffe = typ
	satz = {}
	if ap == null:
		return # wird in _ready nachgeholt
	var roh: Dictionary = SAETZE.get(SATZ_VON.get(typ, typ), {}).duplicate(true)
	# Auswahl aus der Animations-Werkstatt (data/animationen_wahl.json) hat Vorrang
	var eigene: Dictionary = wahl().get(typ, {})
	for k: String in eigene:
		if k == "notizen" or String(eigene[k]) == "":
			continue
		if k.begins_with("schlaege/"):
			if not roh.has("schlaege"):
				roh["schlaege"] = {}
			roh["schlaege"][k.trim_prefix("schlaege/")] = eigene[k]
		else:
			roh[k] = eigene[k]
	for k in roh:
		var v = roh[k]
		if v is Dictionary:
			var d := {}
			for art in v:
				if _da(v[art]):
					d[art] = v[art]
			satz[k] = d
		elif v is Array and v.size() == 4 and not (v[1] is float):
			var liste: Array = v.map(func(n): return n if _da(n) else "")
			if liste.any(func(n): return n != ""): # nur Richtungen behalten, von denen es Animationen gibt
				satz[k] = liste
		elif _da(v):
			satz[k] = v


func _da(v) -> bool:
	if v is Array:
		return not v.is_empty() and _da(v[0])
	return v is String and v != "" and ap != null and ap.has_animation(_voll(v))


## Name aus dem Satz (bei [Name, Wert] der Name), sonst `ersatz`.
func _aus(schluessel: String, ersatz: String) -> String:
	var v = satz.get(schluessel, "")
	if v is Array:
		v = v[0]
	return v if v != "" else ersatz


## Spielt eine Animation einmal. `dauer` > 0 streckt sie auf diese Länge, `halten` friert das Ende ein.
## `bis` (0–1) spielt nur bis zu diesem Anteil der Animation.
## Schleifen (Haltungen wie Zielen oder Knien) laufen in normalem Tempo für `dauer` und werden weicher überblendet.
func einmal(n: String, dauer := -1.0, halten := false, danach := "", bis := 1.0) -> void:
	if not ap.has_animation(_voll(n)):
		return
	var anim := ap.get_animation(_voll(n))
	var schleife := anim.loop_mode != Animation.LOOP_NONE and dauer > 0.0
	var laenge := dauer if schleife else anim.length * bis
	var tempo := 1.0 if dauer <= 0.0 or schleife else clampf(laenge / dauer, 0.4, 3.0)
	ap.speed_scale = 1.0
	var gleich := ap.assigned_animation == _voll(n)
	ap.play(_voll(n), UEBERGANG * (2.0 if schleife else 0.6), tempo)
	if gleich:
		ap.seek(0.0, true)
	_einmal = n
	_einmal_rest = laenge / tempo
	_halten = halten
	_danach = danach
	_frei_ab = INF


## Schlag nach Schlagart: die Animation wird so schnell abgespielt, dass ihr Treffer auf `treffer` (s) fällt.
func schlag(art: String, treffer: float) -> void:
	var s: Array = SCHLAEGE.get(art, SCHLAEGE["h_right"])
	var eigene: Dictionary = satz.get("schlaege", {})
	if eigene.has(art):
		var e = eigene[art]
		var n: String = e[0] if e is Array else e
		var anteil: float = e[1] if e is Array else float(ap.get_animation(_voll(n)).get_meta("treffer", 0.4))
		s = [n, clampf(anteil, 0.15, 0.8), ""]
	var laenge := ap.get_animation(_voll(s[0])).length if ap.has_animation(_voll(s[0])) else 0.5
	var bis_treffer := laenge * float(s[1])
	einmal(s[0], laenge * treffer / maxf(bis_treffer, 0.05), false, s[2])
	# kurz nach dem Treffer darf Laufen die Nachbewegung abbrechen
	_frei_ab = maxf(0.0, _einmal_rest - treffer - 0.25)


## Einmalige Animation aus dem Satz (z. B. "buff", "dash", "tod"), sonst `ersatz`.
## `abbrechbar`: Laufen darf sie beenden (nicht bei Ansturm und Sprung, die selbst schnell bewegen).
func satz_einmal(schluessel: String, ersatz: String, dauer := -1.0, halten := false, abbrechbar := true) -> void:
	einmal(_aus(schluessel, ersatz), dauer, halten)
	if not halten and abbrechbar:
		_frei_ab = INF if dauer <= 0.0 else 0.0
		if dauer <= 0.0:
			_frei_ab = maxf(0.0, _einmal_rest - 0.5)


## Schuss mit Fernkampfwaffe oder Zauber (Magie wechselt zwischen mehreren Würfen ab).
## `aus_ruhe`: der Bogen war nicht gespannt (Fähigkeit), also erst kurz spannen.
func schuss(magie: bool, dauer: float, aus_ruhe := false) -> void:
	var v = satz.get("schuss", "")
	if v is Array and not v.is_empty():
		_schuss_nr += 1
		v = v[_schuss_nr % v.size()] if _da(v[_schuss_nr % v.size()]) else v[0]
	if v is String and v != "":
		var a := ap.get_animation(_voll(v))
		if aus_ruhe and not magie and _da(satz.get("spannen", "")):
			einmal(satz["spannen"], 0.25, false, v)
			return
		var anteil := float(a.get_meta("treffer", 0.3)) if magie else 0.0
		# Zauber: bis zum Wurf in `dauer`, danach mit gleichem Tempo weiter (Laufen bricht ab)
		einmal(v, a.length * dauer / maxf(a.length * anteil, 0.05) if magie else dauer)
		_frei_ab = maxf(0.0, _einmal_rest - dauer)
		return
	if satz.has("zielen"):
		return # kein eigener Schuss (Muskete, Armbrust): Zielhaltung bleibt
	einmal("Spell_Simple_Shoot" if magie else "Pistol_Shoot", dauer)


## Ausweichschritt in eine Richtung (Weg relativ zur Figur: x rechts, y vorn).
func ausweichen(richtung: Vector2, dauer: float) -> bool:
	var v = satz.get("ausweichen", [])
	if not v is Array or v.size() < 4:
		return false
	var n: String = v[_richtung_index(richtung)]
	if n == "":
		return false
	einmal(n, dauer)
	return true


## Endlosschleife (Sammeln, Angeln): läuft, bis eine andere Animation sie ablöst.
func schleife(n: String, tempo := 1.0) -> void:
	if not ap.has_animation(_voll(n)):
		return
	ap.speed_scale = 1.0
	ap.play(_voll(n), UEBERGANG, tempo)
	_einmal = n
	_einmal_rest = INF
	_halten = false
	_danach = ""


## Bricht einmalige Animationen ab (die Grundbewegung übernimmt im nächsten Bild).
func zuruecksetzen() -> void:
	_einmal = ""
	_einmal_rest = 0.0
	_halten = false
	_danach = ""


func ist_frei() -> bool:
	return _einmal == ""


## Jedes Bild: Grundbewegung aus dem Zustand des Spielers.
## tempo = waagerechte Geschwindigkeit (m/s), kampf = Waffe gezogen, block/zielen = Haltung.
## lokal = Bewegung relativ zur Blickrichtung der Figur (x rechts, y vorn, m/s); leer = nach vorn.
func bewegen(delta: float, tempo: float, am_boden: bool, kampf: bool, block: bool, schild: bool, zielen: bool, fernkampf: String, lokal := Vector2.INF) -> void:
	if lokal == Vector2.INF:
		lokal = Vector2(0.0, tempo)
	if _einmal != "":
		_einmal_rest -= delta
		if _einmal_rest > 0.0 and not (_einmal_rest <= _frei_ab and tempo > 0.8 and am_boden):
			return
		if _einmal_rest > 0.0:
			_einmal_rest = 0.0
			_danach = ""
			_halten = false
		if _halten:
			ap.pause()
			_einmal_rest = INF
			return
		if _danach != "":
			var d := _danach
			_danach = ""
			einmal(d)
			return
		_einmal = ""
	# Sprung: Absprung, Flug, Landung
	if not am_boden:
		_in_luft += delta
		if _in_luft > 0.12:
			_grund("Jump" if _in_luft > 0.35 else "Jump_Start")
			return
	elif _in_luft > 0.35:
		_landen = 0.25
	if am_boden:
		_in_luft = 0.0
	if _landen > 0.0:
		_landen -= delta
		_grund("Jump_Land", 1.6)
		return
	if block:
		if tempo >= 0.4 and satz.has("gehen"):
			_richtung(satz["gehen"], lokal, tempo)
		elif satz.has("block"):
			_grund(satz["block"])
		else:
			_grund("Idle_Shield" if schild else "Sword_Block", 1.0, 0.0 if schild else 0.35)
		return
	if zielen:
		if tempo >= 0.4 and _richtung(satz.get("ziel_gehen", []), lokal, tempo):
			return
		var z = satz.get("zielen", "")
		if z is Array:
			_grund(z[0], 1.0, z[1])
		elif z != "":
			_grund(z)
		else:
			_grund("Spell_Simple_Idle" if fernkampf == "magic" else "Pistol_Aim_Neutral")
		return
	if kampf and tempo >= 0.4 and tempo < (LAUF_TEMPO + SPRINT_TEMPO) * 0.5:
		var lauf := tempo >= (GEH_TEMPO + LAUF_TEMPO) * 0.5 and satz.has("rennen")
		if _richtung(satz.get("rennen" if lauf else "gehen", []), lokal, tempo):
			return
	if tempo < 0.4:
		_grund(_aus("ruhe", ("Sword_Idle" if fernkampf == "" else "Pistol_Idle")) if kampf else "Idle")
	elif tempo < (GEH_TEMPO + LAUF_TEMPO) * 0.5:
		_grund("Walk", clampf(tempo / GEH_TEMPO, 0.6, 2.2))
	elif tempo < (LAUF_TEMPO + SPRINT_TEMPO) * 0.5:
		_grund("Jog_Fwd", clampf(tempo / LAUF_TEMPO, 0.7, 1.6))
	else:
		_grund("Sprint", clampf(tempo / SPRINT_TEMPO, 0.7, 1.5))


## Gehen/Rennen in Richtung `lokal` mit einer der 4 Richtungsanimationen; Tempo nach dem Weg der Animation.
func _richtung(liste, lokal: Vector2, tempo: float) -> bool:
	if not liste is Array or liste.size() < 4:
		return false
	var n: String = liste[_richtung_index(lokal)]
	if n == "":
		n = liste[0]
		if lokal.y < -0.3: # kein Rückwärts: vorwärts gehen geht nicht, dann Quaternius
			return false
	if n == "" or not ap.has_animation(_voll(n)):
		return false # fehlt die Mixamo-Animation, übernimmt die Quaternius-Bewegung
	var weg: Vector3 = ap.get_animation(_voll(n)).get_meta("weg", Vector3(0, 0, GEH_TEMPO))
	var eigen := Vector2(weg.x, weg.z).length()
	_grund(n, clampf(tempo / maxf(eigen, 0.3), 0.6, 1.8))
	return true


static func _richtung_index(lokal: Vector2) -> int:
	if absf(lokal.y) >= absf(lokal.x) * 0.8:
		return 0 if lokal.y >= 0.0 else 1
	return 3 if lokal.x > 0.0 else 2


## Wechselt zur Grundbewegung n (ohne Neustart, wenn sie schon läuft). `standbild` >= 0 hält diese Stelle (0–1).
func _grund(n: String, tempo := 1.0, standbild := -1.0) -> void:
	var v := _voll(n)
	if ap.assigned_animation != v or (not ap.is_playing() and standbild < 0.0):
		ap.play(v, UEBERGANG)
		if standbild >= 0.0:
			ap.seek(ap.get_animation(v).length * standbild, true)
			ap.pause()
	ap.speed_scale = tempo


## Hängt einen Knoten an eine Hand (BoneAttachment3D, Griff in der Handfläche).
## Die Klinge eines Modells zeigt entlang -Z; sie zeigt dann vom kleinen Finger zum Zeigefinger.
func an_hand(knoten: Node3D, links: bool) -> void:
	var sk := mensch.skelett
	var seite := "Left" if links else "Right"
	var griff: Node3D = sk.get_node_or_null(seite + "Hand/Griff")
	if griff == null:
		var halter := BoneAttachment3D.new()
		halter.name = seite + "Hand"
		halter.bone_idx = sk.find_bone(seite + "Hand")
		sk.add_child(halter)
		griff = Node3D.new()
		griff.name = "Griff"
		griff.transform = griff_transform(sk, links)
		halter.add_child(griff)
	if knoten.get_parent() == griff:
		return
	if knoten.get_parent():
		knoten.get_parent().remove_child(knoten)
	griff.add_child(knoten)
	knoten.transform = Transform3D()


## Griff relativ zum Handknochen, aus der Ruhe der Fingerknochen berechnet (passt zu jeder Körperform).
static func griff_transform(sk: Skeleton3D, links: bool) -> Transform3D:
	var seite := "Left" if links else "Right"
	var hand := sk.get_bone_global_rest(sk.find_bone(seite + "Hand"))
	var inv := hand.affine_inverse()
	var zeige := inv * sk.get_bone_global_rest(sk.find_bone(seite + "IndexProximal")).origin
	var klein := inv * sk.get_bone_global_rest(sk.find_bone(seite + "LittleProximal")).origin
	var mitte := inv * sk.get_bone_global_rest(sk.find_bone(seite + "MiddleProximal")).origin
	var finger := mitte.normalized()                       # Richtung der Finger (Handknochen-Y)
	var klinge := (zeige - klein).normalized()             # quer durch die Faust
	klinge = (klinge - finger * finger.dot(klinge)).normalized()
	var z := -klinge
	var y := finger
	var x := y.cross(z).normalized()
	# Handfläche: senkrecht zu Finger und Klinge; Griff liegt zwischen Handwurzel und Fingeransatz
	var pos := mitte * 0.75
	var flaeche := x * (0.025 if links else -0.025)
	return Transform3D(Basis(x, y, z), pos + flaeche)


# --- Griffe (Philipp, 25.11.) -----------------------------------------------
## Je Waffe in data/griffe.json: Hand ("rechts"/"links"), Lage der Waffe im Griff der Hand (pos in m, rot in Grad)
## und bei Zweihändern der Punkt, an dem die zweite Hand greift ("zweite", im Raum der Waffe). Vorausgerichtet aus
## den Mixamo-Posen (tests/griffe_vorausrichten.gd), einstellbar in der Animations-Werkstatt.
const GRIFFE_DATEI := "res://data/griffe.json"
static var _griffe = null

var _ik: TwoBoneIK3D
var _ik_ziel: Node3D
var _zweite: Node3D               # Griffpunkt der linken Hand an der Waffe (null = einhändig)
var _zweite_versatz := Vector3.ZERO


const WAHL_DATEI := "res://data/animationen_wahl.json"
static var _wahl = null


## Animationen je Waffe und Platz aus der Werkstatt: {waffe: {"schlaege/h_right": "lib/anim", "buff": …, "notizen": {platz: text}}}.
static func wahl() -> Dictionary:
	if _wahl == null:
		_wahl = {}
		if FileAccess.file_exists(WAHL_DATEI):
			var d = JSON.parse_string(FileAccess.get_file_as_string(WAHL_DATEI))
			if d is Dictionary:
				_wahl = d
	return _wahl


static func wahl_speichern(d: Dictionary) -> bool:
	_wahl = d
	var f := FileAccess.open(WAHL_DATEI, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(d, "\t", false))
	return true


static func griffe() -> Dictionary:
	if _griffe == null:
		_griffe = {}
		var f := FileAccess.open(GRIFFE_DATEI, FileAccess.READ)
		if f:
			var d = JSON.parse_string(f.get_as_text())
			if d is Dictionary:
				_griffe = d
	return _griffe


static func griffe_speichern(d: Dictionary) -> bool:
	_griffe = d
	var f := FileAccess.open(GRIFFE_DATEI, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(d, "\t", false))
	return true


static func _v(a, standard := Vector3.ZERO) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2])) if a is Array and a.size() == 3 else standard


## Griff einer Waffe: {"links": bool, "pos": Vector3, "rot": Vector3 (Grad), "zweite": Vector3 oder null}.
static func griff(typ: String) -> Dictionary:
	var g: Dictionary = griffe().get(typ, {})
	return {"links": String(g.get("hand", "rechts")) == "links", "pos": _v(g.get("pos")), "rot": _v(g.get("rot")),
		"zweite": _v(g.get("zweite")) if g.get("zweite") is Array else null}


## Zweite Hand an die Waffe: `punkt` im Raum von `waffe` (null = loslassen). Die linke Hand greift per IK dorthin.
func zweite_hand(waffe: Node3D, punkt: Variant) -> void:
	if punkt == null or waffe == null:
		if _zweite:
			_zweite.queue_free()
		_zweite = null
		if _ik:
			_ik.active = false
		return
	if _ik == null:
		_ik_anlegen()
	if _zweite == null or _zweite.get_parent() != waffe:
		if _zweite:
			_zweite.queue_free()
		_zweite = Node3D.new()
		_zweite.name = "ZweiteHand"
		waffe.add_child(_zweite)
	_zweite.position = punkt
	_ik.active = true


func _ik_anlegen() -> void:
	var sk := mensch.skelett
	_ik_ziel = Node3D.new()
	_ik_ziel.name = "LinkeHandZiel"
	sk.add_child(_ik_ziel)
	var pol := Node3D.new()
	pol.name = "LinkerEllbogenPol"
	pol.position = Vector3(0.9, 0.6, -0.6) # links, Hüfthöhe, hinter dem Körper: Ellbogen zeigt nach unten außen
	sk.add_child(pol)
	# Vor der IK: liest die Pose der Animation, setzt Ziel und Stärke (Modifikatoren laufen in Reihenfolge der Kinder)
	var helfer := ZweiteHand.new()
	helfer.name = "ZweiteHandHelfer"
	helfer.figur = self
	sk.add_child(helfer)
	_ik = TwoBoneIK3D.new()
	_ik.name = "LinkeHandIK"
	sk.add_child(_ik)
	_ik.setting_count = 1
	_ik.set_root_bone_name(0, "LeftUpperArm")
	_ik.set_middle_bone_name(0, "LeftLowerArm")
	_ik.set_end_bone_name(0, "LeftHand")
	_ik.set_target_node(0, _ik.get_path_to(_ik_ziel))
	_ik.set_pole_node(0, _ik.get_path_to(pol))
	_zweite_versatz = griff_transform(sk, true).origin


## Setzt das Ziel der linken Hand auf den Griffpunkt an der Waffe. Greift nur, wenn die Animation die linke Hand
## ohnehin in die Nähe bringt (Zweihandschläge, Zielen); lässt sie die Waffe los, bleibt die Animation.
class ZweiteHand extends SkeletonModifier3D:
	var figur
	const VOLL := 0.25    # m Abstand: IK ganz
	const AUS := 0.45     # m Abstand: IK aus

	func _process_modification() -> void:
		var f = figur
		var sk := get_skeleton()
		if f._ik == null or f._zweite == null or not f._ik.active:
			return
		if not f._zweite.is_visible_in_tree():
			f._ik.influence = 0.0
			return
		# Griffpunkt aus der aktuellen Pose der rechten Hand (der Halter der Waffe hinkt sonst ein Bild hinterher)
		var waffe: Node3D = f._zweite.get_parent()
		var griff: Node3D = waffe.get_parent()
		var rechts := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("RightHand"))
		var punkt: Vector3 = rechts * griff.transform * waffe.transform * f._zweite.position
		var links := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("LeftHand"))
		var flaeche: Vector3 = links * f._zweite_versatz
		var d := flaeche.distance_to(punkt)
		f._ik.influence = clampf((AUS - d) / (AUS - VOLL), 0.0, 1.0)
		f._ik_ziel.global_position = punkt - links.basis.orthonormalized() * f._zweite_versatz
