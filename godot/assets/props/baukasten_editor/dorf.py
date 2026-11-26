"""Baut viele zufällige Dorfhäuser für das World Building als data/gebaeude/dorf_<zustand>_NN.json.
Aufruf: python3 dorf.py [anzahl_heil anzahl_alt anzahl_ruine]   (Standard 14 10 10, feste Saat: gleiche Häuser bei jedem Lauf)

Drei Zustände (Feld "gruppe" in der Datei, der Baukasten sortiert die Vorlagen danach):
  heil  – Fachwerk, 1–3 Stockwerke, Sattel- oder Walmdach, teils Steinsockel mit Podest und Seitentreppe, Keller,
          Holzterrasse mit Geländer, Einrichtung vor dem Haus
  alt   – verlassen: Bretterwände und Bretterdach, ein Teil der Module kaputt, umgefallene Kisten und Fässer
  ruine – Fachwerk, viele Module kaputt, Dachflächen und Teile der Obergeschosse fehlen
Bausteine (Rechteckhaus, Steinring, Haus) kommen aus beispiele.py."""
import random, sys
from beispiele import Haus, rechteckhaus, steinring, felder

ARTEN = "FFFSSW"


def wandreihen(rnd, W, stockwerk, stil, tuer_feld):
    """Buchstaben je Seite für ein Stockwerk. Erdgeschoss: Tür vorne im Feld tuer_feld."""
    n = W // 2
    def reihe(k, ohne_tuer=True):
        return "".join(rnd.choice(ARTEN if stil == "putz" else "FWWW") for _ in range(k))
    vorne = list(reihe(n))
    if stockwerk == 0:
        vorne[tuer_feld] = "T"
    elif stil == "putz":
        vorne = [rnd.choice("FFS") for _ in range(n)]
    return {"vorne": "".join(vorne), "rechts": reihe(2), "hinten": reihe(n), "links": reihe(2)}


def terrasse(h, W, ox, oz, tuer_feld):
    """Holzterrasse 2 m tief vor der Vorderseite mit Geländer rundum (innen eingerückt) und Öffnung vor der Tür."""
    for x in range(0, W, 2):
        h.t("boden_2x2", (x + ox, 0, 2 + oz))
    oeffnung = 2 * tuer_feld + 1                     # Feld direkt vor der Türmitte bleibt offen
    h.t("gelaender_pfosten", (ox, 0, 2 + oz))        # Innenecken
    h.t("gelaender_pfosten", (W + ox, 0, 2 + oz), (0, 90, 0))
    for x in range(W):
        if x in (oeffnung - 1, oeffnung):
            if x == oeffnung - 1:                    # Stück vor der Öffnung endet mit Pfosten
                h.t("gelaender_1m_pfosten" if x < W - 1 else "gelaender_1m", (x + ox, 0, 2 + oz))
            else:
                h.t("gelaender_pfosten_mitte", (x + 1 + ox, 0, 2 + oz))   # Pfosten nach der Öffnung
            continue
        h.t("gelaender_1m" if x == W - 1 else "gelaender_1m_pfosten", (x + ox, 0, 2 + oz))
    # Seiten: von der Hauswand (Endstück am Pfosten der Ecke) bzw. zur Hauswand (Endstück an der Wand)
    h.t("gelaender_1m_pfosten", (ox, 0, oz), (0, 270, 0)); h.t("gelaender_1m", (ox, 0, 1 + oz), (0, 270, 0))
    h.t("gelaender_1m_pfosten", (W + ox, 0, 2 + oz), (0, 90, 0)); h.t("gelaender_1m", (W + ox, 0, 1 + oz), (0, 90, 0))


def einrichtung(h, rnd, W, kaputt, vorne_frei=True):
    """Ein paar Dinge ums Haus (nicht vor der Tür)."""
    stellen = [(-0.7, -0.8), (-0.7, -3.0), (W + 0.7, -0.9), (W + 0.7, -3.1), (0.8, -4.8), (W - 0.8, -4.8)]
    rnd.shuffle(stellen)
    for (x, z) in stellen[:rnd.randint(2, 4)]:
        modell = rnd.choice(["fass", "fass", "kiste", "kiste", "bank", "karren", "laterne", "hocker"])
        if modell == "karren":
            x += 1.2 if x > W / 2 else -1.2
        h.t(modell, (round(x, 2), 0, round(z, 2)), (0, rnd.choice([0, 15, 30, 75, 90, 160, 200]), 0),
            kaputt=kaputt and rnd.random() < 0.6)


def heiles_haus(nr, rnd):
    W = rnd.choice([4, 6, 6, 8, 8, 10])
    stockwerke = rnd.choices([1, 2, 3], [5, 4, 1 if W <= 6 else 0])[0]
    dach = "walm" if rnd.random() < 0.3 else "sattel"
    tuer = rnd.randrange(W // 2)
    sockel = rnd.random() < 0.3
    keller = not sockel and rnd.random() < 0.25
    deck = not sockel and not keller and rnd.random() < 0.35
    name = ["Hütte", "Kate", "Wohnhaus", "Bauernhaus", "Langhaus"][min(4, W // 2 - 1 + (stockwerke > 1))]
    if stockwerke >= 2:
        name = "Stadthaus" if W <= 6 else "Gasthaus" if W == 10 else "Bürgerhaus"
    h = Haus("%s %d" % (name, nr), saat=rnd.random())
    reihen = [wandreihen(rnd, W, s, "putz", tuer) for s in range(stockwerke)]
    oy = 0; loecher = ()
    if sockel:
        felder_n = W + 4
        steinring(h, W, 0, 1, fenster=tuple(i for i in range(felder_n) if rnd.random() < 0.3 and i != tuer))
        oy = 1
    if keller:
        steinring(h, W, -2, 2)
        for x in range(0, W, 2):
            for z in (0, -2):
                h.t("steinboden_2x2", (x, -2, z))
        h.t("treppe_holz", (0, -2, 0)); h.t("treppe_holz", (0, -1, -2))
        loecher = {(0, 0, 0), (0, 0, -2)}
        h.t("fass", (W - 0.6, -2, -0.6)); h.t("kiste", (W - 1.4, -2, -3.4), (0, 10, 0))
    rechteckhaus(h, W, reihen, dach=dach, oy=oy, loecher=loecher)
    if sockel:   # Podest vor der Tür, Treppe seitlich (zur Seite mit mehr Platz)
        h.t("podest_stein", (2 * tuer + 0.5, 0, 1.15))
        if 2 * tuer + 3.5 <= W + 1.5:
            h.t("treppe_stein", (2 * tuer + 3.5, 0, 1.15), (0, 90, 0))
        else:
            h.t("treppe_stein", (2 * tuer - 1.5, 0, 0.15), (0, 270, 0))
    if deck:
        terrasse(h, W, 0, 0, tuer)
    einrichtung(h, rnd, W, False)
    h.gruppe = "Dorf: heil"
    return h


def altes_haus(nr, rnd):
    W = rnd.choice([4, 4, 6, 6, 8])
    stockwerke = 1 if rnd.random() < 0.8 else 2
    tuer = rnd.randrange(W // 2)
    h = Haus("Verlassenes Haus %d" % nr, saat=rnd.random(), kaputt=rnd.uniform(0.2, 0.4))
    reihen = [wandreihen(rnd, W, s, "bretter", tuer) for s in range(stockwerke)]
    sockel = rnd.random() < 0.25
    if sockel:
        steinring(h, W, 0, 1)
    fehlt = set()
    for x in range(0, W, 2):
        if rnd.random() < 0.3:
            fehlt.add(("dach_bretter_2x2", (x, 2 * stockwerke, 0)))
        if rnd.random() < 0.3:
            fehlt.add(("dach_bretter_2x2", (x + 2, 2 * stockwerke, -4)))
    rechteckhaus(h, W, reihen, stil="bretter", oy=1 if sockel else 0, ohne_dach=fehlt)
    if sockel:
        h.t("treppe_stein", (2 * tuer + 0.5, 0, 2.15), kaputt=True)
    ueber_kaputt_entfernen(h); schwebende_entfernen(h)
    einrichtung(h, rnd, W, True)
    h.gruppe = "Dorf: alt"
    return h


def ruine(nr, rnd):
    W = rnd.choice([4, 6, 6, 8, 8, 10])
    stockwerke = rnd.choice([1, 1, 2])
    tuer = rnd.randrange(W // 2)
    dach = "walm" if rnd.random() < 0.25 else "sattel"
    h = Haus("Ruine %d" % nr, saat=rnd.random(), kaputt=rnd.uniform(0.45, 0.7))
    reihen = [wandreihen(rnd, W, s, "putz", tuer) for s in range(stockwerke)]
    H = 2 * stockwerke
    ohne = set()
    dach_weg = 1.0 if stockwerke > 1 else rnd.uniform(0.3, 1.0)   # Anteil fehlender Dachteile (1,0 = eingestürzt)
    for x in range(0, W + 2, 2):
        for modell, pos in (("dach_2x2", (x, H, 0)), ("dach_traufe", (x, H, 0)), ("dach_2x2", (x, H, -4)),
                            ("dach_traufe", (x, H, -4)), ("dach_first", (x, H + 2, -2)),
                            ("dach_grat_2x2", (x, H, 0)), ("dach_grat_2x2", (x, H, -4))):
            if rnd.random() < dach_weg:
                ohne.add((modell, pos))
    rechteckhaus(h, W, reihen, dach=dach, ohne_dach=ohne)
    # Firstbalken nur, wo das Firstbrett noch liegt; Giebelzier ist abgefallen; Decke unter fehlendem Dach eingebrochen
    firste = {tuple(t["pos"]) for t in h.teile if t["modell"] == "dach_first"}
    h.teile = [t for t in h.teile if not t["modell"].startswith("dach_zier") and
               not (t["modell"] == "balken_2m" and t["pos"][1] == H + 2 and tuple(t["pos"]) not in firste) and
               not (t["modell"] == "boden_2x2" and t["pos"][1] == H and rnd.random() < 0.7 * dach_weg)]
    # Obergeschosse teilweise eingestürzt: Teile ab 2 m Höhe fallen weg (Böden, Wände, Balken, Giebel)
    if stockwerke > 1 or dach_weg > 0.8:
        weg = rnd.uniform(0.25, 0.5)
        h.teile = [t for t in h.teile if t["pos"][1] < 2 or rnd.random() > weg]
    if dach_weg > 0.8:   # Dach eingestürzt: auch Giebel, Firstbalken und Zier weg
        h.teile = [t for t in h.teile if not (t["pos"][1] >= H and (t["modell"].startswith(("wand_dreieck", "dach_", "strebe"))
                                                                   or t["pos"][1] > H))]
    ueber_kaputt_entfernen(h); schwebende_entfernen(h)
    einrichtung(h, rnd, W, True)
    h.gruppe = "Dorf: Ruine"
    return h


WANDE = ("wand", "bretter_", "steinwand")


def schwebende_entfernen(h):
    """Waagerechte Balken über Wandfeldern brauchen eine heile Wand darunter (sonst schweben sie in der Ruine);
    Firstbretter brauchen mindestens eine Dachfläche daneben."""
    heil = {(t["pos"][0], t["pos"][1], t["pos"][2], t["dreh"][1]) for t in h.teile
            if t["modell"].startswith(WANDE) and not t["kaputt"]}
    flaechen = {(t["pos"][0], t["pos"][1], t["pos"][2]) for t in h.teile if t["modell"].startswith(("dach_2x2", "dach_bretter_2x2"))}
    def bleibt(t):
        x, y, z = t["pos"]
        if t["modell"] == "balken_2m" and t["dreh"][2] == 0 and y > 0 and y % 2 == 0 and not (z == -2 and t["dreh"][1] == 0):
            return (x, y - 2, z, t["dreh"][1]) in heil
        if t["modell"] == "dach_first":
            return (x, y - 2, 0) in flaechen or (x + 2, y - 2, -4) in flaechen
        return True
    h.teile = [t for t in h.teile if bleibt(t)]
    firste = {tuple(t["pos"]) for t in h.teile if t["modell"] == "dach_first"}
    h.teile = [t for t in h.teile if not (t["modell"] == "balken_2m" and t["dreh"] == [0, 0, 0] and t["pos"][2] == -2
                                          and tuple(t["pos"]) not in firste)]


def ueber_kaputt_entfernen(h):
    """Über einer kaputten (niedrigeren) Wand kann keine Wand mehr stehen: solche Felder fallen weg."""
    kaputt = {}
    for t in h.teile:
        if t["kaputt"] and t["modell"].startswith(WANDE):
            k = (t["pos"][0], t["pos"][2], t["dreh"][1]); kaputt[k] = min(kaputt.get(k, 99), t["pos"][1])
    h.teile = [t for t in h.teile if not (t["modell"].startswith(WANDE) and
               t["pos"][1] > kaputt.get((t["pos"][0], t["pos"][2], t["dreh"][1]), 99))]


def main():
    n_heil, n_alt, n_ruine = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (14, 10, 10)
    rnd = random.Random(20261126)
    for art, n, bauer in (("heil", n_heil, heiles_haus), ("alt", n_alt, altes_haus), ("ruine", n_ruine, ruine)):
        for i in range(1, n + 1):
            h = bauer(i, rnd)
            h.speichern("dorf_%s_%02d.json" % (art, i))


if __name__ == "__main__":
    main()
