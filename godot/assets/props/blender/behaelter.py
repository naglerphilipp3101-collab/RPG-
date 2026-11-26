"""Vorratsbehälter für die POIs der Karte. Jedes Modell gibt es voll (<name>.glb, geschlossen, Vorräte sichtbar)
und geplündert (<name>_kaputt.glb, offen und leer). Im Spiel tauscht der Behälter nach dem Öffnen auf die
geplünderte Fassung und füllt sich nach einem Spieltag wieder.
Aufruf: python behaelter.py -- <zielordner/modelle> [--nur vorratskiste,grubenlore] [--vorschau <ordner>]

  vorratskiste        Dörfer, Höfe: Kiste mit Seilgriffen und Riegel, Kornsack, Korb mit Äpfeln
  versorgungswagen    Militärlager, Forts: Handkarren mit Kisten und Fass unter einer verschnürten Plane
  grubenlore          Minen: eisenbeschlagene Holzlore auf vier Eisenrädern mit Säcken, Seil und Laterne
  fischerkorb         Strand: Weidenkorb mit Deckel und Tragriemen, Netz und Schwimmer
  schatzkiste_klein   Burgen: Truhe mit gewölbtem Deckel, Eisenbändern und Vorhängeschloss
Boden bei z = 0, Mitte im Ursprung, Vorderseite (Schloss, Riegel) zeigt nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, verbiegen
import props
from props import bretterwand, boden_setzen, laterne_koerper, rad


# ======================================================================== Kleinteile

def sack(m, matrix, h=0.55, r=0.2, leer=False):
    """Kornsack, oben mit Seil abgebunden. leer: zusammengesunken und flach."""
    if not leer:
        prof = [(0.0, 0.0), (r * 0.75, 0.005), (r * 0.98, 0.06), (r, h * 0.35), (r * 0.92, h * 0.7),
                (r * 0.45, h * 0.86), (r * 0.17, h * 0.9), (r * 0.2, h * 0.95), (r * 0.3, h), (0.0, h * 1.01)]
    else:
        prof = [(0.0, 0.0), (r * 1.2, 0.004), (r * 1.3, 0.03), (r * 1.1, 0.07), (r * 0.6, 0.09), (0.0, 0.095)]
    bm = drehkoerper(prof, 16)
    verbiegen(bm, m.rnd, 0.03 if not leer else 0.02, 0.15)
    verbiegen(bm, m.rnd, 0.01, 0.05)
    m.teil(bm, "stoff", matrix, uv="zylz", r=r)
    if not leer:
        z = h * 0.885
        ring = [(r * 0.19 * math.cos(a), r * 0.19 * math.sin(a), z) for a in
                (2 * math.pi * k / 10 for k in range(11))]
        bm = rohr(ring, 0.008, 5)
        m.teil(bm, "seil", matrix, uv="rohr", r=0.008, seg=5)


def apfel(m, matrix, r=0.04):
    prof = [(0.0, -r * 0.82), (r * 0.6, -r * 0.75), (r * 0.98, -r * 0.2), (r, r * 0.2), (r * 0.75, r * 0.72),
            (r * 0.2, r * 0.8), (0.0, r * 0.68)]
    bm = drehkoerper(prof, 10)
    verbiegen(bm, m.rnd, r * 0.08, r * 1.5)
    m.teil(bm, "obst", matrix, uv="zylz", r=r)


def korb(m, matrix, r_unten=0.15, r_oben=0.2, h=0.18, wand=0.012, henkel=True):
    """Offener Weidenkorb mit Randwulst und Henkel."""
    prof = [(0.0, 0.0), (r_unten, 0.0), (r_oben, h), (r_oben - wand, h), (r_unten - wand, wand), (0.0, wand)]
    bm = drehkoerper(prof, 24, False, False)
    m.teil(bm, "weide", matrix, uv="zylz", r=r_oben)
    rand = [(r_oben * math.cos(a), r_oben * math.sin(a), h) for a in (2 * math.pi * k / 24 for k in range(25))]
    m.teil(rohr(rand, 0.012, 6), "weide", matrix, uv="rohr", r=0.012, seg=6)
    if henkel:
        bogen = [(r_oben * math.cos(a), 0.0, h + r_oben * 0.9 * math.sin(a)) for a in
                 (math.pi * k / 12 for k in range(13))]
        m.teil(rohr(bogen, 0.011, 6), "weide", matrix, uv="rohr", r=0.011, seg=6)


def seilrolle(m, matrix, r=0.16, dicke=0.018, lagen=3):
    """Aufgerolltes Seil: mehrere flache Windungen übereinander."""
    pts = []
    for i in range(lagen * 24 + 1):
        a = 2 * math.pi * i / 24
        rr = r - (i // 24) * 0.004 + 0.006 * math.sin(a * 3)
        pts.append((rr * math.cos(a), rr * math.sin(a), dicke * (0.5 + i / 24 * 0.9)))
    m.teil(rohr(pts, dicke / 2, 6), "seil", matrix, uv="rohr", r=dicke / 2, seg=6)


def kistenkoerper(m, bx, by, h, matrix=None, deckel="zu", griffe=True, riegel=True, eisen=True):
    """Bretterkiste (Mitte unten im Ursprung). deckel: zu | offen (nach hinten aufgeklappt) | weg."""
    G0 = m.G
    m.G = (G0 @ matrix) if (G0 is not None and matrix is not None) else (matrix or G0)
    d = 0.02; latte = 0.05
    n = max(2, round(h / 0.19))
    bretterwand(m, bx, h - 0.04, n, M((0, -by / 2 + d / 2, h / 2)))
    bretterwand(m, bx, h - 0.04, n, M((0, by / 2 - d / 2, h / 2)))
    for s in (-1, 1):
        bretterwand(m, by - 2 * d, h - 0.04, n, M((s * (bx / 2 - d / 2), 0, h / 2), (0, 0, 90)))
    m.brett(bx - 0.01, by - 0.01, d, M((0, 0, 0.03)), "holz")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.kantholz((sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), 0.0),
                       (sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), h - 0.01), latte, 0.022, oben=(0, sy, 0))
    if eisen:
        for sx in (-1, 1):
            for sy in (-1, 1):
                for dx, dy in ((0.06, 0), (0, 0.06)):
                    p = Vector((sx * (bx / 2 + 0.012 - dx / 2), sy * (by / 2 + 0.012 - dy / 2), h - 0.05))
                    m.teil(quader(0.004 + dx, 0.004 + dy, 0.09, fase=0.001), "eisen", M(p), versatz=(m.rnd.random(), 0))
    if griffe:
        # Seilschlaufen an den Seiten, durch zwei Löcher gezogen
        for s in (-1, 1):
            x = s * (bx / 2 + 0.02)
            pts = [(x - s * 0.02, -0.09, h * 0.7)] + [
                (x + s * 0.035 * math.sin(math.pi * k / 8), -0.09 + 0.18 * k / 8, h * 0.7 - 0.06 * math.sin(math.pi * k / 8))
                for k in range(9)] + [(x - s * 0.02, 0.09, h * 0.7)]
            m.seil(pts, 0.011)
    if deckel != "weg":
        dm = M((0, 0, h + 0.012)) if deckel == "zu" else \
            Matrix.Translation((0, by / 2 + 0.01, h + 0.012)) @ M(rot=(-108, 0, 0)) @ Matrix.Translation((0, -by / 2 - 0.01, 0))
        nb = max(2, round(by / 0.2))
        bb = (by + 0.02) / nb
        for i in range(nb):
            y = -by / 2 - 0.01 + bb * (i + 0.5)
            m.brett(bx + 0.02, bb - 0.005, d, dm @ M((0, y, 0)), "holz")
        for x in (-bx / 2 + 0.1, bx / 2 - 0.1):
            m.brett(latte, by - 0.06, 0.02, dm @ M((x, 0, -0.02)), "holz", nx=2)
        if riegel:
            # Überwurf am Deckel, Krampe an der Front
            m.teil(quader(0.04, 0.008, 0.09, fase=0.002), "eisen", dm @ M((0, -by / 2 - 0.016, -0.035)))
    if riegel:
        m.teil(quader(0.05, 0.02, 0.025, fase=0.002), "eisen", M((0, -by / 2 - 0.02, h - 0.1)))
    m.G = G0


# ======================================================================== Vorratskiste (Dorf)

def vorratskiste(m, kaputt):
    bx, by, h = 0.9, 0.6, 0.55
    if not kaputt:
        kistenkoerper(m, bx, by, h)
        # Korb mit Äpfeln auf dem Deckel
        km = M((-0.12, 0.02, h + 0.035))
        korb(m, km, 0.13, 0.17, 0.14)
        for k in range(14):
            a = 2 * math.pi * k / 9 + m.rnd.uniform(-0.2, 0.2)
            rr = 0.0 if k == 0 else (0.075 if k < 9 else 0.035)
            z = 0.12 + (0.035 if k >= 9 or k == 0 else 0.0)
            apfel(m, km @ M((rr * math.cos(a), rr * math.sin(a), z), (m.rnd.uniform(0, 40), 0, m.rnd.uniform(0, 360))))
        # Kornsack lehnt rechts an der Kiste, ein kleinerer liegt davor
        sack(m, M((bx / 2 + 0.2, 0.05, 0.0), (0, -9, 20)), 0.6, 0.2)
        sack(m, M((bx / 2 + 0.05, -0.42, 0.13), (90, 0, 70)), 0.42, 0.13)
    else:
        kistenkoerper(m, bx, by, h, deckel="offen")
        # leerer Korb umgekippt daneben, leerer Sack am Boden, Äpfel verstreut
        korb(m, M((-0.75, -0.25, 0.165), (0, 115, 30)), 0.13, 0.17, 0.14)
        sack(m, M((bx / 2 + 0.3, 0.0, 0.0), (0, 0, 40)), 0.6, 0.2, leer=True)
        for k in range(3):
            apfel(m, M((-0.6 + 0.25 * k + m.rnd.uniform(-0.05, 0.05), -0.55 - m.rnd.uniform(0, 0.2), 0.033),
                       (m.rnd.uniform(0, 90), 0, m.rnd.uniform(0, 360))))


# ======================================================================== Versorgungswagen (Militärlager)

def plane(m, matrix, lx, ly, h, rnd, loch=None):
    """Über eine Ladung geworfene Plane: Buckel über lx x ly, an den Rändern bis fast auf die Ladefläche."""
    nx, ny = 18, 22
    gitter = []
    for i in range(ny + 1):
        y = -ly / 2 + ly * i / ny
        zeile = []
        for j in range(nx + 1):
            x = -lx / 2 + lx * j / nx
            # weicher Kasten: oben flach, an den Rändern abfallend, dazwischen leicht durchhängend
            fx = min(1.0, (lx / 2 - abs(x)) / 0.18)
            fy = min(1.0, (ly / 2 - abs(y)) / 0.18)
            z = h * math.sin(min(fx, fy) * math.pi / 2) - 0.03 * math.sin(math.pi * j / nx * 3) ** 2
            zeile.append((x * (1 + 0.04 * (1 - min(fx, fy))), y, max(0.0, z)))
        gitter.append(zeile)
    bm = flaeche(gitter, 0.006, loch)
    verbiegen(bm, rnd, 0.025, 0.2, (0.3, 0.3, 1))
    m.teil(bm, "stoff", matrix)


def versorgungswagen(m, kaputt):
    r = 0.45
    ladeh = 0.6
    lb, ll = 1.0, 1.5
    neigung = math.degrees(math.atan2(ladeh - 0.06, 1.75))
    props.karren(m, False)
    # Ladung auf der geneigten Ladefläche (gleiche Neigung wie im Karren)
    boden_setzen(m, (neigung, 0, 0), (0, 0, r))
    lade = M((0, 0, ladeh + 0.012))
    if not kaputt:
        kistenkoerper(m, 0.5, 0.42, 0.36, lade @ M((-0.22, 0.42, 0.0)), riegel=False)
        kistenkoerper(m, 0.5, 0.42, 0.36, lade @ M((-0.22, -0.05, 0.0), (0, 0, 4)), riegel=False)
        kistenkoerper(m, 0.42, 0.36, 0.3, lade @ M((-0.2, 0.2, 0.37), (0, 0, -6)), riegel=False, griffe=False)
        G0 = m.G
        m.G = G0 @ lade @ M((0.25, 0.3, 0.0), skal=0.72)
        props.fass(m, False)
        m.G = G0
        sack(m, lade @ M((0.25, -0.45, 0.0), (0, 0, 30)), 0.5, 0.17)
        # Plane über allem, mit zwei Seilen quer verzurrt
        plane(m, lade @ M((0, 0.0, 0.0)), lb + 0.1, ll - 0.05, 0.74, m.rnd)
        for y in (-0.35, 0.4):
            pts = []
            for k in range(13):
                x = -0.56 + 1.12 * k / 12
                f = min(1.0, max(0.0, (0.55 - abs(x)) / 0.18))
                pts.append(lade @ Vector((x, y, 0.74 * math.sin(f * math.pi / 2) + 0.012)))
            m.seil(pts, 0.01)
    else:
        # eine offene, leere Kiste bleibt auf dem Wagen
        kistenkoerper(m, 0.5, 0.42, 0.36, lade @ M((-0.2, 0.35, 0.0), (0, 0, 8)), deckel="weg", riegel=False)
    m.G = None
    if kaputt:
        # Plane heruntergerissen und auf dem Boden, Deckel und leerer Sack daneben, Fass umgekippt
        def loch(i, j):
            return (i - 9) ** 2 + (j - 5) ** 2 < 5
        plane(m, M((-1.25, 0.2, 0.0), (0, 0, 80)), 1.2, 1.4, 0.12, m.rnd, loch)
        sack(m, M((0.95, 0.6, 0.0), (0, 0, 10)), 0.5, 0.17, leer=True)
        G0 = m.G
        m.G = M((1.0, -0.4, 0.24), (90, 0, 60), skal=0.72)
        props.fass(m, False)
        m.G = G0
        for i in range(3):
            m.brett(0.52, 0.13, 0.02, M((-0.9 + i * 0.05, -0.75 + 0.14 * i, 0.012 + 0.02 * i), (0, 0, 20 + 8 * i)), "holz")


# ======================================================================== Grubenlore (Mine)

def lore_rad(m, mitte, r=0.15):
    """Kleines Eisenrad mit Spurkranz, Achse entlang x."""
    prof = [(0.03, -0.035), (r - 0.01, -0.035), (r, -0.025), (r, 0.02), (r + 0.022, 0.025), (r + 0.022, 0.035),
            (0.03, 0.035)]
    bm = drehkoerper(prof, 20, False, False)
    m.teil(bm, "eisen", M(mitte, (0, 90, 0)), uv="zylz", r=r)
    m.teil(rundholz(0.03, 0.1, 8), "eisen", M(mitte), uv="zyl", r=0.03)


def grubenlore(m, kaputt):
    lu, lo = 0.95, 1.15                          # Kastenlänge unten/oben (y)
    bu, bo = 0.62, 0.78                          # Breite unten/oben (x)
    z0, z1 = 0.24, 0.84                          # Kastenboden, Oberkante
    rr = 0.15
    if kaputt:
        # ein Rad fehlt: die Lore sackt an dieser Ecke ab
        boden_setzen(m, (-2.5, 3.0, 0), (-0.33, -0.33, 0))
    # Fahrgestell: zwei Längsträger, Achsen, vier Räder
    for s in (-1, 1):
        m.kantholz((s * 0.24, -0.55, z0 - 0.05), (s * 0.24, 0.55, z0 - 0.05), 0.08, 0.08)
    for y in (-0.33, 0.33):
        m.teil(rundholz(0.022, 0.76, 8), "eisen", M((0, y, rr + 0.02)), uv="zyl", r=0.022)
        for s in (-1, 1):
            if kaputt and s > 0 and y > 0:
                continue
            lore_rad(m, (s * 0.33, y, rr + 0.02), rr)
            m.teil(quader(0.05, 0.12, 0.1, fase=0.004), "eisen", M((s * 0.24, y, rr + 0.07)))
    # Kasten: schräge Bretterwände (oben weiter), Boden, Eisenbänder und Eckwinkel
    def wand(ax, s):
        """ax = 'x' -> Längsseite bei x = ±, 'y' -> Stirnseite bei y = ±."""
        n = 4
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            tm = (t0 + t1) / 2
            z = z0 + (z1 - z0) * tm
            lang = (lu + (lo - lu) * tm) if ax == "x" else (bu + (bo - bu) * tm) - 0.04
            pos = (bu + (bo - bu) * tm) / 2 if ax == "x" else (lu + (lo - lu) * tm) / 2
            kipp = math.degrees(math.atan2(((bo - bu) if ax == "x" else (lo - lu)) / 2, z1 - z0))
            hb = (z1 - z0) / n / math.cos(math.radians(kipp)) - 0.006
            if ax == "x":
                m.brett(lang, 0.025, hb, M((s * pos, 0, z), (0, 0, 90)) @ M(rot=(-s * kipp, 0, 0)), "holz")
            else:
                m.brett(lang, 0.025, hb, M((0, s * pos, z)) @ M(rot=(s * kipp, 0, 0)), "holz")
    for s in (-1, 1):
        wand("x", s); wand("y", s)
    m.teil(quader(bu, lu, 0.03), "holz", M((0, 0, z0 + 0.015)))
    for tz in (0.08, 0.92):
        z = z0 + (z1 - z0) * tz
        b = bu + (bo - bu) * tz + 0.03; l = lu + (lo - lu) * tz + 0.03
        ring = [(-b / 2, -l / 2, z), (b / 2, -l / 2, z), (b / 2, l / 2, z), (-b / 2, l / 2, z), (-b / 2, -l / 2, z)]
        m.teil(rohr(ring, 0.012, 4), "eisen", None, uv="rohr", r=0.012, seg=4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.stab((sx * (bu / 2 + 0.012), sy * (lu / 2 + 0.012), z0), (sx * (bo / 2 + 0.015), sy * (lo / 2 + 0.015), z1 + 0.01),
                   0.014, "eisen", seg=4, biegen=0)
    # Kupplungshaken vorne und hinten
    for s in (-1, 1):
        m.teil(quader(0.06, 0.16, 0.04, fase=0.004), "eisen", M((0, s * 0.62, z0 - 0.05)))
        bogen = [(0, s * (0.7 + 0.04 * math.sin(math.pi * k / 8)), z0 - 0.05 + 0.04 * math.cos(math.pi * k / 8)) for k in range(9)]
        m.seil(bogen, 0.012, 5, "eisen")
    if not kaputt:
        # Ladung: Säcke ragen über den Rand, Seilrolle obenauf, Laterne an der vorderen Ecke
        sack(m, M((-0.15, -0.25, z0 + 0.03), (0, 6, 10)), 0.7, 0.21)
        sack(m, M((0.17, -0.2, z0 + 0.03), (4, -8, 70)), 0.66, 0.2)
        sack(m, M((0.0, 0.25, z0 + 0.03), (-6, 0, 30)), 0.72, 0.22)
        sack(m, M((0.05, 0.05, z1 - 0.05), (90, 0, 15)), 0.55, 0.17)
        seilrolle(m, M((-0.12, 0.3, z1 + 0.08), (8, -6, 0)))
        props.laterne_koerper(m, False, M((bo / 2 - 0.1, -lo / 2 - 0.06, z1 - 0.32)))
        m.seil([(bo / 2 - 0.1, -lo / 2 - 0.06, z1 - 0.02), (bo / 2 - 0.1, -lo / 2 - 0.01, z1 + 0.02),
                (bo / 2 - 0.1, -lo / 2 + 0.03, z1 - 0.02)], 0.006, 5, "eisen")
    m.G = None
    if kaputt:
        # das abgefallene Rad liegt daneben
        m.teil(drehkoerper([(0.03, -0.035), (rr, -0.035), (rr + 0.022, 0.035), (0.03, 0.035)], 20, False, False),
               "eisen", M((0.75, 0.6, 0.036)), uv="zylz", r=rr)
        sack(m, M((-0.7, -0.6, 0.0), (0, 0, 20)), 0.7, 0.21, leer=True)
        seilrolle(m, M((0.75, -0.45, 0.0)), 0.16, 0.018, 2)


# ======================================================================== Fischerkorb (Strand)

def korbkoerper(m, matrix, r_unten, r_oben, h, wand=0.015):
    prof = [(0.0, 0.0), (r_unten - 0.02, 0.0), (r_unten, 0.03), (r_oben * 1.02, h * 0.55), (r_oben, h),
            (r_oben - wand, h), (r_oben * 1.02 - wand, h * 0.55), (r_unten - wand, 0.03 + wand), (0.0, wand)]
    bm = drehkoerper(prof, 28, False, False)
    verbiegen(bm, m.rnd, 0.008, 0.2)
    m.teil(bm, "weide", matrix, uv="zylz", r=r_oben)
    for z, rr in ((h, r_oben), (0.02, r_unten)):
        ring = [(rr * math.cos(a), rr * math.sin(a), z) for a in (2 * math.pi * k / 28 for k in range(29))]
        m.teil(rohr(ring, 0.015, 6), "weide", matrix, uv="rohr", r=0.015, seg=6)


def korbdeckel(m, matrix, r):
    prof = [(0.0, 0.05), (r * 0.5, 0.045), (r * 0.95, 0.02), (r + 0.02, 0.0), (r + 0.02, -0.02), (r - 0.01, -0.02),
            (r - 0.01, 0.0), (r * 0.5, 0.03), (0.0, 0.035)]
    bm = drehkoerper(prof, 28, False, False)
    m.teil(bm, "weide", matrix, uv="zylz", r=r)
    # Griff: kleiner Bügel aus Weide
    bogen = [(-0.06 + 0.12 * k / 8, 0.0, 0.05 + 0.04 * math.sin(math.pi * k / 8)) for k in range(9)]
    m.teil(rohr(bogen, 0.01, 6), "weide", matrix, uv="rohr", r=0.01, seg=6)


def netz(m, matrix, lx, ly, n_x, n_y, hoehe_fn):
    """Fischernetz aus dünnen Schnüren über eine Form gelegt (hoehe_fn(x, y) -> z)."""
    for j in range(n_x + 1):
        x = -lx / 2 + lx * j / n_x
        pts = [(x + 0.01 * math.sin(i * 1.7 + j), -ly / 2 + ly * i / 24, 0) for i in range(25)]
        m.teil(rohr([(p[0], p[1], hoehe_fn(p[0], p[1])) for p in pts], 0.003, 3), "seil", matrix, uv="rohr", r=0.003, seg=3)
    for i in range(n_y + 1):
        y = -ly / 2 + ly * i / n_y
        pts = [(-lx / 2 + lx * k / 24, y + 0.01 * math.sin(k * 1.3 + i), 0) for k in range(25)]
        m.teil(rohr([(p[0], p[1], hoehe_fn(p[0], p[1])) for p in pts], 0.003, 3), "seil", matrix, uv="rohr", r=0.003, seg=3)


def schwimmer(m, matrix):
    m.teil(rundholz(0.03, 0.09, 8), "holz_alt", matrix, uv="zyl", r=0.03)


def fischerkorb(m, kaputt):
    ru, ro, h = 0.28, 0.34, 0.62
    if not kaputt:
        korbkoerper(m, None, ru, ro, h)
        korbdeckel(m, M((0, 0, h + 0.02)), ro)
        # Tragriemen aus Seil über die Seite, Netz über den Deckel gehängt
        for s in (-1, 1):
            pts = [(s * ro * 0.9, -0.08, h - 0.05)] + [(s * (ro + 0.03), -0.08 + 0.16 * k / 6, h * 0.45 - 0.12 * math.sin(math.pi * k / 6))
                                                       for k in range(7)] + [(s * ro * 0.9, 0.08, h - 0.05)]
            m.seil(pts, 0.01)

        def ueber_korb(x, y):
            rr = math.hypot(x, y)
            if rr < ro:
                return h + 0.06 + 0.04 * (1 - rr / ro)
            return max(0.01, h + 0.06 - (rr - ro) * 2.2)
        netz(m, M((0.1, -0.05, 0.0), (0, 0, 25)), 0.62, 0.95, 12, 18, ueber_korb)
        for k in range(3):
            schwimmer(m, M((0.25 + 0.06 * k, -0.48 + 0.04 * k, 0.03), (0, 0, 70 + 15 * k)))
        # Treibholz-Brett liegt dahinter
        m.brett(0.9, 0.14, 0.03, M((-0.1, 0.55, 0.015), (0, 0, 12)), "holz_alt", bruch=1)
    else:
        # umgekippt und leer, Deckel liegt daneben, Netz am Boden ausgebreitet
        korbkoerper(m, M((0.0, 0.0, ro * 1.02), (-90 + 8, 0, 20)) @ M((0, 0, -h / 2)), ru, ro, h)
        korbdeckel(m, M((-0.55, -0.5, 0.021), (0, 0, 10)), ro)
        netz(m, M((0.55, -0.15, 0.0), (0, 0, -15)), 0.7, 0.9, 12, 16,
             lambda x, y: 0.006 + 0.015 * max(0.0, math.sin(x * 9) * math.cos(y * 7)))
        schwimmer(m, M((0.8, 0.35, 0.03), (0, 0, 20)))
        m.brett(0.9, 0.14, 0.03, M((0.05, 0.62, 0.015), (0, 0, 8)), "holz_alt", bruch=1)


# ======================================================================== Kleine Schatzkiste (Burg)

def schatzkiste_klein(m, kaputt):
    bx, by, h = 0.7, 0.45, 0.32
    R = by / 2
    kistenkoerper(m, bx, by, h, deckel="weg", griffe=False, riegel=False, eisen=False)
    # Gewölbter Deckel aus Brettern um die Scharnierachse; Drehpunkt hinten oben
    def deckel_matrix():
        if not kaputt:
            return M((0, 0, h))
        return Matrix.Translation((0, R, h)) @ M(rot=(-105, 0, 0)) @ Matrix.Translation((0, -R, 0))
    dm = deckel_matrix()
    n = 7
    for k in range(n):
        a = math.radians(180 * (k + 0.5) / n)
        w = 2 * R * math.sin(math.pi / (2 * n)) + 0.004
        m.brett(bx + 0.01, w, 0.022, dm @ M((0, R * math.cos(a) * 0.985, R * 0.55 * math.sin(a)),
                                          (math.degrees(math.atan2(0.55 * math.cos(a), math.sin(a))) * -1, 0, 0)), "holz", fase=0.003)
    # Stirnseiten des Deckels: halbe Ellipsen
    for s in (-1, 1):
        prof = [(0.0, -0.011), (1.0, -0.011), (1.0, 0.011), (0.0, 0.011)]
        bm = drehkoerper(prof, 12, winkel=(0.0, 180.0))
        for v in bm.verts:
            v.co = Vector((v.co.x * R, v.co.y * R * 0.55, v.co.z))
        m.teil(bm, "holz", dm @ M((s * (bx / 2 - 0.011), 0, 0), (90, 0, 90)))
    # Eisenbänder über Deckel und Korpus
    for x in (-bx / 2 + 0.08, 0.0, bx / 2 - 0.08):
        bogen = [(x, R * 1.01 * math.cos(math.pi * k / 16), R * 0.57 * math.sin(math.pi * k / 16)) for k in range(17)]
        bm = rohr(bogen, 0.012, 4, kappen=True)
        for v in bm.verts:
            v.co.x = x + max(-0.02, min(0.02, (v.co.x - x) * 2.2))
        m.teil(bm, "eisen", dm, uv="rohr", r=0.012, seg=4)
        if x != 0.0:
            for s in (-1, 1):
                m.teil(quader(0.04, 0.006, h - 0.02, fase=0.001), "eisen", M((x, s * (by / 2 + 0.012), h / 2)))
    # Eckbeschläge unten, Tragringe an den Seiten
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.teil(quader(0.07, 0.07, 0.07, fase=0.003), "eisen", M((sx * (bx / 2 - 0.025), sy * (by / 2 - 0.025), 0.035)) @
                   M(skal=(1.05, 1.05, 1.0)))
        ring = [(sx * (bx / 2 + 0.02), 0.05 * math.cos(2 * math.pi * k / 12), h * 0.62 + 0.05 * math.sin(2 * math.pi * k / 12))
                for k in range(13)]
        m.seil(ring, 0.007, 5, "eisen")
    # Schloss: Platte am Korpus, Überwurf am Deckel, Vorhängeschloss
    m.teil(quader(0.1, 0.01, 0.1, fase=0.002), "eisen", M((0, -by / 2 - 0.014, h - 0.06)))
    if not kaputt:
        m.teil(quader(0.04, 0.012, 0.1, fase=0.002), "eisen", M((0, -by / 2 - 0.024, h - 0.02)))
        schloss = M((0, -by / 2 - 0.05, h - 0.1))
    else:
        # aufgebrochen: Schloss liegt vor der Kiste
        schloss = M((0.12, -by / 2 - 0.25, 0.03), (90, 0, 35))
    m.teil(quader(0.07, 0.03, 0.06, fase=0.006), "eisen", schloss)
    bugel = [(0.025 * math.cos(math.pi * k / 8), 0.0, 0.03 + 0.035 * math.sin(math.pi * k / 8)) for k in range(9)]
    if kaputt:
        bugel = bugel[:6]
    m.seil([schloss @ Vector(p) for p in bugel], 0.006, 5, "eisen")


MODELLE = {"vorratskiste": vorratskiste, "versorgungswagen": versorgungswagen, "grubenlore": grubenlore,
           "fischerkorb": fischerkorb, "schatzkiste_klein": schatzkiste_klein}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
