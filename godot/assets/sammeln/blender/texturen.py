"""Erzeugt Baum-Texturen (kachelbar) per numpy/PIL.
Aufruf: python texturen.py <zielordner>"""
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def fft_noise(h, w, fy, fx, seed):
    """Kachelbares Rauschen: Filter im Frequenzraum. fy/fx = Grenzfrequenz je Achse (anisotrop)."""
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h; kx = np.fft.fftfreq(w)[None, :] * w
    filt = np.exp(-((ky / fy) ** 2 + (kx / fx) ** 2))
    r = np.real(np.fft.ifft2(np.fft.fft2(n) * filt))
    return (r - r.min()) / (r.max() - r.min())

def normal_map(height, strength):
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))

def colorize(t, stops):
    """t in 0..1 -> Farbe über Farbverlauf [(pos, (r,g,b)), ...]"""
    out = np.zeros(t.shape + (3,))
    pos = [p for p, _ in stops]; cols = np.array([c for _, c in stops], float)
    for ch in range(3): out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out

def rinde_fichte(out, size=512):
    # Fichtenrinde: grau-braune, schuppige Platten, leicht vertikal gestreckt
    platten = fft_noise(size, size, 4, 12, 1)
    schuppen = fft_noise(size, size, 16, 40, 2)
    fein = fft_noise(size, size, 120, 120, 3)
    risse = 1 - np.clip(np.abs(fft_noise(size, size, 5, 20, 4) - 0.5) * 9, 0, 1)   # schmale dunkle Risse
    h = platten * 0.45 + schuppen * 0.35 + fein * 0.2 - risse * 0.5
    h = (h - h.min()) / (h.max() - h.min())
    col = colorize(h, [(0.0, (28, 22, 18)), (0.35, (70, 56, 46)), (0.7, (104, 90, 78)), (1.0, (128, 116, 104))])
    col *= (0.85 + 0.3 * fft_noise(size, size, 4, 4, 5))[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, "fichte_rinde.png"))
    normal_map(h, 6.0).save(os.path.join(out, "fichte_rinde_normal.png"))

def nadelzweig(out, name, farbe_dunkel, farbe_hell, seed, W=2048, H=1024):
    """Zweig-Karte: Ansatz links (u=0), Spitze rechts. Alpha = Zweig. Doppelt groß gezeichnet, dann verkleinert."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2
    def farbe(hell=0.0):
        t = min(1, max(0, rnd.uniform(0, 0.7) + hell))
        return tuple(int(farbe_dunkel[i] + (farbe_hell[i] - farbe_dunkel[i]) * t) for i in range(3)) + (255,)
    def nadeln(x0, y0, x1, y1, laenge, dichte, hell):
        n = int(math.hypot(x1 - x0, y1 - y0) / dichte)
        ang = math.atan2(y1 - y0, x1 - x0)
        for k in range(n):
            t = k / max(1, n - 1); px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for seite in (-1, 1):
                a = ang + seite * rnd.uniform(0.6, 1.2)
                l = laenge * rnd.uniform(0.7, 1.1) * (1 - 0.4 * t)
                d.line([(px, py), (px + math.cos(a) * l, py + math.sin(a) * l)], fill=farbe(hell * t), width=5)
    # Hauptast
    spitze = W - 40
    d.line([(0, cy), (spitze, cy)], fill=(60, 45, 30, 255), width=14)
    # Seitenzweige: Dreiecksumriss (breit am Ansatz, spitz am Ende)
    x = 60
    while x < spitze - 80:
        t = x / spitze
        laenge = (H * 0.46) * (1 - t) ** 0.7 + 30
        for seite in (-1, 1):
            a = seite * rnd.uniform(0.75, 1.0)      # ~50° nach vorne
            ex, ey = x + math.cos(a) * laenge, cy + math.sin(a) * laenge
            d.line([(x, cy), (ex, ey)], fill=(55, 42, 28, 255), width=6)
            nadeln(x, cy, ex, ey, 34, 7, 0.5)
        x += rnd.uniform(55, 80)
    nadeln(0, cy, spitze, cy, 40, 6, 0.6)
    img = img.resize((W // 2, H // 2), Image.LANCZOS)
    # Alpha-Ränder für Alpha-Scissor glätten; Farbe in transparente Bereiche ausbluten (verhindert helle Ränder in Mipmaps)
    a = np.array(img)[..., 3]
    rgb = np.array(img.convert("RGB").filter(ImageFilter.MaxFilter(5)))
    base = np.array(img)[..., :3]
    rgb = np.where(a[..., None] > 0, base, rgb)
    Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").save(os.path.join(out, name))

def schnittflaeche(out, name, size=512):
    """Jahresringe für den Baumstumpf (planar, Mitte = Kern)."""
    y, x = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.sqrt(x ** 2 + y ** 2) * 2
    verz = fft_noise(size, size, 6, 6, 7) * 0.08
    ringe = (np.sin((r + verz) * 2 * math.pi * 18) * 0.5 + 0.5) ** 3
    col = colorize(ringe * 0.6 + fft_noise(size, size, 60, 60, 8) * 0.4,
                   [(0.0, (196, 160, 112)), (0.6, (170, 128, 82)), (1.0, (120, 82, 48))])
    rand = np.clip((r - 0.9) * 12, 0, 1)[..., None]          # Rinde am Rand
    col = col * (1 - rand) + np.array([60, 48, 38]) * rand
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, name))

def rinde_kiefer_unten(out, size=512):
    # grobe, tief gefurchte Borke: große Platten, graubraun mit rötlichem Stich
    platten = fft_noise(size, size, 3, 9, 21)
    furchen = 1 - np.clip(np.abs(fft_noise(size, size, 4, 14, 22) - 0.5) * 6, 0, 1)
    fein = fft_noise(size, size, 60, 90, 23)
    h = platten * 0.6 + fein * 0.25 - furchen * 0.7
    h = (h - h.min()) / (h.max() - h.min())
    col = colorize(h, [(0.0, (22, 16, 13)), (0.35, (66, 48, 38)), (0.7, (112, 84, 66)), (1.0, (140, 112, 92))])
    col *= (0.85 + 0.3 * fft_noise(size, size, 4, 4, 24))[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, "kiefer_rinde.png"))
    normal_map(h, 8.0).save(os.path.join(out, "kiefer_rinde_normal.png"))

def rinde_kiefer_oben(out, size=512):
    # "Spiegelrinde": orange-rötlich, dünne, quer abblätternde Schuppen
    schuppen = fft_noise(size, size, 30, 6, 31)
    kanten = 1 - np.clip(np.abs(fft_noise(size, size, 22, 4, 32) - 0.5) * 10, 0, 1)
    fein = fft_noise(size, size, 120, 60, 33)
    h = schuppen * 0.6 + fein * 0.3 - kanten * 0.35
    h = (h - h.min()) / (h.max() - h.min())
    col = colorize(h, [(0.0, (96, 48, 28)), (0.4, (158, 84, 48)), (0.75, (196, 118, 70)), (1.0, (214, 150, 104))])
    col *= (0.88 + 0.24 * fft_noise(size, size, 4, 4, 34))[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, "kiefer_rinde_oben.png"))
    normal_map(h, 4.0).save(os.path.join(out, "kiefer_rinde_oben_normal.png"))

def kiefer_buschel(out, name, farbe_dunkel, farbe_hell, seed, W=2048, H=1024):
    """Kiefern-Nadelbüschel: Zweig von links (u=0) nach rechts, lange Nadeln in Paaren nach vorne,
    am Ende ein dichter Pinsel. Alpha = Nadeln."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2; ende = W * 0.78
    def farbe(t):
        t = min(1, max(0, t + rnd.uniform(-0.25, 0.25)))
        return tuple(int(farbe_dunkel[i] + (farbe_hell[i] - farbe_dunkel[i]) * t) for i in range(3)) + (255,)
    d.line([(0, cy), (ende, cy)], fill=(92, 58, 36, 255), width=16)
    x = 120
    while x < ende:
        t = x / ende
        for _ in range(4):                                  # Nadelpaare rund um den Zweig
            a = rnd.choice((-1, 1)) * rnd.uniform(0.25, 1.05)
            l = rnd.uniform(0.32, 0.46) * H * (0.6 + 0.4 * t)
            x0 = x + rnd.uniform(-6, 6)
            d.line([(x0, cy), (x0 + math.cos(a) * l, cy + math.sin(a) * l)], fill=farbe(0.3 + 0.5 * t), width=5)
        x += rnd.uniform(9, 15)
    for _ in range(70):                                     # Pinsel an der Spitze
        a = rnd.uniform(-0.9, 0.9)
        l = rnd.uniform(0.25, 0.42) * H
        d.line([(ende, cy), (ende + math.cos(a) * l, cy + math.sin(a) * l)], fill=farbe(0.8), width=5)
    img = img.resize((W // 2, H // 2), Image.LANCZOS)
    a = np.array(img)[..., 3]
    rgb = np.array(img.convert("RGB").filter(ImageFilter.MaxFilter(5)))
    rgb = np.where(a[..., None] > 0, np.array(img)[..., :3], rgb)
    Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").save(os.path.join(out, name))

def rinde_eiche(out, size=512):
    # Eichenborke: lange, senkrechte Rippen mit tiefen Furchen, dazu Querrisse
    rippen = fft_noise(size, size, 2, 16, 51)
    furchen = 1 - np.clip(np.abs(fft_noise(size, size, 2, 12, 52) - 0.5) * 5, 0, 1)
    quer = 1 - np.clip(np.abs(fft_noise(size, size, 18, 4, 53) - 0.5) * 12, 0, 1)
    fein = fft_noise(size, size, 80, 80, 54)
    h = rippen * 0.5 + fein * 0.2 - furchen * 0.8 - quer * 0.25
    h = (h - h.min()) / (h.max() - h.min())
    col = colorize(h, [(0.0, (20, 18, 16)), (0.35, (54, 48, 42)), (0.7, (92, 84, 74)), (1.0, (124, 116, 104))])
    col *= (0.85 + 0.3 * fft_noise(size, size, 4, 4, 55))[..., None]
    moos = np.clip((fft_noise(size, size, 5, 5, 56) - 0.62) * 4, 0, 1)[..., None] * 0.5   # etwas Moos
    col = col * (1 - moos) + np.array([62, 80, 34]) * moos
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, "eiche_rinde.png"))
    normal_map(h, 9.0).save(os.path.join(out, "eiche_rinde_normal.png"))

def eichenblatt(laenge, breite, lappen):
    """Umriss eines gelappten Eichenblatts entlang der x-Achse (Stiel bei x=0)."""
    pts_o, pts_u = [], []
    n = 60
    for k in range(n + 1):
        t = k / n
        w = math.sin(math.pi * min(1, t * 1.08)) ** 0.7 * (0.55 + 0.45 * abs(math.sin(lappen * math.pi * t)))
        w *= breite / 2 * (0.6 + 0.4 * t)                 # vorne breiter
        pts_o.append((t * laenge, -w)); pts_u.append((t * laenge, w))
    return pts_o + pts_u[::-1]

def rundblatt(laenge, breite, _lappen=None):
    """eiförmiges Blatt mit Spitze und gesägtem Rand (Hasel-artig)"""
    pts_o, pts_u = [], []
    n = 80
    for k in range(n + 1):
        t = k / n
        w = math.sin(math.pi * t) ** 0.9 * (1 - 0.35 * t) * breite / 2
        w *= 1 + 0.06 * (1 if k % 4 < 2 else -1)        # Sägezähne
        pts_o.append((t * laenge, -w)); pts_u.append((t * laenge, w))
    return pts_o + pts_u[::-1]

def eichen_laub(out, name, farbe_dunkel, farbe_hell, seed, W=2048, H=1024, blattform=None, groesse=1.0):
    """Laubbüschel: Zweig von links nach rechts, gelappte Blätter wechselständig + Endbüschel."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2; ende = W * 0.72
    def farbe(hell):
        t = min(1, max(0, hell + rnd.uniform(-0.25, 0.25)))
        return tuple(int(farbe_dunkel[i] + (farbe_hell[i] - farbe_dunkel[i]) * t) for i in range(3)) + (255,)
    def blatt(x, y, winkel, groesse, hell):
        L = groesse
        form = (blattform or eichenblatt)(L, L * (0.8 if blattform else 0.55), rnd.choice((3.5, 4.5, 5.5)))
        c, s_ = math.cos(winkel), math.sin(winkel)
        poly = [(x + px * c - py * s_, y + px * s_ + py * c) for px, py in form]
        d.polygon(poly, fill=farbe(hell))
        d.line([(x, y), (x + L * 0.95 * c, y + L * 0.95 * s_)], fill=farbe(hell - 0.35)[:3] + (255,), width=4)   # Mittelrippe
    d.line([(0, cy), (ende, cy)], fill=(80, 62, 44, 255), width=14)
    x = 160; seite = 1
    while x < ende:
        t = x / ende
        w = seite * rnd.uniform(0.5, 1.1)
        blatt(x, cy, w, rnd.uniform(260, 340) * (0.75 + 0.35 * t) * groesse, 0.2 + 0.5 * t)
        x += rnd.uniform(70, 110); seite = -seite
    for k in range(7):                                    # Büschel am Ende
        blatt(ende, cy, rnd.uniform(-1.2, 1.2), rnd.uniform(280, 360) * groesse, 0.6)
    img = img.resize((W // 2, H // 2), Image.LANCZOS)
    a = np.array(img)[..., 3]
    rgb = np.array(img.convert("RGB").filter(ImageFilter.MaxFilter(5)))
    rgb = np.where(a[..., None] > 0, np.array(img)[..., :3], rgb)
    Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").save(os.path.join(out, name))

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    rinde_fichte(out)
    nadelzweig(out, "fichte_nadeln.png", (14, 38, 26), (52, 92, 52), 11)
    schnittflaeche(out, "schnitt.png")
    rinde_kiefer_unten(out)
    rinde_kiefer_oben(out)
    kiefer_buschel(out, "kiefer_nadeln.png", (28, 52, 30), (96, 128, 64), 41)
    rinde_eiche(out)
    eichen_laub(out, "eiche_laub.png", (30, 58, 20), (110, 140, 50), 61)
    eichen_laub(out, "busch_laub.png", (40, 72, 22), (128, 160, 58), 71, blattform=rundblatt, groesse=0.85)
    print(sorted(os.listdir(out)))
