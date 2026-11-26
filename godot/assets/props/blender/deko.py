"""Deko-Props, die die Welt füllen (nicht benutzbar), jedes heil und kaputt.
Aufruf: python deko.py -- <zielordner/modelle> [--nur amboss,brunnen] [--vorschau <ordner>]
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y. Ausnahmen:
  wandfackel   Ursprung auf der Wandfläche (Wand bei y = 0 hinter dem Modell), Halter 1,6 m hoch montieren
  haengelampe  Ursprung am Deckenhaken, das Modell hängt nach unten (z < 0)"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, ausrichten, quader, rundholz, drehkoerper, rohr, flaeche, klotz, brocken, verbiegen, bruchkante
import props
from props import boden_setzen


# ======================================================================== Hilfen

def flamme(m, matrix, gross=1.0):
    bm = drehkoerper([(0.0, 0.0), (0.012 * gross, 0.012 * gross), (0.009 * gross, 0.035 * gross), (0.0, 0.055 * gross)], 6)
    m.teil(bm, "glut", matrix)


def kerze(m, matrix, h=0.12, r=0.018, brennt=True, tropfen=3):
    """Kerze aus Wachs (Material putz) mit Wachsnasen, Docht und Flamme."""
    bm = drehkoerper([(0.0, 0.0), (r, 0.0), (r, h - 0.006), (r * 0.7, h), (0.0, h - 0.004)], 10)
    verbiegen(bm, m.rnd, 0.0015, 0.03)
    m.teil(bm, "putz", matrix, uv="zylz", r=r)
    for k in range(tropfen):
        a = m.rnd.uniform(0, 2 * math.pi)
        l = m.rnd.uniform(0.02, h * 0.6)
        p = [(r * 1.02 * math.cos(a), r * 1.02 * math.sin(a), h - 0.004 - l * t / 4) for t in range(5)]
        m.teil(rohr(p, 0.004, 4, r_ende=0.0055), "putz", matrix, uv=None)
    m.teil(rundholz(0.0015, 0.012, 4), "eisen", matrix @ M((0, 0, h + 0.004), (0, 90, 0)), uv=None)
    if brennt:
        flamme(m, matrix @ M((0, 0, h + 0.006)))


def buch(m, matrix, l=0.24, b=0.17, d=0.04):
    """Geschlossenes Buch: Seitenblock (putz) und Ledereinband mit Rücken an -y."""
    m.teil(quader(l - 0.01, b - 0.008, d - 0.008, fase=0.002), "putz", matrix @ M((0, 0.004, 0)))
    for s in (-1, 1):
        m.teil(quader(l, b, 0.004, fase=0.001), "leder", matrix @ M((0, 0, s * (d / 2 - 0.002))))
    bm = drehkoerper([(d / 2, -l / 2), (d / 2 + 0.002, -l / 2), (d / 2 + 0.002, l / 2), (d / 2, l / 2)], 10, False, False,
                     winkel=(90, 270))
    m.teil(bm, "leder", matrix @ M((0, -b / 2, 0), (0, 90, 0)))


# ======================================================================== Stühle und Tische

def stuhl_armlehne(m, kaputt):
    """Schwerer Lehnstuhl mit Armlehnen und Lederpolster (Taverne, Burg)."""
    sb, st, sh = 0.56, 0.5, 0.46
    b = 0.05
    if kaputt:
        boden_setzen(m, (0, -84, 10), (-sb / 2, 0, 0))
        m.G = Matrix.Translation((0, 0, sb / 2 + 0.04)) @ m.G
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * (sb / 2 - b / 2); y = sy * (st / 2 - b / 2)
            hoch = 1.12 if sy > 0 else 0.68
            if kaputt and sx > 0 and sy < 0:
                m.kantholz((x, y, 0.3), (x, y, hoch), b, b, oben=(0, -1, 0), bruch=-1)
                continue
            m.kantholz((x, y + (0.0 if sy < 0 else 0.0), 0.0), (x, y + (0.07 if sy > 0 else 0.0), hoch), b, b, oben=(0, -1, 0))
        # Armlehne
        m.kantholz((sx * (sb / 2 - b / 2), -st / 2 - 0.04, 0.68), (sx * (sb / 2 - b / 2), st / 2, 0.66), 0.07, 0.03)
        m.kantholz((sx * (sb / 2 - b / 2), -st / 2 + b, sh - 0.05), (sx * (sb / 2 - b / 2), st / 2 - b, sh - 0.05), 0.08, 0.025,
                   oben=(sx, 0, 0))
        m.kantholz((sx * (sb / 2 - b / 2), -st / 2 + b, 0.12), (sx * (sb / 2 - b / 2), st / 2 - b, 0.12), 0.03, 0.03)
    for sy in (-1, 1):
        m.kantholz((-sb / 2 + b, sy * (st / 2 - b / 2), sh - 0.05), (sb / 2 - b, sy * (st / 2 - b / 2), sh - 0.05), 0.08, 0.025,
                   oben=(0, sy, 0))
    # Sitzpolster (Leder) auf einem Brett
    m.brett(sb - 0.02, st - 0.02, 0.025, M((0, 0, sh)), "holz")
    pol = quader(sb - 0.1, st - 0.08, 0.06, 4, 4, 2, fase=0.02)
    for v in pol.verts:
        v.co.z += 0.012 * (1 - (2 * v.co.x / sb) ** 2) * (1 - (2 * v.co.y / st) ** 2) * (v.co.z > 0)
    if kaputt:
        bruchkante(pol, m.rnd, 1, 0.1)
    m.teil(pol, "leder", M((0, -0.01, sh + 0.04)))
    # Lehne: Rahmen mit Lederbespannung
    for z in (0.62, 1.06):
        m.kantholz((-sb / 2 + b, st / 2 - b / 2 + 0.07 * z / 1.12, z), (sb / 2 - b, st / 2 - b / 2 + 0.07 * z / 1.12, z), 0.07, 0.03,
                   oben=(0, -1, 0))
    if not kaputt:
        m.teil(quader(sb - 2 * b, 0.012, 0.4, 4, 1, 4), "leder", M((0, st / 2 - b / 2 + 0.055, 0.84), (-3.5, 0, 0)))
    else:
        bm = flaeche([[(-sb / 2 + b + 0.01, 0, 0.0), (0.05, 0, -0.02)], [(-sb / 2 + b + 0.01, 0, 0.18), (-0.1, 0, 0.12)]], 0.01)
        m.teil(bm, "leder", M((0, st / 2 - b / 2 + 0.055, 0.84)))
    m.G = None
    if kaputt:
        m.kantholz((0.4, -0.5, 0.025), (0.55, -0.15, 0.025), b, b, bruch=1)


def stuhl_brett(m, kaputt):
    """Brettstuhl: Sitzbrett, vier schräg eingesteckte Rundbeine, ausgesägte Rückenlehne aus einem Brett."""
    sh = 0.46
    if kaputt:
        # umgekippt, liegt auf der Seite
        boden_setzen(m, (0, 78, 25), (0.22, 0, 0))
        m.G = Matrix.Translation((0, 0, 0.03)) @ m.G
    sitz = quader(0.42, 0.4, 0.04, 2, 2, 1, fase=0.008)
    for v in sitz.verts:
        if abs(v.co.y + 0.2) < 1e-4:
            v.co.x *= 0.88
    m.teil(sitz, "holz", M((0, 0, sh - 0.02)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            oben = Vector((sx * 0.14, sy * 0.13, sh - 0.04))
            unten = Vector((sx * 0.22, sy * 0.21, 0.0))
            if kaputt and sx < 0 and sy < 0:
                m.stab(oben, oben + (unten - oben) * 0.35, 0.02, kappen=True)
                continue
            m.stab(unten, oben, 0.02, r2=0.017)
    # Lehne: Brett mit Herz-Ausschnitt (angedeutet als Loch im Gitter)
    nx, nz = 10, 12
    w, h = 0.34, 0.44
    def loch(i, j):
        x = (j + 0.5) / nx - 0.5; z = (i + 0.5) / nz
        return ((x * 2.2) ** 2 + ((z - 0.55) * 3.0) ** 2) < 0.3 or (kaputt and z > 0.6 and x > -0.05)
    gitter = [[(-w / 2 * (1 + 0.15 * i / nz) + w * (1 + 0.15 * i / nz) * j / nx, 0.0, h * i / nz) for j in range(nx + 1)]
              for i in range(nz + 1)]
    for zeile in gitter:
        for k, (x, y, z) in enumerate(zeile):
            if z > h * 0.85:
                zeile[k] = (x, y, z + 0.04 * math.cos(math.pi * x / (w * 0.6)))
    bm = flaeche(gitter, 0.03, loch)
    m.teil(bm, "holz", M((0, 0.18, sh), (-12, 0, 0)), uv="boxz")
    m.G = None


def tisch_rund(m, kaputt):
    """Runder Tisch auf einer Mittelsäule mit drei Füßen (Taverne)."""
    r, h = 0.5, 0.76
    if kaputt:
        # umgekippt: liegt auf der Plattenkante und einem Fuß
        boden_setzen(m, (0, -40, 0), (0.38, 0, 0))
    n = 6
    for i in range(n):
        y = -r + (2 * r) * (i + 0.5) / n
        l = 2 * math.sqrt(max(0.0, r * r - y * y)) + 0.02
        if kaputt and i == n - 1:
            continue
        bm = quader(l, 2 * r / n - 0.006, 0.035, 12, 1, 1)
        for v in bm.verts:
            vy = y + v.co.y
            lim = math.sqrt(max(0.0, r * r - vy * vy))
            v.co.x = max(-lim, min(lim, v.co.x))
        m.teil(bm, "holz", M((0, y, h - 0.018)))
    for k in range(2):
        m.kantholz((-r * 0.75, (k - 0.5) * 0.5, h - 0.05), (r * 0.75, (k - 0.5) * 0.5, h - 0.05), 0.06, 0.03, oben=(0, 0, 1))
    m.teil(drehkoerper([(0.0, 0.08), (0.07, 0.08), (0.05, 0.2), (0.045, 0.45), (0.055, 0.6), (0.06, h - 0.06), (0.0, h - 0.06)], 12),
           "holz", None, uv="zylz", r=0.06)
    for k in range(3):
        a = 2 * math.pi * k / 3
        m.kantholz((0.03 * math.cos(a), 0.03 * math.sin(a), 0.05), (0.38 * math.cos(a), 0.38 * math.sin(a), 0.03), 0.07, 0.06)
    m.G = None
    if kaputt:
        bm = quader(0.8, 2 * r / n - 0.006, 0.035, 3, 1, 1)
        m.teil(bm, "holz", M((0.2, -0.85, 0.018), (0, 0, 15)))


def tisch_lang(m, kaputt):
    """Langer Bocktisch für Tavernen und Hallen: 2,4 m Platte aus drei Bohlen auf zwei Böcken."""
    l, b, h = 2.4, 0.8, 0.76
    if kaputt:
        boden_setzen(m, (0, -9, 0), (l / 2 - 0.3, 0, 0))
    for i in range(3):
        y = -b / 2 + b / 3 * (i + 0.5)
        if kaputt and i == 2:
            m.brett(1.5, b / 3 - 0.006, 0.05, M((-0.45, y, h - 0.025)), "holz", bruch=1, bruch_tiefe=0.15)
            continue
        m.brett(l, b / 3 - 0.006, 0.05, M((0, y, h - 0.025)), "holz", nx=8)
    for sx in (-1, 1):
        x = sx * (l / 2 - 0.35)
        if kaputt and sx > 0:
            continue
        m.kantholz((x, -b / 2 + 0.05, h - 0.08), (x, b / 2 - 0.05, h - 0.08), 0.1, 0.07)
        for sy in (-1, 1):
            m.kantholz((x, sy * 0.06, h - 0.1), (x, sy * (b / 2 - 0.02), 0.0), 0.08, 0.06, oben=(1, 0, 0))
    m.kantholz((-l / 2 + 0.35, 0, 0.3), (l / 2 - 0.35, 0, 0.3), 0.08, 0.06, bruch=1 if kaputt else 0)
    m.G = None
    if kaputt:
        x = l / 2 - 0.35
        m.kantholz((x - 0.1, -0.5, 0.035), (x + 0.2, 0.3, 0.035), 0.1, 0.07)
        m.kantholz((x + 0.3, -0.6, 0.03), (x + 0.6, 0.05, 0.03), 0.08, 0.06, bruch=1)
        m.brett(0.8, b / 3 - 0.006, 0.05, M((0.7, -0.75, 0.025), (0, 0, -12)), "holz", bruch=-1)


# ======================================================================== Gefäße

def krug(m, kaputt):
    """Tonkrug mit Henkel und Ausguss."""
    prof = [(0.0, 0.0), (0.065, 0.0), (0.075, 0.01), (0.105, 0.09), (0.11, 0.15), (0.09, 0.22), (0.06, 0.26),
            (0.055, 0.29), (0.065, 0.31), (0.058, 0.315), (0.048, 0.3), (0.045, 0.27), (0.08, 0.2), (0.095, 0.15),
            (0.09, 0.09), (0.065, 0.02), (0.0, 0.02)]
    if not kaputt:
        bm = drehkoerper(prof, 24, False, False)
        for v in bm.verts:                         # Ausguss: Rand vorne nach außen ziehen
            if v.co.z > 0.28 and v.co.y < 0:
                f = max(0.0, -v.co.y / 0.06 - 0.6)
                v.co.y -= 0.02 * f; v.co.z += 0.01 * f
        m.teil(bm, "ton", None, uv="zylz", r=0.1)
        henkel = [(0.0, 0.06 + 0.075 * math.sin(math.pi * k / 10) ** 0.7, 0.275 - 0.135 * k / 10) for k in range(11)]
        m.seil(henkel, 0.012, 6, "ton")
    else:
        # zerbrochen: unterer Teil steht noch, Scherben liegen herum
        bm = drehkoerper(prof[:4] + [(0.104, 0.11), (0.096, 0.11)] + prof[-3:], 24, False, False)
        for v in bm.verts:
            if v.co.z > 0.08:
                v.co.z -= m.rnd.uniform(0, 0.04)
        m.teil(bm, "ton", None, uv="zylz", r=0.1)
        for k in range(5):
            a0 = m.rnd.uniform(0, 2 * math.pi); a1 = a0 + m.rnd.uniform(0.4, 0.9)
            scherbe = drehkoerper([(0.105, 0.0), (0.11, 0.05), (0.105, 0.09)], 4, False, False,
                                  winkel=(math.degrees(a0), math.degrees(a1)))
            bmesh.ops.solidify(scherbe, geom=scherbe.faces[:], thickness=0.008)
            m.teil(scherbe, "ton", M((0.18 * math.cos(k * 1.3), 0.18 * math.sin(k * 1.3) - 0.05, 0.02),
                                     (m.rnd.uniform(60, 110), 0, m.rnd.uniform(0, 360))) @ M((-0.1, 0, -0.045)), uv="zylz", r=0.1)


def humpen(m, kaputt):
    """Holzhumpen aus Dauben mit zwei Eisenreifen und Henkel."""
    h, r = 0.16, 0.05
    G0 = m.G
    if kaputt:
        m.G = M((0.0, 0.0, r + 0.01), (90, 0, 25)) @ M((0, 0, -h / 2))
    n = 10
    for i in range(n):
        a0 = 2 * math.pi * i / n + 0.01; a1 = 2 * math.pi * (i + 1) / n - 0.01
        props.daube(m, h, r, r * 1.08, a0, a1, dicke=0.008)
    for z in (0.025, h - 0.025):
        props.reifen(m, z, h, r, r * 1.08, breite=0.012, dicke=0.002)
    m.teil(drehkoerper([(0.0, 0.005), (r * 1.05, 0.005), (r * 1.05, 0.015), (0.0, 0.015)], 12), "holz", None)
    m.seil([(0.0, -r - 0.005, 0.13), (0.0, -r - 0.035, 0.12), (0.0, -r - 0.04, 0.07), (0.0, -r - 0.005, 0.04)], 0.008, 6, "holz")
    m.G = G0


def kochtopf(m, kaputt):
    """Eiserner Kochkessel auf drei Füßen mit Bügel, daneben ein kleiner Topf mit Deckel."""
    prof = [(0.0, 0.06), (0.12, 0.065), (0.2, 0.12), (0.23, 0.2), (0.22, 0.3), (0.2, 0.34), (0.215, 0.35), (0.215, 0.36),
            (0.19, 0.355), (0.205, 0.3), (0.21, 0.2), (0.185, 0.13), (0.11, 0.08), (0.0, 0.08)]
    G0 = m.G
    if kaputt:
        m.G = M((0, 0, 0.22), (0, 100, 30)) @ M((0, 0, -0.2))
    bm = drehkoerper(prof, 28, False, False)
    if kaputt:
        for v in bm.verts:                      # eingedellt
            if v.co.x > 0.15 and v.co.z > 0.2:
                v.co.x -= 0.03
    m.teil(bm, "eisen", None, uv="zylz", r=0.22)
    for k in range(3):
        a = 2 * math.pi * k / 3
        m.stab((0.14 * math.cos(a), 0.14 * math.sin(a), 0.09), (0.17 * math.cos(a), 0.17 * math.sin(a), 0.0), 0.016,
               "eisen", r2=0.012, biegen=0)
    for s in (-1, 1):
        m.teil(quader(0.03, 0.02, 0.04, fase=0.004), "eisen", M((s * 0.215, 0, 0.32)))
    if not kaputt:
        bugel = [(0.22 * math.cos(math.pi * k / 16), 0.0, 0.33 + 0.25 * math.sin(math.pi * k / 16)) for k in range(17)]
    else:
        bugel = [(0.22, 0.0, 0.33), (0.3, -0.05, 0.3), (0.42, -0.1, 0.25)]
    m.seil(bugel, 0.008, 5, "eisen")
    m.G = G0
    # kleiner Topf mit Stiel und Deckel
    tp = M((0.42, -0.2, 0.0), (0, 0, 30))
    topf = [(0.0, 0.0), (0.09, 0.0), (0.1, 0.12), (0.093, 0.12), (0.083, 0.008), (0.0, 0.008)]
    m.teil(drehkoerper(topf, 20, False, False), "eisen", tp, uv="zylz", r=0.1)
    m.stab(tp @ Vector((0.09, 0, 0.1)), tp @ Vector((0.27, 0, 0.13)), 0.01, "eisen", biegen=0)
    deckel = M((0.42, -0.2, 0.122)) if not kaputt else M((0.65, 0.05, 0.03), (75, 0, 10))
    m.teil(drehkoerper([(0.0, 0.025), (0.1, 0.0), (0.1, 0.006), (0.0, 0.03)], 20), "eisen", deckel)
    m.teil(drehkoerper([(0.0, 0.0), (0.015, 0.0), (0.012, 0.03), (0.0, 0.03)], 8), "holz", deckel @ M((0, 0, 0.025)))
    if kaputt:
        # verschüttete Asche/Brei als flacher Fleck
        m.teil(drehkoerper([(0.0, 0.004), (0.25, 0.0), (0.0, 0.006)], 16), "asche", M((-0.35, -0.15, 0.0), skal=(1.4, 0.8, 1)))


def buecher(m, kaputt):
    """Bücherstapel mit einem aufgeschlagenen Buch obendrauf und einer Kerze daneben."""
    if not kaputt:
        z = 0.0
        for k, (l, b, d, rot) in enumerate(((0.3, 0.22, 0.06, 4), (0.27, 0.2, 0.05, -7), (0.24, 0.17, 0.045, 12),
                                            (0.22, 0.16, 0.035, -3))):
            buch(m, M((0.01 * k, 0.0, z + d / 2), (0, 0, rot)), l, b, d)
            z += d
        # aufgeschlagenes Buch: zwei leicht gewölbte Seitenblöcke
        for s in (-1, 1):
            g = [[(s * 0.11 * j / 6, -0.08 + 0.16 * i / 2, 0.012 + 0.012 * math.sin(math.pi * j / 6) + 0.006 * (1 - j / 6))
                  for j in range(7)] for i in range(3)]
            m.teil(flaeche(g, 0.012), "putz", M((0.0, 0.0, z), (0, 0, 8)))
            m.teil(quader(0.115, 0.175, 0.004), "leder", M((s * 0.058, 0.0, z + 0.002), (0, 0, 8)) @ M(rot=(0, -s * 4, 0)))
        kerze(m, M((0.25, 0.08, 0.0)), 0.09, 0.016)
        m.teil(drehkoerper([(0.0, 0.0), (0.045, 0.0), (0.045, 0.01), (0.025, 0.012), (0.0, 0.012)], 12), "eisen",
               M((0.25, 0.08, 0.0)))
    else:
        # umgestoßen: Bücher liegen verstreut, eins aufgeklappt mit dem Rücken nach oben
        for k in range(4):
            a = m.rnd.uniform(0, 360)
            buch(m, M((-0.25 + 0.17 * k, m.rnd.uniform(-0.15, 0.15), 0.025), (0, 0, a)), 0.26 - 0.01 * k, 0.19, 0.045)
        for s in (-1, 1):
            m.teil(quader(0.12, 0.18, 0.004), "leder", M((0.3 + s * 0.05, 0.25, 0.04), (0, s * 35, 20)))
        m.teil(rundholz(0.016, 0.06, 8), "putz", M((0.0, -0.3, 0.016), (0, 0, 30)), uv="zyl", r=0.016)


# ======================================================================== Licht

def wandfackel(m, kaputt):
    """Eiserner Wandhalter mit Fackel. Ursprung auf der Wand (y = 0), das Modell ragt nach -y heraus."""
    m.teil(quader(0.09, 0.012, 0.22, fase=0.003), "eisen", M((0, -0.006, 0)))
    for z in (-0.08, 0.08):
        m.teil(drehkoerper([(0.0, 0.0), (0.008, 0.0), (0.006, 0.006), (0.0, 0.008)], 6), "eisen", M((0, -0.012, z), (90, 0, 0)))
    arm = [(0, -0.012, -0.05), (0, -0.08, -0.02), (0, -0.14, 0.02)]
    m.seil(arm, 0.009, 5, "eisen")
    ring = [(0.04 * math.cos(2 * math.pi * k / 12), -0.15 + 0.04 * math.sin(2 * math.pi * k / 12), 0.03) for k in range(13)]
    m.seil(ring, 0.006, 5, "eisen")
    if kaputt:
        # Fackel ausgebrannt und heruntergefallen: nur verkohlter Stummel hängt schief im Ring
        m.stab((0.0, -0.13, -0.08), (0.02, -0.17, 0.12), 0.022, "holz_verkohlt", r2=0.02)
        return
    oben = Vector((0.0, -0.3, 0.3)); unten = Vector((0.0, -0.12, -0.1))
    m.stab(unten, oben, 0.018, "holz", r2=0.022)
    # umwickelter Kopf (Stoff, verkohlt) und Flamme
    kopf = drehkoerper([(0.0, 0.0), (0.026, 0.0), (0.033, 0.04), (0.03, 0.08), (0.0, 0.09)], 10)
    verbiegen(kopf, m.rnd, 0.004, 0.03)
    rot = ausrichten(unten, oben) @ M(rot=(0, 90, 0))
    kopfpos = Matrix.Translation(oben) @ rot.to_3x3().to_4x4()
    m.teil(kopf, "holz_verkohlt", kopfpos @ M((0, 0, -0.06)), uv="zylz", r=0.033)
    flamme(m, M(oben + Vector((0, 0, 0.02))), 2.2)


def haengelampe(m, kaputt):
    """Öllampe an einer Kette, Ursprung am Deckenhaken; die Lampe hängt 0,8 m tiefer."""
    m.teil(drehkoerper([(0.0, 0.0), (0.04, 0.0), (0.04, -0.01), (0.0, -0.012)], 8), "eisen", None)
    tief = 0.8
    glieder = 14 if not kaputt else 7
    for k in range(glieder):
        z = -0.03 - k * (tief - 0.1) / 14
        dreh = 90 * (k % 2)
        g = [(0.012 * math.cos(2 * math.pi * i / 10), 0.0, z - 0.025 + 0.025 * math.sin(2 * math.pi * i / 10) * 1.4) for i in range(11)]
        m.seil(g if dreh == 0 else [(0.0, p[0], p[2]) for p in g], 0.003, 4, "eisen")
    if kaputt:
        # Kette gerissen, die Lampe ist heruntergefallen (sie liegt nicht mit im Modell, weil es an der Decke hängt)
        return
    # drei Kettchen zur Schale
    for k in range(3):
        a = 2 * math.pi * k / 3
        m.seil([(0.0, 0.0, -tief + 0.1), (0.1 * math.cos(a), 0.1 * math.sin(a), -tief - 0.08)], 0.003, 4, "eisen")
    schale = [(0.0, -tief - 0.16), (0.05, -tief - 0.155), (0.11, -tief - 0.1), (0.12, -tief - 0.08), (0.112, -tief - 0.08),
              (0.1, -tief - 0.095), (0.045, -tief - 0.145), (0.0, -tief - 0.15)]
    m.teil(drehkoerper(schale, 20, False, False), "eisen", None, uv="zylz", r=0.12)
    m.teil(drehkoerper([(0.0, -tief - 0.15), (0.1, -tief - 0.1), (0.0, -tief - 0.098)], 16), "asche", None)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        p = Vector((0.06 * math.cos(a), 0.06 * math.sin(a), -tief - 0.1))
        m.teil(rundholz(0.004, 0.03, 4), "seil", M(p, (0, 90, 0)), uv=None)
        flamme(m, M(p + Vector((0, 0, 0.012))), 1.3)


def kerzen(m, kaputt):
    """Gruppe aus drei Kerzen auf einem Teller (für Tische, Regale, Altäre)."""
    m.teil(drehkoerper([(0.0, 0.0), (0.09, 0.0), (0.1, 0.012), (0.094, 0.014), (0.085, 0.004), (0.0, 0.004)], 20), "eisen", None)
    for k, (x, y, h) in enumerate(((-0.03, 0.02, 0.16), (0.035, 0.025, 0.11), (0.0, -0.035, 0.07))):
        if kaputt:
            h *= 0.3
        kerze(m, M((x, y, 0.004)), h, 0.017, brennt=not kaputt)
    if kaputt:
        m.teil(drehkoerper([(0.0, 0.0), (0.06, 0.0), (0.0, 0.004)], 12), "putz", M((0.0, 0.0, 0.004), skal=(1.3, 0.9, 1)))


def kerzenstaender(m, kaputt):
    """Schmiedeeiserner Standleuchter, 1,5 m, drei Arme mit Kerzen."""
    h = 1.45
    if kaputt:
        boden_setzen(m, (0, 86, 20), (0, 0, 0))
        m.G = Matrix.Translation((0, 0, 0.06)) @ m.G
    for k in range(3):
        a = 2 * math.pi * k / 3
        fuss = [(0.0, 0.0, 0.18), (0.08 * math.cos(a), 0.08 * math.sin(a), 0.06), (0.2 * math.cos(a), 0.2 * math.sin(a), 0.0),
                (0.23 * math.cos(a), 0.23 * math.sin(a), 0.03)]
        m.seil(fuss, 0.012, 5, "eisen")
    m.stab((0, 0, 0.15), (0, 0, h), 0.014, "eisen", biegen=0)
    for z in (0.5, 0.95):
        m.teil(drehkoerper([(0.0, -0.03), (0.03, 0.0), (0.0, 0.03)], 10), "eisen", M((0, 0, z)))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        r = 0.0 if k == 0 else 0.2
        if k > 0:
            arm = [(0, 0, h - 0.15)] + [(r * t / 6 * math.cos(a), r * t / 6 * math.sin(a), h - 0.15 + 0.12 * math.sin(math.pi * t / 12))
                                        for t in range(1, 7)]
            m.seil(arm, 0.009, 5, "eisen")
        p = Vector((r * math.cos(a), r * math.sin(a), (h if k == 0 else h - 0.03)))
        m.teil(drehkoerper([(0.0, 0.0), (0.045, 0.0), (0.05, 0.012), (0.04, 0.012), (0.02, 0.004), (0.0, 0.004)], 12), "eisen", M(p))
        if not kaputt:
            kerze(m, M(p + Vector((0, 0, 0.004))), 0.14 if k == 0 else 0.11, 0.018)
    m.G = None
    if kaputt:
        kerze(m, M((0.3, -0.35, 0.018), (90, 0, 40)), 0.1, 0.018, brennt=False)


# ======================================================================== Draußen

def grabstein(m, kaputt):
    """Grabstein mit Rundbogen und eingemeißeltem Kreuz, davor ein Erdhügel."""
    b, d, h = 0.55, 0.12, 0.85
    stein = klotz(m.rnd, b, d, h, fase=0.015, rauh=0.006, abgeschlagen=0.4 if kaputt else 0.15)
    for v in stein.verts:                       # Rundbogen oben
        if v.co.z > 0:
            x = v.co.x / (b / 2)
            v.co.z = min(v.co.z, h / 2 - 0.12 + 0.12 * math.sqrt(max(0.0, 1 - x * x)) * 1.05)
    oben = h if not kaputt else h * 0.55
    if kaputt:
        for v in stein.verts:
            if v.co.z > -h / 2 + oben - 0.05:
                v.co.z = -h / 2 + oben - m.rnd.uniform(0, 0.12) * (0.5 + v.co.x / b)
    m.teil(stein, "stein", M((0, 0, h / 2 - 0.08), (0, 0 if not kaputt else 7, 0)))
    if not kaputt:
        for (lx, lz, z) in ((0.04, 0.3, 0.5), (0.2, 0.04, 0.58)):
            m.teil(quader(lx, 0.02, lz), "asche", M((0, -d / 2 + 0.006, z)))
    else:
        # abgebrochenes Oberteil liegt davor im Gras
        obert = klotz(m.rnd, b * 0.9, d, 0.34, fase=0.015, rauh=0.008, abgeschlagen=0.6)
        m.teil(obert, "stein", M((0.15, -0.55, 0.06), (88, 0, 20)))
    huegel = drehkoerper([(0.0, 0.12), (0.25, 0.1), (0.4, 0.05), (0.48, 0.0), (0.0, 0.0)], 16)
    for v in huegel.verts:
        v.co.y *= 2.6
    verbiegen(huegel, m.rnd, 0.02, 0.2)
    m.teil(huegel, "asche", M((0, -0.95, -0.02)))


def brunnen(m, kaputt):
    """Dorfbrunnen: runde Mauer aus Steinen, zwei Pfosten mit Dach, Haspel mit Seil und Eimer."""
    r, h = 0.75, 0.75
    lagen = 5
    for lg in range(lagen):
        n = 14
        z = h * (lg + 0.5) / lagen
        for k in range(n):
            if kaputt and lg >= 3 and 3 <= k <= 7:
                continue
            a = 2 * math.pi * (k + 0.5 * (lg % 2)) / n
            st = klotz(m.rnd, 2 * math.pi * r / n - 0.02, 0.24, h / lagen - 0.015, fase=0.02, rauh=0.01)
            m.teil(st, "stein", M((r * math.cos(a), r * math.sin(a), z), (0, 0, math.degrees(a) + 90)))
    # Abdeckkranz
    if not kaputt:
        m.teil(drehkoerper([(r - 0.14, h), (r + 0.15, h), (r + 0.15, h + 0.06), (r - 0.14, h + 0.06)], 28, False, False),
               "stein", None, uv="zylz", r=r)
    m.teil(drehkoerper([(0.0, 0.3), (r - 0.1, 0.3), (r - 0.1, 0.31), (0.0, 0.31)], 20), "asche", None)
    # Pfosten, Dach, Haspel
    for s in (-1, 1):
        if kaputt and s > 0:
            m.kantholz((s * (r + 0.02), 0, 0.0), (s * (r + 0.02), 0, 1.0), 0.1, 0.1, bruch=-1)
            continue
        m.kantholz((s * (r + 0.02), 0, 0.0), (s * (r + 0.02), 0, 1.95), 0.1, 0.1)
    if not kaputt:
        m.kantholz((-r - 0.2, 0, 1.95), (r + 0.2, 0, 1.95), 0.1, 0.08)
        for sy in (-1, 1):
            for i in range(3):
                z = 1.98 + 0.08 * (2 - i) * 1.0
                y = sy * (0.1 + 0.2 * i)
                m.brett(2 * r + 0.6, 0.22, 0.025, M((0, y, z + 0.05), (sy * -28, 0, 0)), "holz_alt")
        m.teil(rundholz(0.06, 2 * r, 10), "holz", M((0, 0, 1.35)), uv="zyl", r=0.06)
        kurbel = [(r + 0.06, 0, 1.35), (r + 0.14, 0, 1.35), (r + 0.14, 0, 1.15), (r + 0.25, 0, 1.15)]
        m.seil(kurbel, 0.012, 5, "eisen")
        m.seil([(0.0, 0.0, 1.29), (0.0, 0.0, 0.9)], 0.01)
        eimer = M((0, 0, 0.62))
    else:
        eimer = M((0.95, -0.6, 0.0), (0, 0, 20))
        m.kantholz((-r - 0.2, 0.1, 0.03), (r + 0.1, 0.6, 0.03), 0.1, 0.08, bruch=1)
        for k in range(3):
            st = klotz(m.rnd, 0.3, 0.22, 0.14, fase=0.02, rauh=0.01, abgeschlagen=0.4)
            m.teil(st, "stein", M((0.4 + 0.25 * k, -1.0 + 0.1 * k, 0.07), (0, 0, 30 * k)))
    n = 12
    for i in range(n):
        a0 = 2 * math.pi * i / n + 0.01; a1 = 2 * math.pi * (i + 1) / n - 0.01
        G0 = m.G
        m.G = eimer
        props.daube(m, 0.28, 0.14, 0.12, a0, a1, dicke=0.012)
        m.G = G0
    for z in (0.05, 0.22):
        props.reifen(m, z, 0.28, 0.14, 0.12, breite=0.018, matrix=eimer)
    m.seil([eimer @ Vector((-0.14, 0, 0.26)), eimer @ Vector((0, 0, 0.38)), eimer @ Vector((0.14, 0, 0.26))], 0.006, 5, "eisen")


def trainingspuppe(m, kaputt):
    """Strohpuppe zum Üben: Pfahl im Boden, Querholz als Arme, Strohsack-Körper und -Kopf, mit Seil verschnürt."""
    if kaputt:
        boden_setzen(m, (14, -6, 0), (0, 0, 0))
    m.kantholz((0, 0, 0), (0, 0, 1.75 if not kaputt else 1.2), 0.1, 0.1, bruch=-1 if kaputt else 0)
    if not kaputt:
        m.kantholz((-0.32, 0, 1.38), (0.32, 0, 1.38), 0.07, 0.06)
    else:
        m.kantholz((-0.32, 0, 1.15), (0.05, 0, 1.15), 0.07, 0.06, bruch=1)
    koerper = drehkoerper([(0.0, 0.0), (0.15, 0.02), (0.2, 0.15), (0.21, 0.35), (0.18, 0.5), (0.0, 0.55)], 16)
    verbiegen(koerper, m.rnd, 0.025, 0.12)
    for v in koerper.verts:
        v.co.y *= 0.75
    if kaputt:
        for v in koerper.verts:
            if v.co.z > 0.25 and v.co.x > 0:
                v.co.x *= 0.4
    m.teil(koerper, "stroh", M((0, 0, 0.85)), uv="zylz", r=0.2)
    for z in (0.95, 1.12, 1.3):
        ring = [(0.2 * math.cos(2 * math.pi * k / 14), 0.155 * math.sin(2 * math.pi * k / 14), z) for k in range(15)]
        if not (kaputt and z > 1.2):
            m.seil(ring, 0.008)
    for s in (-1, 1):
        if kaputt and s > 0:
            continue
        arm = drehkoerper([(0.0, 0.0), (0.06, 0.02), (0.065, 0.2), (0.05, 0.24), (0.0, 0.25)], 10)
        verbiegen(arm, m.rnd, 0.01, 0.1)
        m.teil(arm, "stroh", M((s * 0.2, 0, 1.38), (0, s * 90, 0)), uv="zylz", r=0.06)
    if not kaputt:
        kopf = drehkoerper([(0.0, 0.0), (0.09, 0.02), (0.12, 0.12), (0.1, 0.2), (0.0, 0.23)], 14)
        verbiegen(kopf, m.rnd, 0.015, 0.08)
        m.teil(kopf, "stoff", M((0, 0, 1.52)), uv="zylz", r=0.12)
        m.seil([(0.11 * math.cos(2 * math.pi * k / 12), 0.11 * math.sin(2 * math.pi * k / 12), 1.55) for k in range(13)], 0.007)
        # zwei Kreuze als Trefferzonen auf der Brust
        for z in (1.2,):
            for rz in (45, -45):
                m.teil(quader(0.14, 0.01, 0.025), "farbe_rot", M((0, -0.16, z), (0, rz, 0)))
    m.G = None
    if kaputt:
        kopf = drehkoerper([(0.0, 0.0), (0.09, 0.02), (0.12, 0.12), (0.1, 0.2), (0.0, 0.23)], 14)
        verbiegen(kopf, m.rnd, 0.02, 0.08)
        m.teil(kopf, "stoff", M((0.45, -0.4, 0.1), (100, 0, 30)), uv="zylz", r=0.12)
        for k in range(10):                     # herausgerissenes Stroh am Boden
            m.teil(quader(m.rnd.uniform(0.08, 0.2), 0.004, 0.002), "stroh",
                   M((m.rnd.uniform(-0.5, 0.5), m.rnd.uniform(-0.6, 0.1), 0.002), (0, 0, m.rnd.uniform(0, 180))))


def zielscheibe(m, kaputt):
    """Strohscheibe mit bemalten Ringen auf einem Holzgestell, leicht nach hinten geneigt."""
    r = 0.55
    neig = -15
    mitte = Vector((0, 0.0, 1.05))
    scheibe = M(mitte, (90 + neig if not kaputt else 90 + neig, 0, 0)) if not kaputt else M((0.2, -0.3, 0.09), (5, 0, 20))
    prof = [(0.0, -0.09), (r - 0.03, -0.09), (r, -0.06), (r, 0.06), (r - 0.03, 0.09), (0.0, 0.09)]
    bm = drehkoerper(prof, 32)
    if kaputt:
        for v in bm.verts:
            if v.co.x > r * 0.5 and v.co.y > 0:
                v.co.x *= 0.8
    m.teil(bm, "stroh", scheibe, uv="zylz", r=r)
    # Ringe als flache Scheiben auf der Vorderseite (in der Scheibenebene: z der Scheibe zeigt nach vorne)
    for k, (ra, mat) in enumerate(((0.42, "farbe_weiss"), (0.33, "farbe_rot"), (0.24, "farbe_weiss"), (0.15, "farbe_rot"),
                                   (0.07, "farbe_weiss"))):
        ring = drehkoerper([(0.0, 0.0915 + k * 0.001), (ra, 0.0915 + k * 0.001), (ra, 0.093 + k * 0.001), (0.0, 0.093 + k * 0.001)], 32)
        m.teil(ring, mat, scheibe, uv="zylz", r=ra)
    if not kaputt:
        # Pfeile stecken in der Scheibe
        for (x, y, rx, rz) in ((0.08, 0.1, 6, -4), (-0.2, -0.05, -3, 8), (0.02, -0.25, 10, 3)):
            spitze = scheibe @ M((x, y, 0.03), (rx, rz, 0))
            m.stab(spitze @ Vector((0, 0, 0)), spitze @ Vector((0, 0, 0.65)), 0.005, "holz", seg=5)
            for f in range(3):
                a = 2 * math.pi * f / 3
                m.teil(quader(0.09, 0.002, 0.018), "farbe_weiss", spitze @ M((0, 0, 0.6), (0, -90, math.degrees(a))) @ M((0, 0, 0.012)))
    # Gestell: zwei Beine vorne, eins hinten, Querlatte
    oben = Vector((0, 0.15, 1.62)) if not kaputt else Vector((0, 0.15, 1.2))
    for s in (-1, 1):
        if kaputt and s > 0:
            m.kantholz((s * 0.45, -0.05, 0.0), (s * 0.3, 0.05, 0.8), 0.06, 0.05, bruch=-1)
            continue
        m.kantholz((s * 0.45, -0.1, 0.0), oben + Vector((s * 0.05, 0, 0)), 0.06, 0.05)
    m.kantholz((0, 0.85, 0.0), oben, 0.06, 0.05)
    if not kaputt:
        m.kantholz((-0.4, 0.06, 0.55), (0.4, 0.06, 0.55), 0.06, 0.04)


# ======================================================================== Schmiede und Waffen

def amboss(m, kaputt):
    """Amboss auf einem Holzklotz, Hammer und Zange obenauf."""
    stumpf = drehkoerper([(0.0, 0.0), (0.27, 0.0), (0.25, 0.04), (0.24, 0.5), (0.0, 0.5)], 16)
    verbiegen(stumpf, m.rnd, 0.01, 0.15)
    m.teil(stumpf, "holz", None, uv="zylz", r=0.25)
    m.teil(drehkoerper([(0.0, 0.5), (0.24, 0.5), (0.24, 0.505), (0.0, 0.505)], 16), "holz", None)
    for z in (0.08, 0.42):
        props.reifen(m, z, 0.5, 0.245, 0.245, breite=0.03)
    G0 = m.G
    if kaputt:
        # vom Klotz gefallen: der Amboss liegt daneben auf dem Boden
        m.G = Matrix.Translation((0.25, -0.6, -0.49)) @ M(rot=(0, 0, 25))
    z0 = 0.505
    # Fuß, Taille, Körper, Horn und Ende als einzelne Blöcke (Schmiedestahl dunkel)
    m.teil(quader(0.3, 0.2, 0.06, fase=0.008), "eisen", M((0, 0, z0 + 0.03)))
    taille = quader(0.18, 0.12, 0.12, 1, 1, 2, fase=0.008)
    for v in taille.verts:
        if abs(v.co.z) < 1e-4:
            v.co.x *= 0.75; v.co.y *= 0.8
    m.teil(taille, "eisen", M((0, 0, z0 + 0.12)))
    m.teil(quader(0.34, 0.13, 0.1, fase=0.006), "eisen", M((0, 0, z0 + 0.23)))
    horn = drehkoerper([(0.055, 0.0), (0.04, 0.08), (0.02, 0.16), (0.0, 0.2)], 10)
    m.teil(horn, "eisen", M((0.17, 0, z0 + 0.235), (0, 90, 0)) @ M(skal=(1.0, 1.0, 1.0)))
    m.teil(quader(0.08, 0.1, 0.06, fase=0.004), "eisen", M((-0.2, 0, z0 + 0.25)))
    m.G = G0
    if not kaputt:
        # Hammer und Zange liegen auf dem Klotz
        hm = M((-0.05, -0.17, z0 + 0.01), (0, 0, 20))
        m.stab(hm @ Vector((-0.15, 0, 0.012)), hm @ Vector((0.15, 0, 0.012)), 0.012, "holz")
        m.teil(quader(0.04, 0.1, 0.035, fase=0.004), "eisen", hm @ M((0.16, 0, 0.02)))
        zm = M((0.08, 0.17, z0 + 0.006), (0, 0, -15))
        for s in (-1, 1):
            m.seil([zm @ Vector((-0.2, s * 0.012, 0.006)), zm @ Vector((0.05, s * 0.004, 0.006)),
                    zm @ Vector((0.11, -s * 0.012, 0.006))], 0.006, 4, "eisen")
    else:
        m.stab((0.45, 0.25, 0.012), (0.75, 0.1, 0.012), 0.012, "holz")
        m.teil(quader(0.04, 0.1, 0.035, fase=0.004), "eisen", M((0.78, 0.09, 0.018), (0, 0, -25)))


def klinge(m, matrix, laenge, breite=0.05, spitz=True, mat="eisen"):
    """Flache Klinge entlang +z (Angel bei z = 0)."""
    pts = [(-breite / 2, 0.0), (breite / 2, 0.0), (breite / 2 * 0.85, laenge * 0.85), (0.0 if spitz else breite / 3, laenge),
           (-breite / 2 * 0.85 if spitz else -breite / 3, laenge * (0.85 if spitz else 1.0))]
    bm = bmesh.new()
    vorne = [bm.verts.new((x, -0.004, z)) for x, z in pts]
    hinten = [bm.verts.new((x, 0.004, z)) for x, z in pts]
    bm.faces.new(vorne); bm.faces.new(list(reversed(hinten)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((vorne[i], vorne[j], hinten[j], hinten[i]))
    for v in bm.verts:                           # Schneiden dünn
        if abs(v.co.x) > breite * 0.3:
            v.co.y *= 0.2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m.teil(bm, mat, matrix)


def schwert(m, matrix, laenge=0.95):
    m.stab(matrix @ Vector((0, 0, 0.0)), matrix @ Vector((0, 0, 0.17)), 0.014, "leder")
    m.teil(quader(0.04, 0.03, 0.04, fase=0.008), "eisen", matrix @ M((0, 0, -0.01)))
    m.teil(quader(0.2, 0.025, 0.025, fase=0.004), "eisen", matrix @ M((0, 0, 0.185)))
    klinge(m, matrix @ M((0, 0, 0.2)), laenge - 0.2, 0.05)


def speer(m, matrix, laenge=1.9):
    m.stab(matrix @ Vector((0, 0, 0)), matrix @ Vector((0, 0, laenge - 0.22)), 0.016, "holz", biegen=0.003)
    m.teil(drehkoerper([(0.018, 0.0), (0.016, 0.07), (0.0, 0.08)], 8), "eisen", matrix @ M((0, 0, laenge - 0.25)))
    klinge(m, matrix @ M((0, 0, laenge - 0.2)), 0.2, 0.05)


def axt(m, matrix, laenge=0.75):
    m.stab(matrix @ Vector((0, 0, 0)), matrix @ Vector((0, 0, laenge)), 0.016, "holz", biegen=0.003)
    kopf = bmesh.new()
    pts = [(-0.02, laenge - 0.12), (0.03, laenge - 0.1), (0.15, laenge - 0.18), (0.17, laenge - 0.02), (0.03, laenge - 0.04),
           (-0.04, laenge - 0.04), (-0.04, laenge - 0.12)]
    vorne = [kopf.verts.new((x, -0.012, z)) for x, z in pts]
    hinten = [kopf.verts.new((x, 0.012, z)) for x, z in pts]
    kopf.faces.new(vorne); kopf.faces.new(list(reversed(hinten)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        kopf.faces.new((vorne[i], vorne[j], hinten[j], hinten[i]))
    for v in kopf.verts:
        if v.co.x > 0.1:
            v.co.y *= 0.25
    bmesh.ops.recalc_face_normals(kopf, faces=kopf.faces[:])
    m.teil(kopf, "eisen", matrix)


def waffenstaender(m, kaputt):
    """Waffenständer: Gestell mit zwei Querlatten, Schwerter, Speere und Äxte lehnen darin."""
    l = 1.4
    if kaputt:
        boden_setzen(m, (-75, 0, 0), (0, 0.15, 0))
        m.G = Matrix.Translation((0, 0, 0.06)) @ m.G
    for s in (-1, 1):
        m.kantholz((s * l / 2, -0.15, 0.0), (s * l / 2, 0.15, 0.0), 0.07, 0.06)
        m.kantholz((s * l / 2, 0.08, 0.0), (s * l / 2, 0.08, 1.3), 0.07, 0.07)
    m.kantholz((-l / 2, 0.08, 1.25), (l / 2, 0.08, 1.25), 0.07, 0.05)
    m.kantholz((-l / 2, -0.05, 0.15), (l / 2, -0.05, 0.15), 0.12, 0.04, oben=(0, 0, 1))
    # Latte oben mit Kerben angedeutet durch Halteklötze
    for k in range(6):
        x = -l / 2 + 0.15 + k * (l - 0.3) / 5
        m.teil(quader(0.03, 0.04, 0.05, fase=0.004), "holz", M((x - 0.04, 0.02, 1.27)))
    if not kaputt:
        waffen = [("schwert", -0.55), ("speer", -0.35), ("schwert", -0.12), ("axt", 0.1), ("speer", 0.32), ("schwert", 0.52)]
        for i, (art, x) in enumerate(waffen):
            neig = 6 + 3 * (i % 2)
            mx = M((x, -0.06, 0.17), (-neig, 0, 4 * ((i % 3) - 1)))
            if art == "schwert":
                schwert(m, mx @ M((0, 0, 1.08), (180, 0, 0)), 1.05)
            elif art == "speer":
                speer(m, mx, 1.95)
            else:
                axt(m, mx, 1.15)
    m.G = None
    if kaputt:
        schwert(m, M((-0.4, -0.7, 0.012), (-90, 0, 70)), 1.05)
        speer(m, M((0.6, -0.4, 0.016), (-90, 0, 15)), 1.95)


def ruestungsstaender(m, kaputt):
    """Rüstungsständer: Holzkreuz auf Fußkreuz, darauf Brustpanzer, Helm und Schild davor."""
    if kaputt:
        boden_setzen(m, (82, 0, 20), (0, -0.25, 0))
        m.G = Matrix.Translation((0, 0, 0.08)) @ m.G
    m.kantholz((-0.3, 0, 0.035), (0.3, 0, 0.035), 0.07, 0.07)
    m.kantholz((0, -0.3, 0.035), (0, 0.3, 0.035), 0.07, 0.07)
    m.kantholz((0, 0, 0.07), (0, 0, 1.55), 0.06, 0.06)
    m.kantholz((-0.24, 0, 1.38), (0.24, 0, 1.38), 0.06, 0.05)
    # Brustpanzer: Halbschale vorne und hinten
    for s in (-1, 1):
        bm = drehkoerper([(0.13, 0.0), (0.17, 0.1), (0.19, 0.25), (0.18, 0.38), (0.12, 0.45)], 16, False, False,
                         winkel=(180 if s < 0 else 0, 360 if s < 0 else 180))
        for v in bm.verts:
            v.co.y *= 0.62; v.co.x *= 1.1
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.006)
        if kaputt and s < 0:
            for v in bm.verts:
                if v.co.x > 0.08 and v.co.z > 0.2:
                    v.co.y *= 0.6
        m.teil(bm, "eisen", M((0, 0, 0.98)), uv="zylz", r=0.18)
    for s in (-1, 1):                            # Schulterstücke
        sch = drehkoerper([(0.0, 0.0), (0.09, 0.0), (0.08, 0.04), (0.0, 0.07)], 12, winkel=(0, 360))
        m.teil(sch, "eisen", M((s * 0.21, 0, 1.36), (0, s * 35, 0)))
        m.seil([(s * 0.12, -0.11, 1.4), (s * 0.15, -0.02, 1.47), (s * 0.12, 0.08, 1.4)], 0.008, 5, "leder")
    m.teil(quader(0.36, 0.24, 0.05, fase=0.01), "leder", M((0, 0, 0.98)))
    if not kaputt:
        helm = drehkoerper([(0.0, 0.2), (0.07, 0.19), (0.115, 0.13), (0.12, 0.0), (0.112, 0.0), (0.108, 0.13), (0.065, 0.183),
                            (0.0, 0.193)], 18, False, False)
        for v in helm.verts:
            v.co.y *= 1.12
        m.teil(helm, "eisen", M((0, 0, 1.45)), uv="zylz", r=0.12)
        m.teil(quader(0.012, 0.03, 0.14), "eisen", M((0, -0.13, 1.51)))
    m.G = None
    # Rundschild lehnt vorne am Fuß
    sm = M((0.0, -0.42, 0.33), (72, 0, 0)) if not kaputt else M((0.55, -0.3, 0.02), (0, 0, 0))
    m.teil(drehkoerper([(0.0, 0.03), (0.33, 0.012), (0.34, 0.0), (0.0, 0.0)], 28), "holz", sm, uv="box")
    m.teil(drehkoerper([(0.33, -0.003), (0.35, 0.006), (0.35, 0.018), (0.33, 0.016)], 28, False, False), "eisen", sm, uv="zylz", r=0.34)
    m.teil(drehkoerper([(0.0, 0.07), (0.06, 0.06), (0.08, 0.03), (0.0, 0.03)], 14), "eisen", sm)
    if kaputt:
        helm = drehkoerper([(0.0, 0.2), (0.07, 0.19), (0.115, 0.13), (0.12, 0.0), (0.112, 0.0), (0.108, 0.13), (0.065, 0.183),
                            (0.0, 0.193)], 18, False, False)
        m.teil(helm, "eisen", M((-0.5, -0.55, 0.12), (110, 0, 40)), uv="zylz", r=0.12)


MODELLE = {"stuhl_armlehne": stuhl_armlehne, "stuhl_brett": stuhl_brett, "tisch_rund": tisch_rund, "tisch_lang": tisch_lang,
           "krug": krug, "humpen": humpen, "kochtopf": kochtopf, "buecher": buecher,
           "wandfackel": wandfackel, "haengelampe": haengelampe, "kerzen": kerzen, "kerzenstaender": kerzenstaender,
           "grabstein": grabstein, "brunnen": brunnen, "trainingspuppe": trainingspuppe, "zielscheibe": zielscheibe,
           "amboss": amboss, "waffenstaender": waffenstaender, "ruestungsstaender": ruestungsstaender}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
