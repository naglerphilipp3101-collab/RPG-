"""Haus-Baukasten im 1-m-Raster, jedes Teil heil und kaputt. Die Stockwerkshöhe legt Philipp beim Bauen selbst fest.
Aufruf: python baukasten.py -- <zielordner/modelle> [--nur wand,balken_2m] [--vorschau <ordner>]

Grundregeln (Skizze: /mnt/project-files/bilder/props/raster_skizze.png):
  - Wände (10 cm) und Balken (20 x 20 cm) liegen MITTIG auf den Rasterlinien.
  - Ursprung jedes Teils ist sein Anfangspunkt auf einem Rasterpunkt; das Teil läuft von dort 1 oder 2 m entlang +x.
    Gedreht wird immer um diesen Punkt.
  - Alle Stoßflächen sind eben und liegen genau im Raster (für Blueprints und das spätere Backen).
  - In Blender zeigt die Vorderseite nach -y (in Godot nach +z).

Teile:
  wand          massive Wand 2 x 2 m (x 0..2, z 0..2), 0.10 m dick (y -0.05..0.05), Putz auf beiden Seiten.
  wand_2x1      2 m breit, 1 m hoch (hochkant gedreht: 1 m breit, 2 m hoch).
  wand_1x1      1 x 1 m.
  balken_2m     Balken 20 x 20 cm, x 0..2 (bzw. 0..1), Mitte auf der Rasterlinie (y, z um 0). Waagerecht auf eine
  balken_1m     Wandkante legen, als Ständer um 90° hochkant drehen (steht dann auf dem Rasterpunkt).
  staender_2m   Senkrechter Balken (19,6 cm), steht auf dem Rasterpunkt und läuft 2 bzw. 1 m nach oben.
  staender_1m
  strebe_2m     Schräge über eine 2 x 2-Wand: Mittellinie von (0|0) nach (2|2), Enden waagerecht abgeschnitten.
  eckklotz      Würfel 20,4 cm um einen Rasterpunkt: füllt Ecken und Kreuzungen, wo Balken zusammenkommen.

Vorrang bei Überlappung (welche Textur sichtbar ist): eckklotz > balken > staender > strebe, siehe ECKKLOTZ usw.
Die Teile sind dafür absichtlich nicht verbogen: schon 3 mm Krümmung würden die Reihenfolge stellenweise umdrehen."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, quader, flaeche, bruchkante
import props

RASTER = 2.0
WAND_D = 0.10                    # Wanddicke
BALKEN = 0.20                    # Balkenquerschnitt 20 x 20 cm, Mitte auf der Rasterlinie
# Vorrang bei Überlappung: wo sich Teile durchdringen, liegen sonst gleiche Flächen genau aufeinander und flackern.
# Darum ist jede Stufe je Seite 2 mm schmaler als die nächsthöhere; die sichtbare Fläche gehört immer dem höheren Teil.
#   1. eckklotz (20,4 cm)   2. balken (20 cm, waagerecht, läuft durch)   3. staender (19,6 cm)   4. strebe (19,2 cm)
ECKKLOTZ = BALKEN + 0.004
STAENDER = BALKEN - 0.004
STREBE = BALKEN - 0.008


def wand_flaeche(m, kaputt, breite, hoehe):
    """Massive Wand breite x hoehe (x 0..breite, z 0..hoehe). Kaputt: ausgebrochenes Loch,
    abgebröckelte Oberkante, Schutt am Boden. Alle Außenkanten, die stehen bleiben, liegen im Raster."""
    m.G = Matrix.Translation((breite / 2, 0, 0))         # gebaut um die Mitte, Ursprung aber am Anfangspunkt
    if not kaputt:
        m.teil(quader(breite, WAND_D, hoehe, int(breite * 2), 1, int(hoehe * 2)), "putz", M((0, 0, hoehe / 2)),
               versatz=(0, 0))
        m.G = None
        return
    # Gitter aus 5-cm-Zellen: Zellen im Loch und über der Bruchkante fehlen, dann auf Wanddicke aufgedickt
    z = 0.05
    nx, nz = round(breite / z), round(hoehe / z)
    sx, sz = breite / 2, hoehe / 2                       # Maßstab gegenüber der 2 x 2-Wand
    def fehlt(i, j):                                     # i = Zeile (Höhe), j = Spalte (x)
        x = -breite / 2 + (j + 0.5) * z; h = (i + 0.5) * z
        xr = x / sx; hr = h / sz                         # auf 2 x 2 m umgerechnet
        kante = 1.75 - 0.45 * max(0.0, xr + 0.2) + 0.12 * noise.noise(Vector((xr * 4, 0.3, 1.1)))
        r = 0.38 + 0.1 * noise.noise(Vector((xr * 5, hr * 5, 2.7)))
        return hr > kante or ((xr + 0.35) ** 2 + ((hr - 1.0) * 1.2) ** 2) ** 0.5 < r
    gitter = [[(-breite / 2 + j * z, -WAND_D / 2, i * z) for j in range(nx + 1)] for i in range(nz + 1)]
    bm = flaeche(gitter, 0.0, fehlt)
    # Bruchränder zackig verschieben, damit keine Treppenstufen bleiben (Außenkanten bleiben im Raster)
    for v in bm.verts:
        if any(len(e.link_faces) < 2 for e in v.link_edges) and v.co.z > 1e-4 and abs(abs(v.co.x) - breite / 2) > 1e-4:
            v.co.x += m.rnd.uniform(-0.02, 0.02); v.co.z += m.rnd.uniform(-0.025, 0.02)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-WAND_D)
    bm.normal_update()
    m.teil(bm, "putz", None)
    for k in range(int(4 + 5 * breite * hoehe / 4)):
        g = m.rnd.uniform(0.05, 0.13)
        m.teil(basis.brocken(m.rnd, g * 1.5, g, g * 0.6), "putz",
               M((m.rnd.uniform(-0.4, 0.45) * breite, m.rnd.choice((-1, 1)) * m.rnd.uniform(0.12, 0.6), g * 0.3),
                 (0, 0, m.rnd.uniform(0, 180))))
    m.G = None


def wand(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 2.0)


def wand_2x1(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 1.0)


def wand_1x1(m, kaputt):
    wand_flaeche(m, kaputt, 1.0, 1.0)


def balken(m, kaputt, laenge, dicke=BALKEN):
    """Balken dicke x dicke von x = 0 bis laenge, Mitte auf der Rasterlinie (y und z um 0)."""
    if not kaputt:
        bm = quader(laenge, dicke, dicke, max(1, int(laenge / 0.5)), 1, 1)
        m.teil(bm, "holz", M((laenge / 2, 0, 0)))
        return
    # Kaputt: verkohlt, das hintere Ende abgebrochen (nur die Bruchstelle ist uneben)
    rest = laenge * 0.62
    bm = quader(rest, dicke, dicke, max(1, int(rest / 0.3)), 4, 4)
    bruchkante(bm, m.rnd, 1, 0.16)
    m.teil(bm, "holz_verkohlt", M((rest / 2, 0, 0)))


def balken_2m(m, kaputt):
    balken(m, kaputt, 2.0)


def balken_1m(m, kaputt):
    balken(m, kaputt, 1.0)


def staender(m, kaputt, laenge):
    """Senkrechter Balken: steht auf dem Rasterpunkt, läuft nach oben (in Blender +z, in Godot +y).
    Gebaut wie ein Balken entlang x und dann aufgestellt, damit die Maserung senkrecht läuft."""
    m.G = Matrix.Rotation(math.radians(-90), 4, "Y")
    balken(m, kaputt, laenge, STAENDER)
    m.G = None


def staender_2m(m, kaputt):
    staender(m, kaputt, 2.0)


def staender_1m(m, kaputt):
    staender(m, kaputt, 1.0)


def eckklotz(m, kaputt):
    """Würfel um einen Rasterpunkt (Mitte = Ursprung). Füllt die Stufe an Außenecken und deckt Kreuzungen ab."""
    if not kaputt:
        m.teil(quader(ECKKLOTZ, ECKKLOTZ, ECKKLOTZ, 1, 1, 1), "holz", None, uv="boxz")
        return
    bm = quader(ECKKLOTZ, ECKKLOTZ, ECKKLOTZ, 3, 3, 3)
    for v in bm.verts:                       # angekohlt und an den Kanten abgeplatzt, bleibt aber im Raster
        if v.co.z > ECKKLOTZ / 2 - 1e-4 and v.co.x > 0:
            v.co.z -= m.rnd.uniform(0.0, 0.04)
    m.teil(bm, "holz_verkohlt", None, uv="boxz")


def strebe_2m(m, kaputt):
    """Schräge Strebe: Mittellinie vom Rasterpunkt (0|0) zum Rasterpunkt (2|2), Enden waagerecht abgeschnitten
    (sie stecken in den waagerechten Balken)."""
    d = STREBE / 2 * math.sqrt(2)            # halbe Breite, waagerecht gemessen
    h = 2.0 if not kaputt else 1.1           # kaputt: bei 55 % der Höhe abgebrochen
    pts = [(-d, 0.0), (d, 0.0), (h + d, h), (h - d, h)]
    bm = bmesh.new()
    a = [bm.verts.new((x, -STREBE / 2, z)) for x, z in pts]
    b = [bm.verts.new((x, STREBE / 2, z)) for x, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(4):
        bm.faces.new((a[i], b[i], b[(i + 1) % 4], a[(i + 1) % 4]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if kaputt:
        oben = [e for e in bm.edges if all(v.co.z > h - 1e-4 for v in e.verts)]
        bmesh.ops.subdivide_edges(bm, edges=oben, cuts=3, use_grid_fill=True)
        for v in bm.verts:
            if v.co.z > h - 1e-4:
                v.co.z += m.rnd.uniform(-0.1, 0.06)
    # UVs entlang der Schräge: Teil zum Rechnen so drehen, dass die Strebe entlang x liegt
    rot = Matrix.Rotation(math.radians(45), 4, "Y")
    bm.transform(rot)
    m.teil(bm, "holz" if not kaputt else "holz_verkohlt", rot.inverted())


MODELLE = {"wand": wand, "wand_2x1": wand_2x1, "wand_1x1": wand_1x1, "balken_2m": balken_2m, "balken_1m": balken_1m, "strebe_2m": strebe_2m,
           "staender_2m": staender_2m, "staender_1m": staender_1m, "eckklotz": eckklotz}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
