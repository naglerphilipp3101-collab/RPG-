# Lädt die Asset-Bibliothek von Poly Haven (polyhaven.com, alles CC0) nach godot/assets/bibliothek/:
#   texturen/<gruppe>/<id>/   Farbe, Normal (OpenGL), Rauheit, AO, Höhe, ggf. Metall – je 2K-JPG
#   modelle/<gruppe>/<id>/    glTF in 2K mit Texturen (Pflanzen zusätzlich die Alpha-PNGs)
# Die Rohdateien sind nicht im Repository (siehe .gitignore), nur diese Liste. Noch nichts davon ist im Spiel eingebunden.
# Aufruf: Doppelklick auf "godot\Assets laden.bat" – vorhandene Dateien werden übersprungen, Abbruch und Neustart sind kein Problem.
param([string]$aufloesung = "2k")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # sonst ist Invoke-WebRequest in PowerShell 5 sehr langsam
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ziel = $PSScriptRoot

$texturen = [ordered]@{
	"boden" = @("coast_sand_rocks_02", "brown_mud_leaves_01", "aerial_grass_rock", "farm_soil", "dry_river_pebbles", "rocky_trail_02",
		"forest_leaves_02", "rocks_ground_02", "leaf_scattered_gravel", "forest_leaves_04", "rocks_ground_05", "brown_mud_03",
		"dry_decay_leaves", "mud_cracked_dry_03", "forest_floor", "muddy_tracks", "farm_furrows", "rocks_ground_03", "red_mud_stones")
	"fels" = @("aerial_rocks_02", "dark_rock", "gray_rocks", "marble_cliff_05", "dark_rock_02", "lichen_rock", "rock_face_04",
		"rock_wall_08", "marble_cliff_02", "rock_wall_09")
	"holz_rinde" = @("wood_table", "wood_planks", "bark_willow", "bark_brown_02", "wooden_panels", "bark_brown_01", "old_planks_02",
		"wooden_barrel", "wooden_garage_door", "tree_bark_03", "natural_walnut_veneer")
	"mauer_boden_dach" = @("stacked_brick_wall", "herringbone_concrete_tile_03", "damaged_plaster", "stone_tiles_02", "stone_wall_04",
		"stone_pathway_02", "stone_tiles", "grassy_cobblestone", "rough_plasterbrick_05", "thatch_roof_angled", "coral_fort_wall_02",
		"brick_wall_10", "floor_bricks_02", "roof_tiles_14", "rabdentse_ruins_wall", "castle_brick_broken_06", "rough_plaster_03")
	"metall" = @("metal_plate_02", "corrugated_iron")
}
$modelle = [ordered]@{
	"waffen_werkzeuge" = @("cannon_01", "antique_katana_01", "antique_estoc", "wooden_handle_saber", "ornate_medieval_dagger", "machete",
		"ornate_medieval_mace", "ornate_war_hammer", "kite_shield", "watering_can_metal_01", "cross_pein_hammer", "wooden_axe_02",
		"wooden_axe_03", "handsaw_wood", "picke_dirty_01", "spinning_wheel_01")
	"pflanzen" = @("grass_medium_01", "grass_bermuda_01", "fern_02", "searsia_lucida", "shrub_01", "leipoldtia_schultzei")
	"baeume" = @("tree_small_02", "jacaranda_tree", "island_tree_02", "fir_tree_01", "fir_sapling_medium", "quiver_tree_02",
		"dead_tree_trunk", "dead_tree_trunk_02", "pine_roots", "dry_branches_medium_01", "bark_debris_01", "dead_quiver_branch_01")
	"steine" = @("namaqualand_boulder_02", "namaqualand_boulder_03", "namaqualand_boulder_04", "namaqualand_cliff_02", "rock_moss_set_02",
		"boulder_01", "rock_09", "moon_rock_01")
	"licht_deko" = @("Lantern_01", "brass_candleholders", "street_lamp_01", "street_lamp_02", "Chandelier_03", "wooden_lantern_01",
		"wooden_candlestick", "brass_vase_01", "brass_vase_03", "brass_vase_04", "fancy_picture_frame_01", "seadogs_compass",
		"vintage_pocket_watch")
	"behaelter" = @("treasure_chest", "wooden_crate_01", "wooden_crate_02", "wine_barrel_01", "wooden_barrels_01", "wicker_basket_01",
		"wooden_bucket_01", "wooden_bucket_02", "planter_box_01", "planter_box_02")
	"bauten" = @("modular_fort_01", "modular_wooden_pier")
}

function Laden($url, $datei) {
	if (Test-Path $datei) { return 0 }
	New-Item -ItemType Directory -Force (Split-Path $datei) | Out-Null
	$tmp = "$datei.teil"
	Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
	Move-Item -Force $tmp $datei   # erst nach vollständigem Download umbenennen, damit ein Abbruch keine halben Dateien hinterlässt
	return (Get-Item $datei).Length
}

# Alle Poly-Haven-IDs einmal holen: prüft Tippfehler und findet die richtige Schreibweise (Groß/Klein)
$alle = @{}
(Invoke-RestMethod "https://api.polyhaven.com/assets").PSObject.Properties | ForEach-Object { $alle[$_.Name.ToLower()] = $_.Name }
function Pruefen($id) {
	$echt = $alle[$id.ToLower()]
	if (-not $echt) { $script:fehlt += $id; Write-Host "  !! $id gibt es auf Poly Haven nicht (Tippfehler?)" }
	return $echt
}

$summe = 0; $fehlt = @(); $fehler = @()
foreach ($gruppe in $texturen.Keys) {
	foreach ($id in $texturen[$gruppe]) {
		$id = Pruefen $id; if (-not $id) { continue }
		try {
			$f = Invoke-RestMethod "https://api.polyhaven.com/files/$id"
			foreach ($k in @("Diffuse", "nor_gl", "Rough", "AO", "Displacement", "Metal")) {
				$e = $f.$k.$aufloesung.jpg
				if ($e) { $summe += Laden $e.url (Join-Path $ziel "texturen\$gruppe\$id\$id`_$($k.ToLower())_$aufloesung.jpg") }
			}
			Write-Output ("Textur {0,-32} {1,6:N0} MB bisher" -f "$gruppe/$id", ($summe / 1MB))
		} catch { $fehler += $id; Write-Output "  !! Textur $id fehlgeschlagen: $($_.Exception.Message)" }
	}
}
foreach ($gruppe in $modelle.Keys) {
	foreach ($id in $modelle[$gruppe]) {
		$id = Pruefen $id; if (-not $id) { continue }
		try {
			$f = Invoke-RestMethod "https://api.polyhaven.com/files/$id"
			$g = $f.gltf.$aufloesung.gltf
			$ordner = Join-Path $ziel "modelle\$gruppe\$id"
			$summe += Laden $g.url (Join-Path $ordner "$id`_$aufloesung.gltf")
			foreach ($i in $g.include.PSObject.Properties) { $summe += Laden $i.Value.url (Join-Path $ordner $i.Name) }
			# Pflanzen/Bäume: Transparenz liegt als eigene PNG vor (die Farb-JPG im glTF hat keinen Alphakanal)
			foreach ($p in $f.PSObject.Properties) {
				if ($p.Name -match "alpha$") {
					$a = $p.Value.$aufloesung.png
					if ($a) { $summe += Laden $a.url (Join-Path $ordner "textures\$id`_$($p.Name.ToLower())_$aufloesung.png") }
				}
			}
			Write-Output ("Modell {0,-32} {1,6:N0} MB bisher" -f "$gruppe/$id", ($summe / 1MB))
		} catch { $fehler += $id; Write-Output "  !! Modell $id fehlgeschlagen: $($_.Exception.Message)" }
	}
}
Write-Output ""
Write-Output ("Fertig, {0:N0} MB neu geladen nach {1}" -f ($summe / 1MB), $ziel)
if ($fehlt) { Write-Output ("Nicht auf Poly Haven gefunden: " + ($fehlt -join ", ")) }
if ($fehler) { Write-Output ("Fehlgeschlagen (einfach nochmal starten): " + ($fehler -join ", ")) }
