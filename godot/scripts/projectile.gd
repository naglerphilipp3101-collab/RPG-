extends Node3D
## Geschoss (Pfeil, Bolzen, Kugel, Wurfbeil). Prüft pro Physik-Schritt die Strecke auf Welt- und Gegnertreffer.

const WeaponModels := preload("res://scripts/weapon_models.gd")
const FX := preload("res://scripts/fx.gd")
const HIT_RADIUS := 0.3

var shooter = null # Spieler; berechnet den Schaden über on_projectile_hit
var velocity := Vector3.ZERO
var gravity := 0.0
var life := 3.0
var kind := "arrow"
var hit_data: Dictionary = {} # mult, kb, stag, effects, pierce, explode
var hit_list: Array = []
var visual: Node3D


func _ready() -> void:
	visual = Node3D.new()
	add_child(visual)
	WeaponModels.build_projectile(kind, visual)
	_orient()


func _physics_process(delta: float) -> void:
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	velocity.y -= gravity * delta
	var from := global_position
	var to := from + velocity * delta

	# Weltkollision (Boden, Bäume, Felsen)
	var query := PhysicsRayQueryParameters3D.create(from, to, 1)
	var world_hit := get_world_3d().direct_space_state.intersect_ray(query)
	var end: Vector3 = to if world_hit.is_empty() else world_hit["position"]

	# Gegner entlang der Flugstrecke
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if not enemy.is_alive() or hit_list.has(enemy):
			continue
		var center: Vector3 = enemy.get_center()
		var closest := Geometry3D.get_closest_point_to_segment(center, from, end)
		# Kopftreffer: die Flugbahn streift die Kopfkugel (zählt auch, wenn sie den Körper verfehlt)
		var head: Array = enemy.get_head()
		var head_point := Geometry3D.get_closest_point_to_segment(head[0], from, end)
		var headshot: bool = head_point.distance_to(head[0]) <= float(head[1]) + HIT_RADIUS * 0.5
		if headshot or closest.distance_to(center) <= float(enemy.radius) + HIT_RADIUS:
			hit_list.append(enemy)
			if float(hit_data.get("explode", 0.0)) > 0.0:
				_explode(closest)
				return
			var data := hit_data
			if headshot:
				data = hit_data.duplicate()
				data["headshot"] = true
				FX.popup(get_tree(), head[0] + Vector3(0, 0.5, 0), "Kopftreffer", Color(1.0, 0.4, 0.3), 40)
			shooter.on_projectile_hit(enemy, data, from)
			if not hit_data.get("pierce", false):
				queue_free()
				return

	if not world_hit.is_empty():
		if float(hit_data.get("explode", 0.0)) > 0.0:
			_explode(end)
		else:
			queue_free()
		return
	global_position = end
	_orient()
	if kind == "axe":
		visual.rotate_x(-delta * 18.0)


func _orient() -> void:
	if velocity.length() > 0.01 and kind != "axe":
		look_at(global_position + velocity, Vector3.UP if absf(velocity.normalized().y) < 0.99 else Vector3.FORWARD)


func _explode(pos: Vector3) -> void:
	var radius := float(hit_data["explode"])
	FX.shockwave(get_tree(), pos, radius, Color(1.0, 0.55, 0.2, 0.7))
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy = node
		if enemy.is_alive() and enemy.get_center().distance_to(pos) <= radius + float(enemy.radius):
			shooter.on_projectile_hit(enemy, hit_data, pos)
	queue_free()
