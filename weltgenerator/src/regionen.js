// ===== Regionen: Nebeninsel, Zentralberg, Fraktionsregionen, Siedlungsvorschläge =====
// Wird nach marker.js und vor app.js geladen; nutzt deren Globals erst zur Laufzeit (zustand, N, ZELLE, WELT_API …).
//
// Regionen-IDs: 0 Meer · 1 Startgebiet · 2 … (1 + Fraktionen) Fraktionsregionen · 250 Zentralberg · 251 Nebeninseln
// Die Grenzen entstehen durch Ausbreitung von Startpunkten aus (Dijkstra auf 8-m-Raster): Flüsse und steile Hänge
// sind teuer, deshalb treffen sich die Regionen bevorzugt dort. Die Flächen werden über Startvorsprünge angeglichen.

const REGION_BERG = 250, REGION_INSEL = 251;
const RICHTUNGEN = ["Ost", "Südost", "Süd", "Südwest", "West", "Nordwest", "Nord", "Nordost"];
const regionenZustand = { REG: null, namen: {}, gipfel: null, insel: null, zeigen: true, bild: null, mitte: null };

function regionenZuruecksetzen() {
  regionenZustand.REG = null; regionenZustand.namen = {}; regionenZustand.gipfel = null; regionenZustand.bild = null; regionenZustand.mitte = null;
  regionenInfo();
}

// Zusammenhangskomponenten des Landes; liefert Komponenten-IDs, Größen, Schwerpunkte und die Hauptinsel
function landmassen() {
  const H = zustand.H, comp = new Int32Array(N * N).fill(-1), groesse = [], schwer = [];
  for (let s = 0; s < N * N; s++) {
    if (H[s] <= 1.5 || comp[s] >= 0) continue;
    const id = groesse.length; let n = 0, sx = 0, sy = 0; const stapel = [s]; comp[s] = id;
    while (stapel.length) {
      const i = stapel.pop(), x = i % N; n++; sx += x; sy += (i / N) | 0;
      for (const j of [i - 1, i + 1, i - N, i + N])
        if (j >= 0 && j < N * N && H[j] > 1.5 && comp[j] < 0 && Math.abs((j % N) - x) <= 1) { comp[j] = id; stapel.push(j); }
    }
    groesse.push(n); schwer.push([sx / n, sy / n]);
  }
  const haupt = groesse.indexOf(Math.max(...groesse));
  return { comp, groesse, schwer, haupt };
}

// Abstand (in Zellen) jeder Zelle zur nächsten Zelle, für die quelle(i) gilt
function abstandsfeld(quelle) {
  const d = new Int32Array(N * N).fill(-1), q = new Int32Array(N * N); let qh = 0, qt = 0;
  for (let i = 0; i < N * N; i++) if (quelle(i)) { d[i] = 0; q[qt++] = i; }
  while (qh < qt) {
    const i = q[qh++], x = i % N;
    for (const j of [i - 1, i + 1, i - N, i + N]) if (j >= 0 && j < N * N && d[j] < 0 && Math.abs((j % N) - x) <= 1) { d[j] = d[i] + 1; q[qt++] = j; }
  }
  return d;
}

// ---------- Nebeninsel ----------
// Sucht eine Meeresstelle 550–900 m vor der Küste (bevorzugt im Süden, Abstand zum Kartenrand) und formt dort eine Insel.
async function nebeninselFormen() {
  const H = zustand.H, L = landmassen();
  const zumLand = abstandsfeld((i) => H[i] > 1.5);
  const [, my] = L.schwer[L.haupt], rand = Math.round(600 / ZELLE);
  let wahl = null;
  for (let y = rand; y < N - rand; y += 8) for (let x = rand; x < N - rand; x += 8) {
    const i = y * N + x, d = zumLand[i] * ZELLE;
    if (d >= 550 && d <= 900 && H[i] < -15 && (!wahl || y - my > wahl.sued)) wahl = { x, y, sued: y - my };
  }
  if (!wahl) { status("Kein Platz für eine Nebeninsel gefunden (Insel zu groß?)"); return; }
  const { x: ix, y: iy } = wahl;
  const kreis = (r, n, dx = 0, dy = 0) => Array.from({ length: n }, (_, k) => [ix + dx + Math.cos(k / n * 6.283) * r, iy + dy + Math.sin(k / n * 6.283) * r * 0.75]);
  const alt = [zustand.groesse, zustand.staerke];
  zustand.groesse = 240; zustand.staerke = 1;
  WELT_API.strichTest("land", [[ix, iy], ...kreis(22, 12), ...kreis(40, 16), ...kreis(20, 8, 35, -10)], 1.0);
  zustand.groesse = 360; zustand.staerke = 0.6;
  WELT_API.strichTest("huegel", [[ix, iy], ...kreis(18, 8)], 1.0);
  zustand.groesse = 180; zustand.staerke = 0.8;
  WELT_API.strichTest("gebirge", [[ix - 6, iy - 4], [ix + 4, iy + 2]], 1.0);
  [zustand.groesse, zustand.staerke] = alt;
  await erosionAnwenden();
  regionenZustand.insel = [ix, iy];
  status(`Nebeninsel geformt (${Math.round(ix * ZELLE - WELT / 2)} / ${Math.round(iy * ZELLE - WELT / 2)} m)`);
}

// ---------- Zentralberg ----------
// Hebt die Inselmitte großflächig an, setzt sternförmige Grate und wendet Erosion an.
async function zentralbergFormen() {
  const H = zustand.H, L = landmassen(), ziel = parseFloat($("p-berghoehe-zentrum").value);
  const cx = Math.round(L.schwer[L.haupt][0]), cy = Math.round(L.schwer[L.haupt][1]);
  const gipfelSuchen = (r) => { let m = -1e9, gx = cx, gy = cy;
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (H[y * N + x] > m) { m = H[y * N + x]; gx = x; gy = y; }
    return [m, gx, gy]; };
  const vorher = gipfelSuchen(Math.round(600 / ZELLE))[0];
  // Je Pinselpunkt hebt "anheben" (Stärke 1) die Mitte um 25 m; Grate und Erosion bringen etwa 100 m dazu
  const schritte = Math.max(2, Math.round((ziel - vorher - 100) / 25));
  const sockel = Math.ceil(schritte * 0.55), kern = schritte - sockel;
  const alt = [zustand.groesse, zustand.staerke];
  zustand.groesse = 1600; zustand.staerke = 1;
  WELT_API.strichTest("anheben", Array.from({ length: sockel }, () => [cx, cy]), 1.0);
  zustand.groesse = 900;
  WELT_API.strichTest("anheben", Array.from({ length: kern }, () => [cx, cy]), 1.0);
  zustand.groesse = 420; zustand.staerke = 0.6;
  const grate = [];
  for (let k = 0; k < 5; k++) { const a = k / 5 * 6.283 + 0.4; for (let t = 0; t <= 1; t += 0.1) grate.push([cx + Math.cos(a) * t * 150, cy + Math.sin(a) * t * 150]); }
  WELT_API.strichTest("gebirge", grate, 0.5);
  [zustand.groesse, zustand.staerke] = alt;
  await erosionAnwenden();
  const [hoehe, gx, gy] = gipfelSuchen(Math.round(800 / ZELLE));
  regionenZustand.gipfel = [gx, gy];
  status(`Zentralberg geformt: Gipfel ${Math.round(hoehe)} m`);
}

// ---------- Regionen ----------
function regionenBerechnen() {
  const H = zustand.H, AF = zustand.A, L = landmassen(), comp = L.comp, haupt = L.haupt;
  const fraktionen = parseInt($("p-fraktionen").value, 10), startAnteil = parseFloat($("p-startanteil").value) / 100;
  const bergLinie = parseFloat($("p-berglinie").value);
  // Gipfel: gespeichert oder höchster Punkt im Umkreis von 1,5 km um die Inselmitte
  let [gx, gy] = regionenZustand.gipfel || [Math.round(L.schwer[haupt][0]), Math.round(L.schwer[haupt][1])];
  if (!regionenZustand.gipfel) { let m = -1e9; const r = Math.round(1500 / ZELLE), cx = gx, cy = gy;
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (comp[y * N + x] === haupt && H[y * N + x] > m) { m = H[y * N + x]; gx = x; gy = y; } }
  const REG = new Uint8Array(N * N);
  for (let i = 0; i < N * N; i++) if (H[i] > 1.5 && comp[i] !== haupt) REG[i] = REGION_INSEL;
  // Zentralberg: zusammenhängend über der Höhenlinie, höchstens 1,5 km vom Gipfel
  if (H[gy * N + gx] > bergLinie) {
    const st = [gy * N + gx]; REG[gy * N + gx] = REGION_BERG;
    while (st.length) { const i = st.pop();
      for (const j of [i - 1, i + 1, i - N, i + N]) { const jx = j % N, jy = (j / N) | 0;
        if (REG[j] === 0 && comp[j] === haupt && H[j] > bergLinie && Math.hypot(jx - gx, jy - gy) * ZELLE < 1500) { REG[j] = REGION_BERG; st.push(j); } } }
  }
  // Grobraster (2 Zellen) mit Kosten: Flüsse und Steigung bremsen
  const G = N / 2, kosten = new Float64Array(G * G).fill(-1), land = [];
  for (let y = 1; y < G - 1; y++) for (let x = 1; x < G - 1; x++) {
    const i = (y * 2) * N + x * 2; if (comp[i] !== haupt || REG[i] === REGION_BERG) continue;
    const st = Math.max(Math.abs(H[i + 2] - H[i - 2]), Math.abs(H[i + 2 * N] - H[i - 2 * N])) / (4 * ZELLE);
    const fluss = Math.max(AF[i], AF[i + 1], AF[i + N], AF[i + N + 1]) > FLUSS_SCHWELLE ? 6 : 0;
    kosten[y * G + x] = 1 + fluss + Math.min(st, 1) * 8; land.push([x, y]);
  }
  // Startpunkte: Süden (Startgebiet) + Fraktionen ringförmig um den Gipfel
  const sued = land.slice().sort((a, b) => b[1] - a[1]).slice(0, Math.max(1, Math.floor(land.length * 0.05)));
  const ziele = [[sued.reduce((s, p) => s + p[0], 0) / sued.length, sued.reduce((s, p) => s + p[1], 0) / sued.length]];
  const R = Math.sqrt(land.length / Math.PI);
  for (let k = 0; k < fraktionen; k++) { const a = Math.PI / 2 + (k + 0.5) / fraktionen * 2 * Math.PI; ziele.push([gx / 2 + Math.cos(a) * R * 0.6, gy / 2 + Math.sin(a) * R * 0.6]); }
  const saat = ziele.map(([x, y]) => { let best = land[0], bd = Infinity; for (const p of land) { const d = (p[0] - x) ** 2 + (p[1] - y) ** 2; if (d < bd) { bd = d; best = p; } } return best; });
  const anzahl = saat.length, zielAnteil = [startAnteil, ...Array(fraktionen).fill((1 - startAnteil) / fraktionen)];
  const lab = new Int8Array(G * G);
  const lauf = (vorsprung) => {
    const dist = new Float64Array(G * G).fill(Infinity); lab.fill(-1);
    const heap = [];
    const push = (d, i, r) => { heap.push([d, i, r]); let k = heap.length - 1; while (k > 0) { const p = (k - 1) >> 1; if (heap[p][0] <= heap[k][0]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
    const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } } return top; };
    saat.forEach(([x, y], r) => { dist[y * G + x] = vorsprung[r]; push(vorsprung[r], y * G + x, r); });
    while (heap.length) {
      const [d, i, r] = pop(); if (d > dist[i] || lab[i] >= 0) continue; lab[i] = r; const x = i % G;
      for (const j of [i - 1, i + 1, i - G, i + G]) {
        if (!(kosten[j] >= 0) || lab[j] >= 0 || Math.abs((j % G) - x) > 1) continue;
        const nd = d + kosten[j]; if (nd < dist[j]) { dist[j] = nd; push(nd, j, r); }
      }
    }
    const fl = Array(anzahl).fill(0); for (let i = 0; i < G * G; i++) if (lab[i] >= 0) fl[lab[i]]++; return fl;
  };
  const vorsprung = Array(anzahl).fill(0); let beste = Infinity, besterVorsprung = vorsprung.slice(), schritt = 60;
  for (let it = 0; it < 30; it++) {
    const fl = lauf(vorsprung), s = fl.reduce((a, b) => a + b, 0);
    const abw = fl.reduce((m, f, r) => Math.max(m, Math.abs(f / s - zielAnteil[r])), 0);
    if (abw < beste) { beste = abw; besterVorsprung = vorsprung.slice(); }
    for (let r = 0; r < anzahl; r++) vorsprung[r] += schritt * Math.max(-1, Math.min(1, (fl[r] / s - zielAnteil[r]) / zielAnteil[r]));
    schritt *= 0.92;
  }
  lauf(besterVorsprung);
  for (let i = 0; i < N * N; i++) if (comp[i] === haupt && REG[i] !== REGION_BERG) {
    const l = lab[((i / N | 0) >> 1) * G + ((i % N) >> 1)]; REG[i] = l >= 0 ? l + 1 : 1;
  }
  // Namen nach Himmelsrichtung vom Gipfel aus
  const namen = { 1: "Startgebiet", [REGION_BERG]: "Zentralberg", [REGION_INSEL]: "Nebeninsel" };
  for (let k = 0; k < fraktionen; k++) {
    const [sx, sy] = saat[k + 1]; let a = Math.atan2(sy * 2 - gy, sx * 2 - gx); if (a < 0) a += 2 * Math.PI;
    let name = RICHTUNGEN[Math.round(a / (Math.PI / 4)) % 8];
    while (Object.values(namen).includes(name)) name += "²";
    namen[k + 2] = name;
  }
  Object.assign(regionenZustand, { REG, namen, gipfel: [gx, gy] });
  regionenBildBauen(); regionenInfo(); ansicht.zeichne();
  status(`Regionen berechnet (größte Abweichung von der Zielfläche: ${(beste * 100).toFixed(1)} %)`);
}

// ---------- Siedlungen ----------
// Ersetzt Städte, Dörfer, Dungeons und POIs durch einen Vorschlag: je Fraktionsregion N Städte und M Dörfer,
// ein Startdorf, Gipfel und Dungeon-Eingang am Zentralberg, ein Dungeon je Nebeninsel. Felder und Minen bleiben.
function siedlungenVorschlagen() {
  if (!regionenZustand.REG) regionenBerechnen();
  const H = zustand.H, REG = regionenZustand.REG, [gx, gy] = regionenZustand.gipfel;
  const staedteProRegion = parseInt($("p-staedte").value, 10), doerferProRegion = parseInt($("p-doerfer").value, 10);
  let saatWert = params().seed * 7 + 13; const zufall = () => { saatWert = (saatWert * 16807) % 2147483647; return saatWert / 2147483647; };
  const kueste = abstandsfeld((i) => H[i] <= 1.5);
  const steig = (x, y) => Math.max(Math.abs(H[y * N + x - 3] - H[y * N + x + 3]), Math.abs(H[(y - 3) * N + x] - H[(y + 3) * N + x])) / (6 * ZELLE);
  const innen = (x, y, reg, r) => { for (let k = 0; k < 8; k++) { const a = k / 8 * 6.283; if (REG[Math.round(y + Math.sin(a) * r) * N + Math.round(x + Math.cos(a) * r)] !== reg) return false; } return true; };
  const geeignet = (x, y, reg, minKueste, maxSt, rand) => { const i = y * N + x;
    return REG[i] === reg && H[i] >= 4 && H[i] <= 160 && kueste[i] * ZELLE >= minKueste && steig(x, y) <= maxSt && innen(x, y, reg, rand); };
  const kandidaten = (reg, minK, maxSt, rand) => { const k = []; const rz = Math.round(rand / ZELLE);
    for (let y = 40; y < N - 40; y += 5) for (let x = 40; x < N - 40; x += 5) if (geeignet(x, y, reg, minK, maxSt, rz)) k.push([x, y]); return k; };
  const neu = [];
  const abstand = (x, y) => neu.reduce((m, o) => Math.min(m, Math.hypot(o.x - x, o.y - y) * ZELLE), Infinity);
  const fraktionsIds = Object.keys(regionenZustand.namen).map(Number).filter((r) => r >= 2 && r < REGION_BERG).sort((a, b) => a - b);
  for (const r of fraktionsIds) {
    const name = regionenZustand.namen[r];
    // Städte: möglichst weit auseinander (mind. 1,3 km), eben, nicht am Rand der Region
    const kStadt = kandidaten(r, 180, 0.07, 180);
    const staedte = [];
    for (let k = 0; k < staedteProRegion && kStadt.length; k++) {
      let best = null, bw = -Infinity;
      for (let t = 0; t < 3000; t++) {
        const p = kStadt[(zufall() * kStadt.length) | 0];
        const zuEigenen = staedte.reduce((m, s) => Math.min(m, Math.hypot(s[0] - p[0], s[1] - p[1]) * ZELLE), Infinity);
        if (zuEigenen < 1300) continue;
        const w = Math.min(zuEigenen, 2600) + Math.min(abstand(p[0], p[1]), 2000) * 0.4 - steig(p[0], p[1]) * 3000;
        if (w > bw) { bw = w; best = p; }
      }
      if (!best) break;
      staedte.push(best); neu.push({ typ: "stadt", x: best[0], y: best[1], name: `${name} – Stadt ${k + 1}` });
    }
    // Dörfer: verteilt, mind. 450 m zu allem, höchstens 1,8 km von einer Stadt der Region
    const kDorf = kandidaten(r, 100, 0.09, 100);
    for (let k = 0; k < doerferProRegion; k++) {
      let best = null, bw = -Infinity;
      for (const [x, y] of kDorf) {
        const d = abstand(x, y); if (d < 450) continue;
        const zurStadt = staedte.reduce((m, s) => Math.min(m, Math.hypot(s[0] - x, s[1] - y) * ZELLE), Infinity);
        if (staedte.length && zurStadt > 1800) continue;
        const w = Math.min(d, 1200) - steig(x, y) * 2500 + zufall() * 60;
        if (w > bw) { bw = w; best = [x, y]; }
      }
      if (best) neu.push({ typ: "dorf", x: best[0], y: best[1], name: `${name} – Dorf ${k + 1}` });
    }
  }
  // Startdorf
  { let best = null, bw = -Infinity; for (const [x, y] of kandidaten(1, 200, 0.08, 120)) { const w = Math.min(abstand(x, y), 1500) - steig(x, y) * 2000; if (w > bw) { bw = w; best = [x, y]; } }
    if (best) neu.push({ typ: "dorf", x: best[0], y: best[1], name: "Startdorf" }); }
  // Zentralberg: Gipfel und Dungeon-Eingang am Hang Richtung Startgebiet (Süden)
  neu.push({ typ: "poi", x: gx, y: gy, name: "Gipfel – spätere Dämonenfestung" });
  { let best = null, bw = -Infinity; const r = Math.round(1600 / ZELLE);
    for (let y = gy; y < Math.min(N - 4, gy + r); y += 2) for (let x = Math.max(4, gx - r / 2); x < Math.min(N - 4, gx + r / 2); x += 2) {
      const h = H[y * N + x]; if (h < 120 || h > 200) continue; const st = steig(x, y); if (st > 0.35) continue;
      const w = -Math.abs(Math.atan2(x - gx, y - gy)) * 400 - st * 200; if (w > bw) { bw = w; best = [x, y]; } }
    if (best) neu.push({ typ: "dungeon", x: best[0], y: best[1], name: "Abstieg in die Tiefe" }); }
  // Nebeninseln: je ein Dungeon am höchsten Punkt
  { const L = landmassen(); let nr = 0;
    L.groesse.forEach((g, id) => { if (id === L.haupt || g * ZELLE * ZELLE < 30000) return;
      let m = -1e9, bx = 0, by = 0; for (let i = 0; i < N * N; i++) if (L.comp[i] === id && H[i] > m) { m = H[i]; bx = i % N; by = (i / N) | 0; }
      nr++; neu.push({ typ: "dungeon", x: bx, y: by, name: nr === 1 ? "Inseldungeon" : `Inseldungeon ${nr}` }); }); }
  undoPunkt();
  markerZustand.liste = markerZustand.liste.filter((m) => m.typ === "feld" || m.typ === "mine")
    .concat(neu.map((o) => { const m = markerNeu(o.typ, o.x, o.y); m.name = o.name; return m; }));
  markerZustand.auswahl = -1;
  markerGeaendert();
  const staedte = neu.filter((o) => o.typ === "stadt").length, doerfer = neu.filter((o) => o.typ === "dorf").length;
  status(`${staedte} Städte und ${doerfer} Dörfer vorgeschlagen (${fraktionsIds.length} Regionen)`);
}

// ---------- Anzeige ----------
function regionenBildBauen() {
  const REG = regionenZustand.REG; if (!REG) return;
  const c = document.createElement("canvas"); c.width = N; c.height = N;
  const g = c.getContext("2d"), img = g.createImageData(N, N), d = img.data;
  const sichtbar = (r) => r !== 0 && r !== REGION_INSEL;
  for (let y = 2; y < N - 2; y++) for (let x = 2; x < N - 2; x++) {
    const i = y * N + x, r = REG[i]; if (!sichtbar(r)) continue;
    for (const j of [i + 1, i - 1, i + N, i - N, i + 2, i - 2, i + 2 * N, i - 2 * N]) {
      const t = REG[j]; if (t !== r && sichtbar(t)) { d[i * 4] = 255; d[i * 4 + 1] = 110; d[i * 4 + 2] = 20; d[i * 4 + 3] = 255; break; }
    }
  }
  g.putImageData(img, 0, 0);
  const mitte = {};
  for (let y = 0; y < N; y += 6) for (let x = 0; x < N; x += 6) { const r = REG[y * N + x]; if (!regionenZustand.namen[r] || r === REGION_INSEL) continue;
    (mitte[r] ||= [0, 0, 0]); mitte[r][0] += x; mitte[r][1] += y; mitte[r][2]++; }
  regionenZustand.bild = c; regionenZustand.mitte = mitte;
}

function regionenZeichnen(ctx, ox, oy, z) {
  if (!regionenZustand.zeigen || !regionenZustand.bild) return;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(regionenZustand.bild, ox, oy, N * z, N * z);
  ctx.font = "bold 15px system-ui"; ctx.textAlign = "center";
  for (const r in regionenZustand.mitte) {
    const m = regionenZustand.mitte[r], px = ox + m[0] / m[2] * z, py = oy + m[1] / m[2] * z + 26;
    ctx.lineWidth = 4; ctx.strokeStyle = "rgba(0,0,0,.85)"; ctx.strokeText(regionenZustand.namen[r], px, py);
    ctx.fillStyle = "#ffd27a"; ctx.fillText(regionenZustand.namen[r], px, py);
  }
  ctx.textAlign = "left";
}

function regionenInfo() {
  const el = $("regionen-info"); if (!el) return;
  const REG = regionenZustand.REG;
  if (!REG) { el.textContent = "Noch keine Regionen berechnet."; return; }
  const flaeche = {}; for (let i = 0; i < N * N; i++) if (REG[i]) flaeche[REG[i]] = (flaeche[REG[i]] || 0) + 1;
  el.innerHTML = Object.keys(regionenZustand.namen).filter((r) => flaeche[r])
    .map((r) => `${regionenZustand.namen[r]}: ${(flaeche[r] * ZELLE * ZELLE / 1e6).toFixed(1)} km²`).join("<br>");
}

// ---------- Speichern / Export ----------
function regionenExportMeta() {
  if (!regionenZustand.REG) return null;
  return { datei: `regionen_${N}.u8`, format: `uint8 je Zelle (${ZELLE} m), ${N} x ${N}, Zeile für Zeile; 0 Meer, ${REGION_BERG} Zentralberg, ${REGION_INSEL} Nebeninsel`,
    namen: regionenZustand.namen, gipfel_m: regionenZustand.gipfel && regionenZustand.gipfel.map((v) => v * ZELLE - WELT / 2) };
}

function regionenLaden(daten, meta) {
  if (!daten || daten.length !== N * N) { regionenZuruecksetzen(); return; }
  regionenZustand.REG = daten.slice(); regionenZustand.namen = (meta && meta.namen) || {};
  regionenZustand.gipfel = meta && meta.gipfel ? meta.gipfel : null;
  regionenBildBauen(); regionenInfo();
}

function regionenAufbauen() {
  for (const id of ["p-berghoehe-zentrum", "p-fraktionen", "p-startanteil", "p-berglinie", "p-staedte", "p-doerfer"]) {
    const inp = $(id), out = inp.parentElement.querySelector("output");
    inp.addEventListener("input", () => (out.textContent = inp.value)); out.textContent = inp.value;
  }
  const ausfuehren = (f) => async () => { beschaeftigt(true); await new Promise((r) => setTimeout(r, 30)); try { await f(); } finally { beschaeftigt(false); } };
  $("nebeninsel").onclick = ausfuehren(nebeninselFormen);
  $("zentralberg").onclick = ausfuehren(zentralbergFormen);
  $("regionen-berechnen").onclick = ausfuehren(regionenBerechnen);
  $("siedlungen-vorschlagen").onclick = ausfuehren(siedlungenVorschlagen);
  $("regionen-zeigen").onchange = (e) => { regionenZustand.zeigen = e.target.checked; ansicht.zeichne(); };
  regionenInfo();
}
