"""Kachelbare Texturen für die Props, rein prozedural mit numpy (keine Downloads).
Aufruf: python texturen.py -- <zielordner/texturen>
Je Material drei Bilder (1024², JPG): <name>_farbe.jpg, <name>_normal.jpg (OpenGL, wie Godot), <name>_rauheit.jpg.
Alle Muster entstehen über FFT-gefiltertes Rauschen und ganzzahlige Wellen, darum kacheln sie nahtlos.
Die Kachelgröße in Metern steht in KACHEL (die Modell-UVs und die Godot-Materialien rechnen damit)."""
import sys, os
import numpy as np

N = 1024
## Kachelgröße in Metern (u, v) je Material. Holz: u entlang der Faser
KACHEL = {
    "holz": (2.0, 0.5), "holz_alt": (2.0, 0.5), "holz_verkohlt": (1.0, 1.0), "eisen": (0.5, 0.5),
    "stoff": (1.0, 1.0), "seil": (0.25, 0.25), "stein": (1.0, 1.0), "putz": (1.5, 1.5),
    "schindeln": (1.0, 1.0), "dielen": (2.0, 2.0), "glut": (0.5, 0.5),
}


def rauschen(rnd, sx, sy=None, n=N):
    """Kachelbares Rauschen: weißes Rauschen, im Frequenzraum mit einer Gaußglocke geglättet.
    sx/sy = Strukturgröße in Pixeln entlang x (Spalten) und y (Zeilen). Ergebnis normiert auf Mittel 0, Std 1."""
    sy = sx if sy is None else sy
    w = rnd.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    filt = np.exp(-2 * (np.pi ** 2) * ((fx * sx) ** 2 + (fy * sy) ** 2))
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    return (r - r.mean()) / (r.std() + 1e-9)


def fbm(rnd, groesse, oktaven=5, streck=(1.0, 1.0), abfall=0.5):
    erg = np.zeros((N, N)); amp = 1.0; s = groesse; summe = 0
    for _ in range(oktaven):
        erg += amp * rauschen(rnd, s * streck[0], s * streck[1]); summe += amp
        amp *= abfall; s *= 0.5
        if s < 0.6:
            break
    return erg / summe


def norm01(a):
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)


def mischen(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 else t
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def voronoi(rnd, zellen, n=N):
    """Kachelbarer Abstand zum nächsten und zweitnächsten Punkt (in Pixeln), dazu die Zellnummer."""
    pkt = rnd.uniform(0, n, (zellen, 2))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d1 = np.full((n, n), 1e9, np.float32); d2 = d1.copy(); idx = np.zeros((n, n), np.int32)
    for i, (px, py) in enumerate(pkt):
        dx = np.abs(xx - px); dx = np.minimum(dx, n - dx)
        dy = np.abs(yy - py); dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx * dx + dy * dy)
        neu = d < d1
        d2 = np.where(neu, d1, np.minimum(d2, d)); idx = np.where(neu, i, idx); d1 = np.where(neu, d, d1)
    return d1, d2, idx


def normalen(hoehe, staerke):
    """Normal-Map (OpenGL: grün = oben) aus einer Höhe 0..1, kachelbar über np.roll."""
    dx = (np.roll(hoehe, -1, 1) - np.roll(hoehe, 1, 1)) * 0.5 * staerke
    dy = (np.roll(hoehe, -1, 0) - np.roll(hoehe, 1, 0)) * 0.5 * staerke
    # Zeile 0 ist im fertigen Bild oben, v wächst nach oben -> dy umdrehen
    n = np.dstack([-dx, dy, np.ones_like(hoehe)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def maserung(rnd, ringe, verzug, faser):
    """Holzmaserung entlang x: Jahresringe als verzogene Wellen in y, dazu feine Fasern."""
    y = np.mgrid[0:N, 0:N][0] / N
    v = fbm(rnd, 220, 4, (3.5, 0.6)) * verzug
    ring = 0.5 + 0.5 * np.sin(2 * np.pi * (ringe * y + v))
    ring = ring ** 3                                          # schmale dunkle Spätholz-Bänder
    fasern = rauschen(rnd, 60, 0.9) * 0.6 + rauschen(rnd, 14, 0.6) * 0.4
    return ring, fasern * faser


def aeste(rnd, anzahl, groesse):
    """Astlöcher: dunkle Ellipsen mit Ringen drumherum. Liefert Dunkelheit 0..1 und Verzerrung."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    dunkel = np.zeros((N, N)); verzug = np.zeros((N, N))
    for _ in range(anzahl):
        px, py = rnd.uniform(0, N, 2); r = groesse * rnd.uniform(0.6, 1.3)
        dx = np.abs(xx - px); dx = np.minimum(dx, N - dx) / 3.2      # in Faserrichtung gestreckt
        dy = np.abs(yy - py); dy = np.minimum(dy, N - dy)
        d = np.sqrt(dx * dx + dy * dy) / r
        dunkel = np.maximum(dunkel, np.clip(1.2 - d, 0, 1) ** 1.5)
        verzug += np.exp(-d * d * 0.35) * 0.35
    return dunkel, verzug


def holz(rnd, hell, dunkel, alt=0.0):
    ring, fasern = maserung(rnd, 9, 0.9, 1.0)
    ast_d, _ = aeste(rnd, 3, 9)
    grob = fbm(rnd, 300, 3)
    t = np.clip(0.55 * ring + 0.12 * fasern + 0.12 * grob + 0.15, 0, 1)
    t = np.maximum(t, ast_d * 0.95)
    farbe = mischen(hell, dunkel, t)
    risse = np.zeros((N, N))
    if alt > 0:
        # Verwittert: graue Ausbleichung, lange Trockenrisse entlang der Faser
        grau = np.clip(0.5 + 0.5 * fbm(rnd, 160, 4), 0, 1)[..., None]
        farbe = mischen(farbe, np.full(3, farbe.mean()) * 1.05, grau[..., 0] * alt * 0.8)
        riss = 1 - np.abs(rauschen(rnd, 120, 2.2))
        risse = np.clip((riss - 0.93) / 0.07, 0, 1) * np.clip(rauschen(rnd, 200, 40) + 0.3, 0, 1)
        farbe = mischen(farbe, np.array(dunkel) * 0.35, risse * alt)
    farbe *= (1 + 0.06 * fbm(rnd, 40, 3, (4, 0.5)))[..., None]
    hoehe = 0.5 - 0.25 * ring + 0.12 * fasern - 0.6 * risse - 0.2 * ast_d
    rau = np.clip(0.68 + 0.12 * ring + 0.08 * fasern + 0.15 * alt + 0.2 * risse, 0, 1)
    return farbe, norm01(hoehe), rau, 3.0


def holz_verkohlt(rnd):
    d1, d2, idx = voronoi(rnd, 140)
    kante = np.clip((d2 - d1) / 9.0, 0, 1)                  # 0 in den Fugen
    buckel = np.sqrt(np.clip(d2 - d1, 0, 60) / 60)
    k = fbm(rnd, 80, 4)
    farbe = mischen([0.012, 0.011, 0.010], [0.07, 0.065, 0.06], np.clip(buckel * 0.7 + 0.15 * k, 0, 1))
    # vereinzelt noch braunes Holz in den Fugen, grau-weiße Asche auf den Buckeln
    asche = np.clip(fbm(rnd, 120, 4) * 0.7 - 0.35, 0, 1)
    farbe = mischen(farbe, [0.35, 0.33, 0.31], asche * buckel)
    farbe = mischen(farbe, [0.09, 0.04, 0.02], (1 - kante) * 0.6)
    hoehe = buckel * 0.8 + 0.1 * k
    rau = np.clip(0.75 + 0.2 * (1 - buckel) - 0.25 * asche, 0, 1)
    return farbe, norm01(hoehe), rau, 6.0


def eisen(rnd):
    beulen = fbm(rnd, 26, 4)                                  # gehämmert
    rost_m = fbm(rnd, 50, 6)
    rost = np.clip((rost_m - 0.55) * 2.5, 0, 1)
    flecken = np.clip(rauschen(rnd, 6) * 0.5 + 0.5, 0, 1)
    farbe = mischen([0.10, 0.10, 0.11], [0.16, 0.155, 0.15], np.clip(0.5 + 0.3 * beulen, 0, 1))
    rostfarbe = mischen([0.32, 0.13, 0.05], [0.45, 0.24, 0.10], flecken)
    farbe = mischen(farbe, rostfarbe, rost * 0.85)
    hoehe = 0.5 + 0.25 * beulen + 0.25 * rost * flecken
    rau = np.clip(0.45 + 0.15 * beulen + 0.4 * rost, 0, 1)
    return farbe, norm01(hoehe), rau, 2.5


def stoff(rnd):
    yy, xx = np.mgrid[0:N, 0:N] / N
    f = 160                                                    # Fäden je Kachel (1 m)
    kette = np.abs(np.sin(np.pi * f * xx + 0.5 * rauschen(rnd, 30)))
    schuss = np.abs(np.sin(np.pi * f * yy + 0.5 * rauschen(rnd, 30)))
    oben = (np.floor(f * xx) + np.floor(f * yy)) % 2         # Leinwandbindung
    gewebe = np.where(oben > 0, kette, schuss) * 0.6 + 0.4 * kette * schuss
    schmutz = np.clip(fbm(rnd, 180, 5) * 0.6, -1, 1)
    farbe = mischen([0.60, 0.53, 0.40], [0.44, 0.38, 0.28], np.clip(0.5 + 0.5 * schmutz, 0, 1))
    farbe *= (0.86 + 0.14 * gewebe)[..., None]
    flecken = np.clip(fbm(rnd, 60, 4) - 0.9, 0, 1) * 2
    farbe = mischen(farbe, [0.30, 0.25, 0.18], flecken)
    return farbe, norm01(gewebe + 0.2 * schmutz), np.clip(0.88 + 0.08 * gewebe, 0, 1), 2.0


def seil(rnd):
    yy, xx = np.mgrid[0:N, 0:N] / N
    litzen = 0.5 + 0.5 * np.sin(2 * np.pi * (6 * xx + 3 * yy))    # schräg gedrehte Litzen
    litzen = litzen ** 0.6
    fasern = rauschen(rnd, 18, 2)
    farbe = mischen([0.30, 0.24, 0.15], [0.58, 0.49, 0.33], np.clip(litzen * 0.8 + 0.1 * fasern + 0.1, 0, 1))
    return farbe, norm01(litzen + 0.15 * fasern), np.full((N, N), 0.92), 4.0


def stein(rnd):
    grob = fbm(rnd, 260, 6)
    koernung = rauschen(rnd, 2.0)
    poren = np.clip(-rauschen(rnd, 3.5) - 1.9, 0, 1)
    farbe = mischen([0.24, 0.23, 0.21], [0.47, 0.45, 0.41], np.clip(0.5 + 0.3 * grob + 0.1 * koernung, 0, 1))
    farbe = mischen(farbe, [0.16, 0.15, 0.14], poren)
    verfaerb = np.clip(fbm(rnd, 200, 4) - 0.4, 0, 1)
    farbe = mischen(farbe, [0.40, 0.38, 0.28], verfaerb * 0.6)  # Flechten-Stich ins Gelbgrüne
    hoehe = 0.5 + 0.35 * grob + 0.05 * koernung - 0.4 * poren
    return farbe, norm01(hoehe), np.clip(0.82 + 0.1 * koernung * 0.3 + 0.1 * poren, 0, 1), 2.0


def putz(rnd):
    grob = fbm(rnd, 220, 6)
    fein = rauschen(rnd, 1.5)
    schmutz = np.clip(fbm(rnd, 300, 4) * 0.5, 0, 1)
    farbe = mischen([0.74, 0.70, 0.61], [0.55, 0.50, 0.41], np.clip(0.25 + 0.2 * grob + schmutz * 0.6, 0, 1))
    farbe *= (1 + 0.025 * fein)[..., None]
    abplatz = np.clip((fbm(rnd, 90, 5) - 1.5) * 4, 0, 1)        # wenige Abplatzer
    farbe = mischen(farbe, [0.42, 0.37, 0.30], abplatz)
    hoehe = 0.5 + 0.3 * grob + 0.06 * fein - 0.5 * abplatz
    return farbe, norm01(hoehe), np.clip(0.9 + 0.05 * fein, 0, 1), 3.0


def schindeln(rnd):
    """Holzschindeln: 5 Reihen à 20 cm, versetzt, jede Schindel unten dicker (Höhe steigt nach unten)."""
    reihen = 5; rh = N // reihen
    hoehe = np.zeros((N, N)); farbe = np.zeros((N, N, 3)); fuge = np.zeros((N, N))
    ring, fasern = maserung(rnd, 30, 0.8, 1.0)
    for r in range(reihen):
        # Breiten 9..16 cm, Summe genau 1 m (kachelbar)
        b = []
        while sum(b) < N - 180:
            b.append(int(rnd.uniform(92, 164)))
        b.append(N - sum(b))
        ver = int(rnd.uniform(0, N))
        x0 = 0
        for w in b:
            ton = rnd.uniform(-1, 1)
            y0 = r * rh
            for i in range(w):
                x = (x0 + i + ver) % N
                ys = np.arange(rh)
                t = ys / rh                                  # 0 oben, 1 unten (Zeile 0 ist oben)
                hoehe[y0:y0 + rh, x] = 0.25 + 0.6 * t
                rand = min(i, w - 1 - i)
                fuge[y0:y0 + rh, x] = 1.0 if rand < 3 else 0.0
                farbe[y0:y0 + rh, x] = [0.36 + 0.07 * ton, 0.27 + 0.05 * ton, 0.19 + 0.03 * ton]
            x0 += w
        fuge[y0 + rh - 4:y0 + rh, :] = 1.0                    # Schattenkante unter jeder Reihe
    alt = np.clip(fbm(rnd, 200, 4) * 0.5 + 0.5, 0, 1)
    farbe = mischen(farbe, [0.33, 0.31, 0.29], alt * 0.6)
    farbe *= (0.85 + 0.15 * (1 - ring) + 0.04 * fasern)[..., None]
    farbe = mischen(farbe, [0.05, 0.04, 0.03], fuge * 0.9)
    moos = np.clip((fbm(rnd, 100, 5) - 0.75) * 3, 0, 1) * (hoehe < 0.5)
    farbe = mischen(farbe, [0.22, 0.26, 0.10], moos * 0.8)
    hoehe = hoehe - 0.5 * fuge + 0.05 * fasern
    return farbe, norm01(hoehe), np.clip(0.8 + 0.15 * fuge, 0, 1), 6.0


def dielen(rnd):
    """Holzboden: Bretter 20 cm breit entlang x (10 je 2 m), Stoßfugen versetzt."""
    breit = N // 10
    farbe = np.zeros((N, N, 3)); hoehe = np.zeros((N, N)); rau = np.zeros((N, N))
    for b in range(10):
        f, h, r, _ = holz(rnd, [0.50, 0.36, 0.22], [0.27, 0.17, 0.09], alt=0.25)
        ton = rnd.uniform(0.85, 1.1)
        y0 = b * breit; y1 = N if b == 9 else y0 + breit
        sl = slice(y0, y1)
        farbe[sl] = f[sl] * ton; hoehe[sl] = h[sl]; rau[sl] = r[sl]
        # Fuge längs und eine Stoßfuge pro Brett
        hoehe[y0:y0 + 3] = 0; farbe[y0:y0 + 3] *= 0.25
        sx = int(rnd.uniform(0, N))
        for dx in range(-2, 2):
            hoehe[sl, (sx + dx) % N] = 0; farbe[sl, (sx + dx) % N] *= 0.25
    return farbe, norm01(hoehe), rau, 3.0


def glut(rnd):
    d1, d2, _ = voronoi(rnd, 90)
    riss = np.clip(1 - (d2 - d1) / 7.0, 0, 1)                  # leuchtende Fugen
    flack = np.clip(fbm(rnd, 60, 4) * 0.5 + 0.5, 0, 1)
    farbe = mischen([0.02, 0.015, 0.012], [0.08, 0.06, 0.05], np.clip((d2 - d1) / 40, 0, 1))
    leucht = riss * flack
    farbe = mischen(farbe, [1.0, 0.38, 0.06], leucht)
    return farbe, norm01(-riss), np.full((N, N), 0.9), 4.0


ERZEUGER = {
    "holz": lambda r: holz(r, [0.47, 0.32, 0.18], [0.23, 0.13, 0.06], alt=0.15),
    "holz_alt": lambda r: holz(r, [0.44, 0.39, 0.33], [0.22, 0.18, 0.15], alt=1.0),
    "holz_verkohlt": holz_verkohlt, "eisen": eisen, "stoff": stoff, "seil": seil, "stein": stein,
    "putz": putz, "schindeln": schindeln, "dielen": dielen, "glut": glut,
}


def speichern(daten, pfad):
    import bpy
    d = np.clip(daten, 0, 1)
    if d.ndim == 2:
        d = np.dstack([d, d, d])
    rgba = np.dstack([d, np.ones(d.shape[:2])])[::-1]          # Blender: Zeile 0 unten
    img = bpy.data.images.new(os.path.basename(pfad), d.shape[1], d.shape[0], alpha=False)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = pfad; img.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    img.save(filepath=pfad, quality=90)
    bpy.data.images.remove(img)


def erzeugen(ziel, namen=None):
    os.makedirs(ziel, exist_ok=True)
    for i, (name, fn) in enumerate(ERZEUGER.items()):
        if namen and name not in namen:
            continue
        rnd = np.random.default_rng(4100 + i)
        farbe, hoehe, rau, staerke = fn(rnd)
        speichern(farbe, os.path.join(ziel, f"{name}_farbe.jpg"))
        speichern(normalen(hoehe, staerke), os.path.join(ziel, f"{name}_normal.jpg"))
        speichern(rau, os.path.join(ziel, f"{name}_rauheit.jpg"))
        print("Textur", name)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    erzeugen(args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "texturen"),
             args[1:] or None)
