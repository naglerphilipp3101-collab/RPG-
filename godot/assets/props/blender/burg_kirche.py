"""Burg- und Kirchen-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python burg_kirche.py -- <zielordner/modelle> [--nur thron,altar] [--vorschau <ordner>]

  thron             Holzthron mit hoher Lehne und Polster auf einem Steinpodest mit zwei Stufen
  wandteppich       Wandteppich an einer Stange mit Wandhaken (Ursprung: Boden an der Wand, Wand bei y = 0, ragt nach -y)
  kronleuchter      eiserner Ringleuchter mit Kerzen an drei Ketten (Ursprung = Deckenhaken, hängt 1,2 m tief)
  altar             Steinaltar mit Tuch, Leuchtern, Buchpult und Sonnenscheibe
  kirchenbank       Kirchenbank mit Lehne und Wangen (2,4 m)
  weihwasserbecken  Steinbecken auf einer Säule
  statue            Steinstatue einer Heldin mit Schwert auf einem Sockel
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, klotz, verbiegen, ausrichten
import props
import deko
from kueche import haufen, ellipsoid
from taverne import kissen, decke_liegend


def splitter(m, mitte, n, weite, mat="stein", gross=(0.02, 0.06)):
    for k in range(n):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.05, weite)
        g = m.rnd.uniform(*gross)
        m.teil(brocken(m.rnd, g, g * 0.8, g * 0.5, 0.3, 1), mat, M((mitte[0] + d * math.cos(a), mitte[1] + d * math.sin(a), g * 0.3)))


# ======================================================================== Thron

def thron(m, kaputt):
    # Podest: zwei Stufen aus Steinblöcken
    for k, (b, t, h) in enumerate(((2.2, 2.0, 0.2), (1.6, 1.5, 0.2))):
        z = 0.1 + 0.2 * k
        bm = klotz(m.rnd, b, t, h, 0.02, 0.006, abgeschlagen=0.6 if kaputt else 0.0)
        m.teil(bm, "stein", M((0, 0.15 * k, z)))
    z0 = 0.4
    y0 = 0.25
    sitz_h = 0.5
    # Beine, Sitz, Armlehnen
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.kantholz((sx * 0.38, y0 + sy * 0.28, z0), (sx * 0.38, y0 + sy * 0.28, z0 + sitz_h + (0.3 if sy < 0 else 0)), 0.09, 0.09)
        m.kantholz((sx * 0.38, y0 - 0.38, z0 + sitz_h + 0.3), (sx * 0.38, y0 + 0.3, z0 + sitz_h + 0.3), 0.1, 0.07)
        m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.05, 0.03), (0.0, 0.1)], 8), "fahne_gold", M((sx * 0.38, y0 - 0.38, z0 + sitz_h + 0.33)))
    m.brett(0.86, 0.66, 0.06, M((0, y0, z0 + sitz_h)), "holz")
    # hohe Lehne mit Spitzbogen-Abschluss und Goldscheibe
    lehne = M((0, y0 + 0.31, z0 + sitz_h))
    if not kaputt:
        for sx in (-1, 1):
            m.kantholz(lehne @ Vector((sx * 0.38, 0, 0)), lehne @ Vector((sx * 0.38, 0, 1.45)), 0.1, 0.1)
            m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.0, 0.14)], 8), "fahne_gold", lehne @ M((sx * 0.38, 0, 1.45)))
        m.brett(0.66, 0.05, 1.2, lehne @ M((0, 0, 0.62), (0, 0, 0)), "holz")
        dach = bmesh.new()
        pts = [(-0.33, 1.22), (0.33, 1.22), (0.0, 1.55)]
        vo = [dach.verts.new((x, -0.025, z)) for x, z in pts]; hi = [dach.verts.new((x, 0.025, z)) for x, z in pts]
        dach.faces.new(vo); dach.faces.new(list(reversed(hi)))
        for i in range(3):
            dach.faces.new((vo[i], vo[(i + 1) % 3], hi[(i + 1) % 3], hi[i]))
        bmesh.ops.recalc_face_normals(dach, faces=dach.faces[:])
        m.teil(dach, "holz", lehne)
        m.teil(drehkoerper([(0.0, 0.0), (0.16, 0.0), (0.16, 0.02), (0.0, 0.025)], 20), "fahne_gold", lehne @ M((0, -0.03, 0.9), (90, 0, 0)))
        kissen(m, M((0, y0 - 0.02, z0 + sitz_h + 0.03)), 0.72, 0.56, 0.1, "wolle_rot")
        kissen(m, lehne @ M((0, -0.08, 0.5), (90, 0, 0)), 0.6, 0.7, 0.08, "wolle_rot")
        # Teppichläufer vor den Stufen
        m.teil(quader(0.9, 1.0, 0.01), "wolle_rot", M((0, -1.5, 0.005)))
        return
    # Lehne abgebrochen und nach vorn über die Stufen gestürzt, Polster aufgerissen, Goldzier gestohlen
    for sx in (-1, 1):
        m.kantholz(lehne @ Vector((sx * 0.38, 0, 0)), lehne @ Vector((sx * 0.38, 0, 0.35)), 0.1, 0.1, bruch=1)
    m.brett(0.66, 0.05, 0.3, lehne @ M((0, 0, 0.15)), "holz", bruch=1)
    gestuerzt = M((0.3, -1.75, 0.05), (0, 0, 18)) @ M(rot=(90, 0, 0))
    for sx in (-1, 1):
        m.kantholz(gestuerzt @ Vector((sx * 0.38, 0, 0)), gestuerzt @ Vector((sx * 0.38, 0, 1.0)), 0.1, 0.1, bruch=-1)
    m.brett(0.66, 0.05, 0.95, gestuerzt @ M((0, 0.0, 0.48)), "holz", bruch=-1)
    decke_liegend(m, M((0.05, y0, z0 + sitz_h + 0.03)), 0.7, 0.55, m.rnd, hoch=0.04, loch=lambda i, j: (i * 7 + j * 3) % 11 == 0)
    splitter(m, (-0.4, -1.2), 8, 0.6)


# ======================================================================== Wandteppich

def wandteppich(m, kaputt):
    zo = 2.55
    for x in (-0.65, 0.65):
        if kaputt and x > 0:
            m.teil(quader(0.04, 0.03, 0.08), "eisen", M((x, -0.015, zo)))         # Haken abgebrochen
            continue
        m.teil(quader(0.04, 0.03, 0.08), "eisen", M((x, -0.015, zo)))
        m.seil([(x, -0.03, zo), (x, -0.08, zo + 0.02), (x, -0.08, zo + 0.06)], 0.008, 5, "eisen")
    nx, ny = 20, 28
    g = []
    for i in range(ny + 1):
        t = i / ny
        zeile = []
        for j in range(nx + 1):
            s = j / nx
            # lokal: x = Höhe (Teppich-Textur 2,0 lang), y = Breite (1,4), z = Falten
            lx = -1.0 + 2.0 * s; ly = -0.7 + 1.4 * t
            lz = 0.012 * math.sin(t * 22) * (0.4 + 0.6 * (1 - s))
            zeile.append((lx, ly, lz))
        g.append(zeile)
    loch = None
    if kaputt:
        loch = lambda i, j: (math.hypot(j - 7, i - 9) < 3.0 + math.sin(i * 1.3 + j)) or (j < 2 and i % 3 == 0) or \
            (math.hypot(j - 15, i - 20) < 2.2)
    bm = flaeche(g, 0.006, loch)
    # Lage: Textur-x wird senkrecht (oben bei x = +1), y waagerecht, z zeigt von der Wand weg
    if not kaputt:
        lage = Matrix.Translation((0, -0.09, zo - 1.03)) @ Matrix(((0, 1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
    else:
        # rechte Seite heruntergerutscht: hängt schräg nur noch am linken Haken
        lage = Matrix.Translation((-0.65, -0.09, zo)) @ Matrix.Rotation(math.radians(-28), 4, "Y") @ \
            Matrix.Translation((0.65, 0, -1.03)) @ Matrix(((0, 1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
    m.teil(bm, "teppich", lage, versatz=(0.5, 0.5))
    stange = (Vector((-0.78, -0.08, zo + 0.02)), Vector((0.78, -0.08, zo + 0.02)))
    if kaputt:
        r = Matrix.Translation((-0.65, -0.08, zo + 0.02)) @ Matrix.Rotation(math.radians(-28), 4, "Y") @ Matrix.Translation((0.65, 0.08, -zo - 0.02))
        stange = (r @ stange[0], r @ stange[1])
        # verkohlter Rand unten links
        for k in range(4):
            m.teil(ellipsoid(0.06, 0.004, 0.03, 1), "holz_verkohlt", lage @ M((-0.95, -0.4 + 0.2 * k, 0.005)))
    m.stab(tuple(stange[0]), tuple(stange[1]), 0.02, "holz", biegen=0)
    for p in stange:
        m.teil(drehkoerper([(0.0, -0.03), (0.03, 0.0), (0.0, 0.03)], 8), "fahne_gold", Matrix.Translation(p) @ M(rot=(0, 90, 0)))


# ======================================================================== Kronleuchter

def kronleuchter(m, kaputt):
    tief = 1.2
    r = 0.55
    m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.05, -0.01), (0.0, -0.015)], 8), "eisen", None)
    # Hauptkette zum Ring der drei Ketten
    glieder = 10
    for k in range(glieder):
        z = -0.03 - k * 0.055
        g = [(0.015 * math.cos(2 * math.pi * i / 10), 0.0, z - 0.03 + 0.03 * math.sin(2 * math.pi * i / 10) * 1.3) for i in range(11)]
        m.seil(g if k % 2 == 0 else [(0.0, p[0], p[2]) for p in g], 0.004, 4, "eisen")
    knoten = Vector((0, 0, -0.03 - glieder * 0.055))
    m.teil(drehkoerper([(0.0, -0.02), (0.03, 0.0), (0.0, 0.02)], 8), "eisen", Matrix.Translation(knoten))
    neig = Matrix.Identity(4) if not kaputt else (Matrix.Translation(knoten) @ Matrix.Rotation(math.radians(24), 4, "X") @
                                                  Matrix.Translation(-knoten))
    mitte = Vector((0, 0, -tief))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        ende = neig @ (mitte + Vector((r * math.cos(a), r * math.sin(a), 0.0)))
        if kaputt and k == 1:
            # gerissene Kette baumelt
            m.seil([tuple(knoten), tuple(knoten + (ende - knoten) * 0.35 + Vector((0.0, 0.0, -0.05)))], 0.004, 4, "eisen")
            continue
        m.seil([tuple(knoten), tuple(ende)], 0.004, 4, "eisen")
    ring = [tuple(neig @ (mitte + Vector((r * math.cos(2 * math.pi * k / 32), r * math.sin(2 * math.pi * k / 32), 0.0)))) for k in range(33)]
    m.seil(ring, 0.02, 6, "eisen")
    ring2 = [tuple(neig @ (mitte + Vector(((r - 0.07) * math.cos(2 * math.pi * k / 32), (r - 0.07) * math.sin(2 * math.pi * k / 32), 0.04)))) for k in range(33)]
    m.seil(ring2, 0.008, 5, "eisen")
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        p = neig @ (mitte + Vector((r * math.cos(a), r * math.sin(a), 0.02)))
        rot = neig.to_3x3().to_4x4()
        m.teil(drehkoerper([(0.0, 0.0), (0.04, 0.0), (0.045, 0.015), (0.0, 0.012)], 8), "eisen", Matrix.Translation(p) @ rot)
        if kaputt and k % 3 == 0:
            continue
        deko.kerze(m, Matrix.Translation(p + rot.to_3x3() @ Vector((0, 0, 0.012))) @ rot, 0.12 if not kaputt else 0.05, brennt=not kaputt)


# ======================================================================== Altar

def altar(m, kaputt):
    B, T, H = 1.8, 0.8, 1.0
    m.teil(klotz(m.rnd, B + 0.3, T + 0.3, 0.15, 0.02, 0.006, 0.5 if kaputt else 0.0), "stein", M((0, 0, 0.075)))
    m.teil(klotz(m.rnd, B, T, H - 0.25, 0.02, 0.006, 0.8 if kaputt else 0.0), "stein", M((0, 0, 0.15 + (H - 0.25) / 2)))
    m.teil(klotz(m.rnd, B + 0.12, T + 0.12, 0.1, 0.02, 0.006, 0.4 if kaputt else 0.0), "stein", M((0, 0, H - 0.05)))
    # Altartuch: oben flach, vorn herabhängend
    if not kaputt:
        g = []
        for i in range(7):
            t = i / 6
            zeile = []
            for j in range(13):
                x = -0.75 + 1.5 * j / 12
                if t < 0.65:
                    zeile.append((x, T / 2 + 0.06 - (T + 0.12) * t / 0.65, H + 0.003))
                else:
                    zeile.append((x, -T / 2 - 0.062, H - (t - 0.65) / 0.35 * 0.45))
            g.append(zeile)
        m.teil(flaeche(g, 0.004), "fahne_weiss", None)
        m.teil(quader(1.5, 0.006, 0.06), "fahne_gold", M((0, -T / 2 - 0.066, H - 0.42)))
    else:
        g = [[(x, -T / 2 - 0.4 + 0.3 * t, 0.003 + 0.02 * math.sin(x * 9 + t * 4) ** 2) for x in (-0.75 + 1.5 * j / 12 for j in range(13))]
             for t in (i / 6 for i in range(7))]
        m.teil(flaeche(g, 0.004, lambda i, j: (i + 2 * j) % 7 == 0), "fahne_weiss", M((0.1, 0, 0), (0, 0, 8)))
    # Leuchter, Buchpult, Sonnenscheibe
    for sx in (-1, 1):
        if kaputt and sx == 1:
            leuchter(m, M((0.65, -0.8, 0.09), (0, 84, -40)), brennt=False)
            continue
        leuchter(m, M((sx * 0.7, 0.0, H + (0.0 if not kaputt else 0.0))), brennt=not kaputt)
    if not kaputt:
        m.teil(quader(0.32, 0.24, 0.03, fase=0.005), "holz", M((0.0, -0.1, H + 0.1), (20, 0, 0)))
        m.kantholz((0, -0.05, H), (0, -0.05, H + 0.09), 0.04, 0.04)
        deko.buch(m, M((0.0, -0.1, H + 0.12), (20, 0, 0)), 0.26, 0.19, 0.03)
        m.stab((0, 0.25, H), (0, 0.25, H + 0.55), 0.02, "fahne_gold", biegen=0)
        sonne(m, M((0, 0.25, H + 0.75), (90, 0, 0)))
        return
    sonne(m, M((-0.5, -0.9, 0.012), (0, 0, 20)))
    splitter(m, (0.5, -0.6), 10, 0.5)


def leuchter(m, matrix, brennt=True):
    m.teil(drehkoerper([(0.0, 0.0), (0.09, 0.0), (0.07, 0.03), (0.02, 0.05), (0.015, 0.4), (0.04, 0.42), (0.05, 0.45), (0.0, 0.44)], 12),
           "fahne_gold", matrix)
    deko.kerze(m, matrix @ M((0, 0, 0.44)), 0.18, brennt=brennt)


def sonne(m, matrix):
    m.teil(drehkoerper([(0.0, 0.0), (0.12, 0.0), (0.12, 0.02), (0.0, 0.025)], 24), "fahne_gold", matrix)
    for k in range(12):
        a = 2 * math.pi * k / 12
        m.teil(quader(0.12, 0.025 if k % 2 else 0.04, 0.012), "fahne_gold",
               matrix @ M((0.18 * math.cos(a), 0.18 * math.sin(a), 0.01), (0, 0, math.degrees(a))))


# ======================================================================== Kirchenbank

def kirchenbank(m, kaputt):
    L = 2.4
    teile = [(-L / 2, L / 2)] if not kaputt else [(-L / 2, -0.05), (0.05, L / 2)]
    for k, (x0, x1) in enumerate(teile):
        gebrochen = kaputt and k == 1
        if gebrochen:
            # rechte Hälfte: Sitz und Lehne in der Mitte gebrochen, das Bruchende liegt am Boden
            drehpunkt = Vector((x1, 0, 0))
            w = math.atan2(0.45, x1 - x0)
            m.G = Matrix.Translation(drehpunkt) @ Matrix.Rotation(w, 4, Vector((0, 1, 0))) @ Matrix.Translation(-drehpunkt)
        l = x1 - x0; xm = (x0 + x1) / 2
        m.brett(l, 0.38, 0.04, M((xm, 0, 0.45)), "holz", bruch=(0 if not kaputt else (1 if k == 0 else -1)))
        m.brett(l, 0.03, 0.42, M((xm, 0.2, 0.75), (-8, 0, 0)), "holz", bruch=(0 if not kaputt else (1 if k == 0 else -1)))
        m.brett(l, 0.06, 0.04, M((xm, 0.2, 0.98)), "holz", bruch=(0 if not kaputt else (1 if k == 0 else -1)))
        m.G = None
    # Wangen an beiden Enden (Brett mit Rundung oben), unten Querleiste
    for s in (-1, 1):
        x = s * (L / 2 + 0.02)
        bm = quader(0.05, 0.55, 1.0, 1, 4, 6)
        for v in bm.verts:
            if v.co.z > 0.25 and v.co.y < 0:
                v.co.z -= (0.25 + 0.0) * ((v.co.z - 0.25) / 0.25) * (-v.co.y / 0.275) * 0.9
        m.teil(bm, "holz", M((x, 0.05, 0.5)))
    if not kaputt:
        m.kantholz((-L / 2, 0.05, 0.1), (L / 2, 0.05, 0.1), 0.06, 0.06)
        # Kniebank hinten für die nächste Reihe
        m.brett(L, 0.14, 0.04, M((0, 0.4, 0.15)), "holz")
    else:
        m.kantholz((-L / 2, 0.05, 0.1), (-0.1, 0.05, 0.1), 0.06, 0.06, bruch=1)
        m.kantholz((0.3, -0.55, 0.03), (1.1, -0.65, 0.03), 0.06, 0.06, bruch=-1)


# ======================================================================== Weihwasserbecken

BECKEN = [(0.0, 0.0), (0.18, 0.0), (0.3, 0.1), (0.38, 0.22), (0.4, 0.26), (0.36, 0.26), (0.33, 0.21), (0.2, 0.1), (0.0, 0.09)]


def weihwasserbecken(m, kaputt):
    m.teil(drehkoerper([(0.0, 0.0), (0.32, 0.0), (0.32, 0.08), (0.26, 0.12), (0.0, 0.12)], 8), "stein", None, uv="zylz", r=0.32)
    m.teil(drehkoerper([(0.0, 0.0), (0.12, 0.0), (0.1, 0.4), (0.12, 0.55), (0.18, 0.62), (0.0, 0.62)], 12), "stein", M((0, 0, 0.12)),
           uv="zylz", r=0.15)
    zb = 0.72
    if not kaputt:
        bm = drehkoerper(BECKEN, 24, False, False)
        verbiegen(bm, m.rnd, 0.004, 0.1)
        m.teil(bm, "stein", M((0, 0, zb)), uv="zylz", r=0.4)
        m.teil(drehkoerper([(0.0, 0.0), (0.33, 0.0), (0.0, 0.001)], 24), "wasser", M((0, 0, zb + 0.2)), uv=None)
        return
    # Becken zur Hälfte abgeschlagen, das Stück liegt am Boden, leer
    m.teil(drehkoerper(BECKEN, 16, False, False, winkel=(-10, 220)), "stein", M((0, 0, zb)), uv="zylz", r=0.4)
    m.teil(drehkoerper(BECKEN, 8, False, False, winkel=(230, 330)), "stein", M((0.55, -0.15, 0.24), (0, 92, 30)) @ M((0, 0, -0.2)),
           uv="zylz", r=0.4)
    splitter(m, (0.2, -0.3), 9, 0.5)


# ======================================================================== Statue

def figur(m, matrix, kopf=True, arm=True, schwert=True):
    """Stilisierte Heldin im langen Gewand, beide Hände auf dem Schwertknauf (Schwert zeigt nach unten)."""
    robe = drehkoerper([(0.0, 0.0), (0.34, 0.0), (0.3, 0.3), (0.22, 0.8), (0.2, 1.1), (0.22, 1.3), (0.18, 1.42), (0.08, 1.5), (0.0, 1.5)], 20)
    for v in robe.verts:
        v.co.y *= 0.72
        v.co.x *= 1 + 0.05 * math.sin(math.atan2(v.co.y, v.co.x) * 8) * (1 - v.co.z / 1.5)
    verbiegen(robe, m.rnd, 0.01, 0.2)
    m.teil(robe, "stein", matrix, uv="zylz", r=0.3)
    # Umhang hinten
    umhang = drehkoerper([(0.25, 0.0), (0.24, 0.6), (0.22, 1.1), (0.2, 1.4)], 10, False, False, winkel=(20, 160))
    for v in umhang.verts:
        v.co.y = v.co.y * 0.6 + 0.04
    bmesh.ops.solidify(umhang, geom=umhang.faces[:], thickness=0.02)
    m.teil(umhang, "stein", matrix, uv="zylz", r=0.25)
    if kopf:
        m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.055, 0.08)], 8), "stein", matrix @ M((0, 0, 1.48)))
        k = ellipsoid(0.1, 0.11, 0.13, 2)
        m.teil(k, "stein", matrix @ M((0, 0.0, 1.66)))
        haar = ellipsoid(0.11, 0.12, 0.1, 2)
        m.teil(haar, "stein", matrix @ M((0, 0.03, 1.7)))
    # Arme: Schulter -> Ellbogen -> Hände vor dem Bauch
    haende = Vector((0, -0.24, 1.0))
    for s in (-1, 1):
        if not arm and s == 1:
            m.teil(drehkoerper([(0.0, 0.0), (0.06, 0.0), (0.05, 0.05), (0.0, 0.06)], 8), "stein", matrix @ M((s * 0.24, 0, 1.36), (0, s * 90, 0)))
            continue
        schulter = Vector((s * 0.22, 0.0, 1.36)); ell = Vector((s * 0.24, -0.08, 1.1))
        m.teil(rohr([tuple(schulter), tuple(ell), tuple(haende + Vector((s * 0.05, 0, 0.0)))], 0.055, 8), "stein", matrix, uv=None)
    m.teil(ellipsoid(0.08, 0.06, 0.06, 1), "stein", matrix @ M(tuple(haende)))
    if schwert:
        m.teil(quader(0.22, 0.04, 0.04), "stein", matrix @ M((0, -0.25, 0.93)))
        m.teil(rundholz(0.022, 0.12, 8), "stein", matrix @ M((0, -0.25, 1.0), (0, 90, 0)))
        bm = quader(0.08, 0.03, 0.85, 1, 1, 4)
        for v in bm.verts:
            if v.co.z < -0.4:
                v.co.x *= 0.1
        m.teil(bm, "stein", matrix @ M((0, -0.27, 0.48)))


def statue(m, kaputt):
    # Sockel
    m.teil(klotz(m.rnd, 0.95, 0.95, 0.2, 0.02, 0.005, 0.5 if kaputt else 0.0), "stein", M((0, 0, 0.1)))
    m.teil(klotz(m.rnd, 0.8, 0.8, 0.6, 0.02, 0.005, 0.6 if kaputt else 0.0), "stein", M((0, 0, 0.5)))
    m.teil(klotz(m.rnd, 0.9, 0.9, 0.12, 0.02, 0.005, 0.5 if kaputt else 0.0), "stein", M((0, 0, 0.86)))
    m.teil(quader(0.5, 0.01, 0.08), "fahne_gold", M((0, -0.405, 0.55)))
    if not kaputt:
        figur(m, M((0, 0, 0.92)))
        return
    # Kopf und rechter Arm abgeschlagen, Schwertklinge gebrochen; Trümmer am Boden
    figur(m, M((0, 0, 0.92)), kopf=False, arm=False, schwert=False)
    m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.055, 0.05), (0.0, 0.06)], 8), "stein", M((0, 0, 0.92 + 1.48)))
    m.teil(quader(0.22, 0.04, 0.04), "stein", M((0, -0.25, 0.92 + 0.93)))
    kopf = ellipsoid(0.1, 0.11, 0.13, 2)
    m.teil(kopf, "stein", M((0.55, -0.6, 0.1), (70, 0, 30)))
    m.teil(rohr([(0.0, 0.0, 0.055), (0.26, 0.06, 0.055), (0.48, -0.05, 0.055)], 0.055, 8), "stein", M((-0.85, -0.5, 0.0)), uv=None)
    bm = quader(0.08, 0.03, 0.5, 1, 1, 3)
    m.teil(bm, "stein", M((0.2, -0.85, 0.015), (90, 0, 70)))
    splitter(m, (0.0, -0.55), 12, 0.6)


MODELLE = {"thron": thron, "wandteppich": wandteppich, "kronleuchter": kronleuchter, "altar": altar, "kirchenbank": kirchenbank,
           "weihwasserbecken": weihwasserbecken, "statue": statue}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
