// ===== Marker (Städte, Dörfer, Dungeons, Minen, POIs, Felder) + Ressourcen-Overlay =====
// Wird vor app.js geladen; nutzt deren Globals erst zur Laufzeit (zustand, ansicht, N, ZELLE …).

const MARKER_TYPEN = {
  stadt:   { name: "Stadt",   farbe: "#e8b04a", zeichen: "S", radius: 120 },
  dorf:    { name: "Dorf",    farbe: "#e7d38a", zeichen: "D", radius: 60 },
  dungeon: { name: "Dungeon", farbe: "#c0504d", zeichen: "☠", radius: 25 },
  mine:    { name: "Mine",    farbe: "#9aa4b1", zeichen: "⛏", radius: 30 },
  poi:     { name: "POI",     farbe: "#6fb7e8", zeichen: "★", radius: 15 },
  feld:    { name: "Feld",    farbe: "#d9c25a", zeichen: "", radius: 0 },
};
const FELD_ARTEN = { weizen: { name: "Weizen", farbe: "rgba(226,196,92,.75)" }, gemuese: { name: "Gemüse", farbe: "rgba(120,170,70,.75)" } };
const RES_FARBEN = { baeume: "#0f3d1e", buesche: "#7fbf4a", erze: ["#8a8f96", "#d8dce2", "#7fb2ff", "#73e0ff", "#ffb02e", "#b45cff"], pflanzen: ["#b85fd8", "#e0405a", "#ffffff"] };

const markerZustand = { liste: [], auswahl: -1, ziehen: null, ressourcen: null, ressourcenAlt: false, zeigen: true };

function markerNeu(typ, x, y) {
  const t = MARKER_TYPEN[typ];
  const m = { typ, x, y, name: "" };
  if (typ === "feld") Object.assign(m, { art: "weizen", breite: 60, laenge: 90, winkel: 0 });
  else m.radius = t.radius;
  const gleiche = markerZustand.liste.filter((q) => q.typ === typ).length;
  m.name = typ === "feld" ? "" : `${t.name} ${gleiche + 1}`;
  return m;
}

// Treffer-Test in Zellen-Koordinaten
function markerBei(cx, cy) {
  const tol = 17 / ansicht.zoom;    // Symbol (Radius 11–13 px) + Rand
  // zuerst Symbol und Namensschild (darunter) – hat Vorrang vor Radius-Flächen
  for (let k = markerZustand.liste.length - 1; k >= 0; k--) {
    const m = markerZustand.liste[k]; if (m.typ === "feld") continue;
    const dx = (cx - m.x) * ansicht.zoom, dy = (cy - m.y) * ansicht.zoom;
    if (Math.hypot(dx, dy) <= 17 || (m.name && Math.abs(dx) < Math.max(30, m.name.length * 3.6) && dy > 10 && dy < 32)) return k;
  }
  for (let k = markerZustand.liste.length - 1; k >= 0; k--) {
    const m = markerZustand.liste[k];
    if (m.typ === "feld") {
      const c = Math.cos(m.winkel), s = Math.sin(m.winkel), dx = cx - m.x, dy = cy - m.y;
      const u = dx * c + dy * s, v = -dx * s + dy * c;
      if (Math.abs(u) <= m.breite / 2 / ZELLE + tol && Math.abs(v) <= m.laenge / 2 / ZELLE + tol) return k;
    }
  }
  return -1;
}

function markerGeaendert() {
  if (markerZustand.ressourcen) { markerZustand.ressourcenAlt = true; ressourcenInfo(); }
  if (wegeZustand.liste && !wegeZustand.alt) { wegeZustand.alt = true; wegeInfo(); }
  markerPanel();
  ansicht.zeichne();
}

// ---------- Maus ----------
function markerDown(cx, cy, e) {
  const w = zustand.werkzeug;
  const k = markerBei(cx, cy);
  if (w === "marker:auswahl" || k >= 0) {
    markerZustand.auswahl = k;
    if (k >= 0) {
      const m = markerZustand.liste[k];
      markerZustand.ziehen = { k, dx: m.x - cx, dy: m.y - cy, drehen: e.shiftKey && m.typ === "feld" };
    }
    markerPanel(); ansicht.zeichne();
    return;
  }
  const typ = w.slice(7);
  const m = markerNeu(typ, cx, cy);
  markerZustand.liste.push(m);
  markerZustand.auswahl = markerZustand.liste.length - 1;
  markerGeaendert();
}
function markerMove(cx, cy) {
  const z = markerZustand.ziehen; if (!z) return;
  const m = markerZustand.liste[z.k];
  if (z.drehen) m.winkel = Math.atan2(cy - m.y, cx - m.x);
  else { m.x = cx + z.dx; m.y = cy + z.dy; }
  ansicht.zeichne();
}
function markerUp() {
  if (markerZustand.ziehen) { markerZustand.ziehen = null; markerGeaendert(); }
}
function markerLoeschen() {
  if (markerZustand.auswahl < 0) return;
  markerZustand.liste.splice(markerZustand.auswahl, 1);
  markerZustand.auswahl = -1;
  markerGeaendert();
}

// ---------- Zeichnen (wird von ansicht.zeichne aufgerufen) ----------
function markerZeichnen(ctx, ox, oy, z) {
  const P = (x, y) => [ox + x * z, oy + y * z];
  wegeZeichnen(ctx, ox, oy, z);
  // Ressourcen-Punkte
  const r = markerZustand.ressourcen;
  if (r && markerZustand.zeigen) {
    const h = N * ZELLE / 2, s = z / ZELLE, gr = Math.max(1, Math.min(4, z * 0.9));
    const punkte = (liste, farbe, g) => {
      for (const p of liste) {
        const px = ox + (p[0] + h) * s, py = oy + (p[1] + h) * s;
        if (px < -5 || py < -5 || px > ctx.canvas.width || py > ctx.canvas.height) continue;
        ctx.fillStyle = typeof farbe === "function" ? farbe(p) : farbe;
        ctx.fillRect(px - g / 2, py - g / 2, g, g);
      }
    };
    if (z > 0.6) punkte(r.baeume, RES_FARBEN.baeume, gr);
    punkte(r.buesche, RES_FARBEN.buesche, gr);
    punkte(r.pflanzen, (p) => RES_FARBEN.pflanzen[p[2]], gr + 0.5);
    ctx.strokeStyle = "rgba(0,0,0,.8)"; ctx.lineWidth = 1;
    for (const p of r.erze) {
      const px = ox + (p[0] + h) * s, py = oy + (p[1] + h) * s, g = 2.5 + p[3] * 0.8;
      ctx.fillStyle = RES_FARBEN.erze[p[2]];
      ctx.beginPath(); ctx.moveTo(px, py - g); ctx.lineTo(px + g, py); ctx.lineTo(px, py + g); ctx.lineTo(px - g, py); ctx.closePath(); ctx.fill(); ctx.stroke();
    }
  }
  // Marker
  ctx.font = "600 12px system-ui"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  markerZustand.liste.forEach((m, k) => {
    const [px, py] = P(m.x, m.y), aus = k === markerZustand.auswahl, t = MARKER_TYPEN[m.typ];
    if (m.typ === "feld") {
      ctx.save(); ctx.translate(px, py); ctx.rotate(m.winkel);
      const w = m.breite / ZELLE * z, l = m.laenge / ZELLE * z;
      ctx.fillStyle = FELD_ARTEN[m.art].farbe; ctx.fillRect(-w / 2, -l / 2, w, l);
      ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 1;
      for (let u = -w / 2 + 4; u < w / 2; u += Math.max(3, 6 * z / 4)) { ctx.beginPath(); ctx.moveTo(u, -l / 2); ctx.lineTo(u, l / 2); ctx.stroke(); }
      ctx.strokeStyle = aus ? "#fff" : "rgba(60,40,10,.9)"; ctx.lineWidth = aus ? 2.5 : 1.5; ctx.strokeRect(-w / 2, -l / 2, w, l);
      ctx.restore();
      return;
    }
    const rr = m.radius / ZELLE * z;
    if (rr > 8) {
      ctx.fillStyle = t.farbe + "33"; ctx.strokeStyle = t.farbe; ctx.lineWidth = aus ? 2.5 : 1.5; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.arc(px, py, rr, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); ctx.setLineDash([]);
    }
    const g = m.typ === "stadt" ? 13 : 11;
    ctx.fillStyle = t.farbe; ctx.strokeStyle = aus ? "#fff" : "#1a1a1a"; ctx.lineWidth = aus ? 3 : 2;
    ctx.beginPath(); ctx.arc(px, py, g, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#1a1408"; ctx.fillText(t.zeichen, px, py + 0.5);
    if (m.name) {
      ctx.lineWidth = 3; ctx.strokeStyle = "rgba(0,0,0,.75)"; ctx.strokeText(m.name, px, py + g + 10);
      ctx.fillStyle = "#fff"; ctx.fillText(m.name, px, py + g + 10);
    }
  });
  // halbtransparente Vorschau des Markers, der gesetzt wird
  const w = zustand.werkzeug;
  if (ansicht.maus && w.startsWith("marker:") && w !== "marker:auswahl" && !markerZustand.ziehen) {
    const r = ctx.canvas.getBoundingClientRect(), mx = ansicht.maus[0] - r.left, my = ansicht.maus[1] - r.top;
    const [cx, cy] = ansicht.zuZelle(ansicht.maus[0], ansicht.maus[1]);
    if (markerBei(cx, cy) < 0) {
      const typ = w.slice(7), t = MARKER_TYPEN[typ];
      ctx.globalAlpha = 0.55;
      if (typ === "feld") {
        const fw = 60 / ZELLE * z, fl = 90 / ZELLE * z;
        ctx.fillStyle = FELD_ARTEN.weizen.farbe; ctx.fillRect(mx - fw / 2, my - fl / 2, fw, fl);
      } else {
        const rr = t.radius / ZELLE * z;
        if (rr > 8) { ctx.fillStyle = t.farbe + "33"; ctx.beginPath(); ctx.arc(mx, my, rr, 0, Math.PI * 2); ctx.fill(); }
        ctx.fillStyle = t.farbe; ctx.beginPath(); ctx.arc(mx, my, 11, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#1a1408"; ctx.fillText(t.zeichen, mx, my + 0.5);
      }
      ctx.globalAlpha = 1;
    }
  }
  ctx.textAlign = "start"; ctx.textBaseline = "alphabetic";
}

// ---------- Seitenleiste ----------
function markerPanel() {
  markerListe();
  const el = $("marker-panel");
  const m = markerZustand.liste[markerZustand.auswahl];
  const zahl = {}; for (const q of markerZustand.liste) zahl[q.typ] = (zahl[q.typ] || 0) + 1;
  $("marker-zahl").textContent = Object.keys(MARKER_TYPEN).filter((t) => zahl[t]).map((t) => `${zahl[t]} ${MARKER_TYPEN[t].name}`).join(" · ") || "noch keine Marker";
  if (!m) { el.innerHTML = `<div class="hinweis">Marker anklicken, um ihn zu bearbeiten. Ziehen = verschieben, bei Feldern Umschalt+Ziehen = drehen.</div>`; return; }
  const t = MARKER_TYPEN[m.typ];
  let html = `<div class="marker-kopf"><b>${t.name}</b><button id="mk-del" title="Löschen (Entf)">Löschen</button></div>`;
  if (m.typ !== "feld") {
    html += `<label class="regler"><span>Name</span><span></span><input id="mk-name" type="text" value="${(m.name || "").replace(/"/g, "&quot;")}"></label>
      <label class="regler"><span>Radius</span><output>${m.radius} m</output><input id="mk-radius" type="range" min="5" max="400" step="5" value="${m.radius}"></label>`;
  } else {
    html += `<label class="regler"><span>Anbau</span><span></span><select id="mk-art">${Object.entries(FELD_ARTEN).map(([k, v]) => `<option value="${k}" ${m.art === k ? "selected" : ""}>${v.name}</option>`).join("")}</select></label>
      <label class="regler"><span>Breite</span><output>${m.breite} m</output><input id="mk-breite" type="range" min="15" max="200" step="5" value="${m.breite}"></label>
      <label class="regler"><span>Länge</span><output>${m.laenge} m</output><input id="mk-laenge" type="range" min="15" max="300" step="5" value="${m.laenge}"></label>
      <label class="regler"><span>Drehung</span><output>${Math.round(m.winkel * 180 / Math.PI)}°</output><input id="mk-winkel" type="range" min="-180" max="180" step="1" value="${Math.round(m.winkel * 180 / Math.PI)}"></label>`;
  }
  html += `<div class="hinweis">Position: ${Math.round(m.x * ZELLE - N * ZELLE / 2)} / ${Math.round(m.y * ZELLE - N * ZELLE / 2)} m · Höhe ${zustand.H[Math.round(m.y) * N + Math.round(m.x)]?.toFixed(1)} m</div>`;
  el.innerHTML = html;
  $("mk-del").onclick = markerLoeschen;
  const bind = (id, f) => { const i = $(id); if (i) i.addEventListener("input", () => { f(i); const o = i.parentElement.querySelector("output"); if (o) o.textContent = id === "mk-winkel" ? `${i.value}°` : `${i.value} m`; ansicht.zeichne(); }); if (i) i.addEventListener("change", () => markerGeaendert()); };
  bind("mk-name", (i) => (m.name = i.value));
  bind("mk-radius", (i) => (m.radius = +i.value));
  bind("mk-breite", (i) => (m.breite = +i.value));
  bind("mk-laenge", (i) => (m.laenge = +i.value));
  bind("mk-winkel", (i) => (m.winkel = +i.value * Math.PI / 180));
  bind("mk-art", (i) => (m.art = i.value));
}

// Liste aller Marker, nach Typ gruppiert: anklicken = auswählen + hinzoomen, ✕ = löschen
function markerListe() {
  const el = $("marker-liste"); if (!el) return;
  const filter = ($("marker-filter")?.value || "").toLowerCase();
  let html = "";
  for (const [typ, t] of Object.entries(MARKER_TYPEN)) {
    const eintraege = markerZustand.liste.map((m, k) => [m, k]).filter(([m]) => m.typ === typ);
    if (!eintraege.length) continue;
    const zeilen = eintraege.filter(([m]) => !filter || (m.name || "").toLowerCase().includes(filter) || t.name.toLowerCase().includes(filter));
    if (!zeilen.length) continue;
    html += `<div class="ml-gruppe"><i style="background:${t.farbe}"></i>${t.name} <span>${eintraege.length}</span></div>`;
    for (const [m, k] of zeilen) {
      const titel = m.typ === "feld" ? `${FELD_ARTEN[m.art].name}feld ${m.breite}×${m.laenge} m` : (m.name || "(ohne Name)");
      html += `<div class="ml-zeile${k === markerZustand.auswahl ? " aktiv" : ""}" data-k="${k}"><span>${titel.replace(/</g, "&lt;")}</span><button data-del="${k}" title="Löschen">✕</button></div>`;
    }
  }
  el.innerHTML = html || `<div class="hinweis">Noch keine Marker gesetzt.</div>`;
  for (const z of el.querySelectorAll(".ml-zeile")) z.onclick = (e) => {
    if (e.target.dataset.del) return;
    const k = +z.dataset.k, m = markerZustand.liste[k];
    markerZustand.auswahl = k;
    if (ansicht.zoom < 1.5) ansicht.zoom = 2;
    ansicht.cx = m.x; ansicht.cy = m.y;
    markerPanel(); ansicht.zeichne();
  };
  for (const b of el.querySelectorAll("[data-del]")) b.onclick = () => { markerZustand.auswahl = +b.dataset.del; markerLoeschen(); };
}

function ressourcenInfo() {
  const r = markerZustand.ressourcen;
  $("res-info").innerHTML = !r ? "Noch nicht verteilt." :
    `${r.baeume.length.toLocaleString("de")} Bäume · ${r.buesche.length.toLocaleString("de")} Äste-Büsche · ${r.erze.length} Erze · ${r.pflanzen.length.toLocaleString("de")} Pflanzen` +
    (markerZustand.ressourcenAlt ? `<br><b style="color:var(--akzent)">Karte geändert – neu verteilen?</b>` : "");
}

async function vorschlaegeMachen() {
  const neu = vorschlaege(zustand.H, effektiveBiome(), N, ZELLE, markerZustand.liste, params().seed + markerZustand.liste.length);
  for (const m of neu) if (m.typ !== "feld" && !m.name) m.name = `${MARKER_TYPEN[m.typ].name} ${markerZustand.liste.filter((q) => q.typ === m.typ).length + 1}`, markerZustand.liste.push(m);
  markerZustand.liste.push(...neu.filter((m) => m.typ === "feld"));
  markerGeaendert();
  status(`${neu.filter((m) => m.typ === "feld").length} Felder und ${neu.filter((m) => m.typ === "mine").length} Minen vorgeschlagen`);
}

async function ressourcenVerteilenStarten() {
  beschaeftigt(true);
  const rp = { seed: params().seed, wege: wegeZustand.liste || [] };
  for (const k of ["baumdichte", "buschdichte", "erzdichte", "pflanzendichte"]) rp[k] = parseFloat($("p-" + k).value);
  const r = await auftrag({ auftrag: "ressourcen", H: zustand.H.slice(), E: effektiveBiome(), N, zelle: ZELLE, marker: markerZustand.liste, rp, schwelle: FLUSS_SCHWELLE });
  markerZustand.ressourcen = r.r; markerZustand.ressourcenAlt = false;
  ressourcenInfo(); ansicht.zeichne(); status("Ressourcen verteilt"); beschaeftigt(false);
}

// Marker in Welt-Koordinaten (Meter, Mitte = 0) für Godot
function markerExport() {
  const h = N * ZELLE / 2;
  return markerZustand.liste.map((m) => {
    const o = { typ: m.typ, name: m.name || "", x: +(m.x * ZELLE - h).toFixed(1), z: +(m.y * ZELLE - h).toFixed(1),
      hoehe: +zustand.H[Math.min(N - 1, Math.max(0, Math.round(m.y))) * N + Math.min(N - 1, Math.max(0, Math.round(m.x)))].toFixed(2) };
    if (m.typ === "feld") Object.assign(o, { art: m.art, breite: m.breite, laenge: m.laenge, winkel: +m.winkel.toFixed(4) });
    else o.radius = m.radius;
    return o;
  });
}

function markerAufbauen() {
  const mw = $("marker-werkzeuge");
  const knopf = (id, html, titel) => { const b = document.createElement("button"); b.className = "werkzeug biom"; b.dataset.w = id; b.innerHTML = html; b.title = titel || ""; b.onclick = () => waehle(id); mw.appendChild(b); };
  knopf("marker:auswahl", "↖ Auswählen", "Marker auswählen und verschieben");
  for (const [typ, t] of Object.entries(MARKER_TYPEN)) knopf("marker:" + typ, `<i style="background:${t.farbe}"></i>${t.name}`, `${t.name} setzen`);
  $("vorschlaege").onclick = vorschlaegeMachen;
  $("marker-filter").addEventListener("input", markerListe);
  $("marker-alle-loeschen").onclick = () => {
    if (!markerZustand.liste.length || !confirm(`Alle ${markerZustand.liste.length} Marker löschen?`)) return;
    markerZustand.liste = []; markerZustand.auswahl = -1; markerGeaendert();
  };
  $("ressourcen-verteilen").onclick = ressourcenVerteilenStarten;
  $("ressourcen-zeigen").onchange = (e) => { markerZustand.zeigen = e.target.checked; ansicht.zeichne(); };
  for (const k of ["baumdichte", "buschdichte", "erzdichte", "pflanzendichte"]) {
    const i = $("p-" + k), o = i.parentElement.querySelector("output");
    i.addEventListener("input", () => (o.textContent = i.value)); o.textContent = i.value;
  }
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if ((e.key === "Delete" || e.key === "Backspace") && zustand.werkzeug.startsWith("marker")) { e.preventDefault(); markerLoeschen(); }
  });
  markerPanel(); ressourcenInfo(); wegeAufbauen();
}

// ===== Wege & Straßen =====
const wegeZustand = { liste: null, zeigen: true, alt: false };

function wegeZeichnen(ctx, ox, oy, z) {
  const w = wegeZustand.liste; if (!w || !wegeZustand.zeigen) return;
  const P = (q) => [ox + q[0] * z, oy + q[1] * z];
  ctx.lineCap = "round"; ctx.lineJoin = "round";
  const zug = (sel, breite, farbe, nurBr) => {
    for (const s of w) {
      if (!sel(s)) continue;
      ctx.strokeStyle = farbe; ctx.lineWidth = breite(s);
      ctx.beginPath();
      for (let k = 1; k < s.punkte.length; k++) {
        if (nurBr !== undefined && !!s.bruecke[k] !== nurBr) continue;
        const [x0, y0] = P(s.punkte[k - 1]), [x1, y1] = P(s.punkte[k]);
        ctx.moveTo(x0, y0); ctx.lineTo(x1, y1);
      }
      ctx.stroke();
    }
  };
  const bs = (s) => Math.max(s.typ === "strasse" ? 3 : 1.6, s.breite / ZELLE * z);
  zug(() => true, (s) => bs(s) + 2.5, "rgba(40,28,14,.85)");
  zug((s) => s.typ === "weg", bs, "#f4ead2", false);
  zug((s) => s.typ === "strasse", bs, "#e9cf96", false);
  zug(() => true, (s) => bs(s) + 1, "#c8432f", true);
  ctx.lineCap = "butt";
}

function wegeInfo() {
  const w = wegeZustand.liste, el = $("wege-info");
  if (!w) { el.innerHTML = "Noch keine Wege generiert."; return; }
  const km = { strasse: 0, weg: 0 }, brListe = [];
  for (const s of w) for (let k = 1; k < s.punkte.length; k++) {
    if (!s.bruecke[k]) km[s.typ] += Math.hypot(s.punkte[k][0] - s.punkte[k - 1][0], s.punkte[k][1] - s.punkte[k - 1][1]) * ZELLE;
    if (s.bruecke[k] && !s.bruecke[k - 1]) {
      const m = [(s.punkte[k][0] + s.punkte[k - 1][0]) / 2, (s.punkte[k][1] + s.punkte[k - 1][1]) / 2];
      if (!brListe.some((q) => Math.hypot(q[0] - m[0], q[1] - m[1]) < 2)) brListe.push(m);   // gemeinsam genutzte Brücken nur einmal
    }
  }
  const br = brListe.length;
  el.innerHTML = `${(km.strasse / 1000).toFixed(1)} km Straße · ${(km.weg / 1000).toFixed(1)} km Weg · ${br} Brücken` +
    (wegeZustand.alt ? `<br><b style="color:var(--akzent)">Karte/Marker geändert – neu generieren?</b>` : "");
}

async function wegeGenerierenStarten() {
  if (!markerZustand.liste.some((m) => m.typ === "stadt" || m.typ === "dorf")) { status("Erst mindestens eine Stadt oder ein Dorf setzen"); return; }
  beschaeftigt(true);
  const wp = {};
  for (const k of ["strasse_steigung", "weg_steigung", "bruecke_max", "extra"]) wp[k] = parseFloat($("p-" + k).value);
  const r = await auftrag({ auftrag: "wege", H: zustand.H.slice(), E: effektiveBiome(), N, zelle: ZELLE, marker: markerZustand.liste, wp, schwelle: FLUSS_SCHWELLE });
  wegeZustand.liste = r.w; wegeZustand.alt = false;
  ressourcenAufWegenEntfernen();
  wegeInfo(); ansicht.zeichne(); dreiDVeraltet(); status("Wege generiert"); beschaeftigt(false);
}

// Ressourcen, die auf einer Straße/einem Weg stehen, herausnehmen (ohne neu zu verteilen)
function ressourcenAufWegenEntfernen() {
  const r = markerZustand.ressourcen, w = wegeZustand.liste; if (!r || !w) return;
  const h = N * ZELLE / 2, raster = new Map(), Z = 16;   // 16-m-Raster für schnelle Suche
  for (const s of w) for (let k = 1; k < s.punkte.length; k++) {
    const a = s.punkte[k - 1], b = s.punkte[k], ax = a[0] * ZELLE - h, ay = a[1] * ZELLE - h, bx = b[0] * ZELLE - h, by = b[1] * ZELLE - h;
    const seg = [ax, ay, bx, by, s.breite / 2 + 2.5];
    for (let gy = Math.floor((Math.min(ay, by) - 8) / Z); gy <= Math.floor((Math.max(ay, by) + 8) / Z); gy++)
      for (let gx = Math.floor((Math.min(ax, bx) - 8) / Z); gx <= Math.floor((Math.max(ax, bx) + 8) / Z); gx++) {
        const key = gx * 100000 + gy; if (!raster.has(key)) raster.set(key, []); raster.get(key).push(seg);
      }
  }
  const frei = (p) => {
    for (const [ax, ay, bx, by, r2] of raster.get(Math.floor(p[0] / Z) * 100000 + Math.floor(p[1] / Z)) || []) {
      const dx = bx - ax, dy = by - ay, LL = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / LL));
      if (Math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy) < r2) return false;
    }
    return true;
  };
  let vorher = 0, nachher = 0;
  for (const k of ["baeume", "buesche", "erze", "pflanzen"]) { vorher += r[k].length; r[k] = r[k].filter(frei); nachher += r[k].length; }
  ressourcenInfo();
  if (vorher > nachher) status(`Wege generiert – ${vorher - nachher} Ressourcen auf Wegen entfernt`);
}

// Wege in Welt-Koordinaten (Meter, Mitte 0) für Godot
function wegeExport() {
  const h = N * ZELLE / 2;
  return (wegeZustand.liste || []).map((s) => ({ typ: s.typ, breite: s.breite,
    punkte: s.punkte.map((q) => [+(q[0] * ZELLE - h).toFixed(2), +q[2].toFixed(2), +(q[1] * ZELLE - h).toFixed(2)]),
    bruecke: s.bruecke.map((b) => (b ? 1 : 0)) }));
}

function wegeAufbauen() {
  $("wege-generieren").onclick = wegeGenerierenStarten;
  $("wege-entfernen").onclick = () => { wegeZustand.liste = null; wegeInfo(); ansicht.zeichne(); };
  $("wege-zeigen").onchange = (e) => { wegeZustand.zeigen = e.target.checked; ansicht.zeichne(); };
  for (const k of ["strasse_steigung", "weg_steigung", "bruecke_max", "extra"]) {
    const i = $("p-" + k), o = i.parentElement.querySelector("output");
    const f = () => (o.textContent = k.endsWith("steigung") ? `${i.value} %` : k === "bruecke_max" ? `${i.value} m` : i.value);
    i.addEventListener("input", f); f();
  }
  wegeInfo();
}
