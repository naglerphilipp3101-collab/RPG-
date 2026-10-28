class_name SkillIcons
## Kleine Bilder für den Skillbaum: Fähigkeiten, große Passiven und Ultimative.
## Liegt unter res://assets/icons/faehigkeiten/<id>.png oder .svg eine Datei, wird sie benutzt,
## sonst ein per Code gezeichnetes Symbol ("icon" im Knoten, sonst passend zur Vorlage).

const ORDNER := "res://assets/icons/faehigkeiten/"
## Symbol je Fähigkeits-Vorlage, wenn der Knoten kein eigenes "icon" hat.
const NACH_VORLAGE := {
	"strike": "sword", "dash": "dash", "leap": "leap", "buff": "armor", "evade": "dash", "shot": "arrow",
	"zone": "impact", "beam": "arrow", "summon": "crown", "wall": "fortress", "detonate": "impact", "sacrifice": "heart",
}

static var _texturen := {}


static func textur(node_id: String) -> Texture2D:
	if not _texturen.has(node_id):
		var tex: Texture2D = null
		for ext in ["png", "svg"]:
			var path := ORDNER + node_id + "." + String(ext)
			if ResourceLoader.exists(path):
				tex = load(path)
				break
		_texturen[node_id] = tex
	return _texturen[node_id]


static func symbol(node: Dictionary) -> String:
	if node.has("icon"):
		return String(node["icon"])
	match String(node.get("type", "")):
		"passive": return "star"
		"ultimate": return "impact"
	return NACH_VORLAGE.get(String(node.get("skill", {}).get("template", "")), "sword")


## Zeichnet das Bild eines Knotens in ein Quadrat der Kantenlänge 2 * r um `mitte`.
static func zeichnen(ci: CanvasItem, node: Dictionary, mitte: Vector2, r: float, farbe: Color) -> void:
	var tex := textur(String(node.get("id", "")))
	if tex != null:
		ci.draw_texture_rect(tex, Rect2(mitte - Vector2(r, r), Vector2(r, r) * 2.0), false, farbe)
		return
	ci.draw_set_transform(mitte, 0.0, Vector2(r, r))
	_symbol(ci, symbol(node), farbe)
	ci.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


## Alle Symbole in Einheiten von -1 bis 1 (die Transformation skaliert auf die Knotengröße).
static func _symbol(ci: CanvasItem, art: String, f: Color) -> void:
	var dunkel := Color(0.1, 0.08, 0.06, f.a)
	var w := 0.12 # Linienstärke
	match art:
		"sword":
			_schwert(ci, f, PI * 0.25)
		"shield", "armor":
			var schild := PackedVector2Array([Vector2(-0.7, -0.8), Vector2(0, -0.92), Vector2(0.7, -0.8), Vector2(0.68, -0.1),
				Vector2(0.45, 0.45), Vector2(0, 0.92), Vector2(-0.45, 0.45), Vector2(-0.68, -0.1)])
			ci.draw_colored_polygon(schild, f)
			if art == "armor": # Schild mit Kreuz: Schutz
				ci.draw_rect(Rect2(-0.1, -0.6, 0.2, 1.1), dunkel)
				ci.draw_rect(Rect2(-0.45, -0.25, 0.9, 0.2), dunkel)
			else:
				ci.draw_circle(Vector2(0, -0.05), 0.22, dunkel)
		"dash":
			for i in 3:
				var y := -0.45 + i * 0.45
				ci.draw_line(Vector2(-0.9 + i * 0.15, y), Vector2(0.15, y), f, w)
			ci.draw_colored_polygon(PackedVector2Array([Vector2(0.2, -0.65), Vector2(0.9, 0), Vector2(0.2, 0.65)]), f)
		"arrow":
			ci.draw_line(Vector2(-0.75, 0.75), Vector2(0.45, -0.45), f, w)
			ci.draw_colored_polygon(PackedVector2Array([Vector2(0.8, -0.8), Vector2(0.2, -0.6), Vector2(0.6, -0.2)]), f)
			ci.draw_line(Vector2(-0.75, 0.75), Vector2(-0.75, 0.35), f, w)
			ci.draw_line(Vector2(-0.75, 0.75), Vector2(-0.35, 0.75), f, w)
		"leap":
			ci.draw_arc(Vector2(0, 0.35), 0.7, PI * 1.05, PI * 1.85, 12, f, w)
			ci.draw_line(Vector2(-0.85, 0.75), Vector2(0.85, 0.75), f, w)
			ci.draw_colored_polygon(PackedVector2Array([Vector2(0.45, -0.05), Vector2(0.85, 0.05), Vector2(0.62, 0.5)]), f)
		"shout":
			ci.draw_colored_polygon(PackedVector2Array([Vector2(-0.85, -0.25), Vector2(-0.5, -0.25), Vector2(-0.1, -0.6),
				Vector2(-0.1, 0.6), Vector2(-0.5, 0.25), Vector2(-0.85, 0.25)]), f)
			for i in 3:
				ci.draw_arc(Vector2(-0.1, 0), 0.3 + i * 0.25, -PI * 0.3, PI * 0.3, 8, f, w * 0.8)
		"whirl":
			for i in 3:
				var a := TAU * i / 3.0
				ci.draw_arc(Vector2.ZERO, 0.72, a, a + TAU / 3.0 - 0.6, 10, f, w)
				var spitze := Vector2(cos(a + TAU / 3.0 - 0.6), sin(a + TAU / 3.0 - 0.6)) * 0.72
				var richtung := Vector2(-sin(a + TAU / 3.0 - 0.6), cos(a + TAU / 3.0 - 0.6))
				ci.draw_colored_polygon(PackedVector2Array([spitze + richtung * 0.3, spitze - spitze.normalized() * 0.2,
					spitze + spitze.normalized() * 0.2]), f)
			ci.draw_circle(Vector2.ZERO, 0.18, f)
		"heart":
			ci.draw_circle(Vector2(-0.33, -0.25), 0.38, f)
			ci.draw_circle(Vector2(0.33, -0.25), 0.38, f)
			ci.draw_colored_polygon(PackedVector2Array([Vector2(-0.68, -0.1), Vector2(0.68, -0.1), Vector2(0, 0.8)]), f)
			ci.draw_rect(Rect2(-0.07, -0.5, 0.14, 0.6), dunkel)
			ci.draw_rect(Rect2(-0.3, -0.27, 0.6, 0.14), dunkel)
		"fortress":
			ci.draw_rect(Rect2(-0.55, -0.45, 1.1, 1.3), f)
			for i in 3:
				ci.draw_rect(Rect2(-0.55 + i * 0.42, -0.8, 0.26, 0.4), f)
			ci.draw_circle(Vector2(0, 0.45), 0.22, dunkel)
			ci.draw_rect(Rect2(-0.22, 0.45, 0.44, 0.4), dunkel)
		"impact", "spikes", "star":
			var spitzen: int = {"impact": 8, "spikes": 12, "star": 5}[art]
			var innen: float = {"impact": 0.35, "spikes": 0.55, "star": 0.4}[art]
			var punkte := PackedVector2Array()
			for i in spitzen * 2:
				var a := -PI / 2.0 + PI * i / float(spitzen)
				punkte.append(Vector2(cos(a), sin(a)) * (0.92 if i % 2 == 0 else innen))
			ci.draw_colored_polygon(punkte, f)
			if art == "spikes":
				ci.draw_circle(Vector2.ZERO, 0.32, dunkel)
		"crown":
			ci.draw_colored_polygon(PackedVector2Array([Vector2(-0.8, 0.5), Vector2(-0.8, -0.55), Vector2(-0.4, -0.05),
				Vector2(0, -0.75), Vector2(0.4, -0.05), Vector2(0.8, -0.55), Vector2(0.8, 0.5)]), f)
			ci.draw_rect(Rect2(-0.8, 0.6, 1.6, 0.2), f)
		_:
			_schwert(ci, f, PI * 0.25)


static func _schwert(ci: CanvasItem, f: Color, winkel: float) -> void:
	var dreh := Transform2D(winkel, Vector2.ZERO)
	var klinge := PackedVector2Array([Vector2(-0.12, 0.3), Vector2(-0.12, -0.7), Vector2(0, -0.95), Vector2(0.12, -0.7), Vector2(0.12, 0.3)])
	ci.draw_colored_polygon(dreh * klinge, f)
	ci.draw_colored_polygon(dreh * PackedVector2Array([Vector2(-0.45, 0.3), Vector2(0.45, 0.3), Vector2(0.45, 0.45), Vector2(-0.45, 0.45)]), f)
	ci.draw_colored_polygon(dreh * PackedVector2Array([Vector2(-0.08, 0.45), Vector2(0.08, 0.45), Vector2(0.08, 0.82), Vector2(-0.08, 0.82)]), f)
	ci.draw_circle(dreh * Vector2(0, 0.9), 0.11, f)
