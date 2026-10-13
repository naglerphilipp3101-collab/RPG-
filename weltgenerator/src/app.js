// ===== Weltgenerator: Oberfläche =====
const ZELLE = 4;           // Meter pro Rasterzelle (fest)
let WELT = 4096;           // Weltgröße in Metern (Regler "Weltgröße": 2–8 km)
let N = WELT / ZELLE;      // Rasterzellen je Seite (512–2048)
const FLUSS_SCHWELLE = 1500;

const zustand = {
  H: new Float32Array(N * N),
  A: new Float32Array(N * N),
  B: new Uint8Array(N * N),                // automatische Biome
  O: new Uint8Array(N * N).fill(255),      // gemalte Biome (255 = automatisch)
  modus: "biome",                          // Kartenansicht: "biome" oder "hoehe"
  werkzeug: "anheben",
  groesse: 200, staerke: 0.5,
  hoehenlinien: true, fluesseZeigen: true,
  undo: [], redo: [],
  version: 0,
};
const $ = (id) => document.getElementById(id);

// ---------- Worker ----------
let worker = null, wartend = {};
try {
  const src = document.getElementById("kern-src").textContent;
  worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.typ === "fortschritt") status(`${m.text} … ${Math.round(m.f * 100)} %`, m.f);
    else if (m.typ === "fertig") { const r = wartend[m.auftrag]; delete wartend[m.auftrag]; if (r) r(m); }
  };
} catch (err) { console.warn("Worker nicht verfügbar, rechne im Hauptthread", err); worker = null; }

function auftrag(msg, transfer = []) {
  return new Promise((resolve) => {
    if (worker) { wartend[msg.auftrag] = resolve; worker.postMessage(msg, transfer); return; }
    // Rückfall ohne Worker
    setTimeout(() => {
      const st = (t) => (f) => status(`${t} … ${Math.round(f * 100)} %`, f);
      const ana = (H) => { const A = fluesse(H, msg.N); return { A, B: biomeBerechnen(H, A, msg.N, msg.zelle, msg.bp, msg.schwelle) }; };
      if (msg.auftrag === "generieren") {
        const H = generiere(msg.N, msg.p); erodiere(H, msg.N, Math.round(msg.p.erosion * 1000 * (msg.N / 1024) ** 2), msg.p.seed, st("Erosion"));
        thermisch(H, msg.N, 3, 3.2); resolve({ H, ...ana(H) });
      } else if (msg.auftrag === "erosion") {
        erodiere(msg.H, msg.N, msg.anzahl, msg.seed, st("Erosion")); thermisch(msg.H, msg.N, 2, 3.2); resolve({ H: msg.H, ...ana(msg.H) });
      } else if (msg.auftrag === "analyse") resolve({ ...ana(msg.H), version: msg.version });
      else if (msg.auftrag === "flussbetten") { flussbetten(msg.H, msg.N, fluesse(msg.H, msg.N), msg.schwelle); resolve({ H: msg.H, ...ana(msg.H) }); }
      else if (msg.auftrag === "hochskalieren") resolve({ out: hochskalieren(msg.H, msg.N, msg.M, msg.seed, msg.feindetail, st("Export"), msg.welt) });
      else if (msg.auftrag === "steuerkarte") resolve({ out: steuerkarte(msg.E, msg.N, msg.M, msg.seed, st("Export Biome")) });
    }, 20);
  });
}

function status(text, f) {
  $("status-text").textContent = text;
  $("status-balken").style.width = f == null ? "0%" : `${Math.round(f * 100)}%`;
}
function beschaeftigt(an) { document.body.classList.toggle("beschaeftigt", an); }

// ---------- Parameter ----------
const PARAMS = [
  ["seed", "Seed", 1, 999999, 1, 187],
  ["inselgroesse", "Inselgröße", 0.5, 0.95, 0.01, 0.82],
  ["kueste", "Küste zerklüftet", 0, 1, 0.01, 0.6],
  ["berghoehe", "Berghöhe (m)", 80, 500, 5, 300],
  ["gebirge", "Gebirgsanteil", 0, 1, 0.01, 0.5],
  ["huegel", "Hügel (m)", 0, 80, 1, 28],
  ["erosion", "Erosion (Tsd. Tropfen)", 0, 800, 10, 300],
  ["meerestiefe", "Meerestiefe (m)", 10, 100, 1, 40],
];
const BIOM_PARAMS = [
  ["schneegrenze", "Schneegrenze (m)", 120, 500, 5, 220],
  ["baumgrenze", "Baumgrenze (m)", 60, 450, 5, 185],
  ["nadelhoehe", "Nadelwald ab (m)", 0, 300, 5, 60],
  ["waldanteil", "Waldanteil", 0, 1, 0.01, 0.5],
  ["feuchte", "Feuchtigkeit", -1, 1, 0.05, 0],
  ["felsneigung", "Fels ab Hangneigung (°)", 20, 60, 1, 38],
];
const BIOM_FARBEN = [[214, 200, 150], [122, 166, 80], [62, 112, 48], [36, 78, 50], [84, 96, 58], [176, 164, 102], [128, 120, 110], [238, 240, 245]];
function biomParams() {
  const p = { seed: parseFloat($("p-seed").value) };
  for (const [k] of BIOM_PARAMS) p[k] = parseFloat($("p-" + k).value);
  return p;
}
const analyseArgs = () => ({ N, zelle: ZELLE, bp: biomParams(), schwelle: FLUSS_SCHWELLE });
function params() {
  const p = { welt: WELT };
  for (const [k] of PARAMS) p[k] = parseFloat($("p-" + k).value);
  return p;
}

// ---------- Farben ----------
const RAMPE = [[-100, [18, 42, 88]], [-30, [26, 64, 118]], [-6, [52, 112, 160]], [-0.5, [96, 160, 190]], [0, [214, 200, 156]],
  [2.5, [196, 190, 140]], [4, [104, 146, 74]], [40, [92, 136, 66]], [90, [118, 140, 78]], [150, [134, 124, 92]],
  [220, [128, 120, 110]], [290, [150, 148, 145]], [340, [232, 234, 238]]];
const LUT_MIN = -100, LUT_MAX = 500, LUT_SCHRITT = 0.25;
const LUT = (() => {
  const n = Math.round((LUT_MAX - LUT_MIN) / LUT_SCHRITT) + 1, t = new Uint8Array(n * 3);
  for (let k = 0; k < n; k++) {
    const h = LUT_MIN + k * LUT_SCHRITT;
    let i = 0; while (i < RAMPE.length - 2 && h > RAMPE[i + 1][0]) i++;
    const [h0, c0] = RAMPE[i], [h1, c1] = RAMPE[i + 1];
    const f = Math.min(1, Math.max(0, (h - h0) / (h1 - h0)));
    for (let c = 0; c < 3; c++) t[k * 3 + c] = c0[c] + (c1[c] - c0[c]) * f;
  }
  return t;
})();
function lutIndex(h) { return Math.max(0, Math.min(LUT.length / 3 - 1, Math.round((h - LUT_MIN) / LUT_SCHRITT))) * 3; }

// Kartenbild (mit Schattierung) und reine Farbkarte (für Godot / 3D)
let bild = new ImageData(N, N), farbe = new Uint8ClampedArray(N * N * 4);
const basis = document.createElement("canvas"); basis.width = N; basis.height = N;
let bctx = basis.getContext("2d");

// Weltgröße ändern: alle Raster neu anlegen. Marker, Ressourcen und Wege passen nicht mehr und werden verworfen.
function weltgroesseSetzen(meter) {
  if (meter === WELT) return false;
  WELT = meter; N = WELT / ZELLE;
  zustand.H = new Float32Array(N * N); zustand.A = new Float32Array(N * N);
  zustand.B = new Uint8Array(N * N); zustand.O = new Uint8Array(N * N).fill(255);
  zustand.undo = []; zustand.redo = [];
  bild = new ImageData(N, N); farbe = new Uint8ClampedArray(N * N * 4);
  basis.width = N; basis.height = N; bctx = basis.getContext("2d");
  if (typeof markerZustand !== "undefined") { markerZustand.liste = []; markerZustand.auswahl = -1; markerZustand.ressourcen = null; markerPanel(); ressourcenInfo(); }
  if (typeof wegeZustand !== "undefined") { wegeZustand.liste = null; wegeInfo(); }
  if (typeof regionenZustand !== "undefined") regionenZuruecksetzen();
  if (window.WELT_API) window.WELT_API.N = N;
  ansicht.passend();
  exportOptionen();
  return true;
}

// Regler-km -> Meter, gerundet auf 512 m (Terrain3D-Regionen sind 256 m groß, Raster bleibt ganzzahlig)
function weltMeter(km) { return Math.max(2048, Math.min(8192, Math.round(km * 1000 / 512) * 512)); }
function weltText(m) { return `${(m / 1000).toLocaleString("de", { maximumFractionDigits: 1 })} km`; }

function exportOptionen() {
  const sel = $("p-exportgroesse"); if (!sel) return;
  const alt = sel.value, eins = WELT, zwei = WELT / 2;
  sel.innerHTML = `<option value="${eins}">${eins} × ${eins} (1 m pro Pixel${eins > 4096 ? ", ~" + Math.round(eins * eins * 8 / 1e6) + " MB" : ""})</option>` +
    `<option value="${zwei}">${zwei} × ${zwei} (2 m pro Pixel)</option>`;
  sel.value = [...sel.options].some((o) => o.value === alt) ? alt : String(eins > 4096 ? zwei : eins);
}
const LICHT = (() => { const l = [-1, -1, 1.6], n = Math.hypot(...l); return l.map((v) => v / n); })();

function zeichneBereich(x0, y0, x1, y1) {
  const H = zustand.H, A = zustand.A, d = bild.data;
  x0 = Math.max(0, x0 | 0); y0 = Math.max(0, y0 | 0); x1 = Math.min(N - 1, x1 | 0); y1 = Math.min(N - 1, y1 | 0);
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const i = y * N + x, h = H[i];
    let r, g, b;
    if (zustand.modus === "biome" && h > 0) {
      const bf = BIOM_FARBEN[biomBei(i)]; r = bf[0]; g = bf[1]; b = bf[2];
    } else { const li = lutIndex(h); r = LUT[li]; g = LUT[li + 1]; b = LUT[li + 2]; }
    const fluss = zustand.fluesseZeigen && A[i] > FLUSS_SCHWELLE && h > 0;
    if (fluss) { const s = Math.min(1, 0.55 + 0.12 * Math.log2(A[i] / FLUSS_SCHWELLE)); r += (52 - r) * s; g += (110 - g) * s; b += (190 - b) * s; }
    const q = i * 4;
    farbe[q] = r; farbe[q + 1] = g; farbe[q + 2] = b; farbe[q + 3] = 255;
    if (h > 0) {
      const hl = H[i - (x > 0 ? 1 : 0)], hr = H[i + (x < N - 1 ? 1 : 0)], ho = H[i - (y > 0 ? N : 0)], hu = H[i + (y < N - 1 ? N : 0)];
      const gx = (hr - hl) / (2 * ZELLE) * 2.2, gy = (hu - ho) / (2 * ZELLE) * 2.2;
      const ln = Math.hypot(gx, gy, 1);
      const s = Math.max(0, (-gx * LICHT[0] - gy * LICHT[1] + LICHT[2]) / ln) * 0.8 + 0.32;
      r *= s; g *= s; b *= s;
      if (zustand.hoehenlinien) {
        const k0 = Math.floor(h / 10), k1 = Math.floor(hr / 10), k2 = Math.floor(hu / 10);
        if (k0 !== k1 || k0 !== k2) {
          const haupt = Math.floor(h / 50) !== Math.floor(hr / 50) || Math.floor(h / 50) !== Math.floor(hu / 50);
          const m = haupt ? 0.62 : 0.84; r *= m; g *= m; b *= m;
        }
      }
    }
    d[q] = r; d[q + 1] = g; d[q + 2] = b; d[q + 3] = 255;
  }
  bctx.putImageData(bild, 0, 0, x0, y0, x1 - x0 + 1, y1 - y0 + 1);
}
function biomBei(i) { return zustand.O[i] !== 255 ? zustand.O[i] : zustand.B[i]; }
function effektiveBiome() { const E = new Uint8Array(N * N); for (let i = 0; i < E.length; i++) E[i] = biomBei(i); return E; }
function zeichneAlles() { zeichneBereich(0, 0, N - 1, N - 1); ansicht.zeichne(); dreiDVeraltet(); }

// ---------- 2D-Ansicht: Zoom, Verschieben, Pinsel-Cursor ----------
const karte = $("karte"), kctx = karte.getContext("2d");
const ansicht = {
  zoom: 1, cx: N / 2, cy: N / 2, maus: null,
  passend() { const r = karte.getBoundingClientRect(); this.zoom = Math.min(r.width, r.height) / N * 0.96; this.cx = N / 2; this.cy = N / 2; },
  zuZelle(px, py) { const r = karte.getBoundingClientRect(); return [(px - r.left - r.width / 2) / this.zoom + this.cx, (py - r.top - r.height / 2) / this.zoom + this.cy]; },
  zeichne() {
    const dpr = window.devicePixelRatio || 1, r = karte.getBoundingClientRect();
    if (karte.width !== Math.round(r.width * dpr) || karte.height !== Math.round(r.height * dpr)) { karte.width = Math.round(r.width * dpr); karte.height = Math.round(r.height * dpr); }
    kctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    kctx.fillStyle = "#1b2a3f"; kctx.fillRect(0, 0, r.width, r.height);
    kctx.imageSmoothingEnabled = this.zoom < 2;
    const ox = r.width / 2 - this.cx * this.zoom, oy = r.height / 2 - this.cy * this.zoom;
    kctx.drawImage(basis, ox, oy, N * this.zoom, N * this.zoom);
    regionenZeichnen(kctx, ox, oy, this.zoom);
    kctx.imageSmoothingEnabled = this.zoom < 2;
    markerZeichnen(kctx, ox, oy, this.zoom);
    // Maßstab: 500 m
    const l = 500 / ZELLE * this.zoom;
    kctx.fillStyle = "rgba(0,0,0,.55)"; kctx.fillRect(12, r.height - 34, l + 16, 24);
    kctx.fillStyle = "#fff"; kctx.fillRect(20, r.height - 18, l, 3);
    kctx.font = "12px system-ui"; kctx.fillText("500 m", 20, r.height - 22);
    if (this.maus && !zustand.werkzeug.startsWith("marker")) {
      const [mx, my] = this.maus;
      kctx.strokeStyle = "rgba(255,255,255,.9)"; kctx.lineWidth = 1.5;
      kctx.beginPath(); kctx.arc(mx - r.left, my - r.top, zustand.groesse / ZELLE / 2 * this.zoom, 0, Math.PI * 2); kctx.stroke();
    }
  },
};

// ---------- Pinsel ----------
const nzPinsel = makeNoise(4242);
const WERKZEUGE = [
  ["anheben", "Anheben", "1"], ["absenken", "Absenken", "2"], ["glaetten", "Glätten", "3"], ["ebnen", "Ebnen", "4"],
  ["gebirge", "Gebirge", "5"], ["tal", "Tal", "6"], ["huegel", "Hügel", "7"], ["meer", "Meer", "8"], ["land", "Land", "9"],
];
let strich = null;
function pinsel(cx, cy, dt) {
  const H = zustand.H, r = zustand.groesse / ZELLE / 2, s = zustand.staerke, w = zustand.werkzeug;
  if (w.startsWith("biom:")) return biomPinsel(cx, cy, r, w === "biom:auto" ? 255 : parseInt(w.slice(5), 10));
  const x0 = Math.max(1, Math.floor(cx - r)), x1 = Math.min(N - 2, Math.ceil(cx + r));
  const y0 = Math.max(1, Math.floor(cy - r)), y1 = Math.min(N - 2, Math.ceil(cy + r));
  if (x0 > x1 || y0 > y1) return;
  let kopie = null;
  if (w === "glaetten" || w === "tal") {
    kopie = new Float32Array((x1 - x0 + 3) * (y1 - y0 + 3));
    for (let y = y0 - 1; y <= y1 + 1; y++) for (let x = x0 - 1; x <= x1 + 1; x++) kopie[(y - y0 + 1) * (x1 - x0 + 3) + (x - x0 + 1)] = H[y * N + x];
  }
  const kw = x1 - x0 + 3;
  const k = (x, y) => kopie[(y - y0 + 1) * kw + (x - x0 + 1)];
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const d2 = ((x - cx) ** 2 + (y - cy) ** 2) / (r * r);
    if (d2 >= 1) continue;
    const f = (1 - d2) * (1 - d2);
    const i = y * N + x;
    switch (w) {
      case "anheben": H[i] += 25 * s * dt * f; break;
      case "absenken": H[i] -= 25 * s * dt * f; break;
      case "glaetten": {
        const avg = (k(x - 1, y) + k(x + 1, y) + k(x, y - 1) + k(x, y + 1) + k(x, y) * 4) / 8;
        H[i] += (avg - H[i]) * Math.min(1, 12 * s * dt * f); break;
      }
      case "ebnen": H[i] += (strich.ziel - H[i]) * Math.min(1, 6 * s * dt * f); break;
      case "gebirge": {
        // Grat-Rauschen in Weltkoordinaten (~300 m Wellenlänge) -> Bergkämme statt Kuppel
        const rid = nzPinsel.ridged(x * ZELLE / 300, y * ZELLE / 300, 5);
        H[i] += 60 * s * dt * f * (0.15 + 1.6 * rid * rid); break;
      }
      case "tal": {
        const avg = (k(x - 1, y) + k(x + 1, y) + k(x, y - 1) + k(x, y + 1)) / 4;
        H[i] += (avg - H[i]) * Math.min(1, 4 * s * dt * f);
        H[i] -= 18 * s * dt * Math.sqrt(f); break;
      }
      case "huegel": {
        const n = nzPinsel.fbm(x * ZELLE / 90 + 50, y * ZELLE / 90 + 20, 3);
        H[i] += 14 * s * dt * f * Math.max(0, 0.35 + n * 1.4); break;
      }
      case "meer": if (H[i] > -6) H[i] += (-6 - H[i]) * Math.min(1, 5 * s * dt * f); break;
      case "land": if (H[i] < 3) H[i] += (3 - H[i]) * Math.min(1, 5 * s * dt * f); break;
    }
  }
  zeichneBereich(x0 - 1, y0 - 1, x1 + 1, y1 + 1);
}

function biomPinsel(cx, cy, r, id) {
  // harte Kante mit leicht gezacktem Rand, damit gemalte Biome natürlich aussehen
  const O = zustand.O;
  const x0 = Math.max(0, Math.floor(cx - r)), x1 = Math.min(N - 1, Math.ceil(cx + r));
  const y0 = Math.max(0, Math.floor(cy - r)), y1 = Math.min(N - 1, Math.ceil(cy + r));
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r;
    if (d < 1 - 0.22 * (nzPinsel.fbm(x * 0.12, y * 0.12, 3) + 0.5) && zustand.H[y * N + x] > 0) O[y * N + x] = id;
  }
  zeichneBereich(x0 - 1, y0 - 1, x1 + 1, y1 + 1);
}

function undoPunkt() {
  zustand.undo.push({ H: zustand.H.slice(), O: zustand.O.slice() });
  if (zustand.undo.length > 30) zustand.undo.shift();
  zustand.redo = [];
}
function rueckgaengig() {
  if (!zustand.undo.length) return;
  zustand.redo.push({ H: zustand.H, O: zustand.O }); const u = zustand.undo.pop(); zustand.H = u.H; zustand.O = u.O; nachAenderung(true);
}
function wiederholen() {
  if (!zustand.redo.length) return;
  zustand.undo.push({ H: zustand.H, O: zustand.O }); const u = zustand.redo.pop(); zustand.H = u.H; zustand.O = u.O; nachAenderung(true);
}

let flussTimer = null;
function nachAenderung(sofortZeichnen) {
  zustand.version++;
  if (markerZustand.ressourcen && !markerZustand.ressourcenAlt) { markerZustand.ressourcenAlt = true; ressourcenInfo(); }
  if (wegeZustand.liste && !wegeZustand.alt) { wegeZustand.alt = true; wegeInfo(); }
  if (sofortZeichnen) zeichneAlles();
  clearTimeout(flussTimer);
  flussTimer = setTimeout(async () => {
    const v = zustand.version;
    const r = await auftrag({ auftrag: "analyse", H: zustand.H.slice(), ...analyseArgs(), version: v });
    if (v !== zustand.version) return;
    zustand.A = r.A; zustand.B = r.B; zeichneAlles();
  }, 250);
  dreiDVeraltet();
}

karte.addEventListener("contextmenu", (e) => e.preventDefault());
let verschieben = null, leertaste = false;
karte.addEventListener("pointerdown", (e) => {
  karte.setPointerCapture(e.pointerId);
  if (e.button === 1 || e.button === 2 || leertaste) { verschieben = { x: e.clientX, y: e.clientY }; return; }
  if (e.button !== 0) return;
  const [cx, cy] = ansicht.zuZelle(e.clientX, e.clientY);
  if (zustand.werkzeug.startsWith("marker")) { markerDown(cx, cy, e); return; }
  undoPunkt();
  const zi = Math.min(N - 1, Math.max(0, Math.round(cy))) * N + Math.min(N - 1, Math.max(0, Math.round(cx)));
  strich = { cx, cy, zeit: performance.now(), ziel: zustand.H[zi] };
  requestAnimationFrame(strichSchleife);
});
function strichSchleife(t) {
  if (!strich) return;
  const dt = Math.min(0.05, (t - strich.zeit) / 1000); strich.zeit = t;
  if (dt > 0) pinsel(strich.cx, strich.cy, dt);
  ansicht.zeichne();
  requestAnimationFrame(strichSchleife);
}
karte.addEventListener("pointermove", (e) => {
  ansicht.maus = [e.clientX, e.clientY];
  if (verschieben) {
    ansicht.cx -= (e.clientX - verschieben.x) / ansicht.zoom; ansicht.cy -= (e.clientY - verschieben.y) / ansicht.zoom;
    verschieben = { x: e.clientX, y: e.clientY };
  }
  const [cx, cy] = ansicht.zuZelle(e.clientX, e.clientY);
  if (strich) { strich.cx = cx; strich.cy = cy; }
  markerMove(cx, cy);
  if (zustand.werkzeug.startsWith("marker:")) {
    // Zeiger: Hand über vorhandenem Marker (verschieben möglich), sonst Fadenkreuz zum Setzen
    karte.style.cursor = markerZustand.ziehen ? "grabbing" : markerBei(cx, cy) >= 0 ? "grab" : (zustand.werkzeug === "marker:auswahl" ? "default" : "crosshair");
  }
  const xi = Math.round(cx), yi = Math.round(cy);
  if (xi >= 0 && yi >= 0 && xi < N && yi < N) {
    const ii = yi * N + xi, h = zustand.H[ii];
    $("info").textContent = `x ${Math.round(cx * ZELLE)} m · y ${Math.round(cy * ZELLE)} m · Höhe ${h.toFixed(1)} m · ${h > 0 ? BIOM_NAMEN[biomBei(ii)] + (zustand.O[ii] !== 255 ? " (gemalt)" : "") : "Meer"}`;
  }
  ansicht.zeichne();
});
karte.addEventListener("pointerup", () => {
  if (strich) { strich = null; nachAenderung(false); }
  markerUp();
  verschieben = null;
});
karte.addEventListener("pointerleave", () => { ansicht.maus = null; ansicht.zeichne(); });
karte.addEventListener("wheel", (e) => {
  e.preventDefault();
  const [cx, cy] = ansicht.zuZelle(e.clientX, e.clientY);
  const z = Math.min(24, Math.max(0.2, ansicht.zoom * Math.exp(-e.deltaY * 0.0015)));
  ansicht.cx = cx - (cx - ansicht.cx) * ansicht.zoom / z; ansicht.cy = cy - (cy - ansicht.cy) * ansicht.zoom / z;
  ansicht.zoom = z; ansicht.zeichne();
}, { passive: false });

// ---------- 3D ----------
let vorschau = null, dreiDAlt = true;
function dreiDVeraltet() { dreiDAlt = true; if (document.body.dataset.tab === "3d") dreiDAktualisieren(); }
function dreiDAktualisieren() {
  if (!vorschau) {
    vorschau = new Vorschau3D($("gl"));
    if (vorschau.fehler) { status(vorschau.fehler); return; }
    $("p-ueberh").addEventListener("input", (e) => { vorschau.ueberh = parseFloat(e.target.value); vorschau.zeichne(); });
    vorschau.ueberh = parseFloat($("p-ueberh").value);
  }
  if (dreiDAlt) { vorschau.setzeGelaende(zustand.H, N, ZELLE, farbe); dreiDAlt = false; } else vorschau.zeichne();
}
function tab(name) {
  document.body.dataset.tab = name;
  for (const b of document.querySelectorAll("[data-tab-knopf]")) b.classList.toggle("aktiv", b.dataset.tabKnopf === name);
  if (name === "3d") dreiDAktualisieren(); else ansicht.zeichne();
}

// ---------- Aktionen ----------
async function generieren() {
  const gewuenscht = weltMeter(parseFloat($("p-weltgroesse").value));
  if (gewuenscht !== WELT && (markerZustand.liste.length || wegeZustand.liste) &&
      !confirm("Die Weltgröße ändert sich. Marker, Ressourcen und Wege werden dabei entfernt. Fortfahren?")) {
    $("p-weltgroesse").value = WELT / 1000; $("p-weltgroesse").dispatchEvent(new Event("input")); return;
  }
  const neu = weltgroesseSetzen(gewuenscht);
  beschaeftigt(true);
  const r = await auftrag({ auftrag: "generieren", p: params(), ...analyseArgs() });
  if (zustand.version > 0 && !neu) undoPunkt();
  zustand.H = r.H; zustand.A = r.A; zustand.B = r.B; zustand.version++;
  $("p-weltgroesse").dispatchEvent(new Event("input"));
  zeichneAlles(); status("Fertig"); beschaeftigt(false);
}
async function erosionAnwenden() {
  beschaeftigt(true); undoPunkt();
  const H = zustand.H.slice();
  const r = await auftrag({ auftrag: "erosion", H, ...analyseArgs(), anzahl: Math.round(parseFloat($("p-erosion2").value) * 1000 * (N / 1024) ** 2), seed: Math.floor(Math.random() * 1e6) }, [H.buffer]);
  zustand.H = r.H; zustand.A = r.A; zustand.B = r.B; zustand.version++;
  zeichneAlles(); status("Erosion angewendet"); beschaeftigt(false);
}
async function flussbettenEinschneiden() {
  beschaeftigt(true); undoPunkt();
  const H = zustand.H.slice();
  const r = await auftrag({ auftrag: "flussbetten", H, ...analyseArgs() }, [H.buffer]);
  zustand.H = r.H; zustand.A = r.A; zustand.B = r.B; zustand.version++;
  zeichneAlles(); status("Flussbetten eingeschnitten"); beschaeftigt(false);
}

function herunterladen(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
}
const bytes = (ta) => new Uint8Array(ta.buffer, ta.byteOffset, ta.byteLength);
const textBytes = (s) => new TextEncoder().encode(s);
async function canvasPng(c) { return new Uint8Array(await (await new Promise((r) => c.toBlob(r, "image/png"))).arrayBuffer()); }

async function projektSpeichern() {
  const meta = { programm: "Weltgenerator", version: 3, N, welt_m: WELT, params: params(), biome: biomParams(),
    regionen: regionenZustand.REG ? { namen: regionenZustand.namen, gipfel: regionenZustand.gipfel } : null };
  herunterladen(zipErstellen([
    { name: "projekt.json", daten: textBytes(JSON.stringify(meta, null, 2)) },
    { name: "hoehe.r32", daten: bytes(zustand.H) },
    { name: "biome_gemalt.u8", daten: zustand.O },
    ...(regionenZustand.REG ? [{ name: "regionen.u8", daten: regionenZustand.REG }] : []),
    { name: "marker.json", daten: textBytes(JSON.stringify(markerZustand.liste)) },
    ...(markerZustand.ressourcen ? [{ name: "ressourcen.json", daten: textBytes(JSON.stringify(markerZustand.ressourcen)) }] : []),
    ...(wegeZustand.liste ? [{ name: "wege.json", daten: textBytes(JSON.stringify(wegeExport())) }] : []),
    ...(wegeZustand.liste ? [{ name: "wege.json", daten: textBytes(JSON.stringify(wegeZustand.liste)) }] : []),
  ]), `welt_projekt_${meta.params.seed}.zip`);
  status("Projekt gespeichert");
}
async function projektLaden(datei) {
  try {
    const z = await zipLesen(await datei.arrayBuffer());
    const meta = JSON.parse(new TextDecoder().decode(z["projekt.json"]));
    const welt = meta.welt_m || 4096;
    if (welt / ZELLE !== meta.N) throw new Error("Unbekanntes Rasterformat");
    weltgroesseSetzen(welt);
    $("p-weltgroesse").value = welt / 1000; $("p-weltgroesse").dispatchEvent(new Event("input"));
    for (const [k] of PARAMS) if (meta.params[k] != null) { $("p-" + k).value = meta.params[k]; $("p-" + k).dispatchEvent(new Event("input")); }
    for (const [k] of BIOM_PARAMS) if (meta.biome && meta.biome[k] != null) { $("p-" + k).value = meta.biome[k]; $("o-" + k).textContent = meta.biome[k]; }
    undoPunkt();
    const hd = z["hoehe.r32"] || z["hoehe_1024.r32"], bd = z["biome_gemalt.u8"] || z["biome_gemalt_1024.u8"];
    zustand.H = new Float32Array(hd.slice().buffer);
    zustand.O = bd ? bd.slice() : new Uint8Array(N * N).fill(255);
    const lies = (n) => (z[n] ? JSON.parse(new TextDecoder().decode(z[n])) : null);
    markerZustand.liste = lies("marker.json") || []; markerZustand.auswahl = -1;
    markerZustand.ressourcen = lies("ressourcen.json"); markerZustand.ressourcenAlt = false;
    wegeZustand.liste = lies("wege.json"); wegeZustand.alt = false;
    regionenLaden(z["regionen.u8"], meta.regionen);
    markerPanel(); ressourcenInfo(); wegeInfo();
    nachAenderung(true); status("Projekt geladen");
  } catch (err) { status("Laden fehlgeschlagen: " + err.message); }
}

async function exportieren() {
  beschaeftigt(true);
  const M = parseInt($("p-exportgroesse").value, 10);
  const feindetail = parseFloat($("p-feindetail").value);
  const r = await auftrag({ auftrag: "hochskalieren", H: zustand.H.slice(), N, M, welt: WELT, seed: params().seed, feindetail, wege: wegeZustand.liste || [] });
  const E = effektiveBiome();
  const st = await auftrag({ auftrag: "steuerkarte", E: E.slice(), N, M, seed: params().seed });
  if (r.maske) wegInSteuerkarte(st.out, r.maske);
  status("Export: Dateien schreiben …", 1);
  let mn = Infinity, mx = -Infinity;
  for (let i = 0; i < r.out.length; i++) { const v = r.out[i]; if (v < mn) mn = v; if (v > mx) mx = v; }
  // Farbkarte ohne Schattierung (für Godot) und Übersicht mit Schattierung
  const fc = document.createElement("canvas"); fc.width = N; fc.height = N;
  fc.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(farbe), N, N), 0, 0);
  const meta = {
    programm: "Weltgenerator", version: 1,
    welt_m: WELT, aufloesung: M, meter_pro_pixel: WELT / M,
    hoehe: { datei: `hoehe_${M}.r32`, format: "float32 little-endian, Meter, Zeile für Zeile von Norden (oben) nach Süden", min: mn, max: mx },
    raster: N, zelle_m: ZELLE,
    farbe: { datei: `farbe_${N}.png` },
    wege: wegeZustand.liste ? { datei: "wege.json", format: "Liste {typ strasse|weg, breite m, punkte [[x,y,z]] in Metern (y = Fahrbahnhöhe), bruecke [0|1] je Segment (Punkt k-1 -> k)}" } : null,
    marker: { datei: "marker.json", format: "Liste {typ, name, x, z, hoehe, radius | art/breite/laenge/winkel}; x/z in Metern, Weltmitte = 0" },
    ressourcen: markerZustand.ressourcen ? { datei: "ressourcen.json", format: "baeume [x,z,art(0 Fichte,1 Kiefer,2 Eiche),alter(0 jung,1 alt)] · buesche [x,z] · erze [x,z,tier 0-5,groesse 1-5] · pflanzen [x,z,art(0 Hanf,1 Beeren,2 Kräuter),farbe]" } : null,
    steuerung: { datei: `steuerung_${M}.r32`, format: "uint32 little-endian, Terrain3D-Steuerkarte (Basis/Overlay/Überblendung)" },
    biome: { datei: `biome_${N}.u8`, format: `uint8 je Zelle (${ZELLE} m), ${N} x ${N}, Zeile für Zeile`, namen: BIOM_NAMEN, texturen: ["sand", "wiese", "laubboden", "nadelboden", "sumpf", "steppe", "fels", "schnee", "weg"] },
    meeresspiegel: 0, params: params(), biom_params: biomParams(),
    regionen: regionenExportMeta(),
  };
  herunterladen(zipErstellen([
    { name: "welt.json", daten: textBytes(JSON.stringify(meta, null, 2)) },
    { name: `hoehe_${M}.r32`, daten: bytes(r.out) },
    { name: `farbe_${N}.png`, daten: await canvasPng(fc) },
    { name: `steuerung_${M}.r32`, daten: bytes(st.out) },
    { name: `biome_${N}.u8`, daten: E },
    ...(regionenZustand.REG ? [{ name: `regionen_${N}.u8`, daten: regionenZustand.REG }] : []),
    { name: "marker.json", daten: textBytes(JSON.stringify(markerExport(), null, 1)) },
    ...(markerZustand.ressourcen ? [{ name: "ressourcen.json", daten: textBytes(JSON.stringify(markerZustand.ressourcen)) }] : []),
    ...(wegeZustand.liste ? [{ name: "wege.json", daten: textBytes(JSON.stringify(wegeExport())) }] : []),
    { name: "uebersicht.png", daten: await canvasPng(basis) },
  ]), "welt_export.zip");
  status(`Export fertig: ${M} × ${M}, Höhen ${mn.toFixed(1)} … ${mx.toFixed(1)} m`);
  beschaeftigt(false);
}

// ---------- UI aufbauen ----------
function aufbauen() {
  const pg = $("parameter");
  {
    const z = document.createElement("label"); z.className = "regler";
    z.innerHTML = `<span>Weltgröße</span><output id="o-weltgroesse"></output>
      <input id="p-weltgroesse" type="range" min="2" max="8" step="0.5" value="4">`;
    pg.appendChild(z);
    const inp = z.querySelector("input");
    inp.addEventListener("input", () => { const m = weltMeter(+inp.value); z.querySelector("output").textContent = `${weltText(m)} × ${weltText(m)}` + (m !== WELT ? " – „Neu generieren“" : ""); });
    inp.dispatchEvent(new Event("input"));
  }
  for (const [k, name, min, max, step, wert] of PARAMS) {
    const z = document.createElement("label"); z.className = "regler";
    z.innerHTML = `<span>${name}</span><output id="o-${k}">${wert}</output>
      <input id="p-${k}" type="${k === "seed" ? "number" : "range"}" min="${min}" max="${max}" step="${step}" value="${wert}">`;
    pg.appendChild(z);
    const inp = z.querySelector("input");
    inp.addEventListener("input", () => (z.querySelector("output").textContent = inp.value));
  }
  const bg = $("biom-parameter");
  let biomTimer = null;
  for (const [k, name, min, max, step, wert] of BIOM_PARAMS) {
    const z = document.createElement("label"); z.className = "regler";
    z.innerHTML = `<span>${name}</span><output id="o-${k}">${wert}</output><input id="p-${k}" type="range" min="${min}" max="${max}" step="${step}" value="${wert}">`;
    bg.appendChild(z);
    const inp = z.querySelector("input");
    inp.addEventListener("input", () => { z.querySelector("output").textContent = inp.value; clearTimeout(biomTimer); biomTimer = setTimeout(() => nachAenderung(false), 200); });
  }
  const bw = $("biom-werkzeuge");
  BIOM_NAMEN.forEach((name, id) => {
    const b = document.createElement("button"); b.className = "werkzeug biom"; b.dataset.w = "biom:" + id;
    b.innerHTML = `<i style="background:rgb(${BIOM_FARBEN[id].join(",")})"></i>${name}`; b.onclick = () => waehle("biom:" + id); bw.appendChild(b);
  });
  const ba = document.createElement("button"); ba.className = "werkzeug biom"; ba.dataset.w = "biom:auto";
  ba.innerHTML = `<i class="auto"></i>Automatisch`; ba.title = "Gemalte Biome entfernen – zurück zur automatischen Verteilung"; ba.onclick = () => waehle("biom:auto"); bw.appendChild(ba);
  $("gemalt-loeschen").onclick = () => { undoPunkt(); zustand.O.fill(255); zeichneAlles(); status("Alle gemalten Biome entfernt"); };
  for (const r of document.querySelectorAll("input[name=modus]")) r.onchange = () => { zustand.modus = r.value; zeichneAlles(); };
  $("zufall").onclick = () => { $("p-seed").value = Math.floor(Math.random() * 999999) + 1; $("o-seed").textContent = $("p-seed").value; generieren(); };
  $("generieren").onclick = generieren;
  const wg = $("werkzeuge");
  for (const [id, name, taste] of WERKZEUGE) {
    const b = document.createElement("button"); b.className = "werkzeug"; b.dataset.w = id;
    b.innerHTML = `${name}<kbd>${taste}</kbd>`; b.onclick = () => waehle(id); wg.appendChild(b);
  }
  waehle("anheben");
  for (const [id, key] of [["p-groesse", "groesse"], ["p-staerke", "staerke"]]) {
    const inp = $(id); const out = inp.parentElement.querySelector("output");
    const upd = () => { zustand[key] = parseFloat(inp.value); out.textContent = key === "groesse" ? `${inp.value} m` : inp.value; };
    inp.addEventListener("input", upd); upd();
  }
  for (const id of ["p-erosion2", "p-feindetail", "p-ueberh"]) {
    const inp = $(id); const out = inp.parentElement.querySelector("output");
    inp.addEventListener("input", () => (out.textContent = inp.value)); out.textContent = inp.value;
  }
  $("undo").onclick = rueckgaengig; $("redo").onclick = wiederholen;
  $("erosion-anwenden").onclick = erosionAnwenden;
  $("flussbetten").onclick = flussbettenEinschneiden;
  $("hoehenlinien").onchange = (e) => { zustand.hoehenlinien = e.target.checked; zeichneAlles(); };
  $("fluesse").onchange = (e) => { zustand.fluesseZeigen = e.target.checked; zeichneAlles(); };
  $("speichern").onclick = projektSpeichern;
  $("laden").onclick = () => $("laden-datei").click();
  $("laden-datei").onchange = (e) => { if (e.target.files[0]) projektLaden(e.target.files[0]); e.target.value = ""; };
  $("exportieren").onclick = exportieren;
  for (const b of document.querySelectorAll("[data-tab-knopf]")) b.onclick = () => tab(b.dataset.tabKnopf);
  markerAufbauen();
  regionenAufbauen();
  window.addEventListener("keydown", (e) => {
    if ((e.target.tagName === "INPUT" && e.target.type !== "range" && e.target.type !== "checkbox") || e.target.tagName === "SELECT") return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? wiederholen() : rueckgaengig(); return; }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); wiederholen(); return; }
    if (e.key === " ") { leertaste = true; e.preventDefault(); return; }
    const w = WERKZEUGE.find((x) => x[2] === e.key); if (w) waehle(w[0]);
    if (e.key === "[" || e.key === "]") {
      const inp = $("p-groesse"); inp.value = Math.max(+inp.min, Math.min(+inp.max, +inp.value * (e.key === "]" ? 1.2 : 1 / 1.2)));
      inp.dispatchEvent(new Event("input")); ansicht.zeichne();
    }
  });
  window.addEventListener("keyup", (e) => { if (e.key === " ") leertaste = false; });
  window.addEventListener("resize", () => (document.body.dataset.tab === "3d" ? vorschau && vorschau.zeichne() : ansicht.zeichne()));
  tab("karte");
  exportOptionen();
  ansicht.passend();
  generieren();
}
function waehle(id) {
  zustand.werkzeug = id;
  for (const b of document.querySelectorAll(".werkzeug")) b.classList.toggle("aktiv", b.dataset.w === id);
  karte.style.cursor = id === "marker:auswahl" ? "default" : id.startsWith("marker:") ? "crosshair" : "none";
}

// für automatische Tests
window.WELT_API = { weltgroesseSetzen, wegeZustand, wegeGenerierenStarten, markerZustand, markerNeu, vorschlaegeMachen, ressourcenVerteilenStarten, zustand, effektiveBiome, generieren, erosionAnwenden, flussbettenEinschneiden, exportieren, projektSpeichern, pinsel, waehle, tab, ansicht, N, params,
  regionenZustand, nebeninselFormen, zentralbergFormen, regionenBerechnen, siedlungenVorschlagen,
  strichTest(werkzeug, punkte, dt = 0.05) { waehle(werkzeug); undoPunkt(); strich = { ziel: zustand.H[Math.round(punkte[0][1]) * N + Math.round(punkte[0][0])] };
    for (const [x, y] of punkte) pinsel(x, y, dt); strich = null; nachAenderung(true); } };
aufbauen();
