"""Haus-Baukasten im 2-m-Raster: Fachwerkwände (auch mit Fenster und Tür), Tür, Boden, Geschossdecke,
Satteldach (Dachfläche, First, Giebel) und Treppen, jedes Teil heil und kaputt.
Aufruf: python baukasten.py -- <zielordner/modelle> [--nur wand,dach] [--vorschau <ordner>]

Maße und Anschlüsse (alle Teile rasten im 2-m-Raster ein, ein Geschoss ist 3 m hoch):
  wand*        2 m breit (x -1..1), 3 m hoch, 0.2 m dick, Mitte der Wand auf y = 0. Die Eckständer sind
               halbiert: zwei Wände nebeneinander ergeben zusammen einen ganzen Ständer.
  tuer         Türblatt 1.0 x 2.1 m, Ursprung an der Angel (links unten); passt in wand_tuer bei x = -0.5.
  boden        2 x 2 m Dielen, Oberkante z = 0 (Erdgeschoss, liegt auf dem Gelände).
  decke        2 x 2 m Dielen auf Balken, Oberkante z = 0, Balken darunter (von unten die Decke des Geschosses).
               Für das Obergeschoss auf z = 3 setzen.
  dach         Eine Dachfläche 45°, 2 m entlang x, steigt von der Traufe (y = 0, z = 0) bis zum First (y = 2, z = 2),
               dazu 0.4 m Überstand. Auf die Wandkrone (z = 3) setzen, die Gegenseite um 180° gedreht.
  dach_first   Firstbalken mit Abdeckung, 2 m, bei y = 2, z = 2 der Dachfläche (Ursprung am First).
  giebel       Dreieckige Fachwerk-Giebelwand für ein 4 m breites Haus: x -2..2, z 0..2, auf die Wandkrone.
  treppe_holz  Innentreppe 1 m breit, 4 m lang (y 0..4), 3 m hoch: ein Geschoss.
  treppe_stein Stadttreppe 2 m breit, 2 m lang, 1 m hoch (5 Stufen), stapelbar für längere Treppen."""
import bpy, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, quader, flaeche, verbiegen, bruchkante, klotz
import props

H = 3.0          # Geschosshöhe
D = 0.2          # Wanddicke
BALKEN = 0.16    # Fachwerk-Balken (Breite in der Wandebene)


def holz_art(kaputt, rnd):
    """Kaputte Teile sind teils angekohlt."""
    return "holz_verkohlt" if kaputt and rnd.random() < 0.3 else "holz"


def putzfeld(m, x0, x1, z0, z1, loch=None):
    """Gefach mit Lehmputz zwischen den Balken, etwas zurückgesetzt. loch: (x, z, r) ausgebrochen."""
    nx = max(2, int((x1 - x0) / 0.12)); nz = max(2, int((z1 - z0) / 0.12))
    for seite in (-1, 1):
        gitter = []
        for i in range(nz + 1):
            zeile = []
            for j in range(nx + 1):
                x = x0 + (x1 - x0) * j / nx; z = z0 + (z1 - z0) * i / nz
                zeile.append((x, seite * (D / 2 - 0.025), z))
            gitter.append(zeile if seite < 0 else list(reversed(zeile)))
        def l(i, j, seite=seite):
            if not loch:
                return False
            jj = j if seite < 0 else nx - 1 - j
            x = x0 + (x1 - x0) * (jj + 0.5) / nx; z = z0 + (z1 - z0) * (i + 0.5) / nz
            r = loch[2] * (1 + 0.35 * noise.noise(Vector((x * 5, z * 5, 1.7))))
            return (x - loch[0]) ** 2 + (z - loch[1]) ** 2 < r * r
        bm = flaeche(gitter, 0.0, l)
        verbiegen(bm, m.rnd, 0.006, 0.3, (0.0, 1.0, 0.0))
        m.teil(bm, "putz", None)
    # Lehmfüllung zwischen den beiden Putzschichten (sichtbar nur an Löchern): Lochrand als Rohr aus Flechtwerk
    if loch:
        pts = [(loch[0] + loch[2] * 0.95 * math.cos(a), 0, loch[1] + loch[2] * 0.95 * math.sin(a))
               for a in [2 * math.pi * k / 12 for k in range(13)]]
        for s in (-0.05, 0.0, 0.05):
            m.seil([(p[0], s, p[2]) for p in pts], 0.012, 5, "holz_alt")


def fachwerk(m, kaputt, oeffnung=None):
    """Fachwerkwand 2 m. oeffnung: None, ('fenster', x0, x1, z0, z1) oder ('tuer', x0, x1, 0, z1)."""
    rnd = m.rnd
    b = BALKEN; hb = b / 2
    # Schwelle und Rähm (unten/oben), Eckständer halbiert
    m.kantholz((-1, 0, hb / 2 + 0.0), (1, 0, hb / 2), D, b * 0.9, holz_art(kaputt, rnd), oben=(0, 0, 1))
    if not kaputt:
        m.kantholz((-1, 0, H - hb / 2), (1, 0, H - hb / 2), D, b, "holz", oben=(0, 0, 1))
    else:
        m.kantholz((-1, 0, H - hb / 2), (0.25, 0, H - hb / 2), D, b, "holz_verkohlt", oben=(0, 0, 1), bruch=1)
    for s in (-1, 1):
        x = s * (1 - hb / 2)
        top = H - b if not (kaputt and s > 0) else H * 0.62
        m.kantholz((x, 0, b * 0.9), (x, 0, top), hb, D, holz_art(kaputt, rnd), oben=(0, -1, 0),
                   bruch=1 if kaputt and s > 0 else 0)
    # Riegel in halber Höhe und Streben
    zr = 1.0 if not oeffnung or oeffnung[0] != "fenster" else oeffnung[3] - b / 2
    felder = []
    if oeffnung is None:
        m.kantholz((-1 + hb, 0, zr), (1 - hb, 0, zr), b * 0.8, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        m.kantholz((0, 0, b * 0.9), (0, 0, H - b), b, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        # Streben: K-Form
        for s in (-1, 1):
            a = Vector((s * (1 - hb), 0, zr + b * 0.4)); e = Vector((s * b * 0.5, 0, H - b))
            m.kantholz(a, e, b * 0.75, D * 0.9, holz_art(kaputt, rnd), oben=(0, -1, 0),
                       bruch=-1 if kaputt and s < 0 else 0)
        felder = [(-1 + hb, -b / 2, b * 0.9, zr - b * 0.4), (b / 2, 1 - hb, b * 0.9, zr - b * 0.4),
                  (-1 + hb, -b / 2, zr + b * 0.4, H - b), (b / 2, 1 - hb, zr + b * 0.4, H - b)]
    elif oeffnung[0] == "fenster":
        _, x0, x1, z0, z1 = oeffnung
        for x in (x0 - hb / 2 - 0.0, x1 + hb / 2):
            m.kantholz((x, 0, b * 0.9), (x, 0, H - b), hb * 1.1, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        m.kantholz((-1 + hb, 0, z0 - b * 0.4), (1 - hb, 0, z0 - b * 0.4), b * 0.8, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        m.kantholz((x0 - hb, 0, z1 + b * 0.4), (x1 + hb, 0, z1 + b * 0.4), b * 0.8, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        felder = [(-1 + hb, x0 - hb, b * 0.9, z0 - b * 0.8), (x1 + hb, 1 - hb, b * 0.9, z0 - b * 0.8),
                  (-1 + hb, x0 - hb, z0, H - b), (x1 + hb, 1 - hb, z0, H - b),
                  (x0 - hb * 0.0, x1, b * 0.9, z0 - b * 0.8), (x0, x1, z1 + b * 0.8, H - b)]
        # Fensterrahmen, Kreuzsprosse, Fensterbank, Läden
        rb = 0.06
        for (a, e) in (((x0, z0), (x0, z1)), ((x1, z0), (x1, z1)), ((x0, z0), (x1, z0)), ((x0, z1), (x1, z1))):
            m.kantholz((a[0], -0.02, a[1]), (e[0], -0.02, e[1]), rb, D * 0.7, "holz", oben=(0, -1, 0))
        if not kaputt:
            m.kantholz(((x0 + x1) / 2, -0.03, z0), ((x0 + x1) / 2, -0.03, z1), 0.04, 0.04, "holz", oben=(0, -1, 0))
            m.kantholz((x0, -0.03, (z0 + z1) / 2), (x1, -0.03, (z0 + z1) / 2), 0.04, 0.04, "holz", oben=(0, -1, 0))
            m.teil(quader(x1 - x0 - 0.02, 0.006, z1 - z0 - 0.02), "glas", M(((x0 + x1) / 2, -0.03, (z0 + z1) / 2)))
        else:
            m.kantholz(((x0 + x1) / 2, -0.03, z0), ((x0 + x1) / 2, -0.03, z0 + 0.35), 0.04, 0.04, "holz", oben=(0, -1, 0), bruch=1)
        m.brett(x1 - x0 + 0.2, 0.12, 0.04, M(((x0 + x1) / 2, -D / 2 - 0.03, z0 - 0.02)), "holz")
        for s, x in ((-1, x0), (1, x1)):
            breite = (x1 - x0) / 2
            if kaputt and s > 0:
                # Laden hängt schief an einer Angel
                lm = M((x + 0.03, -D / 2 - 0.05, z1 - 0.05), (0, 0, 25)) @ M((0, 0, 0), (0, -14, 0)) @ M((breite / 2, 0, -(z1 - z0) / 2))
            else:
                lm = M((x + s * breite / 2 + s * 0.03, -D / 2 - 0.035, (z0 + z1) / 2))
            for k in range(3):
                bx = -breite / 2 + breite / 6 + k * breite / 3
                m.brett(z1 - z0, breite / 3 - 0.006, 0.025, lm @ M((bx, 0, 0), (0, 90, 0)) @ M(rot=(90, 0, 0)), "holz_alt")
    else:  # Tür
        _, x0, x1, _, z1 = oeffnung
        for x in (x0 - hb / 2, x1 + hb / 2):
            m.kantholz((x, 0, b * 0.9), (x, 0, H - b), hb * 1.1, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        m.kantholz((x0 - hb, 0, z1 + b * 0.5), (x1 + hb, 0, z1 + b * 0.5), b, D * 1.02, holz_art(kaputt, rnd), oben=(0, -1, 0))
        m.kantholz((x1 + hb, 0, 1.0), (1 - hb, 0, 1.0), b * 0.8, D * 0.95, holz_art(kaputt, rnd), oben=(0, -1, 0))
        felder = [(x1 + hb, 1 - hb, b * 0.9, 1.0 - b * 0.4), (x1 + hb, 1 - hb, 1.0 + b * 0.4, H - b),
                  (-1 + hb, x0 - hb, b * 0.9, H - b), (x0, x1, z1 + b, H - b)]
        if x0 - hb - (-1 + hb) < 0.05:
            felder.pop(2)
        # Türschwelle aus Stein
        m.teil(klotz(rnd, x1 - x0, D + 0.1, 0.08, 0.01), "stein", M(((x0 + x1) / 2, -0.05, 0.04)))
    # Gefache
    for i, (x0, x1, z0, z1) in enumerate(felder):
        if x1 - x0 < 0.05 or z1 - z0 < 0.05:
            continue
        loch = None
        if kaputt and i in (1, 2):
            loch = ((x0 + x1) / 2 + rnd.uniform(-0.1, 0.1), (z0 + z1) / 2, min(x1 - x0, z1 - z0) * 0.42)
        if kaputt and i == 3 and z1 > H * 0.6:
            continue                                  # oberes Gefach ganz herausgebrochen
        putzfeld(m, x0, x1, z0, z1, loch)
    if kaputt:
        # Schutt am Boden
        for k in range(5):
            g = rnd.uniform(0.06, 0.12)
            m.teil(basis.brocken(rnd, g * 1.4, g, g * 0.6), "putz",
                   M((rnd.uniform(-0.6, 0.9), rnd.choice((-1, 1)) * rnd.uniform(0.25, 0.6), g * 0.3)))
        m.brett(0.9, b * 0.8, D * 0.8, M((0.4, -0.75, 0.07), (0, 0, 18)), "holz_verkohlt", bruch=1)


def wand(m, kaputt):
    fachwerk(m, kaputt)


def wand_fenster(m, kaputt):
    fachwerk(m, kaputt, ("fenster", -0.4, 0.4, 1.05, 2.05))


def wand_tuer(m, kaputt):
    fachwerk(m, kaputt, ("tuer", -0.5, 0.5, 0.0, 2.15))


def tuer(m, kaputt):
    """Brettertür mit Querleisten, Strebe und Eisenbändern. Ursprung an der Angel links unten,
    Tür liegt in der x-z-Ebene (x 0..1), dreht um die z-Achse."""
    b, h = 0.98, 2.12
    if kaputt:
        # obere Angel ausgerissen: Tür hängt schräg nach außen
        props.boden_setzen(m, (0, -12, -35), (0, 0, 0.1))
    n = 6
    for i in range(n):
        x = b / n * (i + 0.5)
        if kaputt and i in (3, 4):
            laenge = (0.9, 1.3)[i - 3]
            m.brett(laenge, b / n - 0.004, 0.035, M((x, 0, laenge / 2 + 0.02), (0, -90, 0)) @ M(rot=(90, 0, 0)), "holz",
                    bruch=-1, bruch_tiefe=0.15)
            continue
        m.brett(h, b / n - 0.004, 0.035, M((x, 0, h / 2 + 0.01), (0, -90, 0)) @ M(rot=(90, 0, 0)), "holz")
    for z in (0.25, h - 0.25):
        m.kantholz((0.03, 0.035, z), (b - 0.03, 0.035, z), 0.12, 0.03, "holz", oben=(0, 1, 0))
        m.teil(quader(b * 0.75, 0.006, 0.045, fase=0.002), "eisen", M((b * 0.375, -0.022, z)))
        m.teil(basis.rundholz(0.018, 0.08, 8), "eisen", M((-0.01, -0.0, z), (0, 90, 0)), uv="zyl", r=0.018)
    m.kantholz((0.08, 0.035, 0.3), (b - 0.08, 0.035, h - 0.32), 0.1, 0.03, "holz", oben=(0, 1, 0))
    # Griff
    m.seil([(b - 0.12, -0.02, 1.0), (b - 0.12, -0.06, 1.02), (b - 0.12, -0.06, 1.14), (b - 0.12, -0.02, 1.16)], 0.008, 5, "eisen")


def boden(m, kaputt):
    """Dielenboden 2 x 2 m für das Erdgeschoss, Oberkante z = 0."""
    if not kaputt:
        m.teil(quader(2.0, 2.0, 0.05, 4, 4, 1), "dielen", M((0, 0, -0.025)), versatz=(0, 0))
        return
    # Loch mit abgebrochenen Dielen (Dielen hier als einzelne Bretter, 20 cm, Faser entlang y)
    for i in range(10):
        x = -1 + 0.1 + i * 0.2
        if 3 <= i <= 6:
            for s in (-1, 1):
                l = m.rnd.uniform(0.45, 0.75) if i in (4, 5) else m.rnd.uniform(0.7, 0.85)
                m.brett(l, 0.196, 0.04, M((x, s * (1 - l / 2), -0.02), (0, 0, 90)), "holz", bruch=-s, bruch_tiefe=0.12)
        else:
            m.brett(2.0, 0.196, 0.04, M((x, 0, -0.02), (0, 0, 90)), "holz", nx=6)
    m.kantholz((-1, -0.0, -0.12), (1, 0.0, -0.12), 0.16, 0.12, "holz_alt")
    m.brett(0.7, 0.196, 0.04, M((0.0, 0.1, -0.15), (20, 0, 80)), "holz_verkohlt", bruch=1)


def decke(m, kaputt):
    """Geschossdecke: Dielen auf Balken (Abstand 0.67 m), Oberkante z = 0."""
    for i in range(3):
        x = -1 + 1 / 3 + i * 2 / 3
        if kaputt and i == 1:
            m.kantholz((x, -1, -0.15), (x, -0.1, -0.15), 0.14, 0.2, "holz_verkohlt", bruch=1)
            m.kantholz((x, 0.25, -0.65), (x, 1, -0.15), 0.14, 0.2, "holz_verkohlt", bruch=-1)
            continue
        m.kantholz((x, -1, -0.15), (x, 1, -0.15), 0.14, 0.2, "holz" if not kaputt else "holz_alt")
    if not kaputt:
        m.teil(quader(2.0, 2.0, 0.05, 4, 4, 1), "dielen", M((0, 0, -0.025)), versatz=(0, 0))
        return
    for i in range(10):
        x = -1 + 0.1 + i * 0.2
        if 2 <= i <= 6:
            for s in (-1, 1):
                l = m.rnd.uniform(0.35, 0.7)
                m.brett(l, 0.196, 0.04, M((x, s * (1 - l / 2), -0.02), (0, 0, 90)), "holz_alt", bruch=-s, bruch_tiefe=0.12)
        else:
            m.brett(2.0, 0.196, 0.04, M((x, 0, -0.02), (0, 0, 90)), "holz_alt", nx=6)


def dach(m, kaputt):
    """Dachfläche 45°: Sparren, Lattung, Schindeln. Traufe bei y = 0, z = 0; First bei y = 2, z = 2."""
    ueber = 0.4
    neig = M(rot=(45, 0, 0))                    # lokale y-Achse läuft die Dachschräge hinauf
    L = 2 * math.sqrt(2) + ueber * math.sqrt(2)  # Sparrenlänge entlang der Schräge
    y0 = -ueber * math.sqrt(2)                   # Start unten (Überstand)
    def schraeg(x, s, z):
        return neig @ Vector((x, s, z))
    # Sparren (3 je Modul, die äußeren halb: zwei Module nebeneinander ergeben einen ganzen)
    for i, x in enumerate((-1 + 0.04, -1 / 3 + 0.0, 1 / 3, 1 - 0.04)):
        if kaputt and i == 2:
            m.kantholz(schraeg(x, y0, -0.1), schraeg(x, y0 + L * 0.55, -0.1), 0.08 if i in (0, 3) else 0.12, 0.16,
                       "holz_verkohlt", oben=neig @ Vector((0, 0, 1)), bruch=1)
            continue
        m.kantholz(schraeg(x, y0, -0.1), schraeg(x, y0 + L, -0.1), 0.08 if i in (0, 3) else 0.12, 0.16,
                   "holz" if not kaputt else "holz_alt", oben=neig @ Vector((0, 0, 1)))
    # Lattung
    lat = 9
    for k in range(lat):
        s = y0 + 0.15 + k * (L - 0.3) / (lat - 1)
        if kaputt and 3 <= k <= 5:
            m.kantholz(schraeg(-1, s, 0.0), schraeg(-0.2, s, 0.0), 0.05, 0.03, "holz_alt", oben=neig @ Vector((0, 0, 1)), bruch=1)
            continue
        m.kantholz(schraeg(-1, s, 0.0), schraeg(1, s, 0.0), 0.05, 0.03, "holz_alt", oben=neig @ Vector((0, 0, 1)))
    # Schindeldeckung: eine Platte mit Schindel-Textur, Loch bei kaputt
    nx, ny = 8, 12
    gitter = []
    for i in range(ny + 1):
        zeile = []
        for j in range(nx + 1):
            x = -1 + 2 * j / nx; s = y0 + L * i / ny
            zeile.append(tuple(schraeg(x, s, 0.035)))
        gitter.append(zeile)
    loch = None
    if kaputt:
        loch = lambda i, j: (i - 5.5) ** 2 + ((j - 2.5) * 1.3) ** 2 < 6 + 3 * noise.noise(Vector((i * 0.7, j * 0.7, 0.3)))
    bm = flaeche(gitter, 0.04, loch)
    # UV in Dachrichtung: u entlang x, v die Schräge hinauf
    ku, kv = basis.kachel("schindeln")
    uv = bm.loops.layers.uv.verify()
    inv = neig.inverted()
    for f in bm.faces:
        for l in f.loops:
            p = inv @ l.vert.co
            l[uv].uv = (p.x / ku, p.y / kv)
    m.teil(bm, "schindeln", None, uv=None)
    # Traufbrett
    m.kantholz(schraeg(-1, y0 + 0.01, -0.04), schraeg(1, y0 + 0.01, -0.04), 0.2, 0.025, "holz_alt", oben=neig @ Vector((0, -1, 0)))
    if kaputt:
        for k in range(3):
            m.brett(m.rnd.uniform(0.3, 0.6), 0.12, 0.02, M((m.rnd.uniform(-0.8, 0.8), m.rnd.uniform(0.3, 1.6), 0.01),
                                                           (0, 0, m.rnd.uniform(0, 180))), "holz_alt", bruch=1)


def dach_first(m, kaputt):
    """Firstpfette mit Firstabdeckung aus zwei Brettern. Ursprung am First."""
    m.kantholz((-1, 0, -0.22), (1, 0, -0.22), 0.16, 0.2, "holz", oben=(0, 0, 1), bruch=1 if kaputt else 0)
    for s in (-1, 1):
        rot = M(rot=(s * 45, 0, 0))
        if kaputt and s > 0:
            m.brett(1.1, 0.22, 0.03, M((-0.45, 0, 0.06)) @ rot @ M((0, s * 0.11, 0)), "holz_verkohlt", bruch=1)
            continue
        m.brett(2.0, 0.22, 0.03, M((0, 0, 0.06)) @ rot @ M((0, s * 0.11, 0)), "holz_alt")


## Die Giebelschrägen liegen so weit unter der Dachlinie, dass sie unter Sparren und Schindeln verschwinden
UNTER = 0.28


def giebel(m, kaputt):
    """Fachwerk-Giebeldreieck für ein 4 m breites Haus: Basis x -2..2 auf z = 0, Spitze bei z = 2."""
    rnd = m.rnd; b = BALKEN
    m.kantholz((-2, 0, b / 2), (2, 0, b / 2), D, b, "holz", oben=(0, 0, 1))
    for s in (-1, 1):
        m.kantholz((s * (2.05 - UNTER), 0, 0.0), (0, 0, 2.05 - UNTER), b, D, holz_art(kaputt, rnd), oben=(0, -1, 0),
                   bruch=1 if kaputt and s > 0 else 0)
    m.kantholz((0, 0, b), (0, 0, 1.95 - UNTER), b, D * 0.95, "holz", oben=(0, -1, 0))
    m.kantholz((-1.0, 0, b), (-1.0, 0, 0.98), b * 0.8, D * 0.95, "holz", oben=(0, -1, 0))
    m.kantholz((1.0, 0, b), (1.0, 0, 0.98), b * 0.8, D * 0.95, "holz", oben=(0, -1, 0))
    m.kantholz((-1.0, 0, 1.0), (1.0, 0, 1.0), b * 0.8, D * 0.95, "holz", oben=(0, -1, 0))
    # Putzflächen in den Dreiecks-/Trapezfeldern: Gitter, das an der Schräge endet
    def feld(x0, x1, z0, z1, loch=False):
        nx, nz = 6, 6
        if x0 * x1 > 0:                                   # Feld neben der Mitte: endet, wo die Schräge es abschneidet
            z1 = min(z1, 2.0 - UNTER - b * 0.75 - min(abs(x0), abs(x1)))
        for seite in (-1, 1):
            gitter = []
            for i in range(nz + 1):
                z = z0 + (z1 - z0) * i / nz
                rand = 2.0 - UNTER - z - b * 0.75                     # Abstand der Schräge von der Mitte
                xa = max(x0, -rand); xe = max(min(x1, rand), xa + 0.002)
                zeile = [(xa + (xe - xa) * j / nx, seite * (D / 2 - 0.025), z) for j in range(nx + 1)]
                gitter.append(zeile if seite < 0 else list(reversed(zeile)))
            lf = (lambda i, j: (i - 2.5) ** 2 + (j - 3) ** 2 < 2.4 + 1.5 * noise.noise(Vector((i * 0.9, j * 0.9, 0.5)))) \
                if loch else None
            bm = flaeche(gitter, 0.0, lf)
            m.teil(bm, "putz", None)
    feld(-2, -1.0 - b * 0.4, b, 1.0 - b * 0.4)
    feld(-1.0 + b * 0.4, -b / 2, b, 1.0 - b * 0.4, loch=kaputt)
    feld(b / 2, 1.0 - b * 0.4, b, 1.0 - b * 0.4)
    feld(1.0 + b * 0.4, 2, b, 1.0 - b * 0.4)
    feld(-1.0, -b / 2, 1.0 + b * 0.4, 2.0 - UNTER)
    if not kaputt:
        feld(b / 2, 1.0, 1.0 + b * 0.4, 2.0 - UNTER)


def treppe_holz(m, kaputt):
    """Innentreppe: 15 Stufen, 1 m breit, von y = 0 (unten) bis y = 4, z 0..3, zwei Wangen."""
    n = 15; lauf = 4.0; hoehe = H
    for s in (-1, 1):
        a = Vector((s * 0.48, -0.1, 0.0)); e = Vector((s * 0.48, lauf, hoehe))
        m.kantholz(a + Vector((0, 0.0, 0.12)), e + Vector((0, 0.0, -0.05)), 0.28, 0.06, "holz", oben=(s, 0, 0))
    for i in range(n):
        y = (i + 0.5) * lauf / n; z = (i + 1) * hoehe / n
        if kaputt and i in (5, 6, 10):
            if i == 6:
                m.brett(0.45, 0.28, 0.04, M((-0.25, y, z - 0.02)), "holz", bruch=1)
            continue
        m.brett(0.92, 0.3, 0.045, M((0, y, z - 0.022)), "holz" if not (kaputt and i % 4 == 0) else "holz_verkohlt")
        if not (kaputt and i in (4, 9)):                  # Setzstufe
            m.brett(0.92, hoehe / n - 0.045, 0.025, M((0, y - lauf / n / 2 + 0.03, z - hoehe / n / 2 - 0.022), (90, 0, 0)), "holz")
    if kaputt:
        m.brett(0.7, 0.28, 0.04, M((0.1, 1.2, 0.02), (0, 0, 30)), "holz", bruch=-1)


def treppe_stein(m, kaputt):
    """Stadttreppe: 5 Stufen à 20 x 40 cm, 2 m breit, massiv. Unterkante z = 0, y 0..2, oben auf z = 1."""
    rnd = m.rnd
    for i in range(5):
        z0 = i * 0.2; y0 = i * 0.4
        # jede Stufe aus zwei Blöcken (1 m), darunter Füllmauerwerk bis zum Boden
        for k, x in enumerate((-0.5, 0.5)):
            if kaputt and (i, k) in ((4, 1), (3, 1)):
                if i == 3:
                    m.teil(klotz(rnd, 0.95, 0.42, 0.2, 0.02, 0.008, 1.0), "stein",
                           M((1.4, 0.4, 0.1), (rnd.uniform(-6, 6), 0, 25)))
                continue
            tief = 2.0 - y0
            m.teil(klotz(rnd, 0.995, tief, 0.2, 0.012, 0.004, 0.5 if kaputt else 0.0), "stein",
                   M((x, y0 + tief / 2, z0 + 0.1)))


MODELLE = {"wand": wand, "wand_fenster": wand_fenster, "wand_tuer": wand_tuer, "tuer": tuer, "boden": boden,
           "decke": decke, "dach": dach, "dach_first": dach_first, "giebel": giebel, "treppe_holz": treppe_holz,
           "treppe_stein": treppe_stein}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
