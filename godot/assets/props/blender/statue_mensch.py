"""Steinfigur aus dem Körper des Charakter-Editors (MakeHuman-Daten wie im Spiel, gelesen mit
tools/ruestung/mensch_lesen.py): Oberkörper und Kopf einer Frau, Arme so gebeugt, dass beide Hände auf dem
Schwertknauf liegen. Der Rumpf wird geglättet und leicht aufgeblasen (anliegendes Gewand), die Haare sind eine
Kappe über der Kopfhaut mit Knoten. Beine und Hüfte stecken im Rock der Statue (burg_kirche.figur)."""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "ruestung"))
from mensch_lesen import Mensch  # noqa: E402

SKAL = 1.1            # etwas über Lebensgröße
SCHNITT = 0.9         # Körper unterhalb dieser Höhe (vor dem Skalieren) steckt im Rock
_CACHE = {}


def _drehung(a, b):
    a = Vector(a).normalized(); b = Vector(b).normalized()
    return a.rotation_difference(b).to_matrix().to_4x4()


def _um(p, r):
    p = Vector(p)
    return Matrix.Translation(p) @ r @ Matrix.Translation(-p)


def _daten():
    if "d" in _CACHE:
        return _CACHE["d"]
    m = Mensch()
    p = m.form_berechnen({"geschlecht": 0.0, "muskeln": 0.6, "gewicht": 0.45})
    kn = {b["name"]: b for b in m.meta["knochen"]}
    pos = lambda n, w: p[kn[n][w]].mean(0)
    T = {n: Matrix.Identity(4) for n in kn}
    for seite, s in (("Left", 1), ("Right", -1)):
        S = pos(seite + "UpperArm", "kopf"); E = pos(seite + "UpperArm", "ende"); W = pos(seite + "LowerArm", "ende")
        H = pos(seite + "Hand", "ende")
        # Ellbogen hängt neben dem Rumpf, Unterarm nach vorn-innen, Hände übereinander auf dem Knauf
        E2 = Vector(S) + Vector((s * 0.05, -1.0, -0.12)).normalized() * float(np.linalg.norm(E - S))
        W2 = Vector((s * 0.045, 1.0 + (0.035 if s > 0 else 0.0), 0.2))
        W2 = E2 + (W2 - E2).normalized() * float(np.linalg.norm(W - E))
        T1 = _um(S, _drehung(E - S, E2 - Vector(S)))
        R2 = _drehung(W - E, W2 - E2)
        T2 = Matrix.Translation(E2) @ R2 @ Matrix.Translation(-Vector(E))
        # Hand: Finger über den Knauf gelegt (nach innen und unten)
        h_ziel = Vector((-s * 0.8, -0.55, 0.25))
        R3 = _drehung(R2 @ Vector(H - W), h_ziel) @ R2
        T3 = Matrix.Translation(W2) @ R3 @ Matrix.Translation(-Vector(W))
        T[seite + "UpperArm"] = T1
        T[seite + "LowerArm"] = T2
        for n in kn:
            if n.startswith(seite) and any(k in n for k in ("Hand", "Index", "Middle", "Ring", "Little", "Thumb")):
                T[n] = T3
    namen = [b["name"] for b in m.meta["knochen"]]
    Tm = np.array([np.array(T[n]) for n in namen])                 # (B, 4, 4)
    ph = np.c_[p, np.ones(len(p))]
    neu = np.zeros_like(p)
    for k in range(4):
        idx = m.k_idx[:, k]; w = m.k_gew[:, k]
        neu += w[:, None] * np.einsum("nij,nj->ni", Tm[idx], ph)[:, :3]
    # Knochengruppe je Punkt (für Glätten und Bruchstücke)
    gruppe = np.zeros(len(p), dtype=np.int8)
    def anteil(teile):
        return m.knochen_anteil(teile)
    kopf = anteil(["Head"]); rumpf = anteil(["Hips", "Spine", "Chest", "Neck", "Shoulder"])
    rarm = anteil(["RightLowerArm", "RightHand", "RightIndex", "RightMiddle", "RightRing", "RightLittle", "RightThumb"])
    gruppe[kopf > 0.5] = 1
    gruppe[rumpf > 0.35] = 2
    gruppe[rarm > 0.5] = 3
    knauf = Vector((0.0, 0.985, 0.215))
    _CACHE["gruppen"] = m.meta["gruppen"]
    _CACHE["d"] = (neu, m.koerper_dreiecke, gruppe, knauf, p[kn["Head"]["kopf"]].mean(0)[1])
    return _CACHE["d"]


def _b(v):
    """Godot (Y oben, Blick +Z) -> Blender (Z oben, Blick -Y), skaliert."""
    return Vector((v[0], -v[2], v[1])) * SKAL


def _verringern(bm, anteil):
    me = bpy.data.meshes.new("tmp")
    bm.to_mesh(me)
    ob = bpy.data.objects.new("tmp", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("d", "DECIMATE")
    mod.ratio = anteil
    dg = bpy.context.evaluated_depsgraph_get()
    neu = bmesh.new()
    neu.from_mesh(ob.evaluated_get(dg).to_mesh())
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return neu


def _rand_schliessen(bm, rnd, tiefe=0.0):
    rand = [e for e in bm.edges if e.is_boundary]
    if not rand:
        return
    erg = bmesh.ops.holes_fill(bm, edges=rand, sides=0)
    if tiefe:
        # Bruchfläche uneben: mittig aufwölben/einsenken, Ränder bleiben
        neu = erg["faces"]
        p = bmesh.ops.poke(bm, faces=neu)
        for v in p["verts"]:
            n = Vector((0, 0, 0))
            for f in v.link_faces:
                n += f.normal
            if n.length:
                v.co += n.normalized() * rnd.uniform(-tiefe, tiefe)


def _anhaengen(ziel, quelle):
    m_ = [ziel.verts.new(v.co) for v in quelle.verts]
    quelle.verts.index_update()
    for f in quelle.faces:
        try:
            ziel.faces.new([m_[v.index] for v in f.verts])
        except ValueError:
            pass
    ziel.normal_update()


def _knoten():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.045)
    for v in bm.verts:
        v.co.y *= 0.8; v.co.z *= 0.85
    return bm


def figur_teile(rnd, kaputt):
    """bmeshes in Blender-Koordinaten (Füße auf z = 0): 'koerper', 'haare' und bei kaputt 'kopf', 'arm'.
    Dazu der Knaufpunkt (Hände) für das Schwert."""
    neu, dreiecke, gruppe, knauf, _ = _daten()
    bm = bmesh.new()
    gl = bm.verts.layers.int.new("gruppe")
    vs = [bm.verts.new(_b(v)) for v in neu]
    for v, g in zip(vs, gruppe):
        v[gl] = int(g)
    for a, b_, c in dreiecke:
        try:
            bm.faces.new((vs[a], vs[b_], vs[c]))
        except ValueError:
            pass
    # Beine weg (stecken im Rock)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.z < SCHNITT * SKAL for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()
    # Augen und kleine Öffnungen schließen (nicht den großen Rand unten am Rumpf); die Augäpfel wölben sich leicht
    rand = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > (SCHNITT + 0.1) * SKAL]
    # Augäpfel aus den Hilfskugeln des Grundnetzes (helper-l/r-eye), etwas verkleinert, damit sie unter den Lidern sitzen
    if rand:
        bmesh.ops.holes_fill(bm, edges=rand, sides=0)
    for name in ("helper-l-eye", "helper-r-eye"):
        idx = [i for b_ in _CACHE["gruppen"][name] for i in range(int(b_[0]), int(b_[1]) + 1)]
        pts = [_b(neu[i]) for i in idx]
        mitte = sum(pts, Vector()) / len(pts)
        r = sum((p_ - mitte).length for p_ in pts) / len(pts)
        kugel = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r * 0.97, matrix=Matrix.Translation(mitte))
        for v in kugel["verts"]:
            v[gl] = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # Gewand: Rumpf glätten (keine Anatomie unter dem Stoff) und etwas aufblasen; zum Rand hin (Arme, Hals)
    # weich auslaufend, damit keine Stufe entsteht
    rumpf = set(v for v in bm.verts if v[gl] == 2 and (SCHNITT + 0.1) * SKAL < v.co.z < 1.36 * SKAL)
    abstand = {}
    front = [v for v in rumpf if any(e.other_vert(v) not in rumpf for e in v.link_edges)]
    for v in front:
        abstand[v] = 0
    for d in range(1, 6):
        neu_ = []
        for v in front:
            for e in v.link_edges:
                w = e.other_vert(v)
                if w in rumpf and w not in abstand:
                    abstand[w] = d; neu_.append(w)
        front = neu_
    stufen = {}
    for v in rumpf:
        stufen.setdefault(min(abstand.get(v, 6), 6), []).append(v)
    for k in range(120):
        for d, vs_ in stufen.items():
            if d and (k < 30 or d == 6):
                bmesh.ops.smooth_vert(bm, verts=vs_, factor=0.6 * d / 6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in rumpf:
        v.co += v.normal * 0.012 * min(abstand.get(v, 6), 6) / 6
    bm.normal_update()
    saum = None
    # Haare: Kappe über der Kopfhaut (über Stirn und Ohren), dazu ein Knoten am Hinterkopf
    kopf_z = max(v.co.z for v in bm.verts)
    stirn = [f for f in bm.faces if all(v[gl] == 1 for v in f.verts) and f.calc_center_median().z > kopf_z - 0.135 * SKAL and
             (f.calc_center_median().y > -0.035 * SKAL or f.calc_center_median().z > kopf_z - 0.05 * SKAL)]
    haare = bmesh.new()
    hv = {}
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    for f in stirn:
        nv = []
        for v in f.verts:
            if v.index not in hv:
                hv[v.index] = haare.verts.new(v.co + v.normal * 0.02)
            nv.append(hv[v.index])
        haare.faces.new(nv)
    # Haaransatz liegt auf der Haut auf (keine Lücke), innen steht die Kappe ab; so braucht sie keine Rückseite
    zurueck = {nv: i for i, nv in hv.items()}
    for v in haare.verts:
        if any(e.is_boundary for e in v.link_edges):
            bv = bm.verts[zurueck[v]]
            v.co = bv.co.copy()
    for _ in range(3):
        bmesh.ops.smooth_vert(haare, verts=[v for v in haare.verts if not any(e.is_boundary for e in v.link_edges)], factor=0.5,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    haare.normal_update()
    hinten = max((v.co for v in bm.verts if v[gl] == 1), key=lambda c: c.y)
    erg = {"haare": haare, "knoten": Matrix.Translation(hinten + Vector((0, 0.035, 0.02))), "saum": saum}
    if kaputt:
        bm.verts.ensure_lookup_table()
        for name, g in (("kopf", 1), ("arm", 3)):
            teil = bmesh.new()
            m_ = {}
            faces = [f for f in bm.faces if sum(v[gl] == g for v in f.verts) >= 2]
            for f in faces:
                nv = []
                for v in f.verts:
                    if v not in m_:
                        m_[v] = teil.verts.new(v.co)
                    nv.append(m_[v])
                teil.faces.new(nv)
            bmesh.ops.delete(bm, geom=faces, context="FACES")
            _rand_schliessen(teil, rnd, 0.012)
            teil = _verringern(teil, 0.4)
            if name == "kopf":
                # Haare und Knoten gehören zum abgeschlagenen Kopf
                _anhaengen(teil, erg.pop("haare"))
                k = _knoten(); k.transform(erg.pop("knoten")); _anhaengen(teil, k)
            erg[name] = teil
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        # Bruchstellen am Hals und Ellbogen schließen (der offene Rand unten bleibt, er steckt im Rock)
        rand = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > (SCHNITT + 0.1) * SKAL]
        if rand:
            f = bmesh.ops.holes_fill(bm, edges=rand, sides=0)["faces"]
            p = bmesh.ops.poke(bm, faces=f)
            for v in p["verts"]:
                v.co.z += rnd.uniform(-0.01, 0.01)
    bm.normal_update()
    erg["koerper"] = _verringern(bm, 0.35)
    erg["knauf"] = _b(knauf)
    erg["schnitt"] = SCHNITT * SKAL
    return erg
