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
  balken_2m     Balken 20 x 20 cm für 2 m (bzw. 1 m) von Rasterpunkt zu Rasterpunkt, steht an beiden Enden 10 cm über:
  balken_1m     x -0.1..2.1 (2,2 m lang). Mitte auf der Rasterlinie (y, z um 0). Waagerecht auf eine Wandkante legen,
                als Ständer um 90° hochkant drehen. An jedem Rasterpunkt reicht ein Balken damit genau so weit wie ein
                querliegender, Ecken sind ohne Stufe geschlossen.
  strebe_2m     Schräge über eine 2 x 2-Wand: Mittellinie von (0|0) nach (2|2), Enden waagerecht abgeschnitten.

Vorrang bei Überlappung (welche Fläche sichtbar ist) regelt das Material in Godot (materialien/balken.gdshader):
je waagerechter, desto höher. Die Teile sind dafür alle gleich dick und nicht verbogen."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, quader, flaeche, bruchkante, klotz
import props

RASTER = 2.0
WAND_D = 0.10                    # Wanddicke
BALKEN = 0.20                    # Balkenquerschnitt 20 x 20 cm, Mitte auf der Rasterlinie
UEBERSTAND = BALKEN / 2           # Balken stehen je Ende 10 cm über den Rasterpunkt (2 m Raster -> 2,2 m lang)


def mitte_y(bm):
    """Schiebt die aufgedickte Wand mittig auf die Rasterlinie (y -0,05..0,05), egal in welche Richtung solidify ging."""
    ys = [v.co.y for v in bm.verts]
    d = (min(ys) + max(ys)) / 2
    for v in bm.verts:
        v.co.y -= d


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
    mitte_y(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # Außenflächen zeigen nach außen (sonst sieht man die Rückseite)
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


def balken(m, kaputt, raster):
    """Balken 20 x 20 cm über raster Meter (Rasterpunkt 0 bis raster), je Ende UEBERSTAND länger.
    Mitte auf der Rasterlinie (y und z um 0)."""
    laenge = raster + 2 * UEBERSTAND
    if not kaputt:
        bm = quader(laenge, BALKEN, BALKEN, max(1, int(laenge / 0.5)), 1, 1)
        m.teil(bm, "holz", M((raster / 2, 0, 0)))
        return
    # Kaputt: verkohlt, das hintere Ende abgebrochen (nur die Bruchstelle ist uneben)
    rest = laenge * 0.62
    bm = quader(rest, BALKEN, BALKEN, max(1, int(rest / 0.3)), 4, 4)
    bruchkante(bm, m.rnd, 1, 0.16)
    m.teil(bm, "holz_verkohlt", M((rest / 2 - UEBERSTAND, 0, 0)))


def balken_2m(m, kaputt):
    balken(m, kaputt, 2.0)


def balken_1m(m, kaputt):
    balken(m, kaputt, 1.0)


def strebe_2m(m, kaputt):
    """Schräge Strebe: Mittellinie vom Rasterpunkt (0|0) zum Rasterpunkt (2|2), Enden waagerecht abgeschnitten
    (sie stecken in den waagerechten Balken)."""
    d = BALKEN / 2 * math.sqrt(2)            # halbe Breite, waagerecht gemessen
    h = 2.0 if not kaputt else 1.1           # kaputt: bei 55 % der Höhe abgebrochen
    pts = [(-d, 0.0), (d, 0.0), (h + d, h), (h - d, h)]
    bm = bmesh.new()
    a = [bm.verts.new((x, -BALKEN / 2, z)) for x, z in pts]
    b = [bm.verts.new((x, BALKEN / 2, z)) for x, z in pts]
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


# ======================================================================== Wände mit Öffnung (12.11.)
# Öffnungen als (x0, x1, z0, z1) in der Wand. Die Wand selbst ist eine Fläche mit Löchern, auf 10 cm aufgedickt:
# alle Außenkanten bleiben eben und im Raster, nur in der Öffnung sitzt eine Zarge bzw. ein Fensterrahmen.

TUER = (0.55, 1.45, 0.0, 1.9)          # Öffnung in wand_tuer: 0,9 x 1,9 m, darüber liegt der Balken (Unterkante 1,9 m)
TUER_ZARGE = 0.05                      # Zarge 5 cm: lichte Weite 0,8 x 1,85 m, Türblatt genau so groß
FENSTER = {"wand_fenster": (2.0, 2.0, (0.6, 1.4, 0.8, 1.6)),
           "wand_fenster_2x1": (2.0, 1.0, (0.5, 1.5, 0.2, 0.8)),
           "wand_fenster_1x1": (1.0, 1.0, (0.2, 0.8, 0.2, 0.8))}


def wand_loecher(m, breite, hoehe, oeffnungen, kaputt):
    """Wand breite x hoehe mit rechteckigen Öffnungen. Heil: Gitter genau an den Öffnungskanten (wenige Flächen).
    Kaputt: 5-cm-Gitter mit ausgebrochenem Loch und abgebröckelter Oberkante wie wand_flaeche()."""
    if kaputt:
        z = 0.05
        nx, nz = round(breite / z), round(hoehe / z)
        sx, sz = breite / 2, hoehe / 2
        def fehlt(i, j):
            x = (j + 0.5) * z; h = (i + 0.5) * z
            if any(o[0] <= x <= o[1] and o[2] <= h <= o[3] for o in oeffnungen):
                return True
            xr = (x - breite / 2) / sx; hr = h / sz
            kante = 1.8 - 0.4 * max(0.0, xr + 0.1) + 0.12 * noise.noise(Vector((xr * 4, 0.3, 1.1)))
            r = 0.3 + 0.08 * noise.noise(Vector((xr * 5, hr * 5, 2.7)))
            return hr > kante or ((xr - 0.6) ** 2 + ((hr - 0.55) * 1.2) ** 2) ** 0.5 < r
        xs = [j * z for j in range(nx + 1)]; zs = [i * z for i in range(nz + 1)]
    else:
        xs = sorted({0.0, breite, *[o[0] for o in oeffnungen], *[o[1] for o in oeffnungen]})
        zs = sorted({0.0, hoehe, *[o[2] for o in oeffnungen], *[o[3] for o in oeffnungen]})
        def fehlt(i, j):
            x = (xs[j] + xs[j + 1]) / 2; h = (zs[i] + zs[i + 1]) / 2
            return any(o[0] <= x <= o[1] and o[2] <= h <= o[3] for o in oeffnungen)
    gitter = [[(x, -WAND_D / 2, h) for x in xs] for h in zs]
    bm = flaeche(gitter, 0.0, fehlt)
    if kaputt:
        for v in bm.verts:
            rand = any(len(e.link_faces) < 2 for e in v.link_edges)
            aussen = v.co.z < 1e-4 or abs(v.co.x) < 1e-4 or abs(v.co.x - breite) < 1e-4
            in_oeffnung = any(o[0] - 1e-4 <= v.co.x <= o[1] + 1e-4 and o[2] - 1e-4 <= v.co.z <= o[3] + 1e-4
                              for o in oeffnungen)
            if rand and not aussen and not in_oeffnung:
                v.co.x += m.rnd.uniform(-0.02, 0.02); v.co.z += m.rnd.uniform(-0.025, 0.02)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-WAND_D)
    mitte_y(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # Außenflächen zeigen nach außen (sonst sieht man die Rückseite)
    bm.normal_update()
    m.teil(bm, "putz", None, versatz=(0, 0))
    if kaputt:
        for k in range(int(4 + 4 * breite * hoehe / 4)):
            g = m.rnd.uniform(0.05, 0.12)
            m.teil(basis.brocken(m.rnd, g * 1.5, g, g * 0.6), "putz",
                   M((m.rnd.uniform(0.1, 0.9) * breite, m.rnd.choice((-1, 1)) * m.rnd.uniform(0.12, 0.6), g * 0.3),
                     (0, 0, m.rnd.uniform(0, 180))))


EINBETTEN = 0.01   # Rahmen stecken 1 cm in der Wand: keine Fläche liegt genau auf der Laibung (sonst flackert es)


def rahmen(m, o, b, tiefe, mat="holz", unten=True, bruch=()):
    """Rahmen aus Kanthölzern innen an der Öffnung o = (x0, x1, z0, z1): Breite b in der Wandebene, Tiefe quer.
    Der Rahmen ist rundum EINBETTEN größer als die Öffnung, damit seine Außenflächen in der Wand verschwinden.
    bruch: Seiten ('l', 'r', 'o', 'u'), die abgebrochen sind."""
    e = EINBETTEN
    x0, x1, z0, z1 = o[0] - e, o[1] + e, o[2] - (e if unten else 0.0), o[3] + e
    seiten = {"l": ((x0 + b / 2, 0, z0), (x0 + b / 2, 0, z1), (1, 0, 0)),
              "r": ((x1 - b / 2, 0, z0), (x1 - b / 2, 0, z1), (1, 0, 0)),
              "o": ((x0 + b, 0, z1 - b / 2), (x1 - b, 0, z1 - b / 2), (0, 0, 1))}
    if unten:
        seiten["u"] = ((x0 + b, 0, z0 + b / 2), (x1 - b, 0, z0 + b / 2), (0, 0, 1))
    for k, (a, e, oben) in seiten.items():
        # Kantholz: Breite quer zur Wand (tiefe), Dicke in Richtung "oben" (= b, in der Wandebene)
        m.kantholz(a, e, tiefe, b, mat, oben=oben, fase=0.004, biegen=0.0, bruch=1 if k in bruch else 0)


def wand_tuer(m, kaputt):
    """2 x 2-Wand mit Türöffnung 0,9 x 1,9 m in der Mitte (x 0,55..1,45) und Zarge. Das Türblatt ist ein
    eigenes Modell (tuer) mit demselben Ursprung."""
    wand_loecher(m, 2.0, 2.0, [TUER], kaputt)
    rahmen(m, TUER, TUER_ZARGE, WAND_D + 0.04, "holz" if not kaputt else "holz_alt", unten=False,
           bruch=("r",) if kaputt else ())
    # Schwelle aus Stein, bündig mit dem Balken darunter (Oberkante 0,1 m wie der Boden)
    x0, x1 = TUER[0], TUER[1]
    m.teil(klotz(m.rnd, x1 - x0 + 2 * EINBETTEN, WAND_D + 0.1, 0.1, 0.01, 0.003, 0.6 if kaputt else 0.0), "stein",
           M(((x0 + x1) / 2, 0, 0.05)))


def tuer(m, kaputt):
    """Brettertür für wand_tuer: Ursprung wie die Wand (Rasterpunkt), Angel bei x = 0,6, Blatt 0,8 x 1,85 m in der
    Wandebene (y -0,02..0,02). Zum Öffnen um die senkrechte Achse durch (0,6 | 0) drehen."""
    x0 = TUER[0] + TUER_ZARGE; b = TUER[1] - TUER[0] - 2 * TUER_ZARGE; h = TUER[3] - TUER_ZARGE
    z0 = 0.1
    h = h - z0
    if kaputt:   # obere Angel ausgerissen: hängt schräg nach außen
        m.G = M((x0, 0, z0)) @ M(rot=(0, 0, -40)) @ M(rot=(0, -6, 0))
    else:
        m.G = M((x0, 0, z0))
    n = 5
    for i in range(n):
        x = b / n * (i + 0.5)
        if kaputt and i in (3, 4):
            laenge = (0.95, 1.25)[i - 3]
            m.brett(laenge, b / n - 0.004, 0.035, M((x, 0, laenge / 2), (0, -90, 0)) @ M(rot=(90, 0, 0)), "holz",
                    bruch=-1, bruch_tiefe=0.15)
            continue
        m.brett(h, b / n - 0.004, 0.035, M((x, 0, h / 2), (0, -90, 0)) @ M(rot=(90, 0, 0)), "holz")
    for z in (0.25, h - 0.25):
        m.kantholz((0.03, 0.03, z), (b - 0.03, 0.03, z), 0.12, 0.025, "holz", oben=(0, 1, 0))
        m.teil(quader(b * 0.7, 0.006, 0.045, fase=0.002), "eisen", M((b * 0.35, -0.021, z)))
    m.kantholz((0.08, 0.03, 0.3), (b - 0.08, 0.03, h - 0.32), 0.1, 0.025, "holz", oben=(0, 1, 0))
    m.seil([(b - 0.1, -0.02, 0.95), (b - 0.1, -0.06, 0.97), (b - 0.1, -0.06, 1.09), (b - 0.1, -0.02, 1.11)],
           0.008, 5, "eisen")
    m.G = None


def fenster_wand(m, kaputt, name):
    breite, hoehe, o = FENSTER[name]
    wand_loecher(m, breite, hoehe, [o], kaputt)
    x0, x1, z0, z1 = o
    rb = 0.05
    rahmen(m, o, rb, WAND_D + 0.03, "holz", bruch=("o",) if kaputt else ())
    # Fensterkreuz und Glas (in der Wandmitte)
    xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
    if not kaputt:
        m.kantholz((xm, 0, z0 + rb), (xm, 0, z1 - rb), 0.04, 0.035, "holz", oben=(1, 0, 0), biegen=0.0)
        m.kantholz((x0 + rb, 0, zm), (x1 - rb, 0, zm), 0.04, 0.035, "holz", oben=(0, 0, 1), biegen=0.0)
        m.teil(quader(x1 - x0 - 2 * rb, 0.006, z1 - z0 - 2 * rb), "glas", M((xm, 0, zm)))
    else:
        m.kantholz((xm, 0, z0 + rb), (xm, 0, zm + 0.08), 0.04, 0.035, "holz", oben=(1, 0, 0), bruch=1, biegen=0.0)
        # Glasscherben im Rahmen unten links
        bm = bmesh.new()
        pts = [(x0 + rb, z0 + rb), (xm - 0.02, z0 + rb), (xm - 0.05, z0 + rb + 0.12), (x0 + rb + 0.12, zm - 0.05),
               (x0 + rb, zm - 0.02)]
        bm.faces.new([bm.verts.new((x, 0, z)) for x, z in pts])
        m.teil(bm, "glas", None)
    # Fensterbank außen (vorne = -y)
    m.brett(x1 - x0 + 0.12, 0.09, 0.03, M((xm, -WAND_D / 2 - 0.035, z0 - 0.015)), "holz_alt", biegen=0.0)


def wand_fenster(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster")


def wand_fenster_2x1(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster_2x1")


def wand_fenster_1x1(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster_1x1")


def dreieck(m, kaputt, b):
    """Giebel-Dreieck b x b: Ecken (0|0), (b|0), (b|b), die Schräge liegt auf der Diagonale wie strebe_2m.
    Für die andere Giebelseite um 180° drehen (y) und um b verschieben."""
    umriss = [(0.0, 0.0), (b, 0.0), (b, b)]
    if kaputt:   # obere Spitze abgebrochen: zackige Bruchlinie von der Schräge bis zur senkrechten Kante
        za, ze = b * 0.45, b * 0.62
        punkte = []
        n = 7
        for k in range(n + 1):
            t = k / n
            x = za + (b - za) * t
            z = za + (ze - za) * t + (m.rnd.uniform(-0.06, 0.06) if 0 < k < n else 0.0)
            punkte.append((x, min(z, x)))
        umriss = [(0.0, 0.0), (b, 0.0), (b, ze)] + list(reversed(punkte))
    bm = bmesh.new()
    vorne = [bm.verts.new((x, -WAND_D / 2, z)) for x, z in umriss]
    hinten = [bm.verts.new((x, WAND_D / 2, z)) for x, z in umriss]
    bm.faces.new(vorne); bm.faces.new(list(reversed(hinten)))
    for i in range(len(umriss)):
        bm.faces.new((vorne[i], hinten[i], hinten[(i + 1) % len(umriss)], vorne[(i + 1) % len(umriss)]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m.teil(bm, "putz", None, versatz=(0, 0))
    if kaputt:
        for k in range(4):
            g = m.rnd.uniform(0.05, 0.11)
            m.teil(basis.brocken(m.rnd, g * 1.5, g, g * 0.6), "putz",
                   M((m.rnd.uniform(0.4, 0.95) * b, m.rnd.choice((-1, 1)) * m.rnd.uniform(0.12, 0.5), g * 0.3)))


def wand_dreieck(m, kaputt):
    dreieck(m, kaputt, 2.0)


def wand_dreieck_1x1(m, kaputt):
    dreieck(m, kaputt, 1.0)


# ======================================================================== Boden, Dach, Treppe
# Tiefe läuft in Blender entlang +y (in Godot nach -z, also "nach hinten" von der Wandvorderseite weg).

BODEN_OBEN = BALKEN / 2       # Dielen liegen bündig auf der Oberkante der Balken (0,1 m über der Rasterlinie)
DIELE = 0.04


def boden_flaeche(m, kaputt, b):
    """Dielenboden b x b (x 0..b, y 0..b), Oberkante 0,1 m über dem Rasterpunkt (auf den Balken)."""
    z = BODEN_OBEN - DIELE / 2
    if not kaputt:
        m.teil(quader(b, b, DIELE, int(b * 2), int(b * 2), 1), "dielen", M((b / 2, b / 2, z)), versatz=(0, 0))
        return
    n = round(b / 0.2)
    for i in range(n):
        x = 0.1 + i * 0.2
        mitte = n // 2
        if abs(i - mitte + 0.5) < 1.6:
            for s in (0, 1):
                l = m.rnd.uniform(0.3, 0.42) * b
                y = l / 2 if s == 0 else b - l / 2
                m.brett(l, 0.196, DIELE, M((x, y, z), (0, 0, 90)), "dielen", bruch=1 if s == 0 else -1,
                        bruch_tiefe=0.12, biegen=0.0)
        else:
            m.brett(b, 0.196, DIELE, M((x, b / 2, z), (0, 0, 90)), "dielen", nx=int(b * 3), biegen=0.0)
    m.brett(0.6 * b, 0.196, DIELE, M((b * 0.45, b * 0.5, z - 0.25), (18, 0, 70)), "holz_verkohlt", bruch=1)


def boden_2x2(m, kaputt):
    boden_flaeche(m, kaputt, 2.0)


def boden_1x1(m, kaputt):
    boden_flaeche(m, kaputt, 1.0)


DACH_ABSTAND = BALKEN / 2 * math.sqrt(2)   # Unterseite der Dachhaut liegt senkrecht gemessen auf den Balkenkanten
DACH_DICKE = 0.08                          # Schalung + Schindeln


def dach_platte(m, kaputt, b, lauf, y_von=None, x_von=0.0):
    """Dachfläche 45°: Traufe am Rasterpunkt (y 0 | z 0), steigt bis (y lauf | z lauf), b breit entlang x.
    Die Haut liegt auf den Balken (Unterseite 0,1 m senkrecht über der Diagonale), Enden senkrecht im Raster
    abgeschnitten: zwei Seiten treffen sich am First genau, die Traufe endet über der Wandmitte."""
    y0 = 0.0 if y_von is None else y_von
    s2 = math.sqrt(2)
    unten = DACH_ABSTAND * s2                 # senkrechter Versatz der Unterseite über der Diagonale
    oben = (DACH_ABSTAND + DACH_DICKE) * s2
    nx, ny = max(2, int(b * 4)), max(2, int((lauf - y0) * 4))
    def gitter(dz):
        return [[(x_von + b * j / nx, y0 + (lauf - y0) * i / ny, y0 + (lauf - y0) * i / ny + dz) for j in range(nx + 1)]
                for i in range(ny + 1)]
    loch = None
    if kaputt and b >= 1.0 and lauf - y0 >= 1.0:
        loch = lambda i, j: ((i - ny * 0.45) / ny * 4) ** 2 + ((j - nx * 0.4) / nx * 3.2) ** 2 < 1.2 + \
            0.6 * noise.noise(Vector((i * 0.6, j * 0.6, 0.3)))
    # Ober- und Unterseite einzeln, Ränder als senkrechte bzw. seitliche Stirnflächen
    bm = bmesh.new()
    go = [[bm.verts.new(p) for p in zeile] for zeile in gitter(oben)]
    gu = [[bm.verts.new(p) for p in zeile] for zeile in gitter(unten)]
    offen = lambda i, j: loch is not None and loch(i, j)
    for i in range(ny):
        for j in range(nx):
            if offen(i, j):
                continue
            bm.faces.new((go[i][j], go[i][j + 1], go[i + 1][j + 1], go[i + 1][j]))
            bm.faces.new((gu[i][j], gu[i + 1][j], gu[i + 1][j + 1], gu[i][j + 1]))
    # Stirnflächen: überall, wo eine Zelle an den Rand oder an ein Loch grenzt
    def zelle(i, j):
        return 0 <= i < ny and 0 <= j < nx and not offen(i, j)
    for i in range(ny):
        for j in range(nx):
            if not zelle(i, j):
                continue
            if not zelle(i - 1, j):
                bm.faces.new((go[i][j], gu[i][j], gu[i][j + 1], go[i][j + 1]))
            if not zelle(i + 1, j):
                bm.faces.new((go[i + 1][j + 1], gu[i + 1][j + 1], gu[i + 1][j], go[i + 1][j]))
            if not zelle(i, j - 1):
                bm.faces.new((go[i + 1][j], gu[i + 1][j], gu[i][j], go[i][j]))
            if not zelle(i, j + 1):
                bm.faces.new((go[i][j + 1], gu[i][j + 1], gu[i + 1][j + 1], go[i + 1][j + 1]))
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # UV in Dachrichtung: u entlang x, v die Schräge hinauf
    ku, kv = basis.kachel("schindeln")
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (p.x / ku, p.y)   # eine Kachel je Meter Lauf: Stöße zwischen Dachteilen im Raster passen genau
    m.teil(bm, "schindeln", None, uv=None)
    if loch:   # verkohlte Sparren im Loch
        for x in (b * 0.3, b * 0.65):
            a = Vector((x, y0 + 0.05, y0 + 0.05 + unten - 0.06)); e = Vector((x, lauf - 0.05, lauf - 0.05 + unten - 0.06))
            m.kantholz(a, a + (e - a) * m.rnd.uniform(0.55, 0.8), 0.08, 0.1, "holz_verkohlt", oben=(0, -1, 1), bruch=1)


def dach_2x2(m, kaputt):
    dach_platte(m, kaputt, 2.0, 2.0)


def dach_2x1(m, kaputt):
    dach_platte(m, kaputt, 2.0, 1.0)


def dach_1x2(m, kaputt):
    dach_platte(m, kaputt, 1.0, 2.0)


def dach_1x1(m, kaputt):
    dach_platte(m, kaputt, 1.0, 1.0)


def dach_traufe(m, kaputt):
    """Dachüberstand 2 m breit: setzt die Dachfläche an der Traufe 0,5 m nach außen (y -0,5..0) fort.
    Gleicher Ursprung wie dach_*: am Traufpunkt einfach dazusetzen."""
    dach_platte(m, False, 2.0 if not kaputt else 1.2, 0.0, y_von=-0.5)



def windbrett(m, x, y_von, y_bis, kaputt):
    """Windbrett an der Außenkante des Ortgangs: hochkant, folgt der Schräge. Sitzt AUSSEN vor der Dachkante,
    damit keine seiner Flächen auf der Stirnseite des Dachs liegt (sonst flackert es zwischen Holz und Schindeln).
    UVs hängen an der Lage im Raster (u = (y + z) / 2: eine Kachel je Meter Steigung), damit die Maserung
    an den Stößen zwischen Ecke, kurzem und langem Überstand und zwischen gestapelten Teilen durchläuft."""
    c = (DACH_ABSTAND + DACH_DICKE / 2) * math.sqrt(2) - 0.07
    mat = "holz_alt" if not kaputt else "holz_verkohlt"
    if kaputt:
        y_bis = y_von + (y_bis - y_von) * 0.55
    a = Vector((x, y_von, y_von + c)); b = Vector((x, y_bis, y_bis + c))
    bm = quader((b - a).length, 0.025, 0.24, max(1, int((b - a).length / 0.5)), 1, 1)
    if kaputt:
        bruchkante(bm, m.rnd, 1, 0.1)
    bm.transform(basis.ausrichten(a, b, (0, -1, 1)))
    bm.normal_update()
    ku, kv = basis.kachel(mat)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            u = (p.y + p.z) / 2.0 if ku else 0.0
            v = ((p.z - p.y) / math.sqrt(2) + (p.x if abs(f.normal.x) < 0.5 else 0.0)) / kv
            l[uv].uv = (u, v)
    m.teil(bm, mat, None, uv=None)


ORTGANG = 0.5          # seitlicher Dachüberstand


def ortgang(m, kaputt, lauf, seite):
    """Seitlicher Dachüberstand (Ortgang) 0,5 m: setzt die Dachfläche über die Giebelwand hinaus fort.
    seite -1 (links): x -0,5..0, seite +1 (rechts): x 0..0,5. Ursprung wie das Dach (Traufpunkt am Giebel)."""
    x0 = -ORTGANG if seite < 0 else 0.0
    bis = lauf if not kaputt else lauf * 0.6
    dach_platte(m, False, ORTGANG, bis, x_von=x0)
    windbrett(m, seite * (ORTGANG + 0.0125), 0.0, lauf, kaputt)


def dach_ortgang_l(m, kaputt):
    ortgang(m, kaputt, 2.0, -1)


def dach_ortgang_r(m, kaputt):
    ortgang(m, kaputt, 2.0, 1)


def dach_ortgang_1m_l(m, kaputt):
    ortgang(m, kaputt, 1.0, -1)


def dach_ortgang_1m_r(m, kaputt):
    ortgang(m, kaputt, 1.0, 1)


def dach_ecke(m, kaputt, seite):
    """Ecke zwischen Traufe und Ortgang (0,5 x 0,5 m, außen vor dem Traufpunkt)."""
    x0 = -ORTGANG if seite < 0 else 0.0
    if not kaputt:
        dach_platte(m, False, ORTGANG, 0.0, y_von=-0.5, x_von=x0)
    windbrett(m, seite * (ORTGANG + 0.0125), -0.5, 0.0, kaputt)


def dach_ecke_l(m, kaputt):
    dach_ecke(m, kaputt, -1)


def dach_ecke_r(m, kaputt):
    dach_ecke(m, kaputt, 1)


def dach_first(m, kaputt):
    """Firstabdeckung 2 m: zwei Bretter über dem First. Ursprung am First-Rasterpunkt (y 0 | z 0 = Spitze der
    Diagonalen); die Dachflächen beider Seiten treffen sich darüber."""
    spitze = (DACH_ABSTAND + DACH_DICKE) * math.sqrt(2)
    for s in (-1, 1):
        rot = M(rot=(-s * 45, 0, 0))
        if kaputt and s > 0:
            m.brett(1.1, 0.24, 0.03, M((0.55, 0, spitze + 0.01)) @ rot @ M((0, s * 0.11, 0)), "holz_verkohlt", bruch=1)
            continue
        m.brett(2.0, 0.24, 0.03, M((1.0, 0, spitze + 0.01)) @ rot @ M((0, s * 0.11, 0)), "holz_alt")


STUFEN = 5                    # Treppe: 1 m hoch auf 2 m Lauf, Stufen 20 cm hoch, 40 cm tief


def treppe_holz(m, kaputt):
    """Holztreppe 1 m breit (x 0..1), läuft von y 0 nach y 2 und steigt um 1 m: vom Boden (0,1) bis zum Boden
    des nächsten Meters (1,1). Stapelbar für höhere Stockwerke (eine Stufe = 20 cm)."""
    h = 0.2; t = 0.4
    for x in (0.03, 0.97):
        a = Vector((x, 0.0, BODEN_OBEN)); e = Vector((x, 2.0, 1.0 + BODEN_OBEN))
        m.kantholz(a + Vector((0, 0.05, -0.08)), e + Vector((0, 0, -0.12)), 0.06, 0.26, "holz", oben=(0, -1, 2),
                   bruch=1 if kaputt and x > 0.5 else 0)
    for i in range(STUFEN):
        y = (i + 0.5) * t; z = BODEN_OBEN + (i + 1) * h
        if kaputt and i in (1, 3):
            if i == 3:
                m.brett(0.4, t - 0.02, 0.04, M((0.25, y, z - 0.02)), "holz", bruch=1)
            continue
        m.brett(0.94, t - 0.004, 0.04, M((0.5, y, z - 0.02)), "holz" if not (kaputt and i == 4) else "holz_verkohlt",
                biegen=0.0)
        if not (kaputt and i == 2):
            m.brett(0.94, h - 0.04, 0.02, M((0.5, y - t / 2 + 0.012, z - h / 2 - 0.02), (90, 0, 0)), "holz", biegen=0.0)
    if kaputt:
        m.brett(0.7, t - 0.02, 0.04, M((0.6, -0.4, 0.04), (0, 0, 30)), "holz", bruch=-1)


def treppe_stein(m, kaputt):
    """Massive Steintreppe, gleiche Maße wie treppe_holz (1 m breit, 2 m Lauf, 1 m Steigung), Blöcke bis zum Boden."""
    h = 0.2; t = 0.4
    for i in range(STUFEN):
        z1 = BODEN_OBEN + (i + 1) * h; y0 = i * t
        if kaputt and i == 4:
            m.teil(klotz(m.rnd, 0.95, t, h, 0.02, 0.008, 1.0), "stein", M((1.3, 0.6, h / 2), (m.rnd.uniform(-6, 6), 0, 25)))
            continue
        hoch = z1 if i == 0 else h
        m.teil(klotz(m.rnd, 1.0, t if i < STUFEN - 1 else t, hoch, 0.012, 0.003, 0.5 if kaputt else 0.0), "stein",
               M((0.5, y0 + t / 2, z1 - hoch / 2)))
        if i > 0:   # Unterbau bis zum Boden
            m.teil(klotz(m.rnd, 1.0, t, z1 - h, 0.01, 0.002, 0.0), "stein", M((0.5, y0 + t / 2, (z1 - h) / 2)))


MODELLE = {"wand": wand, "wand_2x1": wand_2x1, "wand_1x1": wand_1x1, "balken_2m": balken_2m, "balken_1m": balken_1m,
           "strebe_2m": strebe_2m, "wand_tuer": wand_tuer, "tuer": tuer, "wand_fenster": wand_fenster,
           "wand_fenster_2x1": wand_fenster_2x1, "wand_fenster_1x1": wand_fenster_1x1, "wand_dreieck": wand_dreieck,
           "wand_dreieck_1x1": wand_dreieck_1x1, "boden_2x2": boden_2x2, "boden_1x1": boden_1x1,
           "dach_2x2": dach_2x2, "dach_2x1": dach_2x1, "dach_1x2": dach_1x2, "dach_1x1": dach_1x1,
           "dach_traufe": dach_traufe, "dach_first": dach_first, "dach_ortgang_l": dach_ortgang_l,
           "dach_ortgang_r": dach_ortgang_r, "dach_ortgang_1m_l": dach_ortgang_1m_l, "dach_ortgang_1m_r": dach_ortgang_1m_r,
           "dach_ecke_l": dach_ecke_l, "dach_ecke_r": dach_ecke_r, "treppe_holz": treppe_holz, "treppe_stein": treppe_stein}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
