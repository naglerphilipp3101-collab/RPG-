extends RefCounted
## Kurzlebige visuelle Effekte: schwebende Zahlen/Hinweise und Schockwellen.


static func popup(tree: SceneTree, pos: Vector3, text: String, color: Color, size := 60) -> void:
	var label := Label3D.new()
	label.text = text
	label.modulate = color
	label.outline_modulate = Color(0, 0, 0, 0.85)
	label.font_size = size
	label.outline_size = 14
	label.pixel_size = 0.004
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	label.render_priority = 10
	tree.current_scene.add_child(label)
	label.global_position = pos + Vector3(randf_range(-0.3, 0.3), 0.0, randf_range(-0.3, 0.3))
	var tw := label.create_tween().set_parallel(true)
	tw.tween_property(label, "global_position", label.global_position + Vector3(0, 1.0, 0), 0.9) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_property(label, "modulate:a", 0.0, 0.6).set_delay(0.4)
	tw.tween_property(label, "outline_modulate:a", 0.0, 0.6).set_delay(0.4)
	tw.chain().tween_callback(label.queue_free)


## Leuchtende Linie (Blitz, Strahl), verschwindet nach `life` Sekunden.
static func beam(tree: SceneTree, from: Vector3, to: Vector3, color: Color, life := 0.15) -> void:
	var length := from.distance_to(to)
	if length < 0.05:
		return
	var mesh := BoxMesh.new()
	mesh.size = Vector3(0.07, 0.07, length)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(color.r, color.g, color.b, 0.9)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = m
	tree.current_scene.add_child(mi)
	mi.global_position = (from + to) * 0.5
	mi.look_at(to, Vector3.UP if absf((to - from).normalized().y) < 0.99 else Vector3.FORWARD)
	var tw := mi.create_tween()
	tw.tween_property(m, "albedo_color:a", 0.0, life)
	tw.tween_callback(mi.queue_free)


static func shockwave(tree: SceneTree, pos: Vector3, radius: float, color: Color) -> void:
	var ring := CylinderMesh.new()
	ring.top_radius = 1.0
	ring.bottom_radius = 1.0
	ring.height = 0.04
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = color
	var mi := MeshInstance3D.new()
	mi.mesh = ring
	mi.material_override = m
	mi.scale = Vector3(0.2, 1.0, 0.2)
	tree.current_scene.add_child(mi)
	mi.global_position = pos + Vector3(0, 0.05, 0)
	var tw := mi.create_tween().set_parallel(true)
	tw.tween_property(mi, "scale", Vector3(radius, 1.0, radius), 0.25).set_ease(Tween.EASE_OUT)
	tw.tween_property(m, "albedo_color:a", 0.0, 0.45)
	tw.chain().tween_callback(mi.queue_free)
