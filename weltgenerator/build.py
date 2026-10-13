"""Baut weltgenerator.html aus src/ (alles in einer Datei, läuft offline per Doppelklick)."""
import pathlib
src = pathlib.Path(__file__).parent / "src"
html = (src / "index.html").read_text()
kern = (src / "kern.js").read_text()
for platzhalter, datei in [("/*ZIP*/", "zip.js"), ("/*GL*/", "gl.js"), ("/*MARKER*/", "marker.js"), ("/*APP*/", "app.js")]:
    html = html.replace(platzhalter, (src / datei).read_text())
html = html.replace("/*KERN*/", kern)
assert "</script" not in kern.lower()
(pathlib.Path(__file__).parent / "weltgenerator.html").write_text(html)
print("weltgenerator.html", len(html) // 1024, "KB")
