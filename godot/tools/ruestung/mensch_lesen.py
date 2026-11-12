"""Liest die aufbereiteten MakeHuman-Daten (godot/assets/charakter/daten) in Python,
genau wie mensch_daten.gd/mensch.gd im Spiel: Grundnetz, Formen, Knochengewichte.

form_berechnen(aussehen) rechnet die Punkte für ein Aussehen (Meter, Y oben, Blick +Z,
Füße auf dem Boden) wie Mensch.form_berechnen().
"""
import json
import os
import struct

import numpy as np
import zstandard

ORDNER = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "charakter", "daten")

STANDARD = {"geschlecht": 1.0, "alter": 0.1, "groesse": 0.5, "muskeln": 0.5, "gewicht": 0.5,
            "brust": 0.5, "brust_fest": 0.5, "herkunft": [0.0, 0.0, 1.0], "regler": {}}


def _gcpf(pfad):
    with open(pfad, "rb") as f:
        roh = f.read()
    assert roh[:4] == b"GCPF"
    modus, block, gesamt = struct.unpack("<III", roh[4:16])
    anzahl = gesamt // block + 1
    groessen = struct.unpack("<%dI" % anzahl, roh[16:16 + 4 * anzahl])
    o = 16 + 4 * anzahl
    d = zstandard.ZstdDecompressor()
    out = bytearray()
    for g in groessen:
        if g:
            out += d.decompress(roh[o:o + g], max_output_size=block)
        o += g
    return bytes(out[:gesamt])


class Mensch:
    def __init__(self):
        with open(os.path.join(ORDNER, "mensch.json"), encoding="utf-8") as f:
            self.meta = json.load(f)
        self.puffer = _gcpf(os.path.join(ORDNER, "mensch.bin"))
        g = self.meta["grund"]
        self.grund = self.f32(g["positionen"]).reshape(-1, 3).astype(np.float64)
        self.k_idx = self.i32(g["knochen_index"]).reshape(-1, 4)
        self.k_gew = self.f32(g["knochen_gewicht"]).reshape(-1, 4)
        k = self.meta["teile"]["koerper"]
        self.koerper_mh = self.i32(k["mh_index"])
        dr = self.i32(k["dreiecke"]).reshape(-1, 3)
        self.koerper_dreiecke = self.koerper_mh[dr]          # Dreiecke in MakeHuman-Indizes
        self.knochen = [b["name"] for b in self.meta["knochen"]]

    def stueck(self, spec):
        return self.puffer[spec[0]:spec[0] + spec[1]]

    def f32(self, spec):
        return np.frombuffer(self.stueck(spec), dtype="<f4")

    def i32(self, spec):
        return np.frombuffer(self.stueck(spec), dtype="<i4")

    def form(self, name):
        spec = self.meta["formen"][name]
        n = spec[2]
        roh = self.stueck(spec)
        idx = np.frombuffer(roh[:n * 2], dtype="<u2").astype(np.int64)
        off = n * 2 + (n % 2) * 2
        d = np.frombuffer(roh[off:off + n * 6], dtype="<i2").reshape(-1, 3) * 0.0001
        return idx, d

    @staticmethod
    def _zwei(v):
        v = min(max(v, 0.0), 1.0)
        if v < 0.5:
            return [1.0 - v * 2.0, v * 2.0, 0.0]
        return [0.0, 2.0 - v * 2.0, v * 2.0 - 1.0]

    def gewichte(self, a):
        g = {}

        def dazu(name, w):
            if w > 0.002 and name in self.meta["formen"]:
                g[name] = g.get(name, 0.0) + w
        w = lambda k, s=0.5: float(a.get(k, s))
        mann = min(max(w("geschlecht", 1.0), 0), 1)
        geschl = {"female": 1 - mann, "male": mann}
        alt = min(max(w("alter", 0.1), 0), 1) * 0.8
        alter = {"young": 1 - alt, "old": alt}
        m3, w3 = self._zwei(w("muskeln")), self._zwei(w("gewicht"))
        mus = dict(zip(("minmuscle", "averagemuscle", "maxmuscle"), m3))
        gew = dict(zip(("minweight", "averageweight", "maxweight"), w3))
        h = min(max(w("groesse"), 0), 1)
        hoehe = {"minheight": max(0, 1 - h * 2), "maxheight": max(0, h * 2 - 1)}
        herk = a.get("herkunft", [0, 0, 1])
        hs = max(0.001, sum(herk))
        herkunft = {"african": herk[0] / hs, "asian": herk[1] / hs, "caucasian": herk[2] / hs}
        for gs in geschl:
            for al in alter:
                ga = geschl[gs] * alter[al]
                if ga < 0.001:
                    continue
                for r in herkunft:
                    dazu("%s-%s-%s" % (r, gs, al), ga * herkunft[r])
                for m in mus:
                    for ww in gew:
                        dazu("universal-%s-%s-%s-%s" % (gs, al, m, ww), ga * mus[m] * gew[ww])
                for hh in hoehe:
                    dazu("hoehe-%s-%s-%s" % (gs, al, hh), ga * hoehe[hh])
        c3, f3 = self._zwei(w("brust")), self._zwei(w("brust_fest"))
        for al in alter:
            for c, cw in zip(("mincup", "averagecup", "maxcup"), c3):
                for f, fw in zip(("minfirmness", "averagefirmness", "maxfirmness"), f3):
                    dazu("brust-%s-%s-%s" % (al, c, f), geschl["female"] * alter[al] * cw * fw)
        for rid, v in a.get("regler", {}).items():
            if v > 0:
                dazu(rid + "+", v)
            elif v < 0:
                dazu(rid + "-", -v)
        return g

    def form_berechnen(self, a=None):
        a = dict(STANDARD, **(a or {}))
        p = self.grund.copy()
        for name, w in self.gewichte(a).items():
            idx, d = self.form(name)
            np.add.at(p, idx, d * w)
        punkte = []
        for b in self.meta["gruppen"]["joint-ground"]:
            punkte.extend(range(int(b[0]), int(b[1]) + 1))
        boden = p[punkte].mean(axis=0)
        boden[0] = boden[2] = 0.0
        return p - boden

    def knochen_nr(self, name):
        return self.knochen.index(name)

    def knochen_anteil(self, namen):
        """Je Punkt: Summe der Gewichte der genannten Knochen (Teilstring-Vergleich)."""
        nr = [i for i, n in enumerate(self.knochen) if any(s in n for s in namen)]
        maske = np.isin(self.k_idx, nr)
        return (self.k_gew * maske).sum(axis=1)
