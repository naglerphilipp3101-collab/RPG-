@echo off
rem Laedt die Texturen und 3D-Modelle von Poly Haven (CC0) nach godot\assets\bibliothek\ (ca. 3-5 GB, dauert je nach Internet eine Weile).
rem Bereits geladene Dateien werden uebersprungen, ein Abbruch ist also kein Problem.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0assets\bibliothek\bibliothek_laden.ps1"
echo.
echo Dieses Fenster kann geschlossen werden.
pause
