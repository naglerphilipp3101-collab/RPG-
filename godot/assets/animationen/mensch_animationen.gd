class_name MenschAnimationen
extends RefCounted
## Animationen für alle Menschen (Spieler, NPCs, menschliche Gegner).
## Quelle: Quaternius „Universal Animation Library“ 1 und 2 (CC0). Godot rechnet die Dateien beim
## Import auf das Humanoid-Profil um (Einstellungen in den .import-Dateien, Knochenliste knochen_ue.tres).
## Das Skelett von Mensch nutzt dieselben Knochennamen und Achsen, daher passen die Spuren direkt.

const QUELLEN := [
	"res://assets/animationen/quaternius/UAL1_Standard.glb",
	"res://assets/animationen/quaternius/UAL2_Standard.glb",
]
## Name der Bibliothek im AnimationPlayer: Animationen heißen dann "mensch/Walk_Loop".
const BIBLIOTHEK := "mensch"
## Ohne Schleife geliefert, im Spiel aber als Schleife gebraucht (Sammeln).
const SCHLEIFEN := ["Sword_Idle", "Farm_Harvest", "Fixing_Kneeling"]
## Mixamo-Bibliotheken (je Waffe), von mixamo_umwandeln.gd erzeugt. Liegen nur lokal vor (gitignored);
## fehlt eine, nimmt das Spiel die Quaternius-Animationen.
const MIXAMO := "res://assets/animationen/mixamo/"
const MIXAMO_BIBLIOTHEKEN := ["schwert_schild", "grossschwert", "axt", "bogen", "gewehr", "magie", "bewegung", "einzeln"]

static var _bibliothek: AnimationLibrary
static var _mixamo := {}


## Alle Animationen, Spuren umgeschrieben auf "Skelett:<Knochen>" (AnimationPlayer-Wurzel = Mensch).
## Die Hüfte bewegt sich nur auf und ab (keine Wanderung nach vorn), der Root-Knochen gar nicht.
static func bibliothek() -> AnimationLibrary:
	if _bibliothek:
		return _bibliothek
	_bibliothek = AnimationLibrary.new()
	for pfad in QUELLEN:
		var szene: Node = load(pfad).instantiate()
		var ap: AnimationPlayer = szene.get_node("AnimationPlayer")
		for name in ap.get_animation_list():
			if name == "A_TPose" or _bibliothek.has_animation(name):
				continue
			_bibliothek.add_animation(name, _umschreiben(ap.get_animation(name), name))
		szene.free()
	return _bibliothek


static func _umschreiben(quelle: Animation, name: String) -> Animation:
	var a: Animation = quelle.duplicate(true)
	for t in range(a.get_track_count() - 1, -1, -1):
		var knochen := a.track_get_path(t).get_concatenated_subnames()
		if knochen == "Root":
			a.remove_track(t)
			continue
		a.track_set_path(t, NodePath("Skelett:" + knochen))
	if name in SCHLEIFEN:
		a.loop_mode = Animation.LOOP_LINEAR
	return a


## Hängt einen AnimationPlayer an den Menschen (oder gibt den vorhandenen zurück).
static func spieler_anhaengen(mensch: Node3D) -> AnimationPlayer:
	var ap: AnimationPlayer = mensch.get_node_or_null("Animationen")
	if ap:
		return ap
	ap = AnimationPlayer.new()
	ap.name = "Animationen"
	mensch.add_child(ap)
	ap.root_node = NodePath("..")
	ap.add_animation_library(BIBLIOTHEK, bibliothek())
	for name in mixamo():
		ap.add_animation_library(name, _mixamo[name])
	var sk: Skeleton3D = mensch.skelett
	var hips := sk.find_bone("Hips")
	if hips >= 0:
		sk.motion_scale = sk.get_bone_global_rest(hips).origin.y
	return ap


## Vorhandene Mixamo-Bibliotheken (Name -> AnimationLibrary), einmal geladen.
static func mixamo() -> Dictionary:
	if _mixamo.is_empty():
		for name in MIXAMO_BIBLIOTHEKEN:
			var pfad: String = MIXAMO + name + ".res"
			if ResourceLoader.exists(pfad):
				_mixamo[name] = load(pfad)
		if _mixamo.is_empty():
			_mixamo["_"] = null
	var d := _mixamo.duplicate()
	d.erase("_")
	return d
