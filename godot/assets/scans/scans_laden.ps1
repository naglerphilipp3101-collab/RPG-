# Lädt die gescannten CC0-Assets von Poly Haven (polyhaven.com) nach godot/assets/scans/<id>/.
# Die Rohdateien sind nicht im Repository (siehe .gitignore), nur diese Liste.
# Aufruf (PowerShell): .\scans_laden.ps1        – vorhandene Dateien werden übersprungen
$ziel = $PSScriptRoot
$texturen = @("forest_leaves_02", "forest_ground_04", "leafy_grass", "coast_sand_01", "dry_ground_01", "brown_mud_03",
	"rock_face_03", "rocky_trail_02", "cobblestone_floor_08", "mossy_cobblestone", "snow_02")
$modelle = @("rock_moss_set_01", "rock_moss_set_02", "boulder_01", "rock_09",
	"grass_medium_01", "fern_02", "celandine_01", "dandelion_01")

function Laden($url, $datei) {
	if (Test-Path $datei) { return 0 }
	New-Item -ItemType Directory -Force (Split-Path $datei) | Out-Null
	Invoke-WebRequest -Uri $url -OutFile $datei -UseBasicParsing
	return (Get-Item $datei).Length
}

$summe = 0
foreach ($id in $texturen) {
	$f = Invoke-RestMethod "https://api.polyhaven.com/files/$id"
	foreach ($k in @("Diffuse", "nor_gl", "Rough", "Displacement")) {
		$e = $f.$k."2k".jpg
		if ($e) { $summe += Laden $e.url (Join-Path $ziel "$id\$id`_$($k.ToLower())_2k.jpg") }
	}
	Write-Output "Textur $id"
}
foreach ($id in $modelle) {
	$g = (Invoke-RestMethod "https://api.polyhaven.com/files/$id").gltf."2k".gltf
	$summe += Laden $g.url (Join-Path $ziel "$id\$id`_2k.gltf")
	foreach ($i in $g.include.PSObject.Properties) { $summe += Laden $i.Value.url (Join-Path $ziel "$id\$($i.Name)") }
	Write-Output "Modell $id"
}
Write-Output ("Fertig, {0:N1} MB neu geladen" -f ($summe / 1MB))
