"""Kraut (~0,4–0,6 m, 3 Varianten) + geernteter Zustand als .glb.
Blattrosette am Boden + Blütenstängel mit Dolden. Blüten werden im Material eingefärbt (weiß/gelb/lila/rot).
Material-Slots: rinde (Stängel), nadeln (Blätter), bluete.
Aufruf: python kraut.py -- <zielordner/modelle>"""
import bpy, math, random, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, export
from kiefer import roehre, karte

STENGEL, BLATT, BLUETE = 0, 1, 5

def rosette(b, rnd, anzahl, laenge):
    start = rnd.uniform(0, 2 * math.pi)
    for k in range(anzahl):
        a = start + k * 2 * math.pi / anzahl + rnd.uniform(-0.25, 0.25)
        aus = Vector((math.cos(a), math.sin(a), 0))
        d = (aus + Vector((0, 0, rnd.uniform(0.25, 0.9)))).normalized()
        L = laenge * rnd.uniform(0.75, 1.1)
        karte(b, Vector((0, 0, 0.01)), d, L, L * 0.26, rnd.uniform(-0.3, 0.3), BLATT)

def dolde(b, p, groesse, rnd):
    """Blütenkopf: eine flache Karte + zwei gekreuzte, leicht gekippte (von der Seite sichtbar)"""
    def zentriert(u, v):
        b.face((p - u - v, p + u - v, p + u + v, p - u + v), ((0, 0), (1, 0), (1, 1), (0, 1)), BLUETE)
    g = groesse / 2; dreh = rnd.uniform(0, math.pi)
    u = Vector((math.cos(dreh), math.sin(dreh), 0)) * g
    zentriert(u, Vector((-u.y, u.x, 0)))
    for k in range(2):
        a = dreh + k * math.pi / 2
        u2 = Vector((math.cos(a), math.sin(a), 0)) * g
        zentriert(u2, Vector((0, 0, g * 0.7)) + Vector((-u2.y, u2.x, 0)) * 0.25)

def kraut(seed=1):
    rnd = random.Random(seed * 6007)
    b = Bau()
    rosette(b, rnd, rnd.randint(8, 11), 0.28)
    for k in range(rnd.randint(3, 6)):
        a = rnd.uniform(0, 2 * math.pi); aus = Vector((math.cos(a), math.sin(a), 0))
        h = rnd.uniform(0.35, 0.6)
        pts = [aus * 0.03 + aus * h * 0.25 * s * s + Vector((0, 0, h * s)) for s in (0, 0.33, 0.66, 1)]
        roehre(b, pts, [0.006, 0.005, 0.004, 0.003], 3, STENGEL)
        for s in (0.35, 0.6):                     # kleine Stängelblätter
            p = pts[1].lerp(pts[2], s)
            d = (Vector((math.cos(a + 1.3 * (1 if s < 0.5 else -1)), math.sin(a + 1.3 * (1 if s < 0.5 else -1)), 0.5))).normalized()
            karte(b, p, d, 0.12, 0.035, 0.2, BLATT)
        dolde(b, pts[-1], rnd.uniform(0.26, 0.32), rnd)
    return b.bm

def geerntet(seed=1):
    rnd = random.Random(seed * 6007)
    b = Bau()
    rosette(b, rnd, 6, 0.14)
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for v in (1, 2, 3):
        export(f"kraut_{v}", kraut(seed=v), out)
    export("kraut_geerntet", geerntet(), out)
