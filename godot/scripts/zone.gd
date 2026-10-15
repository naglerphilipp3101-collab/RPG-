extends Node3D
## Flächenangriff (z. B. Pfeilhagel): trifft in regelmäßigen Abständen alle Gegner im Radius.
## Mit `once` ist es eine Falle: sie wartet ticks × interval Sekunden und löst beim ersten Gegner einmal aus.

const MeshUtil := preload("res://scripts/mesh_util.gd")
const FX := preload("res://scripts/fx.gd")

var shooter = null
var radius := 4.0
var ticks := 5
var interval := 0.4
var hit_data: Dictionary = {}
var once := false
var timer := 0.2
var marker_mat: StandardMaterial3D


func _ready() -> void:
	var disc := CylinderMesh.new()
	disc.top_radius = radius
	disc.bottom_radius = radius
	disc.height = 0.03
	marker_mat = StandardMaterial3D.new()
	marker_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	marker_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	marker_mat.albedo_color = Color(0.75, 0.2, 0.15, 0.35) if once else Color(1.0, 0.8, 0.35, 0.25)
	MeshUtil.part(self, disc, marker_mat, Vector3(0, 0.05, 0))


func _physics_process(delta: float) -> void:
	timer -= delta
	if timer > 0.0:
		return
	timer = interval
	ticks -= 1
	var inside: Array = []
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		var to: Vector3 = enemy.global_position - global_position
		to.y = 0.0
		if enemy.is_alive() and to.length() <= radius + float(enemy.radius):
			inside.append(enemy)
	if once:
		if not inside.is_empty():
			FX.shockwave(get_tree(), global_position, radius, Color(1.0, 0.45, 0.2, 0.7))
			ticks = 0
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


## Fallende Striche als Andeutung von Pfeilen/Bolzen.
func _spawn_streaks() -> void:
	var mat := MeshUtil.mat(Color(0.55, 0.4, 0.25))
	for i in 6:
		var angle := randf() * TAU
		var r := sqrt(randf()) * radius
		var streak := MeshUtil.part(self, MeshUtil.box(Vector3(0.03, 0.7, 0.03)), mat,
			Vector3(cos(angle) * r, 6.0, sin(angle) * r))
		var tw := streak.create_tween()
		tw.tween_property(streak, "position:y", 0.3, 0.18)
		tw.tween_interval(0.3)
		tw.tween_callback(streak.queue_free)
