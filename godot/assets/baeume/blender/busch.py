"""Äste-Busch (~1 m, 3 Varianten) + geernteter Zustand als .glb für Godot.
Material-Slots wie fichte.py: rinde, nadeln (= Laub), kern, schnitt, rinde_oben.
Aufruf: python busch.py -- <zielordner/modelle>"""
import bpy, math, random, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, export
from kiefer import roehre, karte

RINDE, LAUB = 0, 1

def laub(b, p, richt, groesse, rnd, karten=3):
    d = (richt.normalized() + Vector((0, 0, 0.25)) + Vector([rnd.uniform(-0.5, 0.5) for _ in range(3)])).normalized()
    s = rnd.uniform(0, math.pi)
    for k in range(karten):
        karte(b, p - d * groesse * 0.45, d, groesse, groesse * 0.7, s + k * math.pi / karten, LAUB)

def trieb(b, basis, a, hoehe, neigung, rnd):
    """gebogener Trieb aus dem Boden; gibt die Punkte zurück"""
    aus = Vector((math.cos(a), math.sin(a), 0))
    pts = [basis + aus * neigung * hoehe * s * s + Vector((0, 0, hoehe * s)) + Vector([rnd.uniform(-0.03, 0.03) for _ in range(2)] + [0]) * (s > 0)
           for s in (0, 0.33, 0.66, 1.0)]
    r = rnd.uniform(0.012, 0.02)
    roehre(b, pts, [r, r * 0.75, r * 0.5, r * 0.25], 4, RINDE)
    return pts

def busch(seed=1):
    rnd = random.Random(seed * 7741)
    b = Bau()
    hoehe = rnd.uniform(0.9, 1.15)
    for k in range(rnd.randint(5, 8)):
        a = rnd.uniform(0, 2 * math.pi)
        basis = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0, 0.08)
        h = hoehe * rnd.uniform(0.65, 1.0)
        pts = trieb(b, basis, a, h, rnd.uniform(0.25, 0.6), rnd)
        aus = (pts[-1] - pts[0]).normalized()
        # Seitenzweige
        for s in (0.45, 0.7):
            if rnd.random() < 0.7:
                q0 = pts[1].lerp(pts[2], s)
                sa = a + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.2)
                q1 = q0 + Vector((math.cos(sa), math.sin(sa), rnd.uniform(0.4, 0.9))).normalized() * h * rnd.uniform(0.25, 0.4)
                roehre(b, [q0, q0.lerp(q1, 0.5), q1], [0.008, 0.005, 0.002], 3, RINDE)
                laub(b, q1, q1 - q0, rnd.uniform(0.3, 0.4), rnd)
        laub(b, pts[-1], aus, rnd.uniform(0.3, 0.4), rnd)
    # Laub gleichmäßig auf runder Hülle (wie Eiche), unten offen damit die Triebe sichtbar bleiben
    rx = hoehe * rnd.uniform(0.45, 0.55); rz = hoehe * 0.38; zc = hoehe * 0.6
    n = 46; gold = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        if y < -0.55 or rnd.random() < 0.08:
            continue
        rad = math.sqrt(1 - y * y); th = gold * i + rnd.uniform(-0.3, 0.3)
        r = Vector((math.cos(th) * rad, math.sin(th) * rad, y))
        f = rnd.uniform(0.65, 1.0)
        p = Vector((r.x * rx * f, r.y * rx * f, zc + r.z * rz * f))
        laub(b, p, r, rnd.uniform(0.28, 0.4), rnd, karten=2)
    return b.bm

def geerntet(seed=1):
    """kurze, abgeschnittene Triebe + etwas Laub am Boden"""
    rnd = random.Random(seed * 7741)
    b = Bau()
    for k in range(rnd.randint(6, 8)):
        a = rnd.uniform(0, 2 * math.pi)
        basis = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0, 0.08)
        trieb(b, basis, a, rnd.uniform(0.08, 0.2), rnd.uniform(0.1, 0.3), rnd)
    for k in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        p = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.05, 0.15) + Vector((0, 0, 0.05))
        laub(b, p, Vector((math.cos(a), math.sin(a), -0.3)), rnd.uniform(0.22, 0.3), rnd)
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for v in (1, 2, 3):
        export(f"busch_{v}", busch(seed=v), out)
    export("busch_geerntet", geerntet(), out)
