"""Haus-Baukasten im 1-m-Raster, jedes Teil heil und kaputt. Die Stockwerkshöhe legt Philipp beim Bauen selbst fest.
Aufruf: python baukasten.py -- <zielordner/modelle> [--nur wand,balken_2m] [--vorschau <ordner>]

Grundregeln (damit später Blueprints einrasten und beim Backen verdeckte Flächen sicher erkannt werden):
  - Alle Maße liegen genau im Raster, Flächen sind eben und achsparallel (keine Fasen an Stoßflächen).
  - Länge entlang x, Boden bei z = 0. In Blender zeigt die Vorderseite nach -y (in Godot nach +z).

Teile:
  wand          massive Wand 2 x 2 m, 0.10 m dick (y -0.05..0.05), Putz auf beiden Seiten.
  wand_2x1      2 m breit, 1 m hoch (hochkant gedreht: 1 m breit, 2 m hoch).
  wand_1x1      1 x 1 m. Alle Wände: Ursprung Mitte der Unterkante, frei drehbar, Überlappen erlaubt.
  balken_2m     Fachwerk-Balken 2 m (x -1..1), Querschnitt 0.14 breit x 0.16 tief (steht je Wandseite 3 cm über).
  balken_1m     Ursprung: Mitte des Balkens. Waagerecht auf eine Wandkante legen (z = 0 oder 2),
                senkrecht als Ständer um 90° um die Querachse drehen (Mitte bei z = 1).
  strebe_2m     schräge Strebe über eine ganze Wand, von unten links (x -1, z 0) nach oben rechts (x 1, z 2),
                Enden waagerecht abgeschnitten. Ursprung wie bei der Wand. Für die Gegenrichtung um die Hochachse drehen."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, quader, flaeche, verbiegen, bruchkante
import props

RASTER = 2.0
WAND_D = 0.10                    # Wanddicke
BALKEN_B = 0.14                  # Balkenbreite (in der Wandebene)
BALKEN_T = 0.16                  # Balkentiefe (quer zur Wand)


def wand_flaeche(m, kaputt, breite, hoehe):
    """Massive Wand breite x hoehe (x -breite/2..breite/2, z 0..hoehe). Kaputt: ausgebrochenes Loch,
    abgebröckelte Oberkante, Schutt am Boden. Alle Außenkanten, die stehen bleiben, liegen im Raster."""
    if not kaputt:
        m.teil(quader(breite, WAND_D, hoehe, int(breite * 2), 1, int(hoehe * 2)), "putz", M((0, 0, hoehe / 2)),
               versatz=(0, 0))
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


def wand(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 2.0)


def wand_2x1(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 1.0)


def wand_1x1(m, kaputt):
    wand_flaeche(m, kaputt, 1.0, 1.0)


def balken(m, kaputt, laenge):
    if not kaputt:
        bm = quader(laenge, BALKEN_T, BALKEN_B, max(1, int(laenge / 0.5)), 1, 1)
        verbiegen(bm, m.rnd, 0.003, 0.7, (0, 1, 1))          # leicht krumm, Stirnflächen bleiben im Raster
        m.teil(bm, "holz", None)
        return
    # Kaputt: verkohlt, ein Ende abgebrochen
    rest = laenge * 0.62
    bm = quader(rest, BALKEN_T, BALKEN_B, max(1, int(rest / 0.3)), 4, 3)
    bruchkante(bm, m.rnd, 1, 0.14)
    verbiegen(bm, m.rnd, 0.004, 0.5)
    m.teil(bm, "holz_verkohlt", M((-laenge / 2 + rest / 2, 0, 0)))


def balken_2m(m, kaputt):
    balken(m, kaputt, 2.0)


def balken_1m(m, kaputt):
    balken(m, kaputt, 1.0)


def strebe_2m(m, kaputt):
    """Prisma zwischen den Ecken unten links und oben rechts, Schnitte waagerecht."""
    d = BALKEN_B / 2 * math.sqrt(2)          # halbe Breite, waagerecht gemessen
    if not kaputt:
        pts = [(-1.0, 0.0), (-1 + 2 * d, 0.0), (1.0, 2.0), (1 - 2 * d, 2.0)]
    else:                                    # bei 55 % der Höhe abgebrochen
        h = 1.1
        pts = [(-1.0, 0.0), (-1 + 2 * d, 0.0), (-1 + 2 * d + h, h), (-1 + h, h)]
    bm = bmesh.new()
    a = [bm.verts.new((x, -BALKEN_T / 2, z)) for x, z in pts]
    b = [bm.verts.new((x, BALKEN_T / 2, z)) for x, z in pts]
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


MODELLE = {"wand": wand, "wand_2x1": wand_2x1, "wand_1x1": wand_1x1, "balken_2m": balken_2m, "balken_1m": balken_1m, "strebe_2m": strebe_2m}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
