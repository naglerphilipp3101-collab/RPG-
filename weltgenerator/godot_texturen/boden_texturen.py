"""Erzeugt 10 kachelbare Bodentexturen für Terrain3D (1024x1024).
Je Boden 2 Dateien: <name>_albedo_hoehe.png (RGB Farbe, A Höhe) und <name>_normal_rauheit.png (RGB Normale OpenGL, A Rauheit).
Aufruf: python boden_texturen.py <zielordner>"""
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw

S = 1024

def rauschen(fy, fx, seed, s=S):
    """kachelbares Rauschen per Frequenzfilter (0..1); fy/fx = Grenzfrequenz in Zyklen pro Kachel"""
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((s, s))
    ky = np.fft.fftfreq(s)[:, None] * s; kx = np.fft.fftfreq(s)[None, :] * s
    r = np.real(np.fft.ifft2(np.fft.fft2(n) * np.exp(-((ky / fy) ** 2 + (kx / fx) ** 2))))
    return (r - r.min()) / (r.max() - r.min())

def norm(a):
    return (a - a.min()) / (a.max() - a.min() + 1e-9)

def verlauf(t, stops):
    pos = [p for p, _ in stops]; col = np.array([c for _, c in stops], float)
    return np.dstack([np.interp(t, pos, col[:, k]) for k in range(3)])

def halme(seed, anzahl, laenge, breite, farben, winkel=(-0.5, 0.5), s=S):
    """Halme/Nadeln/Striche kachelbar zeichnen -> (farbe RGB, höhe 0..1, maske)"""
    rnd = random.Random(seed)
    big = 3 * s
    farbe = Image.new("RGB", (big, big), (0, 0, 0)); hoehe = Image.new("L", (big, big), 0)
    df, dh = ImageDraw.Draw(farbe), ImageDraw.Draw(hoehe)
    for _ in range(anzahl):
        x, y = rnd.uniform(0, s), rnd.uniform(0, s)
        a = rnd.uniform(*winkel) + rnd.choice((0, math.pi)) * 0
        l = laenge * rnd.uniform(0.6, 1.3)
        c = rnd.choice(farben); hgt = rnd.randint(120, 255)
        for ox in (0, s, 2 * s):
            for oy in (0, s, 2 * s):
                p0 = (x + ox, y + oy); p1 = (x + ox + math.sin(a) * l, y + oy - math.cos(a) * l)
                df.line([p0, p1], fill=c, width=breite); dh.line([p0, p1], fill=hgt, width=breite)
    f = np.array(farbe)[s:2 * s, s:2 * s].astype(float); h = np.array(hoehe)[s:2 * s, s:2 * s].astype(float) / 255
    return f, h, (h > 0).astype(float)

def flecken(seed, anzahl, rmin, rmax, farben, s=S):
    """runde/ovale Flecken (Blätter, Steine) kachelbar"""
    rnd = random.Random(seed)
    big = 3 * s
    farbe = Image.new("RGB", (big, big), (0, 0, 0)); hoehe = Image.new("L", (big, big), 0)
    df, dh = ImageDraw.Draw(farbe), ImageDraw.Draw(hoehe)
    for _ in range(anzahl):
        x, y = rnd.uniform(0, s), rnd.uniform(0, s)
        rx, ry = rnd.uniform(rmin, rmax), rnd.uniform(rmin, rmax) * rnd.uniform(0.5, 1.0)
        c = rnd.choice(farben); hgt = rnd.randint(110, 255)
        for ox in (0, s, 2 * s):
            for oy in (0, s, 2 * s):
                box = [x + ox - rx, y + oy - ry, x + ox + rx, y + oy + ry]
                df.ellipse(box, fill=c); dh.ellipse(box, fill=hgt)
    f = np.array(farbe)[s:2 * s, s:2 * s].astype(float); h = np.array(hoehe)[s:2 * s, s:2 * s].astype(float) / 255
    return f, h, (h > 0).astype(float)

def normalen(h, staerke):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * staerke
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * staerke
    n = np.dstack([-dx, dy, np.ones_like(h)])     # OpenGL (+Y)
    return n / np.linalg.norm(n, axis=2, keepdims=True)

def speichern(out, name, farbe, hoehe, staerke, rauheit):
    rgba = np.dstack([np.clip(farbe, 0, 255), np.clip(hoehe, 0, 1) * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(out, f"{name}_albedo_hoehe.png"))
    n = normalen(hoehe, staerke)
    rauheit = np.broadcast_to(np.asarray(rauheit, float), hoehe.shape)
    rgba = np.dstack([(n * 0.5 + 0.5) * 255, np.clip(rauheit, 0, 1) * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(out, f"{name}_normal_rauheit.png"))

def sand(out):
    korn = rauschen(400, 400, 1); wellen = rauschen(3, 14, 2); fleck = rauschen(6, 6, 3)
    h = norm(0.5 * wellen + 0.3 * korn + 0.2 * fleck)
    farbe = verlauf(h, [(0, (168, 150, 112)), (0.5, (196, 180, 140)), (1, (222, 210, 172))])
    farbe *= (0.92 + 0.16 * korn)[..., None]
    speichern(out, "sand", farbe, h, 3, 0.85 + 0.1 * korn)

def gras(out, name, seed, basis, halmfarben, dichte, laenge):
    boden = rauschen(30, 30, seed)
    f, hh, m = halme(seed + 1, dichte, laenge, 3, halmfarben)
    farbe = verlauf(boden, [(0, (basis[0] * 0.6, basis[1] * 0.6, basis[2] * 0.6)), (1, basis)])
    farbe = farbe * (1 - m[..., None]) + f * m[..., None]
    farbe *= (0.85 + 0.3 * rauschen(5, 5, seed + 2))[..., None]   # großflächige Helligkeit
    h = norm(0.25 * boden + 0.75 * hh)
    speichern(out, name, farbe, h, 6, 0.92 - 0.1 * m)

def laubboden(out):
    boden = rauschen(40, 40, 21)
    farbe = verlauf(boden, [(0, (48, 34, 22)), (1, (82, 60, 38))])
    f, hh, m = flecken(22, 2600, 7, 16, [(122, 74, 32), (150, 98, 40), (104, 62, 30), (138, 112, 52), (90, 70, 36)])
    farbe = farbe * (1 - m[..., None]) + f * m[..., None]
    moos = np.clip((rauschen(8, 8, 23) - 0.6) * 4, 0, 1)
    farbe = farbe * (1 - moos[..., None]) + np.array([60, 84, 34]) * moos[..., None]
    h = norm(0.3 * boden + 0.7 * hh)
    speichern(out, "laubboden", farbe, h, 5, 0.9)

def nadelboden(out):
    boden = rauschen(50, 50, 31)
    farbe = verlauf(boden, [(0, (40, 26, 18)), (1, (78, 50, 32))])
    f, hh, m = halme(32, 9000, 18, 2, [(118, 70, 40), (96, 58, 34), (134, 88, 52), (70, 46, 30)], winkel=(-math.pi, math.pi))
    farbe = farbe * (1 - m[..., None] * 0.9) + f * m[..., None] * 0.9
    zapfen = np.clip((rauschen(60, 60, 33) - 0.85) * 8, 0, 1)
    farbe = farbe * (1 - zapfen[..., None]) + np.array([92, 62, 38]) * zapfen[..., None]
    h = norm(0.4 * boden + 0.6 * hh + 0.3 * zapfen)
    speichern(out, "nadelboden", farbe, h, 5, 0.9)

def sumpf(out):
    schlamm = rauschen(20, 20, 41); fein = rauschen(200, 200, 42)
    farbe = verlauf(schlamm, [(0, (58, 54, 38)), (1, (92, 84, 58))])
    moos = np.clip((rauschen(10, 10, 43) - 0.45) * 3, 0, 1)
    farbe = farbe * (1 - moos[..., None]) + (np.array([74, 96, 44]) * (0.8 + 0.4 * fein)[..., None]) * moos[..., None]
    pfuetze = np.clip((0.35 - rauschen(6, 6, 44)) * 6, 0, 1)
    farbe = farbe * (1 - pfuetze[..., None]) + np.array([46, 50, 40]) * pfuetze[..., None]
    h = norm(0.5 * schlamm + 0.3 * moos + 0.2 * fein - 0.4 * pfuetze)
    speichern(out, "sumpf", farbe, h, 3, 0.9 - 0.45 * pfuetze)

def voronoi(zellen, seed, s=S, verzerrung=None):
    """kachelbares Voronoi: liefert F1, F2 (Abstand in Zellgrößen) und Zell-ID-Zufallswert"""
    rng = np.random.default_rng(seed)
    pkt = rng.random((zellen, zellen, 2)); wert = rng.random((zellen, zellen))
    y, x = np.mgrid[0:s, 0:s] / s * zellen
    if verzerrung is not None:
        x = x + verzerrung[0]; y = y + verzerrung[1]
    cx, cy = np.floor(x).astype(int), np.floor(y).astype(int)
    f1 = np.full((s, s), 9.0); f2 = np.full((s, s), 9.0); wid = np.zeros((s, s))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            gx, gy = cx + dx, cy + dy
            p = pkt[gy % zellen, gx % zellen]
            d = np.hypot(gx + p[..., 0] - x, gy + p[..., 1] - y)
            neu = d < f1
            f2 = np.where(neu, f1, np.minimum(f2, d)); wid = np.where(neu, wert[gy % zellen, gx % zellen], wid); f1 = np.where(neu, d, f1)
    return f1, f2, wid

def fels(out):
    # geschichtetes Gestein: schräge Bänder + grobe Brocken; Bruchkanten nur als feines Relief
    verz = (rauschen(10, 10, 59) - 0.5) * 0.6, (rauschen(10, 10, 60) - 0.5) * 0.6
    f1, f2, wid = voronoi(5, 51, verzerrung=verz)
    kante = np.clip((f2 - f1) * 10, 0, 1)
    maske = np.clip((rauschen(6, 6, 61) - 0.4) * 3, 0, 1)        # Brüche nur stellenweise
    bruch = 1 - (1 - kante) * maske
    baender = rauschen(14, 3, 58); grob = rauschen(12, 12, 62); mittel = rauschen(40, 40, 56); fein = rauschen(180, 180, 53)
    h = norm(0.3 * baender + 0.3 * grob + 0.2 * mittel + 0.1 * fein + 0.25 * bruch + 0.1 * wid * maske)
    hell = norm(0.35 * baender + 0.3 * grob + 0.2 * mittel + 0.15 * fein)
    farbe = verlauf(hell, [(0, (78, 74, 68)), (0.45, (112, 106, 98)), (0.8, (138, 132, 122)), (1, (160, 154, 144))])
    farbe *= (0.8 + 0.2 * bruch)[..., None]
    flechte = np.clip((rauschen(12, 12, 55) - 0.72) * 5, 0, 1)
    farbe = farbe * (1 - 0.45 * flechte[..., None]) + np.array([118, 124, 90]) * 0.45 * flechte[..., None]
    speichern(out, "fels", farbe, h, 9, 0.8 + 0.15 * fein)

def schnee(out):
    wellen = rauschen(6, 6, 61); fein = rauschen(250, 250, 62)
    h = norm(0.7 * wellen + 0.3 * fein)
    farbe = verlauf(h, [(0, (196, 206, 222)), (1, (244, 247, 252))])
    speichern(out, "schnee", farbe, h, 2, 0.55 - 0.3 * (fein > 0.9))

def weg(out):
    # festgetretener Erdweg mit Kies und Fahrspuren (Spuren laufen entlang V; Terrain3D dreht nicht – daher dezent)
    erde = rauschen(30, 30, 81); fein = rauschen(220, 220, 82)
    f, hh, m = flecken(83, 5200, 2, 6, [(128, 118, 100), (146, 136, 118), (104, 96, 84), (160, 150, 130)])
    h = norm(0.4 * erde + 0.25 * fein + 0.35 * hh)
    farbe = verlauf(erde, [(0, (92, 76, 56)), (0.5, (118, 100, 74)), (1, (138, 120, 92))])
    farbe = farbe * (1 - 0.7 * m[..., None]) + f * 0.7 * m[..., None]
    farbe *= (0.9 + 0.2 * fein)[..., None]
    speichern(out, "weg", farbe, h, 4, 0.9)

def kies(out):
    # Flussbett: runde, glatte Kiesel in drei Größen (grau bis beige), dazwischen dunkler nasser Sand
    sand_ = rauschen(60, 60, 91); fein = rauschen(260, 260, 92); fleck = rauschen(5, 5, 94)
    farben = np.array([(116, 112, 104), (134, 128, 118), (98, 95, 90), (140, 130, 112), (120, 108, 96), (88, 86, 82), (150, 146, 136)], float)
    h = 0.18 * sand_ + 0.08 * fein
    farbe = verlauf(sand_, [(0, (64, 58, 48)), (1, (96, 86, 70))])
    for zellen, seed, staerke, anteil in ((9, 93, 1.0, 0.5), (20, 95, 0.8, 0.8), (44, 97, 0.55, 0.95), (90, 99, 0.35, 0.95)):
        verz = (rauschen(10, 10, seed + 7) - 0.5) * 0.35, (rauschen(10, 10, seed + 8) - 0.5) * 0.35
        f1, f2, wid = voronoi(zellen, seed, verzerrung=verz)
        radius = 0.24 + 0.18 * ((wid * 7.31) % 1.0)             # je Kiesel eigene Größe (in Zellgrößen)
        t = np.clip(1 - (f1 / radius) ** 2, 0, 1)
        kuppe = np.sqrt(t) * (wid < anteil)                       # nicht jede Zelle hat einen Kiesel
        neu = kuppe * staerke > h
        idx = (wid * 997).astype(int) % len(farben)
        c = farben[idx] * (0.72 + 0.38 * kuppe)[..., None] * (0.94 + 0.1 * fein)[..., None]
        m = (neu * np.clip(kuppe * 4, 0, 1))[..., None]
        farbe = farbe * (1 - m) + c * m
        h = np.where(neu, kuppe * staerke, h)
    farbe *= (0.9 + 0.2 * fleck)[..., None]
    h = norm(h)
    speichern(out, "kies", farbe, h, 6, 0.5 + 0.4 * (1 - h))

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    sand(out)
    gras(out, "wiese", 11, (70, 96, 40), [(84, 124, 46), (100, 140, 54), (70, 108, 38), (118, 150, 62)], 26000, 26)
    laubboden(out)
    nadelboden(out)
    sumpf(out)
    gras(out, "steppe", 71, (122, 104, 64), [(176, 158, 92), (156, 140, 80), (196, 178, 110), (138, 128, 72)], 15000, 30)
    fels(out)
    schnee(out)
    weg(out)
    kies(out)
    print(sorted(os.listdir(out)))
