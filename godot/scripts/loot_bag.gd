extends Node3D
## Beutebeutel, den besiegte Gegner fallen lassen. Wird beim Darüberlaufen automatisch eingesammelt.

const MeshUtil := preload("res://scripts/mesh_util.gd")
const PICKUP_RADIUS := 1.6
const LIFETIME := 120.0

var items: Dictionary = {}
var life := LIFETIME
var full_cooldown := 0.0
var player = null
var bag: Node3D
var time := 0.0


func _ready() -> void:
	bag = Node3D.new()
	add_child(bag)
	var sack := SphereMesh.new()
	sack.radius = 0.22
	sack.height = 0.4
	var cloth := MeshUtil.mat(Color(0.55, 0.4, 0.22))
	MeshUtil.part(bag, sack, cloth)
	MeshUtil.part(bag, MeshUtil.box(Vector3(0.1, 0.12, 0.1)), cloth, Vector3(0, 0.22, 0))

	# Lichtsäule, damit man die Beute von weitem sieht
	var beam := CylinderMesh.new()
	beam.top_radius = 0.04
	beam.bottom_radius = 0.08
	beam.height = 2.5
	var beam_mat := StandardMaterial3D.new()
	beam_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	beam_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	beam_mat.albedo_color = Color(1.0, 0.85, 0.4, 0.35)
	MeshUtil.part(self, beam, beam_mat, Vector3(0, 1.25, 0))


func _process(delta: float) -> void:
	time += delta
	life -= delta
	full_cooldown -= delta
	bag.position.y = 0.3 + sin(time * 3.0) * 0.06
	bag.rotation.y += delta
	if life <= 0.0:
		queue_free()
		return
	if player == null:
		player = get_tree().get_first_node_in_group("player")
		return
	if full_cooldown > 0.0 or not player.is_alive():
		return
	if global_position.distance_to(player.global_position) < PICKUP_RADIUS:
		items = player.receive_items(items)
		if items.is_empty():
			queue_free()
		else:
			full_cooldown = 3.0 # Tasche voll: nicht jeden Frame erneut versuchen
