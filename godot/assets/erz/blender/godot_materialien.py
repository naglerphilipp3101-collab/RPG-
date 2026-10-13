"""Schreibt die Godot-Materialien (.tres) aus den Tier-Definitionen in tiers.py.
Aufruf: python godot_materialien.py <zielordner/materialien>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tiers import TIERS

SLUG = {"T1 Iron": "iron", "T2 Palladium": "palladium", "T3 Mithril": "mithril",
        "T4 Glacialore": "glacialore", "T5 Sungold": "sungold", "T6 Darksteel": "darksteel"}

def srgb(c):  # Blender rechnet linear, Godot-Farben im Inspector sind sRGB
    f = lambda x: 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return "Color(%.4f, %.4f, %.4f, 1)" % tuple(f(max(0.0, min(1.0, x))) for x in c)

def shader_material(t, schutt=False):
    p = {
        "gestein_dunkel": srgb(t["base"][0]), "gestein_hell": srgb(t["base"][1]),
        "gestein_metall": t["base_metal"], "gestein_rauheit": t["base_rough"],
        "muster": 0 if t["kind"] == "spots" else 1,
        "menge": t.get("amount", 0.5) - 0.15 + (0.1 if schutt else 0.0),
        "weichheit": t.get("soft", 0.06),
        "aderbreite": t.get("width", 0.022) * (1.6 if schutt else 1.0),
        "mit_rand": "true" if t.get("halo") else "false",
        "rand_farbe": srgb(t.get("halo") or (0, 0, 0)),
        "erz_farbe": srgb(t["ore"]), "erz_metall": t["ore_metal"], "erz_rauheit": t["ore_rough"],
        "leucht_farbe": srgb(t["emit"][0] if t.get("emit") else (0, 0, 0)),
        "leucht_staerke": t["emit"][1] if t.get("emit") else 0.0,
        "muster_skalierung": 3.5 if schutt else 1.0,
    }
    lines = ['[gd_resource type="ShaderMaterial" load_steps=4 format=3]', "",
             '[ext_resource type="Shader" path="erz.gdshader" id="1"]',
             '[ext_resource type="Texture2D" path="noise_fbm.tres" id="2"]',
             '[ext_resource type="Texture2D" path="noise_zellen.tres" id="3"]', "",
             "[resource]", 'shader = ExtResource("1")']
    lines += [f"shader_parameter/{k} = {v}" for k, v in p.items()]
    lines += ['shader_parameter/noise_fbm = ExtResource("2")', 'shader_parameter/noise_zellen = ExtResource("3")', ""]
    return "\n".join(lines)

def crystal_material(c):
    col = srgb(c["col"]); a = 1.0 - c["transmission"] * 0.4
    lines = ['[gd_resource type="StandardMaterial3D" format=3]', "", "[resource]"]
    if a < 1: lines += ["transparency = 1"]
    lines += [f"albedo_color = {col[:-2]}{a:.2f})", "metallic_specular = 0.9", f"roughness = {0.08 if a < 1 else 0.25}",
              "emission_enabled = true", f"emission = {srgb(c['emit'][0])}",
              f"emission_energy_multiplier = {c['emit'][1] * (0.8 if a < 1 else 0.3):.2f}"]
    if a < 1: lines += ["rim_enabled = true", "rim = 0.4"]   # Eiskristalle: heller Rand
    lines += [""]
    return "\n".join(lines)

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    for name, t in TIERS.items():
        s = SLUG[name]
        open(os.path.join(out, f"erz_{s}.tres"), "w").write(shader_material(t))
        open(os.path.join(out, f"schutt_{s}.tres"), "w").write(shader_material(t, schutt=True))
        if "crystals" in t:
            open(os.path.join(out, f"kristall_{s}.tres"), "w").write(crystal_material(t["crystals"]))
    print(sorted(os.listdir(out)))
