@echo off
rem Importiert die Weltdaten (welt_daten) neu in Terrain3D: Boeden nach Biom-Regeln, Kiesbett unter Fluessen.
echo Weltimport laeuft, das dauert ein paar Minuten ...
"C:\Users\Philipp\Desktop\Godot\Godot_v4.7.2-stable_win64.exe" --headless --path "%~dp0." -s res://tests/welt_importieren.gd
echo.
echo Fertig. Dieses Fenster kann geschlossen werden.
pause
