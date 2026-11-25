extends Camera3D
## Freie Kamera (Philipp, 25.11.): mit F4 umschalten, um Animationen von nah und aus jedem Winkel anzusehen.
## WASD fliegen, Leertaste/C hoch/runter, Umschalt schnell, Alt langsam, Mausrad zoomen (Blickwinkel),
## G Zeitlupe (1 → ½ → ¼ → ⅒), V Standbild. Die Spielfigur bleibt stehen, greift aber weiter an
## (Maustasten, Q/E/R, X), damit man ihre Schläge von außen betrachten kann.
## Läuft mit echter Zeit, also auch in Zeitlupe und im Standbild.

const TEMPO := 4.0               # m/s
const MAUS := 0.0025
const ZEITLUPE := [1.0, 0.5, 0.25, 0.1]

var gier := 0.0
var neigung := 0.0
var _letzte := 0
var zeitlupe := 0                # Index in ZEITLUPE
var standbild := false


func _ready() -> void:
	fov = 60.0
	near = 0.03
	current = false
	_letzte = Time.get_ticks_usec()


## Übernimmt Lage und Blick der Spielerkamera.
func starten(von: Camera3D) -> void:
	global_transform = von.global_transform
	var r := von.global_transform.basis.get_euler()
	gier = r.y
	neigung = r.x
	fov = von.fov
	zeitlupe = 0
	standbild = false
	_letzte = Time.get_ticks_usec()
	current = true


func beenden() -> void:
	current = false


## Zeitfaktor des Spiels (0 im Standbild).
func zeitfaktor() -> float:
	return 0.0 if standbild else float(ZEITLUPE[zeitlupe])


func drehen(relativ: Vector2) -> void:
	gier -= relativ.x * MAUS
	neigung = clampf(neigung - relativ.y * MAUS, -1.5, 1.5)


func zoomen(schritt: float) -> void:
	fov = clampf(fov * (0.9 if schritt > 0.0 else 1.0 / 0.9), 8.0, 90.0)


func _process(_delta: float) -> void:
	if not current:
		return
	# echte Zeit, unabhängig von Engine.time_scale
	var jetzt := Time.get_ticks_usec()
	var dt := minf((jetzt - _letzte) / 1000000.0, 0.1)
	_letzte = jetzt
	rotation = Vector3(neigung, gier, 0.0)
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	var eingabe := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var hoch := (1.0 if Input.is_action_pressed("jump") else 0.0) - (1.0 if Input.is_action_pressed("fly_down") else 0.0)
	var richtung := global_transform.basis * Vector3(eingabe.x, 0.0, eingabe.y) + Vector3.UP * hoch
	if richtung.length() > 1.0:
		richtung = richtung.normalized()
	var tempo := TEMPO
	if Input.is_key_pressed(KEY_SHIFT):
		tempo *= 4.0
	if Input.is_key_pressed(KEY_ALT):
		tempo *= 0.2
	global_position += richtung * tempo * dt
