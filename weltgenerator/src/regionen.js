// ===== Regionen: Nebeninsel, Zentralberg, Seen, Fraktionsregionen, Siedlungsvorschläge, Varianten =====
// Wird nach marker.js und vor app.js geladen; nutzt deren Globals erst zur Laufzeit (zustand, N, ZELLE, WELT_API …).
//
// Regionen-IDs: 0 Meer · 1 Startgebiet · 2 … (1 + Fraktionen) Fraktionsregionen · 250 Zentralberg · 251 Nebeninseln
// Die Grenzen entstehen durch Ausbreitung von Startpunkten aus (Dijkstra auf grobem Raster): Flüsse, Seen und steile
// Hänge sind teuer, deshalb treffen sich die Regionen bevorzugt dort. Die Flächen werden über Startvorsprünge angeglichen.
// Alle Entfernungen sind für eine 8-km-Welt gewählt und wachsen mit der Weltgröße mit (massstab()).

const REGION_BERG = 250, REGION_INSEL = 251;
const RICHTUNGEN = ["Ost", "Südost", "Süd", "Südwest", "West", "Nordwest", "Nord", "Nordost"];
const regionenZustand = { REG: null, namen: {}, gipfel: null, insel: null, zeigen: true, bild: null, mitte: null,
  SEE: null, seen: [] };   // SEE: je Zelle 0 oder Seenummer + 1 · seen: {x, y (Zellen), spiegel (m), flaeche (m²), tiefe (m)}
const massstab = () => WELT / 8192;
const saatZufall = (saat) => mulberry32((saat * 2654435761) >>> 0);

function regionenZuruecksetzen() {
  regionenZustand.REG = null; regionenZustand.namen = {}; regionenZustand.gipfel = null; regionenZustand.bild = null; regionenZustand.mitte = null;
  seenZuruecksetzen();
  regionenInfo();
}
function seenZuruecksetzen() { regionenZustand.SEE = null; regionenZustand.seen = []; }

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
const istWasser = (i) => zustand.H[i] <= 1.5 || (regionenZustand.SEE && regionenZustand.SEE[i] > 0);

// ---------- Nebeninsel ----------
// Sucht eine Stelle draußen auf dem offenen Meer (650–1000 m vor der Küste, bei 16 km doppelt so weit) in einer
// zufälligen Himmelsrichtung und formt dort eine Insel. Liefert false, wenn kein Platz gefunden wurde.
async function nebeninselFormen(saat) {
  const H = zustand.H, L = landmassen(), s = massstab();
  const rnd = saatZufall(typeof saat === "number" ? saat : Math.floor(Math.random() * 1e6));
  const zumLand = abstandsfeld((i) => H[i] > 1.5);
  const [mx, my] = L.schwer[L.haupt], rand = Math.round(500 * s / ZELLE), richtung = rnd() * Math.PI * 2;
  let wahl = null;
  for (const [dmin, dmax] of [[650, 1000], [500, 1000], [400, 1100]]) {
    for (let y = rand; y < N - rand; y += 4) for (let x = rand; x < N - rand; x += 4) {
      const i = y * N + x, d = zumLand[i] * ZELLE;
      if (d < dmin * s || d > dmax * s || H[i] > -15) continue;
      const w = Math.cos(Math.atan2(y - my, x - mx) - richtung);
      if (!wahl || w > wahl.w) wahl = { x, y, w };
    }
    if (wahl) break;
  }
  if (!wahl) { status("Kein Platz für eine Nebeninsel gefunden (Insel zu groß?)"); return false; }
  const { x: ix, y: iy } = wahl, k = s * (0.9 + 0.5 * rnd()), m = (meter) => meter * k / ZELLE;
  const dreh = rnd() * Math.PI * 2;
  const kreis = (r, n, dx = 0, dy = 0) => Array.from({ length: n }, (_, j) => { const a = j / n * 6.283;
    const px = Math.cos(a) * r + dx, py = Math.sin(a) * r * 0.75 + dy;
    return [ix + px * Math.cos(dreh) - py * Math.sin(dreh), iy + px * Math.sin(dreh) + py * Math.cos(dreh)]; });
  const alt = [zustand.groesse, zustand.staerke];
  zustand.groesse = 240 * k; zustand.staerke = 1;
  WELT_API.strichTest("land", [[ix, iy], ...kreis(m(88), 12), ...kreis(m(160), 16), ...kreis(m(80), 8, m(140), -m(40))], 1.0);
  zustand.groesse = 360 * k; zustand.staerke = 0.6;
  WELT_API.strichTest("huegel", [[ix, iy], ...kreis(m(72), 8)], 1.0);
  zustand.groesse = 180 * k; zustand.staerke = 0.8;
  WELT_API.strichTest("gebirge", [[ix - m(24), iy - m(16)], [ix + m(16), iy + m(8)]], 1.0);
  [zustand.groesse, zustand.staerke] = alt;
  await erosionAnwenden(typeof saat === "number" ? saat : undefined);
  regionenZustand.insel = [ix, iy];
  status(`Nebeninsel geformt (${Math.round(ix * ZELLE - WELT / 2)} / ${Math.round(iy * ZELLE - WELT / 2)} m)`);
  return true;
}

// ---------- Zentralberg ----------
// Hebt die Inselmitte großflächig an, setzt sternförmige Grate und wendet Erosion an.
async function zentralbergFormen(saat) {
  const H = zustand.H, L = landmassen(), s = massstab(), ziel = parseFloat($("p-berghoehe-zentrum").value);
  const cx = Math.round(L.schwer[L.haupt][0]), cy = Math.round(L.schwer[L.haupt][1]);
  const gipfelSuchen = (r) => { let m = -1e9, gx = cx, gy = cy;
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (H[y * N + x] > m) { m = H[y * N + x]; gx = x; gy = y; }
    return [m, gx, gy]; };
  const vorher = gipfelSuchen(Math.round(600 * s / ZELLE))[0];
  // Je Pinselpunkt hebt "anheben" (Stärke 1) die Mitte um 25 m; Grate und Erosion bringen etwa 100 m dazu
  const schritte = Math.max(2, Math.round((ziel - vorher - 100) / 25));
  const sockel = Math.ceil(schritte * 0.55), kern = schritte - sockel;
  const alt = [zustand.groesse, zustand.staerke];
  zustand.groesse = 1600 * s; zustand.staerke = 1;
  WELT_API.strichTest("anheben", Array.from({ length: sockel }, () => [cx, cy]), 1.0);
  zustand.groesse = 900 * s;
  WELT_API.strichTest("anheben", Array.from({ length: kern }, () => [cx, cy]), 1.0);
  zustand.groesse = 420 * s; zustand.staerke = 0.6;
  const grate = [], r = 600 * s / ZELLE, versatz = typeof saat === "number" ? saatZufall(saat)() * 6.283 : 0.4;
  for (let k = 0; k < 5; k++) { const a = k / 5 * 6.283 + versatz; for (let t = 0; t <= 1; t += 0.1) grate.push([cx + Math.cos(a) * t * r, cy + Math.sin(a) * t * r]); }
  WELT_API.strichTest("gebirge", grate, 0.5);
  [zustand.groesse, zustand.staerke] = alt;
  await erosionAnwenden(typeof saat === "number" ? saat : undefined);
  const [hoehe, gx, gy] = gipfelSuchen(Math.round(800 * s / ZELLE));
  regionenZustand.gipfel = [gx, gy];
  status(`Zentralberg geformt: Gipfel ${Math.round(hoehe)} m`);
}

// ---------- Seen ----------
// Sucht eine ebene Stelle im Landesinneren (fern von Küste, Zentralberg und anderen Seen), ebnet sie, senkt eine
// unregelmäßige Mulde ab und füllt sie von der tiefsten Stelle aus bis zum Überlauf (Priority-Flood) mit Wasser.
async function seeFormen(saat) {
  const s = massstab(), rnd = saatZufall(typeof saat === "number" ? saat : Math.floor(Math.random() * 1e6));
  const L = landmassen(), kueste = abstandsfeld(istWasser);
  const [gx, gy] = regionenZustand.gipfel || L.schwer[L.haupt];
  const H0 = zustand.H;
  const steig = (x, y) => Math.max(Math.abs(H0[y * N + x - 3] - H0[y * N + x + 3]), Math.abs(H0[(y - 3) * N + x] - H0[(y + 3) * N + x])) / (6 * ZELLE);
  const kandidaten = [];
  for (const [minK, maxSt] of [[900, 0.05], [650, 0.08], [450, 0.12]]) {
    for (let y = 8; y < N - 8; y += 6) for (let x = 8; x < N - 8; x += 6) {
      const i = y * N + x, h = H0[i];
      if (L.comp[i] !== L.haupt || h < 28 || h > 170 || kueste[i] * ZELLE < minK * s || steig(x, y) > maxSt) continue;
      if (Math.hypot(x - gx, y - gy) * ZELLE < 2400 * s) continue;
      if (regionenZustand.seen.some((o) => Math.hypot(o.x - x, o.y - y) * ZELLE < 2500 * s)) continue;
      kandidaten.push([x, y]);
    }
    if (kandidaten.length > 20) break;
  }
  for (let versuch = 0; versuch < 12 && kandidaten.length; versuch++) {
    const [cx, cy] = kandidaten.splice((rnd() * kandidaten.length) | 0, 1)[0];
    const R = (230 + 170 * rnd()) * s, Rz = R / ZELLE;
    const sicherung = zustand.H.slice();
    const alt = [zustand.groesse, zustand.staerke];
    // 1) Umgebung ebnen, 2) Mulde aus mehreren Keulen absenken, 3) Ufer glätten
    zustand.groesse = R * 2.6; zustand.staerke = 1;
    WELT_API.strichTest("ebnen", [[cx, cy], [cx + Rz * 0.3, cy], [cx - Rz * 0.3, cy], [cx, cy + Rz * 0.3], [cx, cy - Rz * 0.3]], 1.0);
    const keulen = [[cx, cy]];
    for (let k = 0, n = 3 + ((rnd() * 3) | 0); k < n; k++) { const a = rnd() * 6.283, d = Rz * (0.35 + 0.35 * rnd()); keulen.push([cx + Math.cos(a) * d, cy + Math.sin(a) * d]); }
    // Mulde ca. 26 m tief, in niedrigem Gelände flacher: der Seegrund bleibt über dem Meeresspiegel (sonst zählt er als Meer)
    zustand.groesse = R * 1.5;
    WELT_API.strichTest("absenken", keulen.concat([[cx, cy]]), 0.32 * Math.min(1, Math.max(0.4, (zustand.H[cy * N + cx] - 8) / 26)));
    zustand.groesse = R * 2.4; zustand.staerke = 0.5;
    WELT_API.strichTest("glaetten", [[cx, cy], ...keulen], 0.4);
    [zustand.groesse, zustand.staerke] = alt;
    const see = seeFuellen(cx, cy, Math.round(Math.PI * (R * 2.2 / ZELLE) ** 2));
    if (see && see.tiefe >= 3 && see.flaeche >= 0.25 * Math.PI * R * R) {
      seeEintragen(see);
      zeichneAlles();
      status(`See geformt: ${(see.flaeche / 1e6).toFixed(2)} km², Wasserspiegel ${see.spiegel.toFixed(1)} m, bis ${see.tiefe.toFixed(1)} m tief`);
      return true;
    }
    zustand.H = sicherung; nachAenderung(true);   // Mulde hält kein Wasser -> nächste Stelle
  }
  status("Kein Platz für einen See gefunden");
  return false;
}

// Füllt ab der tiefsten Stelle nahe (cx, cy) bis zum Überlauf. Liefert {x, y, spiegel, zellen, flaeche, tiefe} oder null.
function seeFuellen(cx, cy, maxZellen) {
  const H = zustand.H;
  let start = Math.round(cy) * N + Math.round(cx);
  for (let y = Math.round(cy) - 20; y <= Math.round(cy) + 20; y++) for (let x = Math.round(cx) - 20; x <= Math.round(cx) + 20; x++) if (H[y * N + x] < H[start]) start = y * N + x;
  const besucht = new Uint8Array(N * N), heap = [start], innen = [];
  const hoch = (k) => { while (k > 0) { const p = (k - 1) >> 1; if (H[heap[p]] <= H[heap[k]]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
  const runter = () => { let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && H[heap[l]] < H[heap[m]]) m = l; if (r < heap.length && H[heap[r]] < H[heap[m]]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } };
  besucht[start] = 1;
  let spiegel = H[start];
  while (heap.length) {
    const c = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; runter(); }
    if (H[c] < spiegel - 0.01 || H[c] <= 1.5) break;     // Überlauf: von hier fließt das Wasser ab
    if (innen.length >= maxZellen) { spiegel = H[c]; break; } // zu groß: Spiegel bleibt unter dieser Höhe
    spiegel = Math.max(spiegel, H[c]); innen.push(c);
    const x = c % N;
    for (const j of [c - 1, c + 1, c - N, c + N]) if (j >= 0 && j < N * N && !besucht[j] && Math.abs((j % N) - x) <= 1) { besucht[j] = 1; heap.push(j); hoch(heap.length - 1); }
  }
  spiegel -= 0.3;   // etwas Ufer über dem Wasser
  const zellen = innen.filter((i) => H[i] < spiegel);
  if (!zellen.length) return null;
  let sx = 0, sy = 0; for (const i of zellen) { sx += i % N; sy += (i / N) | 0; }
  return { x: Math.round(sx / zellen.length), y: Math.round(sy / zellen.length), spiegel, zellen,
    flaeche: zellen.length * ZELLE * ZELLE, tiefe: spiegel - H[start] };
}

function seeEintragen(see) {
  if (!regionenZustand.SEE) regionenZustand.SEE = new Uint8Array(N * N);
  regionenZustand.seen.push({ x: see.x, y: see.y, spiegel: +see.spiegel.toFixed(2), flaeche: Math.round(see.flaeche), tiefe: +see.tiefe.toFixed(1) });
  const nr = regionenZustand.seen.length;
  for (const i of see.zellen) regionenZustand.SEE[i] = nr;
}

function seenExportMeta() {
  if (!regionenZustand.SEE) return null;
  return { datei: `seen_${N}.u8`, format: `uint8 je Zelle (${ZELLE} m), ${N} x ${N}; 0 = kein See, sonst Seenummer (1 …)`,
    liste: regionenZustand.seen.map((o, k) => ({ nr: k + 1, x: Math.round(o.x * ZELLE - WELT / 2), z: Math.round(o.y * ZELLE - WELT / 2),
      wasserspiegel: o.spiegel, flaeche_m2: o.flaeche, tiefe_m: o.tiefe })) };
}

function seenLaden(daten, liste) {
  seenZuruecksetzen();
  if (!daten || daten.length !== N * N || !liste) return;
  regionenZustand.SEE = daten.slice(); regionenZustand.seen = liste;
}

// ---------- Regionen ----------
function regionenBerechnen() {
  const H = zustand.H, AF = zustand.A, SEE = regionenZustand.SEE, L = landmassen(), comp = L.comp, haupt = L.haupt, s = massstab();
  const fraktionen = parseInt($("p-fraktionen").value, 10), startAnteil = parseFloat($("p-startanteil").value) / 100;
  const bergLinie = parseFloat($("p-berglinie").value), bergRadius = 1500 * s;
  // Gipfel: gespeichert oder höchster Punkt im Umkreis von 1,5 km (× Maßstab) um die Inselmitte
  let [gx, gy] = regionenZustand.gipfel || [Math.round(L.schwer[haupt][0]), Math.round(L.schwer[haupt][1])];
  if (!regionenZustand.gipfel) { let m = -1e9; const r = Math.round(bergRadius / ZELLE), cx = gx, cy = gy;
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (comp[y * N + x] === haupt && H[y * N + x] > m) { m = H[y * N + x]; gx = x; gy = y; } }
  const REG = new Uint8Array(N * N);
  for (let i = 0; i < N * N; i++) if (H[i] > 1.5 && comp[i] !== haupt) REG[i] = REGION_INSEL;
  // Zentralberg: zusammenhängend über der Höhenlinie, höchstens bergRadius vom Gipfel
  if (H[gy * N + gx] > bergLinie) {
    const st = [gy * N + gx]; REG[gy * N + gx] = REGION_BERG;
    while (st.length) { const i = st.pop();
      for (const j of [i - 1, i + 1, i - N, i + N]) { const jx = j % N, jy = (j / N) | 0;
        if (REG[j] === 0 && comp[j] === haupt && H[j] > bergLinie && Math.hypot(jx - gx, jy - gy) * ZELLE < bergRadius) { REG[j] = REGION_BERG; st.push(j); } } }
  }
  // Grobraster (2 Zellen) mit Kosten: Flüsse, Seen und Steigung bremsen
  const G = N / 2, kosten = new Float64Array(G * G).fill(-1), land = [];
  for (let y = 1; y < G - 1; y++) for (let x = 1; x < G - 1; x++) {
    const i = (y * 2) * N + x * 2; if (comp[i] !== haupt || REG[i] === REGION_BERG) continue;
    const st = Math.max(Math.abs(H[i + 2] - H[i - 2]), Math.abs(H[i + 2 * N] - H[i - 2 * N])) / (4 * ZELLE);
    const fluss = Math.max(AF[i], AF[i + 1], AF[i + N], AF[i + N + 1]) > FLUSS_SCHWELLE ? 6 : 0;
    const see = SEE && SEE[i] ? 12 : 0;
    kosten[y * G + x] = 1 + fluss + see + Math.min(st, 1) * 8; land.push([x, y]);
  }
  // Startpunkte: Süden (Startgebiet) + Fraktionen ringförmig um den Gipfel
  const sued = land.slice().sort((a, b) => b[1] - a[1]).slice(0, Math.max(1, Math.floor(land.length * 0.05)));
  const ziele = [[sued.reduce((t, p) => t + p[0], 0) / sued.length, sued.reduce((t, p) => t + p[1], 0) / sued.length]];
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
  const vorsprung = Array(anzahl).fill(0); let beste = Infinity, besterVorsprung = vorsprung.slice(), schritt = 60 * s;
  for (let it = 0; it < 30; it++) {
    const fl = lauf(vorsprung), summe = fl.reduce((a, b) => a + b, 0);
    const abw = fl.reduce((m, f, r) => Math.max(m, Math.abs(f / summe - zielAnteil[r])), 0);
    if (abw < beste) { beste = abw; besterVorsprung = vorsprung.slice(); }
    for (let r = 0; r < anzahl; r++) vorsprung[r] += schritt * Math.max(-1, Math.min(1, (fl[r] / summe - zielAnteil[r]) / zielAnteil[r]));
    schritt *= 0.92;
  }
  lauf(besterVorsprung);
  // Nicht erreichte Flecken (z. B. hinter dem Zentralberg eingeschlossen) bekommen die nächstgelegene Region
  { const q = new Int32Array(G * G); let qh = 0, qt = 0;
    for (let i = 0; i < G * G; i++) if (lab[i] >= 0) q[qt++] = i;
    while (qh < qt) { const i = q[qh++], x = i % G;
      for (const j of [i - 1, i + 1, i - G, i + G]) if (j >= 0 && j < G * G && lab[j] < 0 && Math.abs((j % G) - x) <= 1) { lab[j] = lab[i]; q[qt++] = j; } } }
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
  return beste;
}

// ---------- Siedlungen ----------
// Ersetzt Städte, Dörfer, Dungeons und POIs durch einen Vorschlag: je Fraktionsregion N Städte, je Stadt M Dörfer in
// ihrer Nähe, ein Startdorf, Gipfel und Dungeon-Eingang am Zentralberg, ein Dungeon je Nebeninsel. Felder und Minen bleiben.
function siedlungenVorschlagen() {
  if (!regionenZustand.REG) regionenBerechnen();
  const H = zustand.H, REG = regionenZustand.REG, SEE = regionenZustand.SEE, [gx, gy] = regionenZustand.gipfel, s = massstab();
  const staedteProRegion = parseInt($("p-staedte").value, 10), doerferProStadt = parseInt($("p-doerfer").value, 10);
  let saatWert = params().seed * 7 + 13; const zufall = () => { saatWert = (saatWert * 16807) % 2147483647; return saatWert / 2147483647; };
  const kueste = abstandsfeld(istWasser);
  const steig = (x, y) => Math.max(Math.abs(H[y * N + x - 3] - H[y * N + x + 3]), Math.abs(H[(y - 3) * N + x] - H[(y + 3) * N + x])) / (6 * ZELLE);
  const innen = (x, y, reg, r) => { for (let k = 0; k < 8; k++) { const a = k / 8 * 6.283; if (REG[Math.round(y + Math.sin(a) * r) * N + Math.round(x + Math.cos(a) * r)] !== reg) return false; } return true; };
  const geeignet = (x, y, reg, minKueste, maxSt, rand) => { const i = y * N + x;
    return REG[i] === reg && !(SEE && SEE[i]) && H[i] >= 4 && H[i] <= 160 && kueste[i] * ZELLE >= minKueste && steig(x, y) <= maxSt && innen(x, y, reg, rand); };
  const kandidaten = (reg, minK, maxSt, rand) => { const k = []; const rz = Math.round(rand / ZELLE);
    for (let y = 40; y < N - 40; y += 4) for (let x = 40; x < N - 40; x += 4) if (geeignet(x, y, reg, minK, maxSt, rz)) k.push([x, y]); return k; };
  const neu = [];
  const abstand = (x, y) => neu.reduce((m, o) => Math.min(m, Math.hypot(o.x - x, o.y - y) * ZELLE), Infinity);
  const fraktionsIds = Object.keys(regionenZustand.namen).map(Number).filter((r) => r >= 2 && r < REGION_BERG).sort((a, b) => a - b);
  for (const r of fraktionsIds) {
    const name = regionenZustand.namen[r];
    // Städte: möglichst weit auseinander, eben, nicht am Rand der Region. Wenn die Region zu eng ist, sinkt der Mindestabstand.
    const kStadt = kandidaten(r, 180, 0.07, 180 * s);
    const staedte = [];
    for (let k = 0; k < staedteProRegion && kStadt.length; k++) {
      let best = null;
      for (const minAbstand of [1500 * s, 1200 * s, 900 * s, 700]) {
        let bw = -Infinity;
        for (let t = 0; t < 3000; t++) {
          const p = kStadt[(zufall() * kStadt.length) | 0];
          const zuEigenen = staedte.reduce((m, q) => Math.min(m, Math.hypot(q[0] - p[0], q[1] - p[1]) * ZELLE), Infinity);
          if (zuEigenen < minAbstand) continue;
          const w = Math.min(zuEigenen, 2600 * s) + Math.min(abstand(p[0], p[1]), 2000 * s) * 0.4 - steig(p[0], p[1]) * 3000;
          if (w > bw) { bw = w; best = p; }
        }
        if (best) break;
      }
      if (!best) break;
      staedte.push(best); neu.push({ typ: "stadt", x: best[0], y: best[1], name: `${name} – Stadt ${k + 1}` });
    }
    // Dörfer: je Stadt M Stück, 600 m … 1,6 km (× Maßstab) von ihrer Stadt, näher an ihr als an jeder anderen Stadt
    const kDorf = kandidaten(r, 100, 0.09, 100);
    staedte.forEach((st, si) => {
      for (let k = 0; k < doerferProStadt; k++) {
        let best = null;
        for (const maxStadt of [1600 * s, 2400 * s, 3200 * s]) {
          let bw = -Infinity;
          for (const [x, y] of kDorf) {
            const d = abstand(x, y); if (d < 450) continue;
            const zurStadt = Math.hypot(st[0] - x, st[1] - y) * ZELLE;
            if (zurStadt < 600 || zurStadt > maxStadt) continue;
            if (staedte.some((o, oi) => oi !== si && Math.hypot(o[0] - x, o[1] - y) * ZELLE < zurStadt)) continue;
            const w = Math.min(d, 1200) - Math.abs(zurStadt - 1000 * s) * 0.3 - steig(x, y) * 2500 + zufall() * 60;
            if (w > bw) { bw = w; best = [x, y]; }
          }
          if (best) break;
        }
        if (best) neu.push({ typ: "dorf", x: best[0], y: best[1], name: `${name} – Dorf ${si + 1}${"abcd"[k]}` });
      }
    });
  }
  // Startdorf
  { let best = null, bw = -Infinity; for (const [x, y] of kandidaten(1, 200, 0.08, 120)) { const w = Math.min(abstand(x, y), 1500) - steig(x, y) * 2000; if (w > bw) { bw = w; best = [x, y]; } }
    if (best) neu.push({ typ: "dorf", x: best[0], y: best[1], name: "Startdorf" }); }
  // Zentralberg: Gipfel und Dungeon-Eingang am Hang Richtung Startgebiet (Süden), auf 20–38 % der Gipfelhöhe
  neu.push({ typ: "poi", x: gx, y: gy, name: "Gipfel – spätere Dämonenfestung" });
  { let best = null, bw = -Infinity; const r = Math.round(1600 * s / ZELLE), hg = H[gy * N + gx];
    const hMin = Math.min(120, hg * 0.2), hMax = Math.max(200, hg * 0.38);
    for (let y = gy; y < Math.min(N - 4, gy + r); y += 2) for (let x = Math.max(4, gx - r / 2); x < Math.min(N - 4, gx + r / 2); x += 2) {
      const h = H[y * N + x]; if (h < hMin || h > hMax) continue; const st = steig(x, y); if (st > 0.35) continue;
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
  return { staedte, doerfer };
}

// ---------- Landschaft überarbeiten (Hochebenen, Pässe, Seen, Flüsse; Rechnung in kern.js) ----------
async function landschaftUeberarbeitenStarten(o) {
  o = o || { hochebenen: $("lu-hochebenen").checked, grate: $("lu-grate").checked, seen: $("lu-seen").checked, fluesse: $("lu-fluesse").checked };
  // Siedlungen und Felder bleiben unverändert (Minen liegen bewusst am Hang)
  const schutz = markerZustand.liste.filter((m) => m.typ !== "mine")
    .map((m) => ({ x: m.x, y: m.y, r: m.typ === "feld" ? Math.max(m.breite, m.laenge) / 2 : (m.radius || 40) }));
  undoPunkt(); zustand.undo[zustand.undo.length - 1].wasser = wasserStand();
  const r = await auftrag({ auftrag: "ueberarbeiten", H: zustand.H.slice(), ...analyseArgs(), REG: regionenZustand.REG ? regionenZustand.REG.slice() : null,
    SEE: regionenZustand.SEE ? regionenZustand.SEE.slice() : new Uint8Array(N * N), seen: structuredClone(regionenZustand.seen),
    schutz, seed: params().seed, o });
  zustand.H = r.H; zustand.A = r.A; zustand.B = r.B; zustand.version++;
  regionenZustand.SEE = r.SEE; regionenZustand.seen = r.seen;
  if (r.liste) { flussZustand.liste = r.liste; zustand.FM = r.FM; }
  // alte Wege passen nicht mehr zum Gelände (sie würden beim Export Rinnen durch die neuen Bergrücken ziehen)
  wegeZustand.liste = null; wegeInfo();
  markerZustand.ressourcenAlt = !!markerZustand.ressourcen;
  regionenInfo(); zeichneAlles();
  const i = r.info, teile = [];
  if (i.paesse != null) teile.push(`${i.paesse} Pässe`);
  if (i.neueSeen != null) teile.push(`${i.neueSeen} neue Seen`);
  if (i.fluesse != null) teile.push(`${i.fluesse} Flüsse`);
  status(`Landschaft überarbeitet${teile.length ? ": " + teile.join(", ") : ""}`);
  return i;
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

function regionenZeichnen(ctx, ox, oy, z, schrift = 15) {
  if (!regionenZustand.zeigen || !regionenZustand.bild) return;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(regionenZustand.bild, ox, oy, N * z, N * z);
  ctx.font = `bold ${schrift}px system-ui`; ctx.textAlign = "center";
  for (const r in regionenZustand.mitte) {
    const m = regionenZustand.mitte[r], px = ox + m[0] / m[2] * z, py = oy + m[1] / m[2] * z + schrift * 1.7;
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
    .map((r) => `${regionenZustand.namen[r]}: ${(flaeche[r] * ZELLE * ZELLE / 1e6).toFixed(1)} km²`).join("<br>") +
    (regionenZustand.seen.length ? `<br>Seen: ${regionenZustand.seen.map((o) => (o.flaeche / 1e6).toFixed(2) + " km²").join(", ")}` : "");
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

// ---------- Varianten ----------
// Erzeugt komplette Karten hintereinander und hält sie im Speicher; die Galerie zeigt sie, ein Klick lädt eine davon.
const varianten = [];
let variantenLaufen = false;

async function variantenErzeugen(anzahl, startSaat) {
  if (variantenLaufen) return;
  variantenLaufen = true;
  anzahl = anzahl || parseInt($("p-varianten").value, 10);
  const rnd = mulberry32((startSaat || Date.now()) >>> 0);
  galerieZeigen(true);
  try {
    for (let k = 0; k < anzahl; k++) {
      const v = { seed: 1 + Math.floor(rnd() * 999998), inselgroesse: +(0.74 + 0.1 * rnd()).toFixed(2), kueste: +(0.45 + 0.4 * rnd()).toFixed(2),
        gebirge: +(0.3 + 0.35 * rnd()).toFixed(2), huegel: Math.round(22 + 18 * rnd()), berghoehe: Math.round(280 + 140 * rnd()),
        zentrum: Math.round((650 + 250 * rnd()) / 10) * 10, seen: rnd() < 0.4 ? 2 : 1 };
      $("varianten-info").textContent = `Erzeuge Karte ${k + 1} von ${anzahl} (Seed ${v.seed}) …`;
      const t0 = performance.now();
      const ergebnis = await karteErzeugen(v);
      varianten.push({ ...ergebnis, nr: varianten.length + 1, v, dauer: Math.round((performance.now() - t0) / 1000),
        bild: kartenbild(720), H: zustand.H.slice(), O: zustand.O.slice(), REG: regionenZustand.REG.slice(),
        SEE: regionenZustand.SEE ? regionenZustand.SEE.slice() : null, seen: structuredClone(regionenZustand.seen),
        FM: zustand.FM, fluesse: flussZustand.liste,
        namen: { ...regionenZustand.namen }, gipfel: regionenZustand.gipfel.slice(), welt: WELT,
        marker: structuredClone(markerZustand.liste) });
      galerieAktualisieren();
    }
    $("varianten-info").textContent = `${anzahl} Karten fertig. Klick auf ein Bild lädt die Karte in den Editor.`;
  } finally { variantenLaufen = false; }
}

async function karteErzeugen(v) {
  const setze = (id, wert) => { const e = $(id); e.value = wert; e.dispatchEvent(new Event("input")); };
  setze("p-seed", v.seed); setze("p-inselgroesse", v.inselgroesse); setze("p-kueste", v.kueste); setze("p-gebirge", v.gebirge);
  setze("p-huegel", v.huegel); setze("p-berghoehe", v.berghoehe); setze("p-berghoehe-zentrum", v.zentrum);
  markerZustand.liste = []; markerZustand.ressourcen = null; wegeZustand.liste = null;   // sonst fragt "Neu generieren" nach
  await generieren();
  regionenZuruecksetzen();
  await zentralbergFormen(v.seed + 1);
  const insel = await nebeninselFormen(v.seed + 2);
  let seen = 0;
  for (let j = 0; j < v.seen + 3 && seen < v.seen; j++) if (await seeFormen(v.seed + 3 + j)) seen++;   // bis zu 3 Ersatzversuche
  // Flüsse und Biome sofort auf den letzten Stand bringen (sonst erst verzögert nach dem Malen)
  const r = await auftrag({ auftrag: "analyse", H: zustand.H.slice(), ...analyseArgs(), version: zustand.version });
  zustand.A = r.A; zustand.B = r.B; zeichneAlles();
  zustand.undo = []; zustand.redo = [];   // Rückgängig-Stapel würde bei 10 Karten sehr viel Speicher belegen
  const abw = regionenBerechnen();
  const { staedte, doerfer } = siedlungenVorschlagen();
  await landschaftUeberarbeitenStarten({ hochebenen: true, grate: true, seen: true, fluesse: true });
  zustand.undo = [];
  let landZellen = 0; for (let i = 0; i < N * N; i++) if (zustand.H[i] > 0) landZellen++;
  return { insel, seenAnzahl: seen, staedte, doerfer, abw, gipfelHoehe: Math.round(zustand.H[regionenZustand.gipfel[1] * N + regionenZustand.gipfel[0]]),
    landKm2: Math.round(landZellen * ZELLE * ZELLE / 1e6) };
}

// Übersichtsbild der aktuellen Karte: Gelände, Seen, Regionsgrenzen, Siedlungen (Dörfer mit Linie zu ihrer Stadt)
function kartenbild(groesse) {
  const c = document.createElement("canvas"); c.width = c.height = groesse;
  const g = c.getContext("2d"), z = groesse / N;
  g.fillStyle = "#1b2a3f"; g.fillRect(0, 0, groesse, groesse);
  g.imageSmoothingEnabled = true; g.drawImage(basis, 0, 0, groesse, groesse);
  const zeigen = regionenZustand.zeigen; regionenZustand.zeigen = true;
  regionenZeichnen(g, 0, 0, z, 12); regionenZustand.zeigen = zeigen;
  const liste = markerZustand.liste, staedte = liste.filter((m) => m.typ === "stadt");
  g.strokeStyle = "rgba(255,240,200,.75)"; g.lineWidth = 1.2;
  for (const m of liste) if (m.typ === "dorf" && m.name !== "Startdorf") {
    const st = staedte.find((q) => q.name === m.name.replace(/ – Dorf (\d+)[a-d]$/, " – Stadt $1"));
    if (st) { g.beginPath(); g.moveTo(m.x * z, m.y * z); g.lineTo(st.x * z, st.y * z); g.stroke(); }
  }
  const stil = { stadt: ["#e8b04a", 5.5], dorf: ["#f3e6b0", 3.2], dungeon: ["#e0504d", 4.5], poi: ["#6fb7e8", 4.5], mine: ["#9aa4b1", 2.5] };
  for (const m of liste) { const st = stil[m.typ]; if (!st) continue;
    g.fillStyle = st[0]; g.strokeStyle = "#111"; g.lineWidth = 1.2;
    g.beginPath(); g.arc(m.x * z, m.y * z, st[1], 0, Math.PI * 2); g.fill(); g.stroke(); }
  return c.toDataURL("image/jpeg", 0.88);
}

function galerieZeigen(an) {
  const el = $("galerie"); el.hidden = an === undefined ? !el.hidden : !an;
  if (!el.hidden) galerieAktualisieren();
}

function galerieAktualisieren() {
  const el = $("galerie");
  el.innerHTML = varianten.length ? "" : `<div class="hinweis">Noch keine Varianten – „Varianten erzeugen“ startet.</div>`;
  for (const v of varianten) {
    const f = document.createElement("figure"); f.classList.toggle("aktiv", v.nr === varianteAktiv);
    const pruef = [v.insel ? "" : "⚠ keine Nebeninsel", v.seenAnzahl ? "" : "⚠ kein See"].filter(Boolean).join(" · ");
    f.innerHTML = `<img src="${v.bild}" alt="Karte ${v.nr}"><figcaption><b>Karte ${v.nr}</b> · Seed ${v.v.seed} · ${(v.welt / 1000).toFixed(1)} km<br>` +
      `Land ${v.landKm2} km² · Zentralberg ${v.gipfelHoehe} m · ${v.seenAnzahl} ${v.seenAnzahl === 1 ? "See" : "Seen"} · ${v.staedte} Städte · ${v.doerfer} Dörfer` +
      `${pruef ? "<br>" + pruef : ""}</figcaption>`;
    f.onclick = () => { if (!variantenLaufen) varianteLaden(v.nr); };
    el.appendChild(f);
  }
}

let varianteAktiv = 0;
function varianteLaden(nr) {
  const v = varianten.find((q) => q.nr === nr); if (!v) return;
  if (v.welt !== WELT) weltgroesseSetzen(v.welt);
  const setze = (id, wert) => { const e = $(id); e.value = wert; e.dispatchEvent(new Event("input")); };
  setze("p-weltgroesse", v.welt / 1000);
  setze("p-seed", v.v.seed); setze("p-inselgroesse", v.v.inselgroesse); setze("p-kueste", v.v.kueste); setze("p-gebirge", v.v.gebirge);
  setze("p-huegel", v.v.huegel); setze("p-berghoehe", v.v.berghoehe); setze("p-berghoehe-zentrum", v.v.zentrum);
  undoPunkt();
  zustand.H = v.H.slice(); zustand.O = v.O.slice();
  regionenZustand.REG = v.REG.slice(); regionenZustand.namen = { ...v.namen }; regionenZustand.gipfel = v.gipfel.slice();
  regionenZustand.SEE = v.SEE ? v.SEE.slice() : null; regionenZustand.seen = structuredClone(v.seen);
  zustand.FM = v.FM ? v.FM.slice() : null; flussZustand.liste = v.fluesse ? structuredClone(v.fluesse) : null;
  regionenBildBauen(); regionenInfo();
  markerZustand.liste = structuredClone(v.marker); markerZustand.auswahl = -1; markerZustand.ressourcen = null; wegeZustand.liste = null;
  markerPanel(); ressourcenInfo(); wegeInfo();
  varianteAktiv = nr;
  galerieZeigen(false);
  nachAenderung(true);
  status(`Karte ${nr} geladen (Seed ${v.v.seed})`);
}

function regionenAufbauen() {
  for (const id of ["p-berghoehe-zentrum", "p-fraktionen", "p-startanteil", "p-berglinie", "p-staedte", "p-doerfer", "p-varianten"]) {
    const inp = $(id), out = inp.parentElement.querySelector("output");
    inp.addEventListener("input", () => (out.textContent = inp.value)); out.textContent = inp.value;
  }
  const ausfuehren = (f) => async () => { beschaeftigt(true); await new Promise((r) => setTimeout(r, 30)); try { await f(); } finally { beschaeftigt(false); } };
  $("nebeninsel").onclick = ausfuehren(() => nebeninselFormen());
  $("see").onclick = ausfuehren(() => seeFormen());
  $("zentralberg").onclick = ausfuehren(() => zentralbergFormen());
  $("regionen-berechnen").onclick = ausfuehren(regionenBerechnen);
  $("siedlungen-vorschlagen").onclick = ausfuehren(siedlungenVorschlagen);
  $("landschaft-ueberarbeiten").onclick = ausfuehren(() => landschaftUeberarbeitenStarten());
  $("varianten-erzeugen").onclick = ausfuehren(() => variantenErzeugen());
  $("galerie-zeigen").onclick = () => galerieZeigen();
  $("regionen-zeigen").onchange = (e) => { regionenZustand.zeigen = e.target.checked; ansicht.zeichne(); };
  regionenInfo();
}
