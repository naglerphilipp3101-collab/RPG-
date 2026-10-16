extends RefCounted
## Ersatz für Terrain3D in Tests ohne das Plugin: Höhen aus dem Weltgenerator-Export (hoehe_*.r32),
## bilinear interpoliert. natur.gd fragt terrain.get("data").get_height(Vector3) ab – genau das liefert das hier.

var data
var bild: Image
var n := 0
var mpp := 1.0
var halb := 0.0


func _init() -> void:
	data = self


func laden(ordner: String) -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ordner.path_join("welt.json")))
	n = int(meta["aufloesung"])
	mpp = float(meta["meter_pro_pixel"])
	halb = float(meta["welt_m"]) / 2.0
	bild = Image.create_from_data(n, n, false, Image.FORMAT_RF, FileAccess.get_file_as_bytes(ordner.path_join(meta["hoehe"]["datei"])))


func get_height(p: Vector3) -> float:
	var fx := (p.x + halb) / mpp - 0.5
	var fz := (p.z + halb) / mpp - 0.5
	var x := clampi(int(floor(fx)), 0, n - 2)
	var z := clampi(int(floor(fz)), 0, n - 2)
	var tx := clampf(fx - x, 0.0, 1.0)
	var tz := clampf(fz - z, 0.0, 1.0)
	var a := lerpf(bild.get_pixel(x, z).r, bild.get_pixel(x + 1, z).r, tx)
	var b := lerpf(bild.get_pixel(x, z + 1).r, bild.get_pixel(x + 1, z + 1).r, tx)
	return lerpf(a, b, tz)
