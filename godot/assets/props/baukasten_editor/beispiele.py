"""Baut Beispielhäuser für den Gebäude-Baukasten als data/gebaeude/*.json (Format rpg_gebaeude v1).
Aufruf: python3 beispiele.py   (überschreibt die hier erzeugten Dateien, eigene Gebäude bleiben unberührt)

Rechteckhaus: Breite W entlang x (Vielfaches von 2), Tiefe 4 m nach -z, Stockwerke je 2 m, Satteldach oder Walmdach.
Wandreihen je Stockwerk als Buchstaben, eine je 2-m-Feld, im Uhrzeigersinn: vorne (z 0, nach +x), rechts (x W, nach -z),
hinten (z -4, nach -x), links (x 0, nach +z). T = Tür, F = Fenster, W = Wand, S = Wand mit Strebe."""
import json, math, os, random

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

    def abhaengige_entfernen(self):
        """Teile, die an einem anderen hängen, fliegen raus, wenn ihr Träger fehlt (z. B. in Ruinen):
        Traufe und Ortgang brauchen die Dachfläche, die Ortgang-Ecke braucht den Ortgang, alle an gleicher Stelle."""
        da = {(t["modell"], tuple(t["pos"]), tuple(t["dreh"])) for t in self.teile}
        def hat(modelle, t, zurueck=0):
            # zurueck: Träger beginnt so viele Meter vor dem Teil (rechte Ortgänge sitzen am Ende der Dachfläche)
            r = math.radians(t["dreh"][1]); x, y, z = t["pos"]
            pos = (round(x - zurueck * math.cos(r), 3), y, round(z + zurueck * math.sin(r), 3))
            pos = tuple(int(v) if float(v).is_integer() else v for v in pos)
            return any((mo, pos, tuple(t["dreh"])) in da for mo in modelle)
        flaechen = ("dach_2x2", "dach_grat_2x2")
        def ende(t):
            r = math.radians(t["dreh"][1])
            return (t["pos"][0] + 2 * math.cos(r), t["pos"][1], t["pos"][2] - 2 * math.sin(r))
        behalten = []
        for t in self.teile:
            mo = t["modell"]
            rechts = 2 if mo.startswith(("dach_ortgang_r", "dach_ecke_r")) else 0
            if mo in ("dach_traufe", "dach_grat_traufe") or mo.startswith("dach_ortgang"):
                # an einer Walmseite trägt der Grat der nächsten Ecke (andere Drehung) die Traufe
                grat_da = any(g["modell"] == "dach_grat_2x2" and g["pos"][1] == t["pos"][1] and
                              any(abs(g["pos"][0] - p[0]) < 1e-6 and abs(g["pos"][2] - p[2]) < 1e-6
                                  for p in (t["pos"], ende(t))) for g in self.teile)
                if not hat(flaechen, t, rechts) and not (mo == "dach_traufe" and grat_da):
                    continue
            if mo.startswith("dach_ecke"):
                seite = mo[-1]
                if not hat(("dach_ortgang_" + seite,), t) or not hat(flaechen, t, rechts):
                    continue
            behalten.append(t)
        self.teile = behalten

    def speichern(self, datei):
        self.abhaengige_entfernen()
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


def wand_feld(h, art, x, y, z, r, stil="putz"):
    if stil == "bretter":
        modell = {"T": "bretter_tuer", "F": "bretter_fenster"}.get(art, "bretter_2x2")
        h.t(modell, (x, y, z), (0, r, 0))
        if art == "T":
            h.t("tuer_alt", (x, y, z), (0, r, 0))
        return
    if art == "T":
        h.t("wand_tuer", (x, y, z), (0, r, 0)); h.t("tuer", (x, y, z), (0, r, 0))
    elif art == "F":
        h.t("wand_fenster", (x, y, z), (0, r, 0))
    else:
        h.t("wand", (x, y, z), (0, r, 0))
        if art == "S":
            h.t("strebe_2m", (x, y, z), (0, r, 0))


def rechteckhaus(h, W, stockwerke, dach="sattel", treppe=True, ox=0, oz=0, ohne_dach=(), oy=0, stil="putz",
                 loecher=()):
    """stockwerke: Liste je Stockwerk mit dict seite -> Buchstaben. ohne_dach: Dachteile, die fehlen (Ruine).
    oy: Höhe des Erdgeschossbodens (z. B. 1 auf einem Steinsockel). stil "bretter": Bretterwände und Bretterdach.
    loecher: Bodenfelder (x, y, z), die frei bleiben (z. B. für eine Kellertreppe)."""
    n = len(stockwerke); H = 2 * n
    F = felder(W)
    ecken = [(x, 0) for x in range(0, W + 1, 2)] + [(x, -D) for x in range(0, W + 1, 2)] + [(0, -2), (W, -2)]
    def P(x, y, z):
        return (x + ox, y + oy, z + oz)
    for s, reihen in enumerate(stockwerke):
        y = 2 * s
        for seite, liste in F.items():
            for (x, z, r), art in zip(liste, reihen[seite]):
                wand_feld(h, art, *P(x, y, z), r, stil)
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
                if treppe and 0 < y < H and x == W - 2 and z == -2 or (x, y, z) in loecher:
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
    if stil == "bretter":     # Bretterdach ohne Überstände, Giebel aus Brettern
        for x in range(0, W, 2):
            d("dach_bretter_2x2", (x, H, 0), 0); d("dach_bretter_2x2", (x + 2, H, -D), 180)
            h.t("balken_2m", P(x, H + 2, -2)); d("dach_first", (x, H + 2, -2), 0)
        for gx in (0, W):
            h.t("bretter_dreieck", P(gx, H, 0), (0, 90, 0)); h.t("bretter_dreieck", P(gx, H, -D), (0, 270, 0))
            h.t("balken_2m", P(gx, H, -2), (0, 0, 90))
    elif dach == "sattel":
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


def steinring(h, W, y, hoehe, fenster=(), ox=0, oz=0):
    """Steinmauern rundum (Keller oder Sockel) mit Pfeilern an jedem Rasterpunkt. fenster: Indizes der Felder
    (im Uhrzeigersinn ab vorne links) mit Kellerfenster (nur bei hoehe 1)."""
    i = 0
    for liste in felder(W).values():
        for x, z, r in liste:
            if hoehe == 1:
                modell = "steinwand_fenster" if i in fenster else "steinwand_2x1"
            else:
                modell = "steinwand_2x2"
            h.t(modell, (x + ox, y, z + oz), (0, r, 0))
            i += 1
    for x in range(0, W + 1, 2):
        for z in (0, -D, -2) if x in (0, W) else (0, -D):
            h.t("steinpfeiler_%dm" % hoehe, (x + ox, y, z + oz))


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

    h = Haus("Verlassene Hütte", saat=11, kaputt=0.35)
    rechteckhaus(h, 4, [{"vorne": "TW", "rechts": "WF", "hinten": "WW", "links": "FW"}], stil="bretter")
    h.t("fass", (4.5, 0, 0.5), kaputt=True); h.t("kiste", (-0.6, 0, -1.0), (0, 30, 0), kaputt=True)
    h.t("karren", (6.0, 0, -2.5), (0, 120, 0), kaputt=True)
    h.speichern("verlassene_huette.json")

    h = Haus("Haus am Fluss")
    steinring(h, 6, 0, 1, fenster=(1, 4, 8))
    rechteckhaus(h, 6, [{"vorne": "FTF", "rechts": "FS", "hinten": "SFS", "links": "FS"}], oy=1)
    h.t("podest_stein", (2.5, 0, 1.15))                          # Podest vor der Tür (Sockel-Außenkante z 0,15)
    h.t("treppe_stein", (5.5, 0, 1.15), (0, 90, 0))              # Treppe seitlich, steigt nach -x zum Podest
    h.t("fass", (0.6, 0, 0.6)); h.t("kiste", (6.6, 0, -0.8), (0, 15, 0))
    h.speichern("haus_am_fluss.json")

    h = Haus("Haus mit Keller")
    steinring(h, 6, -2, 2)
    for x in range(0, 6, 2):
        for z in (0, -2):
            h.t("steinboden_2x2", (x, -2, z))
    h.t("treppe_holz", (4, -2, 0)); h.t("treppe_holz", (4, -1, -2))   # Kellertreppe, darüber Loch im Boden
    rechteckhaus(h, 6, [{"vorne": "FTF", "rechts": "SF", "hinten": "FSF", "links": "FS"}],
                 loecher={(4, 0, 0), (4, 0, -2)})
    h.t("fass", (0.6, -2, -0.6)); h.t("fass", (0.6, -2, -1.4)); h.t("kiste", (2.4, -2, -3.4), (0, 10, 0))
    h.speichern("haus_mit_keller.json")

    h = Haus("Befestigung")
    # Hof 8 x 8 m: Mauern als 1 m breiter Ring, vorne/links Stein mit Zinnen, hinten/rechts Holz mit Palisade
    seiten = [("stein", [(x, 0, 0) for x in (0, 2, 4, 6)], 0),
              ("holz", [(8, 0, z) for z in (-1, -3, -5)], 90),
              ("holz", [(x, 0, -8) for x in (8, 6, 4, 2)], 180),
              ("stein", [(0, 0, z) for z in (-7, -5, -3)], 270)]
    for art, stuecke, r in seiten:
        for x, y, z in stuecke:
            h.t("festung_%s_2m" % art, (x, y, z), (0, r, 0))
            h.t("bruestung_%s_15_2m" % art, (x, 3, z), (0, r, 0))
    for x in (3, 5, 7):                                         # Absturzsicherung innen am vorderen Wehrgang
        h.t("bruestung_holz_10_2m", (x, 3, -1), (0, 180, 0))
    for k in range(3):                                          # Treppe im Hof hinauf zum linken Wehrgang
        h.t("treppe_holz", (7 - 2 * k, k, -5), (0, 90, 0))
    h.t("fass", (6.4, 0, -6.4)); h.t("kiste", (5.6, 0, -6.5), (0, 15, 0)); h.t("lagerfeuer", (4.0, 0, -3.2))
    h.speichern("befestigung.json")

    h = Haus("Ruine", saat=7, kaputt=0.55)
    bauernhaus(h, ohne_dach={("dach_2x2", (2, 2, 0)), ("dach_traufe", (2, 2, 0)), ("dach_first", (2, 4, -2)),
                             ("dach_2x2", (6, 2, -4)), ("dach_first", (4, 4, -2))})
    h.speichern("ruine.json")


if __name__ == "__main__":
    main()
