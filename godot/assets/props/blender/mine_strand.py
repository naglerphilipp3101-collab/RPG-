"""Mine- und Strand-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python mine_strand.py -- <zielordner/modelle> [--nur stuetzbalken,ruderboot] [--vorschau <ordner>]

  stuetzbalken      Türstock im Stollen: zwei Stempel, Kappe, Keile und Verzugbretter (2,4 m breit, 2,5 m hoch)
  schienen          2 m Grubengleis auf Schwellen (Spur 0,6 m)
  erzhaufen         Haufen aus Erzbrocken mit Schaufel
  spitzhacke_fels   Felsbrocken, in dem eine Spitzhacke steckt
  ruderboot         Ruderboot mit zwei Duchten und Riemen, liegt auf dem Kiel
  steg              Anlegesteg 4 m (Deck bei z = 0,6, Pfähle bis 1,5 m unter den Boden für Wasser)
  hummerkorb        Hummerkorb aus Latten mit Netz, Leine und Schwimmer
  fischgestell      Trockengestell mit aufgehängten Fischen
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, klotz, verbiegen, ausrichten
import props
from behaelter import netz, schwimmer
from kueche import haufen, ellipsoid


# ======================================================================== Hilfen

def geroell(m, mitte, n, weite, gross=(0.04, 0.12), mat="stein", rx=1.0):
    for k in range(n):
        a = m.rnd.uniform(0, 2 * math.pi); d = math.sqrt(m.rnd.random()) * weite
        g = m.rnd.uniform(*gross)
        m.teil(brocken(m.rnd, g, g * 0.8, g * 0.6, 0.25, 1), mat,
               M((mitte[0] + d * math.cos(a) * rx, mitte[1] + d * math.sin(a), g * 0.35), (0, 0, m.rnd.uniform(0, 360))))


def spitzhacke(m, matrix, stiel=0.85, nur_kopf=False):
    """Spitzhacke: Stiel entlang z, Kopf quer (x) am oberen Ende."""
    if not nur_kopf:
        m.stab(tuple(matrix @ Vector((0, 0, 0))), tuple(matrix @ Vector((0, 0, stiel))), 0.018, "holz", biegen=0.002)
    for s in (-1, 1):
        kopf = drehkoerper([(0.022, 0.0), (0.018, 0.12), (0.008, 0.24), (0.0, 0.27)], 6)
        verbiegen(kopf, m.rnd, 0.003, 0.1)
        m.teil(kopf, "eisen", matrix @ M((0, 0, stiel - 0.04), (0, s * 90 - s * 8, 0)))
    m.teil(quader(0.07, 0.05, 0.08, fase=0.008), "eisen", matrix @ M((0, 0, stiel - 0.04)))


# ======================================================================== Stützbalken

def stuetzbalken(m, kaputt):
    B, H = 2.4, 2.5
    r = 0.12
    for s in (-1, 1):
        x = s * (B / 2 - 0.15)
        if kaputt and s == 1:
            # rechter Stempel weggeknickt, die Kappe hängt rechts herunter
            m.stab((x, 0, 0), (x - 0.12, 0, 1.3), r, "holz_alt", biegen=0.01)
            m.stab((x + 0.15, -0.25, 0.12), (x + 0.75, -0.9, 0.12), r, "holz_alt", biegen=0.01)
            continue
        m.stab((x + s * 0.12, 0, 0), (x, 0, H - 0.12), r, "holz_alt", biegen=0.008)
    if not kaputt:
        m.stab((-B / 2 - 0.05, 0, H), (B / 2 + 0.05, 0, H), r + 0.01, "holz_alt", biegen=0.008)
        # Keile zwischen Stempel und Kappe, Verzug oben
        for s in (-1, 1):
            m.teil(quader(0.2, 0.1, 0.04), "holz", M((s * (B / 2 - 0.15), 0.0, H - 0.115), (0, s * 8, 0)))
        for k in range(7):
            y = -0.45 + 0.15 * k
            m.brett(B + 0.3, 0.14, 0.03, M((0, y, H + r + 0.03), (0, 0, m.rnd.uniform(-2, 2))), "holz_alt", biegen=0.01)
        return
    # Kappe gebrochen, schräg; Verzug teils heruntergefallen; Geröll darunter
    links = Vector((-B / 2 - 0.05, 0, H)); knick = Vector((0.1, 0, H - 0.15)); rechts = Vector((B / 2 - 0.1, 0.0, 1.35))
    m.stab(tuple(links), tuple(knick), r + 0.01, "holz_alt", biegen=0.008)
    m.stab(tuple(knick + Vector((0.03, 0, -0.02))), tuple(rechts), r + 0.01, "holz_alt", biegen=0.008)
    for k in range(4):
        y = -0.45 + 0.3 * k
        m.brett(1.4, 0.14, 0.03, M((-0.55, y, H + r + 0.03)), "holz_alt", biegen=0.01, bruch=1)
    for k in range(3):
        m.brett(1.2, 0.14, 0.03, M((0.4 + 0.2 * k, -0.6 + 0.4 * k, 0.12 + 0.03 * k), (0, 0, 30 * k - 20)), "holz_alt", bruch=-1)
    haufen(m, (0.6, 0.0), 0.8, 0.7, 0.35, "stein", m.rnd, rand_rauh=0.3)
    geroell(m, (0.6, -0.2), 16, 0.8, (0.06, 0.18))


# ======================================================================== Schienen

def schienen(m, kaputt):
    L, spur = 2.0, 0.6
    for k in range(5):
        y = -L / 2 + 0.2 + 0.4 * k
        if kaputt and k == 2:
            m.kantholz((-0.5, y, 0.05), (0.05, y + 0.05, 0.05), 0.14, 0.1, "holz_alt", bruch=1)
            continue
        m.kantholz((-0.55, y, 0.05), (0.55, y, 0.05), 0.14, 0.1, "holz_alt")
    for s in (-1, 1):
        x = s * spur / 2
        pts = [(x, -L / 2, 0.135), (x, L / 2, 0.135)]
        if kaputt and s == 1:
            pts = [(x, -L / 2, 0.135), (x, 0.0, 0.135), (x + 0.05, 0.4, 0.2), (x + 0.12, 0.8, 0.45), (x + 0.15, 1.0, 0.6)]
        for (a, b) in zip(pts, pts[1:]):
            m.kantholz(a, b, 0.05, 0.07, "eisen", fase=0.004, biegen=0)
        # Nägel
        for k in range(5):
            y = -L / 2 + 0.2 + 0.4 * k
            if kaputt and s == 1 and y > 0.0:
                continue
            for d in (-1, 1):
                m.teil(quader(0.02, 0.02, 0.03), "eisen", M((x + d * 0.04, y, 0.112)))


# ======================================================================== Erzhaufen

def erzbrocken(m, matrix, g, rnd):
    m.teil(brocken(rnd, g, g * 0.8, g * 0.65, 0.3, 1), "stein", matrix)
    for k in range(2):
        a = rnd.uniform(0, 2 * math.pi)
        p = Vector((g * 0.75 * math.cos(a), g * 0.6 * math.sin(a), g * 0.25))
        m.teil(brocken(rnd, g * 0.35, g * 0.3, g * 0.25, 0.3, 1), "erz", matrix @ M(tuple(p)))


def erzhaufen(m, kaputt):
    if not kaputt:
        haufen(m, (0.0, 0.0), 0.8, 0.65, 0.45, "stein", m.rnd, rand_rauh=0.2)
        for k in range(34):
            a = m.rnd.uniform(0, 2 * math.pi); u = math.sqrt(m.rnd.random())
            x = 0.75 * u * math.cos(a); y = 0.6 * u * math.sin(a)
            z = 0.45 * (1 - u * u) ** 1.6
            erzbrocken(m, M((x, y, z), (m.rnd.uniform(0, 360), m.rnd.uniform(0, 360), 0)), m.rnd.uniform(0.05, 0.11), m.rnd)
        # Schaufel im Haufen
        m.stab((0.35, -0.55, 0.15), (0.75, -0.95, 0.85), 0.017, "holz", biegen=0)
        m.teil(quader(0.22, 0.26, 0.012, fase=0.004), "eisen", ausrichten((0.25, -0.45, 0.02), (0.38, -0.58, 0.18)) @ M((0, 0, 0)))
        return
    # abgetragen: nur ein flacher Rest, Brocken verstreut, Schaufel zerbrochen
    haufen(m, (0.0, 0.0), 0.9, 0.7, 0.12, "stein", m.rnd, rand_rauh=0.35)
    for k in range(14):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.2, 1.2)
        erzbrocken(m, M((d * math.cos(a), d * 0.8 * math.sin(a), 0.03 + (0.06 if d < 0.6 else 0.0))), m.rnd.uniform(0.04, 0.08), m.rnd)
    m.stab((0.5, -0.9, 0.017), (0.95, -0.7, 0.017), 0.017, "holz", biegen=0)
    m.teil(quader(0.22, 0.26, 0.012, fase=0.004), "eisen", M((0.3, -1.05, 0.006), (0, 0, 25)))


# ======================================================================== Spitzhacke im Fels

def spitzhacke_fels(m, kaputt):
    if not kaputt:
        fels = brocken(m.rnd, 0.55, 0.45, 0.4, 0.22, 3)
        m.teil(fels, "stein", M((0, 0, 0.25)))
        # Hacke steckt schräg mit einer Spitze oben im Fels
        spitzhacke(m, M((-0.84, 0.0, 0.33), (0, 60, 0)))
        geroell(m, (0.0, -0.1), 8, 0.8, (0.02, 0.06))
        return
    # Fels gespalten, die Hälften liegen auseinander; Stiel gebrochen, der Kopf steckt noch, der Stiel liegt daneben
    for s in (-1, 1):
        h = brocken(m.rnd, 0.3, 0.45, 0.38, 0.22, 3)
        for v in h.verts:
            if s * v.co.x < -0.0:
                v.co.x *= 0.15
        m.teil(h, "stein", M((s * 0.2, 0, 0.23), (0, s * 6, 0)))
    spitzhacke(m, M((-0.84, 0.0, 0.33), (0, 60, 0)) @ M((0, 0, 0.55)), stiel=0.3)
    m.stab((-0.55, -0.7, 0.018), (-0.05, -0.85, 0.018), 0.018, "holz", biegen=0)
    geroell(m, (0.0, -0.2), 14, 0.9, (0.02, 0.09))


# ======================================================================== Ruderboot

def rumpf(m, matrix, L=3.2, B=1.2, H=0.55, loch=None, mat="holz_alt"):
    nx, nu = 24, 14
    g = []
    for i in range(nx + 1):
        t = -1 + 2 * i / nx
        x = t * L / 2
        breite = B / 2 * (1 - abs(t) ** 2.2) ** 0.7
        tief = H * (0.15 + 0.85 * (1 - abs(t) ** 3))
        zeile = []
        for j in range(nu + 1):
            u = -1 + 2 * j / nu
            y = breite * u
            z = H - tief * (1 - abs(u) ** 2.3) + 0.04 * abs(t) ** 4
            zeile.append(tuple(matrix @ Vector((x, y, z))))
        g.append(zeile)
    bm = flaeche(g, 0.025, loch)
    m.teil(bm, mat, None)
    # Dollbord
    for s in (-1, 1):
        pts = [tuple(matrix @ Vector((t * L / 2, s * B / 2 * (1 - abs(t) ** 2.2) ** 0.7, H + 0.04 * abs(t) ** 4 + 0.01)))
               for t in (-1 + 2 * i / nx for i in range(1, nx))]
        m.seil(pts, 0.022, 5, "holz")


def ruderboot(m, kaputt):
    H = 0.55
    lage = M((0, 0, 0.03)) if not kaputt else M((0, 0, 0.0), (35, 0, 0)) @ M((0, -0.05, 0.04))
    loch = (lambda i, j: (9 <= i <= 11 and 2 <= j <= 4) or (i == 12 and j == 3)) if kaputt else None
    rumpf(m, lage, loch=loch)
    # Duchten (Sitzbänke) und Kiel
    for x, b in ((-0.5, 1.05), (0.55, 1.02)):
        if kaputt and x > 0:
            m.brett(0.5, 0.22, 0.03, lage @ M((x, -0.2, H - 0.12)), "holz", bruch=1)
            continue
        m.brett(0.22, b, 0.03, lage @ M((x, 0, H - 0.12)), "holz")
    m.teil(quader(2.2, 0.06, 0.06), "holz", lage @ M((0, 0, 0.0)))
    # Riemen: liegen im Boot bzw. einer zerbrochen am Strand
    for s in (-1, 1):
        if kaputt and s == 1:
            m.stab((0.6, -1.1, 0.02), (1.6, -1.25, 0.02), 0.02, "holz", biegen=0)
            m.teil(quader(0.4, 0.13, 0.015), "holz", M((-0.05, -1.0, 0.008), (0, 0, -8)))
            continue
        a = lage @ Vector((-1.05, s * 0.18, H - 0.07)); b = lage @ Vector((1.05, s * 0.3, H - 0.07))
        m.stab(tuple(a), tuple(b), 0.02, "holz", biegen=0)
        m.teil(quader(0.45, 0.13, 0.015), "holz", ausrichten(a, b) @ M((-0.95, 0, 0)))


# ======================================================================== Steg

def steg(m, kaputt):
    L, B, zd = 4.0, 1.5, 0.6
    for x in (-1.8, 0.0, 1.8):
        for s in (-1, 1):
            if kaputt and x == 1.8 and s == -1:
                m.stab((x, s * 0.68, -1.5), (x, s * 0.68, 0.1), 0.11, "holz_alt", biegen=0.01)
                continue
            m.stab((x, s * 0.68, -1.5), (x, s * 0.68, zd + (0.05 if not (x == 1.8 and s == 1) else 0.7)), 0.11, "holz_alt", biegen=0.01)
        m.kantholz((x, -B / 2, zd - 0.12), (x, B / 2, zd - 0.12), 0.12, 0.14, "holz_alt")
    for s in (-1, 1):
        m.kantholz((-L / 2, s * 0.5, zd - 0.04), (L / 2, s * 0.5, zd - 0.04) if not (kaputt and s == -1) else (0.9, s * 0.5, zd - 0.04),
                   0.1, 0.1, "holz_alt", bruch=(1 if kaputt and s == -1 else 0))
    n = 26
    for k in range(n):
        x = -L / 2 + (k + 0.5) * L / n
        if kaputt and (k in (5, 6, 14) or (k > 19 and k % 2 == 0)):
            continue
        if kaputt and k > 19:
            # Ende abgesackt: die Bretter hängen zur gebrochenen Seite
            m.brett(0.14, B, 0.035, M((x, 0, zd + 0.0175 - 0.25 * (k - 19) / 6), (-12, 0, 0)), "holz_alt", biegen=0.004)
            continue
        m.brett(0.14, B, 0.035, M((x, 0, zd + 0.0175), (0, 0, m.rnd.uniform(-1, 1))), "holz_alt", biegen=0.004)
    # Seil am Poller
    m.seil([(1.8 + 0.12 * math.cos(2 * math.pi * k / 10), 0.68 + 0.12 * math.sin(2 * math.pi * k / 10), zd + 0.5) for k in range(11)], 0.015)
    if not kaputt:
        m.seil([(1.92, 0.68, zd + 0.5), (2.3, 0.4, zd + 0.1), (2.6, 0.1, -0.2)], 0.015)


# ======================================================================== Hummerkorb

def hummerkorb(m, kaputt):
    L, R = 0.7, 0.25
    m.brett(L + 0.04, 2 * R + 0.04, 0.025, M((0, 0, 0.0125)), "holz_alt")
    # Bögen und Längslatten
    for x in (-L / 2, 0.0, L / 2):
        bogen = [(x, R * math.cos(math.pi * k / 12), 0.025 + R * math.sin(math.pi * k / 12) * (1 if not (kaputt and x > 0) else 0.55))
                 for k in range(13)]
        m.seil(bogen, 0.012, 5, "holz_alt")
    for k in range(9):
        a = math.pi * k / 8
        if kaputt and k in (3, 4, 5):
            continue
        m.stab((-L / 2 - 0.02, R * math.cos(a), 0.025 + R * math.sin(a)), (L / 2 + 0.02, R * math.cos(a), 0.025 + R * math.sin(a) *
                                                                             (1 if not kaputt else 0.6)), 0.008, "holz_alt", biegen=0)
    # Netz an den Stirnseiten (Trichter)
    for s in (-1, 1):
        if kaputt and s == 1:
            continue
        g = [[(s * (L / 2 - 0.06 * (1 - rr)), R * rr * math.cos(math.pi * k / 12), 0.025 + R * rr * math.sin(math.pi * k / 12))
              for k in range(13)] for rr in (0.3, 0.65, 1.0)]
        m.teil(flaeche(g, 0.0, lambda i, j: (i + j) % 2 == 1), "seil", None)
    # Leine mit Schwimmer
    leine = [(L / 2, 0.0, 0.025 + R), (L / 2 + 0.3, -0.1, 0.03), (L / 2 + 0.6, -0.35, 0.02), (L / 2 + 0.75, -0.6, 0.02)]
    m.seil(leine if not kaputt else leine[:2] + [(L / 2 + 0.35, -0.15, 0.01)], 0.006)
    if not kaputt:
        schwimmer(m, M((L / 2 + 0.8, -0.68, 0.03), (0, 0, 40)))
    else:
        for k in range(5):
            m.stab((m.rnd.uniform(-0.6, 0.6), m.rnd.uniform(-0.6, -0.35), 0.008), (m.rnd.uniform(-0.6, 0.6), m.rnd.uniform(-0.6, -0.35), 0.008),
                   0.008, "holz_alt", biegen=0)


# ======================================================================== Fischtrockengestell

def fisch(m, matrix, L=0.32, mat="fisch"):
    """Fisch hängt am Schwanz: Kopf unten (z negativ)."""
    koerper = ellipsoid(L * 0.18, L * 0.06, L * 0.5, 2)
    for v in koerper.verts:
        if v.co.z > 0:                                # zum Schwanz hin schlanker
            f = 1 - 0.7 * (v.co.z / (L * 0.5))
            v.co.x *= f; v.co.y *= f
    m.teil(koerper, mat, matrix @ M((0, 0, -L * 0.5)))
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((0, 0, -0.02), (-L * 0.15, 0, 0.06), (L * 0.15, 0, 0.06))]
    bm.faces.new(vs)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.003)
    m.teil(bm, mat, matrix @ M((0, 0, -0.03)))


def fischgestell(m, kaputt):
    B, H = 2.0, 1.8
    # zwei A-Böcke, Querstangen in zwei Höhen
    for s in (-1, 1):
        x = s * B / 2
        if kaputt and s == 1:
            # rechter Bock umgeknickt, die Stangen liegen dort auf dem Boden
            m.stab((x, -0.45, 0.0), (x, -0.2, 0.7), 0.035, "holz_alt", biegen=0.005)
            m.stab((x + 0.1, 0.5, 0.035), (x - 0.3, 1.7, 0.035), 0.035, "holz_alt", biegen=0.005)
            continue
        for t in (-1, 1):
            m.stab((x, t * 0.45, 0.0), (x, 0.0, H + 0.1), 0.035, "holz_alt", biegen=0.005)
        m.seil([(x + 0.05 * math.cos(2 * math.pi * k / 8), 0.05 * math.sin(2 * math.pi * k / 8), H - 0.02) for k in range(9)], 0.008)
    for z, y in ((H, 0.0), (H - 0.6, 0.14)):
        if kaputt:
            end = Vector((B / 2, y * 0.0, 0.035))
            anfang = Vector((-B / 2, y * (1 - (H - z) / H) if z < H else 0.0, z))
            m.stab(tuple(anfang - (end - anfang).normalized() * 0.1), tuple(end + Vector((0.2, -0.1 + 0.2 * (z < H), 0))), 0.025, "holz", biegen=0.004)
            continue
        m.stab((-B / 2 - 0.1, y, z), (B / 2 + 0.1, y, z), 0.025, "holz", biegen=0.004)
        for k in range(9):
            x = -0.8 + 0.2 * k
            m.seil([(x, y, z - 0.025), (x, y, z - 0.08)], 0.003, 4)
            fisch(m, M((x, y, z - 0.08), (0, 0, m.rnd.uniform(-20, 20))), m.rnd.uniform(0.26, 0.36))
    if kaputt:
        # ein paar Fische und Gräten liegen im Sand
        for k in range(4):
            fisch(m, M((m.rnd.uniform(-0.6, 0.8), m.rnd.uniform(-0.7, 0.5), 0.02), (90, 0, m.rnd.uniform(0, 360))), 0.3, "fisch_trocken")
        for k in range(3):
            x, y = m.rnd.uniform(-0.8, 0.6), m.rnd.uniform(-0.9, -0.3)
            m.stab((x, y, 0.004), (x + 0.2, y + 0.02, 0.004), 0.003, "knochen", seg=4, biegen=0)
            for j in range(6):
                xx = x + 0.03 * (j + 1)
                m.stab((xx, y, 0.004), (xx - 0.015, y + 0.04, 0.004), 0.0015, "knochen", seg=3, biegen=0)
                m.stab((xx, y, 0.004), (xx - 0.015, y - 0.04, 0.004), 0.0015, "knochen", seg=3, biegen=0)


MODELLE = {"stuetzbalken": stuetzbalken, "schienen": schienen, "erzhaufen": erzhaufen, "spitzhacke_fels": spitzhacke_fels,
           "ruderboot": ruderboot, "steg": steg, "hummerkorb": hummerkorb, "fischgestell": fischgestell}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
