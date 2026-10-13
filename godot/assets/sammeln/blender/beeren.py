"""Beerenstrauch (~0,9 m, 3 Varianten). Strauch und Beeren als getrennte .glb:
beeren_N.glb (Strauch) + beeren_frucht_N.glb (Beeren) – beim Ernten verschwinden nur die Beeren.
Material-Slots (siehe ../baeume/fichte.py MATS): rinde (Zweige), nadeln (Blätter), kern (= Beeren).
Aufruf: python beeren.py -- <zielordner/modelle>"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, export
from kiefer import roehre, karte

ZWEIG, BLATT, BEERE = 0, 1, 2
GOLD = math.pi * (3 - math.sqrt(5))

def huelle(i, n, rnd):
    y = 1 - 2 * (i + 0.5) / n
    rad = math.sqrt(max(0, 1 - y * y)); th = GOLD * i + rnd.uniform(-0.3, 0.3)
    return Vector((math.cos(th) * rad, math.sin(th) * rad, y))

def form(seed):
    rnd = random.Random(seed * 9973)
    h = rnd.uniform(0.8, 1.0)
    return rnd, h, h * rnd.uniform(0.5, 0.6), h * 0.38, h * 0.52   # rnd, höhe, rx, rz, zc

def strauch(seed=1):
    rnd, h, rx, rz, zc = form(seed)
    b = Bau()
    for k in range(rnd.randint(6, 9)):          # Zweige aus dem Boden
        a = rnd.uniform(0, 2 * math.pi)
        aus = Vector((math.cos(a), math.sin(a), 0))
        hh = h * rnd.uniform(0.6, 0.95)
        pts = [aus * rnd.uniform(0, 0.06) + aus * rx * 0.7 * s * s + Vector((0, 0, hh * s)) for s in (0, 0.33, 0.66, 1)]
        roehre(b, pts, [0.014, 0.01, 0.007, 0.003], 4, ZWEIG)
    n = 64
    for i in range(n):                           # dichtes Laub auf runder Hülle, unten offen
        r = huelle(i, n, rnd)
        if r.z < -0.6:
            continue
        f = rnd.uniform(0.7, 1.0)
        p = Vector((r.x * rx * f, r.y * rx * f, zc + r.z * rz * f))
        d = (r + Vector((0, 0, 0.3)) + Vector([rnd.uniform(-0.5, 0.5) for _ in range(3)])).normalized()
        g = rnd.uniform(0.28, 0.38); s0 = rnd.uniform(0, math.pi)
        for k in range(2):
            karte(b, p - d * g * 0.45, d, g, g * 0.7, s0 + k * math.pi / 2, BLATT)
    return b.bm

def beere(b, p, r):
    """kleine Kugel (Ikosaeder, 20 Dreiecke)"""
    res = bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=r)
    for v in res["verts"]:
        v.co += p
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = BEERE
        for l in f.loops:
            l[b.uv].uv = (0.5, 0.5)

def fruechte(seed=1):
    rnd, h, rx, rz, zc = form(seed)
    b = Bau()
    n = 18
    for i in range(n):                           # Trauben außen auf der Hülle, eher seitlich/oben
        r = huelle(i, n, random.Random(seed * 31 + i))
        if r.z < -0.35:
            continue
        p = Vector((r.x * rx * 0.97, r.y * rx * 0.97, zc + r.z * rz * 0.97))
        for k in range(rnd.randint(3, 6)):       # Traube hängt leicht nach unten
            q = p + Vector((rnd.uniform(-0.035, 0.035), rnd.uniform(-0.035, 0.035), -k * 0.022 + rnd.uniform(-0.01, 0.01)))
            beere(b, q, rnd.uniform(0.022, 0.03))
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for v in (1, 2, 3):
        export(f"beeren_{v}", strauch(seed=v), out)
        export(f"beeren_frucht_{v}", fruechte(seed=v), out)
