"""Tavernen-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python taverne.py -- <zielordner/modelle> [--nur bett,schrank] [--vorschau <ordner>]
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y (Bett: Kopfende bei +y, an die Wand)."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, klotz, brocken, verbiegen
import props
from props import bretterwand, boden_setzen
from behaelter import kistenkoerper
import deko


# ======================================================================== Hilfen

def kissen(m, matrix, lx, ly, lz, mat="stoff", platt=0.0):
    """Weiches Polster: Quader mit runden Kanten, in der Mitte aufgebläht, platt > 0 drückt es flach."""
    bm = quader(lx, ly, lz, 6, 6, 2, fase=min(lx, ly, lz) * 0.45)
    for v in bm.verts:
        fx = 1 - (2 * v.co.x / lx) ** 2; fy = 1 - (2 * v.co.y / ly) ** 2
        v.co.z *= 1 + (0.35 - platt) * max(0.0, fx * fy)
    verbiegen(bm, m.rnd, lz * 0.06, 0.15)
    m.teil(bm, mat, matrix)


def decke(m, matrix, lx, ly, oben, seite, rnd, falten=0.012, mat="wolle_rot", loch=None):
    """Über ein Polster gelegte Decke: flach auf Höhe oben für |x| < lx/2, an den Seiten bis auf Höhe seite hängend."""
    nx, ny = 16, 20
    g = []
    for i in range(ny + 1):
        y = -ly / 2 + ly * i / ny
        zeile = []
        for j in range(nx + 1):
            t = -1 + 2 * j / nx                       # -1 … 1 über die ganze Breite inkl. Überhang
            x = t * (lx / 2 + 0.1)
            if abs(x) <= lx / 2:
                z = oben
            else:
                k = (abs(x) - lx / 2) / 0.1
                x = math.copysign(lx / 2 + 0.03 * math.sin(k * math.pi / 2), x)
                z = oben - (oben - seite) * k
            z += falten * math.sin(3.1 * y + 1.7 * x) * math.sin(5.3 * x)
            zeile.append((x, y, z))
        g.append(zeile)
    bm = flaeche(g, 0.012, loch)
    verbiegen(bm, rnd, 0.008, 0.2)
    m.teil(bm, mat, matrix)


def decke_liegend(m, matrix, lx, ly, rnd, mat="wolle_rot", loch=None, hoch=0.07):
    """Weich auf den Boden gefallene Decke: liegt flach auf, mit ein paar zusammengeschobenen Wülsten und Falten.
    Die Ränder liegen am Boden, die Umrisse sind unregelmäßig (nicht mehr rechteckig)."""
    from mathutils import noise
    nx, ny = 22, 22
    o = Vector([rnd.uniform(-50, 50) for _ in range(3)])
    wuelste = [(rnd.uniform(-0.25, 0.25) * lx, rnd.uniform(-0.3, 0.3) * ly, rnd.uniform(0.6, 1.0)) for _ in range(3)]
    g = []
    for i in range(ny + 1):
        zeile = []
        for j in range(nx + 1):
            x = -lx / 2 + lx * j / nx; y = -ly / 2 + ly * i / ny
            z = 0.0
            for (wx, wy, st) in wuelste:
                d2 = ((x - wx) / (lx * 0.22)) ** 2 + ((y - wy) / (ly * 0.18)) ** 2
                z += hoch * st * math.exp(-d2)
            p = Vector((x * 2.2, y * 2.2, 0)) + o
            z += 0.018 * (noise.noise(p) * 0.5 + 0.5) + 0.01 * max(0.0, math.sin(x * 14 + 3 * noise.noise(p * 0.7)))
            rand = min(j, nx - j, i, ny - i) / 3.0
            z *= min(1.0, rand)                       # Ränder liegen auf
            # Stoff wird an den Wülsten zusammengezogen: Umriss wird unregelmäßig
            zieh = 0.12 * noise.noise(p * 0.6 + Vector((7, 0, 0)))
            zeile.append((x * (1 + zieh), y * (1 + 0.12 * noise.noise(p * 0.6 + Vector((0, 9, 0)))), 0.006 + z))
        g.append(zeile)
    bm = flaeche(g, 0.01, loch)
    m.teil(bm, mat, matrix)


def teller(m, matrix, r=0.11, mat="ton"):
    m.teil(drehkoerper([(0.0, 0.0), (r * 0.6, 0.0), (r, 0.02), (r * 0.97, 0.024), (r * 0.58, 0.006), (0.0, 0.006)], 20,
                       False, False), mat, matrix, uv="zylz", r=r)


def scherben_teller(m, matrix, r=0.11, n=3, mat="ton"):
    """Zerbrochener Teller: Tortenstücke, leicht verschoben."""
    a = 0.0
    for k in range(n):
        b = a + 360 / n * m.rnd.uniform(0.7, 1.2) if k < n - 1 else 360
        stueck = drehkoerper([(0.0, 0.0), (r * 0.6, 0.0), (r, 0.02), (r * 0.97, 0.024), (r * 0.58, 0.006), (0.0, 0.006)], 8,
                             False, False, winkel=(a, b))
        bmesh.ops.solidify(stueck, geom=stueck.faces[:], thickness=0.004)
        mitte = math.radians((a + b) / 2)
        m.teil(stueck, mat, matrix @ M((0.04 * math.cos(mitte), 0.04 * math.sin(mitte), 0.0), (0, 0, m.rnd.uniform(-15, 15))),
               uv="zylz", r=r)
        a = b


def becher(m, matrix, mat="ton", h=0.1, r=0.035):
    m.teil(drehkoerper([(0.0, 0.0), (r * 0.85, 0.0), (r, h), (r * 0.9, h), (r * 0.78, 0.008), (0.0, 0.008)], 14, False, False),
           mat, matrix, uv="zylz", r=r)


def flasche(m, matrix, h=0.3, r=0.045, mat="glas_gruen", korken=True, hals=True):
    prof = [(0.0, 0.0), (r, 0.0), (r, h * 0.55), (r * 0.5, h * 0.72), (r * 0.32, h * 0.78)]
    if hals:
        prof += [(r * 0.3, h * 0.97), (r * 0.38, h), (0.0, h)]
    else:                                             # abgebrochener Hals: offene, zackige Kante
        prof += [(r * 0.31, h * 0.8)]
    bm = drehkoerper(prof, 14, hals, True)
    if not hals:
        for v in bm.verts:
            if v.co.z > h * 0.75:
                v.co.z -= m.rnd.uniform(0, 0.03)
    m.teil(bm, mat, matrix, uv="zylz", r=r)
    if korken and hals:
        m.teil(rundholz(r * 0.26, 0.03, 8), "holz", matrix @ M((0, 0, h + 0.008), (0, 90, 0)), uv="zyl", r=0.01)


def glasscherben(m, matrix, n=6, mat="glas_gruen", weite=0.15):
    for k in range(n):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.03, weite)
        s = brocken(m.rnd, m.rnd.uniform(0.01, 0.025), m.rnd.uniform(0.008, 0.02), 0.003, rauh=0.3, unterteilung=1)
        m.teil(s, mat, matrix @ M((d * math.cos(a), d * math.sin(a), 0.003), (0, 0, m.rnd.uniform(0, 360))))


def kessel(m, matrix, kaputt=False):
    """Eiserner Kessel mit Bügel, Ursprung am Boden des Kessels (Bügelöse 0,6 m darüber)."""
    prof = [(0.0, 0.0), (0.12, 0.01), (0.2, 0.06), (0.23, 0.15), (0.22, 0.25), (0.2, 0.29), (0.215, 0.3), (0.215, 0.31),
            (0.19, 0.305), (0.205, 0.25), (0.21, 0.15), (0.185, 0.075), (0.11, 0.025), (0.0, 0.02)]
    m.teil(drehkoerper(prof, 28, False, False), "eisen", matrix, uv="zylz", r=0.22)
    for s in (-1, 1):
        m.teil(quader(0.03, 0.02, 0.04, fase=0.004), "eisen", matrix @ M((s * 0.215, 0, 0.27)))
    if not kaputt:
        bugel = [(0.22 * math.cos(math.pi * k / 16), 0.0, 0.28 + 0.3 * math.sin(math.pi * k / 16)) for k in range(17)]
    else:
        bugel = [(0.22 * math.cos(math.pi * k / 16), 0.07 * math.sin(math.pi * k / 16), 0.28 - 0.02 * math.sin(math.pi * k / 16))
                 for k in range(17)]
    pts = [matrix @ Vector(p) for p in bugel]
    m.seil(pts, 0.008, 5, "eisen")


# ======================================================================== Schlafen

def bett(m, kaputt):
    """Holzbett 2 x 1 m mit Kopf- und Fußteil, Lattenrost, Matratze, Kissen und Wolldecke. Kopfende bei +y."""
    bx, ly = 1.0, 2.0
    p = 0.08
    for sx in (-1, 1):
        for sy in (-1, 1):
            hoch = 1.0 if sy > 0 else 0.6
            m.kantholz((sx * (bx / 2 - p / 2), sy * (ly / 2 - p / 2), 0.0), (sx * (bx / 2 - p / 2), sy * (ly / 2 - p / 2), hoch), p, p,
                       oben=(0, 1, 0))
            m.teil(drehkoerper([(0.0, 0.0), (0.035, 0.0), (0.045, 0.03), (0.02, 0.07), (0.0, 0.075)], 10), "holz",
                   M((sx * (bx / 2 - p / 2), sy * (ly / 2 - p / 2), hoch)), uv="zylz", r=0.04)
    # Längszargen (rechts gebrochen im kaputten Bett) und Querzargen
    for sx in (-1, 1):
        x = sx * (bx / 2 - p / 2)
        if kaputt and sx > 0:
            m.kantholz((x, -ly / 2 + p, 0.3), (x, -0.1, 0.12), 0.16, 0.04, oben=(1, 0, 0), bruch=1)
            m.kantholz((x, 0.05, 0.12), (x, ly / 2 - p, 0.3), 0.16, 0.04, oben=(1, 0, 0), bruch=-1)
            continue
        m.kantholz((x, -ly / 2 + p, 0.3), (x, ly / 2 - p, 0.3), 0.16, 0.04, oben=(1, 0, 0))
    for sy in (-1, 1):
        m.kantholz((-bx / 2 + p, sy * (ly / 2 - p / 2), 0.3), (bx / 2 - p, sy * (ly / 2 - p / 2), 0.3), 0.16, 0.04, oben=(0, 1, 0))
    bretterwand(m, bx - 2 * p, 0.5, 3, M((0, ly / 2 - p / 2, 0.68)))
    bretterwand(m, bx - 2 * p, 0.2, 1, M((0, -ly / 2 + p / 2, 0.48)))
    # Lattenrost auf Leisten innen an den Längszargen
    for sx in (-1, 1):
        if not (kaputt and sx > 0):
            m.kantholz((sx * (bx / 2 - p - 0.015), -ly / 2 + p, 0.25), (sx * (bx / 2 - p - 0.015), ly / 2 - p, 0.25), 0.03, 0.03)
    latten = 9
    for i in range(latten):
        y = -ly / 2 + p + 0.08 + (ly - 2 * p - 0.16) * i / (latten - 1)
        if kaputt and i in (3, 4, 5):
            continue
        if kaputt and i in (2, 6):                    # rechts abgerutscht, liegt schräg auf dem Boden
            m.brett(bx - 2 * p - 0.02, 0.08, 0.02, M((0.05, y, 0.16), (0, 22, 0)), "holz")
            continue
        m.brett(bx - 2 * p, 0.08, 0.02, M((0, y, 0.275)), "holz")
    # Matratze
    mat_l, mat_b, mat_h = ly - 2 * p - 0.02, bx - 2 * p - 0.02, 0.16
    bm = quader(mat_b, mat_l, mat_h, 6, 12, 2, fase=0.05)
    for v in bm.verts:
        v.co.z += 0.02 * max(0.0, (1 - (2 * v.co.x / mat_b) ** 2) * (1 - (2 * v.co.y / mat_l) ** 2)) * (v.co.z > 0)
        if kaputt:                                   # rechts in der Mitte durchgesackt
            sack = max(0.0, math.cos(v.co.y / 0.55 * math.pi / 2)) if abs(v.co.y) < 0.55 else 0.0
            v.co.z -= 0.15 * sack * (0.5 + v.co.x / mat_b)
    verbiegen(bm, m.rnd, 0.01, 0.2)
    m.teil(bm, "stoff", M((0, 0, 0.285 + mat_h / 2)))
    if not kaputt:
        kissen(m, M((0, ly / 2 - p - 0.25, 0.285 + mat_h + 0.05), (0, 0, 2)), 0.6, 0.34, 0.1)
        decke(m, M((0, -0.25, 0.0)), mat_b, 1.25, 0.285 + mat_h + 0.03, 0.3, m.rnd)
    else:
        kissen(m, M((0.85, -0.6, 0.045), (0, 0, 30)), 0.6, 0.34, 0.09, platt=0.2)
        # Decke liegt zerknüllt vor dem Bett
        decke_liegend(m, M((-1.0, -0.3, 0.0), (0, 0, 70)), 1.2, 1.1, m.rnd, hoch=0.04)


def strohlager(m, kaputt):
    """Strohsack auf dem Boden mit Kissen (Schlafsaal, Stall)."""
    lx, ly = 0.9, 1.9
    if not kaputt:
        bm = quader(lx, ly, 0.2, 6, 10, 2, fase=0.08)
        for v in bm.verts:
            v.co.z += 0.03 * max(0.0, (1 - (2 * v.co.x / lx) ** 2)) * (v.co.z > 0)
        verbiegen(bm, m.rnd, 0.025, 0.2)
        m.teil(bm, "stroh", M((0, 0, 0.1)))
        for k in range(10):                          # herausstehende Halmbüschel
            x = m.rnd.uniform(-1, 1) * (lx / 2 + 0.02); y = m.rnd.uniform(-1, 1) * (ly / 2 + 0.02)
            if abs(x) < lx / 2 - 0.05 and abs(y) < ly / 2 - 0.05:
                x = math.copysign(lx / 2, x)
            m.teil(brocken(m.rnd, 0.06, 0.04, 0.02, rauh=0.4, unterteilung=1), "stroh", M((x, y, 0.02), (0, 0, m.rnd.uniform(0, 360))))
        kissen(m, M((0, ly / 2 - 0.3, 0.28), (0, 0, -4)), 0.5, 0.3, 0.1, mat="stoff")
    else:
        # zertrampelt: flach, Stroh zu Haufen zusammengeschoben und verstreut
        bm = quader(lx * 1.1, ly, 0.08, 6, 10, 2, fase=0.035)
        verbiegen(bm, m.rnd, 0.03, 0.2)
        m.teil(bm, "stroh", M((0, 0, 0.04), (0, 0, 4)))
        for k in range(14):
            a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.6, 1.3)
            m.teil(brocken(m.rnd, m.rnd.uniform(0.06, 0.14), m.rnd.uniform(0.04, 0.1), 0.025, rauh=0.4, unterteilung=1), "stroh",
                   M((0.6 * d * math.cos(a), d * math.sin(a), 0.015), (0, 0, m.rnd.uniform(0, 360))))


def truhe(m, kaputt):
    """Truhe am Bettende: Bretterkiste mit Eisenbeschlägen und Schloss. Kaputt: aufgebrochen, Kleider hängen heraus."""
    bx, by, h = 0.9, 0.48, 0.45
    kistenkoerper(m, bx, by, h, deckel="weg", griffe=True, riegel=True)
    # Deckel aus vier dicht gestoßenen Brettern, mit zwei Bändern am hinteren Rand angeschlagen
    achse_y, achse_z = by / 2 + 0.012, h + 0.012
    if not kaputt:
        dm = M((0, 0, h + 0.012))
    else:
        dm = Matrix.Translation((0, achse_y, achse_z)) @ M(rot=(-100, 0, 0)) @ Matrix.Translation((0, -achse_y, -achse_z)) @ \
            M((0, 0, h + 0.012))
    nb = 4
    bb = (by + 0.024) / nb
    for i in range(nb):
        y = -by / 2 - 0.012 + bb * (i + 0.5)
        m.brett(bx + 0.02, bb - 0.0015, 0.022, dm @ M((0, y, 0)), "holz", biegen=0.001, fase=0.003)
    for x in (-bx / 2 + 0.1, bx / 2 - 0.1):
        m.brett(0.05, by - 0.06, 0.02, dm @ M((x, 0, -0.021)), "holz", nx=2, biegen=0)
    m.teil(quader(0.04, 0.008, 0.09, fase=0.002), "eisen", dm @ M((0, -by / 2 - 0.016, -0.035)))
    for x in (-0.25, 0.25):
        # Band auf dem Deckel, Rolle auf der Drehachse, Lasche hinten an der Wand
        m.teil(quader(0.035, 0.26, 0.005, fase=0.001), "eisen", dm @ M((x, by / 2 - 0.12, 0.0135)))
        m.teil(rundholz(0.011, 0.05, 8), "eisen", M((x, achse_y, achse_z)), uv=None)
        m.teil(quader(0.035, 0.005, 0.1, fase=0.001), "eisen", M((x, by / 2 + 0.014, h - 0.04)))
    # Schlossblech
    if not kaputt:
        m.teil(quader(0.09, 0.01, 0.1, fase=0.003), "eisen", M((0, -0.255, 0.33)))
    else:
        m.teil(quader(0.09, 0.01, 0.1, fase=0.003), "eisen", M((0.25, -0.5, 0.005), (90, 0, 30)))
        # Kleidung hängt über den vorderen Rand heraus
        g = []
        for i in range(9):
            t = i / 8
            y = -0.15 + 0.12 * t if t < 0.5 else -0.09 - 0.1 * (t - 0.5) * 2
            z = 0.34 + 0.08 * math.sin(t * math.pi) if t < 0.6 else 0.45 - 0.3 * (t - 0.6) / 0.4
            g.append([(x, y - (0.07 if t > 0.55 else 0.0) * (t - 0.55) * 4, z) for x in (-0.25, -0.12, 0.0, 0.12, 0.2)])
        g = [[(x, y, z) for (x, y, z) in zeile] for zeile in g]
        bm = flaeche(g, 0.008)
        verbiegen(bm, m.rnd, 0.01, 0.1)
        m.teil(bm, "wolle_rot", M((0, 0, 0)))
        kissen(m, M((-0.15, -0.6, 0.03), (0, 0, 25)), 0.35, 0.3, 0.05, mat="stoff", platt=0.3)


def schrank(m, kaputt):
    """Kleiderschrank 1 x 0,55 x 1,95 m mit zwei Füllungstüren, Sockel und Kranz."""
    b, t, h = 1.0, 0.55, 1.95
    w = 0.03
    for sx in (-1, 1):
        m.teil(quader(w, t, h - 0.14, 2, 2, 6), "holz", M((sx * (b / 2 - w / 2), 0, 0.1 + (h - 0.14) / 2)), uv="boxz")
    m.teil(klotz(m.rnd, b + 0.02, t + 0.02, 0.1, fase=0.01, rauh=0.002), "holz", M((0, 0, 0.05)))
    m.teil(quader(b + 0.06, t + 0.06, 0.05, fase=0.01), "holz", M((0, 0, h - 0.02)))
    m.teil(quader(b + 0.1, t + 0.08, 0.04, fase=0.012), "holz", M((0, 0.01, h + 0.02)))
    m.teil(quader(b - 2 * w, t - 0.02, 0.025), "holz", M((0, 0, 0.115)))
    bretterwand(m, b - 2 * w, h - 0.16, 7, M((0, t / 2 - 0.012, 0.1 + (h - 0.16) / 2)), dicke=0.015)
    # innen: Fachboden und Kleiderstange
    m.teil(quader(b - 2 * w, t - 0.04, 0.02), "holz", M((0, 0.01, 1.55)))
    m.stab((-b / 2 + w, 0.02, 1.45), (b / 2 - w, 0.02, 1.45), 0.012, "holz", biegen=0)

    def tuer(matrix, spiegel):
        tb, th = (b - 2 * w) / 2 - 0.004, h - 0.26
        for x in (0.03, tb - 0.03):
            m.teil(quader(0.06, 0.025, th, 1, 1, 4), "holz", matrix @ M((x * spiegel, 0, th / 2)), uv="boxz")
        for z in (0.04, th * 0.5, th - 0.04):
            m.teil(quader(tb - 0.12, 0.025, 0.08), "holz", matrix @ M((tb / 2 * spiegel, 0, z)))
        for z0, z1 in ((0.08, th * 0.5 - 0.04), (th * 0.5 + 0.04, th - 0.08)):
            m.teil(quader(tb - 0.12, 0.012, z1 - z0, 2, 1, 2), "holz", matrix @ M((tb / 2 * spiegel, 0.004, (z0 + z1) / 2)), uv="boxz")
        # Knauf und zwei Bänder
        m.teil(drehkoerper([(0.0, 0.0), (0.012, 0.0), (0.018, 0.02), (0.0, 0.03)], 8), "eisen",
               matrix @ M(((tb - 0.06) * spiegel, -0.012, th * 0.5), (90, 0, 0)))
        for z in (0.2, th - 0.2):
            m.teil(quader(0.14, 0.006, 0.03, fase=0.002), "eisen", matrix @ M((0.07 * spiegel, -0.015, z)))

    z0 = 0.13
    yv = -t / 2 + 0.0125
    if not kaputt:
        tuer(M((-b / 2 + w, yv, z0)), 1)
        tuer(M((b / 2 - w, yv, z0)), -1)
        for k in range(3):                           # zusammengelegte Wäsche im Fach
            kissen(m, M((-0.25 + 0.25 * k, 0.02, 1.6 + 0.04)), 0.22, 0.3, 0.07, mat="stoff" if k != 1 else "wolle_rot", platt=0.3)
    else:
        # linke Tür hängt nur noch am oberen Band, weit offen und schief; rechte Tür liegt vor dem Schrank
        tuer(Matrix.Translation((-b / 2 + w, yv, z0)) @ M(rot=(0, 4, -115)), 1)
        tuer(M((b / 2 - w - 0.05, -t / 2 - 0.08, 0.0125), (90, 0, 8)), -1)
        kissen(m, M((0.15, 0.02, 1.6 + 0.03), (0, 0, 15)), 0.22, 0.3, 0.06, mat="stoff", platt=0.3)
        kissen(m, M((-0.2, 0.0, 0.16)), 0.3, 0.3, 0.05, mat="wolle_rot", platt=0.4)


# ======================================================================== Geschirr

def regal(m, kaputt):
    """Wandregal 1,2 x 0,35 x 1,8 m mit vier Böden, darauf Teller, Becher, Krüge und Flaschen."""
    b, t, h = 1.2, 0.35, 1.8
    p = 0.05
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.kantholz((sx * (b / 2 - p / 2), sy * (t / 2 - p / 2), 0.0), (sx * (b / 2 - p / 2), sy * (t / 2 - p / 2), h), p, p,
                       oben=(0, 1, 0))
    m.kantholz((-b / 2 + p, t / 2 - 0.02, 0.3), (b / 2 - p, t / 2 - 0.02, 1.6), 0.08, 0.02, oben=(0, 1, 0))
    boeden = [0.1, 0.55, 1.0, 1.45, h - 0.02]
    for i, z in enumerate(boeden):
        if kaputt and i == 2:
            # Boden auf 1,0 m: rechte Leiste weg, er ist rechts auf den Boden darunter gerutscht
            l = b - 0.06; dz = z - (0.55 + 0.0125 + 0.0125)
            w = math.asin(dz / l)
            m.brett(l, t - 0.02, 0.025, M((-0.55 + l * math.cos(w) / 2, 0, z - dz / 2), (0, math.degrees(w), 0)), "holz",
                    bruch=1, bruch_tiefe=0.06)
            continue
        m.brett(b - 0.02, t - 0.02, 0.025, M((0, 0, z)), "holz")
        for sx in (-1, 1):
            m.kantholz((sx * (b / 2 - p - 0.012), -t / 2 + 0.03, z - 0.03), (sx * (b / 2 - p - 0.012), t / 2 - 0.03, z - 0.03), 0.025, 0.03)
    # Leiste vorne, damit die Teller nicht herausrutschen
    for z in boeden[1:4]:
        if kaputt and z == 1.0:
            continue
        m.kantholz((-b / 2 + p, -t / 2 + 0.02, z + 0.04), (b / 2 - p, -t / 2 + 0.02, z + 0.04), 0.03, 0.012, oben=(0, -1, 0))
    oben = lambda z: z + 0.0125
    # Teller hochkant an der Rückwand (Boden 1,45)
    for k in range(5):
        x = -0.45 + 0.13 * k
        teller(m, M((x, 0.08, oben(1.45) + 0.11), (-78, 0, 0)), mat="ton" if k % 2 else "holz")
    # Becher und Krug (Boden 1,0)
    if not kaputt:
        for k in range(4):
            becher(m, M((-0.45 + 0.12 * k, -0.04 + 0.04 * (k % 2), oben(1.0))))
        G0 = m.G; m.G = M((0.3, 0.0, oben(1.0))); deko.krug(m, False); m.G = G0
    # Flaschen und Teller-Stapel (Boden 0,55)
    for k in range(4):
        flasche(m, M((0.15 + 0.1 * k, 0.03 * (k % 2), oben(0.55))), 0.26 + 0.03 * (k % 2), mat="glas_gruen" if k % 3 else "glas")
    for k in range(5):
        teller(m, M((-0.35, 0.0, oben(0.55) + 0.006 * k)))
    # unten: zwei Holzschüsseln
    for x in (-0.3, 0.1):
        m.teil(drehkoerper([(0.0, 0.0), (0.06, 0.0), (0.12, 0.07), (0.11, 0.07), (0.055, 0.01), (0.0, 0.01)], 18, False, False),
               "holz", M((x, 0.0, oben(0.1))), uv="zylz", r=0.12)
    if kaputt:
        # Inhalt des gebrochenen Bodens: Scherben und Becher vor dem Regal
        for k, (x, y) in enumerate(((-0.4, -0.45), (0.05, -0.55), (0.35, -0.4))):
            scherben_teller(m, M((x, y, 0.0), (0, 0, 40 * k)), mat="ton")
        becher(m, M((-0.1, -0.35, 0.035), (90, 0, 20)) @ M((0, 0, -0.05)))
        becher(m, M((0.55, -0.6, 0.035), (90, 0, -60)) @ M((0, 0, -0.05)))
        G0 = m.G; m.G = M((0.5, 0.05, 0.0)); deko.krug(m, True); m.G = G0


def geschirr(m, kaputt):
    """Gedeck für den Tavernentisch: zwei Teller mit Löffel, zwei Becher, Holzbrett mit Messer (liegt bei z = 0)."""
    if not kaputt:
        for x in (-0.22, 0.22):
            teller(m, M((x, -0.05, 0.0)))
            m.stab((x + 0.12, -0.12, 0.004), (x + 0.12, 0.04, 0.004), 0.004, "holz", biegen=0)
            m.teil(drehkoerper([(0.0, 0.0), (0.02, 0.0), (0.022, 0.008), (0.0, 0.004)], 8), "holz", M((x + 0.12, 0.055, 0.0)))
            becher(m, M((x + 0.05, 0.14, 0.0)))
    else:
        scherben_teller(m, M((-0.22, -0.05, 0.0)))
        teller(m, M((0.22, -0.05, 0.0)))
        becher(m, M((0.05, 0.17, 0.035), (90, 0, 70)) @ M((0, 0, -0.05)))
        becher(m, M((0.27, 0.14, 0.0)))
    # Brett mit Brotkanten und Messer
    m.brett(0.3, 0.18, 0.02, M((0.0, 0.3, 0.01), (0, 0, -8)), "holz", biegen=0)
    m.teil(drehkoerper([(0.0, 0.0), (0.07, 0.0), (0.08, 0.03), (0.06, 0.06), (0.0, 0.07)], 14), "leder", M((-0.05, 0.3, 0.02),
                                                                                                         skal=(1, 0.7, 1)))
    deko.klinge(m, M((0.08, 0.27, 0.025), (0, 90, 82)), 0.12, 0.022)
    m.stab((0.08, 0.27 - 0.012, 0.025), (0.09, 0.27 - 0.1, 0.025), 0.008, "holz", biegen=0)


def flaschen(m, kaputt):
    """Drei Glasflaschen und eine Tonflasche (für Theke, Regal, Tisch)."""
    if not kaputt:
        flasche(m, M((-0.08, 0.0, 0.0)), 0.3)
        flasche(m, M((0.03, 0.05, 0.0)), 0.27, mat="glas")
        flasche(m, M((0.12, -0.03, 0.0)), 0.32, r=0.04)
    else:
        flasche(m, M((-0.08, 0.0, 0.0)), 0.3, hals=False)
        glasscherben(m, M((-0.08, -0.05, 0.0)))
        flasche(m, M((0.15, -0.05, 0.045), (0, 90, 30)) @ M((0, 0, -0.13)), 0.27, mat="glas")
        glasscherben(m, M((0.25, 0.1, 0.0)), 4, mat="glas", weite=0.1)
    # Tonflasche mit Henkel
    # hohl: außen hoch, über die Lippe, innen wieder hinunter bis auf den Boden
    prof = [(0.0, 0.0), (0.06, 0.0), (0.07, 0.1), (0.05, 0.17), (0.022, 0.2), (0.02, 0.24), (0.026, 0.25), (0.016, 0.252),
            (0.012, 0.24), (0.013, 0.2), (0.04, 0.17), (0.061, 0.1), (0.052, 0.012), (0.0, 0.012)]
    m.teil(drehkoerper(prof, 18, False, False), "ton", M((-0.02, -0.14, 0.0)), uv="zylz", r=0.06)
    m.seil([(-0.02, -0.14 + 0.02, 0.22), (-0.02, -0.14 + 0.07, 0.2), (-0.02, -0.14 + 0.065, 0.13)], 0.008, 5, "ton")


# ======================================================================== Feuerstelle, Teppich, Zapffass

def feuerstelle(m, kaputt):
    """Gemauerte Feuerstelle 1,4 x 1 m mit Holzfeuer, darüber an einem Eisengalgen ein Kessel am Haken."""
    bx, by, h = 1.4, 1.0, 0.35
    # Einfassung aus Steinblöcken, innen Steinplatte
    for i in range(6):
        for s in (-1, 1):
            x = -bx / 2 + bx * (i + 0.5) / 6
            m.teil(klotz(m.rnd, bx / 6 - 0.01, 0.2, h, fase=0.02, rauh=0.008), "stein", M((x, s * (by / 2 - 0.1), h / 2)))
    for i in range(3):
        for s in (-1, 1):
            y = -by / 2 + 0.2 + (by - 0.4) * (i + 0.5) / 3
            m.teil(klotz(m.rnd, 0.2, (by - 0.4) / 3 - 0.01, h, fase=0.02, rauh=0.008), "stein", M((s * (bx / 2 - 0.1), y, h / 2)))
    m.teil(quader(bx - 0.38, by - 0.38, h - 0.06), "stein", M((0, 0, (h - 0.06) / 2)))
    m.teil(drehkoerper([(0.0, 0.03), (0.35, 0.015), (0.42, 0.0), (0.0, 0.0)], 18), "asche", M((0, 0, h - 0.06), skal=(1, 0.75, 1)))
    hf = h - 0.04
    if not kaputt:
        for k in range(4):                           # Scheite im Kreuz, glühend
            a = math.pi * k / 4 + 0.3
            m.stab((0.26 * math.cos(a), 0.2 * math.sin(a), hf), (-0.1 * math.cos(a), -0.08 * math.sin(a), hf + 0.12), 0.04,
                   "holz_verkohlt", r2=0.035)
        for k in range(7):
            a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.0, 0.2)
            m.teil(brocken(m.rnd, 0.04, 0.03, 0.025, rauh=0.3, unterteilung=1), "glut", M((d * math.cos(a), d * math.sin(a), hf)))
        for k in range(5):
            a = 2 * math.pi * k / 5
            deko.flamme(m, M((0.08 * math.cos(a), 0.06 * math.sin(a), hf + 0.05), (m.rnd.uniform(-10, 10), 0, 0)), 4.5 + k % 2)
    else:
        for k in range(3):
            a = math.pi * k / 3 + 0.5
            m.stab((0.25 * math.cos(a), 0.18 * math.sin(a), hf + 0.035), (-0.18 * math.cos(a), -0.14 * math.sin(a), hf + 0.035),
                   0.035, "holz_verkohlt", r2=0.03)
    # Galgen aus Eisen: zwei Ständer in der Einfassung, Querstange, Kette mit Haken
    hoch = h + 1.25
    for s in (-1, 1):
        x = s * (bx / 2 - 0.1)
        if kaputt and s > 0:
            # rechter Ständer umgeknickt: steht nur noch halb, Rest liegt mit der Querstange schräg auf der Einfassung
            m.stab((x, 0, h), (x, 0, h + 0.5), 0.02, "eisen", biegen=0)
            continue
        m.stab((x, 0, h), (x, 0, hoch), 0.02, "eisen", biegen=0)
        m.teil(drehkoerper([(0.0, 0.0), (0.03, 0.0), (0.03, 0.02), (0.0, 0.04)], 8), "eisen", M((x, 0, hoch)))
    if not kaputt:
        m.stab((-bx / 2 + 0.1, 0, hoch - 0.06), (bx / 2 - 0.1, 0, hoch - 0.06), 0.014, "eisen", biegen=0)
        glieder = 8
        for k in range(glieder):
            z = hoch - 0.09 - k * 0.045
            g = [(0.009 * math.cos(2 * math.pi * i / 10), 0.0, z - 0.02 + 0.03 * math.sin(2 * math.pi * i / 10)) for i in range(11)]
            m.seil(g if k % 2 == 0 else [(0.0, q[0], q[2]) for q in g], 0.0035, 4, "eisen")
        unten = hoch - 0.09 - glieder * 0.045
        m.seil([(0.0, 0.0, unten + 0.02), (0.0, 0.0, unten - 0.03), (0.02, 0.0, unten - 0.05), (0.035, 0.0, unten - 0.03)], 0.006, 5,
               "eisen")
        kessel(m, M((0.0, 0.0, unten - 0.04 - 0.58)))
    else:
        # Querstange hängt vom linken Ständer schräg auf die Einfassung herunter
        m.stab((-bx / 2 + 0.1, 0, hoch - 0.06), (bx / 2 - 0.12, -0.05, h + 0.02), 0.014, "eisen", biegen=0)
        m.stab((bx / 2 - 0.1, 0.0, h + 0.5), (bx / 2 + 0.35, -0.3, 0.02), 0.02, "eisen", biegen=0)
        # Kessel umgekippt vor der Feuerstelle, Inhalt verschüttet
        kessel(m, M((0.3, -by / 2 - 0.33, 0.215), (90, 0, 15)) @ M((0, 0, -0.15)), kaputt=True)
        m.teil(drehkoerper([(0.0, 0.006), (0.3, 0.0), (0.0, 0.008)], 16), "asche", M((0.2, -by / 2 - 0.75, 0.0), skal=(1.3, 0.8, 1)))


def teppich(m, kaputt):
    """Geknüpfter Teppich 2 x 1,4 m mit Fransen an den Schmalseiten (Textur teppich = ganzes Bild)."""
    lx, ly = 2.0, 1.4
    nx, ny = 60, 42
    g = []
    for i in range(ny + 1):
        y = -ly / 2 + ly * i / ny
        zeile = []
        for j in range(nx + 1):
            x = -lx / 2 + lx * j / nx
            z = 0.004 + 0.003 * math.sin(x * 7 + y * 3) * math.sin(y * 5)
            if kaputt:
                # Ecke vorne rechts umgeschlagen (an der Linie x - y = 1,2 gespiegelt)
                d = (x - y - 1.25) / math.sqrt(2)
                if d > 0:
                    x, y = x - 2 * d / math.sqrt(2), y + 2 * d / math.sqrt(2)
                    z = 0.016 + 0.01 * min(1.0, d * 8)
                z += 0.02 * max(0.0, math.sin((x + 0.3) * 3)) * (y < -0.2) * 0.5
            zeile.append((x, y, z))
        g.append(zeile)
    def loch(i, j):
        # ausgefranste Löcher: Radius schwankt mit dem Winkel, am Rand fehlen einzelne Maschen
        x = -lx / 2 + lx * (j + 0.5) / nx; y = -ly / 2 + ly * (i + 0.5) / ny
        for (cx, cy, r, s) in ((-0.5, 0.17, 0.13, 1.0), (0.66, -0.44, 0.07, 2.0)):
            dx, dy = x - cx, (y - cy) * 1.2
            a = math.atan2(dy, dx)
            reff = r * (1 + 0.3 * math.sin(3 * a + s) + 0.18 * math.sin(5 * a + 2 * s) + 0.1 * math.sin(9 * a))
            d = math.hypot(dx, dy)
            if d < reff:
                return True
            if d < reff + 0.035 and (i * 7 + j * 13 + int(s)) % 3 == 0:
                return True
        return False
    loch = loch if kaputt else None
    bm = flaeche(g, 0.008, loch)
    m.teil(bm, "teppich", None, versatz=(0.5, 0.5))
    for s in (-1, 1):
        for k in range(28):
            y = -ly / 2 + 0.03 + (ly - 0.06) * k / 27
            if kaputt and s > 0 and k < 9:
                continue
            l = 0.07 + 0.01 * m.rnd.random() - (0.04 * m.rnd.random() if kaputt else 0)
            p0 = Vector((s * lx / 2, y, 0.004))
            m.seil([p0, p0 + Vector((s * l * 0.5, m.rnd.uniform(-0.01, 0.01), -0.001)), p0 + Vector((s * l, m.rnd.uniform(-0.02, 0.02), -0.002))],
                   0.004, 3, "seil")


def zapffass(m, kaputt):
    """Liegendes Fass auf einem Fassbock mit Zapfhahn, darunter ein Humpen."""
    h, rb = 0.95, 0.33
    zm = 0.26 + rb                                   # Achse über der Auflage
    for x in (-0.3, 0.3):
        for s in (-1, 1):
            if kaputt and x > 0 and s < 0:
                m.kantholz((x, -0.36, 0.0), (x, -0.26, 0.12), 0.07, 0.05, oben=(0, -1, 0), bruch=-1)
                continue
            m.kantholz((x, s * 0.36, 0.0), (x, s * 0.18, 0.25), 0.07, 0.05, oben=(0, s, 0))
        m.kantholz((x, -0.3, 0.23), (x, 0.3, 0.23), 0.08, 0.06)
        for s in (-1, 1):
            m.teil(quader(0.08, 0.07, 0.08, fase=0.01), "holz", M((x, s * 0.2, 0.3)))
    G0 = m.G
    if not kaputt:
        m.G = M((0, 0, zm), (0, 90, 0)) @ M((0, 0, -h / 2))
    else:
        # vom Bock gerollt, liegt vorne auf dem Boden
        m.G = M((0.1, -0.85, rb), (0, 90, -12)) @ M((0, 0, -h / 2))
    props.fass(m, False)
    # Zapfhahn im unteren Teil des Deckels (Fass-z = h)
    if not kaputt:
        # Fass-x zeigt nach unten (gedreht um y): +x = unterhalb der Achse
        m.stab((0.15, 0.0, h - 0.04), (0.15, 0.0, h + 0.09), 0.022, "holz", r2=0.018)
        m.stab((0.15, 0.0, h + 0.08), (0.21, 0.0, h + 0.08), 0.012, "eisen", biegen=0)
        m.teil(quader(0.012, 0.05, 0.02, fase=0.003), "eisen", M((0.12, 0.0, h + 0.06)))
    else:
        m.stab((0.15, 0.0, h - 0.04), (0.15, 0.0, h + 0.03), 0.022, "holz", r2=0.02)
    m.G = G0
    if not kaputt:
        G0 = m.G; m.G = M((h / 2 + 0.1, 0.0, 0.0)); deko.humpen(m, False); m.G = G0
    else:
        G0 = m.G; m.G = M((0.7, 0.25, 0.0)); deko.humpen(m, True); m.G = G0
        # ausgelaufenes Bier als dunkler Fleck
        m.teil(drehkoerper([(0.0, 0.003), (0.35, 0.0), (0.0, 0.004)], 18), "holz_verkohlt",
               M((0.6, -0.75, 0.0), skal=(1.4, 0.9, 1)))


MODELLE = {"bett": bett, "strohlager": strohlager, "truhe": truhe, "schrank": schrank, "regal": regal, "geschirr": geschirr,
           "flaschen": flaschen, "feuerstelle": feuerstelle, "teppich": teppich, "zapffass": zapffass}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
