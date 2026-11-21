# Wandelt Poly-Haven-.blend.zip (4K, EXR/PNG) in Bibliotheks-Dateien <id>_<map>_2k.jpg um
# Aufruf: python3 blend_zip_umwandeln.py <id>_4k.blend.zip godot/assets/bibliothek/texturen/<gruppe>/<id>
# Braucht: pip install opencv-python-headless OpenEXR. Gleiche Dateinamen wie bibliothek_laden.ps1, das Skript überspringt sie dann.
import sys, os, zipfile, re
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2, numpy as np
quelle, ziel = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(quelle)
id_ = os.path.basename(quelle).replace("_4k.blend.zip", "")
os.makedirs(ziel, exist_ok=True)
namen = {"diff": "diffuse", "nor_gl": "nor_gl", "rough": "rough", "ao": "ao", "disp": "displacement", "metal": "metal", "arm": "arm"}
def lesen(n):
    daten = z.read(n)
    if n.endswith(".exr"):   # OpenCV-Wheels lesen kein EXR, daher das OpenEXR-Paket
        import OpenEXR, tempfile
        with tempfile.NamedTemporaryFile(suffix=".exr") as t:
            t.write(daten); t.flush()
            with OpenEXR.File(t.name) as f:
                k = f.channels()
                if "RGB" in k: return np.ascontiguousarray(k["RGB"].pixels[:, :, ::-1]).astype(np.float32)
                if "RGBA" in k: return np.ascontiguousarray(k["RGBA"].pixels[:, :, 2::-1]).astype(np.float32)
                ch = {n: c.pixels for n, c in k.items()}
                if all(c in ch for c in "RGB"): return np.dstack([ch["B"], ch["G"], ch["R"]]).astype(np.float32)
                return next(iter(ch.values())).astype(np.float32)
    return cv2.imdecode(np.frombuffer(daten, np.uint8), cv2.IMREAD_UNCHANGED)
def schreiben(art, img):
    if img.dtype != np.uint8:
        f = img.astype(np.float32)
        if img.dtype == np.uint16: f /= 65535.0
        img = (np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)
    if img.ndim == 3 and img.shape[2] == 4: img = img[:, :, :3]
    img = cv2.resize(img, (2048, 2048), interpolation=cv2.INTER_AREA)
    p = os.path.join(ziel, f"{id_}_{art}_2k.jpg")
    cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 92]); print("  ", os.path.basename(p))
for n in z.namelist():
    m = re.match(rf"textures/{re.escape(id_)}_(diff|nor_gl|rough|ao|disp|metal|arm)_4k\.\w+$", n)
    if not m: continue
    art = namen[m.group(1)]; img = lesen(n)
    if art == "arm":   # gepackt: R=AO, G=Rauheit, B=Metall (OpenCV liest BGR)
        if img.dtype != np.uint8: img = img.astype(np.float32)
        schreiben("ao", img[:, :, 2]); schreiben("rough", img[:, :, 1])
        if img[:, :, 0].max() > (0.02 if img.dtype != np.uint8 else 5): schreiben("metal", img[:, :, 0])
    else:
        schreiben(art, img)
print(id_, sorted(x for x in z.namelist() if x.startswith("textures/")))
