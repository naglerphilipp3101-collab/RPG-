"""Friedhof- und Ruinen-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python friedhof.py -- <zielordner/modelle> [--nur gruft,schaedel] [--vorschau <ordner>]
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y. eisenzaun: 2 m entlang x, Pfosten bei x = -1 (wie zaun)."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, klotz, brocken, verbiegen
import props


# ======================================================================== Knochen

def _ellipsoid(rx, ry, rz, unterteilung=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=unterteilung, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
    bm.normal_update()
    return bm


def schaedel(m, matrix, kaputt=False, kiefer=True):
    """Menschenschädel (ca. 0,2 m lang), Gesicht nach -y, Ursprung am Boden unter dem Kiefer.
    Hirnschale, Gesichtsteil, Jochbögen, Zähne und Unterkiefer; Augen- und Nasenhöhlen dunkel (Material asche)."""
    unten = 0.106 if (kiefer and not kaputt) else 0.085
    G = matrix @ M((0, 0, unten))
    augen = [Vector((sx * 0.03, -0.083, 0.004)) for sx in (-1, 1)]
    nase = Vector((0.0, -0.088, -0.03))
    loch = Vector((-0.058, 0.015, 0.06))

    def hoehlen(bm):
        for v in bm.verts:
            for a in augen:
                d = Vector(((v.co.x - a.x) / 0.024, (v.co.y - a.y) / 0.03, (v.co.z - a.z) / 0.021)).length
                if d < 1:
                    v.co.y += 0.022 * (1 - d * d)
            d = Vector(((v.co.x - nase.x) / 0.011, (v.co.y - nase.y) / 0.03, (v.co.z - nase.z) / 0.017)).length
            if d < 1:
                v.co.y += 0.016 * (1 - d * d)
            if kaputt:
                d = (v.co - loch).length
                if d < 0.03:
                    v.co -= (v.co - Vector((0, 0.01, 0.02))).normalized() * 0.03 * (1 - (d / 0.03) ** 1.5)
        bm.normal_update()

    # Hirnschale
    hirn = _ellipsoid(0.07, 0.093, 0.078, 4)
    for v in hirn.verts:
        v.co += Vector((0, 0.012, 0.03))
        if v.co.z < -0.035:                              # Schädelbasis flach
            v.co.z = -0.035 - (v.co.z + 0.035) * 0.3
        if v.co.y < -0.05:                               # Stirn steiler
            v.co.y = -0.05 + (v.co.y + 0.05) * 0.75
    hoehlen(hirn)
    m.teil(hirn, "knochen", G, uv="box")
    # Gesichtsteil (Oberkiefer), unten schmaler
    ges = quader(0.084, 0.05, 0.062, 6, 4, 6, fase=0.022)
    for v in ges.verts:
        v.co.x *= 0.72 + 0.28 * (v.co.z + 0.031) / 0.062
    ges.normal_update()
    bmesh.ops.translate(ges, verts=ges.verts, vec=(0, -0.066, -0.043))
    verbiegen(ges, m.rnd, 0.002, 0.03)
    hoehlen(ges)
    m.teil(ges, "knochen", G, uv="box")
    # dunkle Höhlen
    for a in augen:
        m.teil(_ellipsoid(0.021, 0.008, 0.019, 2), "asche", G @ M(a + Vector((0, 0.016, 0))))
    m.teil(_ellipsoid(0.009, 0.006, 0.015, 2), "asche", G @ M(nase + Vector((0, 0.012, 0))))
    if kaputt:
        m.teil(_ellipsoid(0.02, 0.02, 0.02, 2), "asche", G @ M(loch + Vector((0.022, 0.0, -0.015))))
    # Jochbögen
    for sx in (-1, 1):
        m.teil(rohr([G @ Vector(q) for q in ((sx * 0.04, -0.078, -0.012), (sx * 0.057, -0.05, -0.016), (sx * 0.06, -0.02, -0.022),
                                         (sx * 0.056, 0.0, -0.026))], 0.0065, 6), "knochen", None, uv=None)
    # obere Zahnreihe
    for k in range(10):
        if kaputt and k in (2, 3, 7):
            continue
        a = math.pi * (0.12 + 0.76 * k / 9)
        q = Vector((0.026 * math.cos(a), -0.06 - 0.028 * math.sin(a), -0.077))
        m.teil(quader(0.008, 0.007, 0.014, fase=0.002), "knochen", G @ M(q, (0, 0, math.degrees(a) - 90)))
    if kiefer:
        km = G if not kaputt else matrix @ M((0.16, -0.08, 0.0), (0, 0, 35)) @ M((0, 0, 0.107))
        bahn = [(-0.056, -0.004, -0.032), (-0.056, -0.01, -0.082), (-0.045, -0.045, -0.092), (-0.026, -0.068, -0.095),
                (0.0, -0.076, -0.097)]
        bahn = bahn + [(-x, y, z) for (x, y, z) in reversed(bahn[:-1])]
        unterkiefer = rohr(bahn, 0.0095, 8)
        for v in unterkiefer.verts:                      # hochkant gequetscht
            mz = -0.092
            if v.co.z < -0.072:
                v.co.z = mz + (v.co.z - mz) * 1.5
        unterkiefer.normal_update()
        m.teil(unterkiefer, "knochen", km, uv=None)
        for k in range(10):
            if kaputt and k in (0, 5):
                continue
            a = math.pi * (0.15 + 0.7 * k / 9)
            q = Vector((0.024 * math.cos(a), -0.06 - 0.016 * math.sin(a), -0.085))
            m.teil(quader(0.007, 0.006, 0.012, fase=0.002), "knochen", km @ M(q, (0, 0, math.degrees(a) - 90)))


def langknochen(m, matrix, l=0.4, r=0.016, gebrochen=False):
    """Röhrenknochen entlang z (0 … l) mit verdickten Gelenkenden; gebrochen: oberes Ende splittrig abgebrochen."""
    prof = [(0.0, 0.0), (r * 1.6, 0.004), (r * 1.9, l * 0.05), (r * 1.1, l * 0.13), (r, l * 0.5), (r * 1.1, l * 0.87),
            (r * 1.9, l * 0.95), (r * 1.5, l * 0.995), (0.0, l)]
    if gebrochen:
        prof = prof[:5] + [(r * 1.05, l * 0.62), (0.0, l * 0.6)]
    bm = drehkoerper(prof, 8)
    if gebrochen:
        for v in bm.verts:
            if v.co.z > l * 0.55:
                v.co.z -= m.rnd.uniform(0, l * 0.06)
    verbiegen(bm, m.rnd, r * 0.15, 0.1)
    m.teil(bm, "knochen", matrix, uv="zylz", r=r)


def rippe(m, matrix, l=0.25):
    pts = [(l * 0.5 * math.sin(math.pi * k / 10 * 0.9), l * 0.35 * (1 - math.cos(math.pi * k / 10 * 0.9)), 0.0) for k in range(11)]
    m.teil(rohr(pts, 0.006, 5), "knochen", matrix, uv=None)


def schaedel_model(m, kaputt):
    """Einzelner Schädel; kaputt: eingeschlagen, Kiefer liegt daneben."""
    schaedel(m, M(), kaputt)


def knochenhaufen(m, kaputt):
    """Haufen aus Knochen, Rippen und Schädeln auf einem Erdhügel (Monsterhöhle, Gruft). Kaputt: verstreut."""
    if not kaputt:
        R, H = 0.55, 0.24
        huegel = drehkoerper([(0.0, H - 0.04), (R * 0.5, (H - 0.04) * 0.75), (R * 0.85, 0.05), (R, 0.0), (0.0, 0.0)], 18)
        verbiegen(huegel, m.rnd, 0.02, 0.2)
        m.teil(huegel, "asche", None)
        hoehe = lambda x, y: max(0.0, H * (1 - (x * x + y * y) / (R * R)))
        for k in range(26):
            a = m.rnd.uniform(0, 2 * math.pi); d = R * math.sqrt(m.rnd.random()) * 0.9
            x, y = d * math.cos(a), d * math.sin(a)
            l = m.rnd.uniform(0.25, 0.45); r = l * 0.04
            neig = math.degrees(math.atan(2 * H * d / (R * R))) * (1 if m.rnd.random() < 0.5 else -1) * 0.6
            langknochen(m, M((x, y, hoehe(x, y) + r * 0.8), (90 + neig, 0, m.rnd.uniform(0, 360))) @ M((0, 0, -l / 2)), l, r,
                        gebrochen=k % 5 == 0)
        for k in range(8):
            a = m.rnd.uniform(0, 2 * math.pi); d = R * 0.7 * math.sqrt(m.rnd.random())
            x, y = d * math.cos(a), d * math.sin(a)
            rippe(m, M((x, y, hoehe(x, y) + 0.01), (m.rnd.uniform(-20, 20), 0, m.rnd.uniform(0, 360))))
        schaedel(m, M((0.05, -0.05, H - 0.03), (8, 0, 15)))
        schaedel(m, M((-0.28, -0.22, hoehe(-0.28, -0.22) - 0.02), (12, -10, -30)), kiefer=False)
        schaedel(m, M((0.3, 0.2, hoehe(0.3, 0.2) - 0.02), (0, 15, 160)), kiefer=False)
    else:
        for k in range(18):
            a = m.rnd.uniform(0, 2 * math.pi); d = 1.0 * math.sqrt(m.rnd.random())
            l = m.rnd.uniform(0.2, 0.42); r = l * 0.04
            langknochen(m, M((d * math.cos(a), d * math.sin(a), r * 1.6), (90, 0, m.rnd.uniform(0, 360))) @ M((0, 0, -l / 2)), l, r,
                        gebrochen=k % 2 == 0)
        for k in range(6):
            a = m.rnd.uniform(0, 2 * math.pi); d = 0.8 * math.sqrt(m.rnd.random())
            rippe(m, M((d * math.cos(a), d * math.sin(a), 0.006), (0, 0, m.rnd.uniform(0, 360))))
        schaedel(m, M((0.1, -0.2, 0.0), (0, 0, 20)), kaputt=True)
        for k in range(10):                               # Splitter
            a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.1, 0.9)
            m.teil(brocken(m.rnd, 0.025, 0.01, 0.006, rauh=0.4, unterteilung=1), "knochen",
                   M((d * math.cos(a), d * math.sin(a), 0.005), (0, 0, m.rnd.uniform(0, 360))))


# ======================================================================== Gräber

def huegel(m, matrix, laenge=1.8, breite=0.9, hoch=0.12):
    h = drehkoerper([(0.0, hoch), (0.25, hoch * 0.85), (0.4, hoch * 0.4), (0.48, 0.0), (0.0, 0.0)], 16)
    for v in h.verts:
        v.co.x *= breite / 0.96; v.co.y *= laenge / 0.96
    verbiegen(h, m.rnd, 0.02, 0.2)
    m.teil(h, "asche", matrix)


def grabkreuz(m, kaputt):
    """Holzkreuz mit Dächlein und Namensbrett, davor der Grabhügel."""
    G0 = m.G
    if kaputt:
        m.G = M(rot=(-12, 16, 0))                     # schief eingesunken, kippt nach vorne rechts
    m.kantholz((0, 0, -0.15), (0, 0, 1.15), 0.09, 0.07, oben=(0, -1, 0), mat="holz_alt")
    if not kaputt:
        m.kantholz((-0.3, -0.07, 0.83), (0.3, -0.07, 0.83), 0.08, 0.06, oben=(0, -1, 0), mat="holz_alt")
    else:
        m.kantholz((-0.3, -0.07, 0.83), (0.05, -0.07, 0.83), 0.08, 0.06, oben=(0, -1, 0), mat="holz_alt", bruch=1)
    for s in (-1, 1):                                  # Dächlein
        if kaputt and s > 0:
            continue
        m.brett(0.16, 0.16, 0.015, M((s * 0.06, 0.0, 1.17), (0, s * 35, 0)), "holz_alt", biegen=0.002)
    m.brett(0.24, 0.11, 0.015, M((0.0, -0.11, 0.66), (90, 0, 2)), "holz_alt")
    for x in (-0.09, 0.09):
        m.teil(drehkoerper([(0.0, 0.0), (0.007, 0.0), (0.006, 0.004), (0.0, 0.005)], 6), "eisen", M((x, -0.118, 0.66), (90, 0, 0)))
    # Kranz aus trockenen Zweigen über dem Kreuzarm
    if not kaputt:
        ring = [(-0.17 + 0.07 * math.cos(2 * math.pi * k / 14), -0.11, 0.78 + 0.08 * math.sin(2 * math.pi * k / 14)) for k in range(15)]
        m.seil(ring, 0.012, 5, "stroh")
    m.G = G0
    if kaputt:
        # abgebrochener Arm liegt auf dem Hügel, Kranz daneben
        m.kantholz((0.15, -0.55, 0.11), (0.4, -0.75, 0.08), 0.08, 0.06, mat="holz_alt", bruch=-1)
        ring = [(0.4 + 0.07 * math.cos(2 * math.pi * k / 14), -1.1 + 0.08 * math.sin(2 * math.pi * k / 14), 0.012) for k in range(15)]
        m.seil(ring, 0.012, 5, "stroh")
        huegel(m, M((0, -0.95, 0.0), skal=(1, 1, 0.5)))
    else:
        huegel(m, M((0, -0.95, 0.0)))


def eisenzaun(m, kaputt):
    """Schmiedeeiserner Zaun 2 m auf einem Steinsockel, Stäbe mit Speerspitzen, Pfosten bei x = -1."""
    m.teil(klotz(m.rnd, 2.0, 0.28, 0.25, fase=0.02, rauh=0.006, abgeschlagen=0.6 if kaputt else 0.1), "stein", M((0, 0, 0.125)))
    # Pfosten mit Kugel
    m.teil(quader(0.06, 0.06, 1.3, 1, 1, 4, fase=0.006), "eisen", M((-1.0, 0, 0.25 + 0.65)))
    m.teil(drehkoerper([(0.0, 0.0), (0.04, 0.0), (0.045, 0.04), (0.035, 0.075), (0.0, 0.09)], 10), "eisen", M((-1.0, 0, 1.55)))
    # Querstäbe
    m.teil(quader(2.0, 0.015, 0.03, 8, 1, 1), "eisen", M((0.0, 0, 0.4)))
    if not kaputt:
        m.teil(quader(2.0, 0.015, 0.03, 8, 1, 1), "eisen", M((0.0, 0, 1.25)))
    else:
        m.teil(quader(1.3, 0.015, 0.03, 6, 1, 1), "eisen", M((-0.35, 0, 1.25)))
        # abgerissenes Ende hängt herunter
        m.seil([(0.32, 0.0, 1.25), (0.5, -0.03, 1.1), (0.62, -0.06, 0.85), (0.68, -0.08, 0.62)], 0.012, 4, "eisen")
    spitze = drehkoerper([(0.0, 0.0), (0.012, 0.0), (0.022, 0.025), (0.012, 0.055), (0.0, 0.075)], 4)
    n = 15
    for i in range(n):
        x = -0.93 + 1.86 * i / (n - 1)
        if kaputt and i in (4, 11, 12):
            continue
        if kaputt and i in (7, 9):
            # verbogen: unten gerade, oben nach vorne gezogen
            pts = [(x, 0, 0.25), (x, 0, 0.42), (x + 0.02, -0.06, 0.75), (x + 0.06, -0.22, 1.0), (x + 0.1, -0.38, 1.15)]
            m.seil(pts, 0.01, 6, "eisen")
            m.teil(spitze.copy(), "eisen", _richtung(Vector(pts[-2]), Vector(pts[-1])))
            continue
        top = 1.38 + (0.06 if i % 2 == 0 else 0.0)
        m.stab((x, 0, 0.25), (x, 0, top), 0.01, "eisen", biegen=0)
        m.teil(spitze.copy(), "eisen", M((x, 0, top)))
        if i < n - 1 and not (kaputt and i >= 6):
            # Zierringe zwischen den Stäben unter dem oberen Querstab
            xm = x + 1.86 / (n - 1) / 2
            ring = [(xm + 0.05 * math.cos(2 * math.pi * k / 12), 0.0, 1.13 + 0.05 * math.sin(2 * math.pi * k / 12)) for k in range(13)]
            m.seil(ring, 0.006, 4, "eisen")
    if kaputt:
        for (x, y, rz) in ((0.3, -0.45, 20), (0.8, -0.35, -50)):
            m.stab((x, y, 0.012), (x + 1.1 * math.cos(math.radians(rz)), y + 1.1 * math.sin(math.radians(rz)), 0.012), 0.01, "eisen",
                   biegen=0.01)


def _richtung(a, b):
    """Matrix: Ursprung in b, lokale z-Achse in Richtung a -> b."""
    d = (b - a).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    return Matrix.Translation(b) @ q.to_matrix().to_4x4()


# ======================================================================== Säulen

def trommel(m, r0, r1, h, gebrochen=False, unten_gebrochen=False):
    seg = 24
    bm = bmesh.new()
    ringe = []
    for i in range(5):
        t = i / 4; rr = r0 + (r1 - r0) * t
        ringe.append([bm.verts.new((rr * (1 - 0.035 * (k % 2)) * math.cos(2 * math.pi * k / seg),
                                    rr * (1 - 0.035 * (k % 2)) * math.sin(2 * math.pi * k / seg), h * t)) for k in range(seg)])
    for a, b in zip(ringe, ringe[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bm.faces.new(list(reversed(ringe[0]))); bm.faces.new(ringe[-1])
    o = Vector([m.rnd.uniform(-40, 40) for _ in range(3)])
    if gebrochen:
        for v in ringe[-1]:
            v.co.z += -0.25 * h * (0.5 + 0.5 * noise.noise(v.co * 3 + o)) - 0.15 * h * (v.co.x / r0)
    if unten_gebrochen:
        for v in ringe[0]:
            v.co.z += 0.2 * h * (0.5 + 0.5 * noise.noise(v.co * 3 + o + Vector((5, 0, 0))))
    verbiegen(bm, m.rnd, 0.008, 0.2)
    bm.normal_update()
    return bm


def saeule_liegend(m, kaputt):
    """Umgestürzte Säule: Stumpf auf der Plinthe, die Trommeln liegen in einer Reihe davor, am Ende das Kapitell.
    Kaputt: zerschlagen, Trommeln gebrochen, verstreut und eingesunken, mehr Schutt."""
    r = 0.26
    m.teil(klotz(m.rnd, 0.78, 0.78, 0.26, 0.012, 0.008, 0.6 if kaputt else 0.25), "stein", M((0, 0, 0.13)))
    stumpf = 0.55 if not kaputt else 0.3
    m.teil(trommel(m, r, r * 0.995, stumpf, gebrochen=True), "stein", M((0, 0, 0.26)), uv="zylz", r=r)
    # liegende Trommeln: Achse entlang x
    if not kaputt:
        lagen = [(0.75, 0.05, 0.8, 4, False), (1.6, 0.1, 0.8, -3, False), (2.45, 0.08, 0.6, 6, True)]
        for x, y, h, gier, br in lagen:
            m.teil(trommel(m, r, r * 0.98, h, gebrochen=br), "stein", M((x, y, r * 0.97), (0, 90, gier)) @ M((0, 0, -0.02)),
                   uv="zylz", r=r)
        kap = klotz(m.rnd, 0.7, 0.7, 0.18, 0.012, 0.008, 0.3)
        m.teil(kap, "stein", M((3.45, 0.25, 0.09), (0, 0, 18)))
        m.teil(drehkoerper([(r, 0), (r * 1.2, 0.08), (r * 1.25, 0.12)], 24, False, True), "stein",
               M((3.45, 0.25, 0.18), (0, 0, 18)), uv="zylz", r=r)
    else:
        lagen = [(0.85, -0.2, 0.55, 25, 0.88), (1.55, 0.35, 0.7, -40, 0.8), (2.3, -0.35, 0.45, 70, 0.9), (2.9, 0.4, 0.5, 10, 0.75)]
        for x, y, h, gier, tief in lagen:
            m.teil(trommel(m, r, r * 0.98, h, gebrochen=True, unten_gebrochen=True), "stein",
                   M((x, y, r * tief), (0, 90, gier)) @ M((0, 0, -h / 2)), uv="zylz", r=r)
        kap = klotz(m.rnd, 0.7, 0.7, 0.18, 0.012, 0.008, 0.9)
        m.teil(kap, "stein", M((3.5, -0.1, 0.07), (8, 4, 40)))
        for k in range(12):
            x = m.rnd.uniform(0.3, 3.5); y = m.rnd.uniform(-0.7, 0.7)
            g = m.rnd.uniform(0.05, 0.14)
            m.teil(brocken(m.rnd, g, g * 0.8, g * 0.6, rauh=0.3), "stein", M((x, y, g * 0.35), (0, 0, m.rnd.uniform(0, 360))))


# ======================================================================== Gruft

def gruft(m, kaputt):
    """Kleine Gruft 2,4 x 3 m aus Stein: Sockel, Stufe, Eckpfeiler, Satteldach, Gittertür, Inschrifttafel und Kreuz."""
    bx, by = 2.4, 3.0
    sockel = 0.3
    wand_h = 2.2
    d = 0.3
    ab = 0.5 if kaputt else 0.1
    m.teil(klotz(m.rnd, bx + 0.4, by + 0.4, sockel, 0.02, 0.008, ab), "stein", M((0, 0.1, sockel / 2)))
    m.teil(klotz(m.rnd, 1.4, 0.45, 0.15, 0.015, 0.006, ab), "stein", M((0, -by / 2 - 0.3, 0.075)))
    z0 = sockel
    zm = z0 + wand_h / 2
    # Rückwand, Seitenwände (rechte im kaputten Zustand oben eingebrochen)
    m.teil(quader(bx, d, wand_h, 4, 1, 4, fase=0.01), "stein", M((0, by / 2 - d / 2, zm)))
    for s in (-1, 1):
        bm = quader(d, by - 2 * d, wand_h, 1, 6, 4, fase=0.01)
        if kaputt and s > 0:
            for v in bm.verts:
                if v.co.z > 0:
                    v.co.z -= (0.5 + 0.35 * math.sin(v.co.y * 2.3 + 1)) * max(0.0, 0.5 + v.co.y / (by - 2 * d))
        m.teil(bm, "stein", M((s * (bx / 2 - d / 2), 0, zm)))
    # Vorderwand mit Türöffnung 0,9 x 1,9 m
    tb, th = 0.9, 1.9
    seite = (bx - tb) / 2
    for s in (-1, 1):
        m.teil(quader(seite, d, wand_h, 2, 1, 4, fase=0.01), "stein", M((s * (tb / 2 + seite / 2), -by / 2 + d / 2, zm)))
    m.teil(quader(tb, d, wand_h - th, 2, 1, 1, fase=0.01), "stein", M((0, -by / 2 + d / 2, z0 + th + (wand_h - th) / 2)))
    m.teil(klotz(m.rnd, tb + 0.3, d + 0.08, 0.16, 0.015, 0.006, ab), "stein", M((0, -by / 2 + d / 2 - 0.02, z0 + th + 0.08)))
    # Inschrifttafel und Eckpfeiler
    m.teil(quader(0.7, 0.04, 0.22, fase=0.01), "stein", M((0, -by / 2 - 0.02, z0 + th + 0.33)))
    for x in (-0.25, -0.1, 0.05, 0.2):
        m.teil(quader(0.1, 0.01, 0.025), "asche", M((x, -by / 2 - 0.042, z0 + th + 0.36)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.teil(klotz(m.rnd, 0.4, 0.4, wand_h + 0.1, 0.015, 0.006, ab), "stein",
                   M((sx * (bx / 2 - 0.15), sy * (by / 2 - 0.15) + (0.0 if sy > 0 else -0.05), z0 + (wand_h + 0.1) / 2)))
    # Gesims (rechts im kaputten Zustand abgestürzt)
    zg = z0 + wand_h + 0.1
    if not kaputt:
        m.teil(klotz(m.rnd, bx + 0.3, by + 0.3, 0.15, 0.015, 0.006, 0.1), "stein", M((0, 0, zg + 0.075)))
    else:
        m.teil(klotz(m.rnd, bx / 2 + 0.15, by + 0.3, 0.15, 0.015, 0.006, 0.6), "stein", M((-bx / 4 - 0.075, 0, zg + 0.075)))
    # Giebel vorne und hinten
    zb = zg + 0.15
    gh = 0.75
    for sy in (-1, 1):
        bm = quader(bx + 0.2, 0.25, gh, 2, 1, 1)
        for v in bm.verts:
            if v.co.z > 0 and abs(v.co.x) > 0.1:
                v.co.z = -gh / 2
        if kaputt and sy < 0:
            for v in bm.verts:
                if v.co.x > 0.05 and v.co.z > -gh / 2 + 0.01:
                    v.co.z -= 0.4
        m.teil(bm, "stein", M((0, sy * (by / 2 + 0.02), zb + gh / 2)))
    # Dachplatten (rechte Platte im kaputten Zustand eingestürzt)
    lang = math.hypot(bx / 2 + 0.1, gh) + 0.2
    w = math.degrees(math.atan2(gh, bx / 2 + 0.1))
    for s in (-1, 1):
        if kaputt and s > 0:
            continue
        mx = s * (bx / 2 + 0.1) / 2 - s * 0.06 * math.sin(math.radians(w))
        mz = zb + gh / 2 + 0.06 * math.cos(math.radians(w))
        m.teil(klotz(m.rnd, lang, by + 0.5, 0.12, 0.012, 0.006, ab), "stein", M((mx, 0, mz), (0, s * w, 0)))
    # Kreuz auf dem vorderen First
    if not kaputt:
        m.teil(quader(0.1, 0.1, 0.55, fase=0.01), "stein", M((0, -by / 2 - 0.05, zb + gh + 0.27)))
        m.teil(quader(0.34, 0.1, 0.1, fase=0.01), "stein", M((0, -by / 2 - 0.05, zb + gh + 0.38)))
    # Gittertür
    def gitter(matrix):
        for z in (0.1, th / 2, th - 0.1):
            m.teil(quader(tb - 0.04, 0.02, 0.03), "eisen", matrix @ M((tb / 2, 0, z)))
        for k in range(8):
            x = 0.05 + (tb - 0.1) * k / 7
            m.stab(matrix @ Vector((x, 0, 0.02)), matrix @ Vector((x, 0, th - 0.02)), 0.01, "eisen", biegen=0)
        m.teil(quader(0.03, 0.03, th - 0.02), "eisen", matrix @ M((0.015, 0, th / 2)))
    if not kaputt:
        gitter(M((-tb / 2, -by / 2 + 0.08, z0)))
    else:
        # Tür liegt vor der Gruft auf Stufe und Boden
        gitter(M((-0.6, -by / 2 - 0.5, 0.17), (-84, 0, 10)))
        # Trümmer des Dachs und Gesims rechts neben der Gruft
        for k, (x, y, g) in enumerate(((1.65, -0.6, 0.35), (1.7, 0.5, 0.3), (1.95, 0.0, 0.22), (1.55, 1.3, 0.28), (2.0, -1.2, 0.2))):
            m.teil(klotz(m.rnd, g * 2.2, g * 1.6, g, 0.012, 0.006, 0.9), "stein", M((x, y, g / 2 - 0.02), (m.rnd.uniform(-8, 8), 0, m.rnd.uniform(0, 90))))
        for k in range(14):
            x = m.rnd.uniform(1.4, 2.4); y = m.rnd.uniform(-1.6, 1.6); g = m.rnd.uniform(0.05, 0.12)
            m.teil(brocken(m.rnd, g, g * 0.8, g * 0.6, rauh=0.3), "stein", M((x, y, g * 0.35), (0, 0, m.rnd.uniform(0, 360))))
        # schräg ins Innere gestürzte Dachplatte
        m.teil(klotz(m.rnd, lang * 0.8, by * 0.6, 0.12, 0.012, 0.006, 0.9), "stein",
               M((0.55, 0.2, z0 + 0.9), (0, -38, 6)))


MODELLE = {"gruft": gruft, "grabkreuz": grabkreuz, "eisenzaun": eisenzaun, "saeule_liegend": saeule_liegend,
           "knochenhaufen": knochenhaufen, "schaedel": schaedel_model}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
