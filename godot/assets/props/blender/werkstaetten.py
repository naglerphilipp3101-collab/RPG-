"""Werkstatt-Props (Deko, nicht benutzbar), jedes heil und kaputt (kaputt = beschädigt, geplündert, verlassen).
Aufruf: python werkstaetten.py -- <zielordner/modelle> [--nur schleifstein,werkbank] [--vorschau <ordner>]

  schleifstein   Schleifstein im Holzgestell mit Kurbel und Wassertrog darunter
  werkbank       Hobelbank mit Zange (Schraubstock), Werkzeug und Hobelspänen
  holzstapel     gestapelte Holzscheite zwischen Pfählen, Hackklotz mit Axt
  webstuhl       Trittwebstuhl mit Kettfäden, halbfertigem Tuch und Bank
  gerberrahmen   Stangenrahmen mit eingeschnürter Haut, Gerbbottich und Schaber
  wassertrog     Bretter-Trog mit Eisenbändern auf zwei Kufen
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, klotz, verbiegen, ausrichten
import props
from props import bretterwand
import deko
from kueche import drehstueck, haufen, ellipsoid


# ======================================================================== Hilfen

def wasserflaeche(m, matrix, lx, ly):
    m.teil(quader(lx, ly, 0.004), "wasser", matrix)


def bein(m, oben, unten, b=0.07, mat="holz", bruch=0):
    m.kantholz(oben, unten, b, b, mat, bruch=bruch)


def scheit(m, matrix, L=0.4, r=0.075, a0=None):
    """Gespaltenes Holzscheit (Viertel eines Rundholzes) entlang x, Rinde außen."""
    a0 = m.rnd.uniform(0, 360) if a0 is None else a0
    prof = [(0.0, -L / 2), (r, -L / 2), (r * 1.02, 0.0), (r, L / 2), (0.0, L / 2)]
    drehstueck(m, prof, a0, a0 + 95, "holz_alt", "holz", matrix @ M(rot=(0, 90, 0)), seg=5,
               verformen=lambda bm: verbiegen(bm, m.rnd, 0.004, 0.1))


def hammer(m, matrix):
    m.stab(tuple(matrix @ Vector((0, 0, 0.012))), tuple(matrix @ Vector((0.3, 0, 0.012))), 0.012, "holz", biegen=0)
    m.teil(quader(0.03, 0.1, 0.03, fase=0.004), "eisen", matrix @ M((0.29, 0.01, 0.015)))


def saege(m, matrix, bruch=False):
    """Fuchsschwanz: Blatt entlang x, liegt flach."""
    bm = bmesh.new()
    L = 0.42 if not bruch else 0.22
    pts = [(0.0, -0.05), (L, -0.025), (L, 0.0), (0.0, 0.0)]
    vs = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    bm.faces.new(vs)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.002)
    m.teil(bm, "eisen", matrix @ M((0, 0, 0.004)))
    m.teil(quader(0.11, 0.06, 0.025, fase=0.008), "holz", matrix @ M((-0.05, -0.025, 0.0125)))


def meissel(m, matrix):
    m.stab(tuple(matrix @ Vector((0, 0, 0.012))), tuple(matrix @ Vector((0.1, 0, 0.012))), 0.012, "holz", biegen=0)
    m.teil(quader(0.1, 0.016, 0.005), "eisen", matrix @ M((0.15, 0, 0.006)))


def hobel(m, matrix):
    m.teil(quader(0.24, 0.07, 0.06, fase=0.01), "holz", matrix @ M((0, 0, 0.03)))
    m.teil(quader(0.012, 0.05, 0.07), "eisen", matrix @ M((0.02, 0, 0.05), (0, -35, 0)))
    m.teil(drehkoerper([(0.0, 0.0), (0.02, 0.0), (0.02, 0.05), (0.0, 0.055)], 8), "holz", matrix @ M((-0.07, 0, 0.06), (0, -20, 0)))


def spaene(m, matrix, n, weite):
    """Hobelspäne: kleine Locken."""
    for k in range(n):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0, weite)
        r = m.rnd.uniform(0.01, 0.018)
        locke = [(r * math.cos(t), 0.004 * t, r + r * math.sin(t)) for t in (i * 0.5 for i in range(14))]
        bm = rohr(locke, 0.004, 3)
        for v in bm.verts:
            v.co.y *= 1.0
        m.teil(bm, "holz", M((matrix @ Vector((d * math.cos(a), d * math.sin(a), 0)))) @ M(rot=(0, 0, m.rnd.uniform(0, 360))),
               uv=None)


# ======================================================================== Schleifstein

def schleifstein(m, kaputt):
    zr = 0.55                                        # Oberkante der Holme
    for s in (-1, 1):
        x = s * 0.1
        m.kantholz((x, -0.5, zr - 0.04), (x, 0.5, zr - 0.04), 0.06, 0.08)
        for t in (-1, 1):
            bein(m, (x, t * 0.42, zr - 0.06), (s * 0.2, t * 0.55, 0.0), 0.06)
    # Querriegel unten, darauf der Trog
    for t in (-1, 1):
        y = t * 0.5
        m.kantholz((-0.17, y, 0.22), (0.17, y, 0.22), 0.05, 0.05)
    tz = 0.245
    m.brett(0.15, 0.1, 0.02, M((0, -0.47, tz + 0.06), (90, 0, 0)), "holz", biegen=0)
    if not kaputt:
        m.brett(0.15, 0.1, 0.02, M((0, 0.47, tz + 0.06), (90, 0, 0)), "holz", biegen=0)
    for s in (-1, 1):
        m.brett(0.96, 0.1, 0.02, M((s * 0.085, 0, tz + 0.06), (0, 0, 90)) @ M(rot=(90, 0, 0)), "holz", biegen=0.002)
    m.brett(0.96, 0.17, 0.02, M((0, 0, tz), (0, 0, 90)), "holz", biegen=0.002)
    # Lagerböcke auf den Holmen, Achse
    za = zr + 0.03
    for s in (-1, 1):
        m.teil(quader(0.06, 0.1, 0.06, fase=0.006), "holz", M((s * 0.1, 0, zr + 0.03)))
    ring = [(0.03, -0.04), (0.28, -0.04), (0.3, -0.025), (0.3, 0.025), (0.28, 0.04), (0.03, 0.04), (0.03, -0.04)]
    stein = M((0, 0, za), (0, 90, 0))
    if not kaputt:
        wasserflaeche(m, M((0, 0, tz + 0.07)), 0.15, 0.92)
        m.stab((-0.16, 0, za), (0.3, 0, za), 0.02, "eisen", biegen=0)
        bm = drehkoerper(ring, 36, False, False)
        verbiegen(bm, m.rnd, 0.004, 0.1)
        m.teil(bm, "stein", stein, uv="zylz", r=0.3)
        # Kurbel
        m.stab((0.3, 0, za), (0.3, 0, za - 0.16), 0.014, "eisen", biegen=0)
        m.stab((0.3, 0, za - 0.16), (0.42, 0, za - 0.16), 0.016, "holz", biegen=0)
        return
    # Stein zersprungen: ein Stück hängt noch auf der Achse, eins liegt im leeren Trog, eins am Boden; Kurbel fehlt
    m.stab((-0.16, 0, za), (0.2, 0, za), 0.02, "eisen", biegen=0)
    bm = drehkoerper(ring, 14, False, False, winkel=(-20, 140))
    m.teil(bm, "stein", stein, uv="zylz", r=0.3)
    stueck = drehkoerper(ring, 8, False, False, winkel=(150, 230))
    m.teil(stueck, "stein", M((0.0, -0.05, tz + 0.29), (0, 90, 0)) @ M(rot=(0, 0, 25)), uv="zylz", r=0.3)
    stueck = drehkoerper(ring, 10, False, False, winkel=(230, 340))
    m.teil(stueck, "stein", M((0.45, -0.35, 0.04), (0, 0, 30)) @ M((0, 0.0, 0), (0, 0, 0)) @ M((-0.17, 0.0, 0.0)), uv="zylz", r=0.3)
    for k in range(6):
        g = m.rnd.uniform(0.015, 0.035)
        m.teil(brocken(m.rnd, g, g * 0.8, g * 0.5, 0.3, 1), "stein", M((m.rnd.uniform(-0.4, 0.6), m.rnd.uniform(-0.6, -0.2), g * 0.4)))


# ======================================================================== Werkbank

def werkbank(m, kaputt):
    L, B, H = 1.6, 0.6, 0.85
    for sx in (-1, 1):
        for sy in (-1, 1):
            bein(m, (sx * 0.68, sy * 0.24, H - 0.06), (sx * 0.7, sy * 0.25, 0.0), 0.08)
        m.kantholz((sx * 0.69, -0.26, 0.18), (sx * 0.69, 0.26, 0.18), 0.06, 0.06)
    m.kantholz((-0.7, 0.0, 0.18), (0.7, 0.0, 0.18), 0.06, 0.06)
    # Ablage unten
    for k in range(4):
        if kaputt and k == 1:
            m.brett(0.7, 0.12, 0.02, M((-0.3, -0.2 + 0.13 * k, 0.21), (0, 0, 3)), "holz", bruch=1)
            continue
        m.brett(1.38, 0.12, 0.02, M((0, -0.2 + 0.13 * k, 0.22)), "holz")
    # dicke Platte aus drei Bohlen
    for k in range(3):
        if kaputt and k == 0:
            # vordere Bohle gebrochen: nur noch der linke Teil liegt auf
            m.brett(0.9, 0.2, 0.06, M((-0.35, -0.2, H - 0.03)), "holz", bruch=1)
            continue
        m.brett(L, 0.2, 0.06, M((0, -0.2 + 0.2 * k, H - 0.03)), "holz", biegen=0.002)
    # Zange (Vorderzange) links vorn
    m.teil(quader(0.3, 0.06, 0.2, fase=0.01), "holz", M((-0.6, -0.33, H - 0.1)))
    if not kaputt:
        m.stab((-0.6, -0.38, H - 0.07), (-0.6, -0.2, H - 0.07), 0.018, "holz", biegen=0)
        m.stab((-0.68, -0.4, H - 0.07), (-0.52, -0.4, H - 0.07), 0.012, "holz", biegen=0)
        # Werkzeug
        hammer(m, M((0.25, -0.1, H), (0, 0, 20)))
        saege(m, M((-0.2, 0.15, H), (0, 0, -5)))
        meissel(m, M((0.5, -0.18, H), (0, 0, -30)))
        meissel(m, M((0.55, -0.12, H), (0, 0, -20)))
        hobel(m, M((0.05, 0.05, H), (0, 0, 70)))
        m.brett(0.6, 0.12, 0.03, M((0.4, 0.15, H + 0.015), (0, 0, 8)), "holz", biegen=0.002)
        spaene(m, M((0.1, -0.05, H)), 10, 0.15)
        spaene(m, M((0.0, -0.45, 0.0)), 8, 0.2)
        return
    # geplündert: Zangenspindel fehlt, nur eine zerbrochene Säge liegt am Boden
    saege(m, M((0.3, -0.55, 0.0), (0, 0, 160)), bruch=True)
    spaene(m, M((0.1, 0.1, H)), 4, 0.2)
    spaene(m, M((-0.2, -0.5, 0.0)), 10, 0.3)
    # heruntergefallenes Bohlenstück
    m.brett(0.6, 0.2, 0.06, M((0.45, -0.55, 0.03), (0, 0, 12)), "holz", bruch=-1)


# ======================================================================== Holzstapel mit Hackklotz

def holzstapel(m, kaputt):
    L, r = 0.4, 0.075
    xs = [-0.6 + 0.085 * k for k in range(15)]
    if not kaputt:
        for reihe in range(6):
            versatz = 0.04 * (reihe % 2)
            for x in xs[: 15 - reihe % 2]:
                scheit(m, M((x + versatz, 0.3, 0.05 + reihe * 0.085), (0, 0, 90)), L, r)
        for s in (-1, 1):
            m.stab((s * 0.7, 0.3, -0.05), (s * 0.7, 0.3, 0.65), 0.035, "holz_alt", biegen=0.004)
    else:
        # umgestürzt: Scheite in einem flachen Haufen, ein Pfahl umgebrochen
        for k in range(46):
            x = m.rnd.uniform(-0.75, 0.75); y = m.rnd.uniform(0.0, 0.6)
            lage = 0 if k < 26 else 1
            scheit(m, M((x, y, 0.045 + lage * 0.07), (m.rnd.uniform(-8, 8), m.rnd.uniform(-8, 8), m.rnd.uniform(-60, 60) + 90)), L, r)
        m.stab((-0.7, 0.3, -0.05), (-0.7, 0.3, 0.65), 0.035, "holz_alt", biegen=0.004)
        m.stab((0.7, 0.3, -0.05), (0.7, 0.3, 0.2), 0.035, "holz_alt", biegen=0.004)
        m.stab((0.75, 0.0, 0.035), (0.9, -0.42, 0.035), 0.035, "holz_alt", biegen=0.004)
    # Hackklotz mit Axt
    kx, ky = 0.2, -0.55
    m.teil(drehkoerper([(0.0, 0.0), (0.25, 0.0), (0.24, 0.42), (0.0, 0.44)], 16), "holz_alt", M((kx, ky, 0.0)), uv="zylz", r=0.25)
    m.teil(drehkoerper([(0.0, 0.0), (0.235, 0.0), (0.0, 0.004)], 16), "holz", M((kx, ky, 0.437)), uv=None)
    if not kaputt:
        # Axt steckt schräg im Klotz
        deko.axt(m, M((kx - 0.708, ky, 0.261), (0, 65, 0)), 0.75)
        scheit(m, M((kx - 0.4, ky - 0.15, 0.06), (0, 0, 40)), L, r)
        scheit(m, M((kx + 0.15, ky - 0.35, 0.06), (0, 0, -20)), L, r)
    else:
        # Klotz gespalten (Riss), Axt liegt am Boden
        m.teil(quader(0.4, 0.008, 0.2), "holz_verkohlt", M((kx, ky - 0.02, 0.36), (0, 0, 30)))
        deko.axt(m, M((kx - 0.6, ky - 0.2, 0.016), (90, 0, 70)) @ M((0, 0, -0.35)), 0.75)


# ======================================================================== Webstuhl

def webstuhl(m, kaputt):
    W = 1.2
    # vier Pfosten, Seitenholme oben und unten
    for sx in (-1, 1):
        x = sx * W / 2
        bein(m, (x, -0.55, 0.95), (x, -0.55, 0.0), 0.08)
        bein(m, (x, 0.55, 1.5), (x, 0.55, 0.0), 0.08)
        m.kantholz((x, -0.6, 0.9), (x, 0.6, 0.9), 0.06, 0.07)
        m.kantholz((x, -0.6, 0.12), (x, 0.6, 0.12), 0.06, 0.07)
        m.kantholz((x, 0.55, 1.45), (x, -0.05, 1.45), 0.06, 0.07)
        bein(m, (x, -0.05, 1.45), (x, -0.05, 0.9), 0.06)
    # Brustbaum vorn, Kettbaum hinten (Walzen), Querholz oben für die Schäfte
    m.stab((-W / 2 - 0.05, -0.55, 0.95), (W / 2 + 0.05, -0.55, 0.95), 0.04, "holz", biegen=0)
    m.stab((-W / 2 - 0.05, 0.55, 0.85), (W / 2 + 0.05, 0.55, 0.85), 0.06, "holz", biegen=0)
    m.kantholz((-W / 2, 0.15, 1.45), (W / 2, 0.15, 1.45), 0.06, 0.06)
    n = 36
    xs = [-0.45 + 0.9 * k / (n - 1) for k in range(n)]
    za, zb = 0.99, 0.91
    if not kaputt:
        # Kettfäden vom Kettbaum über die Schäfte zum Brustbaum
        for k, x in enumerate(xs):
            dz = 0.02 if k % 2 else -0.02
            m.teil(rohr([(x, 0.55, zb), (x, 0.15, 0.95 + dz), (x, -0.25, za)], 0.0016, 3, False), "seil", None, uv=None)
        # gewebtes Tuch vom Brustbaum bis zur Lade, Rolle auf dem Brustbaum
        tuch = [[(x, y, za + 0.002) for x in (-0.46, 0.0, 0.46)] for y in (-0.55, -0.4, -0.25)]
        m.teil(flaeche(tuch, 0.003), "wolle_rot", None)
        m.teil(rundholz(0.05, 0.94, 16), "wolle_rot", M((0, -0.55, 0.95)))
        # zwei Schäfte an Schnüren, Lade (Kamm) mit Armen
        for k, y in enumerate((0.1, 0.2)):
            m.teil(quader(1.0, 0.02, 0.02), "holz", M((0, y, 1.08)))
            m.teil(quader(1.0, 0.02, 0.02), "holz", M((0, y, 0.82)))
            for s in (-1, 1):
                m.seil([(s * 0.45, y, 1.09), (s * 0.45, y, 1.44)], 0.004)
        m.teil(quader(1.08, 0.04, 0.06), "holz", M((0, -0.2, 1.02)))
        m.teil(quader(1.08, 0.04, 0.03), "holz", M((0, -0.2, 0.9)))
        for s in (-1, 1):
            m.kantholz((s * 0.56, -0.2, 0.9), (s * 0.56, -0.05, 1.42), 0.03, 0.04)
        # Weberschiffchen auf dem Tuch, Tritte unten
        m.teil(quader(0.2, 0.035, 0.025, fase=0.01), "holz", M((0.15, -0.35, za + 0.016)))
        for s in (-1, 1):
            m.kantholz((s * 0.12, 0.4, 0.06), (s * 0.12, -0.45, 0.08), 0.08, 0.025)
    else:
        # Kette zerschnitten: die Fäden hängen hinten vom Kettbaum, das Tuch ist zerrissen und hängt vorn herunter
        for k, x in enumerate(xs):
            if k % 3 == 0:
                continue
            l = m.rnd.uniform(0.25, 0.6)
            m.teil(rohr([(x, 0.55, zb - 0.05), (x + m.rnd.uniform(-0.02, 0.02), 0.5, zb - 0.05 - l)], 0.0016, 3, False), "seil", None,
                   uv=None)
        g = []
        for i in range(9):
            t = i / 8
            g.append([(x, -0.55 - 0.06 * math.sin(t * 2), 0.95 - 0.6 * t + 0.02 * math.sin(x * 20 + t * 5)) for x in
                      (-0.46 + 0.92 * j / 10 for j in range(11))])
        loecher = {(5, 2), (6, 2), (6, 3), (7, 3), (7, 4), (4, 7), (5, 7), (8, 8), (8, 9), (7, 9), (3, 1)}
        m.teil(flaeche(g, 0.003, lambda i, j: (i, j) in loecher), "wolle_rot", None)
        m.teil(rundholz(0.05, 0.94, 16), "wolle_rot", M((0, -0.55, 0.95)))
        # ein Schaft ist heruntergefallen, die Lade lehnt schief
        m.teil(quader(1.0, 0.02, 0.02), "holz", M((0, 0.2, 1.08)))
        m.teil(quader(1.0, 0.02, 0.02), "holz", M((0, 0.2, 0.82)))
        for s in (-1, 1):
            m.seil([(s * 0.45, 0.2, 1.09), (s * 0.45, 0.2, 1.44)], 0.004)
        m.teil(quader(1.0, 0.02, 0.02), "holz", M((0.05, 0.1, 0.13), (0, 0, 6)))
        m.teil(quader(1.08, 0.04, 0.06), "holz", M((0.1, -0.9, 0.03), (0, 0, 10)))
        for s in (-1, 1):
            m.kantholz((s * 0.12, 0.4, 0.06), (s * 0.12, -0.45, 0.08), 0.08, 0.025)
    # Bank vor dem Webstuhl
    bank = M((0, -0.95, 0)) if not kaputt else M((0.1, -1.05, 0.0))
    if kaputt:
        m.umfallen_start()
    m.brett(0.9, 0.25, 0.04, bank @ M((0, 0, 0.47)), "holz")
    for s in (-1, 1):
        m.brett(0.04, 0.22, 0.45, bank @ M((s * 0.38, 0, 0.225)), "holz", biegen=0)
    if kaputt:
        m.umfallen_ende(-90)


# ======================================================================== Gerberrahmen

def gerberrahmen(m, kaputt):
    neig = math.radians(15)
    B, H = 1.5, 1.9
    hinten = Vector((0, math.sin(neig), math.cos(neig)))           # Richtung der Seitenstangen (nach hinten geneigt)

    def rp(u, v):                                                  # Punkt im Rahmen: u quer, v entlang der Stangen
        return Vector((u, 0, 0)) + hinten * v

    for s in (-1, 1):
        m.stab(tuple(rp(s * B / 2, -0.05)), tuple(rp(s * B / 2, H)), 0.035, "holz_alt", biegen=0.004)
        # Stütze nach hinten
        m.stab(tuple(rp(s * B / 2, H * 0.8)), (s * B / 2 * 1.05, 1.1, 0.0), 0.03, "holz_alt", biegen=0.004)
    for v in (0.3, H - 0.12):
        m.stab(tuple(rp(-B / 2 - 0.12, v)), tuple(rp(B / 2 + 0.12, v)), 0.03, "holz_alt", biegen=0.004)
        for s in (-1, 1):                                          # Bindungen an den Ecken
            ring = [tuple(rp(s * B / 2, v) + Vector((0.04 * math.cos(a), 0, 0)) + Vector((0, -0.04 * math.sin(a) * math.cos(neig),
                                                                                        0.04 * math.sin(a) * math.sin(neig) * 0))
                          + hinten * (0.012 * k / 8)) for k, a in enumerate(2 * math.pi * i / 8 for i in range(9))]
            m.seil(ring, 0.006)
    # Haut: Umriss mit vier Beinlappen und Hals
    mitte_v = (0.3 + H - 0.12) / 2
    nr, na = 6, 48

    def umriss(a):
        return 0.52 * (1 + 0.16 * math.cos(4 * a + 0.6) + 0.06 * math.sin(7 * a)), 0.66 * (1 + 0.12 * math.cos(4 * a + 0.6))

    g = []
    for i in range(nr + 1):
        u = i / nr
        zeile = []
        for j in range(na + 1):
            a = 2 * math.pi * j / na
            rx, ry = umriss(a)
            x = rx * u * math.cos(a); v = mitte_v + ry * u * math.sin(a)
            if not kaputt:
                p = rp(x, v) + Vector((0, -0.01 * (1 - u * u), 0))
            else:
                # aus den unteren Schnüren gerissen: hängt von oben senkrecht herab und wellt sich
                oben = mitte_v + 0.66
                p0 = rp(x, oben)
                p = p0 + Vector((0, -0.03 * math.sin(x * 9) - 0.02, -(oben - v)))
            zeile.append(tuple(p))
        g.append(zeile)
    loch = None
    if kaputt:
        loch = lambda i, j: (i in (3, 4) and j in (10, 11, 12)) or (i in (4, 5) and j in (30, 31))
    m.teil(flaeche(g, 0.006, loch), "haut", None)
    # Schnürung vom Hautrand zum Rahmen
    for j in range(0, na, 4):
        a = 2 * math.pi * j / na
        rx, ry = umriss(a)
        x = rx * math.cos(a); v = mitte_v + ry * math.sin(a)
        if kaputt and v < mitte_v + 0.4:
            continue
        rand = Vector(g[nr][j])
        if abs(math.cos(a)) * B / 2 / max(rx, 1e-3) > abs(math.sin(a)) * ((H - 0.12 - 0.3) / 2) / max(ry, 1e-3):
            ziel = rp(math.copysign(B / 2, x), v)
        else:
            ziel = rp(x, 0.3 if v < mitte_v else H - 0.12)
        m.seil([tuple(rand), tuple(ziel)], 0.004)
    # Gerbbottich und Schaber
    bottich = [(0.0, 0.0), (0.3, 0.0), (0.33, 0.45), (0.31, 0.45), (0.28, 0.03), (0.0, 0.03)]
    if not kaputt:
        m.teil(drehkoerper(bottich, 20, False, False), "holz", M((0.9, -0.5, 0.0)), uv="zylz", r=0.33)
        m.teil(drehkoerper([(0.0, 0.38), (0.32, 0.38), (0.0, 0.381)], 20), "faul", M((0.9, -0.5, 0.0)), uv=None)
        m.stab((-0.6, -0.45, 0.015), (-0.3, -0.5, 0.015), 0.015, "holz", biegen=0)
        m.teil(quader(0.03, 0.18, 0.006), "eisen", M((-0.29, -0.5, 0.004), (0, 0, -10)))
    else:
        m.umfallen_start()
        m.teil(drehkoerper(bottich, 20, False, False), "holz", M((0.9, -0.5, 0.0)), uv="zylz", r=0.33)
        m.umfallen_ende(-70)
        haufen(m, (1.05, -1.1), 0.3, 0.22, 0.004, "faul", m.rnd)


# ======================================================================== Wassertrog

def wassertrog(m, kaputt):
    L, B, H = 1.6, 0.55, 0.42
    for s in (-1, 1):
        m.kantholz((s * 0.55, -B / 2 - 0.08, 0.04), (s * 0.55, B / 2 + 0.08, 0.04), 0.1, 0.08)
    zb = 0.08
    # Boden, Seiten, Stirnbretter
    m.brett(L, B, 0.04, M((0, 0, zb + 0.02)), "holz")
    for s in (-1, 1):
        y = s * (B / 2 - 0.02)
        for k in range(3):
            z = zb + 0.04 + 0.11 * k + 0.055
            if kaputt and s == -1 and k == 2:
                m.brett(0.7, 0.11, 0.04, M((-0.42, y, z), (90, 0, 0)), "holz", bruch=1)
                continue
            m.brett(L - 0.08, 0.11, 0.04, M((0, y, z), (90, 0, 0)), "holz", biegen=0.002)
    for s in (-1, 1):
        m.brett(0.04, B, H - 0.04, M((s * (L / 2 - 0.02), 0, zb + 0.04 + (H - 0.04) / 2 - 0.02)), "holz", biegen=0)
    # Eisenbänder um den Trog
    for x in (-0.5, 0.5):
        band = [(x, -B / 2 - 0.004, zb + 0.02), (x, -B / 2 - 0.004, zb + H - 0.03), (x, B / 2 + 0.004, zb + H - 0.03),
                (x, B / 2 + 0.004, zb + 0.02)]
        if kaputt and x > 0:
            band = band[:2] + [(x + 0.02, -B / 2 - 0.06, zb + H - 0.12)]
        m.seil(band, 0.006, 4, "eisen")
    if not kaputt:
        wasserflaeche(m, M((0, 0, zb + H - 0.1)), L - 0.08, B - 0.08)
        return
    # ausgelaufen: nur eine Pfütze am Grund, eine größere vor dem Trog, das Stück Brett liegt darin
    wasserflaeche(m, M((0.2, 0.0, zb + 0.042)), 0.5, 0.3)
    haufen(m, (0.3, -0.75), 0.5, 0.25, 0.003, "wasser", m.rnd, rand_rauh=0.35)
    m.brett(0.6, 0.11, 0.04, M((0.5, -0.65, 0.02), (0, 0, 15)), "holz", bruch=-1)


MODELLE = {"schleifstein": schleifstein, "werkbank": werkbank, "holzstapel": holzstapel, "webstuhl": webstuhl,
           "gerberrahmen": gerberrahmen, "wassertrog": wassertrog}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
