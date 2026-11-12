"""Baut Beispielhäuser für den Gebäude-Baukasten als data/gebaeude/*.json (Format rpg_gebaeude v1).
Aufruf: python3 beispiele.py   (überschreibt die hier erzeugten Dateien, eigene Gebäude bleiben unberührt)

Rechteckhaus: Breite W entlang x (Vielfaches von 2), Tiefe 4 m nach -z, Stockwerke je 2 m, Satteldach oder Walmdach.
Wandreihen je Stockwerk als Buchstaben, eine je 2-m-Feld, im Uhrzeigersinn: vorne (z 0, nach +x), rechts (x W, nach -z),
hinten (z -4, nach -x), links (x 0, nach +z). T = Tür, F = Fenster, W = Wand, S = Wand mit Strebe."""
import json, os, random

ZIEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "gebaeude")
D = 4


class Haus:
    def __init__(self, name, saat=1, kaputt=0.0):
        self.name = name; self.teile = []; self.rnd = random.Random(saat); self.kaputt = kaputt

    def t(self, modell, pos, dreh=(0, 0, 0), kaputt=None):
        if kaputt is None:
            kaputt = self.kaputt > 0 and self.rnd.random() < self.kaputt
        self.teile.append({"modell": modell, "kaputt": bool(kaputt), "pos": [round(v, 3) for v in pos],
                           "dreh": list(dreh)})

    def speichern(self, datei):
        with open(os.path.join(ZIEL, datei), "w", encoding="utf-8") as f:
            json.dump({"format": "rpg_gebaeude", "version": 1, "name": self.name, "raster": 1.0, "teile": self.teile},
                      f, ensure_ascii=False, indent=1)
        print(datei, len(self.teile), "Teile")


def felder(W):
    """(Ursprung x, z, Drehung) aller 2-m-Wandfelder im Uhrzeigersinn, getrennt nach Seite."""
    return {"vorne": [(x, 0, 0) for x in range(0, W, 2)],
            "rechts": [(W, -z, 90) for z in range(0, D, 2)],
            "hinten": [(x, -D, 180) for x in range(W, 0, -2)],
            "links": [(0, -z, 270) for z in range(D, 0, -2)]}


def wand_feld(h, art, x, y, z, r):
    if art == "T":
        h.t("wand_tuer", (x, y, z), (0, r, 0)); h.t("tuer", (x, y, z), (0, r, 0))
    elif art == "F":
        h.t("wand_fenster", (x, y, z), (0, r, 0))
    else:
        h.t("wand", (x, y, z), (0, r, 0))
        if art == "S":
            h.t("strebe_2m", (x, y, z), (0, r, 0))


def rechteckhaus(h, W, stockwerke, dach="sattel", treppe=True, ox=0, oz=0, ohne_dach=()):
    """stockwerke: Liste je Stockwerk mit dict seite -> Buchstaben. ohne_dach: Dachteile, die fehlen (Ruine)."""
    n = len(stockwerke); H = 2 * n
    F = felder(W)
    ecken = [(x, 0) for x in range(0, W + 1, 2)] + [(x, -D) for x in range(0, W + 1, 2)] + [(0, -2), (W, -2)]
    def P(x, y, z):
        return (x + ox, y, z + oz)
    for s, reihen in enumerate(stockwerke):
        y = 2 * s
        for seite, liste in F.items():
            for (x, z, r), art in zip(liste, reihen[seite]):
                wand_feld(h, art, *P(x, y, z), r)
        for x, z in ecken:
            h.t("balken_2m", P(x, y, z), (0, 0, 90))
    for y in range(0, H + 1, 2):
        for liste in F.values():
            for x, z, r in liste:
                h.t("balken_2m", P(x, y, z), (0, r, 0))
    # Böden und Decken, Treppe an der rechten Seite (x W-2..W-1), Loch in der Decke darüber
    for y in range(0, H + 1, 2):
        for x in range(0, W, 2):
            for z in (0, -2):
                if treppe and 0 < y < H and x == W - 2 and z == -2:
                    continue
                h.t("boden_2x2", P(x, y, z))
    if treppe:
        for s in range(n - 1):
            h.t("treppe_holz", P(W - 2, 2 * s, 0)); h.t("treppe_holz", P(W - 2, 2 * s + 1, -2))
    # Dach
    def d(modell, pos, r):
        if (modell, pos) in ohne_dach:
            return
        h.t(modell, P(*pos), (0, r, 0))
    if dach == "sattel":
        for x in range(0, W, 2):
            d("dach_2x2", (x, H, 0), 0); d("dach_traufe", (x, H, 0), 0)
            d("dach_2x2", (x + 2, H, -D), 180); d("dach_traufe", (x + 2, H, -D), 180)
            h.t("balken_2m", P(x, H + 2, -2)); d("dach_first", (x, H + 2, -2), 0)
        for gx, l_r in ((0, ("l", "r")), (W, ("r", "l"))):
            h.t("wand_dreieck", P(gx, H, 0), (0, 90, 0)); h.t("wand_dreieck", P(gx, H, -D), (0, 270, 0))
            h.t("strebe_2m", P(gx, H, 0), (0, 90, 0)); h.t("strebe_2m", P(gx, H, -D), (0, 270, 0))
            h.t("balken_2m", P(gx, H, -2), (0, 0, 90))
            h.t("dach_ortgang_" + l_r[0], P(gx, H, 0)); h.t("dach_ecke_" + l_r[0], P(gx, H, 0))
            h.t("dach_ortgang_" + l_r[1], P(gx, H, -D), (0, 180, 0)); h.t("dach_ecke_" + l_r[1], P(gx, H, -D), (0, 180, 0))
            h.t("dach_zier_" + l_r[0], P(gx, H + 2, -2))
    else:   # Walmdach: Grate an den vier Ecken, dazwischen normale Flächen
        for x in range(2, W - 2, 2):
            d("dach_2x2", (x, H, 0), 0); d("dach_2x2", (x + 2, H, -D), 180)
            h.t("balken_2m", P(x, H + 2, -2)); d("dach_first", (x, H + 2, -2), 0)
        for pos, r in (((0, H, 0), 0), ((0, H, -D), 270), ((W, H, 0), 90), ((W, H, -D), 180)):
            d("dach_grat_2x2", pos, r); d("dach_grat_traufe", pos, r)
        for liste in F.values():
            for x, z, r in liste:
                d("dach_traufe", (x, H, z), r)


def bauernhaus(h, **kw):
    rechteckhaus(h, 6, [{"vorne": "FTF", "rechts": "SF", "hinten": "SFS", "links": "FS"}], **kw)
    h.t("bank", (1.0, 0, 0.7), (0, 0, 0)); h.t("fass", (5.3, 0, 0.6)); h.t("fass", (5.9, 0, 0.9))
    h.t("karren", (8.0, 0, -1.5), (0, 75, 0)); h.t("kiste", (6.7, 0, -3.3), (0, 20, 0))


def main():
    os.makedirs(ZIEL, exist_ok=True)
    h = Haus("Bauernhaus"); bauernhaus(h); h.speichern("bauernhaus.json")

    h = Haus("Stadthaus")
    rechteckhaus(h, 4, [{"vorne": "TF", "rechts": "FS", "hinten": "SF", "links": "SF"},
                        {"vorne": "FF", "rechts": "FS", "hinten": "FF", "links": "SF"}])
    h.t("laterne", (-0.3, 0, 0.5)); h.t("kiste", (4.6, 0, 0.6), (0, 15, 0))
    h.speichern("stadthaus.json")

    h = Haus("Walmdachhaus")
    rechteckhaus(h, 8, [{"vorne": "SFTF", "rechts": "FS", "hinten": "FSFS", "links": "SF"}], dach="walm")
    h.t("bank", (1.0, 0, 0.7)); h.t("tisch", (2.6, 0, 1.6)); h.t("hocker", (3.4, 0, 1.4))
    h.speichern("walmdachhaus.json")

    h = Haus("Gasthaus")
    rechteckhaus(h, 10, [{"vorne": "FFTFF", "rechts": "FS", "hinten": "SFSFS", "links": "SF"},
                         {"vorne": "FSFSF", "rechts": "FF", "hinten": "FFSFF", "links": "FF"}])
    for x in (4.0, 6.0):
        h.t("laternenpfahl", (x - 0.4 if x < 5 else x + 0.4, 0, 1.4))
    for x, z in ((1.2, 2.2), (8.6, 2.2)):
        h.t("tisch", (x, 0, z)); h.t("bank", (x, 0, z - 0.75)); h.t("bank", (x, 0, z + 0.75), (0, 180, 0))
    h.t("fass", (10.6, 0, -0.6)); h.t("fass", (10.7, 0, -1.4)); h.t("kiste", (10.6, 0, -2.4), (0, 10, 0))
    h.speichern("gasthaus.json")

    h = Haus("Ruine", saat=7, kaputt=0.55)
    bauernhaus(h, ohne_dach={("dach_2x2", (2, 2, 0)), ("dach_traufe", (2, 2, 0)), ("dach_first", (2, 4, -2)),
                             ("dach_2x2", (6, 2, -4)), ("dach_first", (4, 4, -2))})
    h.speichern("ruine.json")


if __name__ == "__main__":
    main()
