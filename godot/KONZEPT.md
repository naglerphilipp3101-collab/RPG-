# Spielkonzept (Arbeitstitel: „Insel der Elemente“)

Third-Person-Einzelspieler-RPG in Godot 4. Fokus: **Kampf, Sammeln und Crafting**, eingebettet in eine **lebendige Welt** mit Fraktionskriegen und einem Hauptstrang.
Mit **[Vorschlag]** markierte Punkte sind Ideen von Claude und noch nicht entschieden.

---

## 1. Setting & Story

- Eine große Insel im Meer mit unterschiedlichen **Biomen und Wetterzonen**.
- **6 Fraktionen** kämpfen um die Herrschaft und um die Ressourcen der Insel, führen Krieg und schließen zeitweise Allianzen.
- **Spieler:** Überlebender eines gefallenen Königreichs. Er wacht im Startgebiet auf.
- **Hauptstrang:**
  1. Der Spieler erledigt Quests für alle Fraktionen und lernt die Insel kennen.
  2. Ab einem bestimmten Punkt fallen **Dämonen** ein. Ihre Basis liegt in **Region 8**, von dort greifen sie an und erobern Städte.
  3. Ziel: Region 8 einnehmen und die Zerstörung der Insel abwenden.

## 2. Welt

| Teil | Inhalt |
|---|---|
| Region 1 | **Startgebiet:** klein, Tutorial |
| Regionen 2–7 | **6 Fraktionsregionen:** jeweils von einer Fraktion dominiert, mit 3 Hauptstädten, mehreren Dörfern, Forts, Dungeons und POIs |
| Region 8 | **Dämonenreich:** Endgebiet |

- Jede Region hat **Ressourcenschwerpunkte**, z. B. Gebirge → Eisen, Wald → Holz.
- **Städte erzeugen passiv Ressourcen** der Tiers 1–3 für die Wirtschaft.
- **Tier 4 bis 6** kommen nur durch den Spieler (oder seine Gilde) ins Spiel.
- Fraktionen kämpfen um Städte. Der Spieler kann einer Fraktion **beitreten**.

## 3. Kampf

- **Klassenlos:** Die Waffenwahl bestimmt die Rolle (Tank, DPS, Support).
- **Jede Waffe hat einen eigenen Skillbaum** (wie in New World).
- **Magie und Elemente vorerst zurückgestellt.** Dafür kommt später ein eigenes Konzept.

### 3.1 Waffentypen

| Nahkampf (einhändig) | Nahkampf (zweihändig) | Sonstige Nahkampfwaffen | Fernkampf |
|---|---|---|---|
| Einhandschwert | Zweihandschwert | Speer | Bogen |
| Einhandaxt | Zweihandaxt | Degen | Flinte |
| Einhandkeule (auch Morgenstern, Flegel) | Zweihandkeule (Kriegshammer …) | 2 Dolche | Armbrust |
| Schild (zusammen mit einer Einhandwaffe) | | | |

### 3.2 Kampfgrundlagen (umgesetzt in M1)

- Leichter Angriff (Kombo aus 3 Schlägen), schwerer Angriff (Taste halten)
- Blocken mit Schild (kostet Ausdauer, bei leerer Ausdauer wird die Deckung gebrochen)
- Ausweichrolle mit Unverwundbarkeitsfenster (kostet Ausdauer)
- 3 aktive Fähigkeiten pro Waffe (Q / R / F) mit Abklingzeit
- Gegner kündigen Angriffe an (Leuchten + Ausholen). Leichte Treffer unterbrechen sie dabei nicht, schwere schon.

## 4. Fortschritt

- **Hauptlevel:** steigt durch Quests und schaltet Ausrüstung frei: größere Tasche, besseres Werkzeug, Waffenrezepte.
- **Kampflevel:** getrennt nach Waffe und Element, steigt durch Benutzung (wie Waffenbeherrschung in New World).
- **Berufslevel:** pro Sammel- und Crafting-Beruf.

## 5. Sammeln

| Beruf | Ressourcen |
|---|---|
| Holzfällen | Holz |
| Bergbau | Erz, Stein |
| Fischen | Fische |
| Sammeln | Kräuter, Fasern, Pflanzen |
| Häuten | Felle, Leder (von Tieren und Monstern) |

- **6 Tiers** pro Ressource (Erze: Iron, Palladium, Mithril, Glacialore, Sungold, Darksteel). Für höhere Tiers braucht man ein höheres Berufslevel und besseres Werkzeug.
- Monster droppen zusätzliche Crafting-Materialien.

## 6. Crafting (angelehnt an New World)

**Veredelung (Rohstoff → Material):**
Schmelzen · Tischlern · Gerben · Weben · Steinmetz

**Herstellung:**
Waffenschmied · Rüstungsschmied · Ingenieur · Juwelier · Arcana · Koch

**Zusatzmaterialien:**
- Ins Rezept können zusätzliche Items gegeben werden, z. B. ein Schmiedestein (+ATK) oder ein Schleifstein (+Blutungschance).
- **Höheres Tier = mehr Zusatz-Slots.**

**Abbau-Formel (umgesetzt in M3):**
- Jede Rohstoffquelle hat **Lebenspunkte (LP)**, höheres Tier = mehr LP (z. B. Kiefer 30, Alte Eiche 60).
- Werkzeuge haben **Abbaukraft** (Start 10, Kupfer 12–13, Eisen 15–17, Harz als Zusatz +15 %).
- Abbauzeit = LP ÷ Abbaukraft (leicht verkürzt durch die Berufsstufe).

**Umschmieden zu Splittern (Anti-Grind):**
- Waffen mit schlechten Werten lassen sich in **Splitter** zerlegen.
- Mit genug Splittern baut man gezielt die **perfekte Endgame-Waffe** und wählt Perks und Werte selbst.

## 7. Wirtschaft & Gilde

- Städte bringen passiv Tier-1–3-Ressourcen in die Wirtschaft (Händler und Lager der Stadt).
- **Gilde:** Später kann der Spieler eine Gilde besitzen und **Produktionsstätten kaufen** (Mine, Sägewerk, Farm …). Diese erzeugen passiv Ressourcen, damit das Farmen im Spielverlauf leichter wird.

## 8. Lebendige Welt (angelehnt an S.T.A.L.K.E.R. A-Life)

Die Welt läuft auch ohne den Spieler weiter:
- Fraktionen **erobern Städte**, schließen und brechen Allianzen.
- **Events** passieren: Monsterwellen, Karawanen, Dämonenangriffe.
- Der Spieler kann **gejagt** werden, z. B. von verfeindeten Fraktionen oder Kopfgeldjägern.
- **Notrufe:** NPCs bitten um Hilfe gegen Monster oder um Items. Andere NPCs können sie ebenfalls erledigen.
- **Mehr Gegner** in der Welt, um die fehlenden Mitspieler zu ersetzen.

### 8.1 Technischer Ansatz [Vorschlag]

Zwei Ebenen, damit das auf einem normalen PC läuft:
- **Strategieebene (abstrakt):** Die ganze Insel läuft als Datensimulation: Fraktionsstärke, Stadtbesitz, NPC-Trupps als Datenpunkte auf einer Karte, Ressourcenflüsse. Sie tickt z. B. alle paar Sekunden und kostet kaum Leistung.
- **Szenenebene (konkret):** Nur in der Nähe des Spielers werden NPCs und Kämpfe als echte 3D-Objekte erzeugt. Entfernt sich der Spieler, werden sie wieder zu Datenpunkten.
- Diese Trennung wird **von Anfang an** eingebaut, damit später kein Umbau nötig ist.

## 9. Grafik

- Einheitlicher **Low-Poly-Stil**.
- Assets: Quaternius, KayKit, Kenney (kostenlos), Mixamo für Animationen, später ggf. Synty.

---

## 10. Umfang & Meilensteine [Vorschlag]

Das Gesamtkonzept ist sehr groß. Deshalb **datengetrieben** bauen: Items, Rezepte, Gegner, Quests und Fraktionen liegen in Datendateien, damit neuer Content ohne neuen Code dazukommt.

| # | Meilenstein | Inhalt |
|---|---|---|
| M1 ✅ | **Spielbarer Kern** | Third-Person-Steuerung, Kamera, Ausweichen, Schwert & Schild mit 3 Fähigkeiten, 3 Gegnertypen, Leben/Tod |
| M2 ✅ | **Sammeln & Inventar** | Holzfällen, Bergbau, Sammeln, Häuten, Fischen (Tier 1–2); Inventar mit Gewicht; Beute von Gegnern; Berufslevel |
| M3 ✅ | **Crafting** | 11 Werkstätten, Rezepte Tier 1–2, Zusatzmaterialien, Ausrüstung mit Zufallswerten, Tränke & Essen, Herstellungsberufe |
| M4 ✅ | **Waffen & Skills** | 12 Waffentypen + Schild, Fernkampf mit Zielen, Skillbaum pro Waffe (2 Äste, 4 aktive Fähigkeiten), Waffenmeisterschaft bis Stufe 20, 2 Waffenplätze |
| M5 | **Startgebiet** | Tutorial-Region mit Questbeginn, NPCs, Dialogen (Speichern ✅ vorgezogen) |
| M6 | **Erste Fraktionsregion** | Städte, Händler, Fraktionen, Hauptlevel-Freischaltungen |
| M7 | **Lebendige Welt v1** | Strategieebene, Stadteroberung, Notrufe, Events |
| M8+ | **Ausbau** | weitere Regionen, Gilde, Splitter-System, Dämonen, Region 8 |

## 11. Offene Fragen

- Magie-/Elementsystem: neues Konzept folgt

- Name des Spiels, Namen und Charakter der 6 Fraktionen?
- Welche Waffen genau zum Start?
- Wie wird der Spieler in Städten/Fraktionen dargestellt (Ruf, Ränge)?
- Tod: Was verliert man (Haltbarkeit, Items, nichts)?
- Tag/Nacht-Zyklus? Hunger/Ausdauer-Systeme?
