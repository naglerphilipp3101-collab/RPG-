"""Eiche (jung/alt, je 3 Varianten) + Baumstumpf als .glb für Godot.
Alt: kurzer Stamm gabelt sich in knorrige Hauptäste; Laubbüschel auf einer ovalen Hülle.
Jung: durchgehender Leittrieb mit Seitenästen.
Material-Slots wie fichte.py: rinde, nadeln (= Laub), kern, schnitt, rinde_oben.
Aufruf: python eiche.py -- <zielordner/modelle>"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, stamm_radius, export
from kiefer import roehre, karte

# höhe, stamm_d, krone_breit, krone_ab, büschel_anzahl, stumpf_höhe, büschelgröße  (siehe groessen.py)
EICHE = {"jung": (4.5, 0.21, 2.2, 2.0, 60, 0.35, 0.95),
         "alt":  (9.8, 0.70, 6.0, 2.8, 150, 0.55, 1.8)}
RINDE, LAUB, KERN, SCHNITT = range(4)

def laubbuschel(b, p, normale, groesse, rnd):
    """3 Karten sternförmig, zeigen nach außen und leicht nach oben"""
    d = (normale.normalized() * 0.75 + Vector((0, 0, 0.35)) + Vector([rnd.uniform(-0.3, 0.3) for _ in range(3)])).normalized()
    start = rnd.uniform(0, math.pi)
    for k in range(3):
        karte(b, p - d * groesse * 0.4, d, groesse, groesse * 0.6, start + k * math.pi / 3, LAUB)

def knorriger_ast(p0, p1, rnd, knick=0.18):
    """Punkte von p0 nach p1 mit seitlichen Knicken (Eichenäste sind krumm)"""
    pts = [p0]
    for s in (0.33, 0.66):
        q = p0.lerp(p1, s)
        q += Vector([rnd.uniform(-1, 1) for _ in range(3)]) * (p1 - p0).length * knick
        pts.append(q)
    pts.append(p1)
    return pts

def auf_huelle(zc, rx, rz, richt, f):
    """Punkt auf dem Krone-Ellipsoid (Faktor f) in Richtung richt"""
    r = richt.normalized()
    t = 1 / math.sqrt((r.x / rx) ** 2 + (r.y / rx) ** 2 + (r.z / rz) ** 2)
    return Vector((0, 0, zc)) + r * t * f

def eiche(alter, seed=1):
    H, dm, kb, ka, n_buschel, _, bg = EICHE[alter]
    rnd = random.Random(seed * 15485863)
    r0 = dm / 2; jung = alter == "jung"
    kh = H - ka; zc = ka + kh / 2
    # Krone leicht verformt pro Variante: etwas breiter/schmaler, leicht verschoben
    rx = kb / 2 * rnd.uniform(0.9, 1.08); rz = kh / 2 * rnd.uniform(0.92, 1.05)
    versatz = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * kb * 0.06
    noff = Vector((seed * 3.3, seed * 9.1, 0))
    def achse(z):
        return Vector((noise.noise(Vector((z * 0.3, 0, 0)) + noff), noise.noise(Vector((0, z * 0.3, 0)) + noff), 0)) * r0 * 0.8 \
            + versatz * min(1, z / H) ** 2
    b = Bau()
    if jung:
        b.stamm(H, r0, H * 0.9, 9, seed, mat=RINDE, achse=achse)
        aeste = []
        for k in range(rnd.randint(5, 7)):
            z = rnd.uniform(ka - 0.2, H * 0.78); a = rnd.uniform(0, 2 * math.pi)
            richt = Vector((math.cos(a), math.sin(a), rnd.uniform(0.4, 1.0)))
            p0 = Vector((0, 0, z)) + achse(z)
            p1 = auf_huelle(zc, rx, rz, (p0 + richt - Vector((0, 0, zc))), rnd.uniform(0.75, 0.9)) + versatz
            pts = knorriger_ast(p0, p1, rnd, 0.08)
            rr = stamm_radius(z, H, r0) * 0.45
            roehre(b, pts, [rr, rr * 0.7, rr * 0.45, rr * 0.2], 4, RINDE)
            aeste.append(pts)
    else:
        gabel = ka + rnd.uniform(0.2, 0.8)
        b.stamm(H, r0, gabel + 0.3, 14, seed, mat=RINDE, achse=achse)
        aeste = []
        n = rnd.randint(3, 4)
        start = rnd.uniform(0, 2 * math.pi)
        rg = stamm_radius(gabel, H, r0)
        for k in range(n + 1):
            if k < n:   # Hauptäste schräg nach außen
                a = start + 2 * math.pi * k / n + rnd.uniform(-0.35, 0.35)
                richt = Vector((math.cos(a), math.sin(a), rnd.uniform(0.7, 1.4)))
                f = rnd.uniform(0.72, 0.85); rr = rg * rnd.uniform(0.55, 0.7)
            else:       # Leitast nach oben
                richt = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 1)); f = 0.8; rr = rg * 0.5
            p0 = Vector((0, 0, gabel)) + achse(gabel)
            p1 = auf_huelle(zc, rx, rz, richt, f) + versatz
            pts = knorriger_ast(p0, p1, rnd, 0.16)
            roehre(b, pts, [rr, rr * 0.75, rr * 0.5, rr * 0.25], 6, RINDE)
            aeste.append(pts)
            # Nebenäste
            for s in (0.45, 0.75):
                if rnd.random() < 0.8:
                    q0 = pts[1].lerp(pts[2], s)
                    seit = Vector([rnd.uniform(-1, 1) for _ in range(2)] + [rnd.uniform(0, 0.8)])
                    q1 = auf_huelle(zc, rx, rz, (q0 - Vector((0, 0, zc))) + seit * 2.0, rnd.uniform(0.78, 0.92)) + versatz
                    qp = knorriger_ast(q0, q1, rnd, 0.12)
                    roehre(b, qp, [rr * 0.45, rr * 0.3, rr * 0.18, rr * 0.08], 4, RINDE)
                    aeste.append(qp)
    # Laub: Büschel an Astenden + gleichmäßig auf der äußeren Hülle (Fibonacci-Kugel)
    for pts in aeste:
        laubbuschel(b, pts[-1], pts[-1] - Vector((0, 0, zc)), bg * rnd.uniform(0.9, 1.15), rnd)
    gold = math.pi * (3 - math.sqrt(5))
    for i in range(n_buschel):
        y = 1 - 2 * (i + 0.5) / n_buschel
        if y < -0.75:            # Unterseite der Krone dünner
            continue
        rad = math.sqrt(1 - y * y); th = gold * i + rnd.uniform(-0.2, 0.2)
        richt = Vector((math.cos(th) * rad, math.sin(th) * rad, y))
        p = auf_huelle(zc, rx, rz, richt, rnd.uniform(0.75, 0.95)) + versatz * 0.8
        if rnd.random() < 0.05:  # kleine Lücken in der Krone
            continue
        laubbuschel(b, p, richt, bg * rnd.uniform(0.8, 1.2), rnd)
        if i % 3 == 0:           # innere Schicht für Tiefe
            laubbuschel(b, auf_huelle(zc, rx, rz, richt, rnd.uniform(0.45, 0.62)) + versatz * 0.8, richt, bg * 0.9, rnd)
    # Kern: Laub-Ellipsoid innen, lässt die Krone dicht wirken
    kern = bmesh.ops.create_uvsphere(b.bm, u_segments=10, v_segments=6, radius=1)
    for v in kern["verts"]:
        v.co = Vector((v.co.x * rx * 0.7, v.co.y * rx * 0.7, v.co.z * rz * 0.68 + zc)) + versatz * 0.8
    for f in {f for v in kern["verts"] for f in v.link_faces}:
        f.material_index = KERN
        for l in f.loops:
            c = l.vert.co - Vector((0, 0, zc))
            l[b.uv].uv = (math.atan2(c.y, c.x) / math.pi * 2, c.z / 1.0)
    return b.bm

def stumpf(alter, seed=1):
    H, dm, *_ , h_stumpf, _bg = EICHE[alter]
    b = Bau()
    b.stamm(H, dm / 2, h_stumpf, 9 if alter == "jung" else 14, seed, mat=RINDE, deckel_mat=SCHNITT)
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for alter in EICHE:
        for v in (1, 2, 3):
            export(f"eiche_{alter}_{v}", eiche(alter, seed=v), out)
        export(f"eiche_stumpf_{alter}", stumpf(alter), out)
