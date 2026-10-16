extends Control
## Kompass oben in der Mitte mit Himmelsrichtungen, aufgespürten Rohstoffen und der Uhrzeit.
## Aufspüren: Vorkommen erscheinen, sobald der Sammelberuf 25 Punkte über der Tier-Schwelle liegt
## (Tier 1 ab Skill 25, Tier 2 ab 75 …). Spiritual 450 verdoppelt die Reichweite für Fischgründe.

const WIDTH := 520.0
const HEIGHT := 28.0
const HALF_FOV := PI / 2.0 # sichtbarer Ausschnitt: 90° nach links und rechts
const TRACK_RANGE := 80.0
const SCAN_INTERVAL := 0.25
const LETTERS := {"mining": "B", "woodcutting": "H", "harvesting": "E", "fishing": "F"}
const DIRECTIONS := [["N", 0.0], ["NO", -PI / 4.0], ["O", -PI / 2.0], ["SO", -PI * 0.75], ["S", PI],
	["SW", PI * 0.75], ["W", PI / 2.0], ["NW", PI / 4.0]]

var player = null
var font: Font
var tracked: Array[Dictionary] = [] # {pos: Vector3, tier: int, profession: String}
var _scan_timer := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	font = ThemeDB.fallback_font


func _process(delta: float) -> void:
	if player == null:
		return
	_scan_timer -= delta
	if _scan_timer <= 0.0:
		_scan_timer = SCAN_INTERVAL
		tracked = scan(player)
	queue_redraw()


## Alle Vorkommen in Reichweite, die der Spieler mit seinen Sammelberufen aufspüren kann.
static func scan(p) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	var tiers := {}
	for id in LETTERS:
		tiers[id] = p.track_tier(id)
	for node in p.get_tree().get_nodes_in_group("interactable"):
		var source = node
		var data = source.get("data")
		if not data is Dictionary or not source.has_method("get_profession") or not source.is_interactable():
			continue
		var profession: String = source.get_profession()
		var tier := int(data.get("tier", 1))
		if not tiers.has(profession) or tier > int(tiers[profession]):
			continue
		var reach: float = TRACK_RANGE * (1.0 + p.bonus("track_range:" + profession))
		if source.global_position.distance_to(p.global_position) <= reach:
			result.append({"pos": source.global_position, "tier": tier, "profession": profession})
	return result


func _bearing_x(angle: float, center: float) -> float:
	var rel := wrapf(angle - float(player.cam_yaw), -PI, PI)
	if absf(rel) > HALF_FOV:
		return -1.0
	return center - rel / HALF_FOV * WIDTH * 0.5


func _draw() -> void:
	if player == null:
		return
	var view := get_viewport_rect().size
	var rect := Rect2(view.x * 0.5 - WIDTH * 0.5, 8.0, WIDTH, HEIGHT)
	var center := rect.get_center().x
	draw_rect(rect, Color(0, 0, 0, 0.45))
	draw_line(Vector2(center, rect.position.y), Vector2(center, rect.end.y), Color(1.0, 0.85, 0.5, 0.8), 2.0)
	for d in DIRECTIONS:
		var x := _bearing_x(float(d[1]), center)
		if x < 0.0:
			continue
		var text: String = d[0]
		var size := 16 if text.length() == 1 else 12
		var color := Color(1.0, 0.5, 0.4) if text == "N" else Color(0.9, 0.9, 0.9)
		var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		draw_string(font, Vector2(x - w * 0.5, rect.position.y + 20.0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
	for t in tracked:
		var to: Vector3 = t["pos"] - player.global_position
		var x := _bearing_x(atan2(-to.x, -to.z), center)
		if x < 0.0:
			continue
		var color := Game.tier_color(int(t["tier"]))
		var pos := Vector2(x, rect.end.y + 9.0)
		draw_circle(pos, 7.0, Color(0, 0, 0, 0.6))
		draw_circle(pos, 5.5, color)
		var letter: String = LETTERS.get(t["profession"], "?")
		draw_string(font, pos + Vector2(-3.5, 4.0), letter, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(0, 0, 0, 0.85))
	var clock := "Tag %d  ·  %s" % [Game.day, clock_text()]
	var cw := font.get_string_size(clock, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
	draw_string(font, Vector2(center - cw * 0.5, rect.end.y + 34.0), clock, HORIZONTAL_ALIGNMENT_LEFT, -1, 13,
		Color(0.9, 0.9, 0.9, 0.85))


static func clock_text() -> String:
	var minutes := int(Game.time_of_day * 60.0) % (24 * 60)
	return "%02d:%02d" % [minutes / 60, minutes % 60]
