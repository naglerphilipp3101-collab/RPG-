extends Node3D
## Flächenangriff (z. B. Pfeilhagel): trifft in regelmäßigen Abständen alle Gegner im Radius.
## Mit `once` ist es eine Falle: sie wartet ticks × interval Sekunden und löst beim ersten Gegner einmal aus.
## Weitere Formen (Magie): `line` > 0 = Streifen dieser Länge entlang `direction`, `delay` = Einschlag erst nach
## dieser Zeit (Meteor), `heal` = heilt den Spieler je Treffer-Takt, solange er in der Fläche steht.

const MeshUtil := preload("res://scripts/mesh_util.gd")
const FX := preload("res://scripts/fx.gd")

var shooter = null
var radius := 4.0
var ticks := 5
var interval := 0.4
var hit_data: Dictionary = {}
var once := false
var delay := 0.0
var line := 0.0
var direction := Vector3.FORWARD
var heal := 0.0
var color := Color(1.0, 0.8, 0.35)
var timer := 0.2
var marker_mat: StandardMaterial3D


func _ready() -> void:
	if delay > 0.0:
		timer = delay
	marker_mat = StandardMaterial3D.new()
	marker_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	marker_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	marker_mat.albedo_color = Color(0.75, 0.2, 0.15, 0.35) if once else Color(color.r, color.g, color.b, 0.25)
	if line > 0.0:
		var strip := MeshUtil.part(self, MeshUtil.box(Vector3(radius * 2.0, 0.03, line)), marker_mat, Vector3(0, 0.05, 0))
		strip.basis = Basis.looking_at(direction, Vector3.UP)
		return
	var disc := CylinderMesh.new()
	disc.top_radius = radius
	disc.bottom_radius = radius
	disc.height = 0.03
	MeshUtil.part(self, disc, marker_mat, Vector3(0, 0.05, 0))
	if delay > 0.0: # Vorwarnung: der Rand pulsiert bis zum Einschlag
		var tw := create_tween().set_loops(int(delay / 0.3) + 1)
		tw.tween_property(marker_mat, "albedo_color:a", 0.55, 0.15)
		tw.tween_property(marker_mat, "albedo_color:a", 0.2, 0.15)


func _physics_process(delta: float) -> void:
	timer -= delta
	if timer > 0.0:
		return
	timer = interval
	ticks -= 1
	var inside: Array = []
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy.is_alive() and _contains(enemy.global_position, float(enemy.radius)):
			inside.append(enemy)
	if heal > 0.0 and shooter != null and is_instance_valid(shooter) and _contains(shooter.global_position, 0.4):
		shooter.heal(shooter.max_health * heal)
	if once:
		if not inside.is_empty():
			FX.shockwave(get_tree(), global_position, radius, Color(1.0, 0.45, 0.2, 0.7))
			ticks = 0
	elif delay > 0.0:
		FX.shockwave(get_tree(), global_position, radius, Color(color.r, color.g, color.b, 0.8))
	else:
		_spawn_streaks()
	if not once or ticks <= 0:
		for enemy in inside:
			shooter.on_projectile_hit(enemy, hit_data, global_position + (Vector3.ZERO if once else Vector3(0, 5, 0)))
	if ticks <= 0:
		var tw := create_tween()
		tw.tween_property(marker_mat, "albedo_color:a", 0.0, 0.4)
		tw.tween_callback(queue_free)
		set_physics_process(false)


func _contains(pos: Vector3, extra: float) -> bool:
	var to := pos - global_position
	to.y = 0.0
	if line > 0.0:
		var half := direction * line * 0.5
		var p := Geometry3D.get_closest_point_to_segment(to, -half, half)
		return to.distance_to(p) <= radius + extra
	return to.length() <= radius + extra


## Fallende Striche als Andeutung von Pfeilen/Bolzen (bei Magie in der Farbe des Elements).
func _spawn_streaks() -> void:
	var mat := MeshUtil.mat(Color(0.55, 0.4, 0.25)) if color == Color(1.0, 0.8, 0.35) else MeshUtil.mat(color)
	for i in 6:
		var offset := Vector3.ZERO
		if line > 0.0:
			offset = direction * randf_range(-0.5, 0.5) * line + direction.cross(Vector3.UP) * randf_range(-radius, radius)
		else:
			var angle := randf() * TAU
			var r := sqrt(randf()) * radius
			offset = Vector3(cos(angle) * r, 0.0, sin(angle) * r)
		var streak := MeshUtil.part(self, MeshUtil.box(Vector3(0.03, 0.7, 0.03)), mat, offset + Vector3(0, 6.0, 0))
		var tw := streak.create_tween()
		tw.tween_property(streak, "position:y", 0.3, 0.18)
		tw.tween_interval(0.3)
		tw.tween_callback(streak.queue_free)
