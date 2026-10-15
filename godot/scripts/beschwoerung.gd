extends Node3D
## Beschwörung der Leerenmagie.
## "wesen": schwebt zum nächsten Gegner (bis 14 m um den Spieler) und schlägt jede Sekunde zu.
## "klinge": kreist um den Spieler und trifft Gegner, die sie berührt; mit Klingenbinder schlägt sie bei jedem
## Treffer des Spielers mit zu (strike).

const MeshUtil := preload("res://scripts/mesh_util.gd")
const FX := preload("res://scripts/fx.gd")
const BEING_SPEED := 7.0
const BEING_RANGE := 14.0
const ORBIT_RADIUS := 1.7

var shooter = null
var kind := "wesen"
var time_left := 15.0
var mult := 0.5
var big := false
var index := 0
var count := 1
var source := "" # Waffenart, der der Schaden zählt
var color := Color(0.65, 0.3, 0.95)
var _attack_timer := 0.6
var _age := 0.0
var _visual: Node3D


func _ready() -> void:
	_visual = Node3D.new()
	add_child(_visual)
	var glow := MeshUtil.mat(color)
	glow.emission_enabled = true
	glow.emission = color
	glow.emission_energy_multiplier = 2.0
	if kind == "klinge":
		MeshUtil.part(_visual, MeshUtil.box(Vector3(0.05, 0.02, 0.7)), glow)
		return
	var body := MeshUtil.mat(Color(0.12, 0.05, 0.2))
	var size := 1.5 if big else 1.0
	var sphere := SphereMesh.new()
	sphere.radius = 0.35 * size
	sphere.height = 0.7 * size
	MeshUtil.part(_visual, sphere, body)
	for x in [-1.0, 1.0]:
		MeshUtil.part(_visual, MeshUtil.box(Vector3(0.08, 0.05, 0.05) * size), glow, Vector3(x * 0.12, 0.08, -0.3) * size)
	scale = Vector3.ONE
	_visual.scale = Vector3.ONE * 0.1
	create_tween().tween_property(_visual, "scale", Vector3.ONE, 0.3)


func _physics_process(delta: float) -> void:
	_age += delta
	time_left -= delta
	if time_left <= 0.0 or shooter == null or not is_instance_valid(shooter) or not shooter.is_alive():
		set_physics_process(false)
		var tw := create_tween()
		tw.tween_property(_visual, "scale", Vector3.ONE * 0.05, 0.25)
		tw.tween_callback(queue_free)
		return
	_attack_timer -= delta
	if kind == "klinge":
		_orbit()
	else:
		_hunt(delta)


func _orbit() -> void:
	var angle := _age * 2.6 + index * TAU / maxi(count, 1)
	global_position = shooter.global_position + Vector3(cos(angle) * ORBIT_RADIUS, 1.1, sin(angle) * ORBIT_RADIUS)
	rotation.y = -angle
	if _attack_timer > 0.0:
		return
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy.is_alive() and enemy.get_center().distance_to(global_position) <= float(enemy.radius) + 0.7:
			_attack_timer = 0.6
			shooter.summon_hit(enemy, mult, global_position, source)
			return


func _hunt(delta: float) -> void:
	var target = null
	var best := BEING_RANGE
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive():
			continue
		var d: float = enemy.global_position.distance_to(shooter.global_position)
		if d <= best:
			best = d
			target = enemy
	var goal: Vector3
	if target == null: # neben dem Spieler schweben
		goal = shooter.global_position + Vector3(cos(index * 2.1) * 1.8, 1.6, sin(index * 2.1) * 1.8)
	else:
		var to: Vector3 = target.get_center() - global_position
		goal = target.get_center() - to.normalized() * (float(target.radius) + 0.6)
		if Vector2(to.x, to.z).length() > 0.1:
			look_at(target.get_center(), Vector3.UP)
	global_position = global_position.move_toward(goal, BEING_SPEED * delta)
	_visual.position.y = sin(_age * 3.0) * 0.08
	if target != null and _attack_timer <= 0.0 and global_position.distance_to(target.get_center()) <= float(target.radius) + 1.2:
		_attack_timer = 1.0
		shooter.summon_hit(target, mult, global_position, source)
		var tw := create_tween()
		tw.tween_property(_visual, "position:z", -0.4, 0.08)
		tw.tween_property(_visual, "position:z", 0.0, 0.15)


## Klingenbinder: die Klinge schlägt sofort mit zu.
func strike(enemy) -> void:
	FX.beam(get_tree(), global_position, enemy.get_center(), color, 0.12)
	shooter.summon_hit(enemy, float(shooter._pp("mult", 0.2)), global_position, source)
