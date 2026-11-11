class_name MenschDaten
extends RefCounted
## Lädt die aufbereiteten MakeHuman-Daten (daten/mensch.json + mensch.bin) einmal
## und hält sie für alle Menschen im Spiel bereit. Formen werden erst bei Bedarf entpackt.

const ORDNER := "res://assets/charakter/daten/"

static var _geladen := false
static var meta: Dictionary
static var _puffer: PackedByteArray
static var grund_pos: PackedVector3Array        # Punkte des Grundnetzes in Metern
static var knochen_index: PackedInt32Array      # je Punkt 4 Knochen
static var knochen_gewicht: PackedFloat32Array  # je Punkt 4 Gewichte
static var _formen := {}                        # Name -> [PackedInt32Array, PackedVector3Array]
static var _teile := {}                         # Name -> Dictionary (mh_index, uv, dreiecke, dreiecke_mh)
static var _anbau := {}


static func laden() -> void:
	if _geladen:
		return
	_geladen = true
	var f := FileAccess.open(ORDNER + "mensch.json", FileAccess.READ)
	meta = JSON.parse_string(f.get_as_text())
	var b := FileAccess.open_compressed(ORDNER + "mensch.bin", FileAccess.READ, FileAccess.COMPRESSION_ZSTD)
	_puffer = b.get_buffer(b.get_length())
	var g: Dictionary = meta["grund"]
	grund_pos = _vec3(_f32(g["positionen"]))
	knochen_index = _i32(g["knochen_index"])
	knochen_gewicht = _f32(g["knochen_gewicht"])


static func _stueck(spec: Array) -> PackedByteArray:
	var a: int = spec[0]
	var n: int = spec[1]
	return _puffer.slice(a, a + n)


static func _f32(spec: Array) -> PackedFloat32Array:
	return _stueck(spec).to_float32_array()


static func _i32(spec: Array) -> PackedInt32Array:
	return _stueck(spec).to_int32_array()


static func _vec3(f: PackedFloat32Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	out.resize(f.size() / 3)
	for i in out.size():
		out[i] = Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2])
	return out


static func hat_form(name: String) -> bool:
	laden()
	return meta["formen"].has(name)


## Liefert [Indizes, Verschiebungen in Metern] einer Form.
static func form(name: String) -> Array:
	laden()
	if _formen.has(name):
		return _formen[name]
	var spec: Array = meta["formen"][name]
	var anzahl: int = spec[2]
	var roh := _stueck(spec)
	var idx := PackedInt32Array()
	idx.resize(anzahl)
	for i in anzahl:
		idx[i] = roh.decode_u16(i * 2)
	var off := anzahl * 2 + (anzahl % 2) * 2
	var d := PackedVector3Array()
	d.resize(anzahl)
	for i in anzahl:
		var o := off + i * 6
		d[i] = Vector3(roh.decode_s16(o), roh.decode_s16(o + 2), roh.decode_s16(o + 4)) * 0.0001
	var paar := [idx, d]
	_formen[name] = paar
	return paar


## Sichtbares Teil (koerper, wimpern, zaehne, zunge).
static func teil(name: String) -> Dictionary:
	laden()
	if _teile.has(name):
		return _teile[name]
	var spec: Dictionary = meta["teile"][name]
	var t := {
		"mh_index": _i32(spec["mh_index"]),
		"uv": _f32(spec["uv"]),
		"dreiecke": _i32(spec["dreiecke"]),
	}
	var mh: PackedInt32Array = t["mh_index"]
	var dr: PackedInt32Array = t["dreiecke"]
	var dmh := PackedInt32Array()
	dmh.resize(dr.size())
	for i in dr.size():
		dmh[i] = mh[dr[i]]
	t["dreiecke_mh"] = dmh
	_teile[name] = t
	return t


## Anbauteil im MakeHuman-Format (.mhclo): Augen.
static func anbau(name: String) -> Dictionary:
	laden()
	if _anbau.has(name):
		return _anbau[name]
	var spec: Dictionary = meta["anbau"][name]
	var t := {
		"bindung": _f32(spec["bindung"]),
		"skalierung": spec["skalierung"],
		"uv": _f32(spec["uv"]),
		"dreiecke": _i32(spec["dreiecke"]),
	}
	_anbau[name] = t
	return t
