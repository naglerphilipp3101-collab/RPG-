extends Control
## Minimap (oben rechts) und große Karte (M) auf Basis der Übersichtskarte des Weltgenerators.
## Zeigt Spieler mit Blickrichtung, Städte, Dörfer, Dungeons, POIs und Minen.
## Im Debug-Flug: Klick auf die große Karte springt dorthin.

const SIZE := 230.0
const ZOOMS := [2.0, 4.0, 8.0, 16.0] # Meter pro Bildschirmpixel
const MARKER_STYLE := {
	"stadt": [Color(0.95, 0.72, 0.28), 6.0], "dorf": [Color(0.92, 0.86, 0.58), 4.0],
	"dungeon": [Color(0.85, 0.3, 0.28), 5.0], "poi": [Color(0.45, 0.75, 0.95), 5.0], "mine": [Color(0.65, 0.68, 0.72), 3.5],
}

var player = null
var main = null # für Geländehöhe beim Teleport
var texture: Texture2D
var world_size := 8192.0
var markers: Array[Dictionary] = [] # {pos: Vector2(x, z), typ, name}
var zoom_index := 1
var big := false
var font: Font


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	font = ThemeDB.fallback_font
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


## Karte einrichten. `texture` = Übersichtsbild der ganzen Welt (Norden oben), `size` = Seitenlänge in Metern.
func setup(p, main_node, tex: Texture2D, size: float, marker_nodes: Array) -> void:
	player = p
	main = main_node
	texture = tex
	world_size = size
	markers.clear()
	for m in marker_nodes:
		var typ: String = m.get_meta("typ", "")
		if MARKER_STYLE.has(typ):
			markers.append({"pos": Vector2(m.global_position.x, m.global_position.z), "typ": typ, "name": m.get_meta("name", "")})
	visible = texture != null


func set_big(on: bool) -> void:
	big = on
	mouse_filter = Control.MOUSE_FILTER_STOP if on else Control.MOUSE_FILTER_IGNORE
	queue_redraw()


func cycle_zoom() -> void:
	zoom_index = (zoom_index + 1) % ZOOMS.size()


func _process(_delta: float) -> void:
	if visible:
		queue_redraw()


# Welt (x/z in Metern) -> Pixel im Übersichtsbild
func _tex_px(world: Vector2) -> Vector2:
	return (world + Vector2.ONE * world_size / 2.0) / world_size * Vector2(texture.get_size())


func _draw() -> void:
	if texture == null or player == null:
		return
	if big:
		_draw_big()
	else:
		_draw_mini()


func _draw_mini() -> void:
	var view := get_viewport_rect().size
	var rect := Rect2(view.x - SIZE - 16.0, 34.0, SIZE, SIZE)
	var center := rect.get_center()
	var mpp: float = ZOOMS[zoom_index]
	var p := Vector2(player.global_position.x, player.global_position.z)
	# Ausschnitt aus dem Übersichtsbild um den Spieler
	var tex_per_m := float(texture.get_width()) / world_size
	var src_size := Vector2.ONE * SIZE * mpp * tex_per_m
	var src := Rect2(_tex_px(p) - src_size / 2.0, src_size)
	draw_rect(rect.grow(3.0), Color(0.75, 0.62, 0.35))
	draw_rect(rect, Color(0.1, 0.2, 0.32))
	draw_texture_rect_region(texture, rect, src)
	for m in markers:
		var d: Vector2 = (m["pos"] - p) / mpp
		if absf(d.x) > SIZE / 2.0 - 4.0 or absf(d.y) > SIZE / 2.0 - 4.0:
			continue
		var style: Array = MARKER_STYLE[m["typ"]]
		draw_circle(center + d, style[1], style[0])
		draw_arc(center + d, style[1], 0, TAU, 12, Color(0, 0, 0, 0.7), 1.0)
		if m["typ"] == "stadt" and mpp <= 4.0:
			_label(center + d + Vector2(8, 4), m["name"], 11, style[0])
	_draw_player(center, 9.0)
	# Himmelsrichtung, Zoom und Position
	_label(Vector2(center.x - 4, rect.position.y + 13), "N", 13, Color.WHITE)
	var h: float = player.global_position.y
	var info := "X %d   Z %d   Höhe %d m   ·   %d m/px (N)" % [roundi(p.x), roundi(p.y), roundi(h), roundi(mpp)]
	_label(Vector2(rect.position.x, rect.end.y + 16.0), info, 12, Color(0.92, 0.92, 0.92))
	if player.debug_fly:
		_label(Vector2(rect.position.x, rect.end.y + 33.0), "DEBUG-FLUG (F3)", 13, Color(1.0, 0.55, 0.3))


func _big_rect() -> Rect2:
	var view := get_viewport_rect().size
	var s := minf(view.x, view.y) * 0.9
	return Rect2((view - Vector2(s, s)) / 2.0, Vector2(s, s))


func _draw_big() -> void:
	var view := get_viewport_rect().size
	draw_rect(Rect2(Vector2.ZERO, view), Color(0, 0, 0, 0.6))
	var rect := _big_rect()
	draw_rect(rect.grow(3.0), Color(0.75, 0.62, 0.35))
	draw_texture_rect(texture, rect, false)
	var scale := rect.size.x / world_size
	var to_screen := func(world: Vector2) -> Vector2: return rect.position + (world + Vector2.ONE * world_size / 2.0) * scale
	for m in markers:
		var style: Array = MARKER_STYLE[m["typ"]]
		var pos: Vector2 = to_screen.call(m["pos"])
		draw_circle(pos, style[1], style[0])
		draw_arc(pos, style[1], 0, TAU, 12, Color(0, 0, 0, 0.7), 1.0)
		if m["typ"] != "mine":
			_label(pos + Vector2(8, 4), m["name"], 12 if m["typ"] == "stadt" else 10, style[0])
	_draw_player(to_screen.call(Vector2(player.global_position.x, player.global_position.z)), 11.0)
	var hint := "M: Karte schließen"
	if player.debug_fly:
		hint += "   ·   Klick: dorthin springen"
	else:
		hint += "   ·   im Debug-Flug (F3) kannst du per Klick springen"
	_label(Vector2(rect.position.x, rect.end.y + 22.0), hint, 14, Color(1.0, 0.9, 0.65))


func _draw_player(pos: Vector2, size: float) -> void:
	# Spitze zeigt in Blickrichtung (Norden = oben, Welt −Z)
	var r: float = player.model.rotation.y
	var fwd := Vector2(-sin(r), -cos(r))
	var side := Vector2(-fwd.y, fwd.x)
	var pts := PackedVector2Array([pos + fwd * size, pos - fwd * size * 0.6 + side * size * 0.6, pos - fwd * size * 0.3, pos - fwd * size * 0.6 - side * size * 0.6])
	draw_colored_polygon(pts, Color(1, 1, 1))
	pts.append(pts[0])
	draw_polyline(pts, Color(0, 0, 0), 1.5)


func _label(pos: Vector2, text: String, size: int, color: Color) -> void:
	draw_string_outline(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, 4, Color(0, 0, 0, 0.85))
	draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)


func _gui_input(event: InputEvent) -> void:
	if not big or player == null or not player.debug_fly:
		return
	var mb := event as InputEventMouseButton
	if mb == null or not mb.pressed or mb.button_index != MOUSE_BUTTON_LEFT:
		return
	var rect := _big_rect()
	if not rect.has_point(mb.position):
		return
	var world := (mb.position - rect.position) / rect.size.x * world_size - Vector2.ONE * world_size / 2.0
	var ground := 0.0
	if main and main.terrain:
		var h: float = main.terrain.get("data").get_height(Vector3(world.x, 0, world.y))
		ground = 0.0 if is_nan(h) else maxf(h, 0.0)
	player.teleport(Vector3(world.x, ground + 40.0, world.y))
	player.message.emit("Gesprungen nach X %d  Z %d" % [roundi(world.x), roundi(world.y)])
