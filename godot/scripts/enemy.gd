extends CharacterBody3D
## Gegner mit Zustandsmaschine: Umherstreifen, Verfolgen, angekündigter Angriff, Taumeln, Rückkehr.
## Werte kommen aus data/enemies.json.

const FX := preload("res://scripts/fx.gd")
const MeshUtil := preload("res://scripts/mesh_util.gd")
const LootBagScript := preload("res://scripts/loot_bag.gd")

const GRAVITY := 18.0
const LEASH_DISTANCE := 35.0
const ALERT_RADIUS := 12.0
const WANDER_RADIUS := 6.0
const BAR_VISIBLE_DISTANCE := 35.0
const WEAPON_REST := Vector3(30, 0, 0)

enum State { IDLE, CHASE, WINDUP, STRIKE, RECOVER, STAGGER, RETURN, DEAD }

var type_id := ""
var data: Dictionary = {}
var home := Vector3.ZERO
var radius := 0.5
var max_health := 100.0
var health := 100.0
var speed := 4.0
var base_scale := 1.0

var state: State = State.IDLE
var state_timer := 0.0
var wander_target := Vector3.ZERO
var wander_timer := 0.0
var attack_cooldown := 0.0
var strike_done := false
var move_velocity := Vector3.ZERO
var knockback_velocity := Vector3.ZERO
var player = null
var dt := 0.0
var shown_ratio := -1.0
var life_id := 0 # zählt Tode, damit alte Timer nach dem Wiedererscheinen ignoriert werden
var corpse_present := false
var interact_radius := 2.0
var bleed_dps := 0.0
var bleed_time := 0.0
var bleed_tick := 0.0
var slow_pct := 0.0 # Verlangsamung durch Fähigkeiten
var slow_time := 0.0
var expose_pct := 0.0 # erhöhter erlittener Schaden
var expose_time := 0.0

var model: Node3D
var weapon_pivot: Node3D
var body_material: StandardMaterial3D
var collision: CollisionShape3D
var bar_root: Node3D
var bar_fill: QuadMesh
var anim_tween: Tween


func setup(id: String, home_position: Vector3) -> void:
	type_id = id
	data = Game.enemies.get(id, {})
	home = home_position


func _ready() -> void:
	add_to_group("enemies")
	add_to_group("interactable")
	collision_layer = 4
	collision_mask = 1 | 2 | 4
	base_scale = float(data.get("scale", 1.0))
	radius = float(data.get("radius", 0.5)) * base_scale
	max_health = float(data.get("health", 100.0))
	health = max_health
	speed = float(data.get("speed", 4.0))
	interact_radius = radius + 1.8

	collision = CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = radius
	capsule.height = maxf(float(data.get("height", 1.8)) * base_scale, radius * 2.0)
	collision.shape = capsule
	collision.position.y = capsule.height / 2.0
	add_child(collision)

	_build_model()
	_build_health_bar()
	wander_target = home
	wander_timer = randf_range(1.0, 4.0)
	model.rotation.y = randf() * TAU


func is_alive() -> bool:
	return state != State.DEAD


# --- Häuten (Schnittstelle wie bei Rohstoffquellen) -----------------------

func is_interactable() -> bool:
	return state == State.DEAD and corpse_present and bool(data.get("skinnable", false))


func is_fishing() -> bool:
	return false


func get_prompt() -> String:
	return "%s häuten" % data.get("name", type_id)


func get_profession() -> String:
	return "skinning"


func get_required_level() -> int:
	return int(data.get("skin_level", 1))


func get_gather_hp() -> float:
	return float(data.get("skin_hp", 20.0))


func harvest(p) -> void:
	var level: int = p.get_profession_level("skinning")
	p.receive_items(Game.roll_drops(data.get("skin_drops", []), level))
	p.add_profession_xp("skinning", int(data.get("skin_xp", 15)))
	_remove_corpse(life_id)


func alert() -> void:
	if state == State.IDLE:
		_set_state(State.CHASE)


# --- Aufbau -------------------------------------------------------------

func _build_model() -> void:
	model = Node3D.new()
	model.scale = Vector3.ONE * base_scale
	add_child(model)
	var c: Array = data.get("color", [0.5, 0.5, 0.5])
	var base := Color(float(c[0]), float(c[1]), float(c[2]))
	body_material = MeshUtil.mat(base)
	body_material.emission_enabled = true
	body_material.emission = Color(1.0, 0.35, 0.05)
	body_material.emission_energy_multiplier = 0.0
	var dark := MeshUtil.mat(base.darkened(0.45))
	var eyes := MeshUtil.mat(Color(1.0, 0.85, 0.2))
	eyes.emission_enabled = true
	eyes.emission = Color(1.0, 0.7, 0.1)

	if data.get("shape", "humanoid") == "beast":
		MeshUtil.part(model, MeshUtil.box(Vector3(0.5, 0.48, 1.1)), body_material, Vector3(0, 0.62, 0))
		MeshUtil.part(model, MeshUtil.box(Vector3(0.36, 0.34, 0.42)), body_material, Vector3(0, 0.85, -0.68))
		MeshUtil.part(model, MeshUtil.box(Vector3(0.2, 0.16, 0.26)), dark, Vector3(0, 0.78, -0.98))
		for x: float in [-0.11, 0.11]:
			MeshUtil.part(model, MeshUtil.box(Vector3(0.08, 0.14, 0.06)), dark, Vector3(x, 1.08, -0.6))
			MeshUtil.part(model, MeshUtil.box(Vector3(0.06, 0.05, 0.02)), eyes, Vector3(x, 0.9, -0.9))
		for x: float in [-0.17, 0.17]:
			for z: float in [-0.38, 0.38]:
				MeshUtil.part(model, MeshUtil.box(Vector3(0.13, 0.42, 0.13)), dark, Vector3(x, 0.21, z))
		var tail := MeshUtil.part(model, MeshUtil.box(Vector3(0.1, 0.1, 0.5)), dark, Vector3(0, 0.78, 0.75))
		tail.rotation_degrees.x = 25.0
		return

	var torso := CapsuleMesh.new()
	torso.radius = 0.3
	torso.height = 1.25
	MeshUtil.part(model, torso, body_material, Vector3(0, 0.85, 0))
	var head := SphereMesh.new()
	head.radius = 0.2
	head.height = 0.4
	MeshUtil.part(model, head, body_material, Vector3(0, 1.66, 0))
	for x: float in [-0.07, 0.07]:
		MeshUtil.part(model, MeshUtil.box(Vector3(0.05, 0.04, 0.02)), eyes, Vector3(x, 1.7, -0.19))

	weapon_pivot = Node3D.new()
	weapon_pivot.position = Vector3(0.38, 1.0, -0.1)
	weapon_pivot.rotation_degrees = WEAPON_REST
	model.add_child(weapon_pivot)
	var wood := MeshUtil.mat(Color(0.4, 0.27, 0.14))
	var metal := MeshUtil.mat(Color(0.6, 0.62, 0.65), 0.7, 0.4)
	if data.get("weapon", "axe") == "club":
		var club := CylinderMesh.new()
		club.top_radius = 0.16
		club.bottom_radius = 0.07
		club.height = 1.0
		var mi := MeshUtil.part(weapon_pivot, club, wood, Vector3(0, 0, -0.5))
		mi.rotation_degrees.x = -90.0
	else:
		MeshUtil.part(weapon_pivot, MeshUtil.box(Vector3(0.05, 0.05, 0.85)), wood, Vector3(0, 0, -0.38))
		MeshUtil.part(weapon_pivot, MeshUtil.box(Vector3(0.04, 0.28, 0.2)), metal, Vector3(0, 0.08, -0.72))


func _bar_height() -> float:
	return float(data.get("height", 1.8)) * base_scale + 0.45


func _build_health_bar() -> void:
	bar_root = Node3D.new()
	bar_root.position.y = _bar_height()
	add_child(bar_root)
	var bg_mesh := QuadMesh.new()
	bg_mesh.size = Vector2(1.0, 0.11)
	MeshUtil.part(bar_root, bg_mesh, _bar_material(Color(0, 0, 0, 0.65), 0))
	bar_fill = QuadMesh.new()
	bar_fill.size = Vector2(0.96, 0.07)
	MeshUtil.part(bar_root, bar_fill, _bar_material(Color(0.85, 0.18, 0.12), 1))
	var label := Label3D.new()
	label.text = "%s  Stufe %d" % [data.get("name", type_id), int(data.get("level", 1))]
	label.position.y = 0.2
	label.font_size = 36
	label.outline_size = 10
	label.pixel_size = 0.004
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	bar_root.add_child(label)
	bar_root.visible = false


func _bar_material(color: Color, priority: int) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.billboard_keep_scale = true
	m.no_depth_test = true
	m.render_priority = priority
	return m


func _update_bar() -> void:
	var ratio := clampf(health / max_health, 0.0, 1.0)
	if not is_equal_approx(ratio, shown_ratio):
		shown_ratio = ratio
		bar_fill.size = Vector2(0.96 * ratio, 0.07)
		bar_fill.center_offset = Vector3(-0.48 * (1.0 - ratio), 0.0, 0.0)
	var near := _player_valid() and global_position.distance_to(player.global_position) < BAR_VISIBLE_DISTANCE
	bar_root.visible = near and (state != State.IDLE or health < max_health)


# --- Hauptschleife ------------------------------------------------------

func _physics_process(delta: float) -> void:
	dt = delta
	if state == State.DEAD:
		return
	if player == null:
		player = get_tree().get_first_node_in_group("player")
	_update_bleed(delta)
	if state == State.DEAD:
		return
	attack_cooldown -= delta
	state_timer -= delta

	var desired := Vector3.ZERO
	match state:
		State.IDLE:
			desired = _do_idle()
		State.CHASE:
			desired = _do_chase()
		State.WINDUP:
			_do_windup()
		State.STRIKE:
			desired = _do_strike()
		State.RECOVER, State.STAGGER:
			if state_timer <= 0.0:
				_set_state(State.CHASE)
		State.RETURN:
			desired = _do_return()

	if state != State.STRIKE:
		desired += _separation()
	move_velocity = move_velocity.lerp(desired, clampf(10.0 * delta, 0.0, 1.0))
	knockback_velocity = knockback_velocity.move_toward(Vector3.ZERO, 25.0 * delta)
	velocity.x = move_velocity.x + knockback_velocity.x
	velocity.z = move_velocity.z + knockback_velocity.z
	if is_on_floor():
		velocity.y = -0.1
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	_update_bar()


func _player_valid() -> bool:
	return player != null and is_instance_valid(player) and player.is_alive()


func _flat_to_player() -> Vector3:
	var to: Vector3 = player.global_position - global_position
	to.y = 0.0
	return to


func _face(dir: Vector3, rate: float) -> void:
	if dir.length() < 0.01:
		return
	model.rotation.y = lerp_angle(model.rotation.y, atan2(-dir.x, -dir.z), clampf(rate * dt, 0.0, 1.0))


func _forward() -> Vector3:
	var f := -model.global_transform.basis.z
	f.y = 0.0
	return f.normalized()


func _set_state(new_state: State, timer := 0.0) -> void:
	var was_attacking := state == State.WINDUP or state == State.STRIKE
	var continues := new_state == State.STRIKE or new_state == State.RECOVER
	state = new_state
	state_timer = timer
	if was_attacking and not continues and new_state != State.DEAD:
		_return_to_rest(0.15)


func _do_idle() -> Vector3:
	if _player_valid() and _flat_to_player().length() < float(data.get("aggro_range", 12.0)):
		_aggro()
		return Vector3.ZERO
	wander_timer -= dt
	if wander_timer <= 0.0:
		var angle := randf() * TAU
		wander_target = home + Vector3(cos(angle), 0.0, sin(angle)) * randf_range(1.0, WANDER_RADIUS)
		wander_timer = randf_range(3.0, 7.0)
	var to := wander_target - global_position
	to.y = 0.0
	if to.length() < 0.6:
		return Vector3.ZERO
	_face(to, 4.0)
	return to.normalized() * speed * 0.3


func _aggro() -> void:
	_set_state(State.CHASE)
	# Andere Gegner in der Nähe werden mit alarmiert
	for node in get_tree().get_nodes_in_group("enemies"):
		var other = node
		if other != self and other.global_position.distance_to(global_position) < ALERT_RADIUS:
			other.alert()


func _do_chase() -> Vector3:
	if not _player_valid() or global_position.distance_to(home) > LEASH_DISTANCE:
		_set_state(State.RETURN)
		return Vector3.ZERO
	var to := _flat_to_player()
	var dist := to.length()
	_face(to, float(data.get("turn_rate", 6.0)))
	var reach: float = data.get("attack_range", 1.8)
	if dist <= reach and attack_cooldown <= 0.0:
		_start_windup()
		return Vector3.ZERO
	if dist <= reach * 0.75:
		# Zu nah und Angriff noch nicht bereit: seitlich umkreisen
		return to.normalized().cross(Vector3.UP) * _speed() * 0.35
	return to.normalized() * _speed()


func _start_windup() -> void:
	var t: float = data.get("windup", 0.5)
	_set_state(State.WINDUP, t)
	strike_done = false
	_kill_anim()
	# Rotes Leuchten = nicht blockbar (nur ausweichen hilft), orange = blockbar
	if data.get("unblockable", false):
		body_material.emission = Color(1.0, 0.05, 0.05)
	else:
		body_material.emission = Color(1.0, 0.35, 0.05)
	anim_tween = create_tween().set_parallel(true)
	anim_tween.tween_property(body_material, "emission_energy_multiplier", 3.0, t)
	if weapon_pivot:
		anim_tween.tween_property(weapon_pivot, "rotation_degrees", Vector3(120, 0, 0), t).set_trans(Tween.TRANS_BACK)
	anim_tween.tween_property(model, "rotation_degrees:x", 15.0, t)


func _do_windup() -> void:
	if _player_valid():
		_face(_flat_to_player(), float(data.get("turn_rate", 6.0)) * 0.5)
	if state_timer <= 0.0:
		_start_strike()


func _start_strike() -> void:
	var t: float = data.get("strike_time", 0.25)
	_set_state(State.STRIKE, t)
	move_velocity = _forward() * float(data.get("lunge_speed", 0.0))
	_kill_anim()
	anim_tween = create_tween().set_parallel(true)
	anim_tween.tween_property(body_material, "emission_energy_multiplier", 0.0, t)
	if weapon_pivot:
		anim_tween.tween_property(weapon_pivot, "rotation_degrees", Vector3(-50, 0, 0), t * 0.5)
	anim_tween.tween_property(model, "rotation_degrees:x", -12.0, t * 0.5)


func _do_strike() -> Vector3:
	var total: float = data.get("strike_time", 0.25)
	if not strike_done and state_timer <= total * 0.5:
		strike_done = true
		_resolve_strike()
	if state_timer <= 0.0:
		_set_state(State.RECOVER, float(data.get("recover", 0.6)))
		attack_cooldown = float(data.get("cooldown", 1.5))
		_return_to_rest(0.3)
		return Vector3.ZERO
	return _forward() * float(data.get("lunge_speed", 0.0)) * (state_timer / total)


func _resolve_strike() -> void:
	var reach: float = float(data.get("attack_range", 1.8)) + 0.6
	if data.get("slam", false):
		FX.shockwave(get_tree(), global_position + _forward() * reach * 0.5, reach, Color(0.6, 0.45, 0.3, 0.6))
	if not _player_valid():
		return
	var to := _flat_to_player()
	if to.length() > reach + radius:
		return
	var arc: float = data.get("attack_arc", 100.0)
	if to.length() > 0.3 and rad_to_deg(_forward().angle_to(to.normalized())) > arc * 0.5:
		return
	player.take_damage(float(data.get("damage", 10.0)), global_position, bool(data.get("unblockable", false)))


func _do_return() -> Vector3:
	var to := home - global_position
	to.y = 0.0
	health = minf(health + max_health * 0.25 * dt, max_health)
	if to.length() < 1.5:
		_set_state(State.IDLE)
		wander_timer = randf_range(1.0, 3.0)
		return Vector3.ZERO
	_face(to, 6.0)
	return to.normalized() * speed


func _separation() -> Vector3:
	var push := Vector3.ZERO
	for node in get_tree().get_nodes_in_group("enemies"):
		var other = node
		if other == self or not other.is_alive():
			continue
		var away: Vector3 = global_position - other.global_position
		away.y = 0.0
		var d := away.length()
		var min_d: float = radius + float(other.radius) + 0.3
		if d > 0.01 and d < min_d:
			push += away / d * (min_d - d) * 4.0
	return push


# --- Schaden & Tod ------------------------------------------------------

## Blutung: Schaden über Zeit, einmal pro Sekunde.
func _speed() -> float:
	return speed * (1.0 - slow_pct if slow_time > 0.0 else 1.0)


## Mittelpunkt des Körpers (für Geschosstreffer).
func get_center() -> Vector3:
	return global_position + Vector3(0, (_bar_height() - 0.45) * 0.5, 0)


## Schwächungen durch Fähigkeiten: "slow" (langsamer) oder "expose" (nimmt mehr Schaden).
func apply_debuff(kind: String, pct: float, duration: float) -> void:
	if state == State.DEAD:
		return
	var head := global_position + Vector3(0, _bar_height() + 0.4, 0)
	if kind == "slow":
		slow_pct = maxf(slow_pct if slow_time > 0.0 else 0.0, pct)
		slow_time = maxf(slow_time, duration)
		FX.popup(get_tree(), head, "Verlangsamt", Color(0.5, 0.75, 1.0), 40)
	elif kind == "expose":
		expose_pct = maxf(expose_pct if expose_time > 0.0 else 0.0, pct)
		expose_time = maxf(expose_time, duration)
		FX.popup(get_tree(), head, "Verwundbar", Color(1.0, 0.6, 0.2), 40)


func apply_bleed(dps: float, duration: float) -> void:
	if bleed_time <= 0.0:
		FX.popup(get_tree(), global_position + Vector3(0, _bar_height() + 0.4, 0), "Blutung", Color(0.85, 0.1, 0.15), 44)
	bleed_dps = maxf(bleed_dps, dps)
	bleed_time = maxf(bleed_time, duration)


func _update_bleed(delta: float) -> void:
	slow_time = maxf(slow_time - delta, 0.0)
	expose_time = maxf(expose_time - delta, 0.0)
	if bleed_time <= 0.0:
		return
	bleed_time -= delta
	bleed_tick -= delta
	if bleed_tick > 0.0:
		return
	bleed_tick = 1.0
	health -= bleed_dps
	FX.popup(get_tree(), global_position + Vector3(0, _bar_height(), 0), str(roundi(bleed_dps)), Color(0.85, 0.15, 0.2), 48)
	if health <= 0.0:
		_die()


func take_damage(amount: float, from_pos: Vector3, knockback: float, stagger: float, crit := false) -> void:
	if state == State.DEAD:
		return
	if expose_time > 0.0:
		amount *= 1.0 + expose_pct
	health -= amount
	var heavy := stagger >= 0.6
	var text := str(roundi(amount)) + ("!" if crit else "")
	var color := Color(1.0, 0.55, 0.15) if crit else (Color(1.0, 0.85, 0.25) if heavy else Color.WHITE)
	FX.popup(get_tree(), global_position + Vector3(0, _bar_height(), 0), text, color, 90 if crit else (80 if heavy else 60))
	if health <= 0.0:
		_die()
		return
	if state == State.IDLE or state == State.RETURN:
		_aggro()

	var away := global_position - from_pos
	away.y = 0.0
	away = away.normalized()
	var poise: float = data.get("poise", 0.0)
	var attacking := state == State.WINDUP or state == State.STRIKE
	# Leichte Treffer unterbrechen keinen laufenden Angriff, schwere schon
	if stagger > poise and (not attacking or heavy):
		knockback_velocity = away * knockback
		move_velocity = Vector3.ZERO
		_set_state(State.STAGGER, stagger)
		_kill_anim()
		body_material.emission_energy_multiplier = 0.0
		if weapon_pivot:
			weapon_pivot.rotation_degrees = WEAPON_REST
		anim_tween = create_tween()
		anim_tween.tween_property(model, "rotation_degrees:x", -20.0, 0.08)
		anim_tween.tween_property(model, "rotation_degrees:x", 0.0, stagger)
	else:
		knockback_velocity = away * knockback * 0.2
		var punch := create_tween()
		punch.tween_property(model, "scale", Vector3.ONE * base_scale * 1.08, 0.05)
		punch.tween_property(model, "scale", Vector3.ONE * base_scale, 0.1)


func _die() -> void:
	health = 0.0
	_set_state(State.DEAD)
	collision.set_deferred("disabled", true)
	bar_root.visible = false
	_kill_anim()
	body_material.emission_energy_multiplier = 0.0
	model.scale = Vector3.ONE * base_scale
	anim_tween = create_tween()
	anim_tween.tween_property(model, "rotation_degrees:z", 90.0, 0.5).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	_drop_loot()

	# Häutbare Leichen bleiben eine Weile liegen, andere verschwinden bald
	life_id += 1
	corpse_present = true
	var respawn_time := float(data.get("respawn", 30.0))
	var corpse_time := minf(40.0, respawn_time - 2.0) if data.get("skinnable", false) else 2.5
	get_tree().create_timer(corpse_time).timeout.connect(_remove_corpse.bind(life_id))
	get_tree().create_timer(respawn_time).timeout.connect(_respawn)


func _drop_loot() -> void:
	var drops := Game.roll_drops(data.get("loot", []))
	if drops.is_empty():
		return
	var bag = LootBagScript.new()
	bag.items = drops
	var spot := global_position + _forward() * (radius + 0.6)
	bag.position = Vector3(spot.x, 0.0, spot.z)
	get_tree().current_scene.add_child.call_deferred(bag)


func _remove_corpse(for_life: int) -> void:
	if for_life != life_id or not corpse_present:
		return
	corpse_present = false
	_kill_anim()
	anim_tween = create_tween()
	anim_tween.tween_property(model, "position:y", -1.0 * base_scale, 1.5)
	anim_tween.tween_callback(func() -> void: model.visible = false)


func _respawn() -> void:
	corpse_present = false
	bleed_time = 0.0
	slow_time = 0.0
	expose_time = 0.0
	var angle := randf() * TAU
	global_position = home + Vector3(cos(angle) * 2.0, 0.5, sin(angle) * 2.0)
	health = max_health
	move_velocity = Vector3.ZERO
	knockback_velocity = Vector3.ZERO
	attack_cooldown = 0.0
	_kill_anim()
	model.visible = true
	model.position = Vector3.ZERO
	model.rotation = Vector3(0, randf() * TAU, 0)
	if weapon_pivot:
		weapon_pivot.rotation_degrees = WEAPON_REST
	collision.set_deferred("disabled", false)
	_set_state(State.IDLE)


func _kill_anim() -> void:
	if anim_tween and anim_tween.is_valid():
		anim_tween.kill()


func _return_to_rest(t: float) -> void:
	_kill_anim()
	anim_tween = create_tween().set_parallel(true)
	anim_tween.tween_property(body_material, "emission_energy_multiplier", 0.0, t)
	if weapon_pivot:
		anim_tween.tween_property(weapon_pivot, "rotation_degrees", WEAPON_REST, t)
	anim_tween.tween_property(model, "rotation_degrees:x", 0.0, t)
