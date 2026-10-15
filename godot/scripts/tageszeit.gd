extends Node
## Tag/Nacht-Zyklus: bewegt die Sonne über den Himmel (Osten → Süden → Westen), färbt Himmel, Nebel
## und Umgebungslicht und lässt nachts einen schwachen Mond scheinen. Die Uhrzeit steht in Game.time_of_day
## (gespeichert im Spielstand), ein ganzer Tag dauert Game.DAY_LENGTH Sekunden.

const SUN_TILT := deg_to_rad(40.0) # Neigung der Sonnenbahn nach Süden; mittags 50° hoch
const SUN_ENERGY := 1.2
const MOON_ENERGY := 0.18

## Farben bei Tag, in der Dämmerung und nachts: Himmel oben, Horizont, Nebel
const DAY := [Color(0.3, 0.48, 0.78), Color(0.72, 0.8, 0.88), Color(0.7, 0.78, 0.86)]
const DUSK := [Color(0.25, 0.3, 0.55), Color(0.95, 0.6, 0.4), Color(0.75, 0.55, 0.45)]
const NIGHT := [Color(0.02, 0.03, 0.08), Color(0.08, 0.1, 0.18), Color(0.06, 0.08, 0.13)]

var sun: DirectionalLight3D
var env: Environment
var sky_mat: ProceduralSkyMaterial
var paused := false # Tests können die Zeit anhalten


func setup(sun_light: DirectionalLight3D, environment: Environment, sky_material: ProceduralSkyMaterial) -> void:
	sun = sun_light
	env = environment
	sky_mat = sky_material
	apply()


func _process(delta: float) -> void:
	if paused:
		return
	Game.time_of_day += delta * 24.0 / Game.DAY_LENGTH
	if Game.time_of_day >= 24.0:
		Game.time_of_day -= 24.0
		Game.day += 1
	apply()


## Richtung zur Sonne für eine Uhrzeit (Aufgang 6 Uhr im Osten, Untergang 18 Uhr im Westen).
static func sun_direction(hour: float) -> Vector3:
	var a := (hour - 6.0) / 12.0 * PI
	var up := Vector3(0, cos(SUN_TILT), sin(SUN_TILT)) # Süden = +z
	return (Vector3.RIGHT * cos(a) + up * sin(a)).normalized()


## Höhe der Sonne über dem Horizont als Sinus (−1 … 1).
static func sun_height(hour: float) -> float:
	return sun_direction(hour).y


func apply() -> void:
	if sun == null:
		return
	var dir := sun_direction(Game.time_of_day)
	var h := dir.y
	var day_amount := smoothstep(-0.08, 0.18, h) # 0 nachts, 1 am Tag
	var dusk_amount := clampf(1.0 - absf(h) / 0.25, 0.0, 1.0) * smoothstep(-0.2, 0.0, h)
	# Nachts scheint der Mond aus der Gegenrichtung
	var light_dir := dir if h > -0.05 else -dir
	if light_dir.y < 0.08:
		light_dir = (light_dir + Vector3(0, 0.08 - light_dir.y, 0)).normalized()
	sun.basis = Basis.looking_at(-light_dir, Vector3.UP)
	sun.light_energy = lerpf(MOON_ENERGY, SUN_ENERGY, day_amount)
	sun.light_color = Color(0.6, 0.7, 1.0).lerp(Color(1.0, 0.75, 0.55).lerp(Color.WHITE, 1.0 - dusk_amount), day_amount)
	var top: Color = NIGHT[0].lerp(DAY[0], day_amount).lerp(DUSK[0], dusk_amount * 0.6)
	var horizon: Color = NIGHT[1].lerp(DAY[1], day_amount).lerp(DUSK[1], dusk_amount)
	var fog: Color = NIGHT[2].lerp(DAY[2], day_amount).lerp(DUSK[2], dusk_amount * 0.7)
	sky_mat.sky_top_color = top
	sky_mat.sky_horizon_color = horizon
	sky_mat.ground_horizon_color = horizon.darkened(0.15)
	sky_mat.ground_bottom_color = Color(0.2, 0.24, 0.2).lerp(Color(0.02, 0.03, 0.04), 1.0 - day_amount)
	env.fog_light_color = fog
	env.ambient_light_energy = lerpf(0.35, 1.0, day_amount)
	env.background_energy_multiplier = lerpf(0.6, 1.0, day_amount)


## Für Tests und Anzeigen: Ist gerade Nacht?
static func is_night() -> bool:
	return sun_height(Game.time_of_day) < -0.05
