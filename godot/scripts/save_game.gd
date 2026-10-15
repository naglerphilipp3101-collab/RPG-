extends RefCounted
## Speichern und Laden des Spielstands als JSON-Datei.
## Ort unter Windows: %APPDATA%\Godot\app_userdata\RPG\savegame.json

const VERSION := 2 # 2: Berufe als Skill 0–300, Charakterlevel, Attribute, Tageszeit


static func has_save(path: String) -> bool:
	return FileAccess.file_exists(path)


static func save(tree: SceneTree, path: String) -> bool:
	var player = tree.get_first_node_in_group("player")
	if player == null:
		return false
	var data := {
		"version": VERSION,
		"saved_at": Time.get_datetime_string_from_system(false, true),
		"next_uid": Game._next_uid,
		"time_of_day": Game.time_of_day,
		"day": Game.day,
		"player": player.to_save(),
	}
	# Erst in eine temporäre Datei schreiben, dann ersetzen: so bleibt bei einem Absturz der alte Stand erhalten
	var tmp := path + ".tmp"
	var file := FileAccess.open(tmp, FileAccess.WRITE)
	if file == null:
		push_error("Speichern fehlgeschlagen: %s" % error_string(FileAccess.get_open_error()))
		return false
	file.store_string(JSON.stringify(data, "\t"))
	file.close()
	var dir := DirAccess.open(path.get_base_dir())
	if dir.file_exists(path.get_file()):
		dir.remove(path.get_file())
	return dir.rename(tmp.get_file(), path.get_file()) == OK


static func load_into(tree: SceneTree, path: String) -> bool:
	if not has_save(path):
		return false
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return false
	var data = JSON.parse_string(file.get_as_text())
	if not data is Dictionary or not data.has("player"):
		push_error("Spielstand beschädigt: %s" % path)
		return false
	var player = tree.get_first_node_in_group("player")
	if player == null:
		return false
	Game._next_uid = maxi(Game._next_uid, int(data.get("next_uid", 1)))
	Game.time_of_day = fposmod(float(data.get("time_of_day", Game.START_HOUR)), 24.0)
	Game.day = maxi(int(data.get("day", 1)), 1)
	var player_data: Dictionary = data["player"]
	player_data["_version"] = int(data.get("version", 1))
	player.from_save(player_data)
	return true


static func delete(path: String) -> void:
	if has_save(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))


static func saved_at(path: String) -> String:
	if not has_save(path):
		return ""
	var file := FileAccess.open(path, FileAccess.READ)
	var data = JSON.parse_string(file.get_as_text())
	if data is Dictionary:
		return String(data.get("saved_at", "")).replace("T", "  ")
	return ""
