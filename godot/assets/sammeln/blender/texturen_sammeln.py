"""Texturen für Sammelpflanzen (Hanf). Nutzt die Helfer aus ../baeume/texturen.py.
Aufruf: python texturen_sammeln.py <zielordner>"""
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def ausbluten_und_speichern(img, pfad):
    """verkleinern, Farbe in transparente Bereiche ausbluten (keine hellen Ränder in Mipmaps)"""
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    a = np.array(img)[..., 3]
    rgb = np.array(img.convert("RGB").filter(ImageFilter.MaxFilter(5)))
    rgb = np.where(a[..., None] > 0, np.array(img)[..., :3], rgb)
    Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").save(pfad)

def hanf_blatt(out, seed=81, W=2048, H=2048):
    """gefingertes Hanfblatt: Stiel von links (u=0), 7 gesägte Fiederblättchen fächerförmig nach vorne"""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2; mitte = (W * 0.3, cy)
    d.line([(0, cy), mitte], fill=(96, 130, 52, 255), width=14)
    winkel = [-78, -52, -26, 0, 26, 52, 78]
    laengen = [0.32, 0.58, 0.85, 1.0, 0.85, 0.58, 0.32]
    for wg, lf in zip(winkel, laengen):
        L = W * 0.64 * lf; a = math.radians(wg + rnd.uniform(-4, 4))
        c, s = math.cos(a), math.sin(a)
        oben, unten = [], []
        n = 110
        for k in range(n + 1):
            t = k / n
            w = math.sin(math.pi * t) ** 0.8 * L * 0.075 * (1 - 0.2 * t)
            w *= 1 + 0.12 * (1 if k % 6 < 3 else -0.3)          # gesägter Rand
            oben.append((t * L, -w)); unten.append((t * L, w))
        poly = [(mitte[0] + px * c - py * s, mitte[1] + px * s + py * c) for px, py in oben + unten[::-1]]
        g = rnd.uniform(0, 0.25)
        d.polygon(poly, fill=(int(46 + 30 * g), int(92 + 30 * g), int(32 + 12 * g), 255))
        d.line([mitte, (mitte[0] + L * 0.95 * c, mitte[1] + L * 0.95 * s)], fill=(110, 150, 70, 255), width=5)
    ausbluten_und_speichern(img, os.path.join(out, "hanf_blatt.png"))

def hanf_bluete(out, seed=82, W=2048, H=512):
    """Blütenstand: Stiel von links, dichte, schmale Hochblätter und Knospen, lila mit hellen Härchen"""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2
    d.line([(0, cy), (W * 0.95, cy)], fill=(100, 128, 50, 255), width=12)
    for _ in range(420):
        x = rnd.uniform(W * 0.05, W * 0.95); t = x / W
        breite = H * 0.42 * math.sin(math.pi * min(1, t * 1.1)) ** 0.6
        a = rnd.choice((-1, 1)) * rnd.uniform(0.3, 1.1)
        l = rnd.uniform(0.3, 1.0) * breite
        g = rnd.uniform(0, 1)
        col = (int(118 + 55 * g), int(58 + 32 * g), int(150 + 55 * g), 255)   # lila
        x2, y2 = x + math.cos(a) * l * 0.6, cy + math.sin(a) * l
        d.polygon([(x - 8, cy), (x + 8, cy), (x2, y2)], fill=col)
        if rnd.random() < 0.25:
            d.ellipse([x2 - 4, y2 - 4, x2 + 4, y2 + 4], fill=(238, 215, 245, 255))
    ausbluten_und_speichern(img, os.path.join(out, "hanf_bluete.png"))

def kraut_blatt(out, seed=91, W=2048, H=512):
    """lanzettliches Blatt: Basis links (u=0), Spitze rechts, Mittelrippe"""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cy = H / 2; L = W * 0.96
    oben, unten = [], []
    for k in range(101):
        t = k / 100
        w = math.sin(math.pi * t ** 0.8) ** 0.9 * H * 0.42
        w *= 1 + 0.05 * (1 if k % 4 < 2 else -1)
        oben.append((t * L, cy - w)); unten.append((t * L, cy + w))
    d.polygon(oben + unten[::-1], fill=(58, 104, 40, 255))
    for k in range(12):  # Seitenadern, enden innerhalb des Blattrands
        t = 0.08 + 0.72 * k / 12; x = L * t
        w = math.sin(math.pi * (t + 0.04) ** 0.8) ** 0.9 * H * 0.42 * 0.75
        d.line([(x, cy), (x + w * 0.5, cy - w)], fill=(76, 124, 52, 255), width=4)
        d.line([(x, cy), (x + w * 0.5, cy + w)], fill=(76, 124, 52, 255), width=4)
    d.line([(0, cy), (L, cy)], fill=(110, 150, 75, 255), width=8)
    ausbluten_und_speichern(img, os.path.join(out, "kraut_blatt.png"))

def kraut_bluete(out, seed=92, W=1024, H=1024):
    """Blütendolde von oben: viele kleine 5-blättrige Blüten, fast weiß (wird im Material eingefärbt)"""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy = W / 2, H / 2
    for _ in range(34):
        r = abs(rnd.gauss(0, W * 0.2)); a = rnd.uniform(0, 2 * math.pi)
        if r > W * 0.4:
            continue
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        g = rnd.randint(205, 255); rb = rnd.uniform(48, 70); dreh = rnd.uniform(0, 1.3)
        for k in range(5):
            pa = dreh + k * 2 * math.pi / 5
            px, py = x + math.cos(pa) * rb * 0.75, y + math.sin(pa) * rb * 0.75
            d.ellipse([px - rb * 0.55, py - rb * 0.55, px + rb * 0.55, py + rb * 0.55], fill=(g, g, g, 255))
        d.ellipse([x - rb * 0.28, y - rb * 0.28, x + rb * 0.28, y + rb * 0.28], fill=(150, 140, 90, 255))
    ausbluten_und_speichern(img, os.path.join(out, "kraut_bluete.png"))

def beeren_blatt(out):
    from texturen import eichen_laub, rundblatt
    eichen_laub(out, "beeren_blatt.png", (24, 52, 22), (78, 112, 42), 101, blattform=rundblatt, groesse=0.6)

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    hanf_blatt(out); hanf_bluete(out)
    kraut_blatt(out); kraut_bluete(out); beeren_blatt(out)
    print(sorted(os.listdir(out)))
