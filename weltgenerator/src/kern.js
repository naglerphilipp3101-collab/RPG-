// ===== Weltgenerator: Rechenkern =====
// Läuft im Web Worker (Generierung, Erosion, Flüsse, Export) und wird auch im Hauptthread geladen (Pinsel-Rauschen).
// Höhen in Metern, Meeresspiegel = 0. Raster N x N, Zellgröße ZELLE Meter.

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Gradientenrauschen (Perlin), Ausgabe ca. -1..1. Bewusst schlicht gehalten: V8 optimiert das sehr gut.
function makeNoise(seed) {
  const rnd = mulberry32(seed >>> 0);
  const pp = [];
  for (let i = 0; i < 256; i++) pp.push(i);
  for (let i = 255; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = pp[i]; pp[i] = pp[j]; pp[j] = t; }
  const perm = new Int32Array(512);
  for (let i = 0; i < 512; i++) perm[i] = pp[i & 255];
  const GX = new Float64Array([1, 0.7071, 0, -0.7071, -1, -0.7071, 0, 0.7071]);
  const GY = new Float64Array([0, 0.7071, 1, 0.7071, 0, -0.7071, -1, -0.7071]);
  function noise(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const X = xi & 255, Y = yi & 255;
    const px = perm[X], px1 = perm[X + 1];
    const a = perm[px + Y] & 7, b = perm[px1 + Y] & 7, c = perm[px + Y + 1] & 7, d = perm[px1 + Y + 1] & 7;
    const n00 = GX[a] * xf + GY[a] * yf, n10 = GX[b] * (xf - 1) + GY[b] * yf;
    const n01 = GX[c] * xf + GY[c] * (yf - 1), n11 = GX[d] * (xf - 1) + GY[d] * (yf - 1);
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10), v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const nx0 = n00 + u * (n10 - n00), nx1 = n01 + u * (n11 - n01);
    return 1.4142 * (nx0 + v * (nx1 - nx0));
  }
  function fbm(x, y, oct, lac = 2.0, gain = 0.5) {
    let s = 0, a = 0.5, f = 1;
    for (let i = 0; i < oct; i++) { s += a * noise(x * f + i * 17.3, y * f - i * 9.1); f *= lac; a *= gain; }
    return s;   // ca. -1..1
  }
  function ridged(x, y, oct) {
    // Grate: 1-|n|, quadriert, gewichtet -> 0..1
    let s = 0, a = 0.5, f = 1, w = 1, norm = 0;
    for (let i = 0; i < oct; i++) {
      let n = 1 - Math.abs(noise(x * f + i * 31.7, y * f + i * 11.3));
      n *= n; n *= w;
      w = Math.min(1, Math.max(0, n * 2));
      s += n * a; norm += a; f *= 2.1; a *= 0.5;
    }
    return s / norm;
  }
  return { noise, fbm, ridged };
}

function smoothstep(e0, e1, x) {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

// ---------- Grundlandschaft ----------
function generiere(N, p) {
  const nz = makeNoise(p.seed);
  const f = (p.welt || 4096) / 4096;     // größere Welt = mehr Hügel/Gebirgszüge statt größerer
  const H = new Float32Array(N * N);
  for (let j = 0; j < N; j++) {
    const v = (j + 0.5) / N;
    for (let i = 0; i < N; i++) {
      const u = (i + 0.5) / N;
      const dx = u - 0.5, dy = v - 0.5;
      // Küstenlinie: Domain-Warp + winkelabhängige Buchten/Halbinseln
      const wx = nz.fbm(u * 2.5 + 1.7, v * 2.5 + 8.3, 5) * 0.25 * p.kueste;
      const wy = nz.fbm(u * 2.5 + 5.2, v * 2.5 + 1.3, 5) * 0.25 * p.kueste;
      const ex = dx + wx, ey = dy + wy;
      const d = Math.sqrt(ex * ex + ey * ey) / 0.5;
      const a = Math.atan2(ey, ex);
      const rmod = 1 + 0.45 * p.kueste * nz.fbm(Math.cos(a) * 2.0 + 7, Math.sin(a) * 2.0 + 3, 4);
      const t = d / (p.inselgroesse * rmod);          // < 1 = Land
      const maske = smoothstep(1.0, 0.95, t);
      const innen = smoothstep(1.0, 0.0, t);
      // Flachland, das zur Mitte hin leicht ansteigt
      const basis = 2 + 18 * innen + 7 * nz.fbm(u * 7 * f, v * 7 * f, 4);
      // Hügel: in Hügelregionen stärker
      const hregion = 0.35 + 0.65 * smoothstep(-0.25, 0.35, nz.fbm(u * 3.5 * f + 11, v * 3.5 * f + 2, 3));
      const huegel = p.huegel * hregion * (0.55 + 0.45 * nz.fbm(u * 16 * f + 3, v * 16 * f + 9, 5)) * smoothstep(1.0, 0.7, t);
      // Gebirgszüge: nur in Gebirgsregionen, Abstand zur Küste
      const g = nz.fbm(u * 2.3 * Math.sqrt(f) + 20, v * 2.3 * Math.sqrt(f) + 40, 3) * 0.5 + 0.5;
      let mreg = smoothstep(0.62 - 0.4 * p.gebirge, 0.8 - 0.4 * p.gebirge, g) * smoothstep(0.92, 0.5, t);
      const wr = nz.fbm(u * 4 * f + 50, v * 4 * f + 60, 3) * 0.15;
      const rid = nz.ridged(u * 5.5 * f + wr, v * 5.5 * f - wr, 6);
      const berg = p.berghoehe * Math.pow(rid, 1.7) * mreg;
      const land = basis + huegel + berg;
      const meer = -1.5 - p.meerestiefe * smoothstep(0.97, 1.3, t);
      H[j * N + i] = meer + (land - meer) * maske;
    }
  }
  return H;
}

// ---------- Hydraulische Erosion (Wassertropfen) ----------
function erodiere(H, N, anzahl, seed, fortschritt) {
  const SK = 6;                       // Meter pro Erosions-Einheit (stabilere Zahlen)
  const rnd = mulberry32(seed * 7 + 13);
  const inertia = 0.06, kap = 4, minKap = 0.01, ablag = 0.3, abtrag = 0.3, verdunst = 0.025, grav = 4, maxSchritte = 70;
  const R = 2;
  // Pinsel-Gewichte für den Abtrag
  const ox = [], oy = [], gw = [];
  let summe = 0;
  for (let y = -R; y <= R; y++) for (let x = -R; x <= R; x++) {
    const dd = Math.sqrt(x * x + y * y);
    if (dd <= R) { ox.push(x); oy.push(y); gw.push(1 - dd / R); summe += 1 - dd / R; }
  }
  const OX = Int32Array.from(ox), OY = Int32Array.from(oy), GW = Float64Array.from(gw.map((w) => w / summe));
  const K = OX.length, iSK = 1 / SK;
  const schritt = Math.max(1, Math.floor(anzahl / 50));
  for (let n = 0; n < anzahl; n++) {
    if (fortschritt && n % schritt === 0) fortschritt(n / anzahl);
    let px = rnd() * (N - 3) + 1, py = rnd() * (N - 3) + 1;
    if (H[Math.floor(py) * N + Math.floor(px)] < 1) continue;   // nur auf Land starten
    let dx = 0, dy = 0, tempo = 1, wasser = 1, sed = 0;
    for (let s = 0; s < maxSchritte; s++) {
      const x = Math.floor(px), y = Math.floor(py);
      const fx = px - x, fy = py - y;
      const i = y * N + x;
      const a = H[i] * iSK, b = H[i + 1] * iSK, c = H[i + N] * iSK, d = H[i + N + 1] * iSK;
      const gx = (b - a) * (1 - fy) + (d - c) * fy;
      const gy = (c - a) * (1 - fx) + (d - b) * fx;
      const halt = a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy;
      dx = dx * inertia - gx * (1 - inertia);
      dy = dy * inertia - gy * (1 - inertia);
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len < 1e-6) break;
      dx /= len; dy /= len;
      px += dx; py += dy;
      if (px < 1 || py < 1 || px >= N - 2 || py >= N - 2) break;
      const x2 = Math.floor(px), y2 = Math.floor(py), fx2 = px - x2, fy2 = py - y2, j2 = y2 * N + x2;
      const neu = (H[j2] * (1 - fx2) * (1 - fy2) + H[j2 + 1] * fx2 * (1 - fy2) + H[j2 + N] * (1 - fx2) * fy2 + H[j2 + N + 1] * fx2 * fy2) * iSK;
      const dh = neu - halt;
      const kapazitaet = Math.max(-dh * tempo * wasser * kap, minKap);
      if (sed > kapazitaet || dh > 0) {
        const menge = dh > 0 ? Math.min(dh, sed) : (sed - kapazitaet) * ablag;
        sed -= menge;
        const m = menge * SK;
        H[i] += m * (1 - fx) * (1 - fy); H[i + 1] += m * fx * (1 - fy);
        H[i + N] += m * (1 - fx) * fy; H[i + N + 1] += m * fx * fy;
      } else {
        const menge = Math.min((kapazitaet - sed) * abtrag, -dh);
        if (x > R && y > R && x < N - R - 1 && y < N - R - 1) {
          for (let k = 0; k < K; k++) H[i + OY[k] * N + OX[k]] -= menge * GW[k] * SK;
          sed += menge;
        }
      }
      tempo = Math.sqrt(Math.max(0, tempo * tempo - dh * grav));
      wasser *= 1 - verdunst;
    }
  }
  if (fortschritt) fortschritt(1);
}

// leichte thermische Glättung: zu steile Kanten rutschen ab
function thermisch(H, N, runden, maxSteigung) {
  const tmp = new Float32Array(H.length);
  for (let r = 0; r < runden; r++) {
    tmp.set(H);
    for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
      const i = y * N + x;
      for (const o of [1, -1, N, -N]) {
        const diff = tmp[i] - tmp[i + o];
        if (diff > maxSteigung) { const m = (diff - maxSteigung) * 0.25; H[i] -= m; H[i + o] += m; }
      }
    }
  }
}

// ---------- Flüsse: Senken füllen (Priority-Flood) + Abflussakkumulation ----------
function fluesse(H, N) {
  const n = N * N;
  const F = new Float32Array(H);           // gefüllte Höhen
  const fertig = new Uint8Array(n);
  const reihenfolge = new Int32Array(n);   // Zellen in aufsteigender gefüllter Höhe
  let rk = 0;
  // Binärer Min-Heap über Zellindizes
  const heap = new Int32Array(n); let hs = 0;
  const push = (i) => {
    let k = hs++; heap[k] = i;
    while (k > 0) { const pk = (k - 1) >> 1; if (F[heap[pk]] <= F[heap[k]]) break; const t = heap[pk]; heap[pk] = heap[k]; heap[k] = t; k = pk; }
  };
  const pop = () => {
    const top = heap[0]; heap[0] = heap[--hs]; let k = 0;
    for (;;) {
      const l = 2 * k + 1, r = l + 1; let m = k;
      if (l < hs && F[heap[l]] < F[heap[m]]) m = l;
      if (r < hs && F[heap[r]] < F[heap[m]]) m = r;
      if (m === k) break; const t = heap[m]; heap[m] = heap[k]; heap[k] = t; k = m;
    }
    return top;
  };
  for (let i = 0; i < N; i++) for (const c of [i, (N - 1) * N + i, i * N, i * N + N - 1]) if (!fertig[c]) { fertig[c] = 1; push(c); }
  const ziel = new Int32Array(n).fill(-1);  // Abflussziel jeder Zelle
  const nb = [1, -1, N, -N, N + 1, N - 1, -N + 1, -N - 1];
  while (hs > 0) {
    const c = pop();
    reihenfolge[rk++] = c;
    const cx = c % N;
    for (const o of nb) {
      const q = c + o;
      if (q < 0 || q >= n) continue;
      const qx = q % N;
      if (Math.abs(qx - cx) > 1 || fertig[q]) continue;
      fertig[q] = 1;
      if (F[q] <= F[c]) F[q] = F[c] + 1e-3;   // Senke auffüllen, minimales Gefälle
      ziel[q] = c;
      push(q);
    }
  }
  // Akkumulation: von hoch nach tief
  const A = new Float32Array(n);
  for (let k = n - 1; k >= 0; k--) {
    const c = reihenfolge[k];
    if (H[c] > 0) A[c] += 1;
    if (ziel[c] >= 0) A[ziel[c]] += A[c];
  }
  return A;
}

// Flussnetz als Linienzüge für den Export: von jeder Quelle (Zelle über der Schwelle ohne Zufluss über der Schwelle)
// flussabwärts bis ins Meer, in einen See (seeMaske) oder bis zur Mündung in einen schon verfolgten Fluss.
// Ergebnis: [{ punkte: [[x, y, A], …] (Zellen, A = Einzugsgebiet in Zellen) }]
function flussNetz(H, N, schwelle, seeMaske) {
  const n = N * N;
  // Abflussrichtung wie in fluesse(): Priority-Flood über gefüllte Höhen
  const F = new Float32Array(H), fertig = new Uint8Array(n), ziel = new Int32Array(n).fill(-1), reihenfolge = new Int32Array(n);
  const heap = new Int32Array(n); let hs = 0, rk = 0;
  const push = (i) => { let k = hs++; heap[k] = i; while (k > 0) { const p = (k - 1) >> 1; if (F[heap[p]] <= F[heap[k]]) break; const t = heap[p]; heap[p] = heap[k]; heap[k] = t; k = p; } };
  const pop = () => { const top = heap[0]; heap[0] = heap[--hs]; let k = 0;
    for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < hs && F[heap[l]] < F[heap[m]]) m = l; if (r < hs && F[heap[r]] < F[heap[m]]) m = r; if (m === k) break; const t = heap[m]; heap[m] = heap[k]; heap[k] = t; k = m; }
    return top; };
  for (let i = 0; i < N; i++) for (const c of [i, (N - 1) * N + i, i * N, i * N + N - 1]) if (!fertig[c]) { fertig[c] = 1; push(c); }
  const nb = [1, -1, N, -N, N + 1, N - 1, -N + 1, -N - 1];
  while (hs > 0) {
    const c = pop(); reihenfolge[rk++] = c; const cx = c % N;
    for (const o of nb) { const q = c + o; if (q < 0 || q >= n || fertig[q] || Math.abs((q % N) - cx) > 1) continue;
      fertig[q] = 1; if (F[q] <= F[c]) F[q] = F[c] + 1e-3; ziel[q] = c; push(q); }
  }
  const A = new Float32Array(n);
  for (let k = n - 1; k >= 0; k--) { const c = reihenfolge[k]; if (H[c] > 0) A[c] += 1; if (ziel[c] >= 0) A[ziel[c]] += A[c]; }
  // Quellen: Fluss-Zellen, in die kein anderer Fluss mündet
  const zufluss = new Uint8Array(n);
  for (let i = 0; i < n; i++) if (A[i] > schwelle && ziel[i] >= 0) zufluss[ziel[i]] = 1;
  const besucht = new Uint8Array(n), netz = [];
  const quellen = [];
  for (let i = 0; i < n; i++) if (A[i] > schwelle && !zufluss[i] && H[i] > 0) quellen.push(i);
  quellen.sort((a, b) => H[b] - H[a]);
  for (const q of quellen) {
    const punkte = []; let c = q;
    while (c >= 0) {
      punkte.push([c % N, (c / N) | 0, A[c]]);
      if (H[c] <= 0 || (seeMaske && seeMaske[c])) break;   // Meer oder See erreicht
      if (besucht[c] && punkte.length > 1) break;           // Mündung in einen schon verfolgten Fluss
      besucht[c] = 1; c = ziel[c];
    }
    if (punkte.length > 2) netz.push({ punkte });
  }
  return netz;
}

// Flussbetten einschneiden: Tiefe wächst mit Einzugsgebiet
function flussbetten(H, N, A, schwelle) {
  const tief = new Float32Array(H.length);
  for (let i = 0; i < H.length; i++) {
    if (A[i] > schwelle && H[i] > 0) tief[i] = Math.min(4, 0.8 * Math.log2(A[i] / schwelle) + 1);
  }
  // Ufer weich: 2x verwischen
  for (let r = 0; r < 2; r++) {
    const t = new Float32Array(tief);
    for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
      const i = y * N + x;
      tief[i] = Math.max(t[i], (t[i - 1] + t[i + 1] + t[i - N] + t[i + N]) * 0.2);
    }
  }
  for (let i = 0; i < H.length; i++) H[i] -= tief[i];
}

// ---------- Biome ----------
// 0 Strand · 1 Wiese · 2 Laubwald · 3 Nadelwald · 4 Sumpf · 5 Steppe · 6 Fels · 7 Schnee  (= Textur-IDs in Terrain3D)
const BIOM_NAMEN = ["Strand", "Wiese", "Laubwald", "Nadelwald", "Sumpf", "Steppe", "Fels", "Schnee"];
const AUTO = 255;

// Abstand (Meter) jeder Zelle zum nächsten Wasser (Fluss oder Meer), Chamfer-Distanztransformation
function wasserabstand(H, A, N, zelle, schwelle) {
  const D = new Float32Array(N * N);
  const INF = 1e9, d1 = zelle, d2 = zelle * 1.4142;
  for (let i = 0; i < N * N; i++) D[i] = (H[i] <= 0 || (A[i] > schwelle && H[i] > 0)) ? 0 : INF;
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const i = y * N + x; let d = D[i];
    if (x > 0) d = Math.min(d, D[i - 1] + d1);
    if (y > 0) { d = Math.min(d, D[i - N] + d1); if (x > 0) d = Math.min(d, D[i - N - 1] + d2); if (x < N - 1) d = Math.min(d, D[i - N + 1] + d2); }
    D[i] = d;
  }
  for (let y = N - 1; y >= 0; y--) for (let x = N - 1; x >= 0; x--) {
    const i = y * N + x; let d = D[i];
    if (x < N - 1) d = Math.min(d, D[i + 1] + d1);
    if (y < N - 1) { d = Math.min(d, D[i + N] + d1); if (x < N - 1) d = Math.min(d, D[i + N + 1] + d2); if (x > 0) d = Math.min(d, D[i + N - 1] + d2); }
    D[i] = d;
  }
  return D;
}

// automatische Biome aus Höhe, Hangneigung und Feuchtigkeit
function biomeBerechnen(H, A, N, zelle, p, schwelle) {
  const nz = makeNoise((p.seed || 1) * 31 + 7);
  const D = wasserabstand(H, A, N, zelle, schwelle);
  const B = new Uint8Array(N * N);
  const felsTan = Math.tan(p.felsneigung * Math.PI / 180);
  const f = N * zelle / 4096;
  for (let y = 0; y < N; y++) {
    const v = y / N * f;
    for (let x = 0; x < N; x++) {
      const i = y * N + x, h = H[i], u = x / N * f;
      if (h <= 0) { B[i] = 0; continue; }
      const hl = H[i - (x > 0 ? 1 : 0)], hr = H[i + (x < N - 1 ? 1 : 0)], ho = H[i - (y > 0 ? N : 0)], hu = H[i + (y < N - 1 ? N : 0)];
      const steig = Math.hypot((hr - hl) / (2 * zelle), (hu - ho) / (2 * zelle));
      const n1 = 0.7 * nz.fbm(u * 9, v * 9, 4) + 0.3 * nz.fbm(u * 30 + 3, v * 30 + 7, 3), n2 = nz.fbm(u * 22 + 5, v * 22 + 9, 3);
      // Feuchtigkeit 0..1: Nähe zu Wasser, großes Einzugsgebiet, Rauschen, Regler
      let feuchte = 0.55 * Math.exp(-D[i] / 260) + 0.18 * Math.min(1, Math.log2(1 + A[i]) / 14) + 0.32 * (nz.fbm(u * 4 + 30, v * 4 + 10, 4) + 0.5) + 0.3 * p.feuchte - 0.1;
      feuchte -= Math.max(0, h - 60) / 900;
      let b;
      if (h > p.schneegrenze + 25 * n1) b = steig < felsTan * 1.4 ? 7 : 6;   // Schnee liegt auch auf steileren Gipfeln
      else if (steig > felsTan * (1 + 0.15 * n2)) b = 6;
      else if (h < 2.2 + 1.5 * n2 && steig < 0.3) b = 0;
      else if (h > p.baumgrenze + 30 * n1) b = (steig > felsTan * 0.6 || n2 > 0.25) ? 6 : 1;
      else if (feuchte > 0.66 && steig < 0.1 && h < 30) b = 4;
      else {
        const wald = (n1 * 0.9 + 0.5) + (feuchte - 0.5) * 0.7;
        const nadelfleck = nz.fbm(u * 5 + 70, v * 5 + 20, 3) > 0.1;
        if (wald > 1 - p.waldanteil) b = (h > p.nadelhoehe + 35 * n2 || nadelfleck) ? 3 : 2;
        else if (feuchte < 0.3) b = 5;
        else b = 1;
      }
      B[i] = b;
    }
  }
  // einzelne Ausreißer-Pixel entfernen (Mehrheitsfilter 3x3)
  const C = B.slice(), z = new Uint8Array(8);
  for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
    const i = y * N + x; if (H[i] <= 0) continue;
    z.fill(0);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) z[C[i + dy * N + dx]]++;
    let best = C[i]; for (let k = 0; k < 8; k++) if (z[k] > z[best]) best = k;
    if (z[best] >= 5) B[i] = best;
  }
  return B;
}

// Terrain3D-Steuerkarte (uint32 je Pixel): Basis-Textur, Overlay-Textur, Überblendung
function steuerkarte(E, N, M, seed, fortschritt) {
  const nz = makeNoise(seed + 4711);
  const out = new Uint32Array(M * M);
  const s = N / M, w = new Float32Array(8);
  for (let j = 0; j < M; j++) {
    if (fortschritt && (j & 63) === 0) fortschritt(j / M);
    for (let i = 0; i < M; i++) {
      // leicht verwackelte Abtastposition -> organische Biomgrenzen
      const u = i / M * N / 1024, v = j / M * N / 1024;
      const fx = (i + 0.5) * s - 0.5 + 1.3 * nz.fbm(u * 60, v * 60, 3);
      const fy = (j + 0.5) * s - 0.5 + 1.3 * nz.fbm(u * 60 + 9, v * 60 + 4, 3);
      // Gewichte aus 4x4 Nachbarzellen (Glockenkurve, Radius ~2 Zellen = 8 m) -> weiche Biomgrenzen
      const x0 = Math.floor(fx), y0 = Math.floor(fy);
      w.fill(0);
      for (let dy = -1; dy <= 2; dy++) for (let dx = -1; dx <= 2; dx++) {
        const xx = x0 + dx, yy = y0 + dy;
        const d2 = (xx - fx) * (xx - fx) + (yy - fy) * (yy - fy);
        if (d2 > 4) continue;
        w[E[Math.min(N - 1, Math.max(0, yy)) * N + Math.min(N - 1, Math.max(0, xx))]] += Math.exp(-d2 * 0.9);
      }
      let b1 = 0, b2 = -1;
      for (let k = 1; k < 8; k++) if (w[k] > w[b1]) b1 = k;
      for (let k = 0; k < 8; k++) if (k !== b1 && (b2 < 0 || w[k] > w[b2])) b2 = k;
      let blend = 0;
      if (w[b2] > 0) { const f = w[b2] / (w[b1] + w[b2]); blend = Math.round(255 * Math.min(1, f * 1.25)); }
      else b2 = b1;
      out[j * M + i] = (((b1 & 31) << 27) | ((b2 & 31) << 22) | ((blend & 255) << 14)) >>> 0;
    }
  }
  if (fortschritt) fortschritt(1);
  return out;
}

// ---------- Ressourcen verteilen ----------
// Marker-Typen, die Ressourcen freihalten (Radius in Metern kommt vom Marker)
const FREIHALTEN = { stadt: 1, dorf: 1, feld: 1, mine: 0.4, dungeon: 0.4, poi: 0.3 };

// Liefert { baeume:[[x,z,art,alter]], buesche:[[x,z]], erze:[[x,z,tier,groesse]], pflanzen:[[x,z,art,farbe]] }
// x/z in Metern, Weltmitte = 0 (wie in Godot). art/alter/tier/farbe = Enum-Werte der Godot-Skripte.
function ressourcenVerteilen(H, E, A, N, zelle, marker, p, schwelle, fortschritt) {
  const rnd = mulberry32((p.seed || 1) * 97 + 5);
  const nz = makeNoise((p.seed || 1) * 13 + 3);
  const welt = N * zelle, halb = welt / 2;
  // Sperrmaske aus Markern (Kreise bzw. gedrehte Rechtecke für Felder)
  const sperre = new Uint8Array(N * N);
  for (const m of marker) {
    const f = FREIHALTEN[m.typ]; if (!f) continue;
    if (m.typ === "feld") {
      const c = Math.cos(m.winkel || 0), s = Math.sin(m.winkel || 0), hw = m.breite / 2 / zelle + 2, hh = m.laenge / 2 / zelle + 2;
      const R = Math.ceil(Math.hypot(hw, hh));
      for (let y = Math.floor(m.y - R); y <= m.y + R; y++) for (let x = Math.floor(m.x - R); x <= m.x + R; x++) {
        if (x < 0 || y < 0 || x >= N || y >= N) continue;
        const dx = x - m.x, dy = y - m.y, u = dx * c + dy * s, v = -dx * s + dy * c;
        if (Math.abs(u) <= hw && Math.abs(v) <= hh) sperre[y * N + x] = 1;
      }
    } else {
      const r = m.radius * f / zelle;
      for (let y = Math.floor(m.y - r); y <= m.y + r; y++) for (let x = Math.floor(m.x - r); x <= m.x + r; x++) {
        if (x < 0 || y < 0 || x >= N || y >= N) continue;
        if ((x - m.x) ** 2 + (y - m.y) ** 2 <= r * r) sperre[y * N + x] = 1;
      }
    }
  }
  for (const w of (p.wege || [])) for (let k = 0; k < w.punkte.length; k++) {
    if (w.bruecke[k]) continue;
    const r = Math.ceil((w.breite / 2 + 2) / zelle), cx = Math.round(w.punkte[k][0]), cy = Math.round(w.punkte[k][1]);
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (x >= 0 && y >= 0 && x < N && y < N) sperre[y * N + x] = 1;
  }
  const D = wasserabstand(H, A, N, zelle, schwelle);
  const hmax = (() => { let m = 0; for (const h of H) if (h > m) m = h; return m; })();
  const steigung = (i, x, y) => {
    const hl = H[i - (x > 0 ? 1 : 0)], hr = H[i + (x < N - 1 ? 1 : 0)], ho = H[i - (y > 0 ? N : 0)], hu = H[i + (y < N - 1 ? N : 0)];
    return Math.hypot((hr - hl) / (2 * zelle), (hu - ho) / (2 * zelle));
  };
  const out = { baeume: [], buesche: [], erze: [], pflanzen: [] };
  // Abtastung: zufällige Punkte im Raster "abstand" (gestreutes Gitter = keine Klumpen, keine Reihen)
  function streuen(abstand, cb) {
    const n = Math.floor(welt / abstand);
    for (let gy = 0; gy < n; gy++) {
      if (fortschritt && (gy & 15) === 0) fortschritt(gy / n);
      for (let gx = 0; gx < n; gx++) {
        const wx = (gx + 0.1 + 0.8 * rnd()) * abstand, wz = (gy + 0.1 + 0.8 * rnd()) * abstand;
        const x = Math.floor(wx / zelle), y = Math.floor(wz / zelle);
        if (x < 1 || y < 1 || x >= N - 1 || y >= N - 1) continue;
        const i = y * N + x;
        if (H[i] < 0.6 || sperre[i] || D[i] < 3) continue;
        cb(wx - halb, wz - halb, i, x, y);
      }
    }
  }
  const dichte = (x, y, f) => 0.5 + 0.5 * nz.fbm(x / 1024 * f, y / 1024 * f, 3);   // 0..1 Lichtungen/Gruppen
  // Bäume (Abstand 7 m Grundraster)
  streuen(7 / Math.sqrt(Math.max(0.05, p.baumdichte)), (wx, wz, i, x, y) => {
    const b = E[i], st = steigung(i, x, y);
    if (st > 0.7) return;
    const d = dichte(x, y, 18);
    let chance = 0, art = 0;
    const r = rnd();
    if (b === 2) { chance = 0.55 + 0.45 * d; art = r < 0.7 ? 2 : 1; }                // Laubwald: Eiche, Kiefer
    else if (b === 3) { chance = 0.6 + 0.4 * d; art = r < 0.65 ? 0 : 1; }           // Nadelwald: Fichte, Kiefer
    else if (b === 1) { chance = 0.025 * d; art = r < 0.6 ? 2 : 1; }                // Wiese: vereinzelte Bäume
    else if (b === 4) { chance = 0.08; art = 1; }                                    // Sumpf: lichte Kiefern
    else if (b === 5) { chance = 0.01; art = 1; }
    if (rnd() > chance) return;
    out.baeume.push([+wx.toFixed(1), +wz.toFixed(1), art, rnd() < 0.62 ? 1 : 0]);
  });
  // Äste-Büsche: Waldränder, Wiese, Lichtungen
  streuen(14 / Math.sqrt(Math.max(0.05, p.buschdichte)), (wx, wz, i, x, y) => {
    const b = E[i]; let chance = 0;
    if (b === 2 || b === 3) chance = 0.35; else if (b === 1) chance = 0.12; else if (b === 4 || b === 5) chance = 0.06;
    if (steigung(i, x, y) < 0.6 && rnd() < chance) out.buesche.push([+wx.toFixed(1), +wz.toFixed(1)]);
  });
  // Erze: Fels und steile/hohe Hänge; Tier nach relativer Höhe (T1 tief … T6 Gipfel)
  streuen(36 / Math.sqrt(Math.max(0.05, p.erzdichte)), (wx, wz, i, x, y) => {
    const b = E[i], st = steigung(i, x, y), h = H[i];
    let chance = b === 6 || b === 7 ? 0.45 : (st > 0.35 ? 0.2 : (h > 40 ? 0.03 : 0.008));
    if (st > 1.2 || rnd() > chance) return;
    const groesse = 1 + Math.min(4, Math.floor(rnd() * rnd() * 5.5));      // kleine häufiger
    out.erze.push([+wx.toFixed(1), +wz.toFixed(1), h + (rnd() - 0.5) * 30, groesse]);   // Höhe vorerst, Tier unten
  });
  // Tier nach Höhen-Rang: die höchsten Fundorte = höchstes Tier (Anteile T1…T6)
  const ANTEIL = [0.30, 0.25, 0.18, 0.12, 0.09, 0.06];
  const sortiert = out.erze.map((e, k) => [e[2], k]).sort((a, b) => a[0] - b[0]);
  let grenze = 0, t = 0;
  sortiert.forEach(([, k], rang) => {
    while (t < 5 && rang >= (grenze + ANTEIL[t]) * sortiert.length) { grenze += ANTEIL[t]; t++; }
    out.erze[k][2] = t;
  });
  // Sammelpflanzen: Hanf (Wiese/Steppe nahe Wasser, in Gruppen), Beeren (Waldrand/Wiese), Kräuter (Wiese/Sumpf/Wald)
  streuen(16 / Math.sqrt(Math.max(0.05, p.pflanzendichte)), (wx, wz, i, x, y) => {
    const b = E[i]; if (steigung(i, x, y) > 0.5) return;
    const r = rnd(), nah = Math.exp(-D[i] / 150);
    if ((b === 1 || b === 5) && r < 0.05 + 0.25 * nah * dichte(x, y, 30)) {
      // Hanf wächst in kleinen Feldern: 3–6 Pflanzen
      const k = 3 + Math.floor(rnd() * 4);
      for (let n = 0; n < k; n++) out.pflanzen.push([+(wx + (rnd() - 0.5) * 6).toFixed(1), +(wz + (rnd() - 0.5) * 6).toFixed(1), 0, 0]);
    } else if ((b === 1 || b === 2) && r < 0.12) {
      out.pflanzen.push([+wx.toFixed(1), +wz.toFixed(1), 1, Math.floor(rnd() * 4)]);              // Beeren: rot/blau/schwarz/gelb
    } else if ((b === 1 || b === 4 || b === 2 || b === 3) && r < 0.32) {
      out.pflanzen.push([+wx.toFixed(1), +wz.toFixed(1), 2, [4, 3, 5, 0][Math.floor(rnd() * 4)]]); // Kräuter: weiß/gelb/lila/rot
    }
  });
  if (fortschritt) fortschritt(1);
  return out;
}

// Vorschläge: Felder um Dörfer/Städte auf flachem Land, Minen an Erzhängen
function vorschlaege(H, E, N, zelle, marker, seed) {
  const rnd = mulberry32(seed * 7 + 99);
  const neu = [];
  const flach = (x, y, r) => {
    let mn = Infinity, mx = -Infinity;
    for (let dy = -r; dy <= r; dy += 2) for (let dx = -r; dx <= r; dx += 2) {
      const xx = Math.round(x + dx), yy = Math.round(y + dy);
      if (xx < 0 || yy < 0 || xx >= N || yy >= N) return false;
      const i = yy * N + xx, b = E[i];
      if (H[i] < 1.5 || b === 4 || b === 6 || b === 7) return false;
      mn = Math.min(mn, H[i]); mx = Math.max(mx, H[i]);
    }
    return mx - mn < 10;
  };
  const belegt = (x, y, r) => marker.concat(neu).some((m) => Math.hypot(m.x - x, m.y - y) < r + (m.radius || Math.max(m.breite || 0, m.laenge || 0) / 2) / zelle);
  for (const m of marker) {
    if (m.typ !== "dorf" && m.typ !== "stadt") continue;
    const anzahl = m.typ === "stadt" ? 5 : 3;
    let gesetzt = 0;
    for (let v = 0; v < 400 && gesetzt < anzahl; v++) {
      const a = rnd() * Math.PI * 2, d = (m.radius / zelle) * (1.3 + rnd() * 2.2);
      const x = m.x + Math.cos(a) * d, y = m.y + Math.sin(a) * d;
      const breite = 40 + rnd() * 40, laenge = 60 + rnd() * 70;
      const r = Math.ceil(Math.max(breite, laenge) / 2 / zelle);
      if (!flach(x, y, r) || belegt(x, y, r * 0.8)) continue;
      neu.push({ typ: "feld", art: rnd() < 0.6 ? "weizen" : "gemuese", x, y, breite: +breite.toFixed(0), laenge: +laenge.toFixed(0), winkel: a + Math.PI / 2 + (rnd() - 0.5) * 0.5, name: "" });
      gesetzt++;
    }
  }
  // Minen: steile Hänge in Fels-Nähe, mit Abstand zueinander (6 je 8-km-Welt, bei größeren Welten mehr)
  const flaeche = (N * zelle / 8192) ** 2, maxMinen = Math.max(6, Math.round(6 * flaeche));
  const kand = [];
  for (let k = 0; k < 4000 * Math.max(1, flaeche); k++) {
    const x = 2 + Math.floor(rnd() * (N - 4)), y = 2 + Math.floor(rnd() * (N - 4)), i = y * N + x;
    if (E[i] !== 6 || H[i] < 40) continue;
    const st = Math.hypot(H[i + 1] - H[i - 1], H[i + N] - H[i - N]) / (2 * zelle);
    if (st > 0.35 && st < 1.0) kand.push([x, y, H[i]]);
  }
  kand.sort((a, b) => a[2] - b[2]);
  for (const [x, y] of kand) {
    if (neu.filter((m) => m.typ === "mine").length >= maxMinen) break;
    if (belegt(x, y, 480 / zelle)) continue;   // mind. 480 m zu anderen Markern
    neu.push({ typ: "mine", x, y, radius: 30, name: "" });
  }
  return neu;
}

// ---------- Wege & Straßen ----------
// Ergebnis: [{ typ: "strasse"|"weg", breite, punkte: [[x, y, h], …] (Zellen, Höhe m), bruecke: [bool je Punkt-Segment] }]
const WEG_BREITE = { strasse: 6, weg: 3 };

// p.sperre (optional): Uint8Array je Zelle, 1 = hier keine Wege (z. B. Zentralberg); Ziele darin bekommen keinen Weg
function wegeGenerieren(H, A, E, N, zelle, marker, p, schwelle, fortschritt) {
  const n = N * N, sperre = p.sperre || null;
  const fluss = new Uint8Array(n);
  for (let i = 0; i < n; i++) if (A[i] > schwelle && H[i] > 0) fluss[i] = 1;
  // Kostenfaktor je Zelle (Biom, Felder)
  const fak = new Float32Array(n);
  const BIOM_KOSTEN = [1.6, 1.0, 1.15, 1.15, 2.2, 1.0, 1.35, 1.6];
  for (let i = 0; i < n; i++) fak[i] = BIOM_KOSTEN[E[i]] || 1;
  for (const m of marker) if (m.typ === "feld") {
    const c = Math.cos(m.winkel), sn = Math.sin(m.winkel), hw = m.breite / 2 / zelle, hh = m.laenge / 2 / zelle, R = Math.ceil(Math.hypot(hw, hh));
    for (let y = Math.floor(m.y - R); y <= m.y + R; y++) for (let x = Math.floor(m.x - R); x <= m.x + R; x++) {
      if (x < 0 || y < 0 || x >= N || y >= N) continue;
      const dx = x - m.x, dy = y - m.y;
      if (Math.abs(dx * c + dy * sn) <= hw && Math.abs(-dx * sn + dy * c) <= hh) fak[y * N + x] = 4;
    }
  }
  const strasse = new Uint8Array(n);          // 1 = Straße, 2 = Weg (bereits gebaut -> billig)
  const brueckenEnden = new Map();            // Zelle -> [andere Brückenenden]: gebaute Brücken mitbenutzen
  const g = new Float32Array(n), von = new Int32Array(n), sprung = new Uint8Array(n), zu = new Uint8Array(n);
  const heap = new Int32Array(n * 2), hf = new Float32Array(n * 2);
  const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1], [2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [1, -2], [-1, 2], [-1, -2]];

  function pfad(start, ziel, typ) {
    const maxS = (typ === "strasse" ? p.strasse_steigung : p.weg_steigung) / 100;
    const maxL = Math.round(p.bruecke_max / zelle);
    g.fill(Infinity); zu.fill(0);
    const zx = ziel % N, zy = (ziel / N) | 0;
    let hs = 0;
    const push = (i, f) => {
      let k = hs++; heap[k] = i; hf[k] = f;
      while (k > 0) { const q = (k - 1) >> 1; if (hf[q] <= hf[k]) break; [heap[q], heap[k]] = [heap[k], heap[q]]; [hf[q], hf[k]] = [hf[k], hf[q]]; k = q; }
    };
    const pop = () => {
      const top = heap[0]; hs--; heap[0] = heap[hs]; hf[0] = hf[hs]; let k = 0;
      for (;;) { const l = 2 * k + 1, r = l + 1; let m = k;
        if (l < hs && hf[l] < hf[m]) m = l; if (r < hs && hf[r] < hf[m]) m = r;
        if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; [hf[m], hf[k]] = [hf[k], hf[m]]; k = m; }
      return top;
    };
    const heur = (i) => Math.hypot(i % N - zx, ((i / N) | 0) - zy) * 0.45;
    g[start] = 0; von[start] = -1; push(start, heur(start));
    let schritte = 0;
    while (hs > 0) {
      const a = pop();
      if (zu[a]) continue;
      zu[a] = 1;
      if (a === ziel) break;
      if (++schritte > 12000000) return null;
      const ax = a % N, ay = (a / N) | 0, ha = H[a];
      for (let d = 0; d < 16; d++) {
        const [dx, dy] = DIRS[d], bx = ax + dx, by = ay + dy;
        if (bx < 1 || by < 1 || bx >= N - 1 || by >= N - 1) continue;
        const b = by * N + bx;
        if (zu[b] || H[b] < 0.4 || (sperre && sperre[b])) continue;
        // Diagonale/Springer-Züge dürfen nicht zwischen Flusszellen "hindurchschlüpfen":
        // alle Zellen im Rechteck zwischen a und b prüfen
        if (d >= 4) {
          let nass = false;
          for (let yy = Math.min(ay, by); yy <= Math.max(ay, by) && !nass; yy++)
            for (let xx = Math.min(ax, bx); xx <= Math.max(ax, bx); xx++) {
              const q = yy * N + xx; if (q !== a && q !== b && (fluss[q] || H[q] < 0.4)) { nass = true; break; }
            }
          if (nass) continue;
        }
        const dist = Math.hypot(dx, dy);
        const st = Math.abs(H[b] - ha) / (dist * zelle);
        let c = dist * (fak[b] + (st / maxS) ** 2 * 2.5);
        if (st > maxS) c *= 1 + 25 * (st - maxS) / maxS;
        if (fluss[b]) c += 600;                                   // Furt nur im Notfall – Brücke bevorzugt
        if (strasse[b]) c *= strasse[b] === 1 ? 0.3 : (typ === "weg" ? 0.4 : 0.8);
        const ng = g[a] + c;
        if (ng < g[b]) { g[b] = ng; von[b] = a; sprung[b] = 0; push(b, ng + heur(b)); }
      }
      // bereits gebaute Brücke benutzen (billig)
      for (const b of brueckenEnden.get(a) || []) {
        if (zu[b]) continue;
        const ng = g[a] + Math.hypot(b % N - ax, ((b / N) | 0) - ay) * 0.5;
        if (ng < g[b]) { g[b] = ng; von[b] = a; sprung[b] = 1; push(b, ng + heur(b)); }
      }
      // Brücken: über Fluss oder Senke springen (nur wenn direkt daneben Wasser bzw. es deutlich abfällt)
      for (let d = 0; d < 8; d++) {
        const [dx, dy] = DIRS[d], nx = ax + dx, ny = ay + dy;
        if (nx < 1 || ny < 1 || nx >= N - 1 || ny >= N - 1) continue;
        const nb = ny * N + nx;
        if (!(fluss[nb] || H[nb] < ha - 2.5)) continue;
        let tiefMin = Infinity, ueberFluss = false;
        for (let L = 2; L <= maxL; L++) {
          const bx = ax + dx * L, by = ay + dy * L;
          if (bx < 1 || by < 1 || bx >= N - 1 || by >= N - 1) break;
          const zw = (by - dy) * N + (bx - dx);
          if (H[zw] < -1.5) break;                                  // nicht übers Meer
          tiefMin = Math.min(tiefMin, H[zw]); ueberFluss = ueberFluss || fluss[zw] === 1;
          const b = by * N + bx;
          if (zu[b] || H[b] < 0.4 || fluss[b] || (sperre && sperre[b])) continue;
          const len = L * Math.hypot(dx, dy) * zelle;
          if (Math.abs(H[b] - ha) > Math.max(2, len * maxS * 0.6)) continue;
          const deck = Math.min(ha, H[b]);
          if (!ueberFluss && deck - tiefMin < 5) continue;          // keine sinnlosen Brücken
          const c = (len / zelle) * 3.2 + 30;
          const ng = g[a] + c;
          if (ng < g[b]) { g[b] = ng; von[b] = a; sprung[b] = 1; push(b, ng + heur(b)); }
        }
      }
    }
    if (!zu[ziel]) return null;
    const zellen = [], br = [];
    for (let i = ziel; i >= 0; i = von[i]) { zellen.push(i); br.push(sprung[i]); }
    zellen.reverse(); br.reverse();
    return { zellen, br };   // br[k] = 1: Segment (k-1 -> k) ist eine Brücke
  }

  // Zellen als gebaut markieren (Korridor), damit spätere Wege die Strecke mitnutzen
  function markieren(zellen, br, typ) {
    const r = typ === "strasse" ? 1 : 0;
    for (let k = 1; k < zellen.length; k++) if (br[k]) {
      const a = zellen[k - 1], b = zellen[k];
      // Brückenenden (und direkte Nachbarn) verknüpfen, damit andere Strecken einfädeln
      for (const [p0, p1] of [[a, b], [b, a]]) for (const o of [0, 1, -1, N, -N]) {
        const q = p0 + o; if (!brueckenEnden.has(q)) brueckenEnden.set(q, []);
        brueckenEnden.get(q).push(p1);
      }
    }
    for (let k = 0; k < zellen.length; k++) {
      if (k > 0 && br[k]) continue;
      const x = zellen[k] % N, y = (zellen[k] / N) | 0;
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        const i = (y + dy) * N + x + dx;
        if (!strasse[i] || (typ === "strasse")) strasse[i] = typ === "strasse" ? 1 : (strasse[i] || 2);
      }
    }
  }

  const idx = (m) => Math.round(m.y) * N + Math.round(m.x);
  const siedlungen = marker.filter((m) => m.typ === "stadt" || m.typ === "dorf");
  const ziele = marker.filter((m) => (m.typ === "mine" || m.typ === "dungeon" || m.typ === "poi") && !(sperre && sperre[idx(m)]));
  // Verbindungen: minimaler Spannbaum über Siedlungen + Abkürzungen, wo der Umweg groß ist
  const kanten = [];
  if (siedlungen.length > 1) {
    const drin = [0], rest = siedlungen.map((_, k) => k).slice(1);
    const baum = [];
    while (rest.length) {
      let best = null;
      for (const a of drin) for (const b of rest) {
        const d = Math.hypot(siedlungen[a].x - siedlungen[b].x, siedlungen[a].y - siedlungen[b].y);
        if (!best || d < best[2]) best = [a, b, d];
      }
      baum.push(best); drin.push(best[1]); rest.splice(rest.indexOf(best[1]), 1);
    }
    kanten.push(...baum);
    // Graph-Abstände im Baum, um Abkürzungen zu finden
    const S = siedlungen.length, dist = Array.from({ length: S }, () => new Array(S).fill(Infinity));
    for (let k = 0; k < S; k++) dist[k][k] = 0;
    for (const [a, b, d] of baum) { dist[a][b] = d; dist[b][a] = d; }
    for (let k = 0; k < S; k++) for (let i = 0; i < S; i++) for (let j = 0; j < S; j++) dist[i][j] = Math.min(dist[i][j], dist[i][k] + dist[k][j]);
    const extra = [];
    for (let a = 0; a < S; a++) for (let b = a + 1; b < S; b++) {
      const d = Math.hypot(siedlungen[a].x - siedlungen[b].x, siedlungen[a].y - siedlungen[b].y);
      if (d * zelle < 1400 && dist[a][b] > d * (2.2 - p.extra)) extra.push([a, b, d]);
    }
    extra.sort((u, v) => u[2] - v[2]);
    kanten.push(...extra.slice(0, Math.round(S * p.extra)));
  }
  kanten.sort((u, v) => u[2] - v[2]);
  const wege = [];
  const gesamt = kanten.length + ziele.length;
  let fertig = 0;
  const melden = () => fortschritt && fortschritt(fertig / Math.max(1, gesamt));
  for (const [a, b] of kanten) {
    const r = pfad(idx(siedlungen[a]), idx(siedlungen[b]), "strasse");
    fertig++; melden();
    if (!r) continue;
    markieren(r.zellen, r.br, "strasse");
    wege.push({ typ: "strasse", ...r });
  }
  // Wege zu Minen, Dungeons, POIs: zum nächsten Punkt des Netzes bzw. zur nächsten Siedlung
  for (const m of ziele) {
    const start = idx(m);
    let ziel = -1, best = Infinity;
    for (const s2 of siedlungen) { const d = Math.hypot(s2.x - m.x, s2.y - m.y); if (d < best) { best = d; ziel = idx(s2); } }
    // näher gelegene Straßenzelle suchen (Ring-Suche bis 300 m)
    const mx = Math.round(m.x), my = Math.round(m.y), R = Math.round(300 / zelle);
    let bestS = Infinity;
    for (let dy = -R; dy <= R; dy += 2) for (let dx = -R; dx <= R; dx += 2) {
      const x = mx + dx, y = my + dy; if (x < 0 || y < 0 || x >= N || y >= N) continue;
      const i = y * N + x; if (strasse[i] !== 1) continue;
      const d = Math.hypot(dx, dy); if (d < bestS && d < best) { bestS = d; ziel = i; }
    }
    fertig++; melden();
    if (ziel < 0 || ziel === start) continue;
    const r = pfad(start, ziel, "weg");
    if (!r) continue;
    markieren(r.zellen, r.br, "weg");
    wege.push({ typ: "weg", ...r });
  }
  return wege.map((w) => glaetten(w, H, N, zelle, p)).filter((w) => w.punkte.length > 1);
}

// Zellpfad -> geglättete Linie mit Höhen; Brücken bleiben gerade
function glaetten(w, H, N, zelle, p) {
  const pts = w.zellen.map((i) => [i % N, (i / N) | 0]);
  // in Abschnitte teilen: Land / Brücke
  const teile = []; let akt = { br: false, pts: [pts[0]] };
  for (let k = 1; k < pts.length; k++) {
    const br = !!w.br[k];
    if (br !== akt.br) { teile.push(akt); akt = { br, pts: [pts[k - 1]] }; }
    akt.pts.push(pts[k]);
  }
  teile.push(akt);
  const punkte = [], bruecke = [];
  for (const t of teile) {
    let q = t.pts;
    if (!t.br) {
      q = vereinfachen(q, 0.9);
      for (let it = 0; it < 3; it++) q = chaikin(q);
      // Punkte auf ~4 m Abstand bringen
      const dicht = [q[0]];
      for (let k = 1; k < q.length; k++) {
        const [x0, y0] = dicht[dicht.length - 1], [x1, y1] = q[k], d = Math.hypot(x1 - x0, y1 - y0);
        if (d >= 1) { const nn = Math.max(1, Math.round(d)); for (let j = 1; j <= nn; j++) dicht.push([x0 + (x1 - x0) * j / nn, y0 + (y1 - y0) * j / nn]); }
      }
      q = dicht;
    }
    for (let k = 0; k < q.length; k++) {
      if (punkte.length && k === 0) continue;   // Verbindungspunkt nicht doppelt
      punkte.push([q[k][0], q[k][1], hoeheBilinear(H, N, q[k][0], q[k][1])]);
      bruecke.push(t.br && k > 0);
    }
  }
  // Höhen: Brücken linear zwischen den Enden, Land geglättet + Steigung begrenzt
  for (let k = 1; k < punkte.length; k++) if (bruecke[k]) {
    let e = k; while (e + 1 < punkte.length && bruecke[e + 1]) e++;
    const a = k - 1, h0 = punkte[a][2], h1 = punkte[e][2];
    let L = 0; const seg = [0];
    for (let j = a + 1; j <= e; j++) { L += Math.hypot(punkte[j][0] - punkte[j - 1][0], punkte[j][1] - punkte[j - 1][1]); seg.push(L); }
    for (let j = a + 1; j < e; j++) punkte[j][2] = h0 + (h1 - h0) * seg[j - a] / L;
    k = e;
  }
  const hs = punkte.map((q) => q[2]);
  for (let it = 0; it < 3; it++) for (let k = 1; k < punkte.length - 1; k++) if (!bruecke[k] && !bruecke[k + 1]) hs[k] = (hs[k - 1] + 2 * hs[k] + hs[k + 1]) / 4;
  const maxS = (w.typ === "strasse" ? p.strasse_steigung : p.weg_steigung) / 100 * 1.15;
  for (let pass = 0; pass < 2; pass++) {
    for (let k = 1; k < punkte.length; k++) { const d = Math.hypot(punkte[k][0] - punkte[k - 1][0], punkte[k][1] - punkte[k - 1][1]) * zelle; hs[k] = Math.min(Math.max(hs[k], hs[k - 1] - maxS * d), hs[k - 1] + maxS * d); }
    for (let k = punkte.length - 2; k >= 0; k--) { const d = Math.hypot(punkte[k][0] - punkte[k + 1][0], punkte[k][1] - punkte[k + 1][1]) * zelle; hs[k] = Math.min(Math.max(hs[k], hs[k + 1] - maxS * d), hs[k + 1] + maxS * d); }
  }
  punkte.forEach((q, k) => (q[2] = Math.max(0.4, hs[k])));
  return { typ: w.typ, breite: WEG_BREITE[w.typ], punkte: punkte.map((q) => q.map((v) => +v.toFixed(2))), bruecke };
}

function hoeheBilinear(H, N, x, y) {
  const x0 = Math.max(0, Math.min(N - 2, Math.floor(x))), y0 = Math.max(0, Math.min(N - 2, Math.floor(y))), tx = x - x0, ty = y - y0, i = y0 * N + x0;
  return H[i] * (1 - tx) * (1 - ty) + H[i + 1] * tx * (1 - ty) + H[i + N] * (1 - tx) * ty + H[i + N + 1] * tx * ty;
}
function vereinfachen(pts, tol) {
  if (pts.length < 3) return pts;
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1;
  const st = [[0, pts.length - 1]];
  while (st.length) {
    const [a, b] = st.pop(); let best = -1, bd = tol;
    const [ax, ay] = pts[a], [bx, by] = pts[b], L = Math.hypot(bx - ax, by - ay) || 1;
    for (let k = a + 1; k < b; k++) { const d = Math.abs((bx - ax) * (ay - pts[k][1]) - (ax - pts[k][0]) * (by - ay)) / L; if (d > bd) { bd = d; best = k; } }
    if (best >= 0) { keep[best] = 1; st.push([a, best], [best, b]); }
  }
  return pts.filter((_, k) => keep[k]);
}
function chaikin(pts) {
  if (pts.length < 3) return pts;
  const o = [pts[0]];
  for (let k = 0; k < pts.length - 1; k++) {
    const [x0, y0] = pts[k], [x1, y1] = pts[k + 1];
    o.push([0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1], [0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1]);
  }
  o.push(pts[pts.length - 1]);
  return o;
}

// Export: Straßen ins hochaufgelöste Gelände einarbeiten (Ebnen + Böschung) und Weg-Maske liefern
function wegeEinarbeiten(out, M, N, wege, fortschritt, welt = N * 4) {
  const s = M / N;                          // Pixel pro Zelle
  const mpp = welt / M;                     // Meter pro Pixel
  const maske = new Uint8Array(M * M);      // 0..255 = Anteil Weg-Textur
  const ziel = new Float32Array(M * M).fill(NaN), gew = new Float32Array(M * M);
  let nr = 0;
  for (const w of wege) {
    if (fortschritt) fortschritt(nr++ / wege.length);
    const hb = w.breite / 2, boe = w.typ === "strasse" ? 6 : 4;   // halbe Breite, Böschung (m bei 1 m/px)
    for (let k = 1; k < w.punkte.length; k++) {
      if (w.bruecke[k]) continue;
      const [x0, y0, h0] = w.punkte[k - 1], [x1, y1, h1] = w.punkte[k];
      const ax = x0 * s, ay = y0 * s, bx = x1 * s, by = y1 * s;
      const R = (hb + boe) / mpp;
      const minx = Math.max(0, Math.floor(Math.min(ax, bx) - R)), maxx = Math.min(M - 1, Math.ceil(Math.max(ax, bx) + R));
      const miny = Math.max(0, Math.floor(Math.min(ay, by) - R)), maxy = Math.min(M - 1, Math.ceil(Math.max(ay, by) + R));
      const dx = bx - ax, dy = by - ay, LL = dx * dx + dy * dy || 1;
      for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
        let t = ((x - ax) * dx + (y - ay) * dy) / LL; t = Math.max(0, Math.min(1, t));
        const d = Math.hypot(x - (ax + t * dx), y - (ay + t * dy)) * mpp;
        if (d > hb + boe) continue;
        const i = y * M + x, hz = h0 + (h1 - h0) * t;
        const wgt = d <= hb ? 1 : 1 - smoothstep(hb, hb + boe, d);
        if (wgt > gew[i] || (wgt === gew[i] && (isNaN(ziel[i]) || hz > ziel[i]))) { gew[i] = wgt; ziel[i] = hz; }
        const mk = d <= hb - 0.5 ? 255 : Math.round(255 * (1 - smoothstep(hb - 0.5, hb + 1.2, d)));
        if (mk > maske[i]) maske[i] = mk;
      }
    }
  }
  for (let i = 0; i < M * M; i++) if (gew[i] > 0) out[i] = out[i] + (ziel[i] - 0.05 - out[i]) * gew[i];
  if (fortschritt) fortschritt(1);
  return maske;
}

// Weg-Textur (ID 8) in die Steuerkarte mischen
function wegInSteuerkarte(st, maske, nz) {
  for (let i = 0; i < st.length; i++) {
    const m = maske[i]; if (!m) continue;
    const alt = st[i] >>> 0, basis = (alt >>> 27) & 31;
    if (m >= 250) st[i] = ((8 << 27) | (8 << 22)) >>> 0;
    else st[i] = (((basis & 31) << 27) | (8 << 22) | ((m & 255) << 14)) >>> 0;
  }
}

// ---------- Landschaft überarbeiten: Hochebenen, Bergrücken mit Pässen, Seen und Flüsse in Tälern ----------
// Vorbild New World: Hochebenen je Schwierigkeitsstufe, Regionen durch Bergrücken getrennt (Pässe und Flussdurchbrüche
// bleiben offen), wenige Flüsse in Tälern, geschwungen, mit Seen unterwegs. Arbeitet auf einer fertigen Karte
// (Höhen, Regionen, Seen) und lässt Küste, Zentralberg und Siedlungen in Ruhe.
// Wasser schwebt nie: der Wasserspiegel liegt überall unter dem Ufer quer über die ganze Flussbreite.

const FLUSS_KM2 = 0.6;   // Einzugsgebiet, ab dem ein Fluss beginnt (km²)

// Abstand in Metern zur nächsten Zelle mit quelle[i] (Chamfer 3-4, zwei Durchläufe)
function abstandMeter(N, zelle, quelle) {
  const D = new Float32Array(N * N), INF = 1e9, d1 = zelle, d2 = zelle * 1.4142;
  for (let i = 0; i < N * N; i++) D[i] = quelle[i] ? 0 : INF;
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const i = y * N + x; let d = D[i];
    if (x > 0) d = Math.min(d, D[i - 1] + d1);
    if (y > 0) { d = Math.min(d, D[i - N] + d1); if (x > 0) d = Math.min(d, D[i - N - 1] + d2); if (x < N - 1) d = Math.min(d, D[i - N + 1] + d2); }
    D[i] = d;
  }
  for (let y = N - 1; y >= 0; y--) for (let x = N - 1; x >= 0; x--) {
    const i = y * N + x; let d = D[i];
    if (x < N - 1) d = Math.min(d, D[i + 1] + d1);
    if (y < N - 1) { d = Math.min(d, D[i + N] + d1); if (x < N - 1) d = Math.min(d, D[i + N + 1] + d2); if (x > 0) d = Math.min(d, D[i + N - 1] + d2); }
    D[i] = d;
  }
  return D;
}

// Abflussrichtung (Priority-Flood über gefüllte Höhen) und Einzugsgebiet in Zellen
function abfluss(H, N) {
  const n = N * N, F = new Float32Array(H), fertig = new Uint8Array(n), ziel = new Int32Array(n).fill(-1), reihenfolge = new Int32Array(n);
  const heap = new Int32Array(n); let hs = 0, rk = 0;
  const push = (i) => { let k = hs++; heap[k] = i; while (k > 0) { const p = (k - 1) >> 1; if (F[heap[p]] <= F[heap[k]]) break; const t = heap[p]; heap[p] = heap[k]; heap[k] = t; k = p; } };
  const pop = () => { const top = heap[0]; heap[0] = heap[--hs]; let k = 0;
    for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < hs && F[heap[l]] < F[heap[m]]) m = l; if (r < hs && F[heap[r]] < F[heap[m]]) m = r; if (m === k) break; const t = heap[m]; heap[m] = heap[k]; heap[k] = t; k = m; }
    return top; };
  for (let i = 0; i < N; i++) for (const c of [i, (N - 1) * N + i, i * N, i * N + N - 1]) if (!fertig[c]) { fertig[c] = 1; push(c); }
  const nb = [1, -1, N, -N, N + 1, N - 1, -N + 1, -N - 1];
  while (hs > 0) {
    const c = pop(); reihenfolge[rk++] = c; const cx = c % N;
    for (const o of nb) { const q = c + o; if (q < 0 || q >= n || fertig[q] || Math.abs((q % N) - cx) > 1) continue;
      fertig[q] = 1; if (F[q] <= F[c]) F[q] = F[c] + 1e-3; ziel[q] = c; push(q); }
  }
  const A = new Float32Array(n);
  for (let k = n - 1; k >= 0; k--) { const c = reihenfolge[k]; if (H[c] > 0) A[c] += 1; if (ziel[c] >= 0) A[ziel[c]] += A[c]; }
  return { A, ziel };
}

const bilinear = (H, N, x, y) => {
  x = Math.min(N - 1.001, Math.max(0, x)); y = Math.min(N - 1.001, Math.max(0, y));
  const x0 = x | 0, y0 = y | 0, fx = x - x0, fy = y - y0, i = y0 * N + x0;
  return H[i] * (1 - fx) * (1 - fy) + H[i + 1] * fx * (1 - fy) + H[i + N] * (1 - fx) * fy + H[i + N + 1] * fx * fy;
};

// Schutzfaktor 0..1 um Siedlungen und Felder (0 = nicht verändern)
function schutzFeld(N, zelle, schutz) {
  const S = new Float32Array(N * N).fill(1);
  for (const m of schutz || []) {
    const r0 = (m.r + 40) / zelle, r1 = (m.r + 260) / zelle;
    for (let y = Math.max(0, Math.floor(m.y - r1)); y <= Math.min(N - 1, Math.ceil(m.y + r1)); y++)
      for (let x = Math.max(0, Math.floor(m.x - r1)); x <= Math.min(N - 1, Math.ceil(m.x + r1)); x++) {
        const d = Math.hypot(x - m.x, y - m.y), i = y * N + x;
        S[i] = Math.min(S[i], smoothstep(r0, r1, d));
      }
  }
  return S;
}

// Schmale Rinnen auffüllen: alte eingeschnittene Flussbetten („Flussbetten einschneiden“), Erosionsrillen an Bächen und
// schmale Meeresarme an der Küste (Schließen = Maximum-, dann Minimumfilter über ~60 m). Seen bleiben unberührt.
function rinnenFuellen(H, N, zelle, SEE) {
  const n = N * N, r = Math.max(2, Math.round(28 / zelle));
  // Max-/Min-Filter über ein Achteck (abwechselnd 3x3-Quadrat und Kreuz), damit keine eckigen Ränder entstehen
  const filter = (Q, max) => {
    let A = Float32Array.from(Q);
    for (let k = 0; k < r; k++) {
      const B = new Float32Array(n), quadrat = k % 2 === 0;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const i = y * N + x; let m = A[i];
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if ((!quadrat && dx && dy) || x + dx < 0 || y + dy < 0 || x + dx >= N || y + dy >= N) continue;
          const v = A[i + dy * N + dx]; m = max ? Math.max(m, v) : Math.min(m, v);
        }
        B[i] = m;
      }
      A = B;
    }
    return A;
  };
  const C = filter(filter(H, true), false);
  // nur an Wasserläufen (auch kleinen) und an der Küste, nie in oder dicht an Seen
  const { A } = abfluss(H, N), bach = 1500 * (4 / zelle) ** 2, quelle = new Uint8Array(n);
  for (let i = 0; i < n; i++) if ((A[i] > bach && H[i] > 0) || Math.abs(H[i]) < 4) quelle[i] = 1;
  const nahBach = abstandMeter(N, zelle, quelle), see = SEE ? abstandMeter(N, zelle, SEE) : null;
  let gefuellt = 0;
  for (let i = 0; i < n; i++) {
    if (nahBach[i] > 40 || (see && see[i] < 3 * zelle)) continue;
    const neu = Math.min(C[i], H[i] + 6);
    if (neu > H[i] + 0.2) { H[i] = neu; gefuellt++; }
  }
  return gefuellt;
}

// Hochebenen: Höhen werden zu Stufen zusammengeschoben (monoton, es entstehen keine neuen Senken).
// Die Stufenhöhen wandern mit grobem Rauschen, damit keine Ringe um den Berg entstehen.
function hochebenen(H, N, zelle, seed, meer, seeNah, berg, staerke) {
  const nz = makeNoise(seed * 13 + 5), f = N * zelle / 4096;
  const STUFEN = [0, 12, 28, 50, 78, 112, 152, 200, 260, 330, 420, 1e4];
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const i = y * N + x, h = H[i];
    if (h <= 1.5) continue;
    const u = x / N * f, v = y / N * f;
    const w = staerke * smoothstep(60, 260, meer[i]) * smoothstep(120, 380, seeNah[i]) * (1 - smoothstep(170, 250, h)) * smoothstep(150, 700, berg[i]) *
      (0.55 + 0.45 * smoothstep(-0.3, 0.3, nz.fbm(u * 3 + 4, v * 3 + 1, 3)));
    if (w <= 0.01) continue;
    const j = 0.3 * nz.fbm(u * 2 + 9, v * 2 + 3, 3);   // Stufen verschieben (Anteil eines Abstands, höchstens 60 m)
    const stufe = (k) => STUFEN[k] + j * Math.min(60, STUFEN[k + 1] - STUFEN[k]);
    let k = 0; while (k < STUFEN.length - 3 && h >= stufe(k + 1)) k++;
    const a = stufe(k), b = stufe(k + 1);
    if (h >= b || h <= a) continue;
    const t = (h - a) / (b - a);
    H[i] = a + (b - a) * (t + w * (smoothstep(0.3, 0.7, t) - t));
  }
}

// Bergrücken auf den Regionsgrenzen. Offen bleiben: Pässe (1–3 je Grenze, an der tiefsten Stelle beginnend),
// Flussdurchbrüche, Küste, Seen, Zentralberg und Siedlungen.
function grateAnlegen(H, N, zelle, REG, A, T, seed, meer, seeNah, S) {
  const nz = makeNoise(seed * 17 + 3), rnd = mulberry32(seed * 3 + 1), f = N * zelle / 4096;
  const istRegion = (r) => r >= 1 && r < 250;
  const grenze = new Uint8Array(N * N), paare = new Map();
  for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
    const i = y * N + x, r = REG[i]; if (!istRegion(r)) continue;
    for (const j of [i + 1, i + N]) { const q = REG[j];
      if (istRegion(q) && q !== r) { grenze[i] = 1; const k = Math.min(r, q) * 256 + Math.max(r, q);
        (paare.get(k) || paare.set(k, []).get(k)).push(i); } }
  }
  const pass = new Uint8Array(N * N); let paesse = 0;
  for (const zellen of paare.values()) {
    const laenge = zellen.length * zelle, anzahl = Math.min(3, 1 + Math.floor(laenge / 3500));
    if (laenge < 300) continue;
    const gewaehlt = [];
    // erster Pass an der tiefsten Stelle (natürlicher Sattel), weitere möglichst weit weg
    let best = zellen[0]; for (const i of zellen) if (H[i] < H[best] && meer[i] > 400) best = i;
    gewaehlt.push(best);
    while (gewaehlt.length < anzahl) {
      let bi = -1, bd = -1;
      for (let t = 0; t < 400; t++) { const i = zellen[(rnd() * zellen.length) | 0]; if (meer[i] < 400) continue;
        const d = Math.min(...gewaehlt.map((g) => Math.hypot((g % N) - (i % N), ((g / N) | 0) - ((i / N) | 0))));
        if (d > bd) { bd = d; bi = i; } }
      if (bi < 0 || bd * zelle < 900) break; gewaehlt.push(bi);
    }
    for (const g of gewaehlt) { pass[g] = 1; paesse++; }
  }
  const fluss = new Uint8Array(N * N); for (let i = 0; i < N * N; i++) if (A[i] > T * 0.3 && H[i] > 0) fluss[i] = 1;
  const dG = abstandMeter(N, zelle, grenze), dP = abstandMeter(N, zelle, pass), dF = abstandMeter(N, zelle, fluss);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const i = y * N + x; if (dG[i] > 400 || H[i] <= 1.5 || !istRegion(REG[i])) continue;
    const u = x / N * f, v = y / N * f;
    const breite = 120 * (0.75 + 0.5 * (nz.fbm(u * 6, v * 6, 3) + 0.5));
    const hoehe = 48 * (0.55 + 0.9 * nz.ridged(u * 14 + 3, v * 14 + 7, 4));
    const g = Math.exp(-((dG[i] / breite) ** 2)) * smoothstep(90, 300, dP[i]) * smoothstep(50, 190, dF[i]) *
      smoothstep(150, 550, meer[i]) * smoothstep(80, 300, seeNah[i]) * S[i];
    H[i] += hoehe * g;
  }
  return paesse;
}

// Neue Seen auf den Flussläufen in flachem Gelände: Mulde absenken, Ufer leicht anheben, Abfluss flussabwärts.
function seenAnlegen(H, N, zelle, SEE, seen, A, ziel, T, REG, S, meer, anzahl, seed) {
  const rnd = mulberry32(seed * 11 + 7), nz = makeNoise(seed * 19 + 2);
  const steig = (x, y) => Math.max(Math.abs(H[y * N + x - 6] - H[y * N + x + 6]), Math.abs(H[(y - 6) * N + x] - H[(y + 6) * N + x])) / (12 * zelle);
  const kandidaten = [];
  for (let y = 12; y < N - 12; y += 3) for (let x = 12; x < N - 12; x += 3) {
    const i = y * N + x;
    if (A[i] < T * 1.5 || SEE[i] || H[i] < 5 || H[i] > 220 || meer[i] < 450 || S[i] < 1 || (REG && REG[i] >= 250)) continue;
    if (steig(x, y) > 0.035) continue;
    kandidaten.push(i);
  }
  let neu = 0;
  for (let versuch = 0; versuch < anzahl * 6 && neu < anzahl && kandidaten.length; versuch++) {
    const c = kandidaten.splice((rnd() * kandidaten.length) | 0, 1)[0], cx = c % N, cy = (c / N) | 0;
    if (seen.some((o) => Math.hypot(o.x - cx, o.y - cy) * zelle < 1800)) continue;
    const R = (130 + 150 * rnd()) / zelle, tiefe = 4 + 6 * rnd();
    // Richtung des Abflusses: dem Wasser folgen, bis es den Seerand verlässt; der See wird in dieser Richtung länger
    let o = c; for (let k = 0; k < 400 && ziel[o] >= 0 && Math.hypot((o % N) - cx, ((o / N) | 0) - cy) < R * 1.25; k++) o = ziel[o];
    const ax0 = (o % N) - cx, ay0 = ((o / N) | 0) - cy, al = Math.hypot(ax0, ay0) || 1, ax = ax0 / al, ay = ay0 / al;
    const r1 = Math.ceil(R * 2.2), zellen = [];
    for (let y = cy - r1; y <= cy + r1; y++) for (let x = cx - r1; x <= cx + r1; x++) {
      if (x < 1 || y < 1 || x >= N - 1 || y >= N - 1) continue;
      const t = (x - cx) * ax + (y - cy) * ay, q = (x - cx) * ay - (y - cy) * ax, d = Math.hypot(t / 1.45, q);
      if (d > r1) continue;
      const w = Math.atan2(q, t), Rt = R * (1 + 0.35 * nz.fbm(Math.cos(w) * 1.6 + c % 97, Math.sin(w) * 1.6, 3));
      zellen.push([y * N + x, d, Rt]);
    }
    // Wasserspiegel = tiefste Stelle des Rings ums Ufer: so staut der See nichts auf und läuft dort über, wo der Fluss weiterfließt
    let ring = Infinity; for (const [i, d, Rt] of zellen) if (d > Rt * 1.05 && d < Rt * 1.3) ring = Math.min(ring, H[i]);
    const level = ring - 0.2;
    if (!(level > 2)) continue;
    const alt = [];
    for (const [i, d, Rt] of zellen) {
      alt.push(i, H[i]);
      if (d < Rt) H[i] = Math.min(H[i], Math.max(level - tiefe * Math.pow(1 - (d / Rt) ** 2, 0.7), 1.2));
      else if (d < Rt * 1.35) H[i] = Math.min(H[i], level + 0.2 + (d - Rt) * zelle * 0.12);   // flaches Ufer
    }
    const see = seeFuellenH(H, N, zelle, cx, cy, Math.round(Math.PI * (R * 2.2) ** 2));
    if (see && see.tiefe >= 2 && see.flaeche >= 0.3 * Math.PI * (R * zelle) ** 2) {
      seen.push({ x: see.x, y: see.y, spiegel: +see.spiegel.toFixed(2), flaeche: Math.round(see.flaeche), tiefe: +see.tiefe.toFixed(1) });
      for (const i of see.zellen) SEE[i] = seen.length;
      neu++;
    } else for (let k = 0; k < alt.length; k += 2) H[alt[k]] = alt[k + 1];   // hält kein Wasser -> zurück
  }
  return neu;
}

// wie seeFuellen() in regionen.js, aber auf einem übergebenen Höhenfeld
function seeFuellenH(H, N, zelle, cx, cy, maxZellen) {
  let start = Math.round(cy) * N + Math.round(cx);
  for (let y = Math.round(cy) - 20; y <= Math.round(cy) + 20; y++) for (let x = Math.round(cx) - 20; x <= Math.round(cx) + 20; x++) if (H[y * N + x] < H[start]) start = y * N + x;
  const besucht = new Uint8Array(N * N), heap = [start], innen = [];
  const hoch = (k) => { while (k > 0) { const p = (k - 1) >> 1; if (H[heap[p]] <= H[heap[k]]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
  const runter = () => { let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && H[heap[l]] < H[heap[m]]) m = l; if (r < heap.length && H[heap[r]] < H[heap[m]]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } };
  besucht[start] = 1;
  let spiegel = H[start];
  while (heap.length) {
    const c = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; runter(); }
    if (H[c] < spiegel - 0.01 || H[c] <= 1.5) break;
    if (innen.length >= maxZellen) { spiegel = H[c]; break; }
    spiegel = Math.max(spiegel, H[c]); innen.push(c);
    const x = c % N;
    for (const j of [c - 1, c + 1, c - N, c + N]) if (j >= 0 && j < N * N && !besucht[j] && Math.abs((j % N) - x) <= 1) { besucht[j] = 1; heap.push(j); hoch(heap.length - 1); }
  }
  spiegel -= 0.3;
  const zellen = innen.filter((i) => H[i] < spiegel);
  if (!zellen.length) return null;
  let sx = 0, sy = 0; for (const i of zellen) { sx += i % N; sy += (i / N) | 0; }
  return { x: Math.round(sx / zellen.length), y: Math.round(sy / zellen.length), spiegel, zellen, flaeche: zellen.length * zelle * zelle, tiefe: spiegel - H[start] };
}

// Flussläufe: Stämme (Hauptlauf bis zur Mündung, Nebenflüsse enden am Hauptlauf), geglättet und geschwungen,
// Tal und Flussbett eingeschnitten. Ergebnis: liste [{punkte [[x, y, Wasserspiegel, Breite]] (Zellen, m)}], FM (nass = 1)
function flussLaeufe(H, N, zelle, SEE, seen, T, seed, S) {
  const n = N * N, { A, ziel } = abfluss(H, N), rnd = mulberry32(seed * 23 + 9), nz = makeNoise(seed * 29 + 4);
  const fluss = (i) => A[i] >= T && H[i] > 0 && !SEE[i];
  // Hauptzufluss je Zelle: der Zufluss mit dem größten Einzugsgebiet
  const haupt = new Int32Array(n).fill(-1), hatZufluss = new Uint8Array(n);
  for (let i = 0; i < n; i++) if (fluss(i) && ziel[i] >= 0) { const d = ziel[i]; hatZufluss[d] = 1; if (haupt[d] < 0 || A[i] > A[haupt[d]]) haupt[d] = i; }
  const stamm = new Int32Array(n).fill(-1), staemme = [];
  for (let s = 0; s < n; s++) {
    if (!fluss(s) || hatZufluss[s]) continue;
    const zellen = []; let c = s, ende = "meer", muendung = -1;
    for (;;) {
      zellen.push(c); stamm[c] = staemme.length;
      const d = ziel[c];
      if (d < 0 || H[d] <= 0) { ende = "meer"; if (d >= 0) zellen.push(d); break; }
      if (SEE[d]) { ende = "see"; muendung = SEE[d] - 1; zellen.push(d); break; }
      if (haupt[d] !== c) { ende = "fluss"; muendung = d; zellen.push(d); break; }
      c = d;
    }
    // Start an einem See? (Zelle flussaufwärts liegt im See)
    let vonSee = -1; for (const o of [1, -1, N, -N, N + 1, N - 1, -N + 1, -N - 1]) { const q = s + o; if (q >= 0 && q < n && ziel[q] === s && SEE[q]) vonSee = SEE[q] - 1; }
    staemme.push({ zellen, ende, muendung, vonSee, aEnde: A[zellen[zellen.length - 1]] || A[zellen[zellen.length - 2]] });
  }
  // Reihenfolge: große zuerst, damit Hauptläufe fertig sind, bevor Nebenflüsse an sie anschließen
  const ordnung = staemme.map((_, k) => k).sort((a, b) => staemme[b].aEnde - staemme[a].aEnde);
  const fertig = new Array(staemme.length).fill(null), laeufe = [];
  const breiteVon = (a) => Math.min(24, 11 + 4 * Math.log2(Math.max(1, a / T)));        // sichtbar nass (m)
  const tiefeVon = (a) => Math.min(2.4, 0.9 + 0.45 * Math.log2(Math.max(1, a / T)));
  const tVon = (a) => Math.min(20, 5 + 4 * Math.log2(Math.max(1, a / T)));              // Taltiefe (m)
  for (const k of ordnung) {
    const st = staemme[k];
    if (st.ende === "fluss") { const p = stamm[st.muendung]; if (p < 0 || !fertig[p]) continue; }
    const laenge = st.zellen.length * zelle;
    if (st.vonSee < 0 && st.ende === "fluss" && laenge < 450) continue;
    if (st.vonSee < 0 && laenge < 300) continue;
    // 1) Punkte alle ~zelle Meter (in Zellen), dann glätten (Enden fest)
    let P = st.zellen.map((i) => [i % N + 0.5, ((i / N) | 0) + 0.5, A[i] || st.aEnde]);
    for (let r = 0; r < 40; r++) { const Q = P.map((p) => p.slice());
      for (let i = 1; i < P.length - 1; i++) { Q[i][0] = (P[i - 1][0] + 2 * P[i][0] + P[i + 1][0]) / 4; Q[i][1] = (P[i - 1][1] + 2 * P[i][1] + P[i + 1][1]) / 4; } P = Q; }
    // 2) feiner abtasten (halbe Zelle) und schwingen lassen
    const F = [];
    for (let i = 0; i < P.length - 1; i++) { const a = P[i], b = P[i + 1], l = Math.hypot(b[0] - a[0], b[1] - a[1]), m = Math.max(1, Math.ceil(l / 0.5));
      for (let j = 0; j < m; j++) { const t = j / m; F.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]); } }
    F.push(P[P.length - 1].slice());
    const s = [0]; for (let i = 1; i < F.length; i++) s.push(s[i - 1] + Math.hypot(F[i][0] - F[i - 1][0], F[i][1] - F[i - 1][1]) * zelle);
    const L = s[s.length - 1];
    // Gefälle entlang des Laufs, über ~150 m gemittelt (steile Strecken schwingen weniger, aber ohne Sprünge)
    const flach = new Float64Array(F.length);
    for (let i = 0; i < F.length; i++) {
      const x = F[i][0] | 0, y = F[i][1] | 0, j = Math.min(N - 3, Math.max(2, y)) * N + Math.min(N - 3, Math.max(2, x));
      flach[i] = 1 - smoothstep(0.02, 0.09, Math.hypot(H[j + 2] - H[j - 2], H[j + 2 * N] - H[j - 2 * N]) / (4 * zelle));
    }
    for (let r = 0, b = Math.max(1, Math.round(75 / (zelle * 0.5))); r < 3; r++) {
      const c = Float64Array.from(flach), sum = new Float64Array(F.length + 1);
      for (let i = 0; i < F.length; i++) sum[i + 1] = sum[i] + c[i];
      for (let i = 0; i < F.length; i++) { const a = Math.max(0, i - b), e = Math.min(F.length, i + b + 1); flach[i] = (sum[e] - sum[a]) / (e - a); }
    }
    let phase = rnd() * 6.283; const versatz = new Float64Array(F.length);
    for (let i = 0; i < F.length; i++) {
      const W = breiteVon(F[i][2]), lambda = 14 * W + 90;
      if (i) phase += (s[i] - s[i - 1]) / lambda * 6.283 * (1 + 0.4 * nz.noise(s[i] / 300 + k * 7.1, 0.5));
      const huelle = Math.min(1, s[i] / lambda, (L - s[i]) / lambda);
      versatz[i] = 0.13 * lambda * (0.15 + 0.85 * flach[i]) * huelle * (0.6 + 0.4 * nz.noise(s[i] / 500 + k * 3.3, 4.5)) * Math.sin(phase) / zelle;
    }
    const G = F.map((p, i) => { const a = F[Math.max(0, i - 4)], b = F[Math.min(F.length - 1, i + 4)];
      const tx = b[0] - a[0], ty = b[1] - a[1], tl = Math.hypot(tx, ty) || 1;
      return [p[0] - ty / tl * versatz[i], p[1] + tx / tl * versatz[i], p[2]]; });
    // Anschluss an den Hauptlauf: Endpunkt auf dessen nächsten Punkt legen
    let bodenEnde = 0.15, endPunkt = null, anschluss = null;
    if (st.ende === "fluss") {
      const p = fertig[stamm[st.muendung]], mx = st.muendung % N + 0.5, my = ((st.muendung / N) | 0) + 0.5;
      let bi = 0, bd = Infinity; p.punkte.forEach((q, i) => { const d = (q[0] - mx) ** 2 + (q[1] - my) ** 2; if (d < bd) { bd = d; bi = i; } });
      endPunkt = p.punkte[bi]; anschluss = [p, bi];
    } else if (st.ende === "see") bodenEnde = seen[st.muendung].spiegel;
    if (endPunkt) { const e = G[G.length - 1], n0 = Math.max(1, Math.round(40 / (zelle * 0.5)));
      for (let i = Math.max(0, G.length - n0); i < G.length; i++) { const t = (i - (G.length - n0)) / n0; G[i][0] += (endPunkt[0] - e[0]) * t * t; G[i][1] += (endPunkt[1] - e[1]) * t * t; } }
    // Kurven nicht enger als das 1,8-Fache der halben Wasserfläche (sonst überlappt das Wasser sich selbst)
    for (let runde = 0, eng = 1; runde < 120 && eng; runde++) {
      eng = 0;
      for (let i = 6; i < G.length - 6; i++) {
        const a = G[i - 6], b = G[i], c = G[i + 6];
        const ab = Math.hypot(a[0] - b[0], a[1] - b[1]), bc = Math.hypot(b[0] - c[0], b[1] - c[1]), ac = Math.hypot(a[0] - c[0], a[1] - c[1]);
        const fl = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]));
        const R = fl > 1e-9 ? ab * bc * ac / (2 * fl) * zelle : Infinity, Rmin = 1.8 * (breiteVon(b[2]) / 2 + zelle);
        if (R >= Rmin) continue;
        eng++;
        let mx = 0, my = 0; for (let j = i - 3; j <= i + 3; j++) { mx += G[j][0]; my += G[j][1]; }
        b[0] += (mx / 7 - b[0]) * 0.6; b[1] += (my / 7 - b[1]) * 0.6;
      }
    }
    // auf ~4 m ausdünnen (Export und Einschneiden)
    const punkte = [];
    for (let i = 0; i < G.length; i++) punkte.push([G[i][0], G[i][1], 0, breiteVon(G[i][2]), G[i][2]]);
    fertig[k] = { punkte, st, bodenEnde, anschluss, startSpiegel: st.vonSee >= 0 ? seen[st.vonSee].spiegel : null };
    laeufe.push(fertig[k]);
  }
  // kurze Stummel (z. B. ein paar Meter zwischen zwei Seezellen) weglassen, sofern kein anderer Fluss an ihnen hängt
  const angeschlossen = new Set(laeufe.filter((l) => l.anschluss).map((l) => l.anschluss[0]));
  for (let k = laeufe.length - 1; k >= 0; k--) {
    const l = laeufe[k], P = l.punkte; let L = 0;
    for (let i = 1; i < P.length; i++) L += Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]) * zelle;
    if (L < 200 && !angeschlossen.has(l) && !(l.st.vonSee >= 0 && l.st.ende === "meer")) laeufe.splice(k, 1);
  }
  // 3) nächster Flusspunkt je Zelle (Vektor-Ausbreitung von fein gerasterten Punkten)
  const NX = new Float32Array(n).fill(-1e6), NY = new Float32Array(n).fill(-1e6), NL = new Int32Array(n).fill(-1), NP = new Int32Array(n).fill(-1);
  const nah = new Float32Array(n).fill(1e9);
  laeufe.forEach((l, li) => l.punkte.forEach((p, pi) => {
    const x = Math.floor(p[0]), y = Math.floor(p[1]); if (x < 0 || y < 0 || x >= N || y >= N) return;
    const i = y * N + x, d = Math.hypot(x + 0.5 - p[0], y + 0.5 - p[1]);
    if (d < nah[i]) { nah[i] = d; NX[i] = p[0]; NY[i] = p[1]; NL[i] = li; NP[i] = pi; } }));
  const ausbreiten = () => {
    const pruef = (i, j) => { if (NL[j] < 0) return; const x = (i % N) + 0.5, y = ((i / N) | 0) + 0.5, d = Math.hypot(x - NX[j], y - NY[j]);
      if (d < nah[i]) { nah[i] = d; NX[i] = NX[j]; NY[i] = NY[j]; NL[i] = NL[j]; NP[i] = NP[j]; } };
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) { const i = y * N + x;
      if (x > 0) pruef(i, i - 1); if (y > 0) { pruef(i, i - N); if (x > 0) pruef(i, i - N - 1); if (x < N - 1) pruef(i, i - N + 1); } }
    for (let y = N - 1; y >= 0; y--) for (let x = N - 1; x >= 0; x--) { const i = y * N + x;
      if (x < N - 1) pruef(i, i + 1); if (y < N - 1) { pruef(i, i + N); if (x < N - 1) pruef(i, i + N + 1); if (x > 0) pruef(i, i + N - 1); } }
  };
  ausbreiten();
  // 4) Wasserspiegel: flussabwärts nie steigend, quer über die ganze Breite (samt Rand unter der Böschung) unter dem Gelände
  //    Querschnitte, die in einen See reichen, zählen dort nicht (der Seeboden ist kein Ufer); Punkte im See liegen auf dessen Spiegel.
  const seeBei = (x, y) => { const i = Math.min(N - 1, Math.max(0, y | 0)) * N + Math.min(N - 1, Math.max(0, x | 0)); return SEE[i] ? seen[SEE[i] - 1].spiegel : null; };
  const quer = (p, a, q, W) => { const tx = q[0] - a[0], ty = q[1] - a[1], tl = Math.hypot(tx, ty) || 1; let m = Infinity;
    for (let o = -W / 2 - 3; o <= W / 2 + 3; o += 1) { const x = p[0] - ty / tl * o / zelle, y = p[1] + tx / tl * o / zelle;
      if (seeBei(x, y) == null) m = Math.min(m, bilinear(H, N, x - 0.5, y - 0.5)); } return m; };
  for (const l of laeufe) {
    let wl = l.startSpiegel != null ? l.startSpiegel : Infinity;
    const P = l.punkte;
    for (let i = 0; i < P.length; i++) {
      const sp = seeBei(P[i][0], P[i][1]);
      if (sp != null) { wl = Math.min(wl, sp); P[i][2] = sp; continue; }
      const q = P[Math.min(P.length - 1, i + 4)], p0 = P[Math.max(0, i - 4)];
      wl = Math.min(wl, quer(P[i], p0, q, P[i][3] + 2 * zelle) - 0.5);
      P[i][2] = wl;
    }
    // am Seeabfluss nicht mit einer Stufe beginnen: vom Seespiegel aus sanft abfallen, soweit das Ufer es zulässt
    if (l.startSpiegel != null)
      for (let i = 0, weg = 0; i < P.length; i++) {
        if (i) weg += Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]) * zelle;
        if (weg > 300) break;
        const q = P[Math.min(P.length - 1, i + 4)], p0 = P[Math.max(0, i - 4)];
        P[i][2] = Math.max(P[i][2], Math.min(l.startSpiegel - 0.03 * weg, quer(P[i], p0, q, P[i][3] + 2 * zelle) - 0.2));
        if (i) P[i][2] = Math.min(P[i][2], P[i - 1][2]);
      }
    const boden = l.anschluss ? l.anschluss[0].punkte[l.anschluss[1]][2] : l.bodenEnde;
    // zum Ende hin sanft auf den Spiegel des Hauptflusses bzw. Sees zulaufen (nur absenken), damit an der Mündung keine Stufe bleibt
    if (l.anschluss || l.st.ende === "see")
      for (let i = P.length - 1, rest = 0; i >= 0; i--) {
        if (i < P.length - 1) rest += Math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) * zelle;
        if (rest > 400) break;
        P[i][2] = Math.min(P[i][2], boden + 0.006 * rest);
      }
    for (const p of P) p[2] = Math.max(p[2], boden);
  }
  // höchster Wasserspiegel in der Nähe (in Kurven liegt der Lauf flussaufwärts oft näher als der Punkt quer gegenüber)
  const WM = new Float32Array(n).fill(-1e9), WL = new Int32Array(n).fill(-1), WP = new Int32Array(n);
  laeufe.forEach((l, li) => l.punkte.forEach((p, pi) => {
    const r = (p[3] / 2 + zelle + 4) / zelle, x0 = p[0], y0 = p[1];
    for (let y = Math.max(0, Math.floor(y0 - r)); y <= Math.min(N - 1, Math.floor(y0 + r)); y++)
      for (let x = Math.max(0, Math.floor(x0 - r)); x <= Math.min(N - 1, Math.floor(x0 + r)); x++)
        if (Math.hypot(x + 0.5 - x0, y + 0.5 - y0) <= r) { const i = y * N + x; if (p[2] > WM[i]) { WM[i] = p[2]; WL[i] = li; WP[i] = pi; } }
  }));
  const ufer = (i, p, d) => Math.max(p[2], WM[i]) + 0.6 + Math.max(0, d - p[3] / 2) * 0.45;   // Böschung über dem Wasser
  // 5) Täler: glockenförmig absenken, aber nie unter die Böschung des Flusses und nie unter den Spiegel naher Seen
  const meer = abstandMeter(N, zelle, Uint8Array.from(H, (h) => (h <= 0 ? 1 : 0)));
  const T2 = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    if (NL[i] < 0 || H[i] <= 0 || SEE[i]) continue;
    const p = laeufe[NL[i]].punkte[NP[i]], a = p[4], d = nah[i] * zelle;
    const w = Math.min(220, 70 + 25 * Math.log2(Math.max(1, a / T)) + 0.6 * p[3] * 3);
    if (d > w * 2.5) continue;
    T2[i] = tVon(a) * Math.exp(-((d / w) ** 2)) * smoothstep(40, 400, meer[i]) * (0.25 + 0.75 * S[i]);
  }
  for (let r = 0; r < 2; r++) { const t = T2.slice(); for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) { const i = y * N + x;
    T2[i] = (4 * t[i] + t[i - 1] + t[i + 1] + t[i - N] + t[i + N]) / 8; } }
  const SN = seeNiveau(N, zelle, SEE, seen, 500);
  for (let i = 0; i < n; i++) {
    if (!(T2[i] > 0) || H[i] <= 0) continue;
    const p = laeufe[NL[i]].punkte[NP[i]], u = ufer(i, p, nah[i] * zelle), boden = SN[i] < Infinity ? Math.max(u, SN[i]) : u;
    H[i] = Math.max(H[i] - T2[i], Math.min(H[i], boden), Math.min(H[i], 0.8));
  }
  // 6) Flussbett: Parabel bis zur nassen Breite, dann Böschung; nur absenken. Liegt die Zelle zugleich unter dem Wasser
  //    eines höher gelegenen Abschnitts (enge Kurve, Nachbarfluss), bleibt sie über dessen Spiegel – sonst schwebte es dort.
  const FM = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    if (NL[i] < 0 || H[i] <= 0) continue;
    const l = laeufe[NL[i]], p = l.punkte[NP[i]], d = nah[i] * zelle;
    const W = p[3], d0 = W / 2, tiefe = tiefeVon(p[4]);
    if (d > d0 + 40) continue;
    let ziel = d <= d0 ? p[2] - tiefe * (1 - (d / d0) ** 2) : Math.max(p[2], WM[i]) + (d - d0) * 0.45;
    const fremd = WL[i] >= 0 && (WL[i] !== NL[i] || Math.abs(WP[i] - NP[i]) * zelle * 0.5 > W + 4 * zelle + 8);
    if (fremd && WM[i] > p[2] + 0.3) ziel = Math.max(ziel, WM[i] + 0.3);
    if (ziel < H[i]) H[i] = ziel;
    if (d <= d0 && !SEE[i] && !(fremd && WM[i] > p[2] + 0.3)) FM[i] = 1;
  }
  const liste = laeufe.map((l) => ({ v: 2, punkte: l.punkte.filter((_, i) => i % 4 === 0 || i === l.punkte.length - 1)
    .map((p) => [+p[0].toFixed(2), +p[1].toFixed(2), +p[2].toFixed(2), +(p[3] + 2 * zelle).toFixed(1)]) }));
  return { liste, FM };
}

// Wasserspiegel des nächsten Sees je Zelle (bis maxM Meter vom Ufer), sonst +unendlich
function seeNiveau(N, zelle, SEE, seen, maxM) {
  const L = new Float32Array(N * N).fill(Infinity), D = new Int32Array(N * N).fill(-1), q = new Int32Array(N * N); let qh = 0, qt = 0;
  for (let i = 0; i < N * N; i++) if (SEE[i]) { L[i] = seen[SEE[i] - 1].spiegel + 0.4; D[i] = 0; q[qt++] = i; }
  const maxS = Math.round(maxM / zelle);
  while (qh < qt) { const i = q[qh++], x = i % N; if (D[i] >= maxS) continue;
    for (const j of [i - 1, i + 1, i - N, i + N]) if (j >= 0 && j < N * N && D[j] < 0 && Math.abs((j % N) - x) <= 1) { D[j] = D[i] + 1; L[j] = L[i]; q[qt++] = j; } }
  return L;
}

// alles zusammen. o: {hochebenen, grate, seen, fluesse} (true/false), schutz: [{x, y (Zellen), r (m)}]
function landschaftUeberarbeiten(H, N, zelle, REG, SEE, seen, schutz, seed, o, fortschritt) {
  const melde = (t) => fortschritt && fortschritt(t);
  const T = FLUSS_KM2 * 1e6 / (zelle * zelle);
  const S = schutzFeld(N, zelle, schutz);
  const info = {};
  if (o.rinnen !== false) { melde(0.05); info.rinnen = rinnenFuellen(H, N, zelle, SEE); }
  const meer = abstandMeter(N, zelle, Uint8Array.from(H, (h) => (h <= 1.5 ? 1 : 0)));
  let seeNah = abstandMeter(N, zelle, SEE);
  if (o.hochebenen) { melde(0.1); hochebenen(H, N, zelle, seed, meer, seeNah, abstandMeter(N, zelle, REG ? Uint8Array.from(REG, (r) => (r === 250 ? 1 : 0)) : new Uint8Array(N * N)), 0.6); }
  if (o.grate && REG) { melde(0.25); info.paesse = grateAnlegen(H, N, zelle, REG, abfluss(H, N).A, T, seed, meer, seeNah, S); }
  if (o.seen) { melde(0.45); const f = abfluss(H, N); info.neueSeen = seenAnlegen(H, N, zelle, SEE, seen, f.A, f.ziel, T, REG, S, meer, Math.round(3 * N * zelle / 16384 + 2), seed); }
  let liste = null, FM = null;
  if (o.fluesse) { melde(0.65); ({ liste, FM } = flussLaeufe(H, N, zelle, SEE, seen, T, seed, S)); info.fluesse = liste.length; }
  melde(1);
  return { H, SEE, seen, liste, FM, info };
}

// ---------- Export: Hochskalieren (Catmull-Rom) + Feindetail ----------
// nass (optional, je Zelle 1 = Fluss oder See): dort bilinear statt Catmull-Rom (kein Überschwingen über den Wasserspiegel)
// und ohne Feindetail, mit Übergang bis 60 m vom Wasser
function hochskalieren(H, N, M, seed, feindetail, fortschritt, welt = 4096, nass = null) {
  const fw = welt / 4096;
  const D = nass ? abstandMeter(N, welt / N, nass) : null;
  const nz = makeNoise(seed + 999);
  const out = new Float32Array(M * M);
  const s = N / M;
  const cr = (p0, p1, p2, p3, t) => p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));
  const g = (x, y) => H[Math.min(N - 1, Math.max(0, y)) * N + Math.min(N - 1, Math.max(0, x))];
  for (let j = 0; j < M; j++) {
    if (fortschritt && (j & 63) === 0) fortschritt(j / M);
    const fy = (j + 0.5) * s - 0.5, y = Math.floor(fy), ty = fy - y;
    for (let i = 0; i < M; i++) {
      const fx = (i + 0.5) * s - 0.5, x = Math.floor(fx), tx = fx - x;
      const r = [];
      for (let k = -1; k <= 2; k++) r.push(cr(g(x - 1, y + k), g(x, y + k), g(x + 1, y + k), g(x + 2, y + k), tx));
      let h = cr(r[0], r[1], r[2], r[3], ty), fd = feindetail;
      if (D) {
        const xc = Math.min(N - 1, Math.max(0, Math.round(fx))), yc = Math.min(N - 1, Math.max(0, Math.round(fy))), d = D[yc * N + xc];
        if (d < 60) {
          const k = smoothstep(16, 40, d);
          h = k * h + (1 - k) * bilinear(H, N, Math.max(0, fx), Math.max(0, fy));
          fd *= smoothstep(30, 60, d);
        }
      }
      if (fd > 0 && h > 0.3) {
        // kleine Bodenwellen (~40 m) und Unebenheiten (~10 m), an der Küste ausgeblendet
        const u = i / M * fw, v = j / M * fw;
        const w = Math.min(1, h / 3);
        h += w * fd * (1.4 * nz.fbm(u * 100, v * 100, 2) + 0.6 * nz.fbm(u * 400 + 7, v * 400 + 3, 2));
      }
      out[j * M + i] = h;
    }
  }
  if (fortschritt) fortschritt(1);
  return out;
}

// ---------- Worker-Schnittstelle ----------
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  const analyse = (H, m) => { const A = fluesse(H, m.N); return { A, B: biomeBerechnen(H, A, m.N, m.zelle, m.bp, m.schwelle) }; };
  self.onmessage = (e) => {
    const m = e.data;
    const melde = (text) => (f) => self.postMessage({ typ: "fortschritt", text, f });
    if (m.auftrag === "generieren") {
      melde("Landschaft")(0);
      const H = generiere(m.N, m.p);
      erodiere(H, m.N, Math.round(m.p.erosion * 1000), m.p.seed, melde("Erosion"));
      thermisch(H, m.N, 3, 3.2);
      const { A, B } = analyse(H, m);
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, H, A, B }, [H.buffer, A.buffer, B.buffer]);
    } else if (m.auftrag === "erosion") {
      const H = m.H;
      erodiere(H, m.N, m.anzahl, m.seed, melde("Erosion"));
      thermisch(H, m.N, 2, 3.2);
      const { A, B } = analyse(H, m);
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, H, A, B }, [H.buffer, A.buffer, B.buffer]);
    } else if (m.auftrag === "analyse") {
      const { A, B } = analyse(m.H, m);
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, A, B, version: m.version }, [A.buffer, B.buffer]);
    } else if (m.auftrag === "flussbetten") {
      const H = m.H;
      flussbetten(H, m.N, fluesse(H, m.N), m.schwelle);
      const { A, B } = analyse(H, m);
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, H, A, B }, [H.buffer, A.buffer, B.buffer]);
    } else if (m.auftrag === "ressourcen") {
      const r = ressourcenVerteilen(m.H, m.E, fluesse(m.H, m.N), m.N, m.zelle, m.marker, m.rp, m.schwelle, melde("Ressourcen"));
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, r });
    } else if (m.auftrag === "wege") {
      const w = wegeGenerieren(m.H, fluesse(m.H, m.N), m.E, m.N, m.zelle, m.marker, m.wp, m.schwelle, melde("Wege"));
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, w });
    } else if (m.auftrag === "steuerkarte") {
      const out = steuerkarte(m.E, m.N, m.M, m.seed, melde("Export Biome"));
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, out }, [out.buffer]);
    } else if (m.auftrag === "ueberarbeiten") {
      const r = landschaftUeberarbeiten(m.H, m.N, m.zelle, m.REG, m.SEE, m.seen, m.schutz, m.seed, m.o, melde("Landschaft überarbeiten"));
      const { A, B } = analyse(r.H, m);
      const tr = [r.H.buffer, r.SEE.buffer, A.buffer, B.buffer]; if (r.FM) tr.push(r.FM.buffer);
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, H: r.H, SEE: r.SEE, seen: r.seen, liste: r.liste, FM: r.FM, info: r.info, A, B }, tr);
    } else if (m.auftrag === "hochskalieren") {
      const out = hochskalieren(m.H, m.N, m.M, m.seed, m.feindetail, melde("Export"), m.welt, m.nass);
      const maske = m.wege && m.wege.length ? wegeEinarbeiten(out, m.M, m.N, m.wege, melde("Export Wege"), m.welt) : null;
      self.postMessage({ typ: "fertig", auftrag: m.auftrag, out, maske }, maske ? [out.buffer, maske.buffer] : [out.buffer]);
    }
  };
}
