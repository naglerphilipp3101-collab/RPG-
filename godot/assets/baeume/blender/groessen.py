"""Größenvergleich: Bäume (Blockout) + Spieler + Erzbrocken Größe 5. Seitenansicht, 1 Einheit = 1 m.
Aufruf: python groessen.py -- <ausgabe.png>"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, "/home/user/erzbrocken")
from formen import rock_shape

#           name, höhe, stamm_d, krone_breit, krone_ab, form
BAEUME = [("Fichte jung", 5.6, 0.18, 2.1, 2.2, "kegel"),    # 70 % der echten Werte,
          ("Kiefer jung", 4.9, 0.18, 2.5, 2.2, "schirm"),   # Kronen ab >= 2,2 m: Spieler (1,8 m) läuft drunter durch
          ("Eiche jung", 4.5, 0.21, 2.2, 2.0, "kugel"),     # Eiche: schmale, ovale Krone
          ("Fichte alt", 12.6, 0.42, 4.2, 3.5, "kegel"),
          ("Kiefer alt", 11.2, 0.35, 4.9, 6.3, "schirm"),
          ("Eiche alt", 9.8, 0.70, 6.0, 2.8, "kugel")]

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.9
    return m

def obj(name, bm, m):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def zylinder(r1, r2, h, z0, m, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h,
                          matrix=Matrix.Translation((0, 0, z0 + h / 2)))
    return obj("zyl", bm, m)

def ellipsoid(rx, rz, zc, m):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1)
    for v in bm.verts: v.co = Vector((v.co.x * rx, v.co.y * rx, v.co.z * rz + zc))
    return obj("ell", bm, m)

def baum(x, h, d, kb, ka, form, m_stamm, m_krone):
    obs = []
    if form == "kegel":
        obs.append(zylinder(d / 2, d / 6, h * 0.95, 0, m_stamm))
        obs.append(zylinder(kb / 2, 0.05, h - ka, ka, m_krone, 32))
    elif form == "schirm":
        obs.append(zylinder(d / 2, d / 3, h * 0.9, 0, m_stamm))
        kh = h - ka   # flache Schirmkrone: obere Hälfte eines Ellipsoids + flache Unterseite
        obs.append(ellipsoid(kb / 2, kh * 0.75, ka + kh * 0.25, m_krone))
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1)
        for v in bm.verts: v.co = Vector((v.co.x * kb / 2, v.co.y * kb / 2, max(v.co.z, 0) * kh * 0.75 + min(v.co.z, 0) * kh * 0.25 + ka + kh * 0.25))
        bpy.data.objects.remove(obs.pop())
        obs.append(obj("schirm", bm, m_krone))
    else:
        kh = h - ka
        obs.append(zylinder(d / 2, d / 3, ka + kh * 0.4, 0, m_stamm))
        obs.append(ellipsoid(kb / 2, kh / 2, ka + kh / 2, m_krone))
    for o in obs: o.location.x += x

def mensch(x, m):
    zylinder(0.22, 0.2, 1.55, 0, m)                     # Körper
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.13)
    o = obj("kopf", bm, m); o.location = (x, 0, 1.67)
    bpy.data.objects[-1]
    for ob in bpy.data.objects:
        if ob.name.startswith("zyl") and ob.location.x == 0 and ob.get("m") is None and ob.data.materials[0] == m:
            ob.location.x = x

if __name__ == "__main__":
    out = sys.argv[-1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    m_stamm = mat("stamm", (0.12, 0.07, 0.04))
    kronen = {"Fichte": mat("fichte", (0.02, 0.07, 0.04)), "Kiefer": mat("kiefer", (0.06, 0.1, 0.03)),
              "Eiche": mat("eiche", (0.08, 0.16, 0.03))}
    m_mensch = mat("mensch", (0.5, 0.55, 0.65)); m_erz = mat("erz", (0.06, 0.055, 0.05))
    labels = []
    x = 0.0
    # Spieler + Erzbrocken als Maßstab
    mensch(x, m_mensch); labels.append((x, "Spieler\n1,8 m"))
    x += 3.0
    rb = rock_shape(107)  # Form 8 = Größe 5
    for v in rb.verts: v.co *= 1.65 * 0.75
    e = obj("erz", rb, m_erz); e.location.x = x; labels.append((x, "Erz Gr. 5"))
    x += 2.5
    for i, (name, h, d, kb, ka, form) in enumerate(BAEUME):
        if i == 3: x += 2
        x += max(kb / 2 + 1.0, 2.6)
        baum(x, h, d, kb, ka, form, m_stamm, kronen[name.split()[0]])
        labels.append((x, f"{name}\n{str(h).replace('.', ',')} m · Ø {str(d).replace('.', ',')} m\nKrone {str(kb).replace('.', ',')} m, ab {str(ka).replace('.', ',')} m"))
        x += max(kb / 2 + 1.0, 2.6)
    breite = x + 1
    # Boden + Höhenlinien alle 2 m
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=200); obj("boden", bm, mat("b", (0.09, 0.075, 0.05)))
    m_linie = mat("linie", (0.5, 0.5, 0.5))
    for z in range(2, 14, 2):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts: v.co = Vector((v.co.x * (breite + 2) + breite / 2 - 1.5, v.co.y * 0.01 + 30, v.co.z * 0.03 + z))
        obj("linie", bm, m_linie)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts: v.co = Vector((v.co.x * (breite + 2) + breite / 2 - 1.5, v.co.y * 0.01 + 29, v.co.z * 0.04 + 1.8))
    obj("spielerlinie", bm, mat("sl", (0.8, 0.5, 0.1)))
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.65, 0.8, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8; sc.world = w
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3; sun.rotation_euler = (math.radians(60), 0, math.radians(-30))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    hoehe = 17.0
    cam.data.type = "ORTHO"; cam.data.ortho_scale = breite + 4
    cam.location = (breite / 2 - 1, -80, hoehe / 2 - 3.2); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.samples = 32; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.render.resolution_x = 2600; sc.render.resolution_y = int(2600 * hoehe / (breite + 4))
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(out).convert("RGB"); dr = ImageDraw.Draw(img); W, H = img.size
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", 20); fs = ImageFont.truetype("DejaVuSans.ttf", 20)
    for z in range(2, 14, 2):
        q = world_to_camera_view(sc, cam, Vector((0, -30, z)))
        dr.text((8, (1 - q.y) * H), f"{z} m", font=fs, fill=(230, 230, 230), anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
    q = world_to_camera_view(sc, cam, Vector((0, 29, 1.8)))
    dr.text((W - 10, (1 - q.y) * H - 14), "Spielerhöhe 1,8 m", font=fs, fill=(255, 190, 90), anchor="rm", stroke_width=2, stroke_fill=(0, 0, 0))
    for lx, t in labels:
        q = world_to_camera_view(sc, cam, Vector((lx, 0, -0.4)))
        dr.multiline_text((q.x * W, (1 - q.y) * H), t, font=f, fill=(255, 230, 160), anchor="ma", align="center",
                          stroke_width=3, stroke_fill=(0, 0, 0))
    img.save(out)
