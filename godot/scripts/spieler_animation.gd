class_name SpielerAnimation
extends Node
## Spielt die Animationen eines Menschen (Spieler, später auch NPCs und menschliche Gegner).
## Zwei Arten: Grundbewegung (Stehen, Gehen, Rennen, Springen, Blocken), die jedes Bild aus dem
## Zustand gewählt wird, und einmalige Bewegungen (Schlag, Rolle, Treffer, Tod), die die Grundbewegung
## für ihre Dauer überdecken. Die Animationen kommen aus MenschAnimationen (Quaternius, CC0).

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

var mensch: Mensch
var ap: AnimationPlayer
var _einmal := ""                # laufende einmalige Animation ("" = Grundbewegung)
var _einmal_rest := 0.0          # verbleibende Zeit der einmaligen Animation
var _danach := ""                # folgt auf die einmalige Animation (z. B. Erholung nach dem Schlag)
var _halten := false             # letzte Pose der einmaligen Animation halten (Tod)
var _in_luft := 0.0
var _landen := 0.0


func _init(m: Mensch) -> void:
	mensch = m
	name = "Animation"


func _ready() -> void:
	ap = MenschAnimationen.spieler_anhaengen(mensch)
	ap.playback_default_blend_time = UEBERGANG
	ap.play(_voll("Idle"))


static func _voll(n: String) -> String:
	return MenschAnimationen.BIBLIOTHEK + "/" + n


## Spielt eine Animation einmal. `dauer` > 0 streckt sie auf diese Länge, `halten` friert das Ende ein.
## `bis` (0–1) spielt nur bis zu diesem Anteil der Animation.
func einmal(n: String, dauer := -1.0, halten := false, danach := "", bis := 1.0) -> void:
	if not ap.has_animation(_voll(n)):
		return
	var laenge := ap.get_animation(_voll(n)).length * bis
	var tempo := 1.0 if dauer <= 0.0 else clampf(laenge / dauer, 0.4, 3.0)
	ap.speed_scale = 1.0
	var gleich := ap.assigned_animation == _voll(n)
	ap.play(_voll(n), UEBERGANG * 0.6, tempo)
	if gleich:
		ap.seek(0.0, true)
	_einmal = n
	_einmal_rest = laenge / tempo
	_halten = halten
	_danach = danach


## Schlag nach Schlagart: die Animation wird so schnell abgespielt, dass ihr Treffer auf `treffer` (s) fällt.
func schlag(art: String, treffer: float) -> void:
	var s: Array = SCHLAEGE.get(art, SCHLAEGE["h_right"])
	var laenge := ap.get_animation(_voll(s[0])).length if ap.has_animation(_voll(s[0])) else 0.5
	var bis_treffer := laenge * float(s[1])
	einmal(s[0], laenge * treffer / maxf(bis_treffer, 0.05), false, s[2])


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
func bewegen(delta: float, tempo: float, am_boden: bool, kampf: bool, block: bool, schild: bool, zielen: bool, fernkampf: String) -> void:
	if _einmal != "":
		_einmal_rest -= delta
		if _einmal_rest > 0.0:
			return
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
		_grund("Idle_Shield" if schild else "Sword_Block", 1.0, 0.0 if schild else 0.35)
		return
	if zielen:
		_grund("Spell_Simple_Idle" if fernkampf == "magic" else "Pistol_Aim_Neutral")
		return
	if tempo < 0.4:
		_grund(("Sword_Idle" if fernkampf == "" else "Pistol_Idle") if kampf else "Idle")
	elif tempo < (GEH_TEMPO + LAUF_TEMPO) * 0.5:
		_grund("Walk", clampf(tempo / GEH_TEMPO, 0.6, 2.2))
	elif tempo < (LAUF_TEMPO + SPRINT_TEMPO) * 0.5:
		_grund("Jog_Fwd", clampf(tempo / LAUF_TEMPO, 0.7, 1.6))
	else:
		_grund("Sprint", clampf(tempo / SPRINT_TEMPO, 0.7, 1.5))


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
	var bone := sk.find_bone(seite + "Hand")
	var halter := BoneAttachment3D.new()
	halter.name = seite + "Hand"
	halter.bone_idx = bone
	sk.add_child(halter)
	var griff := Node3D.new()
	griff.name = "Griff"
	griff.transform = griff_transform(sk, links)
	halter.add_child(griff)
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
