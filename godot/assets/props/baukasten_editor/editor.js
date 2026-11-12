// Gebäude-Baukasten: Teile aus godot/assets/props/modelle im 1-m-Raster zusammensetzen und als JSON speichern.
// Koordinaten und Drehungen sind genau die von Godot (y oben, Vorderseite +z, Drehung in Grad, Reihenfolge YXZ),
// das gespeicherte Gebäude lädt Godot mit assets/props/gebaeude.gd.
"use strict";
(function () {
const D = window.BAUKASTEN_DATEN;
const T = window.THREE;
const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ Teile-Katalog
// Holz der Baukasten-Balken bekommt Vorrang bei Überlappung (wie materialien/balken.gdshader)
const VORRANG_ACHSE = { balken_2m: [1, 0, 0], balken_1m: [1, 0, 0], strebe_2m: [Math.SQRT1_2, Math.SQRT1_2, 0] };
const KATALOG = [
  ["Wände", [
    ["wand", "Wand", "2 × 2"], ["wand_2x1", "Wand", "2 × 1"], ["wand_1x1", "Wand", "1 × 1"],
    ["wand_dreieck", "Giebel", "2 × 2"], ["wand_dreieck_1x1", "Giebel", "1 × 1"]]],
  ["Türen und Fenster", [
    ["wand_tuer", "Wand mit Tür", "2 × 2"], ["tuer", "Türblatt", "0,8 × 1,85"],
    ["wand_fenster", "Fensterwand", "2 × 2"], ["wand_fenster_2x1", "Fensterwand", "2 × 1"], ["wand_fenster_1x1", "Fensterwand", "1 × 1"]]],
  ["Holz", [
    ["balken_2m", "Balken", "2 m"], ["balken_1m", "Balken", "1 m"],
    ["balken_2m", "Ständer", "2 m", [0, 0, 90]], ["balken_1m", "Ständer", "1 m", [0, 0, 90]],
    ["strebe_2m", "Strebe", "2 × 2"]]],
  ["Boden und Dach", [
    ["boden_2x2", "Dielenboden", "2 × 2"], ["boden_1x1", "Dielenboden", "1 × 1"],
    ["dach_2x2", "Dach 45°", "2 × 2"], ["dach_2x1", "Dach 45°", "2 × 1"], ["dach_1x2", "Dach 45°", "1 × 2"], ["dach_1x1", "Dach 45°", "1 × 1"],
    ["dach_traufe", "Dachüberstand", "2 × 0,5"], ["dach_first", "First", "2 m"]]],
  ["Treppen", [["treppe_holz", "Holztreppe", "1 × 2, 1 m hoch"], ["treppe_stein", "Steintreppe", "1 × 2, 1 m hoch"]]],
  ["Einrichtung", [
    ["kiste", "Kiste"], ["fass", "Fass"], ["tisch", "Tisch"], ["stuhl", "Stuhl"], ["hocker", "Hocker"], ["bank", "Bank"],
    ["laterne", "Laterne"], ["laternenpfahl", "Laternenpfahl"], ["lagerfeuer", "Lagerfeuer"], ["karren", "Karren"],
    ["zelt", "Zelt"], ["zaun", "Zaun", "2 m"], ["palisade", "Palisade", "2 m"], ["saeule", "Säule"], ["mauer", "Mauer", "3 m"], ["bogen", "Bogen"]]],
];

// ------------------------------------------------------------------ Zustand
const zustand = {
  name: "Neues Gebäude", id: null, teile: [],           // teile: {uid, modell, kaputt, pos:[x,y,z], dreh:[x,y,z]}
  werkzeug: "setzen", modell: "wand", dreh: [0, 0, 0], kaputt: false, ebene: 0, raster: 1,
  auswahl: null, geaendert: false, durchsicht: false,
};
let naechsteUid = 1;
const verlauf = [], wiederholen = [];

// ------------------------------------------------------------------ Szene
const leinwand = $("leinwand");
const renderer = new T.WebGLRenderer({ canvas: leinwand, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.toneMapping = T.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
const szene = new T.Scene();
szene.background = new T.Color(0xb9c7d2);
szene.fog = new T.Fog(0xb9c7d2, 60, 160);
const kamera = new T.PerspectiveCamera(45, 1, 0.1, 500);
kamera.position.set(9, 8, 11);
const steuerung = new window.OrbitControls(kamera, leinwand);
steuerung.target.set(2, 1.5, -2);
steuerung.enableDamping = true;
steuerung.mouseButtons = { LEFT: T.MOUSE.ROTATE, MIDDLE: T.MOUSE.DOLLY, RIGHT: T.MOUSE.PAN };
steuerung.maxPolarAngle = Math.PI * 0.495;
steuerung.update();

szene.add(new T.HemisphereLight(0xdfe8f0, 0x5b5040, 1.1));
const sonne = new T.DirectionalLight(0xfff2e0, 2.4);
sonne.position.set(14, 22, 10);
sonne.castShadow = true;
sonne.shadow.mapSize.set(2048, 2048);
Object.assign(sonne.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25, near: 1, far: 80 });
sonne.shadow.bias = -0.0004;
szene.add(sonne, sonne.target);

const bodenMat = new T.MeshStandardMaterial({ color: 0x7d8a63, roughness: 1 });
const boden = new T.Mesh(new T.PlaneGeometry(200, 200), bodenMat);
boden.rotation.x = -Math.PI / 2;
boden.position.y = -0.002;
boden.receiveShadow = true;
szene.add(boden);
const gitter = new T.GridHelper(60, 60, 0x4d5a3a, 0x66744d);
gitter.material.transparent = true; gitter.material.opacity = 0.55;
szene.add(gitter);
const ebeneGitter = new T.GridHelper(30, 30, 0x8a5527, 0x8a5527);
ebeneGitter.material.transparent = true; ebeneGitter.material.opacity = 0.45; ebeneGitter.material.depthWrite = false;
szene.add(ebeneGitter);
// Kreuz am Rasterpunkt unter dem Mauszeiger
const kreuz = new T.Group();
{
  const m = new T.MeshBasicMaterial({ color: 0xc0392b, depthTest: false });
  const a = new T.Mesh(new T.BoxGeometry(0.5, 0.02, 0.02), m), b = new T.Mesh(new T.BoxGeometry(0.02, 0.02, 0.5), m);
  const c = new T.Mesh(new T.SphereGeometry(0.05, 12, 8), m);
  kreuz.add(a, b, c); kreuz.renderOrder = 10; kreuz.children.forEach((k) => (k.renderOrder = 10));
}
szene.add(kreuz);
const gebaeudeGruppe = new T.Group();
szene.add(gebaeudeGruppe);

// ------------------------------------------------------------------ Materialien
const texLader = new T.TextureLoader();
const texturen = {};
function textur(name, farbe) {
  const k = name + (farbe ? "_f" : "_n");
  if (texturen[k] !== undefined) return texturen[k];
  const quelle = D.texturen[name] && D.texturen[name][farbe ? "farbe" : "normal"];
  if (!quelle) return (texturen[k] = null);
  const t = texLader.load(quelle);
  t.wrapS = t.wrapT = T.RepeatWrapping;
  t.anisotropy = 8;
  if (farbe) t.colorSpace = T.SRGBColorSpace;
  return (texturen[k] = t);
}
const materialien = {};
function material(name) {
  if (materialien[name]) return materialien[name];
  let m;
  if (name === "glas") {
    m = new T.MeshStandardMaterial({ color: 0xc7a86b, transparent: true, opacity: 0.32, roughness: 0.08, metalness: 0.1, side: T.DoubleSide, depthWrite: false });
  } else if (name === "asche") {
    m = new T.MeshStandardMaterial({ color: 0x3d3b39, roughness: 1 });
  } else {
    m = new T.MeshStandardMaterial({ map: textur(name, true), normalMap: textur(name, false), roughness: 0.88, color: 0xffffff });
    if (name === "eisen") { m.metalness = 0.6; m.roughness = 0.55; }
    if (name === "stoff") m.side = T.DoubleSide;
    if (name === "glut") { m.emissive = new T.Color(0xff6a20); m.emissiveMap = m.map; m.emissiveIntensity = 2.5; }
    if (!m.map) m.color = new T.Color(0x999999);
  }
  m.name = name;
  return (materialien[name] = m);
}
// Vorrang bei Überlappung: je waagerechter, desto höher; dann x vor z; dann fest nach Rasterposition.
// Godot verschiebt dafür die Tiefe (balken.gdshader), hier macht das polygonOffset.
function vorrang(obj, achse) {
  const a = new T.Vector3(...achse).applyQuaternion(obj.quaternion).normalize();
  const waagerecht = Math.round((1 - Math.abs(a.y)) * 2);
  const b = new T.Vector3(Math.abs(a.x), Math.abs(a.y), Math.abs(a.z));
  const entlangX = b.x >= b.z ? 1 : 0;
  const r = b.x >= b.y && b.x >= b.z ? "x" : b.y >= b.z ? "y" : "z";
  const lage = ((Math.round(obj.position[r]) % 4) + 4) % 4;
  return waagerecht * 8 + entlangX * 4 + lage;
}
function vorrangMaterial(name, v) {
  const k = name + "#" + v;
  if (!materialien[k]) {
    const m = material(name).clone();
    m.polygonOffset = true; m.polygonOffsetFactor = -v * 0.05; m.polygonOffsetUnits = -v * 4;
    materialien[k] = m;
  }
  return materialien[k];
}

// ------------------------------------------------------------------ Modelle
const vorlagen = {};
function b64ZuPuffer(b64) {
  const s = atob(b64), u = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
  return u.buffer;
}
function modellLaden(datei) {
  return new Promise((ok, fehler) => {
    new window.GLTFLoader().parse(b64ZuPuffer(D.modelle[datei]), "", (gltf) => {
      const g = gltf.scene;
      g.traverse((o) => {
        if (o.isMesh) {
          o.userData.matName = (o.material && o.material.name) || "";
          o.material = material(o.userData.matName);
          o.castShadow = o.userData.matName !== "glas";
          o.receiveShadow = true;
        }
      });
      ok(g);
    }, fehler);
  });
}
async function alleModelleLaden() {
  // erst alle Texturen fertig dekodieren, sonst rendern die Vorschaubilder schwarz
  await Promise.all(Object.keys(D.texturen).flatMap((n) => [true, false].map(async (farbe) => {
    const t = await texLader.loadAsync(D.texturen[n][farbe ? "farbe" : "normal"]);
    t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 8;
    if (farbe) t.colorSpace = T.SRGBColorSpace;
    texturen[n + (farbe ? "_f" : "_n")] = t;
  })));
  const namen = Object.keys(D.modelle);
  await Promise.all(namen.map(async (n) => { vorlagen[n] = await modellLaden(n); }));
}
function vorlage(modell, kaputt) {
  return vorlagen[modell + (kaputt ? "_kaputt" : "")] || vorlagen[modell];
}

// ------------------------------------------------------------------ Teile in der Szene
const objekte = new Map();   // uid -> Object3D
const GRAD = Math.PI / 180;
function transformSetzen(obj, t) {
  obj.position.set(t.pos[0], t.pos[1], t.pos[2]);
  obj.rotation.set(t.dreh[0] * GRAD, t.dreh[1] * GRAD, t.dreh[2] * GRAD, "YXZ");
  obj.updateMatrixWorld(true);
  const achse = VORRANG_ACHSE[t.modell];
  if (achse) {
    const v = vorrang(obj, achse);
    obj.traverse((o) => { if (o.isMesh && o.userData.matName.startsWith("holz")) o.material = vorrangMaterial(o.userData.matName, v); });
  }
}
function objektBauen(t) {
  const v = vorlage(t.modell, t.kaputt);
  if (!v) return null;
  const obj = v.clone();
  obj.userData.uid = t.uid;
  obj.traverse((o) => { o.userData.uid = t.uid; if (o.isMesh) o.userData.matName = o.userData.matName || o.material.name; });
  transformSetzen(obj, t);
  return obj;
}
function abgleichen() {
  const da = new Set();
  for (const t of zustand.teile) {
    da.add(t.uid);
    let obj = objekte.get(t.uid);
    const schluessel = t.modell + (t.kaputt ? "_k" : "");
    if (obj && obj.userData.schluessel !== schluessel) { gebaeudeGruppe.remove(obj); obj = null; }
    if (!obj) {
      obj = objektBauen(t);
      if (!obj) continue;
      obj.userData.schluessel = schluessel;
      objekte.set(t.uid, obj);
      gebaeudeGruppe.add(obj);
    } else transformSetzen(obj, t);
  }
  for (const [uid, obj] of objekte) if (!da.has(uid)) { gebaeudeGruppe.remove(obj); objekte.delete(uid); }
  sichtbarkeit();
  infoZeigen();
  markierungen();
}
function sichtbarkeit() {
  for (const t of zustand.teile) {
    const o = objekte.get(t.uid);
    if (o) o.visible = !zustand.durchsicht || t.pos[1] <= zustand.ebene + 0.01;
  }
}

// ------------------------------------------------------------------ Vorschau (Geist) und Markierungen
const geistMat = new T.MeshBasicMaterial({ color: 0xd49a5f, transparent: true, opacity: 0.45, depthWrite: false });
const geistKante = new T.LineBasicMaterial({ color: 0x8a5527 });
let geist = null, geistSchluessel = "";
function geistAktualisieren() {
  const s = zustand.modell + (zustand.kaputt ? "_k" : "");
  if (s !== geistSchluessel) {
    if (geist) szene.remove(geist);
    const v = vorlage(zustand.modell, zustand.kaputt);
    geist = v ? v.clone() : new T.Group();
    geist.traverse((o) => { if (o.isMesh) { o.material = geistMat; o.castShadow = false; o.renderOrder = 5; } });
    geistSchluessel = s;
    szene.add(geist);
  }
  geist.visible = zustand.werkzeug === "setzen" && zeiger.aufLeinwand && zeiger.punkt !== null;
  if (geist.visible) {
    geist.position.copy(zeiger.punkt);
    geist.rotation.set(zustand.dreh[0] * GRAD, zustand.dreh[1] * GRAD, zustand.dreh[2] * GRAD, "YXZ");
  }
}
const markeAuswahl = new T.BoxHelper(undefined, 0xd4a017);
const markeZeiger = new T.BoxHelper(undefined, 0xffffff);
markeAuswahl.visible = markeZeiger.visible = false;
szene.add(markeAuswahl, markeZeiger);
function markierungen() {
  const a = zustand.auswahl !== null && objekte.get(zustand.auswahl);
  markeAuswahl.visible = !!a;
  if (a) markeAuswahl.setFromObject(a);
  const z = zustand.werkzeug !== "setzen" && zeiger.ueber !== null && objekte.get(zeiger.ueber);
  markeZeiger.visible = !!z;
  if (z) {
    markeZeiger.setFromObject(z);
    markeZeiger.material.color.set(zustand.werkzeug === "loeschen" ? 0xe74c3c : 0xffffff);
  }
}

// ------------------------------------------------------------------ Zeiger
const zeiger = { punkt: null, ueber: null, aufLeinwand: false, unten: null };
const strahl = new T.Raycaster();
const ndc = new T.Vector2();
function strahlSetzen(e) {
  const r = leinwand.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  strahl.setFromCamera(ndc, kamera);
}
function rasterPunkt() {
  const ebene = new T.Plane(new T.Vector3(0, 1, 0), -zustand.ebene);
  const p = new T.Vector3();
  if (!strahl.ray.intersectPlane(ebene, p)) return null;
  const r = zustand.raster;
  p.x = runden(Math.round(p.x / r) * r); p.z = runden(Math.round(p.z / r) * r); p.y = zustand.ebene;
  return p;
}
function teilUnterZeiger() {
  const sichtbar = [...objekte.values()].filter((o) => o.visible);
  const treffer = strahl.intersectObjects(sichtbar, true);
  for (const h of treffer) if (h.object.userData.uid !== undefined && h.object.material !== geistMat) return h.object.userData.uid;
  return null;
}
leinwand.addEventListener("pointermove", (e) => {
  zeiger.aufLeinwand = true;
  strahlSetzen(e);
  zeiger.punkt = rasterPunkt();
  zeiger.ueber = zustand.werkzeug === "setzen" ? null : teilUnterZeiger();
  if (zeiger.punkt) { kreuz.position.copy(zeiger.punkt); }
  kreuz.visible = zustand.werkzeug === "setzen" && !!zeiger.punkt;
  geistAktualisieren();
  markierungen();
  infoZeigen();
});
leinwand.addEventListener("pointerleave", () => { zeiger.aufLeinwand = false; kreuz.visible = false; geistAktualisieren(); });
leinwand.addEventListener("pointerdown", (e) => { zeiger.unten = { x: e.clientX, y: e.clientY, knopf: e.button }; });
leinwand.addEventListener("pointerup", (e) => {
  const u = zeiger.unten; zeiger.unten = null;
  if (!u || u.knopf !== 0 || Math.hypot(e.clientX - u.x, e.clientY - u.y) > 5) return;   // gezogen = Ansicht gedreht
  strahlSetzen(e);
  zeiger.punkt = rasterPunkt();
  const uid = teilUnterZeiger();
  if (e.altKey) { if (uid !== null) uebernehmen(uid); return; }
  if (zustand.werkzeug === "setzen") { if (zeiger.punkt) setzen(zeiger.punkt); }
  else if (zustand.werkzeug === "loeschen") { if (uid !== null) loeschen(uid); }
  else { zustand.auswahl = uid; markierungen(); infoZeigen(); }
});
leinwand.addEventListener("contextmenu", (e) => e.preventDefault());

// ------------------------------------------------------------------ Bearbeiten
function runden(x) { return Math.round(x * 1000) / 1000; }
function normWinkel(w) { return ((Math.round(w) % 360) + 360) % 360; }
function merken() {
  verlauf.push(JSON.stringify(zustand.teile));
  if (verlauf.length > 200) verlauf.shift();
  wiederholen.length = 0;
  zustand.geaendert = true;
  $("ungesichert").hidden = false;
}
function setzen(p) {
  merken();
  const t = { uid: naechsteUid++, modell: zustand.modell, kaputt: zustand.kaputt, pos: [p.x, p.y, p.z], dreh: [...zustand.dreh] };
  zustand.teile.push(t);
  abgleichen();
}
function loeschen(uid) {
  merken();
  zustand.teile = zustand.teile.filter((t) => t.uid !== uid);
  if (zustand.auswahl === uid) zustand.auswahl = null;
  zeiger.ueber = null;
  abgleichen();
}
function uebernehmen(uid) {
  const t = zustand.teile.find((x) => x.uid === uid);
  if (!t) return;
  zustand.modell = t.modell; zustand.dreh = [...t.dreh]; zustand.kaputt = t.kaputt;
  $("kaputt").checked = t.kaputt;
  werkzeugWaehlen("setzen");
  ablageMarkieren();
  meldung("Übernommen: " + teilName(t.modell));
}
function ausgewaehlt() { return zustand.teile.find((t) => t.uid === zustand.auswahl); }
function drehen(achse, schritt) {
  const t = zustand.werkzeug === "bearbeiten" && ausgewaehlt();
  if (t) { merken(); t.dreh[achse] = normWinkel(t.dreh[achse] + schritt); abgleichen(); }
  else { zustand.dreh[achse] = normWinkel(zustand.dreh[achse] + schritt); geistAktualisieren(); infoZeigen(); }
}
function verschieben(dx, dy, dz) {
  const t = ausgewaehlt();
  if (!t) return;
  merken();
  const r = zustand.raster;
  t.pos = [runden(t.pos[0] + dx * r), runden(t.pos[1] + dy * r), runden(t.pos[2] + dz * r)];
  abgleichen();
}
function rueckgaengig() {
  if (!verlauf.length) return;
  wiederholen.push(JSON.stringify(zustand.teile));
  zustand.teile = JSON.parse(verlauf.pop());
  zustand.geaendert = true; $("ungesichert").hidden = false;
  abgleichen();
}
function wiederherstellen() {
  if (!wiederholen.length) return;
  verlauf.push(JSON.stringify(zustand.teile));
  zustand.teile = JSON.parse(wiederholen.pop());
  abgleichen();
}
function ebeneSetzen(y) {
  zustand.ebene = Math.max(0, runden(y));
  $("ebene-wert").textContent = String(zustand.ebene).replace(".", ",") + " m";
  ebeneGitter.position.y = zustand.ebene + 0.003;
  ebeneGitter.visible = zustand.ebene > 0;
  sichtbarkeit();
}
function werkzeugWaehlen(w) {
  zustand.werkzeug = w;
  document.querySelectorAll("[data-werkzeug]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.werkzeug === w)));
  if (w !== "bearbeiten") zustand.auswahl = null;
  zeiger.ueber = null;
  kreuz.visible = false;
  geistAktualisieren(); markierungen(); infoZeigen();
}

// ------------------------------------------------------------------ Tasten und Knöpfe
document.addEventListener("keydown", (e) => {
  if (e.target.closest && e.target.closest("input, textarea, select")) return;
  if (!$("fenster").hidden) { if (e.key === "Escape") fensterZu(); return; }
  const strg = e.ctrlKey || e.metaKey;
  const k = e.key.toLowerCase();
  if (strg && k === "z") { e.preventDefault(); e.shiftKey ? wiederherstellen() : rueckgaengig(); return; }
  if (strg && k === "y") { e.preventDefault(); wiederherstellen(); return; }
  if (strg && k === "s") { e.preventDefault(); speichern(); return; }
  if (strg && k === "d" && ausgewaehlt()) {
    e.preventDefault(); merken();
    const t = ausgewaehlt(), n = { ...t, uid: naechsteUid++, pos: [t.pos[0] + zustand.raster, t.pos[1], t.pos[2]], dreh: [...t.dreh] };
    zustand.teile.push(n); zustand.auswahl = n.uid; abgleichen(); return;
  }
  if (strg) return;
  const s = e.shiftKey ? -90 : 90;
  const sel = zustand.werkzeug === "bearbeiten" && ausgewaehlt();
  switch (k) {
    case "r": drehen(1, s); break;
    case "t": drehen(2, s); break;
    case "g": drehen(0, s); break;
    case "k":
      if (sel) { merken(); sel.kaputt = !sel.kaputt; abgleichen(); }
      else { zustand.kaputt = !zustand.kaputt; $("kaputt").checked = zustand.kaputt; geistAktualisieren(); }
      break;
    case "q": case "pagedown": if (sel) verschieben(0, -1, 0); else ebeneSetzen(zustand.ebene - 1); break;
    case "e": case "pageup": if (sel) verschieben(0, 1, 0); else ebeneSetzen(zustand.ebene + 1); break;
    case "1": werkzeugWaehlen("setzen"); break;
    case "2": werkzeugWaehlen("bearbeiten"); break;
    case "3": werkzeugWaehlen("loeschen"); break;
    case "delete": case "backspace":
      if (sel) loeschen(sel.uid); else if (zeiger.ueber !== null) loeschen(zeiger.ueber); break;
    case "escape": zustand.auswahl = null; markierungen(); infoZeigen(); break;
    case "arrowleft": case "arrowright": case "arrowup": case "arrowdown": {
      if (!sel) return;
      e.preventDefault();
      // Pfeile relativ zur Blickrichtung, auf die nächste Rasterachse gerundet
      const vor = new T.Vector3(); kamera.getWorldDirection(vor); vor.y = 0; vor.normalize();
      const rechts = new T.Vector3(-vor.z, 0, vor.x);
      const r = k === "arrowup" ? vor : k === "arrowdown" ? vor.clone().negate() : k === "arrowright" ? rechts : rechts.clone().negate();
      if (Math.abs(r.x) >= Math.abs(r.z)) verschieben(Math.sign(r.x), 0, 0); else verschieben(0, 0, Math.sign(r.z));
      break;
    }
    default: return;
  }
});
document.querySelectorAll("[data-werkzeug]").forEach((b) => b.addEventListener("click", () => werkzeugWaehlen(b.dataset.werkzeug)));
$("k-drehen").addEventListener("click", () => drehen(1, 90));
$("k-kippen").addEventListener("click", () => drehen(2, 90));
$("k-zurueck").addEventListener("click", rueckgaengig);
$("k-hoch").addEventListener("click", () => ebeneSetzen(zustand.ebene + 1));
$("k-runter").addEventListener("click", () => ebeneSetzen(zustand.ebene - 1));
$("raster").addEventListener("change", (e) => { zustand.raster = parseFloat(e.target.value); });
$("kaputt").addEventListener("change", (e) => { zustand.kaputt = e.target.checked; geistAktualisieren(); });
$("durchsicht").addEventListener("change", (e) => { zustand.durchsicht = e.target.checked; sichtbarkeit(); });
$("name").addEventListener("input", (e) => { zustand.name = e.target.value; zustand.geaendert = true; $("ungesichert").hidden = false; });

// ------------------------------------------------------------------ Ablage (Teile-Liste mit Vorschaubildern)
const NAMEN = {};
KATALOG.forEach(([, teile]) => teile.forEach(([id, name]) => { if (!NAMEN[id]) NAMEN[id] = name; }));
function teilName(id) { return NAMEN[id] || id; }
function ablageBauen() {
  const ablage = $("ablage");
  ablage.textContent = "";
  KATALOG.forEach(([gruppe, teile]) => {
    const h = document.createElement("h2"); h.textContent = gruppe; ablage.appendChild(h);
    const raster = document.createElement("div"); raster.className = "teile";
    teile.forEach(([id, name, mass, dreh]) => {
      if (!D.modelle[id]) return;
      const b = document.createElement("button");
      b.className = "teil"; b.dataset.modell = id; b.dataset.dreh = JSON.stringify(dreh || [0, 0, 0]);
      b.setAttribute("aria-pressed", "false");
      const bild = document.createElement("div"); bild.className = "platz";
      const t = document.createElement("span"); t.textContent = name;
      b.append(bild, t);
      if (mass) { const m = document.createElement("small"); m.textContent = mass; b.appendChild(m); }
      b.title = name + (mass ? " " + mass : "") + " (" + id + ")";
      b.addEventListener("click", () => {
        zustand.modell = id; zustand.dreh = dreh ? [...dreh] : [0, 0, 0];
        werkzeugWaehlen("setzen"); ablageMarkieren();
      });
      raster.appendChild(b);
    });
    ablage.appendChild(raster);
  });
  ablageMarkieren();
}
function ablageMarkieren() {
  document.querySelectorAll(".teil").forEach((b) => {
    const gleich = b.dataset.modell === zustand.modell && b.dataset.dreh === JSON.stringify(zustand.dreh);
    b.setAttribute("aria-pressed", String(gleich));
  });
}
// Vorschaubilder einmal rendern (eigener kleiner Renderer, damit die Hauptansicht unberührt bleibt)
function vorschaubilder() {
  const r = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  r.setSize(160, 128); r.toneMapping = T.ACESFilmicToneMapping;
  const s = new T.Scene();
  s.add(new T.HemisphereLight(0xffffff, 0x666655, 1.4));
  const l = new T.DirectionalLight(0xffffff, 2.2); l.position.set(3, 5, 4); s.add(l);
  const k = new T.PerspectiveCamera(30, 160 / 128, 0.05, 100);
  const fertig = {};
  document.querySelectorAll(".teil").forEach((b) => {
    const id = b.dataset.modell, dreh = JSON.parse(b.dataset.dreh), schl = id + b.dataset.dreh;
    if (!fertig[schl]) {
      const o = vorlagen[id].clone();
      o.rotation.set(dreh[0] * GRAD, dreh[1] * GRAD, dreh[2] * GRAD, "YXZ");
      s.add(o);
      const box = new T.Box3().setFromObject(o), mitte = box.getCenter(new T.Vector3()), gr = box.getSize(new T.Vector3()).length();
      k.position.copy(mitte).add(new T.Vector3(0.75, 0.55, 1).normalize().multiplyScalar(gr * 1.55 + 0.2));
      k.lookAt(mitte);
      r.render(s, k);
      fertig[schl] = r.domElement.toDataURL("image/png");
      s.remove(o);
    }
    const img = document.createElement("img"); img.alt = ""; img.src = fertig[schl];
    b.replaceChild(img, b.firstChild);
  });
  r.dispose();
}

// ------------------------------------------------------------------ Info
function infoZeigen() {
  const p = zeiger.punkt;
  const fmt = (x) => String(runden(x)).replace(".", ",");
  let s = zustand.teile.length + " Teile";
  const t = ausgewaehlt();
  if (t) s += " · Auswahl: " + teilName(t.modell) + (t.kaputt ? " (kaputt)" : "") + " bei " + t.pos.map(fmt).join(" | ") + " · Drehung " + t.dreh.join("/") + "°";
  else {
    s += " · " + teilName(zustand.modell) + (zustand.kaputt ? " (kaputt)" : "") + " · Drehung " + zustand.dreh.join("/") + "°";
    if (p && zeiger.aufLeinwand) s += " · Punkt " + fmt(p.x) + " | " + fmt(p.y) + " | " + fmt(p.z);
  }
  $("info").textContent = s;
}
let meldungZeit = 0;
function meldung(text) {
  const m = $("meldung"); m.textContent = text; m.hidden = false;
  clearTimeout(meldungZeit); meldungZeit = setTimeout(() => (m.hidden = true), 2600);
}

// ------------------------------------------------------------------ Format (wie gebaeude.gd)
function alsDaten() {
  return {
    format: "rpg_gebaeude", version: 1, name: zustand.name.trim() || "Ohne Namen", raster: 1.0,
    teile: zustand.teile.map((t) => ({ modell: t.modell, kaputt: t.kaputt, pos: t.pos.map(runden), dreh: t.dreh.map(normWinkel) })),
  };
}
function alsJson(d) {
  // ein Teil je Zeile: gut lesbar und in Git gut vergleichbar
  const kopf = JSON.stringify({ format: d.format, version: d.version, name: d.name, raster: d.raster }).slice(0, -1);
  return kopf + ',"teile":[\n' + d.teile.map((t) => " " + JSON.stringify(t)).join(",\n") + "\n]}\n";
}
function ausDaten(d, id) {
  if (!d || d.format !== "rpg_gebaeude" || !Array.isArray(d.teile)) throw new Error("Das ist keine Gebäude-Datei (format rpg_gebaeude fehlt).");
  zustand.teile = d.teile.map((t) => ({
    uid: naechsteUid++, modell: String(t.modell), kaputt: !!t.kaputt,
    pos: (t.pos || [0, 0, 0]).map(Number), dreh: (t.dreh || [0, 0, 0]).map(Number),
  }));
  zustand.name = d.name || "Ohne Namen"; zustand.id = id || null; zustand.auswahl = null;
  $("name").value = zustand.name;
  verlauf.length = 0; wiederholen.length = 0;
  zustand.geaendert = false; $("ungesichert").hidden = true;
  const fehlend = [...new Set(zustand.teile.filter((t) => !D.modelle[t.modell]).map((t) => t.modell))];
  abgleichen();
  if (fehlend.length) meldung("Unbekannte Teile übersprungen: " + fehlend.join(", "));
  kameraAufGebaeude();
}
function kameraAufGebaeude() {
  if (!zustand.teile.length) return;
  const box = new T.Box3().setFromObject(gebaeudeGruppe);
  if (box.isEmpty()) return;
  const mitte = box.getCenter(new T.Vector3()), gr = Math.max(4, box.getSize(new T.Vector3()).length());
  steuerung.target.copy(mitte);
  kamera.position.copy(mitte).add(new T.Vector3(0.75, 0.6, 1).normalize().multiplyScalar(gr * 1.25));
  steuerung.update();
}
function kennung(name) {
  const s = name.toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60);
  return s || "gebaeude";
}

// ------------------------------------------------------------------ Speicher: geteilte Datenbank im Artifact, sonst Browser
const speicher = {
  art: "lokal", db: null, liste: [], beiAenderung: null,
  async start() {
    try {
      if (window.claude && window.claude.use) {
        const db = await window.claude.use("db");
        if (db) {
          this.db = db; this.art = "db";
          let zeit = setTimeout(() => this.lokalLaden(), 10000);
          db.collection("gebaeude").onSnapshot((snap) => {
            clearTimeout(zeit); zeit = null;
            this.liste = snap.docs.map((d) => ({ id: d.id, ...d.data() })).sort((a, b) => (b.geaendert || "").localeCompare(a.geaendert || ""));
            this.beiAenderung && this.beiAenderung();
          }, (f) => { meldung("Gespeicherte Gebäude konnten nicht geladen werden (" + f.code + ")."); this.lokalLaden(); });
          ortZeigen();
          return;
        }
      }
    } catch (e) { /* ohne claude.ai: Browser-Speicher */ }
    this.lokalLaden();
  },
  lokalLaden() {
    this.art = "lokal"; this.db = null;
    try { this.liste = JSON.parse(localStorage.getItem("gebaeude_baukasten") || "[]"); } catch (e) { this.liste = []; }
    ortZeigen();
    this.beiAenderung && this.beiAenderung();
  },
  lokalSchreiben() {
    try { localStorage.setItem("gebaeude_baukasten", JSON.stringify(this.liste)); return true; } catch (e) { return false; }
  },
  async speichern(id, eintrag) {
    if (this.db) { await this.db.collection("gebaeude").doc(id).set(eintrag); return; }
    this.liste = this.liste.filter((x) => x.id !== id);
    this.liste.unshift({ id, ...eintrag });
    if (!this.lokalSchreiben()) throw new Error("Der Browser erlaubt hier keinen Speicher. Nutze „Exportieren“.");
  },
  async loeschen(id) {
    if (this.db) { await this.db.collection("gebaeude").doc(id).delete(); return; }
    this.liste = this.liste.filter((x) => x.id !== id);
    this.lokalSchreiben();
  },
};
function ortZeigen() {
  $("speicherort").textContent = speicher.art === "db" ? "Gespeichert wird in diesem Artifact" : "Gespeichert wird in diesem Browser";
}
async function speichern() {
  const d = alsDaten();
  if (!d.teile.length) { meldung("Das Gebäude ist noch leer."); return; }
  const id = zustand.id || kennung(d.name);
  const vorhanden = speicher.liste.find((x) => x.id === id);
  if (!zustand.id && vorhanden) { fensterGebaeude("Es gibt schon ein Gebäude „" + vorhanden.name + "“. Bitte gib einen anderen Namen ein oder lade es zuerst."); return; }
  try {
    await speicher.speichern(id, { name: d.name, anzahl: d.teile.length, geaendert: new Date().toISOString(), json: JSON.stringify(d) });
    zustand.id = id; zustand.geaendert = false; $("ungesichert").hidden = true;
    meldung("Gespeichert: " + d.name);
  } catch (e) { meldung("Speichern fehlgeschlagen: " + (e.message || e.code || e)); }
}

// ------------------------------------------------------------------ Fenster: Gebäude, Export, Import
function fensterZu() { $("fenster").hidden = true; speicher.beiAenderung = null; }
function fensterAuf(bauen) { const k = $("karte"); k.textContent = ""; bauen(k); $("fenster").hidden = false; }
$("fenster").addEventListener("click", (e) => { if (e.target.id === "fenster") fensterZu(); });
function el(tag, attr, ...kinder) {
  const e = document.createElement(tag);
  Object.entries(attr || {}).forEach(([k, v]) => (k === "on" ? Object.entries(v).forEach(([n, f]) => e.addEventListener(n, f)) : e.setAttribute(k, v)));
  kinder.forEach((c) => e.append(c));
  return e;
}
function datum(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("de-DE") + " " + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}
function verwerfenFrage(weiter) {
  if (!zustand.geaendert || !zustand.teile.length) { weiter(); return; }
  fensterAuf((k) => k.append(
    el("h3", {}, "Änderungen verwerfen?"),
    el("p", {}, "„" + zustand.name + "“ hat ungespeicherte Änderungen."),
    el("div", { class: "reihe" },
      el("button", { class: "knopf haupt", on: { click: async () => { await speichern(); fensterZu(); weiter(); } } }, "Erst speichern"),
      el("button", { class: "knopf gefahr", on: { click: () => { fensterZu(); weiter(); } } }, "Verwerfen"),
      el("button", { class: "knopf", on: { click: fensterZu } }, "Abbrechen"))));
}
function fensterGebaeude(hinweis) {
  fensterAuf((k) => {
    const liste = el("div", { class: "liste" });
    const zeichnen = () => {
      liste.textContent = "";
      const eigene = speicher.liste;
      if (!eigene.length) liste.append(el("div", { class: "leer" }, "Noch keine gespeicherten Gebäude. Bau etwas und drück „Speichern“."));
      eigene.forEach((g) => {
        const loeschKnopf = el("button", { class: "knopf gefahr" }, "Löschen");
        loeschKnopf.addEventListener("click", async () => {
          if (loeschKnopf.dataset.sicher) { await speicher.loeschen(g.id); if (zustand.id === g.id) zustand.id = null; zeichnen(); meldung("Gelöscht: " + g.name); }
          else { loeschKnopf.dataset.sicher = "1"; loeschKnopf.textContent = "Wirklich löschen?"; }
        });
        liste.append(el("div", { class: "eintrag" + (g.id === zustand.id ? " aktiv" : "") },
          el("div", { class: "t" }, el("b", {}, g.name), el("small", {}, g.anzahl + " Teile · " + datum(g.geaendert))),
          el("button", { class: "knopf", on: { click: () => verwerfenFrage(() => { try { ausDaten(JSON.parse(g.json), g.id); fensterZu(); } catch (e) { meldung(e.message); } }) } }, "Laden"),
          loeschKnopf));
      });
      liste.append(el("h3", { style: "font-size:14px;margin-top:8px" }, "Vorlagen"));
      D.vorlagen.forEach((v) => liste.append(el("div", { class: "eintrag" },
        el("div", { class: "t" }, el("b", {}, v.name), el("small", {}, v.teile.length + " Teile · aus dem Projekt")),
        el("button", { class: "knopf", on: { click: () => verwerfenFrage(() => { ausDaten(v, null); fensterZu(); }) } }, "Laden"))));
    };
    speicher.beiAenderung = zeichnen;
    k.append(el("h3", {}, "Gebäude"));
    if (hinweis) k.append(el("p", { class: "gefahr" }, hinweis));
    k.append(el("p", {}, speicher.art === "db"
      ? "Alles, was du hier speicherst, liegt in diesem Artifact. Claude kann es von dort direkt ins Spiel übernehmen."
      : "Gespeichert wird nur in diesem Browser. Für Godot nutze „Exportieren“ und leg die Datei nach godot/data/gebaeude/."), liste,
      el("div", { class: "reihe" }, el("button", { class: "knopf", on: { click: fensterZu } }, "Schließen")));
    zeichnen();
  });
}
$("k-gebaeude").addEventListener("click", () => fensterGebaeude());
$("k-speichern").addEventListener("click", speichern);
$("k-neu").addEventListener("click", () => verwerfenFrage(() => {
  ausDaten({ format: "rpg_gebaeude", version: 1, name: "Neues Gebäude", teile: [] }, null);
  ebeneSetzen(0);
}));
$("k-export").addEventListener("click", () => fensterAuf((k) => {
  const d = alsDaten(), text = alsJson(d), datei = kennung(d.name) + ".json";
  const feld = el("textarea", { id: "export-text", readonly: "", spellcheck: "false" }); feld.value = text;
  const reihe = el("div", { class: "reihe" });
  reihe.append(el("button", { class: "knopf haupt", on: { click: async (e) => {
    try { await navigator.clipboard.writeText(text); e.target.textContent = "Kopiert"; } catch (_) { feld.focus(); feld.select(); e.target.textContent = "Markiert: Strg+C"; }
  } } }, "Kopieren"));
  const dateiKnopf = el("button", { class: "knopf" }, "Als Datei speichern");
  dateiKnopf.addEventListener("click", async () => {
    try {
      const dl = window.claude && window.claude.use ? await window.claude.use("downloads") : null;
      if (dl) { await dl.save({ filename: datei, data: text }); return; }
    } catch (e) { if (e && e.code === "declined") return; }
    const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: "application/json" })), download: datei });
    document.body.appendChild(a); a.click(); a.remove();
  });
  reihe.append(dateiKnopf, el("button", { class: "knopf", on: { click: fensterZu } }, "Schließen"));
  k.append(el("h3", {}, "Exportieren"),
    el("p", {}, "Für Godot: Datei als " + datei + " nach godot/data/gebaeude/ legen. Ein Node mit gebaeude.gd (Feld „datei“) baut das Gebäude dann auf."),
    feld, reihe);
}));
$("k-import").addEventListener("click", () => fensterAuf((k) => {
  const feld = el("textarea", { id: "import-text", spellcheck: "false", placeholder: "JSON hier einfügen …" });
  const dateiWahl = el("input", { type: "file", id: "import-datei", accept: ".json,application/json" });
  dateiWahl.addEventListener("change", async () => { if (dateiWahl.files[0]) feld.value = await dateiWahl.files[0].text(); });
  k.append(el("h3", {}, "Importieren"), el("p", {}, "Eine Gebäude-Datei auswählen oder ihren Inhalt einfügen."), dateiWahl, feld,
    el("div", { class: "reihe" },
      el("button", { class: "knopf haupt", on: { click: () => verwerfenFrage(() => {
        try { ausDaten(JSON.parse(feld.value), null); fensterZu(); meldung("Importiert: " + zustand.name); }
        catch (e) { meldung(e instanceof SyntaxError ? "Kein gültiges JSON." : e.message); }
      }) } }, "Laden"),
      el("button", { class: "knopf", on: { click: fensterZu } }, "Abbrechen")));
}));
window.addEventListener("beforeunload", (e) => { if (zustand.geaendert && zustand.teile.length) e.preventDefault(); });

// ------------------------------------------------------------------ Schleife
function groesse() {
  const r = leinwand.parentElement.getBoundingClientRect();
  renderer.setSize(r.width, r.height, false);
  kamera.aspect = r.width / Math.max(1, r.height);
  kamera.updateProjectionMatrix();
}
new ResizeObserver(groesse).observe(leinwand.parentElement);
function schleife() {
  steuerung.update();
  renderer.render(szene, kamera);
  requestAnimationFrame(schleife);
}

// ------------------------------------------------------------------ Start
(async function start() {
  ablageBauen();
  groesse();
  schleife();
  try {
    await alleModelleLaden();
  } catch (e) { $("laden").textContent = "Modelle konnten nicht geladen werden: " + e; return; }
  $("laden").hidden = true;
  vorschaubilder();
  if (D.vorlagen.length) ausDaten(D.vorlagen[0], null);
  ebeneSetzen(0);
  geistAktualisieren();
  infoZeigen();
  speicher.start();
  window.BAUKASTEN = { zustand, alsDaten, ausDaten, setzen: (x, y, z) => setzen(new T.Vector3(x, y, z)) };   // für Tests
})();
})();
