"""Baut die Daten für den Basis-Menschen aus MakeHuman (CC0).

Aufruf (Python 3, ohne Blender):
    git clone --depth 1 https://github.com/makehumancommunity/mpfb2
    git clone --depth 1 https://github.com/makehumancommunity/makehuman
    python3 mensch_daten.py <mpfb2-Ordner> <makehuman-Ordner> <godot-Ordner> [<systemassets-Ordner>]

Systemassets: entpacktes makehuman_system_assets_cc0.zip (Haare, Brauen, Wimpern, Zähne,
Zunge, Hauttexturen; CC0) von makehumancommunity.org. Die benötigten Texturen werden nach
godot/assets/charakter/makehuman/ kopiert.

Ergebnis in godot/assets/charakter/daten/:
    mensch.json  Aufbau: Teile, Knochen, Formen (Targets), Regler, Anbauteile
    mensch.bin   Zahlen (im komprimierten Godot-Format "GCPF"/zstd)

Einheiten: MakeHuman rechnet in Dezimetern mit Y nach oben und Blick nach +Z.
Wir speichern Meter (×0,1). Formen als int16 in 1/10000 m.
"""
import gzip
import json
import math
import os
import struct
import sys

import zstandard

MPFB, MH, GODOT = sys.argv[1], sys.argv[2], sys.argv[3]
SYS = sys.argv[4] if len(sys.argv) > 4 else ""
DATA = os.path.join(MPFB, "src", "mpfb", "data")
TARGETS = os.path.join(DATA, "targets")
ZIEL = os.path.join(GODOT, "assets", "charakter", "daten")
os.makedirs(ZIEL, exist_ok=True)

# ---------------------------------------------------------------- Grundnetz
verts, uvs, faces = [], [], []  # faces: (gruppe, [(v, vt), ...])
gruppe = None
with open(os.path.join(DATA, "3dobjs", "base.obj")) as f:
    for z in f:
        if z.startswith("v "):
            verts.append([float(a) * 0.1 for a in z.split()[1:4]])
        elif z.startswith("vt "):
            uvs.append([float(a) for a in z.split()[1:3]])
        elif z.startswith("g "):
            gruppe = z.split()[1]
        elif z.startswith("f "):
            ecken = []
            for t in z.split()[1:]:
                a = t.split("/")
                ecken.append((int(a[0]) - 1, int(a[1]) - 1))
            faces.append((gruppe, ecken))
NV = len(verts)
print("Grundnetz:", NV, "Punkte,", len(faces), "Flächen")

with open(os.path.join(DATA, "mesh_metadata", "basemesh_vertex_groups.json")) as f:
    VGRUPPEN = json.load(f)


def gruppen_punkte(name):
    out = []
    for a, b in VGRUPPEN[name]:
        out.extend(range(a, b + 1))
    return out


# ---------------------------------------------------------------- Binärdaten
puffer = bytearray()


def ablegen(daten: bytes) -> list:
    """Hängt Bytes an (auf 4 ausgerichtet) und gibt [Anfang, Länge] zurück."""
    while len(puffer) % 4:
        puffer.append(0)
    anfang = len(puffer)
    puffer.extend(daten)
    return [anfang, len(daten)]


def f32(werte):
    return struct.pack("<%df" % len(werte), *werte)


def i32(werte):
    return struct.pack("<%di" % len(werte), *werte)


# ---------------------------------------------------------------- Teile (sichtbare Netze)
def teil_bauen(gruppen):
    """Eindeutige (Punkt, UV)-Paare -> Godot-Punkte, Vierecke -> Dreiecke."""
    schluessel = {}
    mh_index, uv_liste, dreiecke = [], [], []
    for g, ecken in faces:
        if g not in gruppen:
            continue
        ids = []
        for v, vt in ecken:
            k = (v, vt)
            if k not in schluessel:
                schluessel[k] = len(mh_index)
                mh_index.append(v)
                uv_liste.extend([uvs[vt][0], 1.0 - uvs[vt][1]])
            ids.append(schluessel[k])
        # Godot: Vorderseite im Uhrzeigersinn -> Reihenfolge umdrehen
        for i in range(1, len(ids) - 1):
            dreiecke.extend([ids[0], ids[i + 1], ids[i]])
    return {
        "punkte": len(mh_index),
        "mh_index": ablegen(i32(mh_index)),
        "uv": ablegen(f32(uv_liste)),
        "dreiecke": ablegen(i32(dreiecke)),
    }


teile = {
    "koerper": teil_bauen({"body"}),
    "wimpern": teil_bauen({"helper-l-eyelashes-1", "helper-l-eyelashes-2",
                           "helper-r-eyelashes-1", "helper-r-eyelashes-2"}),
    "zaehne": teil_bauen({"helper-upper-teeth", "helper-lower-teeth"}),
    "zunge": teil_bauen({"helper-tongue"}),
}
for k, v in teile.items():
    print("Teil", k, v["punkte"], "Punkte")

# ---------------------------------------------------------------- Knochen (Mixamo-Rig -> Godot-Humanoid-Namen)
NAMEN = {
    "Hips": "Hips", "Spine": "Spine", "Spine1": "Chest", "Spine2": "UpperChest",
    "Neck": "Neck", "Head": "Head",
}
for s, gs in (("Left", "Left"), ("Right", "Right")):
    NAMEN.update({
        s + "Shoulder": gs + "Shoulder", s + "Arm": gs + "UpperArm", s + "ForeArm": gs + "LowerArm",
        s + "Hand": gs + "Hand", s + "UpLeg": gs + "UpperLeg", s + "Leg": gs + "LowerLeg",
        s + "Foot": gs + "Foot", s + "ToeBase": gs + "Toes",
        s + "HandThumb1": gs + "ThumbMetacarpal", s + "HandThumb2": gs + "ThumbProximal",
        s + "HandThumb3": gs + "ThumbDistal",
    })
    for mx, gd in (("Index", "Index"), ("Middle", "Middle"), ("Ring", "Ring"), ("Pinky", "Little")):
        NAMEN[s + "Hand" + mx + "1"] = gs + gd + "Proximal"
        NAMEN[s + "Hand" + mx + "2"] = gs + gd + "Intermediate"
        NAMEN[s + "Hand" + mx + "3"] = gs + gd + "Distal"

with open(os.path.join(DATA, "rigs", "standard", "rig.mixamo.json")) as f:
    RIG = json.load(f)["bones"]
with open(os.path.join(DATA, "rigs", "standard", "weights.mixamo.json")) as f:
    GEWICHTE = json.load(f)["weights"]


def punkt_def(d):
    if d["strategy"] == "CUBE":
        return gruppen_punkte(d["cube_name"])
    return list(d["vertex_indices"])


# Reihenfolge: Eltern vor Kindern
knochen_namen = []
offen = list(RIG.keys())
while offen:
    for n in list(offen):
        p = RIG[n]["parent"]
        if not p or p in knochen_namen:
            knochen_namen.append(n)
            offen.remove(n)
knochen = []
for n in knochen_namen:
    b = RIG[n]
    knochen.append({
        "name": NAMEN[n.split(":")[1]],
        "eltern": knochen_namen.index(b["parent"]) if b["parent"] else -1,
        "kopf": punkt_def(b["head"]),
        "ende": punkt_def(b["tail"]),
    })

# Gewichte: je Punkt die 4 stärksten Knochen
je_punkt = [[] for _ in range(NV)]
for n, liste in GEWICHTE.items():
    bi = knochen_namen.index(n)
    for v, w in liste:
        je_punkt[v].append((w, bi))
k_idx, k_gew = [], []
for v in range(NV):
    l = sorted(je_punkt[v], reverse=True)[:4]
    s = sum(w for w, _ in l) or 1.0
    l = l + [(0.0, 0)] * (4 - len(l))
    k_idx.extend(b for _, b in l)
    k_gew.extend(w / s for w, _ in l)

# ---------------------------------------------------------------- Formen (Targets)
def target_lesen(pfad):
    d = {}
    with gzip.open(pfad, "rt") as f:
        for z in f:
            if not z.strip() or z.startswith("#"):
                continue
            a = z.split()
            d[int(a[0])] = [float(a[1]), float(a[2]), float(a[3])]
    return d


formen = {}  # name -> [Anfang, Länge, Anzahl]


def form_ablegen(name, d):
    idx = sorted(i for i in d if any(abs(c) > 1e-5 for c in d[i]))
    werte = []
    for i in idx:
        werte.extend(max(-32767, min(32767, round(c * 1000))) for c in d[i])
    daten = struct.pack("<%dH" % len(idx), *idx)
    if len(idx) % 2:
        daten += b"\0\0"
    daten += struct.pack("<%dh" % len(werte), *werte)
    formen[name] = ablegen(daten) + [len(idx)]


def summe(*ds):
    out = {}
    for d in ds:
        for i, v in d.items():
            o = out.setdefault(i, [0.0, 0.0, 0.0])
            for k in range(3):
                o[k] += v[k]
    return out


def t(rel):
    return target_lesen(os.path.join(TARGETS, rel + ".target.gz"))


MAKRO = os.path.join("macrodetails")
for gesch in ("female", "male"):
    for alter in ("young", "old"):
        for herk in ("african", "asian", "caucasian"):
            form_ablegen("%s-%s-%s" % (herk, gesch, alter), t("macrodetails/%s-%s-%s" % (herk, gesch, alter)))
        for mus in ("minmuscle", "averagemuscle", "maxmuscle"):
            for gew in ("minweight", "averageweight", "maxweight"):
                n = "universal-%s-%s-%s-%s" % (gesch, alter, mus, gew)
                form_ablegen(n, t("macrodetails/" + n))
        for gr in ("minheight", "maxheight"):
            n = "%s-%s-averagemuscle-averageweight-%s" % (gesch, alter, gr)
            form_ablegen("hoehe-%s-%s-%s" % (gesch, alter, gr), t("macrodetails/height/" + n))
    # Brust nur bei Frauen (bei MakeHuman ebenso)
for alter in ("young", "old"):
    for cup in ("mincup", "averagecup", "maxcup"):
        for fest in ("minfirmness", "averagefirmness", "maxfirmness"):
            if cup == "averagecup" and fest == "averagefirmness":
                continue
            n = "female-%s-averagemuscle-averageweight-%s-%s" % (alter, cup, fest)
            form_ablegen("brust-%s-%s-%s" % (alter, cup, fest), t("breast/" + n))

with open(os.path.join(TARGETS, "target.json")) as f:
    TJ = json.load(f)
KATS = {c["name"]: (k, c) for k, v in TJ.items() for c in v["categories"]}

# Regler: (id, Beschriftung, Gruppe, MakeHuman-Kategorie)
REGLER = [
    ("kopf_breite", "Kopfbreite", "Kopf", "head-scale-horiz-decr-incr"),
    ("kopf_hoehe", "Kopfhöhe", "Kopf", "head-scale-vert-decr-incr"),
    ("kopf_tiefe", "Kopftiefe", "Kopf", "head-scale-depth-decr-incr"),
    ("kopf_oval", "Kopf oval", "Kopf", "head-oval"),
    ("kopf_rund", "Kopf rund", "Kopf", "head-round"),
    ("kopf_eckig", "Kopf eckig", "Kopf", "head-square"),
    ("kopf_dreieckig", "Kopf dreieckig", "Kopf", "head-triangular"),
    ("kopf_fett", "Gesichtsfülle", "Kopf", "head-fat-decr-incr"),
    ("stirn_neigung", "Stirnneigung", "Kopf", "forehead-trans-backward-forward"),
    ("stirn_hoehe", "Stirnhöhe", "Kopf", "forehead-scale-vert-decr-incr"),
    ("brauen_hoehe", "Brauenhöhe", "Augen", "eyebrows-trans-down-up"),
    ("brauen_winkel", "Brauenwinkel", "Augen", "eyebrows-angle-down-up"),
    ("brauen_vor", "Brauenwulst", "Augen", "eyebrows-trans-backward-forward"),
    ("augen_groesse", "Augengröße", "Augen", "eye-scale-decr-incr"),
    ("augen_hoehe", "Augenhöhe", "Augen", "eye-trans-down-up"),
    ("augen_abstand", "Augenabstand", "Augen", "eye-trans-in-out"),
    ("augen_tiefe", "Augentiefe", "Augen", "eye-push1-in-out"),
    ("augen_winkel", "Augenwinkel", "Augen", "eye-corner2-down-up"),
    ("augen_oeffnung", "Augenöffnung", "Augen", "eye-height2-decr-incr"),
    ("augen_lidfalte", "Lidfalte", "Augen", "eye-eyefold-down-up"),
    ("augen_mandel", "Mandelform", "Augen", "eye-epicanthus-in-out"),
    ("augen_ringe", "Tränensäcke", "Augen", "eye-bag-decr-incr"),
    ("nase_groesse", "Nasengröße", "Nase", "nose-volume-decr-incr"),
    ("nase_breite", "Nasenbreite", "Nase", "nose-scale-horiz-decr-incr"),
    ("nase_laenge", "Nasenlänge", "Nase", "nose-scale-vert-decr-incr"),
    ("nase_hoehe", "Nasenhöhe", "Nase", "nose-trans-down-up"),
    ("nase_vor", "Nasentiefe", "Nase", "nose-scale-depth-decr-incr"),
    ("nase_hoecker", "Nasenhöcker", "Nase", "nose-hump-decr-incr"),
    ("nase_spitze", "Nasenspitze", "Nase", "nose-point-down-up"),
    ("nase_fluegel", "Nasenflügel", "Nase", "nose-flaring-decr-incr"),
    ("nase_bogen", "Nasenbogen", "Nase", "nose-curve-concave-convex"),
    ("mund_breite", "Mundbreite", "Mund", "mouth-scale-horiz-decr-incr"),
    ("mund_hoehe", "Mundhöhe", "Mund", "mouth-trans-down-up"),
    ("mund_vor", "Mundtiefe", "Mund", "mouth-trans-backward-forward"),
    ("oberlippe", "Oberlippe", "Mund", "mouth-upperlip-volume-decr-incr"),
    ("unterlippe", "Unterlippe", "Mund", "mouth-lowerlip-volume-decr-incr"),
    ("mundwinkel", "Mundwinkel", "Mund", "mouth-angles-down-up"),
    ("kinn_vor", "Kinn vorstehend", "Kinn und Wangen", "chin-prominent-decr-incr"),
    ("kinn_breite", "Kinnbreite", "Kinn und Wangen", "chin-width-decr-incr"),
    ("kinn_hoehe", "Kinnhöhe", "Kinn und Wangen", "chin-height-decr-incr"),
    ("kiefer", "Kieferknochen", "Kinn und Wangen", "chin-bones-decr-incr"),
    ("kinn_gruebchen", "Kinngrübchen", "Kinn und Wangen", "chin-cleft-decr-incr"),
    ("wangenknochen", "Wangenknochen", "Kinn und Wangen", "cheek-bones-decr-incr"),
    ("wangen_voll", "Wangenfülle", "Kinn und Wangen", "cheek-volume-decr-incr"),
    ("wangen_innen", "Wangen eingefallen", "Kinn und Wangen", "cheek-inner-decr-incr"),
    ("ohr_groesse", "Ohrgröße", "Ohren", "ear-scale-decr-incr"),
    ("ohr_abstand", "Abstehende Ohren", "Ohren", "ear-flap-decr-incr"),
    ("ohr_form", "Ohrform spitz/dreieckig", "Ohren", "ear-shape-pointed-triangle"),
    ("ohr_laeppchen", "Ohrläppchen", "Ohren", "ear-lobe-decr-incr"),
    ("hals_dicke", "Halsdicke", "Körper", "neck-scale-horiz-decr-incr"),
    ("hals_laenge", "Halslänge", "Körper", "neck-scale-vert-decr-incr"),
    ("schultern", "Schulterbreite", "Körper", "measure-shoulder-dist-decr-incr"),
    ("v_form", "Oberkörper V-Form", "Körper", "torso-vshape-decr-incr"),
    ("brustmuskel", "Brustmuskel", "Körper", "torso-muscle-pectoral-decr-incr"),
    ("taille", "Taille", "Körper", "measure-waist-circ-decr-incr"),
    ("bauch", "Bauch", "Körper", "stomach-pregnant-decr-incr"),
    ("huefte", "Hüftbreite", "Körper", "hip-scale-horiz-decr-incr"),
    ("po", "Gesäß", "Körper", "buttocks-volume-decr-incr"),
    ("oberarm_muskel", "Oberarmmuskel", "Körper", "upperarm-muscle-decr-incr"),
    ("arm_laenge", "Armlänge", "Körper", "measure-upperarm-length-decr-incr|measure-lowerarm-length-decr-incr"),
    ("bein_laenge", "Beinlänge", "Körper", "upperlegs-height-decr-incr|lowerlegs-height-decr-incr"),
    ("haende", "Handgröße", "Körper", "hand-scale-decr-incr"),
    ("fuesse", "Fußgröße", "Körper", "foot-scale-decr-incr"),
]

regler_json = []
for rid, label, grp, kats in REGLER:
    neg, pos = [], []
    einseitig = False
    for kat in kats.split("|"):
        ordner, c = KATS[kat]
        if "opposites" not in c:
            einseitig = True
            pos.append(t(ordner + "/" + c["targets"][0]))
            continue
        o = c["opposites"]
        for seite, ziel in (("negative", neg), ("positive", pos)):
            namen = [o.get(seite + "-unsided")] if o.get(seite + "-unsided") else [o[seite + "-left"], o[seite + "-right"]]
            ziel.append(summe(*[t(ordner + "/" + n) for n in namen]))
    if neg:
        form_ablegen(rid + "-", summe(*neg))
    form_ablegen(rid + "+", summe(*pos))
    regler_json.append({"id": rid, "name": label, "gruppe": grp, "min": 0.0 if einseitig else -1.0})

# ---------------------------------------------------------------- Augen (MakeHuman-Anbauteil .mhclo)
def mhclo_lesen(pfad_mhclo, pfad_obj):
    ref, skal = [], {}
    in_verts = False
    with open(pfad_mhclo) as f:
        for z in f:
            a = z.split()
            if not a or a[0].startswith("#"):
                continue
            if a[0] in ("x_scale", "y_scale", "z_scale"):
                skal[a[0][0]] = [int(a[1]), int(a[2]), float(a[3]) * 0.1]
            elif a[0] == "verts":
                in_verts = True
            elif in_verts and len(a) == 9 and a[0].isdigit():
                ref.append([int(a[0]), int(a[1]), int(a[2]),
                            float(a[3]), float(a[4]), float(a[5]),
                            float(a[6]) * 0.1, float(a[7]) * 0.1, float(a[8]) * 0.1])
            elif in_verts and len(a) == 1 and a[0].isdigit():
                ref.append([int(a[0]), int(a[0]), int(a[0]), 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            elif in_verts and a[0] in ("delete_verts", "weights", "offsets"):
                in_verts = False
    ov, ouv, of = [], [], []
    with open(pfad_obj) as f:
        for z in f:
            if z.startswith("v "):
                ov.append(z)
            elif z.startswith("vt "):
                ouv.append([float(x) for x in z.split()[1:3]])
            elif z.startswith("f "):
                of.append([tuple(int(x) - 1 for x in e.split("/")[:2]) for e in z.split()[1:]])
    assert len(ref) == len(ov), (len(ref), len(ov))
    # Punkte je (v, vt) aufspalten
    schluessel, quelle, uv_l, dreiecke = {}, [], [], []
    for ecken in of:
        ids = []
        for v, vt in ecken:
            if (v, vt) not in schluessel:
                schluessel[(v, vt)] = len(quelle)
                quelle.append(v)
                uv_l.extend([ouv[vt][0], 1.0 - ouv[vt][1]])
            ids.append(schluessel[(v, vt)])
        for i in range(1, len(ids) - 1):
            dreiecke.extend([ids[0], ids[i + 1], ids[i]])
    bindung = []
    a_idx, a_gew = [], []
    for v in quelle:
        r = ref[v]
        bindung.extend(r)
        # Knochengewichte aus den drei Bezugspunkten mischen (Godot-Index = Rig-Index + 1 wegen "Root")
        summe = {}
        for j in range(3):
            for q in range(4):
                g = k_gew[r[j] * 4 + q] * r[3 + j]
                if g > 0:
                    b = k_idx[r[j] * 4 + q] + 1
                    summe[b] = summe.get(b, 0.0) + g
        beste = sorted(summe.items(), key=lambda e: -e[1])[:4]
        ges = sum(g for _, g in beste) or 1.0
        beste += [(0, 0.0)] * (4 - len(beste))
        a_idx.extend(b for b, _ in beste)
        a_gew.extend(g / ges for _, g in beste)
    return {
        "punkte": len(quelle),
        "knochen_index": ablegen(i32(a_idx)),
        "knochen_gewicht": ablegen(f32(a_gew)),
        "bindung": ablegen(f32(bindung)),  # je Punkt 9 Zahlen: 3 Indizes, 3 Gewichte, Versatz
        "skalierung": skal,
        "uv": ablegen(f32(uv_l)),
        "dreiecke": ablegen(i32(dreiecke)),
    }


anbau = {"augen": mhclo_lesen(os.path.join(MH, "makehuman", "data", "eyes", "high-poly", "high-poly.mhclo"),
                              os.path.join(MH, "makehuman", "data", "eyes", "high-poly", "high-poly.obj"))}
anbau["augen"]["art"] = "augen"
haut = []

if SYS:
    from PIL import Image

    TEX = os.path.join(GODOT, "assets", "charakter", "makehuman")

    def mhmat_lesen(pfad):
        d = {}
        with open(pfad) as f:
            for z in f:
                a = z.split(None, 1)
                if len(a) == 2 and not a[0].startswith("#"):
                    d[a[0]] = a[1].strip()
        return d

    def textur_kopieren(quelle, ziel_rel, jpg=False, max_seite=0):
        ziel = os.path.join(TEX, ziel_rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        im = Image.open(quelle)
        if max_seite and max(im.size) > max_seite:
            im = im.resize((max_seite, max_seite), Image.LANCZOS)
        if jpg:
            im.convert("RGB").save(ziel, quality=90)
        else:
            if im.mode == "P":
                im = im.convert("RGBA")
            im.save(ziel, optimize=True)
        return "res://assets/charakter/makehuman/" + ziel_rel.replace(os.sep, "/")

    for art, ordner, max_seite in (("haar", "hair", 0), ("brauen", "eyebrows", 0), ("wimpern", "eyelashes", 0),
                                   ("zaehne", "teeth", 1024), ("zunge", "tongue", 512)):
        for name in sorted(os.listdir(os.path.join(SYS, ordner))):
            if art == "zaehne" and name != "teeth_base":
                continue
            d = os.path.join(SYS, ordner, name)
            mhclo = [f for f in os.listdir(d) if f.endswith(".mhclo")][0]
            obj = [f for f in os.listdir(d) if f.endswith(".obj")][0]
            mat = mhmat_lesen(os.path.join(d, [f for f in os.listdir(d) if f.endswith(".mhmat")][0]))
            eintrag = mhclo_lesen(os.path.join(d, mhclo), os.path.join(d, obj))
            eintrag["art"] = art
            for schl, feld in (("diffuseTexture", "textur"), ("normalmapTexture", "normal")):
                if schl in mat and os.path.exists(os.path.join(d, mat[schl])):
                    eintrag[feld] = textur_kopieren(os.path.join(d, mat[schl]),
                                                    os.path.join(art, name + "_" + feld + ".png"), max_seite=max_seite)
            if "textur" in eintrag:
                # mittlere Helligkeit der sichtbaren Pixel (für das Umfärben im Shader)
                im = Image.open(os.path.join(d, mat["diffuseTexture"])).convert("RGBA").resize((256, 256))
                hs, n = 0.0, 0
                for r, g, b, a in im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata():
                    if a > 128:
                        hs += (0.3 * r + 0.55 * g + 0.15 * b) / 255.0
                        n += 1
                eintrag["hell"] = round(hs / max(1, n), 4)
            anbau[art + ":" + name] = eintrag
            print("Anbau", art, name, eintrag["punkte"], "Punkte")

    for name in sorted(os.listdir(os.path.join(SYS, "skins"))):
        d = os.path.join(SYS, "skins", name)
        mat = mhmat_lesen(os.path.join(d, name + ".mhmat"))
        quelle = os.path.join(d, mat["diffuseTexture"])
        im = Image.open(quelle).convert("RGB")
        # Mittlere Hautfarbe auf Brust/Bauch (Ausschnitt der Textur); darauf beziehen sich die Hautfarben
        w, h = im.size
        ausschnitt = im.crop((int(0.2 * w), int(0.15 * h), int(0.45 * w), int(0.4 * h))).resize((64, 64))
        px = list(ausschnitt.get_flattened_data() if hasattr(ausschnitt, "get_flattened_data") else ausschnitt.getdata())
        summe_rgb = [sum(p[i] for p in px) for i in range(3)]
        n = len(px)
        mittel = "#%02x%02x%02x" % tuple(round(c / max(1, n)) for c in summe_rgb)
        namensteile = name.split("_")
        haut.append({"id": name, "alter": namensteile[0], "herkunft": namensteile[1], "geschlecht": namensteile[2],
                     "textur": textur_kopieren(quelle, os.path.join("haut", name + ".jpg"), jpg=True),
                     "mittel": mittel})
        print("Haut", name, mittel)

# ---------------------------------------------------------------- Bart- und Stoppelmasken je Punkt
def glatt(a, b, x):
    if a == b:
        return 1.0 if x >= a else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


masken = bytearray()
for (x, y, z) in verts:
    # Koordinaten zurück in MakeHuman-Dezimeter
    x, y, z, ax = x * 10, y * 10, z * 10, abs(x * 10)
    lippen = ((x / 0.30) ** 2 + ((y - 6.56) / 0.13) ** 2 + 0.0)
    ohne_lippen = glatt(1.0, 1.6, lippen) if z > 1.0 else 1.0
    vorne = glatt(-0.2, 0.25, z)
    # Vollbart: Wangen, Kiefer, Kinn, unter dem Kinn
    oben = 6.7 + 0.26 * min(1.0, ax / 0.62)
    unten = 6.1 if z > 0.6 else 6.1 + (0.6 - z) * 0.45
    voll = glatt(oben + 0.06, oben - 0.08, y) * glatt(unten - 0.05, unten + 0.1, y) * vorne * ohne_lippen
    # Schnurrbart zwischen Oberlippe und Nase
    schnurr = glatt(0.36, 0.26, ax) * glatt(6.6, 6.66, y) * glatt(6.8, 6.74, y) * glatt(1.25, 1.4, z)
    # Kinnbart
    kinn = glatt(0.3, 0.2, ax) * glatt(5.95, 6.05, y) * glatt(6.5, 6.44, y) * glatt(0.9, 1.1, z) * ohne_lippen
    # Kopfhaar-Ansatz (Stoppeln): vorne höher, hinten tiefer
    ansatz = 7.82 if z > 1.0 else (7.32 + (z - 0.2) / 0.8 * 0.5 if z > 0.2 else 6.75 + (z + 0.6) / 0.8 * 0.57)
    kopf = glatt(ansatz - 0.04, ansatz + 0.1, y) * (1.0 if y > 6.0 else 0.0)
    if ax > 0.55 and 7.0 < y < 7.55 and 0.0 < z < 0.6:
        kopf *= glatt(0.75, 0.62, ax)  # Ohren frei
    masken.extend(round(255 * max(0.0, min(1.0, v))) for v in (voll, schnurr, kinn, kopf))

# Unterwäsche (Leinen): Hose um die Hüfte, Oberteil um die Brust (nur bei Frauen sichtbar)
waesche = bytearray()
for (x, y, z) in verts:
    x, y, z, ax = x * 10, y * 10, z * 10, abs(x * 10)
    unten_y = -0.25 + min(1.0, ax / 1.6) * 1.05
    # breite, lineare Übergänge: der Shader schneidet bei 0,5 -> gerade Kanten zwischen den Punkten
    def rampe(a, b, v):
        return max(0.0, min(1.0, (v - a) / (b - a)))
    hose = min(rampe(unten_y - 0.15, unten_y + 0.15, y), rampe(1.45, 1.15, y), rampe(2.1, 1.8, ax))
    oben = min(rampe(2.85, 3.15, y), rampe(4.3, 4.0, y), rampe(1.6, 1.3, ax))
    waesche.extend(round(255 * max(0.0, min(1.0, v))) for v in (hose, oben))

# ---------------------------------------------------------------- Schreiben
grund = {
    "masken": ablegen(bytes(masken)),
    "waesche": ablegen(bytes(waesche)),
    "positionen": ablegen(f32([c for v in verts for c in v])),
    "knochen_index": ablegen(i32(k_idx)),
    "knochen_gewicht": ablegen(f32(k_gew)),
}

meta = {
    "quelle": "MakeHuman/MPFB2 (CC0 1.0), siehe LIZENZ_MAKEHUMAN.txt",
    "punkte": NV,
    "grund": grund,
    "teile": teile,
    "knochen": knochen,
    "formen": formen,
    "regler": regler_json,
    "anbau": anbau,
    "haut": haut,
    "gruppen": {k: VGRUPPEN[k] for k in ("helper-hair", "helper-tights", "helper-l-eye", "helper-r-eye", "joint-ground")},
}
with open(os.path.join(ZIEL, "mensch.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))


def gcpf_schreiben(pfad, daten, block=4096 * 16):
    """Godot FileAccessCompressed-Format (COMPRESSION_ZSTD = 2)."""
    cctx = zstandard.ZstdCompressor(level=19)
    bloecke = [cctx.compress(bytes(daten[i:i + block])) for i in range(0, len(daten), block)]
    with open(pfad, "wb") as f:
        f.write(b"GCPF")
        f.write(struct.pack("<III", 2, block, len(daten)))
        # Godot liest (Gesamt / Block) + 1 Blockgrößen
        anzahl = len(daten) // block + 1
        while len(bloecke) < anzahl:
            bloecke.append(cctx.compress(b""))
        for b in bloecke:
            f.write(struct.pack("<I", len(b)))
        for b in bloecke:
            f.write(b)


gcpf_schreiben(os.path.join(ZIEL, "mensch.bin"), puffer)
print("Formen:", len(formen), " Rohdaten:", len(puffer) // 1024, "KB ->",
      os.path.getsize(os.path.join(ZIEL, "mensch.bin")) // 1024, "KB")
