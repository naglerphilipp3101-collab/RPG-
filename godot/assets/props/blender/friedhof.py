"""Friedhof- und Ruinen-Props (Deko, nicht benutzbar), jedes heil und kaputt.
Aufruf: python friedhof.py -- <zielordner/modelle> [--nur gruft,schaedel] [--vorschau <ordner>]
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y. eisenzaun: 2 m entlang x, Pfosten bei x = -1 (wie zaun)."""
import bpy, bmesh, math, sys, os
import numpy as np
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


# ---------------------------------------------------------------- Schädel als Abstandsfeld (Marching Cubes, braucht scikit-image)

def _sd_ell(P, c, r):
    q = (P - np.array(c)) / np.array(r)
    return (np.linalg.norm(q, axis=-1) - 1.0) * min(r)


def _sd_kapsel(P, a, b, r):
    a = np.array(a); b = np.array(b)
    pa = P - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - r


def _sd_box(P, c, h, rund):
    q = np.abs(P - np.array(c)) - (np.array(h) - rund)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(axis=-1), 0) - rund


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


_SCHAEDEL_CACHE = {}


def _schaedel_netz(kaputt, kiefer):
    """Liefert (Punkte, Dreiecke) des Schädels; Gesicht nach -y, Unterkante bei z = 0."""
    key = (kaputt, kiefer)
    if key in _SCHAEDEL_CACHE:
        return _SCHAEDEL_CACHE[key]
    from skimage.measure import marching_cubes
    raster = 0.0035
    lo = np.array([-0.09, -0.13, -0.14]); hi = np.array([0.09, 0.12, 0.13])
    achsen = [np.arange(lo[k], hi[k], raster) for k in range(3)]
    P = np.stack(np.meshgrid(*achsen, indexing="ij"), axis=-1)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    # Hirnschale (Länge 0,19, Breite 0,14), hinten etwas tiefer, Schläfen leicht eingezogen
    d = _sd_ell(P, (0, 0.002, 0.025), (0.07, 0.095, 0.08))
    d = _smin(d, _sd_ell(P, (0, 0.04, -0.015), (0.056, 0.05, 0.05)), 0.02)
    for sx in (-1, 1):
        d = _smax(d, -_sd_ell(P, (sx * 0.09, -0.035, -0.02), (0.018, 0.035, 0.03)), 0.01)
    # Überaugenwulst und Gesicht (Stirnfuß bis Oberkiefer), unten schmaler
    d = _smin(d, _sd_kapsel(P, (-0.038, -0.086, 0.006), (0.038, -0.086, 0.006), 0.01), 0.014)
    gesicht = _sd_box(P, (0, -0.052, -0.034), (0.046, 0.042, 0.04), 0.016)
    gesicht = gesicht + 0.3 * np.clip(-(z + 0.035), 0, None)
    d = _smin(d, gesicht, 0.012)
    for sx in (-1, 1):
        d = _smin(d, _sd_ell(P, (sx * 0.054, -0.066, -0.038), (0.016, 0.022, 0.014)), 0.01)          # Jochbein
        d = _smin(d, _sd_ell(P, (sx * 0.036, -0.045, -0.058), (0.024, 0.035, 0.026)), 0.012)        # Oberkiefer seitlich
        d = _smin(d, _sd_kapsel(P, (sx * 0.06, -0.05, -0.042), (sx * 0.056, 0.022, -0.038), 0.0065), 0.012)  # Jochbogen bis ans Ohr
    # Oberkiefer mit Zahnbogen
    d = _smin(d, _sd_box(P, (0, -0.064, -0.074), (0.03, 0.024, 0.012), 0.009), 0.01)
    # Unterseite hinter dem Gesicht flach (Schädelbasis)
    d = _smax(d, np.where(y > -0.035, -(z + 0.058), -1.0), 0.01)
    # Höhlen: Augen (groß, eckig-rund), Nase (umgekehrte Birne)
    for sx in (-1, 1):
        auge = _sd_box(P, (sx * 0.032, -0.098, -0.014), (0.021, 0.034, 0.019), 0.013)
        d = _smax(d, -auge, 0.004)
    nase = _sd_ell(P, (0, -0.096, -0.048), (0.011, 0.03, 0.014))
    nase = _smin(nase, _sd_ell(P, (0, -0.096, -0.034), (0.005, 0.03, 0.012)), 0.006)
    d = _smax(d, -nase, 0.003)
    if kaputt:
        d = _smax(d, -_sd_ell(P, (-0.062, 0.02, 0.06), (0.03, 0.035, 0.03)), 0.008)
    # Zähne
    reihen = [(-0.085, 0.0075, 0.031)] + ([(-0.094, 0.0065, 0.028)] if kiefer else [])
    for zr, hz, rb in reihen:
        for k in range(14):
            if kaputt and k in (3, 4, 10):
                continue
            a = math.pi * (0.1 + 0.8 * k / 13)
            c = (rb * math.cos(a), -0.06 - 0.032 * math.sin(a), zr)
            d = np.minimum(d, _sd_ell(P, c, (0.0045, 0.0042, hz)))
    if kiefer:
        # Unterkiefer: Körper als flache Spange, Kinn, aufsteigende Äste bis zum Gelenk unter dem Jochbogen
        kd = _sd_box(P, (0, -0.064, -0.106), (0.03, 0.024, 0.012), 0.009)
        for sx in (-1, 1):
            for t in np.linspace(0, 1, 7):                 # Körper als Reihe flacher Ellipsoide (hochkant)
                c = (sx * (0.024 + 0.032 * t), -0.075 + 0.07 * t, -0.11 + 0.004 * t)
                kd = _smin(kd, _sd_ell(P, c, (0.008, 0.016, 0.015)), 0.008)
            kd = _smin(kd, _sd_box(P, (sx * 0.056, -0.008, -0.08), (0.006, 0.017, 0.032), 0.005), 0.012)   # aufsteigender Ast
        kd = _smin(kd, _sd_ell(P, (0, -0.088, -0.118), (0.017, 0.01, 0.01)), 0.008)
        d = np.minimum(d, kd)
    v, f, _, _ = marching_cubes(d, 0.0, spacing=(raster,) * 3)
    v = v + lo
    # mit Blender auf ein Viertel verringern (Prop, nicht Held)
    me = bpy.data.meshes.new("schaedel_tmp")
    me.from_pydata([tuple(p) for p in v], [], [tuple(t[::-1]) for t in f])
    ob = bpy.data.objects.new("schaedel_tmp", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("v", "DECIMATE"); mod.ratio = 0.22
    deg = bpy.context.evaluated_depsgraph_get()
    em = ob.evaluated_get(deg).to_mesh()
    v = np.array([vv.co[:] for vv in em.vertices])
    f = np.array([tuple(pp.vertices) for pp in em.polygons if len(pp.vertices) == 3])
    ob.evaluated_get(deg).to_mesh_clear()
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    versatz = -v[:, 2].min()
    v[:, 2] += versatz
    _SCHAEDEL_CACHE[key] = (v, f, versatz)
    return _SCHAEDEL_CACHE[key]


def schaedel(m, matrix, kaputt=False, kiefer=True):
    """Menschenschädel (ca. 0,2 m lang) aus einem Abstandsfeld: Hirnschale, Überaugenwulst, Augen- und Nasenhöhlen,
    Jochbeine und -bögen, Zahnreihen, Unterkiefer. Gesicht nach -y, Ursprung am Boden. kaputt: Loch in der Hirnschale."""
    v, f, zv = _schaedel_netz(kaputt, kiefer)
    bm = bmesh.new()
    vs = [bm.verts.new((float(a), float(b), float(c))) for a, b, c in v]
    for tri in f:
        try:
            bm.faces.new((vs[tri[0]], vs[tri[1]], vs[tri[2]]))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m.teil(bm, "knochen", matrix, uv="box")
    # dunkle Tiefe hinten in den Augen- und Nasenhöhlen
    for sx in (-1, 1):
        m.teil(_ellipsoid(0.016, 0.006, 0.014, 2), "asche", matrix @ M((sx * 0.032, -0.066, zv - 0.016)))
    m.teil(_ellipsoid(0.008, 0.005, 0.012, 2), "asche", matrix @ M((0, -0.07, zv - 0.044)))


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
    """Einzelner Schädel mit Unterkiefer (nur heil)."""
    schaedel(m, M())


schaedel_model.nur_heil = True


def knochenhaufen(m, kaputt):
    """Haufen aus Knochen, Rippen und Schädeln auf einem Erdhügel (Monsterhöhle, Gruft). Kaputt: verstreut."""
    if not kaputt:
        R, H = 0.55, 0.24
        huegel = drehkoerper([(0.0, H - 0.04), (R * 0.5, (H - 0.04) * 0.75), (R * 0.85, 0.05), (R, 0.0), (0.0, 0.0)], 18)
        verbiegen(huegel, m.rnd, 0.02, 0.2)
        m.teil(huegel, "erde", None)
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
    m.teil(h, "erde", matrix)


def kreuz(m, matrix=None, kaputt=False):
    """Holzkreuz mit Dächlein, Namensbrett und Kranz; steht 0,15 m tief im Boden. kaputt: Arm abgebrochen, Dach halb weg."""
    G0 = m.G
    m.G = (G0 @ matrix) if (G0 is not None and matrix is not None) else (matrix or G0)
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
    if not kaputt:                                     # Kranz aus trockenen Zweigen über dem Kreuzarm
        ring = [(-0.17 + 0.07 * math.cos(2 * math.pi * k / 14), -0.11, 0.78 + 0.08 * math.sin(2 * math.pi * k / 14)) for k in range(15)]
        m.seil(ring, 0.012, 5, "stroh")
    m.G = G0


def holzkreuz(m, kaputt):
    """Einzelnes Holzkreuz (ohne Hügel, z. B. neben Grabsteinen). Kaputt: umgefallen, Arm abgebrochen."""
    if not kaputt:
        kreuz(m)
    else:
        m.umfallen_start()
        kreuz(m, kaputt=True)
        m.umfallen_ende(250)
        m.G = None
        m.kantholz((0.25, -0.35, 0.03), (0.5, -0.5, 0.03), 0.08, 0.06, mat="holz_alt", bruch=-1)
        ring = [(0.55 + 0.07 * math.cos(2 * math.pi * k / 14), -0.15 + 0.08 * math.sin(2 * math.pi * k / 14), 0.012) for k in range(15)]
        m.seil(ring, 0.012, 5, "stroh")


def grabkreuz(m, kaputt):
    """Holzkreuz mit Grabhügel davor. Kaputt: aufgewühltes Grab mit einem Loch, als wäre jemand herausgekrochen."""
    if not kaputt:
        kreuz(m)
        huegel(m, M((0, -0.95, 0.0)))
        return
    kreuz(m, M(rot=(14, -10, 0)))                      # Kreuz nach hinten weggedrückt
    # Hügel als Höhenfeld: aufgeworfener Wall um eine Grube, die bis auf den Boden reicht
    cy = -0.95
    # Gitter in elliptischen Polarkoordinaten: glatter Rand ohne Treppen
    nr, na = 20, 56
    g = []
    for i in range(nr + 1):
        u = 1.08 * i / nr
        zeile = []
        for j in range(na + 1):
            a = 2 * math.pi * j / na
            x = 0.6 * u * math.cos(a); y = 1.1 * u * math.sin(a)
            e = u
            h = 0.16 * max(0.0, 1 - e * e)
            ec = math.hypot(x / 0.3, (y - 0.05) / 0.5)
            wall = 0.12 * math.exp(-((ec - 1.05) / 0.3) ** 2)
            h = (h + wall) * ec ** 2.5 if ec < 1 else h + wall
            h += 0.015 * noise.noise(Vector((x * 6, y * 6, 3.0)))
            if e > 0.9:
                h *= max(0.0, (1.08 - e) / 0.18)          # Rand läuft am Boden aus
            zeile.append((x, y + cy, max(0.003, h)))
        g.append(zeile)
    m.teil(flaeche(g, 0.02), "erde", None)
    # dunkle Tiefe in der Grube und zerbrochene Sargbretter
    m.teil(drehkoerper([(0.0, 0.004), (0.2, 0.002), (0.0, 0.006)], 16), "holz_verkohlt", M((0, cy + 0.05, 0.0), skal=(1, 1.6, 1)))
    m.brett(0.6, 0.14, 0.02, M((0.1, cy + 0.15, 0.06), (0, -18, 70)), "holz_alt", bruch=1)
    m.brett(0.45, 0.14, 0.02, M((-0.12, cy - 0.2, 0.08), (12, 25, -80)), "holz_alt", bruch=-1)
    m.brett(0.5, 0.14, 0.02, M((0.55, cy - 0.7, 0.012), (0, 0, 35)), "holz_alt", bruch=1)
    # herausgeworfene Erdklumpen
    for k in range(16):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.65, 1.2)
        gr = m.rnd.uniform(0.04, 0.09)
        m.teil(brocken(m.rnd, gr, gr * 0.8, gr * 0.5, rauh=0.35, unterteilung=1), "erde",
               M((d * 0.7 * math.cos(a), cy + d * 1.1 * math.sin(a), gr * 0.2), (0, 0, m.rnd.uniform(0, 360))))


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
    # kaputt: nur die Gittertür ist ausgeschlagen und liegt vor der Gruft, der Bau selbst bleibt heil
    tuer_kaputt, kaputt = kaputt, False
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
    if not tuer_kaputt:
        gitter(M((-tb / 2, -by / 2 + 0.08, z0)))
    else:
        # aus den Angeln gerissen: liegt nach vorne gekippt auf der Stufenkante und dem Boden
        gitter(M((-tb / 2 + 0.1, -by / 2 - 0.12, 0.17), (94.5, 0, -6)))
        for z in (0.35, th - 0.25):                       # abgerissene Angelkloben im Türrahmen
            m.teil(quader(0.04, 0.05, 0.03), "eisen", M((-tb / 2 + 0.02, -by / 2 + 0.08, z0 + z)))
        for k in range(6):                                # abgeplatzte Steinbrocken am Rahmen
            g = m.rnd.uniform(0.03, 0.06)
            m.teil(brocken(m.rnd, g, g * 0.8, g * 0.6, rauh=0.3), "stein",
                   M((m.rnd.uniform(-0.8, 0.8), -by / 2 - m.rnd.uniform(0.6, 1.2), g * 0.35), (0, 0, m.rnd.uniform(0, 360))))


MODELLE = {"gruft": gruft, "grabkreuz": grabkreuz, "holzkreuz": holzkreuz, "eisenzaun": eisenzaun, "saeule_liegend": saeule_liegend,
           "knochenhaufen": knochenhaufen, "schaedel": schaedel_model}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
