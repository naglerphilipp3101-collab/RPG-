"""Lager- und Militär-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python militaer.py -- <zielordner/modelle> [--nur banner_weiss,feldbett] [--vorschau <ordner>]

  banner_<farbe>     Fraktionsbanner an einer Stange im Kreuzfuß (weiss New Light, blau Eternal Wrath, schwarz Deaths Dance,
                     gruen Archo's Legacy, rot Sentinels, gelb Obex); kaputt: Stange gebrochen, Banner zerrissen am Boden
  spanische_reiter   Balken mit gekreuzten, angespitzten Pfählen
  pfeilbuendel       Pfeilfass mit Pfeilen und ein verschnürtes Bündel
  ruestungsstapel    Brustpanzer, Helme und Rundschilde auf einer Palette
  feldbett           Klappbett mit Scherenbeinen, Decke und Kissen
  kartentisch        Tisch mit Landkarte, Markern, Kerze und Dolch
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, verbiegen, ausrichten
import props
import deko
from kueche import haufen, ellipsoid


# ======================================================================== Banner

def _poly_innen(u, v, pts):
    drin = False
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        if (y1 > v) != (y2 > v) and u < x1 + (v - y1) * (x2 - x1) / (y2 - y1):
            drin = not drin
    return drin


def _sonne(u, v):
    r = math.hypot(u, v); a = math.atan2(v, u)
    return r < 0.32 or (0.4 < r < 0.62 and math.cos(12 * a) > 0.55)


BLITZ = [(0.15, 0.75), (-0.3, 0.0), (0.0, 0.0), (-0.2, -0.75), (0.35, 0.12), (0.05, 0.12), (0.3, 0.75)]


def _blitz(u, v):
    return _poly_innen(u, v, BLITZ)


def _dolche(u, v):
    for s in (-1, 1):
        a = (u * math.cos(math.pi / 4) + s * v * math.sin(math.pi / 4)); b = (-u * math.sin(math.pi / 4) * s + v * math.cos(math.pi / 4))
        if abs(a) < 0.07 and abs(b) < 0.7 - (0.25 if b > 0.45 else 0) * 0:
            return True
        if abs(b + 0.42) < 0.05 and abs(a) < 0.2:
            return True
    return False


def _pfeil(u, v):
    if abs(u) < 0.06 and -0.65 < v < 0.3:
        return True
    if 0.25 < v < 0.72 and abs(u) < (0.72 - v) * 0.75:
        return True
    return -0.7 < v < -0.45 and abs(u) < 0.06 + (v + 0.45) * -0.6


def _turm(u, v):
    if abs(u) < 0.1 and -0.62 < v < -0.3:
        return False
    if abs(u) < 0.36 and -0.62 < v < 0.38:
        return True
    return abs(u) < 0.36 and 0.38 <= v < 0.58 and int((u + 0.36) / 0.144) % 2 == 0


def _schild(u, v):
    if abs(u) > 0.48 or v > 0.55:
        return False
    return v > -0.75 + 1.6 * u * u


FRAKTIONEN = {
    "weiss": ("fahne_weiss", "fahne_gold", _sonne),           # New Light
    "blau": ("fahne_blau", "fahne_weiss", _blitz),            # Eternal Wrath
    "schwarz": ("fahne_schwarz", "fahne_rot", _dolche),       # Deaths Dance
    "gruen": ("fahne_gruen", "fahne_gold", _pfeil),           # Archo's Legacy
    "rot": ("fahne_rot", "fahne_gold", _turm),                # Sentinels
    "gelb": ("fahne_gelb", "fahne_schwarz", _schild),         # Obex
}


def _fahnentuch(m, T, mat, emblem_mat, emblem, kaputt, W=0.8, L=1.6, zt=3.15):
    """Tuch hängt vom Querholz (Höhe zt) in der x-z-Ebene herab, unten mit Schwalbenschwanz. T: Lage im Modell."""
    nx, nz = 30, 60
    g = []
    o = m.rnd.uniform(0, 6)
    for i in range(nz + 1):
        t = i / nz
        zeile = []
        for j in range(nx + 1):
            s = j / nx
            x = -W / 2 + W * s; z = zt - L * t
            if not kaputt:
                y = 0.035 * math.sin(s * 9 + o) * (0.3 + t)
            else:
                y = -0.035 + 0.02 * (1 + math.sin(s * 7 + o) * math.cos(t * 9))
            zeile.append(tuple(T @ Vector((x, y, z))))
        g.append(zeile)
    zc = zt - 0.62

    def zelle(i, j):
        s = (j + 0.5) / nx; t = (i + 0.5) / nz
        u = (s - 0.5) * 2 * 0.82; v = (zt - L * t - zc) / (W / 2) * 0.82
        schwanz = t > 0.82 and abs(s - 0.5) < (t - 0.82) / 0.18 * 0.3
        loch = False
        if kaputt:
            loch = (math.hypot(s - 0.3, t - 0.7) < 0.09 + 0.04 * math.sin(j * 1.7 + i)) or \
                   (math.hypot(s - 0.75, t - 0.35) < 0.06 + 0.03 * math.sin(i * 2.1)) or (t > 0.9 and j % 5 == 0)
        return schwanz or loch, emblem(u, v)

    m.teil(flaeche(g, 0.004, lambda i, j: zelle(i, j)[0] or zelle(i, j)[1]), mat, None)
    m.teil(flaeche(g, 0.0045, lambda i, j: zelle(i, j)[0] or not zelle(i, j)[1]), emblem_mat, None)
    if kaputt:
        # versengter Saum unten
        g2 = [g[i] for i in range(nz - 6, nz + 1)]
        m.teil(flaeche(g2, 0.005, lambda i, j: (j + i) % 3 != 0 or zelle(i + nz - 6, j)[0]), "holz_verkohlt", None)


def banner(farbe):
    mat, emblem_mat, emblem = FRAKTIONEN[farbe]

    def bauen(m, kaputt):
        # Kreuzfuß mit Streben
        for a in (0, 90):
            m.kantholz(M(rot=(0, 0, a)) @ Vector((-0.6, 0, 0.05)), M(rot=(0, 0, a)) @ Vector((0.6, 0, 0.05)), 0.1, 0.1)
        for a in (0, 90, 180, 270):
            r = M(rot=(0, 0, a))
            m.kantholz(r @ Vector((0.45, 0, 0.1)), r @ Vector((0.03, 0, 0.55)), 0.05, 0.05)
        if not kaputt:
            T = Matrix.Identity(4)
            m.stab((0, 0, 0.0), (0, 0, 3.4), 0.04, "holz", biegen=0.003)
            m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.0, 0.16)], 10), "eisen", M((0, 0, 3.4)))
        else:
            # Stange in 1,2 m Höhe abgeknickt, das obere Stück liegt mit dem Banner am Boden
            m.stab((0, 0, 0.0), (0, 0, 1.2), 0.04, "holz", biegen=0.003)
            for k in range(5):
                a = 2 * math.pi * k / 5
                m.stab((0, 0, 1.18), (0.03 * math.cos(a), 0.03 * math.sin(a), 1.3 + 0.06 * (k % 2)), 0.012, "holz", biegen=0)
            T = Matrix.Translation((0.25, -0.5, 0.04)) @ Matrix.Rotation(math.radians(90), 4, "X") @ \
                Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Translation((0, 0, -1.25))
            m.stab(tuple(T @ Vector((0, 0, 1.25))), tuple(T @ Vector((0, 0, 3.4))), 0.04, "holz", biegen=0.003)
            m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.0, 0.16)], 10), "eisen", T @ M((0, 0, 3.4)))
        # Querholz und Schnüre
        m.stab(tuple(T @ Vector((-0.48, 0.0, 3.2))), tuple(T @ Vector((0.48, 0.0, 3.2))), 0.022, "holz", biegen=0)
        for x in (-0.36, -0.12, 0.12, 0.36):
            ring = [tuple(T @ Vector((x, 0.03 * math.sin(2 * math.pi * k / 8), 3.2 + 0.03 * math.cos(2 * math.pi * k / 8) - 0.0)))
                    for k in range(9)]
            m.seil(ring, 0.004)
        _fahnentuch(m, T, mat, emblem_mat, emblem, kaputt, zt=3.17)
    return bauen


# ======================================================================== Spanische Reiter

def spanische_reiter(m, kaputt):
    L = 2.4
    zb = 0.5
    xs = [-1.05 + 0.35 * k for k in range(7)]

    def pfahl(x, s):
        a = Vector((x + 0.02 * s, -s * 0.55, 0.0))
        b = Vector((x + 0.02 * s, s * 0.55, 1.1))
        return a, b, (b - a).normalized()

    def spitze(b, richtung):
        m.teil(drehkoerper([(0.04, 0.0), (0.0, 0.14)], 8), "holz", ausrichten(b, b + richtung * 0.001) @ M(rot=(0, 90, 0)) @ M((0, 0, -0.005)))

    if not kaputt:
        bm = rundholz(0.09, L, 12, 4)
        verbiegen(bm, m.rnd, 0.01, 0.5)
        m.teil(bm, "holz_alt", M((0, 0, zb)), uv="zyl", r=0.09)
        for x in xs:
            for s in (-1, 1):
                a, b, richtung = pfahl(x, s)
                m.stab(tuple(a), tuple(b), 0.04, "holz_alt", biegen=0.004)
                spitze(b, richtung)
        return
    # In der Mitte durchgebrochen: jede Hälfte kippt um die Füße ihres äußeren Kreuzes, bis das Bruchende am Boden liegt.
    # Die inneren Pfähle sind unter dem Balken abgeknickt (oben stecken Stümpfe), ihre unteren Teile liegen am Boden.
    bruch_x = -0.12
    for seite, (x0, x1, aussen) in enumerate(((-L / 2, bruch_x, -1.05), (bruch_x + 0.03, L / 2, 1.05))):
        innen = x1 if seite == 0 else x0
        dx = abs(innen - aussen) + 0.03
        w = math.atan2(zb - 0.09, dx) * (1 if seite == 0 else -1)
        dreh = Vector((aussen, 0, 0))
        m.G = Matrix.Translation(dreh) @ Matrix.Rotation(w, 4, "Y") @ Matrix.Translation(-dreh)
        m.stab((x0, 0, zb), (x1, 0, zb), 0.09, "holz_alt", seg=12, biegen=0.01, bruch=(1 if seite == 0 else -1), bruch_tiefe=0.1)
        for k, x in enumerate(xs):
            if (x < bruch_x) != (seite == 0) or k == 3:
                continue
            for s in (-1, 1):
                a, b, richtung = pfahl(x, s)
                if k in (0, 6):
                    m.stab(tuple(a), tuple(b), 0.04, "holz_alt", biegen=0.004)
                    spitze(b, richtung)
                else:
                    knick = a + (b - a) * 0.36
                    m.stab(tuple(knick), tuple(b), 0.04, "holz_alt", biegen=0.004, bruch=-1, bruch_tiefe=0.07)
                    if (k + (s > 0)) % 3:
                        spitze(b, richtung)
        m.G = None
    # abgeknickte Unterteile und das ganz herausgerissene mittlere Kreuz liegen am Boden
    for k, (x, y, w, l) in enumerate(((-0.75, -0.95, 15, 0.56), (-0.3, -1.1, -20, 0.56), (0.45, -0.9, 30, 0.56), (0.95, 0.95, -10, 0.56),
                                      (-0.55, 0.95, 60, 0.56), (0.15, 1.15, 5, 1.56), (0.35, -1.35, -5, 1.56))):
        v = Vector((math.cos(math.radians(w)), math.sin(math.radians(w)), 0)) * l / 2
        p = Vector((x, y, 0.04))
        m.stab(tuple(p - v), tuple(p + v), 0.04, "holz_alt", biegen=0.004, bruch=(1 if l < 1 else 0), bruch_tiefe=0.07)
        if l > 1:
            spitze(p + v, v.normalized())


# ======================================================================== Pfeile

def pfeil(m, spitze, nock, gebrochen=False):
    a, b = Vector(spitze), Vector(nock)
    rich = (b - a).normalized()
    if gebrochen:
        b = a + (b - a) * m.rnd.uniform(0.35, 0.6)
    m.stab(tuple(a + rich * 0.04), tuple(b), 0.005, "holz", seg=5, biegen=0)
    m.teil(drehkoerper([(0.011, 0.0), (0.0, 0.05)], 6), "eisen", ausrichten(a + rich * 0.04, a) @ M(rot=(0, 90, 0)) @ M((0, 0, -0.025)))
    if gebrochen:
        return
    rahmen = ausrichten(b - rich * 0.12, b - rich * 0.02)
    for k in range(3):
        m.teil(quader(0.1, 0.0015, 0.016), "farbe_weiss" if k else "fahne_rot", rahmen @ M(rot=(120 * k, 0, 0)) @ M((0, 0, 0.012)))


def pfeilbuendel(m, kaputt):
    fass = [(0.0, 0.0), (0.16, 0.0), (0.18, 0.25), (0.17, 0.5), (0.155, 0.5), (0.165, 0.25), (0.145, 0.02), (0.0, 0.02)]
    if not kaputt:
        m.teil(drehkoerper(fass, 20, False, False), "holz", M((0, 0.1, 0.0)), uv="zylz", r=0.18)
        for z in (0.08, 0.42):
            r = 0.17 + 0.01 * math.sin(math.pi * z / 0.5)
            ring = [(r * math.cos(2 * math.pi * k / 20), 0.1 + r * math.sin(2 * math.pi * k / 20), z) for k in range(21)]
            m.seil(ring, 0.008, 4, "eisen")
        for k in range(26):
            a = m.rnd.uniform(0, 2 * math.pi); d = math.sqrt(m.rnd.random()) * 0.12
            fuss = Vector((d * math.cos(a), 0.1 + d * math.sin(a), 0.03))
            kopf = fuss + Vector((m.rnd.uniform(-0.12, 0.12), m.rnd.uniform(-0.12, 0.12), 0.78))
            pfeil(m, fuss, kopf)
        # verschnürtes Bündel daneben am Boden
        for k in range(12):
            y = -0.35 + (k % 4) * 0.012 - 0.018; z = 0.006 + (k // 4) * 0.011
            pfeil(m, (-0.45, y, z), (0.35, y + 0.004 * (k % 3), z))
        for x in (-0.2, 0.15):
            ring = [(x, -0.37 + 0.035 * math.cos(2 * math.pi * k / 10), 0.018 + 0.02 * math.sin(2 * math.pi * k / 10)) for k in range(11)]
            m.seil(ring, 0.004)
        return
    # Fass umgekippt, Pfeile verstreut und zertreten
    m.umfallen_start()
    m.teil(drehkoerper(fass, 20, False, False), "holz", M((0, 0.1, 0.0)), uv="zylz", r=0.18)
    for z in (0.08, 0.42):
        r = 0.17 + 0.01 * math.sin(math.pi * z / 0.5)
        ring = [(r * math.cos(2 * math.pi * k / 20), 0.1 + r * math.sin(2 * math.pi * k / 20), z) for k in range(21)]
        m.seil(ring, 0.008, 4, "eisen")
    m.umfallen_ende(-60)
    for k in range(18):
        a = m.rnd.uniform(-2.6, -0.5); d = m.rnd.uniform(0.35, 1.0)
        p = Vector((d * math.cos(a), d * math.sin(a), 0.006 + 0.01 * (k % 2)))
        w = m.rnd.uniform(0, 2 * math.pi)
        pfeil(m, p, p + Vector((0.8 * math.cos(w), 0.8 * math.sin(w), 0.0)), gebrochen=k % 3 == 0)


# ======================================================================== Rüstungsstapel

def brustpanzer(m, matrix, beule=0.0, loch=False):
    prof = [(0.15, 0.0), (0.165, 0.08), (0.18, 0.2), (0.17, 0.3), (0.14, 0.37), (0.09, 0.4)]
    bm = drehkoerper(prof, 12, False, False, winkel=(-75, 75))
    if loch:
        weg = [f for f in bm.faces if (lambda c: math.hypot(c.y, c.z - 0.2) < 0.05)(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=weg, context="FACES")
    if beule:
        verbiegen(bm, m.rnd, beule, 0.12)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.004)
    m.teil(bm, "eisen", matrix)


def helm(m, matrix, beule=0.0):
    bm = drehkoerper([(0.19, 0.0), (0.13, 0.025), (0.12, 0.09), (0.1, 0.16), (0.05, 0.2), (0.0, 0.21)], 16, False, False)
    if beule:
        verbiegen(bm, m.rnd, beule, 0.08)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.004)
    m.teil(bm, "eisen", matrix, uv="zylz", r=0.19)


def rundschild(m, matrix, r=0.3, halb=False):
    w = (0, 360) if not halb else (0, 170)
    scheibe = drehkoerper([(0.0, 0.0), (r, 0.0), (r, 0.02), (0.0, 0.02)], 24 if not halb else 12, not halb, not halb, winkel=w)
    m.teil(scheibe, "holz", matrix, uv="box")
    if halb:
        m.teil(quader(2 * r, 0.004, 0.02), "holz", matrix @ M((0, 0.002, 0.01)))
        m.teil(rohr([(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0.01) for a in range(0, 171, 10)], 0.012, 5, False),
               "eisen", matrix, uv=None)
        return
    m.teil(rohr([(r * math.cos(2 * math.pi * k / 24), r * math.sin(2 * math.pi * k / 24), 0.01) for k in range(25)], 0.012, 5, False),
           "eisen", matrix, uv=None)
    m.teil(drehkoerper([(0.07, 0.0), (0.06, 0.03), (0.03, 0.06), (0.0, 0.065)], 12), "eisen", matrix @ M((0, 0, 0.02)))


def palette(m):
    for y in (-0.35, 0.0, 0.35):
        m.kantholz((-0.6, y, 0.04), (0.6, y, 0.04), 0.08, 0.08)
    for k in range(6):
        m.brett(0.19, 0.85, 0.025, M((-0.5 + 0.2 * k, 0, 0.0925)), "holz", biegen=0.002)


def ruestungsstapel(m, kaputt):
    palette(m)
    zp = 0.105
    if not kaputt:
        for k in range(3):
            brustpanzer(m, M((-0.3, 0.0, zp - 0.04 + 0.035 * k), (0, -90, 0)) @ M((0, 0, -0.2)))
        for k, (x, y) in enumerate([(0.25, -0.2), (0.3, 0.2)]):
            helm(m, M((x, y, zp)))
        helm(m, M((0.28, 0.0, zp + 0.21 - 0.03)), 0.0) if False else None
        for k in range(2):
            rundschild(m, M((0.25, 0.0, zp + 0.21 + 0.022 * k), (0, 0, 20 * k)))
        # zwei Schilde an die Palette gelehnt
        for k, x in enumerate((-0.35, 0.25)):
            rundschild(m, M((x, -0.47 - 0.05, 0.3), (-75, 0, 10 * k)) @ M((0, 0, -0.02)) @ M((0, 0, 0)))
        return
    # durchwühlt: Teile verstreut, ein Helm verbeult, ein Panzer durchschlagen, ein Schild gespalten
    brustpanzer(m, M((-0.3, 0.0, zp - 0.04), (0, -90, 0)) @ M((0, 0, -0.2)), loch=True)
    brustpanzer(m, M((-0.7, -0.75, -0.04), (0, -90, 35)) @ M((0, 0, -0.2)), beule=0.015)
    helm(m, M((0.25, 0.15, zp)), beule=0.02)
    helm(m, M((0.55, -0.85, 0.12), (100, 0, 30)) @ M((0, 0, -0.1)), 0.0)
    rundschild(m, M((0.3, -0.75, 0.0), (0, 0, 15)), halb=True)
    rundschild(m, M((0.45, -0.68, 0.0), (0, 0, 200)) @ M((0.03, 0.0, 0)), halb=True)


# ======================================================================== Feldbett

def feldbett(m, kaputt):
    L, B, z = 1.9, 0.66, 0.42
    if kaputt:
        # Kopfende eingeknickt: das Bett liegt dort auf dem Boden
        drehpunkt = Vector((0, -0.85, 0))
        w = math.atan2(z, L * 0.9)
        m.G = Matrix.Translation(drehpunkt) @ Matrix.Rotation(-w, 4, Vector((1, 0, 0))) @ Matrix.Translation(-drehpunkt)
    for s in (-1, 1):
        m.stab((s * B / 2, -L / 2, z), (s * B / 2, L / 2, z), 0.022, "holz", biegen=0)
    for y in (-L / 2 + 0.05, L / 2 - 0.05):
        m.stab((-B / 2, y, z - 0.03), (B / 2, y, z - 0.03), 0.015, "holz", biegen=0)
    beine = (-0.85, 0.0, 0.85) if not kaputt else (-0.85,)
    for y in beine:
        for s in (-1, 1):
            m.stab((s * B / 2, y + 0.03 * s, z), (-s * (B / 2 + 0.02), y + 0.03 * s, 0.0), 0.016, "holz", biegen=0)
        m.stab((0.0, y - 0.03, z / 2), (0.0, y + 0.03, z / 2), 0.012, "eisen", biegen=0)
    # Bespannung: hängt zwischen den Holmen durch
    nx, ny = 8, 20
    g = []
    for i in range(ny + 1):
        y = -L / 2 + 0.08 + (L - 0.16) * i / ny
        zeile = []
        for j in range(nx + 1):
            x = -B / 2 + B * j / nx
            durch = 0.05 if not kaputt else 0.12 * math.sin(math.pi * i / ny)
            zeile.append((x, y, z + 0.015 - durch * math.sin(math.pi * j / nx) - (0.0 if not kaputt else 0.03 * math.sin(i))))
        g.append(zeile)
    loch = (lambda i, j: (i in (9, 10, 11) and j in (3, 4)) or (i == 12 and j == 4)) if kaputt else None
    m.teil(flaeche(g, 0.004, loch), "stoff", None)
    m.G = None
    if not kaputt:
        kissen = quader(0.45, 0.28, 0.1, 4, 3, 1, fase=0.04)
        verbiegen(kissen, m.rnd, 0.01, 0.1)
        m.teil(kissen, "stoff", M((0, L / 2 - 0.25, z)))
        decke = quader(0.6, 0.35, 0.08, 4, 3, 2, fase=0.03)
        verbiegen(decke, m.rnd, 0.01, 0.1)
        m.teil(decke, "wolle_rot", M((0, -L / 2 + 0.3, z + 0.0)))
        return
    # abgebrochene Beine und Decke am Boden
    m.stab((0.3, 0.6, 0.016), (0.75, 0.25, 0.016), 0.016, "holz", biegen=0)
    m.stab((-0.55, 0.3, 0.016), (-0.7, -0.15, 0.016), 0.016, "holz", biegen=0)
    from taverne import decke_liegend
    decke_liegend(m, M((0.85, -0.4, 0.0), (0, 0, 20)), 0.7, 0.6, m.rnd, hoch=0.05)


# ======================================================================== Kartentisch

def karte(m, matrix, lx, ly, kaputt=False):
    nx, ny = 20, 14
    g = []
    for i in range(ny + 1):
        y = -ly / 2 + ly * i / ny
        zeile = []
        for j in range(nx + 1):
            x = -lx / 2 + lx * j / nx
            rand = max(0.0, abs(x) / (lx / 2) - 0.85) * 0.12 + (0.006 * math.sin(i * 1.3 + j) if kaputt else 0.0)
            zeile.append(tuple(matrix @ Vector((x, y, 0.001 + rand))))
        g.append(zeile)
    loch = None
    if kaputt:
        loch = lambda i, j: math.hypot(j - 14, i - 9) < 3.2 + math.sin(i * 2.0 + j) or (i < 2 and j > 15)
    m.teil(flaeche(g, 0.002, loch), "papier", None)
    # gezeichnete Küste, Fluss, Wälder
    kueste = [(-0.4 + 0.8 * k / 16, 0.2 * math.sin(k * 0.7) - 0.05, 0) for k in range(17)]
    for (x, y, _), (x2, y2, _) in zip(kueste, kueste[1:]):
        if kaputt and x > 0.1:
            break
        m.teil(quader(math.hypot(x2 - x, y2 - y) + 0.004, 0.004, 0.001), "holz_verkohlt",
               matrix @ M(((x + x2) / 2, (y + y2) / 2, 0.003), (0, 0, math.degrees(math.atan2(y2 - y, x2 - x)))))
    for k in range(9 if not kaputt else 4):
        x = m.rnd.uniform(-0.38, 0.0); y = m.rnd.uniform(0.0, 0.25)
        m.teil(drehkoerper([(0.0, 0.0), (0.015, 0.0), (0.0, 0.001)], 6), "fahne_gruen", matrix @ M((x, y, 0.0028)), uv=None)
    if kaputt:
        for k in range(5):
            m.teil(drehkoerper([(0.0, 0.0), (0.03, 0.0), (0.0, 0.001)], 8), "holz_verkohlt",
                   matrix @ M((m.rnd.uniform(-0.3, 0.3), m.rnd.uniform(-0.2, 0.2), 0.003), skal=(1.5, 1, 1)), uv=None)


def marker(m, matrix, mat):
    m.teil(drehkoerper([(0.0, 0.0), (0.018, 0.0), (0.014, 0.03), (0.008, 0.04), (0.0, 0.042)], 8), mat, matrix)


def kartentisch(m, kaputt):
    props.tisch(m, kaputt)
    h = 0.76
    if not kaputt:
        karte(m, M((0.0, 0.0, h)), 1.0, 0.65)
        for k, mat in enumerate(["fahne_rot", "fahne_rot", "fahne_blau", "fahne_blau", "fahne_blau", "fahne_schwarz"]):
            marker(m, M((-0.25 + 0.1 * k, -0.1 + 0.08 * (k % 3), h + 0.003)), mat)
        # Fähnchen auf Nadeln
        for x, y, mat in ((0.2, 0.1, "fahne_gelb"), (-0.3, 0.15, "fahne_rot")):
            m.stab((x, y, h), (x, y, h + 0.12), 0.002, "eisen", seg=4, biegen=0)
            bm = bmesh.new()
            vs = [bm.verts.new(p) for p in ((x, y, h + 0.12), (x + 0.06, y, h + 0.1), (x, y, h + 0.08))]
            bm.faces.new(vs)
            bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.002)
            m.teil(bm, mat, None)
        deko.kerze(m, M((0.6, 0.25, h)), 0.1)
        m.teil(drehkoerper([(0.0, 0.0), (0.05, 0.0), (0.05, 0.01), (0.0, 0.012)], 10), "eisen", M((0.6, 0.25, h)))
        # Dolch steckt in der Karte
        deko.klinge(m, M((0.35, -0.12, h - 0.02), (0, 0, 30)), 0.18, 0.03)
        m.stab((0.35, -0.12, h + 0.16), (0.35, -0.12, h + 0.27), 0.012, "leder", biegen=0)
        m.teil(quader(0.1, 0.02, 0.02), "eisen", M((0.35, -0.12, h + 0.16), (0, 0, 30)))
        # Schriftrollen
        for k in range(2):
            m.teil(rundholz(0.025, 0.35, 10), "papier", M((-0.55, 0.28 - 0.06 * k, h + 0.025), (0, 0, 80 + 10 * k)), uv="zyl", r=0.025)
        return
    # Tisch eingeknickt (props.tisch), Karte zerrissen und angesengt am Boden, Marker verstreut
    karte(m, M((-0.35, -1.15, 0.0), (0, 0, -12)), 1.0, 0.65, kaputt=True)
    for k, mat in enumerate(["fahne_rot", "fahne_blau", "fahne_blau", "fahne_schwarz"]):
        marker(m, M((m.rnd.uniform(-0.9, 0.5), m.rnd.uniform(-1.6, -0.9), 0.018), (90, 0, m.rnd.uniform(0, 360))) @ M((0, 0, -0.02)), mat)
    m.teil(rundholz(0.025, 0.35, 10), "papier", M((0.5, -0.9, 0.025), (0, 0, 30)), uv="zyl", r=0.025)


MODELLE = {"banner_" + f: banner(f) for f in FRAKTIONEN}
MODELLE.update({"spanische_reiter": spanische_reiter, "pfeilbuendel": pfeilbuendel, "ruestungsstapel": ruestungsstapel,
                "feldbett": feldbett, "kartentisch": kartentisch})


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
