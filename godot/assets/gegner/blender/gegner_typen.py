"""Menschliche Gegnertypen: Körper, Hautfarbe, Kleidung/Rüstung je Slot, Farben, Abnutzung.

Alle nutzen den MakeHuman-Körper der Charaktererstellung (gemeinsames Gegner-Grundmodell, Abweichungen in 'aussehen').
Slots wie bei der Rüstung: kopf, brust, haende, beine, fuesse (None = frei, Haut sichtbar).
Rüstungsteile der Spieler kommen aus assets/ruestung/blender (iron.py Grundsätze, waffensaetze.py Waffensätze).
"""
import random

import kleidung as kl
from kleidung import ir, ws

SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]

# Gegner-Grundmodell (wie data/charakter.json "gegner_aussehen.gegner")
GRUND = {"geschlecht": 1.0, "alter": 0.2, "muskeln": 0.65, "gewicht": 0.55, "groesse": 0.55, "herkunft": [0.1, 0.1, 1.0],
	"regler": {"kiefer": 0.3, "nase_hoecker": 0.3, "augen_tiefe": -0.3}}

HAUT = {"normal": (0.70, 0.49, 0.36), "hell": (0.82, 0.63, 0.52), "zombie": (0.47, 0.50, 0.40), "vampir": (0.86, 0.84, 0.84),
	"kultist": (0.66, 0.50, 0.42)}


def L(*fns):
	"""Mehrere Bausteine zu einem Slot zusammenfassen."""
	def bau(K):
		out = []
		for fn in fns:
			out += fn(K)
		return out
	return bau


def ruestung(satz, slot):
	"""Ein Teil der Spieler-Rüstung (Iron): satz = leicht|mittel|schwer oder eine Waffe aus waffensaetze.SAETZE."""
	def bau(K):
		if satz in ("leicht", "mittel", "schwer"):
			return [getattr(ir, satz + "_" + slot)(K)]
		return [ws.BAU[satz][slot](K)]
	return bau


# Klassen der Waffensätze je Slot (L/M/S) für die Banditen-Mischung
def _klasse(satz, slot):
	if satz in ("leicht", "mittel", "schwer"):
		return satz[0].upper().replace("L", "L")
	return ws.SAETZE[satz][1][SLOTS.index(slot)]


MAGIE = ("fire_magic", "ice_magic", "lightning_magic", "life_magic", "void_magic")


def banditen_mix(saat, klassen="LM", magie=False):
	"""Zufällige Mischung aus Iron-Rüstungsteilen der Spieler (geklaut von toten Abenteurern).
	magie: nur Teile der Magiesätze (Hexer), sonst nur Teile der Kampfsätze."""
	rnd = random.Random(saat)
	quellen = list(MAGIE) if magie else ["leicht", "mittel", "schwer"] + [w for w in ws.SAETZE if w not in MAGIE]
	out = {}
	for slot in SLOTS:
		moeglich = [q for q in quellen if _klasse(q, slot) in klassen]
		if slot == "kopf" and rnd.random() < 0.3:
			out[slot] = None   # manche ohne Helm
			continue
		out[slot] = ruestung(rnd.choice(moeglich), slot)
	return out


TYPEN = {
	# ------------------------------------------------ Banditen
	"bandit_pluenderer": {"name": "Bandit: Plünderer", "gruppe": "Banditen", "slots": banditen_mix(9, "LM"),
		"waffe": "axe / knife / sword_shield"},
	"bandit_schlaeger": {"name": "Bandit: Schläger", "gruppe": "Banditen", "slots": banditen_mix(11, "MS"),
		"aussehen": {"muskeln": 0.85, "gewicht": 0.65}, "waffe": "hammer / greatsword / spear"},
	"bandit_schuetze": {"name": "Bandit: Schütze", "gruppe": "Banditen", "slots": banditen_mix(7, "LM"),
		"waffe": "bow / crossbow / musket"},
	"bandit_hexer": {"name": "Bandit: Hexer", "gruppe": "Banditen", "slots": banditen_mix(21, "LM", magie=True),
		"waffe": "fire / ice / lightning magic"},
	# ------------------------------------------------ Piraten
	"pirat_matrose": {"name": "Pirat: Matrose", "gruppe": "Piraten", "waffe": "rapier",
		"slots": {"kopf": kl.kopftuch, "brust": L(lambda K: kl.hemd(K, "futter", 0.76, 0.6, offen=0.32, puff=0.02), kl.schaerpe),
			"haende": None, "beine": lambda K: kl.hose(K, "stoff", 0.45, 0.02), "fuesse": None},
		"zerreissen": {"loecher": 0.1, "fransen": 1.0}, "haut": "hell",
		"farben": {"stoff_akzent": (0.45, 0.07, 0.06), "futter": (0.78, 0.74, 0.64), "stoff": (0.32, 0.33, 0.38)}},
	"pirat_enterer": {"name": "Pirat: Enterer", "gruppe": "Piraten", "waffe": "knife",
		"slots": {"kopf": None, "brust": L(lambda K: kl.hemd(K, "futter", 0.8, 0.0, offen=0.5), kl.schaerpe),
			"haende": None, "beine": lambda K: kl.hose(K, "stoff_dunkel", 0.6, 0.015), "fuesse": kl.fusslappen},
		"zerreissen": {"loecher": 0.2, "fransen": 1.4}, "aussehen": {"gewicht": 0.4, "muskeln": 0.75},
		"farben": {"stoff_akzent": (0.12, 0.2, 0.42), "futter": (0.7, 0.66, 0.55)}},
	"pirat_schuetze": {"name": "Pirat: Schütze", "gruppe": "Piraten", "waffe": "Pistole (neu)",
		"slots": {"kopf": kl.kopftuch,
			"brust": L(lambda K: [ir.leicht_brust(K)], lambda K: [ws.schraeg_riemen(K, 0.045, 0.02)[0].objekt()]),
			"haende": None, "beine": lambda K: kl.hose(K, "stoff", 0.8), "fuesse": lambda K: kl.stiefel(K, "leder", 0.28)},
		"farben": {"stoff_akzent": (0.10, 0.10, 0.12), "stoff": (0.38, 0.30, 0.22)}},
	"pirat_kapitaen": {"name": "Pirat: Kapitän", "gruppe": "Piraten", "waffe": "rapier + Pistole",
		"slots": {"kopf": kl.dreispitz,
			"brust": L(lambda K: kl.hemd(K, "futter", 0.82, 1.0, abstand=0.004, weite=0.0), kl.halstuch,
				lambda K: kl.mantel(K, "stoff_akzent"),
				lambda K: kl.schaerpe(K, 0.98, "stoff_dunkel", 0.05)),
			"haende": lambda K: [ws.rapier_haende(K)], "beine": lambda K: kl.hose(K, "stoff_dunkel"),
			"fuesse": lambda K: kl.stiefel(K, "leder_dunkel", 0.42)},
		"farben": {"stoff_akzent": (0.36, 0.05, 0.06), "stoff_dunkel": (0.07, 0.07, 0.08), "rand": (0.75, 0.6, 0.25),
			"futter": (0.85, 0.82, 0.74)}},
	# ------------------------------------------------ Wachen (Name und Level vom Ort)
	"wache_schild": {"name": "Wache: Schildwache", "gruppe": "Wachen", "waffe": "sword_shield",
		"slots": {"kopf": ruestung("schwer", "kopf"),
			"brust": L(ruestung("schwer", "brust"), lambda K: ws.tabard(K)[0]),
			"haende": ruestung("schwer", "haende"), "beine": ruestung("schwer", "beine"), "fuesse": ruestung("schwer", "fuesse")},
		"farben": {"stoff_akzent": (0.18, 0.22, 0.35)}},
	"wache_speer": {"name": "Wache: Speerträger", "gruppe": "Wachen", "waffe": "spear",
		"slots": {"kopf": ruestung("spear", "kopf"),
			"brust": L(ruestung("schwer", "brust"), lambda K: ws.tabard(K, 0.6)[0]),
			"haende": ruestung("schwer", "haende"), "beine": ruestung("schwer", "beine"), "fuesse": ruestung("schwer", "fuesse")},
		"farben": {"stoff_akzent": (0.18, 0.22, 0.35)}},
	"wache_bogen": {"name": "Wache: Bogenschütze", "gruppe": "Wachen", "waffe": "bow",
		"slots": {"kopf": ruestung("mittel", "kopf"),
			"brust": L(ruestung("mittel", "brust"), lambda K: ws.tabard(K, 0.62, 0.065)[0]),
			"haende": ruestung("leicht", "haende"), "beine": ruestung("mittel", "beine"), "fuesse": ruestung("mittel", "fuesse")},
		"farben": {"stoff_akzent": (0.18, 0.22, 0.35)}},
	"wache_hauptmann": {"name": "Wache: Hauptmann", "gruppe": "Wachen", "waffe": "greatsword",
		"slots": {"kopf": ruestung("hammer", "kopf"),
			"brust": L(ruestung("schwer", "brust"), lambda K: ws.tabard(K, 0.5)[0], lambda K: kl.cape(K, "stoff_akzent")),
			"haende": ruestung("schwer", "haende"), "beine": ruestung("schwer", "beine"), "fuesse": ruestung("schwer", "fuesse")},
		"aussehen": {"alter": 0.45, "muskeln": 0.8}, "farben": {"stoff_akzent": (0.18, 0.22, 0.35)}},
	# ------------------------------------------------ Zombies (Haut verwest, Kleidung zerrissen)
	"zombie_wandler": {"name": "Zombie: Wandler", "gruppe": "Zombies", "waffe": "Hände", "haut": "zombie",
		"slots": {"kopf": None, "brust": L(lambda K: kl.hemd(K, "futter", 0.72, 0.9), kl.strick), "haende": None,
			"beine": lambda K: kl.hose(K, "stoff", 0.85), "fuesse": kl.fusslappen},
		"zerreissen": {"loecher": 0.28, "fransen": 1.5}, "aussehen": {"gewicht": 0.3, "muskeln": 0.35, "alter": 0.4},
		"farben": {"futter": (0.62, 0.55, 0.42), "stoff": (0.28, 0.22, 0.16)}},
	"zombie_buerger": {"name": "Zombie: Bürger", "gruppe": "Zombies", "waffe": "Hände", "haut": "zombie",
		"slots": {"kopf": None, "brust": L(lambda K: kl.hemd(K, "stoff_akzent", 0.62, 1.0, weite=0.06),
			lambda K: ir.guertel(K, 0.98, 0.04, 0.035)),
			"haende": None, "beine": lambda K: kl.hose(K, "stoff_dunkel"), "fuesse": kl.schuhe},
		"zerreissen": {"loecher": 0.22, "fransen": 1.2}, "aussehen": {"gewicht": 0.35, "alter": 0.6},
		"farben": {"stoff_akzent": (0.2, 0.24, 0.3), "stoff_dunkel": (0.15, 0.13, 0.12)}},
	"zombie_spucker": {"name": "Zombie: Spucker", "gruppe": "Zombies", "waffe": "Säure (Fernkampf)", "haut": "zombie",
		"slots": {"kopf": None, "brust": L(lambda K: kl.hemd(K, "futter", 0.7, 0.55, weite=0.07)), "haende": None,
			"beine": lambda K: kl.hose(K, "stoff", 0.5), "fuesse": None},
		"zerreissen": {"loecher": 0.3, "fransen": 1.5}, "aussehen": {"gewicht": 1.0, "muskeln": 0.2},
		"farben": {"futter": (0.55, 0.5, 0.36), "stoff": (0.3, 0.25, 0.2)}},
	"zombie_brecher": {"name": "Zombie: Brecher", "gruppe": "Zombies", "waffe": "Hände (wuchtig)", "haut": "zombie",
		"slots": {"kopf": None, "brust": None, "haende": None,
			"beine": L(lambda K: kl.hose(K, "stoff", 0.55), kl.strick), "fuesse": None},
		"zerreissen": {"loecher": 0.25, "fransen": 1.8}, "aussehen": {"groesse": 1.0, "muskeln": 1.0, "gewicht": 0.75},
		"farben": {"stoff": (0.28, 0.24, 0.2)}, "skalierung": 1.25},
	"zombie_abenteurer": {"name": "Zombie: Gefallener Abenteurer", "gruppe": "Zombies", "waffe": "rostige Spielerwaffe",
		"haut": "zombie", "slots": dict(banditen_mix(2, "MS"), kopf=None),
		"zerreissen": {"loecher": 0.18, "fransen": 1.0}, "aussehen": {"gewicht": 0.3},
		"farben": {"platte": (0.45, 0.33, 0.24), "rand": (0.4, 0.3, 0.22), "kette": (0.42, 0.33, 0.25)}},
	# ------------------------------------------------ Vampire (älter, dunkel, fahl)
	"vampir_klinge": {"name": "Vampir: Klinge", "gruppe": "Vampire", "waffe": "rapier / greatsword", "haut": "vampir",
		"slots": {"kopf": None,
			"brust": L(lambda K: kl.hemd(K, "stoff_akzent", 0.85, 1.0, abstand=0.004, weite=0.0), lambda K: ws.brustplatte_vorne(K, 0.03, 0.98)[0],
				lambda K: kl.mantel(K, "stoff_dunkel", 0.42, 0.42, "stoff_akzent", knoepfe="rand"), kl.stehkragen),
			"haende": kl.handschuhe, "beine": lambda K: kl.hose(K, "stoff_dunkel"),
			"fuesse": lambda K: kl.stiefel(K, "leder_dunkel", 0.4, False)},
		"aussehen": {"alter": 0.6, "gewicht": 0.35, "muskeln": 0.55, "groesse": 0.7},
		"farben": {"stoff_dunkel": (0.05, 0.04, 0.05), "stoff_akzent": (0.28, 0.02, 0.04), "platte": (0.18, 0.17, 0.19),
			"rand": (0.55, 0.5, 0.45), "leder_dunkel": (0.06, 0.04, 0.04)}},
	"vampir_magier": {"name": "Vampir: Magier", "gruppe": "Vampire", "waffe": "void_magic (Lebensentzug)", "haut": "vampir",
		"slots": {"kopf": None,
			"brust": L(lambda K: kl.kutte(K, "stoff_dunkel", 0.06), kl.stehkragen, kl.halstuch,
				lambda K: ir.guertel(K, 0.98, 0.05, 0.05, "stoff_akzent")),
			"haende": kl.handschuhe, "beine": None, "fuesse": kl.schuhe},
		"aussehen": {"alter": 0.85, "gewicht": 0.25, "muskeln": 0.3, "groesse": 0.65},
		"farben": {"stoff_dunkel": (0.05, 0.04, 0.06), "stoff_akzent": (0.28, 0.02, 0.04), "futter": (0.7, 0.66, 0.6),
			"leder_dunkel": (0.06, 0.04, 0.04), "leder": (0.08, 0.05, 0.05)}},
	"vampir_fuerst": {"name": "Vampir: Fürst", "gruppe": "Vampire", "waffe": "rapier + void_magic", "haut": "vampir",
		"slots": {"kopf": None,
			"brust": L(lambda K: kl.hemd(K, "stoff_akzent", 0.85, 1.0, abstand=0.004, weite=0.0), kl.halstuch,
				lambda K: kl.mantel(K, "stoff_dunkel", 0.3, 0.38, "stoff_akzent", knoepfe="rand"),
				lambda K: kl.stehkragen(K, hoehe=0.26, weit=0.12), lambda K: kl.cape(K, "stoff_dunkel", unten_z=0.12)),
			"haende": kl.handschuhe, "beine": lambda K: kl.hose(K, "stoff_dunkel"),
			"fuesse": lambda K: kl.stiefel(K, "leder_dunkel", 0.45, False)},
		"aussehen": {"alter": 0.7, "gewicht": 0.35, "muskeln": 0.5, "groesse": 0.8},
		"farben": {"stoff_dunkel": (0.04, 0.03, 0.04), "stoff_akzent": (0.32, 0.02, 0.05), "rand": (0.7, 0.58, 0.3),
			"futter": (0.8, 0.76, 0.7), "leder_dunkel": (0.05, 0.03, 0.03)}},
	# ------------------------------------------------ Zahr-Kultisten
	"kultist_akolyth": {"name": "Kultist: Akolyth", "gruppe": "Kultisten", "waffe": "knife", "haut": "kultist",
		"slots": {"kopf": kl.kutten_kapuze, "brust": L(kl.kutte, kl.strick), "haende": None, "beine": None,
			"fuesse": kl.fusslappen},
		"zerreissen": {"loecher": 0.0, "fransen": 0.8},
		"farben": {"stoff": (0.32, 0.27, 0.22), "stoff_akzent": (0.25, 0.05, 0.05), "leder": (0.25, 0.2, 0.14)}},
	"kultist_beschwoerer": {"name": "Kultist: Beschwörer", "gruppe": "Kultisten", "waffe": "void_magic", "haut": "kultist",
		"slots": {"kopf": lambda K: kl.kutten_kapuze(K, "stoff_dunkel", "rand"),
			"brust": L(lambda K: kl.kutte(K, "stoff_dunkel"), lambda K: ir.guertel(K, 0.98, 0.06, 0.04, "leder_dunkel")),
			"haende": kl.handschuhe, "beine": None, "fuesse": kl.schuhe},
		"farben": {"stoff_dunkel": (0.07, 0.05, 0.08), "rand": (0.55, 0.12, 0.6)}},
	"kultist_eiferer": {"name": "Kultist: Eiferer", "gruppe": "Kultisten", "waffe": "fire_magic", "haut": "kultist",
		"slots": {"kopf": lambda K: kl.kutten_kapuze(K, "stoff_akzent", "stoff_dunkel"),
			"brust": L(lambda K: kl.kutte(K, "stoff_akzent", 0.3), kl.strick), "haende": None,
			"beine": lambda K: kl.hose(K, "stoff_dunkel"), "fuesse": kl.schuhe},
		"farben": {"stoff_akzent": (0.42, 0.06, 0.03), "stoff_dunkel": (0.08, 0.06, 0.05)}},
}
