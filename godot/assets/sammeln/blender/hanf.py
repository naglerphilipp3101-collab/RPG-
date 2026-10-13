"""Hanf (3 Varianten) + geernteter Zustand als .glb für Godot.
Material-Slots (siehe ../baeume/fichte.py MATS): rinde (= Stängel), nadeln (= Blätter), bluete.
Aufruf: python hanf.py -- <zielordner/modelle>"""
import bpy, math, random, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, export
from kiefer import roehre

STENGEL, BLATT, BLUETE = 0, 1, 5

def quad(b, basis, richtung, laenge, breite, quer, mat):
    """Karte: u entlang richtung, v entlang quer"""
    d = richtung.normalized(); q = quer.normalized()
    a, e = basis, basis + d * laenge
    b.face((a - q * breite / 2, a + q * breite / 2, e + q * breite / 2, e - q * breite / 2),
           ((0, 0), (0, 1), (1, 1), (1, 0)), mat)

def stengel(b, basis, hoehe, rnd, mit_blaettern=True):
    neig = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * hoehe * 0.08
    pts = [basis + Vector((0, 0, hoehe * s)) + neig * s * s for s in (0, 0.25, 0.5, 0.75, 1.0)]
    r = rnd.uniform(0.01, 0.014)
    roehre(b, pts, [r, r * 0.85, r * 0.7, r * 0.5, r * 0.3], 4, STENGEL)
    if not mit_blaettern:
        return
    # Blattpaare an Knoten, gegenständig, jedes Paar 90° gedreht; nach oben kleiner
    z = rnd.uniform(0.25, 0.35); drehung = rnd.uniform(0, math.pi)
    while z < hoehe * 0.85:
        t = z / hoehe
        k = min(int(t * 4), 3); f = t * 4 - k
        p = pts[k].lerp(pts[k + 1], f)
        groesse = (0.52 - 0.24 * t) * rnd.uniform(0.85, 1.1)
        for seite in (0, math.pi):
            a = drehung + seite + rnd.uniform(-0.3, 0.3)
            aus = Vector((math.cos(a), math.sin(a), 0))
            haengen = rnd.uniform(0.25, 0.75)                      # Hanfblätter hängen deutlich
            richt = (aus + Vector((0, 0, -haengen))).normalized()
            quer = Matrix.Rotation(rnd.uniform(-0.9, 0.9), 3, richt) @ aus.cross(Vector((0, 0, 1)))
            quad(b, p, richt, groesse, groesse, quer, BLATT)
            if rnd.random() < 0.55:                                # Seitentrieb mit kleinen Blättern
                st = (aus + Vector((0, 0, 1.0))).normalized()
                for k in range(2):
                    q2 = Matrix.Rotation(k * math.pi / 2 + rnd.uniform(0, 1), 3, st) @ aus.cross(Vector((0, 0, 1)))
                    quad(b, p, st, groesse * 0.65, groesse * 0.65, q2, BLATT)
        drehung += math.pi / 2 + rnd.uniform(-0.2, 0.2)
        z += rnd.uniform(0.13, 0.18)
    # Blütenstand: zwei gekreuzte senkrechte Karten an der Spitze
    spitze = pts[-1] - Vector((0, 0, 0.32))
    for a in (0, math.pi / 2):
        a += rnd.uniform(0, 1)
        quad(b, spitze, (pts[-1] - pts[-2]).normalized(), 0.42, 0.15, Vector((math.cos(a), math.sin(a), 0)), BLUETE)

def hanf(seed=1):
    rnd = random.Random(seed * 3571)
    b = Bau()
    for k in range(rnd.randint(3, 5)):
        a = rnd.uniform(0, 2 * math.pi)
        basis = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0, 0.25)
        stengel(b, basis, rnd.uniform(1.3, 1.8), rnd)
    return b.bm

def geerntet(seed=1):
    rnd = random.Random(seed * 3571)
    b = Bau()
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        basis = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0, 0.22)
        stengel(b, basis, rnd.uniform(0.1, 0.22), rnd, mit_blaettern=False)
    for k in range(3):   # ein paar abgefallene Blätter
        a = rnd.uniform(0, 2 * math.pi)
        p = Vector((math.cos(a), math.sin(a), 0.02)) * rnd.uniform(0.05, 0.25)
        aus = Vector((math.cos(a + 1), math.sin(a + 1), 0.05))
        quad(b, p, aus, 0.25, 0.25, aus.cross(Vector((0, 0, 1))).cross(aus), BLATT)
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for v in (1, 2, 3):
        export(f"hanf_{v}", hanf(seed=v), out)
    export("hanf_geerntet", geerntet(), out)
