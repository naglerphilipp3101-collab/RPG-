"""Felsmonolithen (Landschaftsdeko, nicht abbaubar): Felstürme aus gestapelten Blöcken und breite Felsgruppen.
Nutzt die Brockenformen aus formen.py. Material in Godot: materialien/stein.tres (Triplanar, braucht keine UVs).
Aufruf: blender -b -P monolith.py -- <zielordner/modelle>"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formen import rock_shape
from export_godot import obj_from_bm, decimated, finish, export

def block(bm_ziel, seed, groesse, pos, drehung, subdiv=6):
    """eine Brockenform skalieren (x, y, z), drehen, verschieben und ins Ziel-Mesh übernehmen"""
    rb = rock_shape(seed, subdiv=subdiv)
    m = Matrix.Translation(pos) @ Matrix.Rotation(drehung, 4, "Z")
    for v in rb.verts:
        v.co = m @ Vector((v.co.x * groesse.x, v.co.y * groesse.y, v.co.z * groesse.z))
    tmp = bpy.data.meshes.new("tmp"); rb.to_mesh(tmp); rb.free(); bm_ziel.from_mesh(tmp); bpy.data.meshes.remove(tmp)

def felsturm(seed):
    """3–5 nach oben kleiner werdende Blöcke, leicht versetzt – wie ein verwitterter Felsturm (15–22 m)"""
    rnd = random.Random(seed * 7)
    bm = bmesh.new()
    z = -1.0; breite = rnd.uniform(7.0, 9.0); dreh = rnd.uniform(0, 6.28)
    seitlich = Vector((0, 0, 0))
    for k in range(rnd.randint(3, 5)):
        hoch = rnd.uniform(3.6, 5.4)
        b = breite * (1 - 0.17 * k) * rnd.uniform(0.9, 1.05)
        block(bm, seed * 31 + k, Vector((b * 0.55, b * 0.48, hoch * 0.8)), Vector((seitlich.x, seitlich.y, z)), dreh + rnd.uniform(-0.6, 0.6))
        z += hoch * 0.82
        seitlich += Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 0))
    # ein paar Felsen am Fuß
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 6.28); r = breite * rnd.uniform(0.45, 0.65)
        s = rnd.uniform(1.2, 2.4)
        block(bm, seed * 53 + k, Vector((s, s * 0.85, s * 0.7)), Vector((math.cos(a) * r, math.sin(a) * r, -0.3)), rnd.uniform(0, 6.28), 5)
    return bm

def felsgruppe(seed):
    """2–4 große, nebeneinander lehnende Blöcke (7–10 m hoch) – breite Felsformation"""
    rnd = random.Random(seed * 11)
    bm = bmesh.new()
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0, 5.5) if k else 0
        hoch = rnd.uniform(4.5, 7.0) * (1.0 if k == 0 else 0.75)
        b = rnd.uniform(4.0, 6.0)
        block(bm, seed * 17 + k, Vector((b, b * rnd.uniform(0.6, 0.9), hoch)),
              Vector((math.cos(a) * r, math.sin(a) * r, -0.5)), rnd.uniform(0, 6.28))
    return bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    teile = [("monolith_turm_%d", felsturm, 9000), ("monolith_gruppe_%d", felsgruppe, 7000)]
    for name, bau, tris in teile:
        for v in (1, 2, 3):
            ob = obj_from_bm(name % v, bau(v * 13 + 5))
            decimated(ob, tris); finish(ob, 55)
            export(ob, os.path.join(out, (name % v) + ".glb"))
