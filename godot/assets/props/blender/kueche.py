"""Küchen- und Vorrats-Props (Deko, nicht benutzbar), jedes heil und kaputt (kaputt = angefressen, geplündert, verdorben).
Aufruf: python kueche.py -- <zielordner/modelle> [--nur brotlaib,mehlsack] [--vorschau <ordner>]

  brotlaib         Schneidbrett mit rundem Laib, langem Brot und Messer
  kaeselaib        Käserad und kleiner Laib auf einem Holzbrett
  wurststange      Stange mit Würsten, an zwei Seilen unter der Decke (Ursprung = Deckenhaken, hängt nach unten)
  kraeuterbuendel  Wandleiste mit Holzpflöcken, Kräuter, Lavendel und Knoblauch kopfüber (Ursprung auf der Wand, ragt nach -y)
  mehlsack         stehender und liegender Mehlsack
  gemuesekorb      Weidenkorb mit Kohl, Zwiebeln und Möhren
Boden bei z = 0, Mitte im Ursprung, Vorderseite nach -y."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import M, quader, rundholz, drehkoerper, rohr, flaeche, brocken, verbiegen, ausrichten
import props
from behaelter import sack, korb
import deko


# ======================================================================== Hilfen

def ellipsoid(rx, ry, rz, unterteilung=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=unterteilung, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
    bm.normal_update()
    return bm


def drehstueck(m, profil, a0, a1, mat, innen, matrix, seg=None, verformen=None):
    """Angeschnittener Drehkörper (Laib, Käserad) von Winkel a0 bis a1 (Grad) mit zwei Schnittflächen im Material innen.
    Das Profil beginnt und endet auf der Achse (r = 0). verformen(bm) wird vor dem Einbauen auf den Mantel angewendet."""
    seg = seg or max(4, int((a1 - a0) / 10))
    bm = drehkoerper(profil, seg, winkel=(a0, a1))
    if verformen:
        verformen(bm)
    m.teil(bm, mat, matrix, uv="zylz", r=max(r for r, z in profil))
    for a, s in ((math.radians(a0), 1), (math.radians(a1), -1)):
        f = bmesh.new()
        vs = [f.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profil]
        flaeche_ = f.faces.new(vs)
        f.normal_update()
        aussen = Vector((s * math.sin(a), -s * math.cos(a), 0.0))
        if flaeche_.normal.dot(aussen) < 0:
            bmesh.ops.reverse_faces(f, faces=[flaeche_])
        m.teil(f, innen, matrix)


def flecken(m, matrix, profil, n, a0=0.0, a1=360.0, mat="schimmel", gross=0.012):
    """Schimmelflecken auf der Oberfläche eines Drehkörpers (Profil wie beim Bau)."""
    for k in range(n):
        i = m.rnd.randint(2, len(profil) - 3)
        r, z = profil[i]
        a = math.radians(m.rnd.uniform(a0 + 15, a1 - 15))
        p = Vector((r * math.cos(a), r * math.sin(a), z))
        # Flächennormale aus den Nachbarpunkten des Profils
        dr = profil[i + 1][0] - profil[i - 1][0]; dz = profil[i + 1][1] - profil[i - 1][1]
        nrm = Vector((dz * math.cos(a), dz * math.sin(a), -dr)).normalized()
        g = gross * m.rnd.uniform(0.6, 1.3)
        m.teil(ellipsoid(g * 0.25, g, g * 0.8, 1), mat, matrix @ ausrichten(p - nrm * 0.001, p + nrm * 0.001))


def kruemel(m, matrix, n, weite, mats=("brot", "brot_innen"), gross=0.006):
    for k in range(n):
        a = m.rnd.uniform(0, 2 * math.pi); d = m.rnd.uniform(0.0, weite)
        g = gross * m.rnd.uniform(0.5, 1.4)
        m.teil(brocken(m.rnd, g, g * 0.8, g * 0.6, rauh=0.3, unterteilung=1), mats[k % len(mats)],
               matrix @ M((d * math.cos(a), d * math.sin(a), g * 0.5), (0, 0, m.rnd.uniform(0, 360))))


def haufen(m, mitte, rx, ry, hoch, mat, rnd, rand_rauh=0.25, nr=12, na=40):
    """Flacher Schütthaufen (Mehl, Erde) auf dem Boden: Höhenfeld auf einem elliptischen Polargitter mit ausfransendem Rand."""
    import mathutils.noise as noise
    o = Vector([rnd.uniform(-40, 40) for _ in range(3)])
    g = []
    for i in range(nr + 1):
        u = i / nr
        zeile = []
        for j in range(na + 1):
            a = 2 * math.pi * j / na
            rand = 1 + rand_rauh * noise.noise(Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, 0)) + o)
            x = mitte[0] + rx * u * rand * math.cos(a); y = mitte[1] + ry * u * rand * math.sin(a)
            z = hoch * (1 - u * u) ** 1.6 * (1 + 0.15 * noise.noise(Vector((x * 18, y * 18, 0)) + o))
            zeile.append((x, y, max(0.0005, z)))
        g.append(zeile)
    bm = flaeche(g, 0.0)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    m.teil(bm, mat, None)


def schneidbrett(m, matrix, lx=0.56, ly=0.32, d=0.025):
    m.brett(lx, ly, d, matrix @ M((0, 0, d / 2)), "holz", biegen=0, fase=0.006)
    # Griff mit Loch an einem Ende
    m.teil(drehkoerper([(0.0, 0.0), (0.045, 0.0), (0.045, d), (0.0, d)], 14), "holz", matrix @ M((lx / 2, 0, 0)), uv="zylz", r=0.045)
    m.teil(drehkoerper([(0.0, d - 0.001), (0.012, d - 0.001), (0.012, d + 0.0005), (0.0, d + 0.0005)], 10), "holz_verkohlt",
           matrix @ M((lx / 2 + 0.02, 0, 0)), uv=None)


def messer(m, matrix):
    deko.klinge(m, matrix @ M((0, 0, 0.003), (0, 90, 0)), 0.16, 0.026)
    m.stab(tuple(matrix @ Vector((-0.012, 0, 0.007))), tuple(matrix @ Vector((-0.11, 0, 0.007))), 0.009, "holz", biegen=0)


# ======================================================================== Brot

BROT_RUND = [(0.0, 0.0), (0.085, 0.0), (0.104, 0.012), (0.11, 0.03), (0.104, 0.052), (0.085, 0.072), (0.055, 0.087),
             (0.025, 0.093), (0.0, 0.094)]
BROT_LANG = [(0.0, 0.0), (0.045, 0.0), (0.055, 0.012), (0.058, 0.03), (0.05, 0.05), (0.032, 0.063), (0.0, 0.068)]


def _kreuzschnitt(bm, rnd, hoch=0.035, tief=0.007):
    """Eingeschnittenes Kreuz auf dem Laib: Punkte auf den Meridianen 0/90/180/270° einsinken lassen."""
    for v in bm.verts:
        a = math.degrees(math.atan2(v.co.y, v.co.x)) % 90
        if (a < 2 or a > 88) and v.co.z > hoch and math.hypot(v.co.x, v.co.y) > 0.004:
            v.co.x *= 0.93; v.co.y *= 0.93; v.co.z -= tief
    verbiegen(bm, rnd, 0.004, 0.06)


def _langbrot(bm, rnd, streck=2.3):
    for v in bm.verts:
        v.co.x *= streck
        # drei schräge Einschnitte
        u = v.co.x * 0.87 + v.co.y * 0.5
        if v.co.z > 0.035 and any(abs(u - c) < 0.012 for c in (-0.07, 0.0, 0.07)):
            v.co.z -= 0.006
    verbiegen(bm, rnd, 0.004, 0.06)


def brotlaib(m, kaputt):
    schneidbrett(m, M((0, 0, 0)))
    d = 0.025
    if not kaputt:
        bm = drehkoerper(BROT_RUND, 40)
        _kreuzschnitt(bm, m.rnd)
        m.teil(bm, "brot", M((-0.14, 0.0, d)), uv="zylz", r=0.11)
        bm = drehkoerper(BROT_LANG, 32)
        _langbrot(bm, m.rnd)
        m.teil(bm, "brot", M((0.13, 0.06, d), (0, 0, 15)), uv="zylz", r=0.06)
        messer(m, M((0.1, -0.12, d), (0, 0, 5)))
        return
    # angefressen: halber Laib mit Schnittfläche nach vorn, Schimmel, Krümel; das Langbrot liegt angebissen am Boden
    drehstueck(m, BROT_RUND, 0, 180, "brot", "brot_innen", M((-0.14, 0.03, d)), seg=20,
               verformen=lambda bm: _kreuzschnitt(bm, m.rnd))
    flecken(m, M((-0.14, 0.03, d)), BROT_RUND, 5, 0, 180)
    kruemel(m, M((-0.1, -0.05, d)), 14, 0.08)
    kruemel(m, M((0.06, 0.04, d)), 6, 0.05)
    # Rest des Langbrots (Schnittfläche bei x = 0, nach -x)
    prof = BROT_LANG
    teil = M((0.38, 0.3, 0.0), (0, 0, 200))
    drehstueck(m, prof, -90, 90, "brot", "brot_innen", teil @ M(skal=(2.3, 1, 1)), seg=16,
               verformen=lambda bm: verbiegen(bm, m.rnd, 0.003, 0.05))
    kruemel(m, M((0.3, 0.28, 0.0)), 8, 0.06)
    messer(m, M((0.12, -0.1, d), (0, 0, -25)))


# ======================================================================== Käse

KAESE = [(0.0, 0.0), (0.15, 0.0), (0.165, 0.008), (0.172, 0.03), (0.174, 0.05), (0.172, 0.07), (0.165, 0.092), (0.15, 0.1),
         (0.0, 0.1)]


def _kaese(s):
    return [(r * s, z * s) for r, z in KAESE]


def kaesebrett(m):
    m.teil(drehkoerper([(0.0, 0.0), (0.215, 0.0), (0.225, 0.006), (0.225, 0.02), (0.215, 0.026), (0.0, 0.026)], 28), "holz", None,
           uv="zylz", r=0.225)


def kaeselaib(m, kaputt):
    kaesebrett(m)
    d = 0.026
    klein = _kaese(0.55)
    if not kaputt:
        bm = drehkoerper(KAESE, 36)
        verbiegen(bm, m.rnd, 0.003, 0.1)
        m.teil(bm, "kaese", M((0, 0, d)), uv="zylz", r=0.17)
        bm = drehkoerper(klein, 28)
        verbiegen(bm, m.rnd, 0.002, 0.08)
        m.teil(bm, "kaese", M((0.03, -0.02, d + 0.1)), uv="zylz", r=0.1)
        return
    # Keil herausgeschnitten und daneben gelegt, Schimmel; der kleine Laib ist heruntergefallen und angefressen
    dreh = -75                                       # Lücke (300…360°) zeigt nach vorn
    drehstueck(m, KAESE, 0, 300, "kaese", "kaese_innen", M((0, 0, d), (0, 0, dreh)), seg=30,
               verformen=lambda bm: verbiegen(bm, m.rnd, 0.003, 0.1))
    flecken(m, M((0, 0, d), (0, 0, dreh)), KAESE, 6, 0, 300, gross=0.016)
    # der Keil ist ein Stück herausgezogen
    a = math.radians(dreh + 330)
    drehstueck(m, KAESE, 0, 60, "kaese", "kaese_innen", M((0.045 * math.cos(a), 0.045 * math.sin(a), d), (0, 0, dreh + 310)), seg=6)
    kruemel(m, M((0.06, -0.12, d)), 8, 0.05, ("kaese_innen",), 0.007)
    drehstueck(m, klein, 0, 290, "kaese", "kaese_innen", M((0.36, -0.14, 0.0), (0, 0, -40)), seg=26)
    flecken(m, M((0.36, -0.14, 0.0), (0, 0, -40)), klein, 3, 0, 290, gross=0.01)
    kruemel(m, M((0.3, -0.26, 0.0)), 6, 0.06, ("kaese_innen",), 0.006)


# ======================================================================== Würste an der Stange (unter der Decke)

STANGE_Z = -0.42
STANGE_R = 0.02


def wurst(m, mitte, L=0.13, r=0.021, mat="wurst", halb=False, neig=(0, 0)):
    """Ein Wurstglied entlang z um mitte. halb: unten angefressen (offene Schnittfläche)."""
    prof = [(0.0, L / 2), (r * 0.55, L / 2 - 0.004), (r * 0.9, L / 2 - 0.02), (r, 0.0), (r * 0.9, -L / 2 + 0.02),
            (r * 0.55, -L / 2 + 0.004), (0.0, -L / 2)]
    prof = list(reversed(prof))
    if halb:
        prof = [(0.0, -0.01), (r * 0.98, -0.01 + 0.003)] + [p for p in prof if p[1] > 0.0]
    bm = drehkoerper(prof, 10)
    if halb:
        for v in bm.verts:
            if v.co.z < -0.002:
                v.co.z += m.rnd.uniform(-0.006, 0.006)
    verbiegen(bm, m.rnd, 0.003, 0.05)
    m.teil(bm, mat, M(mitte, (neig[0], neig[1], 0)), uv="zylz", r=r)


def wurstkette(m, x, glieder, rest=None):
    """Schnur um die Stange, darunter hängen die Glieder. rest = Index des angefressenen letzten Glieds."""
    ring = [(x, (STANGE_R + 0.003) * math.sin(2 * math.pi * k / 10), STANGE_Z + (STANGE_R + 0.003) * math.cos(2 * math.pi * k / 10))
            for k in range(11)]
    m.seil(ring, 0.003, 4)
    z = STANGE_Z - STANGE_R - 0.003
    m.seil([(x, 0, z), (x, 0, z - 0.03)], 0.0025, 4)
    z -= 0.03
    L = 0.13
    for k in range(glieder):
        halb = rest is not None and k == rest
        mitte = (x, 0.0, z - L / 2)
        wurst(m, mitte, L, halb=halb)
        if halb:
            flecken(m, M(mitte), [(0.0, -0.01), (0.02, -0.007), (0.021, 0.0), (0.019, 0.045), (0.0, L / 2)], 2, gross=0.008)
            break
        z -= L
        if k < glieder - 1:
            m.seil([(x, 0, z + 0.004), (x, 0, z - 0.014)], 0.003, 4)
            z -= 0.01


def wurststange(m, kaputt):
    for s in (-1, 1):
        x = s * 0.42
        # Deckenhaken: Platte und Öse
        m.teil(drehkoerper([(0.0, 0.0), (0.03, 0.0), (0.03, -0.008), (0.0, -0.01)], 8), "eisen", M((x, 0, 0)))
        haken = [(x + 0.012 * math.sin(2 * math.pi * k / 10), 0.0, -0.028 + 0.016 * math.cos(2 * math.pi * k / 10)) for k in range(11)]
        m.seil(haken, 0.004, 5, "eisen")
        # Seil vom Haken zur Stange und einmal herum
        m.seil([(x, 0, -0.044), (x, 0, STANGE_Z + STANGE_R + 0.008)], 0.008)
        ring = [(x + 0.004 * k, (STANGE_R + 0.008) * math.sin(2 * math.pi * k / 10), STANGE_Z + (STANGE_R + 0.008) * math.cos(2 * math.pi * k / 10))
                for k in range(11)]
        m.seil(ring, 0.008)
    m.stab((-0.56, 0, STANGE_Z), (0.56, 0, STANGE_Z), STANGE_R, "holz", biegen=0.002)
    xs = [-0.32, -0.21, -0.1, 0.0, 0.11, 0.22, 0.33]
    if not kaputt:
        for k, x in enumerate(xs):
            wurstkette(m, x, (3, 2, 3, 2, 3, 2, 3)[k])
        return
    # geplündert: fast alle Würste weg, nur Schnurreste; eine Kette mit angefressenem letzten Glied
    for k, x in enumerate(xs):
        if k == 2:
            wurstkette(m, x, 3, rest=1)
        elif k == 5:
            wurstkette(m, x, 1)
        else:
            ring = [(x, (STANGE_R + 0.003) * math.sin(2 * math.pi * j / 10), STANGE_Z + (STANGE_R + 0.003) * math.cos(2 * math.pi * j / 10))
                    for j in range(11)]
            m.seil(ring, 0.003, 4)
            z = STANGE_Z - STANGE_R - 0.003
            ende = z - m.rnd.uniform(0.02, 0.06)
            m.seil([(x, 0, z), (x + m.rnd.uniform(-0.006, 0.006), 0.002, ende)], 0.0025, 4)


# ======================================================================== Kräuterbündel an der Wand

def _buendel(m, x, y0, z_bund, art, welk=False, fehlende=0):
    """Kopfüber hängendes Bündel unter dem Bindepunkt z_bund. art: kraut, lavendel, knoblauch."""
    mat_stiel = "kraut_welk" if welk else "kraut_trocken"
    if art == "knoblauch":
        n = 5 - fehlende
        for k in range(n):
            a = 2 * math.pi * k / 5 + 0.3
            rr = 0.03 if k % 2 == 0 else 0.018
            zb = z_bund - 0.08 - 0.06 * (k % 3)
            p = Vector((x + rr * math.cos(a), y0 + rr * 0.8 * math.sin(a), zb))
            m.stab((x, y0, z_bund + 0.012), tuple(p + Vector((0, 0, 0.03))), 0.003, "kraut_welk", seg=4, biegen=0)
            prof = [(0.0, -0.024), (0.012, -0.022), (0.024, -0.01), (0.026, 0.004), (0.017, 0.018), (0.006, 0.027), (0.003, 0.034),
                    (0.0, 0.035)]
            bm = drehkoerper(prof, 12)
            for v in bm.verts:                       # Zehen: leichte Rippen
                a2 = math.atan2(v.co.y, v.co.x)
                f = 1 + 0.08 * math.cos(6 * a2)
                v.co.x *= f; v.co.y *= f
            verbiegen(bm, m.rnd, 0.002, 0.02)
            m.teil(bm, "faul" if welk else "knoblauch", M(tuple(p)), uv="zylz", r=0.026)
        m.teil(rohr([(x + 0.011 * math.cos(t), y0 + 0.011 * math.sin(t), z_bund) for t in
                     (2 * math.pi * k / 10 for k in range(11))], 0.003, 4), "seil", None, uv="rohr", r=0.003, seg=4)
        return
    n = 9 if not welk else 6
    for k in range(n):
        phi = 2 * math.pi * k / n + m.rnd.uniform(-0.3, 0.3)
        rho = m.rnd.uniform(0.025, 0.045) * (0.8 if welk else 1.0)
        L = m.rnd.uniform(0.2, 0.26)
        a = Vector((x + 0.007 * math.cos(phi), y0 + 0.007 * math.sin(phi), z_bund + 0.025))
        b = Vector((x + rho * math.cos(phi), y0 + rho * 0.75 * math.sin(phi), z_bund - L))
        m.stab(tuple(a), tuple(b), 0.0022, mat_stiel, seg=4, biegen=0.002)
        if art == "lavendel":
            # Blütenähre am unteren Ende
            m.teil(ellipsoid(0.006, 0.006, 0.03, 1), "lavendel", ausrichten(b + (a - b).normalized() * 0.03, b) @ M(rot=(0, 90, 0)))
            continue
        # Blätter am unteren Zweidrittel, nach außen gerichtet
        for j in range(5 if not welk else 3):
            t = m.rnd.uniform(0.35, 1.0)
            p = a + (b - a) * t
            aus = Vector((math.cos(phi), math.sin(phi), 0)) * 0.012
            ziel = p + aus + Vector((m.rnd.uniform(-0.006, 0.006), m.rnd.uniform(-0.006, 0.006), m.rnd.uniform(-0.02, 0.0)))
            blatt = ellipsoid(0.014, 0.006, 0.0012, 1)
            m.teil(blatt, mat_stiel, ausrichten(tuple(p), tuple(ziel), oben=Vector((-math.sin(phi), math.cos(phi), 0.3))))
    m.teil(rohr([(x + 0.012 * math.cos(t), y0 + 0.012 * math.sin(t), z_bund) for t in
                 (2 * math.pi * k / 10 for k in range(11))], 0.003, 4), "seil", None, uv="rohr", r=0.003, seg=4)


def kraeuterbuendel(m, kaputt):
    # Wandleiste, mit zwei Nägeln an der Wand
    m.brett(0.8, 0.1, 0.025, M((0, -0.0125, 0), (90, 0, 0)), "holz", biegen=0.002)
    for x in (-0.36, 0.36):
        m.teil(drehkoerper([(0.0, 0.0), (0.007, 0.0), (0.006, 0.003), (0.0, 0.004)], 6), "eisen", M((x, -0.025, 0.0), (90, 0, 0)))
    arten = ["kraut", "lavendel", "kraut", "knoblauch"]
    xs = [-0.3, -0.1, 0.1, 0.3]
    y0 = -0.095
    for k, (x, art) in enumerate(zip(xs, arten)):
        pflock_ende = (x, -0.125, 0.012)
        if kaputt and k == 2:
            m.stab((x, -0.02, 0.0), (x, -0.045, 0.003), 0.011, "holz", biegen=0)      # abgebrochener Pflock
            m.teil(brocken(m.rnd, 0.008, 0.008, 0.004, 0.3, 1), "holz", M((x, -0.046, 0.003), (90, 0, 0)))
            continue
        m.stab((x, -0.02, 0.0), pflock_ende, 0.011, "holz", biegen=0)
        # Schlaufe um den Pflock und Schnur zum Bindepunkt
        ring = [(x + 0.014 * math.sin(2 * math.pi * j / 10), y0, 0.008 + 0.014 * math.cos(2 * math.pi * j / 10)) for j in range(11)]
        m.seil(ring, 0.0025, 4)
        if kaputt and k == 1:
            m.seil([(x, y0, -0.006), (x + 0.004, y0, -0.05)], 0.0025, 4)                 # Lavendel ist weg, nur die Schnur
            continue
        z_bund = -0.06
        m.seil([(x, y0, -0.006), (x, y0, z_bund)], 0.0025, 4)
        _buendel(m, x, y0, z_bund, art, welk=kaputt, fehlende=3 if kaputt else 0)


# ======================================================================== Mehlsäcke

def _sack_aufgerissen(m, matrix, h, r, loch_mitte, loch_r, rnd, mehl_innen=0.0, innen_dunkel=False):
    """Zusammengesackter Sack mit ausgefranstem Riss bei loch_mitte (Winkel, Höhe), Stoff mit Dicke; innen Mehl bis mehl_innen."""
    import mathutils.noise as noise
    prof = [(0.0, 0.0), (r * 0.8, 0.004), (r * 1.04, 0.05), (r * 1.06, h * 0.3), (r * 0.98, h * 0.62), (r * 0.6, h * 0.84),
            (r * 0.2, h * 0.9), (r * 0.22, h * 0.95), (r * 0.3, h), (0.0, h * 1.01)]
    fein = []                                        # Profil verfeinern, damit der Riss rund ausfranst
    for (r1, z1), (r2, z2) in zip(prof, prof[1:]):
        n = max(1, int(math.hypot(r2 - r1, z2 - z1) / 0.04))
        fein += [(r1 + (r2 - r1) * k / n, z1 + (z2 - z1) * k / n) for k in range(n)]
    prof = fein + [prof[-1]]
    bm = drehkoerper(prof, 30)
    verbiegen(bm, rnd, 0.03, 0.15)
    a0, z0 = loch_mitte
    o = Vector([rnd.uniform(-40, 40) for _ in range(3)])
    weg = []
    for f in bm.faces:
        c = f.calc_center_median()
        a = math.atan2(c.y, c.x)
        da = math.atan2(math.sin(a - a0), math.cos(a - a0)) * r
        d = math.hypot(da, (c.z - z0) * 0.8)
        if d < loch_r * (1 + 0.35 * noise.noise(c * 14 + o)):
            weg.append(f)
    bmesh.ops.delete(bm, geom=weg, context="FACES")
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.006)
    m.teil(bm, "stoff", matrix, uv="zylz", r=r)
    if innen_dunkel:                                 # leer gefressen: dunkles Inneres statt durchsichtig
        bm = drehkoerper([(0.0, 0.004), (r * 0.9, 0.006), (r * 0.95, h * 0.5), (r * 0.5, h * 0.8), (0.0, h * 0.82)], 16)
        m.teil(bm, "faul", matrix)
    if mehl_innen > 0:
        innen = [(0.0, 0.0), (r * 0.95, 0.0), (r * 0.98, mehl_innen * 0.7), (r * 0.7, mehl_innen), (0.0, mehl_innen * 1.04)]
        bm = drehkoerper(innen, 20)
        verbiegen(bm, rnd, 0.012, 0.1)
        m.teil(bm, "mehl", matrix)


def mehlsack(m, kaputt):
    r = 0.21
    if not kaputt:
        sack(m, M((-0.2, 0.0, 0.0)), 0.62, r)
        sack(m, M((0.06, 0.08, r * 0.82), (0, 90, 12), skal=(0.82, 1, 1)), 0.6, r * 0.95)
        return
    # aufgerissen und ausgelaufen: Mehlhaufen vor dem Riss, der liegende Sack hat ein angenagtes Loch und eine Mehlspur
    _sack_aufgerissen(m, M((-0.2, 0.0, 0.0)), 0.5, r, (math.radians(-90), 0.12), 0.13, m.rnd, mehl_innen=0.2)
    haufen(m, (-0.2, -0.28), 0.2, 0.17, 0.11, "mehl", m.rnd)
    haufen(m, (-0.05, -0.47), 0.1, 0.07, 0.015, "mehl", m.rnd, rand_rauh=0.4)
    # liegender Sack (lokale z-Achse nach +x), Loch am Boden des Sacks (lokal unten) wurde angenagt
    lieg = M((0.06, 0.08, r * 0.95 * 0.82), (0, 90, 12), skal=(0.82, 1, 1))
    _sack_aufgerissen(m, lieg, 0.6, r * 0.95, (math.radians(-60), 0.16), 0.06, m.rnd, mehl_innen=0.0, innen_dunkel=True)
    p = lieg @ Vector((0.0, -r * 0.95, 0.16))
    haufen(m, (p.x, p.y - 0.1), 0.09, 0.12, 0.02, "mehl", m.rnd, rand_rauh=0.4)


# ======================================================================== Gemüsekorb

def moehre(m, matrix, L=0.15, welk=False):
    prof = [(0.0, 0.0), (0.004, 0.012), (0.012, 0.07), (0.017, L - 0.012), (0.014, L - 0.002), (0.0, L)]
    bm = drehkoerper(prof, 10)
    for v in bm.verts:                               # Ringe in der Haut
        v.co.x *= 1 + 0.06 * math.sin(v.co.z * 260); v.co.y *= 1 + 0.06 * math.sin(v.co.z * 260)
    verbiegen(bm, m.rnd, 0.002, 0.04)
    m.teil(bm, "faul" if welk else "karotte", matrix, uv="zylz", r=0.017)
    for k in range(3):
        a = 2 * math.pi * k / 3
        ende = matrix @ Vector((0.025 * math.cos(a), 0.025 * math.sin(a), L + 0.07))
        m.stab(tuple(matrix @ Vector((0, 0, L - 0.004))), tuple(ende), 0.0025, "kraut_welk" if welk else "kohl", seg=4, biegen=0.002)


ZWIEBEL = [(0.0, 0.0), (0.012, 0.002), (0.03, 0.016), (0.034, 0.034), (0.026, 0.054), (0.009, 0.067), (0.003, 0.08), (0.0, 0.082)]


def zwiebel(m, matrix, faul=False):
    bm = drehkoerper(ZWIEBEL, 12)
    verbiegen(bm, m.rnd, 0.002, 0.03)
    m.teil(bm, "faul" if faul else "zwiebel", matrix, uv="zylz", r=0.034)


def kohl(m, matrix, r=0.075, faul=False):
    bm = brocken(m.rnd, r, r, r * 0.9, rauh=0.08, unterteilung=3)
    m.teil(bm, "faul" if faul else "kohl", matrix)
    # zwei abstehende Außenblätter als dünne Schalen
    for k in range(3):
        a = 120 * k + m.rnd.uniform(-20, 20)
        schale = drehkoerper([(0.0, -r * 0.6), (r * 0.7, -r * 0.45), (r * 1.02, 0.0), (r * 0.95, r * 0.45)], 8, False, False,
                             winkel=(a - 45, a + 45))
        bmesh.ops.solidify(schale, geom=schale.faces[:], thickness=0.003)
        m.teil(schale, "faul" if faul else "kohl", matrix)


def gemuesekorb(m, kaputt):
    ru, ro, h = 0.17, 0.22, 0.2
    if kaputt:
        m.umfallen_start()
    korb(m, None, ru, ro, h)
    # Strohpolster als Füllung, das Gemüse liegt darauf
    zf = h - 0.06
    m.teil(drehkoerper([(0.0, zf - 0.02), (ru + (ro - ru) * (zf - 0.02) / h - 0.014, zf - 0.02),
                        (ru + (ro - ru) * zf / h - 0.014, zf), (0.0, zf + 0.01)], 20), "stroh", None, uv="zylz", r=ro)
    if kaputt:
        # umgekippt nach vorn, das Gemüse ist herausgerollt; eine Zwiebel und eine Möhre sind faul
        m.umfallen_ende(-90)
        kohl(m, M((0.12, -0.62, 0.07)))
        for k, (x, y) in enumerate([(-0.15, -0.5), (0.02, -0.46), (-0.3, -0.62), (0.3, -0.42)]):
            zwiebel(m, M((x, y, 0.034), (90, 0, m.rnd.uniform(0, 360))) @ M((0, 0, -0.04)), faul=k == 2)
        moehre(m, M((-0.08, -0.72, 0.017), (0, 90, 30)) @ M((0, 0, -0.08)))
        moehre(m, M((0.35, -0.65, 0.017), (0, 90, -80)) @ M((0, 0, -0.08)), welk=True)
        return
    kohl(m, M((-0.06, 0.06, zf + 0.06)))
    for k, (x, y) in enumerate([(0.09, 0.07), (0.1, -0.05), (-0.03, -0.11), (0.0, 0.0)]):
        zwiebel(m, M((x, y, zf + 0.004), (m.rnd.uniform(-15, 15), m.rnd.uniform(-15, 15), 0)))
    # Möhren schräg über den Rand, Kraut nach außen
    for k, (x, y, rz) in enumerate([(-0.06, -0.06, -30), (0.05, 0.12, 60), (0.02, -0.02, 10)]):
        moehre(m, M((x, y, zf + 0.05), (0, 70, rz)) @ M((0, 0, -0.06)))


MODELLE = {"brotlaib": brotlaib, "kaeselaib": kaeselaib, "wurststange": wurststange, "kraeuterbuendel": kraeuterbuendel,
           "mehlsack": mehlsack, "gemuesekorb": gemuesekorb}


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
