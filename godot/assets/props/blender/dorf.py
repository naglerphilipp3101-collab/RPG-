"""Dorf- und Straßen-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python dorf.py -- <zielordner/modelle> [--nur marktstand,pranger] [--vorschau <ordner>]

  marktstand       Verkaufsstand mit Theke, Stoffplane, Körben und Kisten
  wegweiser        Pfahl mit drei Richtungsbrettern
  pranger          Pranger auf einem Bretterpodest (Kopf- und Handlöcher)
  brennholzstapel  Rundhölzer zur Pyramide gestapelt, mit Keilen gesichert
  heuballen        drei verschnürte Heuballen
  schubkarre       hölzerne Schubkarre mit Speichenrad
  huehnerkaefig    Lattenkäfig mit Tür und Stroh
  futtertrog       Futterkrippe auf Beinen mit Körnern
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, verbiegen, ausrichten
import props
from props import rad
from behaelter import sack, korb, apfel
from kueche import haufen, ellipsoid, kohl, zwiebel, moehre


# ======================================================================== Hilfen

def pfosten(m, unten, oben, b=0.09, mat="holz", bruch=0):
    m.kantholz(unten, oben, b, b, mat, bruch=bruch)


def tuch(m, ecken, nx, ny, durchhang, rnd, mat="wolle_rot", loch=None, dicke=0.004, falten=0.0):
    """Gespanntes Tuch zwischen vier Eckpunkten (v0 vorn links, v1 vorn rechts, v2 hinten rechts, v3 hinten links), hängt in der Mitte durch."""
    v0, v1, v2, v3 = [Vector(e) for e in ecken]
    g = []
    for i in range(ny + 1):
        t = i / ny
        zeile = []
        for j in range(nx + 1):
            s = j / nx
            p = v0.lerp(v1, s).lerp(v3.lerp(v2, s), t)
            p.z -= durchhang * math.sin(math.pi * s) * math.sin(math.pi * t) + falten * math.sin(s * 25) * math.sin(math.pi * t)
            zeile.append(tuple(p))
        g.append(zeile)
    bm = flaeche(g, dicke, loch)
    m.teil(bm, mat, None)


def kiste_klein(m, matrix, b=0.4, t=0.3, h=0.25, leer=False):
    for s in (-1, 1):
        m.brett(b, 0.02, h, matrix @ M((0, s * (t / 2 - 0.01), h / 2)), "holz", biegen=0)
        m.brett(0.02, t - 0.04, h, matrix @ M((s * (b / 2 - 0.01), 0, h / 2)), "holz", biegen=0)
    m.brett(b, t, 0.02, matrix @ M((0, 0, 0.01)), "holz", biegen=0)


# ======================================================================== Marktstand

def marktstand(m, kaputt):
    W, T = 2.2, 1.2
    hv, hh = 2.1, 1.75                               # Plane vorn höher, hinten tiefer
    ecken = [(-W / 2, -T / 2), (W / 2, -T / 2), (W / 2, T / 2), (-W / 2, T / 2)]
    for k, (x, y) in enumerate(ecken):
        h = hv if y < 0 else hh
        if kaputt and k == 1:
            # rechter vorderer Pfosten abgebrochen, der Stumpf steht noch, der Rest liegt vor dem Stand
            pfosten(m, (x, y, 0), (x, y, 0.6), bruch=1)
            m.kantholz((x + 0.2, y - 0.4, 0.045), (x + 0.2 - 1.3, y - 0.4 - 0.4, 0.045), 0.09, 0.09, "holz", bruch=-1)
            continue
        pfosten(m, (x, y, 0), (x, y, h + 0.05))
    # Theke vorn und Ablage hinten
    for z, y0, tiefe in ((0.9, -T / 2 + 0.28, 0.5), (0.7, T / 2 - 0.2, 0.35)):
        if kaputt and z == 0.9:
            m.brett(1.1, tiefe, 0.04, M((-0.55, y0, z)), "holz", bruch=1)
        else:
            m.brett(W - 0.1, tiefe, 0.04, M((0, y0, z)), "holz")
        for s in (-1, 1):
            if kaputt and z == 0.9 and s == 1:
                continue
            m.kantholz((s * (W / 2 - 0.06), y0 - tiefe / 2 + 0.03, z - 0.03), (s * (W / 2 - 0.06), y0 + tiefe / 2 - 0.03, z - 0.03), 0.05, 0.05)
    m.brett(W - 0.1, 0.03, 0.6, M((0, -T / 2 + 0.05, 0.58)), "holz", biegen=0.002) if not kaputt else \
        m.brett(1.0, 0.03, 0.6, M((-0.55, -T / 2 + 0.05, 0.3), (90, 0, 0)) @ M(rot=(-90, 0, 0)), "holz", bruch=1)
    # Rahmen oben und Plane
    v = [(-W / 2 - 0.1, -T / 2 - 0.2, hv), (W / 2 + 0.1, -T / 2 - 0.2, hv), (W / 2 + 0.1, T / 2 + 0.05, hh), (-W / 2 - 0.1, T / 2 + 0.05, hh)]
    if not kaputt:
        m.kantholz((-W / 2 - 0.05, -T / 2, hv + 0.02), (W / 2 + 0.05, -T / 2, hv + 0.02), 0.06, 0.06)
        m.kantholz((-W / 2 - 0.05, T / 2, hh + 0.02), (W / 2 + 0.05, T / 2, hh + 0.02), 0.06, 0.06)
        vz = [(x, y, z + 0.055) for x, y, z in v]
        tuch(m, vz, 16, 10, 0.08, m.rnd, "wolle_rot")
        # Volant vorn
        g = [[(x, -T / 2 - 0.2 + 0.005 * math.sin(x * 30), hv + 0.05 - 0.22 * t) for x in (-W / 2 - 0.1 + (W + 0.2) * j / 16 for j in range(17))]
             for t in (0.0, 0.5, 1.0)]
        m.teil(flaeche(g, 0.004), "farbe_weiss", None)
        # Ware: Äpfel im Korb, Gemüse, Kisten, Säcke
        korb(m, M((-0.65, -0.35, 0.92)), 0.13, 0.17, 0.14, henkel=False)
        for k in range(9):
            a = 2 * math.pi * k / 9
            apfel(m, M((-0.65 + 0.08 * math.cos(a), -0.35 + 0.08 * math.sin(a), 0.92 + 0.13)))
        apfel(m, M((-0.65, -0.35, 0.92 + 0.17)))
        korb(m, M((0.05, -0.33, 0.92)), 0.13, 0.17, 0.14, henkel=False)
        for k, (dx, dy) in enumerate([(-0.05, 0.02), (0.06, -0.03), (0.0, 0.07), (0.05, 0.06)]):
            zwiebel(m, M((0.05 + dx, -0.33 + dy, 0.92 + 0.11)))
        kohl(m, M((0.62, -0.32, 0.92 + 0.07)), 0.07)
        kohl(m, M((0.78, -0.4, 0.92 + 0.065)), 0.065)
        kiste_klein(m, M((-0.5, T / 2 - 0.2, 0.72)))
        kiste_klein(m, M((0.4, T / 2 - 0.2, 0.72), (0, 0, 4)))
        sack(m, M((-0.75, 0.05, 0.0)), 0.5, 0.18)
        sack(m, M((0.8, 0.1, 0.0)), 0.45, 0.17)
        return
    # verlassen: Plane hängt vorn rechts herunter und ist zerrissen, Ware weg, Kisten umgekippt
    m.kantholz((-W / 2 - 0.05, T / 2, hh + 0.02), (W / 2 + 0.05, T / 2, hh + 0.02), 0.06, 0.06)
    m.kantholz((-W / 2 - 0.05, -T / 2, hv + 0.02), (W / 2 - 0.2, -T / 2 - 0.5, 0.05), 0.06, 0.06)
    hang = [(-W / 2 - 0.1, -T / 2 - 0.2, hv + 0.055), (W / 2 - 0.3, -T / 2 - 0.7, 0.02), (W / 2 + 0.1, T / 2 + 0.05, hh + 0.055),
            (-W / 2 - 0.1, T / 2 + 0.05, hh + 0.055)]
    loecher = {(3, 5), (3, 6), (4, 6), (4, 7), (6, 11), (7, 11), (7, 12), (2, 13), (5, 2)}
    tuch(m, hang, 16, 10, 0.25, m.rnd, "wolle_rot", loch=lambda i, j: (i, j) in loecher, falten=0.03)
    m.umfallen_start()
    kiste_klein(m, M((0.5, -0.9, 0.0), (0, 0, 20)))
    m.umfallen_ende(-80)
    kiste_klein(m, M((-0.5, T / 2 - 0.2, 0.72)))
    sack(m, M((-0.75, 0.05, 0.0)), 0.5, 0.18, leer=True)
    for k in range(3):
        apfel(m, M((m.rnd.uniform(-0.6, 0.6), m.rnd.uniform(-1.1, -0.7), 0.033), (0, 70, m.rnd.uniform(0, 360))))


# ======================================================================== Wegweiser

def schild(m, matrix, L=0.6, b=0.13, d=0.025, bruch=0):
    """Pfeilbrett entlang +x (Spitze bei x = L), Ursprung am Pfahl."""
    bm = bmesh.new()
    pts = [(0.0, -b / 2), (L - 0.1, -b / 2), (L, 0.0), (L - 0.1, b / 2), (0.0, b / 2)]
    if bruch:
        pts = [(0.0, -b / 2), (L * 0.55, -b / 2), (L * 0.5, -b * 0.1), (L * 0.6, b * 0.2), (L * 0.52, b / 2), (0.0, b / 2)]
    vo = [bm.verts.new((x, -d / 2, y)) for x, y in pts]
    hi = [bm.verts.new((x, d / 2, y)) for x, y in pts]
    bm.faces.new(vo); bm.faces.new(list(reversed(hi)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((vo[i], vo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    verbiegen(bm, m.rnd, 0.003, 0.2)
    m.teil(bm, "holz_alt", matrix)
    # eingebrannte Schriftzeile (dunkle Striche)
    for k in range(3 if not bruch else 1):
        x = 0.1 + 0.12 * k
        m.teil(quader(0.09, 0.002, 0.03), "holz_verkohlt", matrix @ M((x, -d / 2 - 0.001, 0.0)))


def wegweiser(m, kaputt):
    H = 2.3
    if not kaputt:
        m.stab((0, 0, -0.1), (0, 0, H), 0.07, "holz_alt", biegen=0.005)
        m.teil(drehkoerper([(0.0, 0.0), (0.08, 0.0), (0.0, 0.08)], 8), "holz_alt", M((0, 0, H)))
        for z, rz in ((H - 0.2, 20), (H - 0.42, 150), (H - 0.64, -70)):
            schild(m, M((0, 0, z), (0, 0, rz)) @ M((0.06, 0, 0)))
            m.teil(drehkoerper([(0.0, 0.0), (0.008, 0.0), (0.0, 0.004)], 6), "eisen",
                   M((0, 0, z), (0, 0, rz)) @ M((0.1, -0.015, 0), (90, 0, 0)))
        # Steine um den Fuß
        for k in range(7):
            a = 2 * math.pi * k / 7
            g = m.rnd.uniform(0.07, 0.11)
            m.teil(brocken(m.rnd, g, g * 0.85, g * 0.6, 0.2, 1), "stein", M((0.16 * math.cos(a), 0.16 * math.sin(a), g * 0.35)))
        return
    # Pfahl schief (vom Fuß aus gekippt), ein Schild hängt an einem Nagel, eins liegt am Boden, eins abgebrochen
    for k in range(7):
        a = 2 * math.pi * k / 7
        g = m.rnd.uniform(0.07, 0.11)
        m.teil(brocken(m.rnd, g, g * 0.85, g * 0.6, 0.2, 1), "stein", M((0.16 * math.cos(a) + (0.25 if k == 2 else 0),
                                                                          0.16 * math.sin(a) - (0.2 if k == 2 else 0), g * 0.35)))
    neig = M(rot=(14, 6, 0))
    oben = neig @ Vector((0, 0, H))
    m.stab((0, 0, -0.1), tuple(oben), 0.07, "holz_alt", biegen=0.005)
    m.teil(drehkoerper([(0.0, 0.0), (0.08, 0.0), (0.0, 0.08)], 8), "holz_alt", neig @ M((0, 0, H)))
    schild(m, neig @ M((0, 0, H - 0.2), (0, 0, 20)) @ M((0.06, 0, 0)), bruch=1)
    # hängt am Nagel: um den Nagel nach unten gedreht
    nagel = neig @ M((0, 0, H - 0.42), (0, 0, 150)) @ M((0.1, 0, 0))
    schild(m, nagel @ M(rot=(0, 75, 0)) @ M((-0.04, -0.03, 0)))
    schild(m, M((0.4, -0.7, 0.0125), (90, 0, -30)) @ M(rot=(-90, 0, 0)))


# ======================================================================== Pranger

def pranger(m, kaputt):
    # Podest aus Brettern auf Kanthölzern, zwei Stufen
    for s in (-1, 1):
        m.kantholz((s * 0.7, -0.75, 0.06), (s * 0.7, 0.75, 0.06), 0.12, 0.12)
    m.kantholz((0, -0.75, 0.06), (0, 0.75, 0.06), 0.12, 0.12)
    for k in range(8):
        y = -0.7 + 0.2 * k
        if kaputt and k in (2, 3):
            m.brett(0.6, 0.19, 0.04, M((-0.45, y, 0.14)), "holz_alt", bruch=1)
            continue
        m.brett(1.6, 0.19, 0.04, M((0, y, 0.14)), "holz_alt")
    m.brett(0.8, 0.25, 0.04, M((0, -0.95, 0.08)), "holz_alt")
    for s in (-1, 1):
        m.brett(0.06, 0.25, 0.08, M((s * 0.35, -0.95, 0.04)), "holz_alt", biegen=0)
    # zwei Pfosten, unteres und oberes Joch mit drei Löchern
    z0 = 0.16
    for s in (-1, 1):
        pfosten(m, (s * 0.5, 0.2, z0), (s * 0.5, 0.2, z0 + 1.75), 0.12, "holz_alt")
    jz = z0 + 1.35

    def joch(matrix, oben):
        bm = quader(1.12, 0.1, 0.16, 12, 1, 2)
        weg = []
        for f in bm.faces:
            c = f.calc_center_median()
            for x, r in ((-0.33, 0.055), (0.0, 0.1), (0.33, 0.055)):
                if math.hypot(c.x - x, c.z + (0.08 if oben else -0.08)) < r and abs(c.y) < 0.04:
                    weg.append(f)
        m.teil(bm, "holz_alt", matrix)
        # Halbkreis-Aussparungen als dunkle Einlage
        for x, r in ((-0.33, 0.055), (0.0, 0.1), (0.33, 0.055)):
            halb = drehkoerper([(0.0, -0.052), (r, -0.052), (r, 0.052), (0.0, 0.052)], 12, winkel=(0, 180) if oben else (180, 360))
            m.teil(halb, "holz_verkohlt", matrix @ M((x, 0, -0.08 if oben else 0.08), (90, 0, 0)), uv=None)

    joch(M((0, 0.2, jz - 0.08)), False)
    if not kaputt:
        joch(M((0, 0.2, jz + 0.08)), True)
        m.teil(quader(1.2, 0.12, 0.08), "holz_alt", M((0, 0.2, z0 + 1.75)))
        # Scharnier und Riegel
        m.teil(quader(0.04, 0.11, 0.2), "eisen", M((-0.5, 0.2 - 0.0, jz), (0, 0, 0)))
        m.stab((0.48, 0.13, jz + 0.04), (0.48, 0.13, jz - 0.06), 0.012, "eisen", biegen=0)
        return
    # oberes Joch herausgerissen und vorn auf dem Podest, Querholz fehlt
    m.umfallen_start()
    joch(M((0.1, -0.45, 0.16 + 0.08)), True)
    m.umfallen_ende(-90)
    for k in range(4):
        g = m.rnd.uniform(0.02, 0.04)
        m.teil(brocken(m.rnd, g * 2, g, g * 0.4, 0.3, 1), "holz_alt", M((m.rnd.uniform(-0.6, 0.6), m.rnd.uniform(-0.6, 0.0), 0.165)))


# ======================================================================== Brennholzstapel

def brennholzstapel(m, kaputt):
    L, r = 1.5, 0.085
    if not kaputt:
        reihen = [5, 4, 3, 2, 1]
        for i, n in enumerate(reihen):
            z = r + i * r * 1.732
            for k in range(n):
                y = (k - (n - 1) / 2) * 2 * r
                bm = rundholz(r * m.rnd.uniform(0.9, 1.05), L + m.rnd.uniform(-0.1, 0.1), 12, 3)
                verbiegen(bm, m.rnd, 0.01, 0.5)
                m.teil(bm, "holz_alt", M((m.rnd.uniform(-0.05, 0.05), y, z)), uv="zyl", r=r)
                for s in (-1, 1):                    # Hirnholz an den Enden
                    m.teil(drehkoerper([(0.0, 0.0), (r * 0.9, 0.0), (0.0, 0.001)], 10), "holz",
                           M((s * (L / 2 + 0.06) + 0, y, z), (0, s * 90, 0)), uv=None) if False else None
        # Keile und Pflöcke halten die untere Reihe
        for s in (-1, 1):
            for x in (-0.5, 0.5):
                m.teil(quader(0.12, 0.06, 0.08), "holz", M((x, s * 5 * r + s * 0.02, 0.04), (0, 0, 0)))
            m.stab((s * 0.6, -5 * r - 0.05, -0.1), (s * 0.6, -5 * r - 0.05, 0.4), 0.03, "holz", biegen=0)
        return
    # Pflock gebrochen: die Stämme sind auseinandergerollt
    m.stab((0.6, -5 * r - 0.05, -0.1), (0.6, -5 * r - 0.05, 0.4), 0.03, "holz", biegen=0)
    m.stab((-0.6, -5 * r - 0.05, -0.1), (-0.6, -5 * r - 0.05, 0.08), 0.03, "holz", biegen=0)
    m.stab((-0.55, -5 * r - 0.1, 0.03), (-0.6, -5 * r - 0.4, 0.03), 0.03, "holz", biegen=0)
    ys = [0.3, 0.13, -0.04, -0.21, -0.45, -0.68, -0.92, -1.2]
    for k, y in enumerate(ys):
        bm = rundholz(r, L + m.rnd.uniform(-0.1, 0.1), 12, 3)
        verbiegen(bm, m.rnd, 0.01, 0.5)
        m.teil(bm, "holz_alt", M((m.rnd.uniform(-0.1, 0.1), y, r), (0, 0, m.rnd.uniform(-12, 12) if k > 3 else 0)), uv="zyl", r=r)
    for k, y in enumerate([0.215, 0.045, -0.125]):
        bm = rundholz(r, L, 12, 3)
        m.teil(bm, "holz_alt", M((0.0, y, r + r * 1.732)), uv="zyl", r=r)
    bm = rundholz(r, L, 12, 3)
    m.teil(bm, "holz_alt", M((0.0, 0.13, r + 2 * r * 1.732)), uv="zyl", r=r)


# ======================================================================== Heuballen

def ballen(m, matrix, lx=0.9, ly=0.45, lz=0.4, offen=False):
    bm = quader(lx, ly, lz, 6, 4, 4, fase=0.05)
    verbiegen(bm, m.rnd, 0.02, 0.15)
    verbiegen(bm, m.rnd, 0.008, 0.04)
    m.teil(bm, "stroh", matrix @ M((0, 0, lz / 2)))
    for x in (-lx / 4, lx / 4):
        if offen and x > 0:
            m.seil([tuple(matrix @ Vector((x, -ly / 2 - 0.008, 0.02))), tuple(matrix @ Vector((x, -ly / 2 - 0.008, lz * 0.6))),
                    tuple(matrix @ Vector((x + 0.1, -ly / 2 - 0.15, 0.01)))], 0.006)
            continue
        ring = [(x, -ly / 2 - 0.006, 0.005), (x, -ly / 2 - 0.006, lz + 0.006), (x, ly / 2 + 0.006, lz + 0.006), (x, ly / 2 + 0.006, 0.005)]
        m.seil([tuple(matrix @ Vector(p)) for p in ring], 0.006)


def heuballen(m, kaputt):
    if not kaputt:
        ballen(m, M((-0.48, 0.0, 0.0), (0, 0, 2)))
        ballen(m, M((0.48, 0.02, 0.0), (0, 0, -3)))
        ballen(m, M((0.0, 0.05, 0.4), (0, 0, 5)))
        return
    # oberer Ballen heruntergefallen und aufgeplatzt, das Heu liegt verstreut
    ballen(m, M((-0.48, 0.0, 0.0), (0, 0, 2)))
    ballen(m, M((0.48, 0.02, 0.0), (0, 0, -3)), lz=0.3, offen=True)
    haufen(m, (0.2, -0.65), 0.6, 0.4, 0.16, "stroh", m.rnd, rand_rauh=0.35)
    haufen(m, (0.9, -0.3), 0.35, 0.3, 0.07, "stroh", m.rnd, rand_rauh=0.4)
    for k in range(25):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.5, 1.1)
        p = Vector((0.2 + d * math.cos(a), -0.4 + d * 0.7 * math.sin(a), 0.004))
        m.stab(tuple(p), tuple(p + Vector((m.rnd.uniform(-0.12, 0.12), m.rnd.uniform(-0.12, 0.12), 0.0))), 0.003, "stroh", seg=3,
               biegen=0)


# ======================================================================== Schubkarre

def schubkarre(m, kaputt):
    if kaputt:
        m.umfallen_start()
    r = 0.22
    # Holme: vom Rad bis zu den Griffen
    for s in (-1, 1):
        m.kantholz((s * 0.06, -0.62, r), (s * 0.3, 0.78, 0.62), 0.05, 0.06)
        # Beine
        m.kantholz((s * 0.25, 0.42, 0.52), (s * 0.27, 0.48, 0.0), 0.045, 0.045)
    # Kasten mit schrägen Wänden
    boden = M((0, 0.05, 0.42), (-8, 0, 0))
    m.brett(0.5, 0.75, 0.025, boden, "holz")
    for s in (-1, 1):
        m.brett(0.8, 0.22, 0.025, boden @ M((s * 0.3, 0, 0.1), (s * 20, 0, 90)) @ M(rot=(90, 0, 0)), "holz")
    m.brett(0.62, 0.025, 0.24, boden @ M((0, 0.39, 0.1), (-15, 0, 0)), "holz")
    m.brett(0.55, 0.025, 0.24, boden @ M((0, -0.4, 0.11), (25, 0, 0)), "holz")
    # Griffe
    for s in (-1, 1):
        m.stab((s * 0.3, 0.78, 0.62), (s * 0.32, 0.95, 0.66), 0.022, "holz", biegen=0)
    if not kaputt:
        rad(m, (0, -0.62, r), r, 0.05, (1, 0, 0), 8)
        m.stab((-0.09, -0.62, r), (0.09, -0.62, r), 0.012, "eisen", biegen=0)
        # etwas Erde im Kasten
        m.teil(drehkoerper([(0.0, 0.0), (0.22, 0.0), (0.0, 0.08)], 12), "erde", boden @ M((0, 0, 0.012), skal=(1, 1.4, 1)))
        return
    m.stab((-0.09, -0.62, r), (0.09, -0.62, r), 0.012, "eisen", biegen=0)
    m.umfallen_ende(0)
    # Rad abgebrochen, liegt daneben
    rad(m, (-0.6, -0.5, 0.03), r, 0.05, (0, 0, 1), 8, kaputt=True)
    haufen(m, (0.6, 0.3), 0.3, 0.25, 0.05, "erde", m.rnd)


# ======================================================================== Hühnerkäfig

def huehnerkaefig(m, kaputt):
    B, T, H = 0.9, 0.6, 0.55
    # Kufen, Boden, Eckpfosten, Rahmen
    for s in (-1, 1):
        m.kantholz((s * (B / 2 - 0.04), -T / 2, 0.025), (s * (B / 2 - 0.04), T / 2, 0.025), 0.05, 0.05)
    m.brett(B, T, 0.02, M((0, 0, 0.06)), "holz")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.kantholz((sx * (B / 2 - 0.02), sy * (T / 2 - 0.02), 0.07), (sx * (B / 2 - 0.02), sy * (T / 2 - 0.02), H), 0.04, 0.04)
    for z in (0.09, H - 0.02):
        for sy in (-1, 1):
            m.kantholz((-B / 2, sy * (T / 2 - 0.02), z), (B / 2, sy * (T / 2 - 0.02), z), 0.035, 0.035)
        for sx in (-1, 1):
            m.kantholz((sx * (B / 2 - 0.02), -T / 2, z), (sx * (B / 2 - 0.02), T / 2, z), 0.035, 0.035)
    m.brett(B + 0.06, T + 0.06, 0.02, M((0, 0, H + 0.01)), "holz")
    # senkrechte Latten an allen Seiten, vorn mit Tür
    zl0, zl1 = 0.1, H - 0.04
    for sy in (-1, 1):
        for k in range(9):
            x = -B / 2 + 0.1 * (k + 0.5)
            if sy == -1 and 3 <= k <= 5:
                continue                             # Türöffnung
            if kaputt and sy == -1 and k in (6, 7):
                m.stab((x, sy * (T / 2 - 0.02), zl0), (x, sy * (T / 2 - 0.02), zl0 + 0.15), 0.008, "holz", biegen=0)
                continue
            m.stab((x, sy * (T / 2 - 0.02), zl0), (x, sy * (T / 2 - 0.02), zl1), 0.008, "holz", biegen=0)
    for sx in (-1, 1):
        for k in range(5):
            y = -T / 2 + 0.1 * (k + 1)
            m.stab((sx * (B / 2 - 0.02), y, zl0), (sx * (B / 2 - 0.02), y, zl1), 0.008, "holz", biegen=0)
    # Stroh innen
    haufen(m, (0.0, 0.05), 0.38, 0.24, 0.05, "stroh", m.rnd) if False else None
    m.teil(drehkoerper([(0.0, 0.0), (0.36, 0.0), (0.32, 0.03), (0.0, 0.05)], 16), "stroh", M((0, 0, 0.07), skal=(1, 0.65, 1)))
    tuer = M((-0.15, -T / 2 - 0.02, 0.1))
    if not kaputt:
        for k in range(4):
            m.stab(tuple(tuer @ Vector((0.03 + 0.08 * k, 0, 0.02))), tuple(tuer @ Vector((0.03 + 0.08 * k, 0, 0.38))), 0.008, "holz", biegen=0)
        for z in (0.03, 0.37):
            m.brett(0.29, 0.02, 0.03, tuer @ M((0.15, -0.012, z)), "holz", biegen=0)
        m.teil(quader(0.015, 0.03, 0.06), "eisen", tuer @ M((0.3, -0.02, 0.2)))
        return
    # Tür herausgerissen und davor im Gras, Federn verstreut
    tuer_boden = M((-0.3, -0.75, 0.025), (90, 0, 15)) @ M(rot=(-90, 0, 0))
    for k in range(4):
        m.stab(tuple(tuer_boden @ Vector((0.03 + 0.08 * k, 0.03, 0.0))), tuple(tuer_boden @ Vector((0.03 + 0.08 * k, 0.38, 0.0))), 0.008,
               "holz", biegen=0)
    for y in (0.03, 0.37):
        m.brett(0.29, 0.03, 0.02, tuer_boden @ M((0.15, y, 0.015)), "holz", biegen=0)
    for k in range(18):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.1, 0.8)
        p = (d * math.cos(a), -0.5 + d * 0.6 * math.sin(a), 0.004) if k < 12 else (m.rnd.uniform(-0.3, 0.3), m.rnd.uniform(-0.2, 0.2), 0.115)
        m.teil(ellipsoid(0.025, 0.007, 0.0015, 1), "farbe_weiss" if k % 3 else "holz", M(p, (0, 0, m.rnd.uniform(0, 360))))


# ======================================================================== Futtertrog

def futtertrog(m, kaputt):
    L = 1.5
    if kaputt:
        # linkes Beinpaar weggebrochen: die Krippe liegt links auf dem Boden, rechts auf den Füßen
        drehpunkt = Vector((L / 2 - 0.1, 0, 0))
        w = math.atan2(0.46, L - 0.1 - 0.0)
        m.G = Matrix.Translation(drehpunkt) @ Matrix.Rotation(-w, 4, Vector((0, 1, 0))) @ Matrix.Translation(-drehpunkt)
    # V-förmige Krippe aus zwei Brettern, Stirnbretter, gekreuzte Beine
    for s in (-1, 1):
        m.brett(L, 0.24, 0.03, M((0, s * 0.09, 0.55), (s * 40, 0, 0)), "holz")
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.015)
        bm = bmesh.new()
        pts = [(-0.2, 0.68), (0.0, 0.46), (0.2, 0.68)]
        vo = [bm.verts.new((x - 0.015, y, z)) for y, z in pts]
        hi = [bm.verts.new((x + 0.015, y, z)) for y, z in pts]
        bm.faces.new(vo); bm.faces.new(list(reversed(hi)))
        for i in range(3):
            j = (i + 1) % 3
            bm.faces.new((vo[i], vo[j], hi[j], hi[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        m.teil(bm, "holz", None)
        for sy in (-1, 1):
            if kaputt and sx == -1:
                m.kantholz((sx * (L / 2 - 0.1), sy * 0.12, 0.62), (sx * (L / 2 - 0.1), -sy * 0.03, 0.42), 0.05, 0.05, bruch=-1)
                continue
            m.kantholz((sx * (L / 2 - 0.1), sy * 0.12, 0.62), (sx * (L / 2 - 0.1), -sy * 0.25, 0.0), 0.05, 0.05)
    if not kaputt:
        m.kantholz((-L / 2 + 0.1, 0, 0.12), (L / 2 - 0.1, 0, 0.12), 0.05, 0.05)
    if not kaputt:
        # Körner und Heu in der Krippe
        g = [[(x, y, 0.6 + 0.02 * math.sin(x * 9) * math.cos(y * 20)) for x in (-L / 2 + 0.04 + (L - 0.08) * j / 12 for j in range(13))]
             for y in (-0.1, -0.05, 0.0, 0.05, 0.1)]
        m.teil(flaeche(g, 0.0), "stroh", None)
        return
    m.G = None
    # abgebrochene Beine und Querholz liegen am Boden, das Futter ist links herausgerutscht
    m.kantholz((-0.95, -0.35, 0.025), (-0.5, -0.6, 0.025), 0.05, 0.05, bruch=1)
    m.kantholz((-0.4, 0.45, 0.025), (0.05, 0.6, 0.025), 0.05, 0.05, bruch=-1)
    m.kantholz((-0.2, -0.45, 0.025), (0.8, -0.5, 0.025), 0.05, 0.05, bruch=1)
    haufen(m, (-1.0, 0.0), 0.3, 0.35, 0.06, "stroh", m.rnd, rand_rauh=0.4)


MODELLE = {"marktstand": marktstand, "wegweiser": wegweiser, "pranger": pranger, "brennholzstapel": brennholzstapel,
           "heuballen": heuballen, "schubkarre": schubkarre, "huehnerkaefig": huehnerkaefig, "futtertrog": futtertrog}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
