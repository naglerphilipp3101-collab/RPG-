"""Kiefer (jung/alt, je 3 Varianten) + Baumstumpf als .glb für Godot.
Hauptäste als echte Geometrie, Nadelbüschel als gekreuzte Karten an den Astenden -> Schirmkrone.
Material-Slots wie fichte.py: rinde, nadeln, kern, schnitt, rinde_oben.
Aufruf: python kiefer.py -- <zielordner/modelle>"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fichte import Bau, stamm_radius, export

# höhe, stamm_d, krone_breit, krone_ab, quirle, stumpf_höhe, büschelgröße  (siehe groessen.py)
KIEFER = {"jung": (4.9, 0.18, 2.5, 2.2, 5, 0.35, 0.85),
          "alt":  (11.2, 0.35, 4.9, 6.3, 7, 0.5, 1.45),
          "uralt": (18.0, 0.62, 7.5, 12.0, 6, 0.6, 1.9)}   # untere 2/3 kahl
RINDE, NADELN, KERN, SCHNITT, RINDE_OBEN = range(5)

def roehre(b, punkte, radien, seiten, mat):
    """dünner Ast entlang einer Punktliste (wenige Seiten, spart Dreiecke)"""
    ringe = []
    for k, (p, r) in enumerate(zip(punkte, radien)):
        d = (punkte[min(k + 1, len(punkte) - 1)] - punkte[max(k - 1, 0)]).normalized()
        u = d.orthogonal().normalized(); v = d.cross(u)
        ringe.append([b.bm.verts.new(p + (u * math.cos(2 * math.pi * i / seiten) + v * math.sin(2 * math.pi * i / seiten)) * r)
                      for i in range(seiten)])
    for k in range(len(ringe) - 1):
        for i in range(seiten):
            i2 = (i + 1) % seiten
            f = b.bm.faces.new((ringe[k][i], ringe[k][i2], ringe[k + 1][i2], ringe[k + 1][i])); f.material_index = mat
            for l, uv in zip(f.loops, ((i / seiten, k), ((i + 1) / seiten, k), ((i + 1) / seiten, k + 1), (i / seiten, k + 1))):
                l[b.uv].uv = uv

def kahle_aeste(b, H, r0, achse, z_von, z_bis, rnd, laenge=(0.8, 2.4), mat=RINDE):
    """Abgestorbene, blattlose Äste am unteren Stamm alter Bäume (z_von..z_bis): leicht hängend, nach oben länger,
    manche abgebrochen, längere mit einem Seitenzweig. Kostet viel weniger als belaubte Äste."""
    z = z_von
    while z < z_bis:
        a = rnd.uniform(0, 2 * math.pi)
        d = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.35, 0.12))).normalized()
        t = (z - z_von) / max(0.1, z_bis - z_von)
        L = rnd.uniform(*laenge) * (0.45 + 0.55 * t)
        if rnd.random() < 0.35:
            L *= rnd.uniform(0.15, 0.35)                 # abgebrochener Stummel
        p0 = Vector((0, 0, z)) + achse(z) + d * stamm_radius(z, H, r0) * 0.6
        pts = [p0, p0 + d * L * 0.5 + Vector((0, 0, -0.05 * L)), p0 + d * L + Vector((0, 0, -0.18 * L))]
        rr = max(0.025, stamm_radius(z, H, r0) * 0.16)
        roehre(b, pts, [rr, rr * 0.55, rr * 0.15], 4, mat)
        if L > 1.0 and rnd.random() < 0.6:
            sa = a + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.1)
            q1 = pts[1] + Vector((math.cos(sa), math.sin(sa), rnd.uniform(-0.2, 0.3))).normalized() * L * rnd.uniform(0.3, 0.5)
            roehre(b, [pts[1], q1], [rr * 0.45, rr * 0.1], 3, mat)
        z += rnd.uniform(0.35, 0.8)

def karte(b, basis, richtung, laenge, breite, drehung, mat):
    """ein Quad: u entlang richtung (0 = Basis), v quer"""
    d = richtung.normalized()
    quer = Matrix.Rotation(drehung, 3, d) @ d.orthogonal().normalized()
    a, e = basis, basis + d * laenge
    b.face((a - quer * breite / 2, a + quer * breite / 2, e + quer * breite / 2, e - quer * breite / 2),
           ((0, 0), (0, 1), (1, 1), (1, 0)), mat)

def buschel(b, p, richtung, groesse, rnd):
    """3 Karten sternförmig um die Richtung, Basis leicht hinter dem Punkt"""
    d = (richtung.normalized() + Vector((0, 0, 0.3))).normalized()
    start = rnd.uniform(0, math.pi)
    for k in range(3):
        karte(b, p - d * groesse * 0.25, d, groesse, groesse * 0.55, start + k * math.pi / 3, NADELN)

def kiefer(alter, seed=1):
    H, dm, kb, ka, quirle, _, bg = KIEFER[alter]
    rnd = random.Random(seed * 104729)
    r0 = dm / 2; R = kb / 2; jung = alter == "jung"
    # Kiefern wachsen krummer als Fichten
    neig_dir = rnd.uniform(0, 2 * math.pi); neig = rnd.uniform(0.05, 0.12) * H
    noff = Vector((seed * 4.1, seed * 7.7, 0))
    def achse(z):
        t = z / H
        return Vector((math.cos(neig_dir), math.sin(neig_dir), 0)) * neig * t * t \
            + Vector((noise.noise(Vector((z * 0.25, 0, 0)) + noff), noise.noise(Vector((0, z * 0.25, 0)) + noff), 0)) * r0 * 1.2
    b = Bau()
    b.stamm(H, r0, H * 0.93, 10 if jung else 12, seed, mat=RINDE, achse=achse,
            mat_oben=RINDE_OBEN, grenze=H * (0.45 if jung else 0.4))
    if alter == "uralt":                                    # untere zwei Drittel: nur kahle Äste
        kahle_aeste(b, H, r0, achse, 2.2, ka - 0.3, rnd, laenge=(0.8, 2.6))
    # abgestorbene Aststummel am kahlen Stamm
    for _ in range(0 if jung or alter == "uralt" else rnd.randint(3, 6)):
        z = rnd.uniform(2.5, ka - 0.5); a = rnd.uniform(0, 2 * math.pi)
        d = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.1, 0.3))).normalized()
        p = Vector((0, 0, z)) + achse(z)
        roehre(b, [p, p + d * rnd.uniform(0.25, 0.6)], [r0 * 0.18, r0 * 0.06], 4, RINDE)
    # Krone: Quirle aus Hauptästen; Umriss jung = Kegel, alt = Schirm (Viertel-Ellipse)
    kh = H - ka
    for q in range(quirle):
        t = (q + rnd.uniform(-0.2, 0.2)) / quirle            # 0 = unten in der Krone
        t = min(max(t, 0.0), 0.92)
        z = ka + kh * t * 0.85
        umriss = (1 - t) ** 0.8 if jung else math.sqrt(max(0.05, 1 - t ** 2))
        anzahl = rnd.randint(4, 6) if not jung else rnd.randint(3, 5)
        start = rnd.uniform(0, 2 * math.pi)
        for j in range(anzahl):
            if rnd.random() < 0.12:
                continue
            a = start + 2 * math.pi * j / anzahl + rnd.uniform(-0.4, 0.4)
            steig = math.radians(rnd.uniform(18, 38) if jung else rnd.uniform(4, 26) + 14 * t)
            d = Vector((math.cos(a) * math.cos(steig), math.sin(a) * math.cos(steig), math.sin(steig)))
            L = R * umriss * rnd.uniform(0.75, 1.1) / max(0.5, math.cos(steig)) * 0.85 + 0.3
            p0 = Vector((0, 0, z)) + achse(z)
            # Ast leicht gebogen: Spitze dreht nach oben
            pts = [p0 + d * L * s + Vector((0, 0, L * 0.12 * s * s)) for s in (0, 0.35, 0.7, 1.0)]
            rad = stamm_radius(z, H, r0) * 0.45
            roehre(b, pts, [rad, rad * 0.7, rad * 0.45, rad * 0.2], 4, RINDE_OBEN)
            # Büschel entlang der äußeren Asthälfte + am Ende, dazu seitliche Zweigpolster
            seite = d.cross(Vector((0, 0, 1))).normalized()
            s = 0.4
            while s <= 1.0:
                k = min(int(s * 3), 2); f = s * 3 - k
                p = pts[k].lerp(pts[k + 1], f) + Vector([rnd.uniform(-0.1, 0.1) for _ in range(3)]) * bg
                richt = d + Vector([rnd.uniform(-0.35, 0.35) for _ in range(3)])
                buschel(b, p, richt, bg * rnd.uniform(0.85, 1.15), rnd)
                if rnd.random() < 0.7:                       # Seitenzweig
                    sv = seite * rnd.choice((-1, 1))
                    buschel(b, p + sv * bg * rnd.uniform(0.35, 0.6), d * 0.6 + sv * 0.8, bg * rnd.uniform(0.7, 0.95), rnd)
                s += rnd.uniform(0.18, 0.26) * (1.4 if jung else 1.0)
    # Wipfel
    pz = H * 0.93; p = Vector((0, 0, pz)) + achse(pz)
    for _ in range(3):
        buschel(b, p + Vector([rnd.uniform(-0.15, 0.15) for _ in range(2)] + [0]),
                Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 1)), bg, rnd)
    return b.bm

def stumpf(alter, seed=1):
    H, dm, *_ , h_stumpf, _bg = KIEFER[alter]
    b = Bau()
    b.stamm(H, dm / 2, h_stumpf, 10 if alter == "jung" else 12, seed, mat=RINDE, deckel_mat=SCHNITT)
    return b.bm

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for alter in KIEFER:
        for v in (1, 2, 3):
            export(f"kiefer_{alter}_{v}", kiefer(alter, seed=v), out)
        export(f"kiefer_stumpf_{alter}", stumpf(alter), out)
