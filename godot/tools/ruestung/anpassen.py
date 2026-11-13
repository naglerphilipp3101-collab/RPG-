"""Passform: Rüstungsteile folgen dem Körper (alle Regler, Mann und Frau).

Die Rüstung wird einmal um den Standard-Mann gebaut (rgeo/iron/waffensaetze). Für jeden
anderen Körper verschiebt sich jeder Rüstungspunkt so wie die Haut unter ihm:

    punkt = punkt_0 + Σ gewicht_i · (haut_i − haut_0_i)

über die K nächsten Hautpunkte des Standard-Körpers. Die Gewichte fallen weich auf 0 ab
(beim K+1-ten Punkt genau 0), damit benachbarte Rüstungspunkte keine Sprünge machen.
Das ist linear in den Körperformen; das Spiel kann dieselbe Rechnung beim Laden machen.

Zusätzlich je Teil:
- verdeckt: Hautpunkte, die unter dem Teil liegen und ausgeblendet werden (kein Durchstoßen).
- korrektur_frau: geglättete Zusatzverschiebung für den Frauenkörper (Geschlecht 0),
  wird mit (1 − geschlecht) überblendet. Sie macht aus „folgt jeder Rundung“ eine
  getriebene Form und hält Mindestabstand zur Haut.

Koordinaten: wie MakeHuman/glTF (Y oben, Blick +Z, Meter).
"""
import json
import struct

import numpy as np
from scipy.spatial import cKDTree

from mensch_lesen import Mensch

K_NACHBARN = 12


# ------------------------------------------------------------------ GLB lesen/schreiben
def glb_lesen(pfad):
	"""-> (json, binärpuffer)"""
	d = open(pfad, "rb").read()
	n = struct.unpack("<I", d[12:16])[0]
	j = json.loads(d[20:20 + n])
	o = 20 + n
	bl = struct.unpack("<I", d[o:o + 4])[0]
	return j, bytearray(d[o + 8:o + 8 + bl])


def _accessor(j, b, i, typ=np.float32):
	a = j["accessors"][i]
	bv = j["bufferViews"][a["bufferView"]]
	anz = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
	dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]]
	off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
	return np.frombuffer(bytes(b[off:off + a["count"] * anz * np.dtype(dt).itemsize]), dtype=dt).reshape(a["count"], anz)


def glb_netz(pfad):
	"""Alle Primitive eines GLB als ein Netz: Punkte, Dreiecke, Material je Dreieck, Bereiche je Primitive."""
	j, b = glb_lesen(pfad)
	pts, dr, mat, bereiche = [], [], [], []
	n0 = 0
	for m in j["meshes"]:
		for p in m["primitives"]:
			pos = _accessor(j, b, p["attributes"]["POSITION"]).astype(np.float64)
			idx = _accessor(j, b, p["indices"]).reshape(-1, 3).astype(np.int64)
			name = j["materials"][p["material"]]["name"] if "material" in p else "?"
			pts.append(pos)
			dr.append(idx + n0)
			mat += [name] * len(idx)
			bereiche.append((n0, n0 + len(pos), name))
			n0 += len(pos)
	return np.concatenate(pts), np.concatenate(dr), np.array(mat), bereiche


# ------------------------------------------------------------------ Körper
class Koerper:
	"""Haut des Körpers für ein Aussehen (nur sichtbare Hautpunkte, ohne Hilfsgeometrie)."""

	def __init__(self, m: Mensch, aussehen=None):
		self.m = m
		alle = m.form_berechnen(aussehen)
		self.haut_idx = np.unique(m.koerper_dreiecke)          # MakeHuman-Indizes der Haut
		self.p = alle[self.haut_idx]
		umb = -np.ones(len(alle), np.int64)
		umb[self.haut_idx] = np.arange(len(self.haut_idx))
		self.dreiecke = umb[m.koerper_dreiecke][:, [0, 2, 1]]   # MakeHuman dreht im Uhrzeigersinn -> nach außen
		self.n = normalen(self.p, self.dreiecke)


def normalen(p, dr):
	a, b, c = p[dr[:, 0]], p[dr[:, 1]], p[dr[:, 2]]
	fn = np.cross(b - a, c - a)
	n = np.zeros_like(p)
	for k in range(3):
		np.add.at(n, dr[:, k], fn)
	l = np.linalg.norm(n, axis=1, keepdims=True)
	return n / np.maximum(l, 1e-12)


# ------------------------------------------------------------------ Bindung
def bindung(punkte, haut0, k=K_NACHBARN, max_n=None):
	"""Je Rüstungspunkt Hautpunkte und Gewichte (Summe 1).

	Glockenkurve mit Breite sigma = Abstand zur Haut (mind. 1,2 cm, höchstens 6 cm): hautnahe Punkte
	folgen der Haut genau, weiter abstehende Teile (Helmglocke, Robensaum, Schulterplatte) dem
	geglätteten Mittel – so verschieben sich übereinanderliegende Teile gleich und kreuzen sich nicht.
	Höchstens max_n Hautpunkte je Rüstungspunkt (die mit den größten Gewichten)."""
	max_n = max_n or MAX_N
	baum = cKDTree(haut0)
	d0, _ = baum.query(punkte, k=1)
	sigma = np.clip(d0 * SIGMA_FAKTOR, SIGMA_MIN, SIGMA_MAX)
	idx = np.zeros((len(punkte), max_n), np.int32)
	w = np.zeros((len(punkte), max_n), np.float32)
	# Hautpunkte grob ausdünnen, wo sigma groß ist (gleichmäßiger Abdeckung statt der nächsten Handvoll)
	grob = _ausduennen(haut0, 0.02)
	baum_grob = cKDTree(haut0[grob])
	for i, (p, sg) in enumerate(zip(punkte, sigma)):
		if sg < 0.025:
			nb = np.array(baum.query_ball_point(p, 2.5 * sg))
		else:
			nb = grob[np.array(baum_grob.query_ball_point(p, 2.5 * sg), dtype=np.int64)]
		if len(nb) == 0:
			nb = np.array([baum.query(p)[1]])
		dd = np.linalg.norm(haut0[nb] - p, axis=1)
		ww = np.exp(-0.5 * (dd / sg) ** 2) - np.exp(-0.5 * 2.5 ** 2)
		if len(nb) > max_n:
			o = np.argpartition(-ww, max_n)[:max_n]
			nb, ww = nb[o], ww[o]
		ww = np.maximum(ww, 0) + 1e-9
		idx[i, :len(nb)] = nb
		w[i, :len(nb)] = ww / ww.sum()
	return idx, w


SIGMA_FAKTOR = 1.0
SIGMA_MIN = 0.012
SIGMA_MAX = 0.06
MAX_N = 32


def _ausduennen(p, abstand):
	"""Indizes einer gleichmäßig verteilten Teilmenge (Raster, je Zelle ein Punkt)."""
	z = np.floor(p / abstand).astype(np.int64)
	_, erst = np.unique(z, axis=0, return_index=True)
	return np.sort(erst)


def anwenden(punkte0, bind, haut0, haut):
	idx, w = bind
	d = haut - haut0
	return punkte0 + (d[idx] * w[..., None]).sum(1)


# ------------------------------------------------------------------ Verdeckte Haut
def verdeckt(haut, haut_n, dreiecke, ruest_p, ruest_dr, reichweite=0.30, schrumpfen=1):
	"""Hautpunkte, deren Strahl entlang der Normale das Teil trifft (nahe genug).
	Danach um `schrumpfen` Ringe verkleinert, damit am Rand immer etwas Haut bleibt."""
	import bpy  # noqa: F401  (mathutils kommt mit bpy)
	from mathutils import Vector
	from mathutils.bvhtree import BVHTree
	bvh = BVHTree.FromPolygons([Vector(v) for v in ruest_p], ruest_dr.tolist(), all_triangles=True)
	tr = np.zeros(len(haut), bool)
	for i, (p, n) in enumerate(zip(haut, haut_n)):
		h = bvh.ray_cast(Vector(p - n * 0.002), Vector(n), reichweite)
		tr[i] = h[0] is not None
	# kleine Löcher schließen (z. B. zwischen Riemen), dann vom Rand her schrumpfen
	nb = _nachbarn(len(haut), dreiecke)
	for _ in range(2):
		tr = tr | (_anteil(tr, nb) >= 0.6)
	for _ in range(schrumpfen):
		tr = tr & (_anteil(tr, nb) >= 0.999)
	return tr


def _nachbarn(n, dr):
	import scipy.sparse as sp
	r = np.concatenate([dr[:, 0], dr[:, 1], dr[:, 2], dr[:, 1], dr[:, 2], dr[:, 0]])
	c = np.concatenate([dr[:, 1], dr[:, 2], dr[:, 0], dr[:, 0], dr[:, 1], dr[:, 2]])
	a = sp.coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n)).tocsr()
	a.data[:] = 1.0
	return a


def _anteil(maske, nb):
	s = nb @ maske.astype(np.float64)
	z = np.asarray(nb.sum(1)).ravel()
	return s / np.maximum(z, 1)
