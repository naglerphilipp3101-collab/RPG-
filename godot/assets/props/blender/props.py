"""Lager- und Dorf-Props, jedes heil und kaputt.
Aufruf: python props.py -- <zielordner/modelle> [--nur kiste,fass] [--vorschau <ordner>]
Ergebnis: <name>.glb und <name>_kaputt.glb, Boden bei z = 0, Mitte im Ursprung, Vorderseite zeigt nach -y.
Materialien tragen feste Namen (holz, holz_alt, eisen, stoff, ...); Godot setzt dafür die eigenen
Materialien aus ../materialien ein (prop.gd)."""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, ausrichten, quader, rundholz, drehkoerper, rohr, flaeche, verbiegen, bruchkante


# ======================================================================== Kiste

def bretterwand(m, breite, hoehe, n, matrix, mat="holz", dicke=0.02, fuge=0.006, fehlt=(), bruch=None):
    """Waagerechte Bretter in der x-z-Ebene (Mitte im Ursprung), Dicke in y.
    fehlt: Indizes ohne Brett, bruch: {index: (seite, länge)} kürzeres, abgebrochenes Brett."""
    bh = (hoehe - fuge * (n - 1)) / n
    for i in range(n):
        if i in fehlt:
            continue
        z = -hoehe / 2 + bh / 2 + i * (bh + fuge)
        if bruch and i in bruch:
            seite, laenge = bruch[i]
            x = -seite * (breite - laenge) / 2
            m.brett(laenge, dicke, bh, matrix @ M((x, 0, z)), mat, bruch=seite, bruch_tiefe=0.1)
        else:
            m.brett(breite, dicke, bh, matrix @ M((0, 0, z)), mat)


def kiste(m, kaputt):
    bx, by, h = 0.8, 0.6, 0.6
    d = 0.02; latte = 0.05
    # Seitenwände: vorne/hinten (x-z), links/rechts (um z gedreht)
    vorne_fehlt, vorne_bruch = ((1,), {0: (1, 0.45), 2: (-1, 0.3)}) if kaputt else ((), None)
    bretterwand(m, bx, h - 0.04, 3, M((0, -by / 2 + d / 2, h / 2)), fehlt=vorne_fehlt, bruch=vorne_bruch)
    bretterwand(m, bx, h - 0.04, 3, M((0, by / 2 - d / 2, h / 2)))
    for s in (-1, 1):
        bretterwand(m, by - 2 * d, h - 0.04, 3, M((s * (bx / 2 - d / 2), 0, h / 2), (0, 0, 90)))
    # Boden
    m.brett(bx - 0.01, by - 0.01, d, M((0, 0, 0.03)), "holz")
    # Eckleisten senkrecht und Querleisten
    for sx in (-1, 1):
        for sy in (-1, 1):
            if kaputt and sx == 1 and sy == -1:
                m.kantholz((sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), 0.01),
                           (sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), h * 0.55), latte, 0.022, oben=(0, sy, 0),
                           bruch=1)
                continue
            m.kantholz((sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), 0.0),
                       (sx * (bx / 2 - latte / 2 + 0.005), sy * (by / 2 + 0.008), h - 0.01), latte, 0.022, oben=(0, sy, 0))
    for sy in (-1, 1):
        if not (kaputt and sy == -1):
            m.kantholz((-bx / 2 + 0.08, sy * (by / 2 + 0.008), h - 0.1), (bx / 2 - 0.08, sy * (by / 2 + 0.008), 0.1),
                       0.08, 0.02, oben=(0, sy, 0))
    # Eisenwinkel an den oberen Ecken
    for sx in (-1, 1):
        for sy in (-1, 1):
            if kaputt and sx == 1 and sy == -1:
                continue
            for dx, dy in ((0.06, 0), (0, 0.06)):
                p = Vector((sx * (bx / 2 + 0.012 - dx / 2), sy * (by / 2 + 0.012 - dy / 2), h - 0.05))
                m.teil(quader(0.004 + dx, 0.004 + dy, 0.09, fase=0.001), "eisen", M(p), versatz=(m.rnd.random(), 0))
    # Deckel
    deckel = M((0, 0, h + 0.012)) if not kaputt else M((0.75, -0.25, 0.32), (0, -78, 25))
    for i in range(3):
        y = -by / 2 + 0.1 + i * 0.2
        m.brett(bx + 0.02, 0.195, d, deckel @ M((0, y + 0.0, 0)), "holz")
    for x in (-bx / 2 + 0.1, bx / 2 - 0.1):
        m.brett(latte, by - 0.06, 0.02, deckel @ M((x, 0, -0.02)), "holz", nx=2)
    if kaputt:
        # herausgebrochene Bretter liegen davor
        m.brett(0.42, 0.18, d, M((-0.15, -0.62, 0.012), (0, 0, 14)), "holz", bruch=1)
        m.brett(0.33, 0.18, d, M((0.25, -0.55, 0.035), (12, 0, -36)), "holz", bruch=-1)


# ======================================================================== Fass

def fass_radius(z, h, r_bauch, r_ende):
    t = (z / h) * 2 - 1
    return r_ende + (r_bauch - r_ende) * (1 - t * t)


def daube(m, h, r_bauch, r_ende, a0, a1, dicke=0.022, kippen=0.0, laenge=1.0, mat="holz", bruch=False):
    """Eine Fassdaube als gebogenes Brett (Faser entlang z). kippen: oberes Ende nach außen (m),
    laenge < 1: oben abgebrochen."""
    nz, na = 8, 2
    bm = bmesh.new()
    ringe = []
    for i in range(nz + 1):
        t = i / nz * laenge
        z = t * h
        ra = fass_radius(z, h, r_bauch, r_ende) + kippen * t * t
        reihe = []
        for k in range(na + 1):
            a = a0 + (a1 - a0) * k / na
            aussen = Vector((ra * math.cos(a), ra * math.sin(a), z))
            innen = Vector(((ra - dicke) * math.cos(a), (ra - dicke) * math.sin(a), z))
            reihe.append((bm.verts.new(aussen), bm.verts.new(innen)))
        ringe.append(reihe)
    for i in range(nz):
        for k in range(na):
            a, b, c, d = ringe[i][k], ringe[i][k + 1], ringe[i + 1][k + 1], ringe[i + 1][k]
            bm.faces.new((a[0], b[0], c[0], d[0]))
            bm.faces.new((d[1], c[1], b[1], a[1]))
    for i in range(nz):
        for k in (0, na):
            a, d = ringe[i][k], ringe[i + 1][k]
            f = (a[0], d[0], d[1], a[1]) if k == 0 else (a[1], d[1], d[0], a[0])
            bm.faces.new(f)
    for i, rev in ((0, False), (nz, True)):
        for k in range(na):
            a, b = ringe[i][k], ringe[i][k + 1]
            f = (a[0], a[1], b[1], b[0])
            bm.faces.new(tuple(reversed(f)) if rev else f)
    bm.normal_update()
    if bruch:
        oben = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if abs(v.co.z - oben) < 1e-4:
                v.co.z -= m.rnd.uniform(0, 0.09)
    verbiegen(bm, m.rnd, 0.003, 0.4)
    m.teil(bm, mat, None, uv="boxz")


def reifen(m, z, h, r_bauch, r_ende, breite=0.035, dicke=0.005, kippen=0.0, matrix=None):
    r = fass_radius(z, h, r_bauch, r_ende) + kippen
    prof = [(r - 0.002, z - breite / 2), (r + dicke, z - breite / 2), (r + dicke, z + breite / 2), (r - 0.002, z + breite / 2)]
    bm = drehkoerper(prof, 32, False, False)
    # Innen schließen: Ober- und Unterkante als Ring
    m.teil(bm, "eisen", matrix, uv="zylz", r=r)


def fass(m, kaputt):
    h, rb, re = 0.95, 0.33, 0.275
    n = 18
    luecke = 0.004
    fehlen = {3, 4, 11} if kaputt else set()
    for i in range(n):
        if i in fehlen:
            continue
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n
        a0 += luecke / rb; a1 -= luecke / rb
        if kaputt:
            kipp = 0.10 + 0.08 * m.rnd.random() if i not in (8, 9) else 0.03
            laenge = 1.0 if i % 4 else 0.62 + 0.2 * m.rnd.random()
            daube(m, h, rb, re, a0, a1, kippen=kipp, laenge=laenge, bruch=laenge < 1)
        else:
            daube(m, h, rb, re, a0, a1)
    hoehen = (0.07, 0.25, h - 0.25, h - 0.07)
    for i, z in enumerate(hoehen):
        if kaputt and i >= 2:
            continue
        reifen(m, z, h, rb, re, kippen=0.0 if not kaputt else 0.002)
    # Böden (Deckel) innen
    for z in (0.05, h - 0.045):
        if kaputt and z > 0.5:
            continue
        r = fass_radius(z, h, rb, re) - 0.018
        bm = drehkoerper([(0.0, z - 0.012), (r, z - 0.012), (r, z + 0.012), (0.0, z + 0.012)], 24)
        m.teil(bm, "holz", None, uv="box")
    if kaputt:
        # Deckel und abgesprungene Reifen liegen am Boden, zwei Dauben daneben
        r = re - 0.02
        bm = drehkoerper([(0.0, 0), (r, 0), (r, 0.024), (0.0, 0.024)], 24)
        m.teil(bm, "holz", M((0.55, -0.35, 0.0), (6, 3, 0)))
        bm = drehkoerper([(re + 0.02, -0.0175), (re + 0.026, -0.0175), (re + 0.026, 0.0175), (re + 0.02, 0.0175)], 32, False, False)
        m.teil(bm, "eisen", M((-0.45, -0.42, 0.02), (90 - 6, 0, 30)), uv="zylz", r=re)
        m.brett(0.85, 0.11, 0.022, M((0.1, -0.62, 0.012), (0, 0, 72)), "holz", bruch=1)
        m.brett(0.5, 0.11, 0.022, M((-0.62, 0.15, 0.03), (8, 0, -30)), "holz", bruch=-1)


# ======================================================================== Möbel

def boden_setzen(m, drehung, drehpunkt=(0, 0, 0)):
    """Kippt alle folgenden Teile um einen Punkt (für umgefallene oder eingesackte kaputte Modelle)."""
    p = Vector(drehpunkt)
    m.G = Matrix.Translation(p) @ M(rot=drehung) @ Matrix.Translation(-p)


def stuhl(m, kaputt):
    sb, st, sh = 0.44, 0.42, 0.45          # Sitzbreite, -tiefe, -höhe
    b = 0.038
    if kaputt:
        # vorderes linkes Bein abgebrochen: Stuhl kippt nach vorne links auf den Stumpf
        boden_setzen(m, (-9, -11, 0), (-sb / 2, -st / 2, 0))
        m.G = Matrix.Translation((0, 0, 0.012)) @ m.G
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * (sb / 2 - b / 2); y = sy * (st / 2 - b / 2)
            unten = Vector((x + sx * 0.015, y + sy * 0.015, 0))
            if sy > 0:      # Hinterbeine laufen bis zur Lehne hoch und neigen sich nach hinten
                m.kantholz(unten, (x, y + 0.06, 0.98), b, b, oben=(0, -1, 0))
            elif kaputt and sx < 0:
                m.kantholz((x, y, sh * 0.48), (x, y, sh - 0.01), b, b, oben=(0, -1, 0), bruch=-1)
            else:
                m.kantholz(unten, (x, y, sh - 0.01), b, b, oben=(0, -1, 0))
    # Zargen und Querstreben
    for sy in (-1, 1):
        m.kantholz((-sb / 2 + b, sy * (st / 2 - b / 2), sh - 0.06), (sb / 2 - b, sy * (st / 2 - b / 2), sh - 0.06), 0.06, 0.02,
                   oben=(0, sy, 0))
        m.kantholz((-sb / 2 + b, sy * (st / 2 - b / 2), 0.16), (sb / 2 - b, sy * (st / 2 - b / 2), 0.16), 0.025, 0.025)
    for sx in (-1, 1):
        m.kantholz((sx * (sb / 2 - b / 2), -st / 2 + b, sh - 0.06), (sx * (sb / 2 - b / 2), st / 2 - b, sh - 0.06), 0.06, 0.02,
                   oben=(sx, 0, 0))
    # Sitz aus drei Brettern
    for i in range(3):
        y = -st / 2 + 0.07 + i * (st - 0.02) / 3
        m.brett(sb + 0.03, (st - 0.02) / 3 - 0.006, 0.022, M((0, y, sh + 0.011)), "holz")
    # Lehne: zwei Querbretter
    for i, z in enumerate((0.72, 0.9)):
        y = st / 2 - b / 2 + 0.06 * (z - 0.0) / 0.98
        if kaputt and i == 1:
            m.brett(0.22, 0.02, 0.08, M((-0.12, y + 0.02, z), (0, 0, 0)), "holz", bruch=1)
            continue
        m.brett(sb - 0.01, 0.02, 0.08, M((0, y + 0.02, z)), "holz")
    if kaputt:
        m.G = None
        m.kantholz((-0.52, -0.42, 0.02), (-0.36, -0.2, 0.02), b, b, bruch=1)
        m.brett(0.2, 0.02, 0.08, M((0.42, 0.38, 0.01), (90, 0, 40)), "holz", bruch=-1)


def hocker(m, kaputt):
    h, r = 0.46, 0.17
    if kaputt:
        # umgefallen, ein Bein fehlt
        boden_setzen(m, (0, 78, 20), (0, 0, 0))
        m.G = Matrix.Translation((0, 0, r + 0.02)) @ m.G
    bm = drehkoerper([(0.0, h - 0.04), (r, h - 0.04), (r + 0.006, h - 0.02), (r, h), (0.0, h)], 20)
    verbiegen(bm, m.rnd, 0.004, 0.3)
    m.teil(bm, "holz", None, uv="box")
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        oben = Vector((math.cos(a) * r * 0.62, math.sin(a) * r * 0.62, h - 0.04))
        unten = Vector((math.cos(a) * r * 1.25, math.sin(a) * r * 1.25, 0.0))
        if kaputt and k == 0:
            m.stab(oben, oben + (unten - oben) * 0.3, 0.02, r2=0.018, kappen=True)
            continue
        m.stab(unten, oben, 0.021, r2=0.017)
    for k in range(3):
        a0 = 2 * math.pi * k / 3 + 0.3; a1 = a0 + 2 * math.pi / 3
        f = 0.85
        p0 = Vector((math.cos(a0) * r * f * 1.2, math.sin(a0) * r * f * 1.2, 0.17))
        p1 = Vector((math.cos(a1) * r * f * 1.2, math.sin(a1) * r * f * 1.2, 0.17))
        m.stab(p0, p1, 0.011)
    if kaputt:
        m.G = None
        m.stab((0.35, -0.3, 0.02), (0.6, -0.05, 0.02), 0.02, r2=0.017)


def tisch(m, kaputt):
    l, b, h = 1.6, 0.8, 0.76
    bein = 0.075
    if kaputt:
        # hinteres rechtes Bein gebrochen, die Ecke liegt auf dem Boden
        boden_setzen(m, (-14, 12, 0), (-l / 2, -b / 2, 0))
    fehlt_brett = 1 if kaputt else -1
    for i in range(4):
        if i == fehlt_brett:
            continue
        y = -b / 2 + 0.1 + i * 0.2
        m.brett(l, 0.195, 0.04, M((0, y, h - 0.02)), "holz", nx=6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * (l / 2 - 0.12); y = sy * (b / 2 - 0.08)
            if kaputt and sx > 0 and sy > 0:
                m.kantholz((x, y, h - 0.24), (x, y, h - 0.04), bein, bein, bruch=-1)
                continue
            m.kantholz((x, y, 0.0), (x, y, h - 0.04), bein, bein)
    for sy in (-1, 1):
        m.kantholz((-l / 2 + 0.1, sy * (b / 2 - 0.08), h - 0.09), (l / 2 - 0.1, sy * (b / 2 - 0.08), h - 0.09), 0.09, 0.03,
                   oben=(0, sy, 0))
    for sx in (-1, 1):
        m.kantholz((sx * (l / 2 - 0.12), -b / 2 + 0.06, h - 0.09), (sx * (l / 2 - 0.12), b / 2 - 0.06, h - 0.09), 0.09, 0.03,
                   oben=(sx, 0, 0))
        m.kantholz((sx * (l / 2 - 0.12), -b / 2 + 0.08, 0.14), (sx * (l / 2 - 0.12), b / 2 - 0.08, 0.14), 0.05, 0.04)
    m.kantholz((-l / 2 + 0.12, 0, 0.14), (l / 2 - 0.12, 0, 0.14), 0.06, 0.04)
    if kaputt:
        m.G = None
        m.brett(1.1, 0.195, 0.04, M((0.25, -0.75, 0.02), (0, 0, 8)), "holz", bruch=1)
        m.kantholz((0.95, 0.55, 0.04), (1.2, 0.1, 0.04), bein, bein, bruch=1)


def bank(m, kaputt):
    l, b, h = 1.5, 0.3, 0.45
    if not kaputt:
        m.brett(l, b, 0.05, M((0, 0, h - 0.025)), "holz", nx=6)
    else:
        # Sitzbrett in der Mitte durchgebrochen, beide Hälften hängen zum Boden
        for s in (-1, 1):
            p = Vector((s * (l / 2 - 0.2), 0, h))
            ende = Vector((s * 0.02, 0, 0.03))
            mitte = (p * 1.32 + ende * -0.32) if False else None
            a = Vector((s * l / 2, 0, h + 0.02))
            m.brett((a - ende).length, b, 0.05, ausrichten(a if s < 0 else ende, ende if s < 0 else a), "holz",
                    bruch=1 if s < 0 else -1, bruch_tiefe=0.12)
    for s in (-1, 1):
        x = s * (l / 2 - 0.22)
        if kaputt:
            boden_setzen(m, (0, s * 6, 0), (x, 0, 0))
        # Beine aus einem breiten Brett mit Ausschnitt unten
        m.brett(h - 0.05, b - 0.02, 0.05, M((x, 0, (h - 0.05) / 2), (0, 90, 0)), "holz")
        m.G = None
    m.kantholz((-l / 2 + 0.24, 0, 0.12), (l / 2 - 0.24, 0, 0.12), 0.07, 0.04, oben=(0, 1, 0),
               bruch=0 if not kaputt else 0)


# ======================================================================== Zäune

def zaun(m, kaputt):
    """Lattenzaun, 2 m: Pfosten bei x = -1, Riegel bis x = +1 (dort sitzt der Pfosten des nächsten Stücks)."""
    if kaputt:
        boden_setzen(m, (11, 0, 0), (0, 0, 0))
    m.kantholz((-1.0, 0, -0.1), (-1.0, 0, 1.25), 0.1, 0.1, "holz_alt", oben=(0, -1, 0))
    m.teil(quader(0.14, 0.14, 0.02, fase=0.005), "holz_alt", M((-1.0, 0, 1.255)))
    riegel = (0.35, 0.92)
    for i, z in enumerate(riegel):
        if kaputt and i == 1:
            m.kantholz((-0.96, 0.07, z), (0.1, 0.07, z), 0.08, 0.04, "holz_alt", oben=(0, 1, 0), bruch=1)
            m.kantholz((0.25, 0.07, z - 0.05), (0.98, 0.07, z - 0.45), 0.08, 0.04, "holz_alt", oben=(0, 1, 0), bruch=-1)
            continue
        m.kantholz((-0.96, 0.07, z), (1.0, 0.07, z), 0.08, 0.04, "holz_alt", oben=(0, 1, 0))
    n = 13
    for i in range(n):
        x = -0.86 + i * 1.82 / (n - 1)
        hoehe = 1.05 + 0.03 * m.rnd.uniform(-1, 1)
        if kaputt and i in (4, 9):
            continue
        bm = quader(0.1, 0.022, hoehe, 1, 2, 3)
        for v in bm.verts:
            if v.co.z > hoehe / 2 - 1e-4 and abs(v.co.y) < 1e-4:
                pass
            if v.co.z > hoehe / 2 - 1e-4:
                v.co.z -= 0.05 * abs(v.co.x) / 0.05 if True else 0
        laenge_bruch = kaputt and i in (5, 10, 11)
        if laenge_bruch:
            bm = quader(hoehe * 0.55, 0.1, 0.022, 3, 4, 2)
            bruchkante(bm, m.rnd, 1, 0.12)
            verbiegen(bm, m.rnd, 0.004, 0.5)
            m.teil(bm, "holz_alt", M((x, 0.03, -0.02 + hoehe * 0.55 / 2), (0, -90, 90)))
            continue
        verbiegen(bm, m.rnd, 0.004, 0.5)
        kipp = m.rnd.uniform(-1.5, 1.5) + (12 if kaputt and i == 7 else 0)
        m.teil(bm, "holz_alt", M((x, 0.03, -0.05 + hoehe / 2), (0, kipp, 0)), uv="boxz")
    if kaputt:
        m.G = None
        bm = quader(1.0, 0.1, 0.022, 3, 1, 1)
        verbiegen(bm, m.rnd, 0.004, 0.5)
        m.teil(bm, "holz_alt", M((0.2, -0.45, 0.012), (0, 0, 20)))


def palisade(m, kaputt):
    """Palisade, 2 m breit: 8 angespitzte Stämme, hinten ein Querriegel mit Seilbund."""
    n = 8
    for i in range(n):
        x = -1.0 + 0.125 + i * 0.25
        r = 0.11 + 0.015 * m.rnd.uniform(-1, 1)
        h = 2.7 + 0.15 * m.rnd.uniform(-1, 1)
        if kaputt and i == 5:
            continue
        gebrochen = kaputt and i in (2, 3, 6)
        if gebrochen:
            h_st = (0.7, 1.2, 0.9)[(2, 3, 6).index(i)]
            prof = [(r, -0.3), (r, h_st)]
            bm = drehkoerper(prof, 10, True, True)
            oben = max(v.co.z for v in bm.verts)
            for v in bm.verts:
                if abs(v.co.z - oben) < 1e-4:
                    v.co.z += m.rnd.uniform(-0.12, 0.2); v.co.x *= m.rnd.uniform(0.6, 1); v.co.y *= m.rnd.uniform(0.6, 1)
            verbiegen(bm, m.rnd, 0.01, 0.4)
            m.teil(bm, "holz_alt", M((x, 0, 0)), uv="zylz", r=r)
            continue
        prof = [(r, -0.3), (r * 1.02, h * 0.4), (r * 0.97, h - 0.42), (r * 0.5, h - 0.2), (0.012, h)]
        bm = drehkoerper(prof, 10, False, True)
        verbiegen(bm, m.rnd, 0.012, 0.5)
        m.teil(bm, "holz_alt", M((x, 0, 0), (m.rnd.uniform(-1.5, 1.5), m.rnd.uniform(-1.5, 1.5), m.rnd.uniform(0, 360))),
               uv="zylz", r=r)
    # Querriegel hinten mit Seil um jeden Stamm
    if not kaputt:
        m.stab((-1.0, 0.18, 1.9), (1.0, 0.18, 1.9), 0.07, "holz_alt", r2=0.065)
    else:
        m.stab((-1.0, 0.18, 1.9), (-0.15, 0.18, 1.9), 0.07, "holz_alt")
        m.stab((0.05, 0.18, 1.6), (1.0, 0.2, 1.05), 0.07, "holz_alt")
    for i in range(n):
        if kaputt and i in (2, 3, 5, 6):
            continue
        x = -1.0 + 0.125 + i * 0.25
        pts = [(x + 0.12 * math.cos(a), 0.03 + 0.15 * math.sin(a), 1.9 + 0.03 * math.sin(a * 2))
               for a in [math.radians(t) for t in range(-90, 271, 30)]]
        m.seil(pts, 0.012)
    if kaputt:
        bm = drehkoerper([(0.11, 0), (0.11, 1.8), (0.06, 1.95), (0.012, 2.1)], 10, True, True)
        verbiegen(bm, m.rnd, 0.01, 0.5)
        m.teil(bm, "holz_alt", M((0.2, -0.6, 0.11), (0, 88, 12)), uv="zylz", r=0.11)


# ======================================================================== Zelt

def zelt(m, kaputt):
    lx, by, hf = 2.4, 2.2, 1.6               # Länge, Breite, Firsthöhe
    nx, ns = 12, 8
    def firsthoehe(u):                        # u = 0..1 entlang x
        if not kaputt:
            return hf
        return hf - 1.0 * math.sin(math.pi * u) ** 1.5      # Firststange in der Mitte gebrochen
    loecher = set()
    if kaputt:
        for (ci, cj, r) in ((3, 4, 1.6), (6, 9, 1.2)):
            for i in range(ns):
                for j in range(nx):
                    if (i - ci) ** 2 + (j - cj) ** 2 * 0.6 < r * r + m.rnd.uniform(-0.6, 0.6):
                        loecher.add((i, j))
    for seite in (-1, 1):
        gitter = []
        for i in range(ns + 1):
            s = i / ns                        # 0 = Boden, 1 = First
            zeile = []
            for j in range(nx + 1):
                u = j / nx
                x = -lx / 2 - 0.08 + (lx + 0.16) * u
                fh = firsthoehe(u)
                y = seite * (by / 2) * (1 - s)
                z = 0.04 + (fh - 0.04) * s
                durch = 0.06 * math.sin(math.pi * s) * (0.6 + 0.4 * math.sin(math.pi * u))   # Tuch hängt durch
                y -= seite * durch * 0.4; z -= durch
                if kaputt and seite < 0 and s < 0.5:
                    y -= seite * 0.25 * (0.5 - s) * math.sin(math.pi * u)
                zeile.append((x, y, z))
            gitter.append(zeile)
        loch = (lambda i, j: (i, j) in loecher) if seite < 0 else None
        bm = flaeche(gitter if seite > 0 else [list(reversed(z)) for z in gitter], 0.008,
                     loch if seite > 0 else (lambda i, j: (i, nx - 1 - j) in loecher) if kaputt else None)
        m.teil(bm, "stoff", None)
    # Rückwand (Dreieck) bei +x, vorne eine halb geschlossene Klappe
    for x, voll in ((lx / 2 + 0.06, True), (-lx / 2 - 0.06, False)):
        gitter = []
        for i in range(ns + 1):
            s = i / ns
            fh = firsthoehe(1.0 if x > 0 else 0.0)
            z = 0.04 + (fh - 0.04) * s
            breite = (by / 2) * (1 - s)
            y0 = -breite; y1 = breite if voll else -breite * 0.1
            gitter.append([(x + 0.03 * math.sin(math.pi * s), y0 + (y1 - y0) * t, z) for t in (0, 0.25, 0.5, 0.75, 1)])
        m.teil(flaeche(gitter, 0.008), "stoff", None)
    # Aufgerollte Klappe an der offenen Seite
    m.teil(rundholz(0.05, hf * 0.95, 8, 4), "stoff", ausrichten((-lx / 2 - 0.08, by / 2 - 0.05, 0.08), (-lx / 2 - 0.08, 0.06, hf - 0.08)),
           uv="zyl", r=0.05)
    # Stangen
    for x in (-lx / 2 - 0.02, lx / 2 + 0.02):
        if kaputt and x > 0:
            m.stab((x, 0.0, 0.0), (x - 0.15, 0.0, firsthoehe(1.0) + 0.06), 0.03, r2=0.026)
        else:
            m.stab((x, 0.0, 0.0), (x, 0.0, hf + 0.08), 0.03, r2=0.026)
    if not kaputt:
        m.stab((-lx / 2 - 0.1, 0, hf + 0.03), (lx / 2 + 0.1, 0, hf + 0.03), 0.028)
    else:
        m.stab((-lx / 2 - 0.1, 0, hf + 0.03), (0.0, 0, firsthoehe(0.5) + 0.03), 0.028, kappen=True)
        m.stab((0.05, 0, firsthoehe(0.5) + 0.05), (lx / 2 + 0.1, 0, firsthoehe(1.0) + 0.03), 0.028)
    # Abspannseile mit Heringen
    anker = [((-lx / 2 - 0.02, 0, hf + 0.05), (-lx / 2 - 0.9, 0, 0)), ((lx / 2 + 0.02, 0, hf + 0.05), (lx / 2 + 0.9, 0, 0))]
    for x in (-lx / 2 + 0.1, 0.0, lx / 2 - 0.1):
        for sy in (-1, 1):
            anker.append(((x, sy * (by / 2 - 0.02), 0.07), (x, sy * (by / 2 + 0.45), 0.0)))
    for i, (a, b) in enumerate(anker):
        if kaputt and i in (1, 4):
            continue
        a = Vector(a); b = Vector(b)
        if kaputt and i == 0:
            a = Vector((a.x, a.y, firsthoehe(0.0) + 0.05))
        mitte = (a + b) * 0.5 - Vector((0, 0, 0.03))
        m.seil([a, mitte, b + Vector((0, 0, 0.04))], 0.006, 4)
        m.stab(b + Vector((0, 0, -0.12)), b + Vector((0, 0, 0.08)), 0.014, r2=0.009)


# ======================================================================== Lagerfeuer

def lagerfeuer(m, kaputt):
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n + m.rnd.uniform(-0.1, 0.1)
        r = 0.48 + (0.1 * m.rnd.random() if kaputt else 0.02 * m.rnd.random())
        if kaputt and i in (3, 7):
            r += 0.35
        g = m.rnd.uniform(0.11, 0.16)
        bm = basis.brocken(m.rnd, g * 1.2, g, g * 0.7, rauh=0.32, unterteilung=3)
        m.teil(bm, "stein", M((r * math.cos(a), r * math.sin(a), g * 0.4), (0, 0, math.degrees(a) + m.rnd.uniform(-20, 20))))
    # Asche und Glut in der Mitte
    asche = drehkoerper([(0.0, 0.0), (0.4, 0.0), (0.33, 0.035), (0.15, 0.06), (0.0, 0.065)], 16)
    verbiegen(asche, m.rnd, 0.015, 0.15, (0.3, 0.3, 1))
    m.teil(asche, "asche" if kaputt else "glut", None)
    if not kaputt:
        # Holzscheite als Pyramide, unten verkohlt
        for k in range(6):
            a = 2 * math.pi * k / 6 + 0.2
            unten = Vector((0.36 * math.cos(a), 0.36 * math.sin(a), 0.05))
            oben = Vector((0.05 * math.cos(a), 0.05 * math.sin(a), 0.6))
            mitte = unten + (oben - unten) * 0.45
            m.stab(unten, mitte, 0.045, "holz_verkohlt", r2=0.042)
            m.stab(mitte, oben, 0.042, "holz", r2=0.035)
        for k in range(3):
            a = 2 * math.pi * k / 3
            p = Vector((0.12 * math.cos(a), 0.12 * math.sin(a), 0.08))
            q = p + Vector((0.3 * math.cos(a + 1.7), 0.3 * math.sin(a + 1.7), 0.02))
            m.stab(p, q, 0.04, "holz_verkohlt")
    else:
        # erloschen: Scheite eingefallen und verstreut
        for k in range(5):
            a = 2 * math.pi * k / 5 + m.rnd.uniform(-0.3, 0.3)
            p = Vector((0.08 * math.cos(a), 0.08 * math.sin(a), 0.06))
            l = m.rnd.uniform(0.3, 0.5)
            q = p + Vector((l * math.cos(a + 0.4), l * math.sin(a + 0.4), m.rnd.uniform(-0.02, 0.06)))
            m.stab(p, q, m.rnd.uniform(0.032, 0.045), "holz_verkohlt", r2=0.025)
        m.stab((0.7, -0.4, 0.04), (0.95, -0.15, 0.04), 0.04, "holz_verkohlt")


# ======================================================================== Karren

def rad(m, mitte, r=0.45, breite=0.07, achse=(1, 0, 0), speichen=10, kaputt=False):
    """Speichenrad: Nabe, Speichen, Felge mit Eisenreifen. Die Drehachse liegt entlang x (vor dem Ausrichten)."""
    mtx = Matrix.Translation(Vector(mitte)) @ Vector((1, 0, 0)).rotation_difference(Vector(achse)).to_matrix().to_4x4()
    zur_x = M(rot=(0, 90, 0))               # Drehkörper laufen um z -> um x drehen
    nabe = drehkoerper([(0.0, -0.11), (0.06, -0.11), (0.075, -0.05), (0.08, 0.0), (0.075, 0.05), (0.06, 0.11), (0.0, 0.11)], 12)
    m.teil(nabe, "holz", mtx @ zur_x, uv="zylz", r=0.07)
    felge = drehkoerper([(r - 0.07, -breite / 2), (r - 0.005, -breite / 2), (r - 0.005, breite / 2), (r - 0.07, breite / 2),
                         (r - 0.07, -breite / 2)], 28, False, False)
    m.teil(felge, "holz", mtx @ zur_x, uv="zylz", r=r)
    reifen = drehkoerper([(r - 0.006, -breite / 2 - 0.002), (r + 0.008, -breite / 2 - 0.002), (r + 0.008, breite / 2 + 0.002),
                          (r - 0.006, breite / 2 + 0.002)], 28, False, False)
    m.teil(reifen, "eisen", mtx @ zur_x, uv="zylz", r=r)
    for k in range(speichen):
        if kaputt and k in (2, 3):
            continue
        a = 2 * math.pi * k / speichen
        rich = Vector((0, math.cos(a), math.sin(a)))
        m.stab(rich * 0.07, rich * (r - 0.06), 0.018, mat="holz", r2=0.014) if False else None
        bm = rundholz(0.018, r - 0.12, 6, 2, 0.013)
        m.teil(bm, "holz", mtx @ ausrichten(rich * 0.07, rich * (r - 0.05)), uv="zyl", r=0.016)


def karren(m, kaputt):
    """Zweirädriger Handkarren. Er steht mit den Deichselenden auf dem Boden (vorne = -y)."""
    r = 0.45
    ladeh = 0.6
    lb, ll = 1.0, 1.5                          # Ladefläche Breite (x), Länge (y)
    neigung = math.degrees(math.atan2(ladeh - 0.06, 1.75))
    if not kaputt:
        boden_setzen(m, (neigung, 0, 0), (0, 0, r))
    else:
        # linkes Rad fehlt: der Karren liegt links auf der Achse und vorne auf der Deichsel
        boden_setzen(m, (neigung - 4, -17, 0), (0, 0, r))
        m.G = Matrix.Translation((0, 0, -0.06)) @ m.G
    # Achse und Räder
    m.kantholz((-lb / 2 - 0.18, 0, r), (lb / 2 + 0.18, 0, r), 0.07, 0.07)
    for s in (-1, 1):
        if kaputt and s < 0:
            continue
        rad(m, (s * (lb / 2 + 0.12), 0, r), r, kaputt=False)
    # Rahmen und Deichseln (laufen nach vorne über die Ladefläche hinaus)
    for s in (-1, 1):
        m.kantholz((s * (lb / 2 - 0.05), ll / 2, ladeh - 0.06), (s * 0.28, -ll / 2 - 1.0, ladeh - 0.06), 0.07, 0.07)
    m.kantholz((-0.33, -ll / 2 - 0.9, ladeh - 0.06), (0.33, -ll / 2 - 0.9, ladeh - 0.06), 0.05, 0.05)
    for y in (-ll / 2 + 0.05, 0.0, ll / 2 - 0.05):
        m.kantholz((-lb / 2, y, ladeh - 0.06 - 0.06), (lb / 2, y, ladeh - 0.06 - 0.06), 0.06, 0.05)
    # Ladefläche aus Längsbrettern
    n = 5
    for i in range(n):
        x = -lb / 2 + lb / n * (i + 0.5)
        if kaputt and i == 1:
            m.brett(0.6, lb / n - 0.008, 0.025, M((x, -ll / 2 + 0.3, ladeh), (0, 0, 90)), "holz", bruch=1)
            continue
        m.brett(ll, lb / n - 0.008, 0.025, M((x, 0, ladeh), (0, 0, 90)), "holz", nx=5)
    # Seitenbretter mit Rungen
    for s in (-1, 1):
        for z in (ladeh + 0.1, ladeh + 0.24):
            if kaputt and s < 0 and z > ladeh + 0.2:
                m.brett(0.7, 0.025, 0.12, M((s * (lb / 2 + 0.015), 0.35, z), (0, 0, 90)), "holz", bruch=-1)
                continue
            m.brett(ll, 0.025, 0.12, M((s * (lb / 2 + 0.015), 0, z), (0, 0, 90)), "holz", nx=5)
        for y in (-ll / 2 + 0.08, 0.0, ll / 2 - 0.08):
            m.kantholz((s * (lb / 2 + 0.045), y, ladeh - 0.08), (s * (lb / 2 + 0.045), y, ladeh + 0.32), 0.05, 0.035, oben=(s, 0, 0))
    m.brett(lb + 0.06, 0.025, 0.26, M((0, ll / 2 + 0.014, ladeh + 0.16)), "holz")
    m.G = None
    if kaputt:
        # abgefallenes Rad liegt flach daneben, Bretter auf dem Boden
        rad(m, (-1.15, -0.25, 0.04), r, achse=(0, 0, 1), kaputt=True)
        m.brett(0.9, lb / n - 0.008, 0.025, M((-0.35, -1.5, 0.013), (0, 0, 70)), "holz", bruch=-1)


# ======================================================================== Laternen

def laterne_koerper(m, kaputt=False, matrix=None):
    """Eisenlaterne mit Glas, Ursprung unten in der Mitte (steht auf z = 0); der Aufhängering liegt bei z = 0.30."""
    G0 = m.G
    m.G = (G0 @ matrix) if (G0 is not None and matrix is not None) else (matrix or G0)
    b, h = 0.16, 0.22
    z0 = 0.0                                    # Unterkante
    oben = 0.30                                 # Aufhängering
    # Boden, Deckel, Eckstäbe
    m.teil(quader(b + 0.03, b + 0.03, 0.02, fase=0.004), "eisen", M((0, 0, z0 + 0.01)))
    m.teil(quader(b + 0.03, b + 0.03, 0.015, fase=0.003), "eisen", M((0, 0, z0 + h + 0.0075)))
    dach = drehkoerper([(0.13, z0 + h + 0.015), (0.03, z0 + h + 0.09), (0.0, z0 + h + 0.095)], 4, False, True)
    dach.transform(M(rot=(0, 0, 45)))
    if kaputt:
        verbiegen(dach, m.rnd, 0.012, 0.1)
    m.teil(dach, "eisen", None, uv="box")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.teil(quader(0.012, 0.012, h, 1, 1, 2), "eisen", M((sx * b / 2, sy * b / 2, z0 + h / 2)))
    # Glasscheiben
    for i, (dx, dy, rz) in enumerate(((0, -b / 2, 0), (0, b / 2, 0), (-b / 2, 0, 90), (b / 2, 0, 90))):
        if kaputt and i in (0, 2):
            if i == 0:   # nur ein Rest steckt noch unten im Rahmen
                bm = flaeche([[(-b / 2 + 0.01, 0, 0), (b / 2 - 0.01, 0, 0)], [(-b / 2 + 0.01, 0, 0.06), (0.02, 0, 0.11)]], 0.003)
                m.teil(bm, "glas", M((dx, dy, z0 + 0.02), (0, 0, rz)))
            continue
        m.teil(quader(b - 0.01, 0.003, h - 0.01), "glas", M((dx, dy, z0 + h / 2), (0, 0, rz)))
    # Kerze und Flamme
    m.teil(rundholz(0.022, 0.09 if not kaputt else 0.04, 8, 1), "putz",
           M((0, 0, z0 + 0.02 + (0.045 if not kaputt else 0.02)), (0, 90, 0)), uv="zyl", r=0.022)
    if not kaputt:
        flamme = drehkoerper([(0.0, 0.0), (0.009, 0.012), (0.006, 0.03), (0.0, 0.045)], 6)
        m.teil(flamme, "glut", M((0, 0, z0 + 0.11)))
    # Bügel
    m.seil([(-0.05, 0, z0 + h + 0.09), (-0.045, 0, oben - 0.03), (0, 0, oben), (0.045, 0, oben - 0.03), (0.05, 0, z0 + h + 0.09)],
           0.005, 5, "eisen")
    m.G = G0


def laterne(m, kaputt):
    """Laterne zum Hinstellen oder Aufhängen (Ring 0.30 m über dem Boden). Kaputt liegt sie auf der Seite."""
    if not kaputt:
        laterne_koerper(m)
    else:
        laterne_koerper(m, True, M((-0.12, 0.0, 0.11), (0, 88, 20)))


def laternenpfahl(m, kaputt):
    """Holzpfahl mit Ausleger, die Laterne hängt an einer kurzen Kette."""
    h = 2.6
    arm = 0.65
    if not kaputt:
        m.kantholz((0, 0, -0.1), (0, 0, h), 0.13, 0.13, "holz_alt", oben=(0, -1, 0))
        m.teil(quader(0.17, 0.17, 0.03, fase=0.008), "holz_alt", M((0, 0, h + 0.015)))
        m.kantholz((-0.05, 0, h - 0.12), (arm, 0, h - 0.12), 0.08, 0.1, "holz_alt", oben=(0, 0, 1))
        m.kantholz((0.05, 0, h - 0.6), (0.4, 0, h - 0.17), 0.06, 0.06, "holz_alt", oben=(0, -1, 0))
        m.teil(quader(0.02, 0.06, 0.02), "eisen", M((arm - 0.05, 0, h - 0.18)))
        kette = [(arm - 0.05, 0, h - 0.19 - 0.035 * i) for i in range(5)]
        for i, p in enumerate(kette):
            m.seil([(p[0] + 0.01 * math.cos(a), p[1] + 0.01 * math.sin(a) * (i % 2), p[2] - 0.015 + 0.015 * math.sin(a) * ((i + 1) % 2))
                    for a in [math.radians(t) for t in range(0, 361, 45)]], 0.0035, 4, "eisen")
        laterne_koerper(m, False, M((arm - 0.05, 0, h - 0.37 - 0.30)))
    else:
        # Pfahl auf 1,3 m abgebrochen, Oberteil liegt mit kaputter Laterne am Boden
        m.kantholz((0, 0, -0.1), (0, 0, 1.3), 0.13, 0.13, "holz_alt", oben=(0, -1, 0), bruch=1)
        ob = M((0.35, -0.2, 0.065), (0, 90, 15))
        m.kantholz((0, 0, 0.0), (0, 0, h - 1.4), 0.13, 0.13, "holz_alt", oben=(0, -1, 0), bruch=-1) if False else None
        G0 = m.G; m.G = ob @ M((0, 0, -1.4))
        m.kantholz((0, 0, 1.4), (0, 0, h), 0.13, 0.13, "holz_alt", oben=(0, -1, 0), bruch=-1)
        m.teil(quader(0.17, 0.17, 0.03, fase=0.008), "holz_alt", M((0, 0, h + 0.015)))
        m.kantholz((-0.05, 0, h - 0.12), (arm, 0, h - 0.12), 0.08, 0.1, "holz_alt", oben=(0, 0, 1))
        m.G = G0
        laterne_koerper(m, True, M((0.75, 0.35, 0.11), (0, 80, 60)))


# ======================================================================== Ruinen (Stein)

def saeule(m, kaputt):
    """Säule aus Trommeln auf einer Plinthe, oben ein Kapitell."""
    r = 0.26
    plinthe = basis.klotz(m.rnd, 0.78, 0.78, 0.26, 0.012, 0.008, 0.6 if kaputt else 0.15)
    m.teil(plinthe, "stein", M((0, 0, 0.13)))
    trommeln = [0.8, 0.8, 0.8, 0.6]
    z = 0.26
    def trommel(r0, r1, h, gebrochen=False):
        seg = 24
        bm = bmesh.new()
        ringe = []
        stufen = 4
        for i in range(stufen + 1):
            t = i / stufen; rr = r0 + (r1 - r0) * t
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                kann = 1 - 0.035 * (k % 2)               # Kanneluren
                ring.append(bm.verts.new((rr * kann * math.cos(a), rr * kann * math.sin(a), h * t)))
            ringe.append(ring)
        for a, b in zip(ringe, ringe[1:]):
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
        bm.faces.new(list(reversed(ringe[0]))); bm.faces.new(ringe[-1])
        if gebrochen:
            o = Vector([m.rnd.uniform(-40, 40) for _ in range(3)])
            for v in ringe[-1]:
                v.co.z += -0.25 * h * (0.5 + 0.5 * noise.noise(v.co * 3 + o)) - 0.15 * h * (v.co.x / r)
        verbiegen(bm, m.rnd, 0.008, 0.2)
        bm.normal_update()
        return bm
    stehen = 4 if not kaputt else 2
    rr = r
    for i, h in enumerate(trommeln[:stehen]):
        r1 = r * (1 - 0.03 * (z + h) / 3)
        bm = trommel(rr, r1, h, gebrochen=kaputt and i == stehen - 1)
        m.teil(bm, "stein", M((0, 0, z), (0, 0, m.rnd.uniform(0, 360))), uv="zylz", r=r)
        z += h; rr = r1
    if not kaputt:
        kap = basis.klotz(m.rnd, 0.7, 0.7, 0.18, 0.012, 0.008, 0.15)
        m.teil(drehkoerper([(rr, 0), (rr * 1.2, 0.08), (rr * 1.25, 0.12)], 24, False, False), "stein", M((0, 0, z)), uv="zylz", r=r)
        m.teil(kap, "stein", M((0, 0, z + 0.21)))
    else:
        noise_frei = lambda: None
        # umgestürzte Trommeln am Boden
        for i, (x, y, rz) in enumerate(((0.9, -0.4, 20), (1.75, -0.1, 35))):
            bm = trommel(r, r * 0.98, 0.8, gebrochen=i == 1)
            m.teil(bm, "stein", M((x, y, r * 0.97), (0, 90, rz)), uv="zylz", r=r)
        kap = basis.klotz(m.rnd, 0.7, 0.7, 0.18, 0.012, 0.008, 0.8)
        m.teil(kap, "stein", M((-0.85, 0.55, 0.12), (6, 14, 30)))


def mauer(m, kaputt):
    """Mauerrest aus behauenen Blöcken: 3 m lang, 0.6 m dick, 2.1 m hoch (heil mit Abdeckplatten)."""
    l, d = 3.0, 0.6
    lagen = 7; lh = 0.3
    for j in range(lagen):
        z = j * lh
        x = -l / 2
        versatz = 0.25 if j % 2 else 0.0
        breiten = []
        rest = l
        erst = 0.35 + versatz if versatz else 0.6 + m.rnd.uniform(-0.1, 0.1)
        breiten.append(erst); rest -= erst
        while rest > 0.85:
            w = m.rnd.uniform(0.5, 0.8); breiten.append(w); rest -= w
        breiten.append(rest)
        for k, w in enumerate(breiten):
            mitte_x = x + w / 2
            x += w
            if kaputt:
                # stufig abgebrochene Oberkante: höher am linken Ende
                grenze = 6.2 - (mitte_x + l / 2) * 1.7 + 0.8 * noise.noise(Vector((mitte_x * 1.3, j * 0.7, 3.3)))
                if j > grenze:
                    continue
            bm = basis.klotz(m.rnd, w - 0.012, d - 0.01 * m.rnd.random(), lh - 0.012, 0.012, 0.008, 0.6 if kaputt else 0.0)
            m.teil(bm, "stein", M((mitte_x, m.rnd.uniform(-0.01, 0.01), z + lh / 2)))
    if not kaputt:
        for k in range(4):
            bm = basis.klotz(m.rnd, l / 4 - 0.01, d + 0.08, 0.1, 0.012, 0.006, 0.2)
            m.teil(bm, "stein", M((-l / 2 + l / 8 + k * l / 4, 0, lagen * lh + 0.05)))
    else:
        # heruntergefallene Blöcke
        for i in range(6):
            w = m.rnd.uniform(0.4, 0.7)
            bm = basis.klotz(m.rnd, w, 0.5, 0.28, 0.012, 0.008, 0.9)
            x = m.rnd.uniform(0.0, 1.6); y = m.rnd.choice((-1, 1)) * m.rnd.uniform(0.6, 1.2)
            m.teil(bm, "stein", M((x, y, 0.13), (m.rnd.uniform(-8, 8), m.rnd.uniform(-8, 8), m.rnd.uniform(0, 180))))


def bogen(m, kaputt):
    """Rundbogen aus Keilsteinen auf zwei Pfeilern, lichte Weite 2.2 m, Scheitel 3.3 m."""
    w = 2.2; d = 0.6; pf = 0.6; h_pf = 2.2
    rin = w / 2; rau = rin + 0.5
    for s in (-1, 1):
        lagen = 6 if not (kaputt and s > 0) else 3
        for j in range(lagen):
            bm = basis.klotz(m.rnd, pf - 0.012, d, h_pf / 6 - 0.012, 0.012, 0.008, 0.6 if kaputt else 0.0)
            m.teil(bm, "stein", M((s * (rin + pf / 2), 0, j * h_pf / 6 + h_pf / 12)))
    n = 11
    for k in range(n):
        if kaputt and k >= 4:
            continue
        a0 = math.pi * k / n; a1 = math.pi * (k + 1) / n
        # Keilstein als Ring-Segment
        bm = bmesh.new()
        pts = []
        for a in (a0 + 0.004, a1 - 0.004):
            for r in (rin, rau):
                for y in (-d / 2, d / 2):
                    pts.append(bm.verts.new((-r * math.cos(a), y, h_pf + r * math.sin(a))))
        v = pts
        # Indizes: a(0/1)*4 + r(0/1)*2 + y(0/1)
        quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        for q in quads:
            bm.faces.new([v[i] for i in q])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
        verbiegen(bm, m.rnd, 0.008, 0.25)
        m.teil(bm, "stein", None)
    # Schlussstein etwas höher
    if not kaputt:
        bm = basis.klotz(m.rnd, 0.3, d + 0.04, 0.62, 0.012, 0.008, 0.2)
        m.teil(bm, "stein", M((0, 0, h_pf + rin + 0.27)))
    else:
        for i in range(5):
            bm = basis.klotz(m.rnd, 0.42, 0.55, 0.32, 0.012, 0.008, 0.9)
            m.teil(bm, "stein", M((m.rnd.uniform(0.3, 2.2), m.rnd.uniform(-1.2, 1.0), 0.16),
                                  (m.rnd.uniform(-10, 10), m.rnd.uniform(-10, 10), m.rnd.uniform(0, 180))))


MODELLE = {"kiste": kiste, "fass": fass, "stuhl": stuhl, "hocker": hocker, "tisch": tisch, "bank": bank,
           "zaun": zaun, "palisade": palisade, "zelt": zelt, "lagerfeuer": lagerfeuer, "karren": karren,
           "laterne": laterne, "laternenpfahl": laternenpfahl, "saeule": saeule, "mauer": mauer, "bogen": bogen}


# ======================================================================== Export

def exportieren(ob, pfad):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=pfad, export_format="GLB", use_selection=True, export_materials="EXPORT",
                              export_image_format="NONE", export_apply=True, export_yup=True)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print(f"  {os.path.basename(pfad)}: {tris} Dreiecke, Materialien {[s.material.name for s in ob.material_slots]}")
    return tris


def bauen(namen=None, modelle=MODELLE):
    obs = {}
    for name, fn in modelle.items():
        if namen and name not in namen:
            continue
        for kaputt in (False, True):
            n = name + ("_kaputt" if kaputt else "")
            m = Modell(n, saat=sum(map(ord, n)))
            fn(m, kaputt)
            obs[n] = m.fertig()
    return obs


def hauptprogramm(modelle=MODELLE):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    hier = os.path.dirname(os.path.abspath(__file__))
    ziel = args[0] if args and not args[0].startswith("--") else os.path.join(hier, "..", "modelle")
    nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else None
    vorschau = args[args.index("--vorschau") + 1] if "--vorschau" in args else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    basis.TEXTUR_ORDNER = os.path.join(hier, "..", "texturen")
    os.makedirs(ziel, exist_ok=True)
    obs = bauen(nur, modelle)
    for n, ob in obs.items():
        exportieren(ob, os.path.join(ziel, n + ".glb"))
    if vorschau:
        import vorschau as vs
        os.makedirs(vorschau, exist_ok=True)
        vs.szene_vorbereiten()
        for n, ob in obs.items():
            vs.rendern([ob], os.path.join(vorschau, n + ".jpg"))


if __name__ == "__main__":
    hauptprogramm()
