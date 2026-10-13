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
var roads: Array[Dictionary] = [] # {pts: PackedVector2Array (x, z), strasse: bool}
const ROAD_COLOR := Color(0.93, 0.82, 0.6)
const PATH_COLOR := Color(0.85, 0.74, 0.55, 0.8)
var zoom_index := 1
var big := false
var font: Font
# Große Karte: 1 = ganze Insel, bis 32-fach; Mittelpunkt des Ausschnitts in Weltkoordinaten (x, z)
const BIG_ZOOM_MAX := 32.0
var big_zoom := 1.0
var big_center := Vector2.ZERO
var _drag_from := Vector2.ZERO
var _dragging := false
var _drag_moved := false


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
	# Straßen und Wege als Linienzüge (x/z), aus den Path3D-Knoten des Weltimports
	roads.clear()
	for pf in get_tree().get_nodes_in_group("welt_wege"):
		var pts := PackedVector2Array()
		var curve: Curve3D = pf.curve
		for i in curve.point_count:
			var q := curve.get_point_position(i)
			pts.append(Vector2(q.x, q.z))
		if pts.size() > 1:
			var box := Rect2(pts[0], Vector2.ZERO)
			for q in pts:
				box = box.expand(q)
			roads.append({"pts": pts, "box": box.grow(10.0), "strasse": pf.get_meta("typ", "") == "strasse"})
	visible = texture != null


func set_big(on: bool) -> void:
	big = on
	_dragging = false
	if on and player:
		# Zoom bleibt erhalten, der Ausschnitt springt zum Spieler
		big_center = Vector2(player.global_position.x, player.global_position.z)
		_clamp_center()
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
	_draw_roads(rect, func(w: Vector2) -> Vector2: return center + (w - p) / mpp, 1.0, Rect2(p - Vector2.ONE * SIZE * mpp / 2.0, Vector2.ONE * SIZE * mpp))
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


## Bildschirmpixel pro Weltmeter auf der großen Karte
func _big_scale() -> float:
	return _big_rect().size.x / world_size * big_zoom


func _big_to_screen(world: Vector2) -> Vector2:
	return _big_rect().get_center() + (world - big_center) * _big_scale()


func _big_to_world(screen: Vector2) -> Vector2:
	return big_center + (screen - _big_rect().get_center()) / _big_scale()


## Ausschnitt innerhalb der Insel halten
func _clamp_center() -> void:
	var limit := world_size / 2.0 - world_size / (2.0 * big_zoom)
	big_center = big_center.clamp(-Vector2.ONE * limit, Vector2.ONE * limit)


func _draw_big() -> void:
	var view := get_viewport_rect().size
	draw_rect(Rect2(Vector2.ZERO, view), Color(0, 0, 0, 0.6))
	var rect := _big_rect()
	draw_rect(rect.grow(3.0), Color(0.75, 0.62, 0.35))
	# sichtbarer Ausschnitt des Übersichtsbilds
	var half := Vector2.ONE * world_size / (2.0 * big_zoom)
	draw_texture_rect_region(texture, rect, Rect2(_tex_px(big_center - half), _tex_px(big_center + half) - _tex_px(big_center - half)))
	_draw_roads(rect, _big_to_screen, clampf(big_zoom / 4.0, 0.6, 1.6), Rect2(big_center - half, half * 2.0))
	for m in markers:
		var pos := _big_to_screen(m["pos"])
		if not rect.grow(-4.0).has_point(pos):
			continue
		var style: Array = MARKER_STYLE[m["typ"]]
		var r: float = style[1] * clampf(sqrt(big_zoom), 1.0, 2.0)
		draw_circle(pos, r, style[0])
		draw_arc(pos, r, 0, TAU, 12, Color(0, 0, 0, 0.7), 1.0)
		# Namen: Städte immer, Dörfer/Dungeons/POIs ab 2-fach, Minen ab 4-fach
		var zeigen: bool = m["typ"] == "stadt" or (m["typ"] != "mine" and big_zoom >= 2.0) or big_zoom >= 4.0
		if zeigen:
			_label(pos + Vector2(r + 4, 4), m["name"], 13 if m["typ"] == "stadt" else 11, style[0])
	var p := _big_to_screen(Vector2(player.global_position.x, player.global_position.z))
	if rect.has_point(p):
		_draw_player(p, 11.0)
	_draw_scale_bar(rect)
	var hint := "M: schließen  ·  Mausrad: zoomen  ·  Ziehen: verschieben"
	if player.debug_fly:
		hint += "  ·  Klick: dorthin springen"
	else:
		hint += "  ·  im Debug-Flug (F3): Klick = springen"
	_label(Vector2(rect.position.x, rect.end.y + 22.0), hint, 14, Color(1.0, 0.9, 0.65))
	_label(Vector2(rect.end.x - 60.0, rect.end.y + 22.0), "%s×" % String.num(big_zoom, 1), 14, Color(1.0, 0.9, 0.65))


## Straßen (breiter) und Wege; Abschnitte außerhalb des Kartenrechtecks werden ausgelassen
func _draw_roads(rect: Rect2, to_screen: Callable, width: float, view: Rect2) -> void:
	for r in roads:
		if not view.intersects(r["box"]):
			continue
		var pts: PackedVector2Array = r["pts"]
		var color := ROAD_COLOR if r["strasse"] else PATH_COLOR
		var w := (2.0 if r["strasse"] else 1.2) * width
		var prev: Vector2 = to_screen.call(pts[0])
		for i in range(1, pts.size()):
			var cur: Vector2 = to_screen.call(pts[i])
			if rect.has_point(prev) and rect.has_point(cur):
				draw_line(prev, cur, color, w, true)
			prev = cur


## Maßstabsbalken unten links (runde Länge, etwa 120 px)
func _draw_scale_bar(rect: Rect2) -> void:
	var meters := 120.0 / _big_scale()
	var step := pow(10.0, floorf(log(meters) / log(10.0)))
	for f in [5.0, 2.0, 1.0]:
		if f * step <= meters:
			step *= f
			break
	var length := step * _big_scale()
	var start := Vector2(rect.position.x + 14.0, rect.end.y - 16.0)
	draw_rect(Rect2(start - Vector2(6, 22), Vector2(length + 12, 30)), Color(0, 0, 0, 0.55))
	draw_rect(Rect2(start, Vector2(length, 3)), Color.WHITE)
	_label(start + Vector2(0, -6), "%d m" % int(step) if step < 1000.0 else "%s km" % String.num(step / 1000.0, 1), 12, Color.WHITE)


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
	if not big or player == null:
		return
	var motion := event as InputEventMouseMotion
	if motion and _dragging:
		if motion.position.distance_to(_drag_from) > 4.0:
			_drag_moved = true
		if _drag_moved:
			big_center -= motion.relative / _big_scale()
			_clamp_center()
		return
	var mb := event as InputEventMouseButton
	if mb == null:
		return
	if mb.pressed and mb.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		# Zoom um den Mauszeiger: der Punkt unter dem Zeiger bleibt stehen
		var unter := _big_to_world(mb.position)
		var faktor := 1.25 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else 0.8
		big_zoom = clampf(big_zoom * faktor, 1.0, BIG_ZOOM_MAX)
		big_center = unter - (mb.position - _big_rect().get_center()) / _big_scale()
		_clamp_center()
		return
	if mb.button_index not in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]:
		return
	if mb.pressed:
		_dragging = true
		_drag_moved = false
		_drag_from = mb.position
		return
	_dragging = false
	# Loslassen ohne Ziehen = Klick: im Debug-Flug dorthin springen
	if _drag_moved or mb.button_index != MOUSE_BUTTON_LEFT or not player.debug_fly:
		return
	var rect := _big_rect()
	if not rect.has_point(mb.position):
		return
	var world := _big_to_world(mb.position)
	var ground := 0.0
	if main and main.terrain:
		var h: float = main.terrain.get("data").get_height(Vector3(world.x, 0, world.y))
		ground = 0.0 if is_nan(h) else maxf(h, 0.0)
	player.teleport(Vector3(world.x, ground + 40.0, world.y))
	player.message.emit("Gesprungen nach X %d  Z %d" % [roundi(world.x), roundi(world.y)])
