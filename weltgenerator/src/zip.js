// ===== Minimaler ZIP-Schreiber/-Leser (ohne externe Bibliothek) =====
const CRC_TAB = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
  return t;
})();
function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = CRC_TAB[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

// dateien: [{name, daten: Uint8Array}] -> Blob (unkomprimiert, "stored")
function zipErstellen(dateien) {
  const teile = [], zentral = [];
  let offset = 0;
  const enc = new TextEncoder();
  for (const d of dateien) {
    const name = enc.encode(d.name);
    const crc = crc32(d.daten);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
    lh.setUint16(8, 0, true); lh.setUint32(14, crc, true);
    lh.setUint32(18, d.daten.length, true); lh.setUint32(22, d.daten.length, true);
    lh.setUint16(26, name.length, true);
    teile.push(lh.buffer, name, d.daten);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true);
    ch.setUint32(16, crc, true); ch.setUint32(20, d.daten.length, true); ch.setUint32(24, d.daten.length, true);
    ch.setUint16(28, name.length, true); ch.setUint32(42, offset, true);
    zentral.push(ch.buffer, name);
    offset += 30 + name.length + d.daten.length;
  }
  let zgroesse = 0;
  for (const z of zentral) zgroesse += z.byteLength;
  const ende = new DataView(new ArrayBuffer(22));
  ende.setUint32(0, 0x06054b50, true);
  ende.setUint16(8, dateien.length, true); ende.setUint16(10, dateien.length, true);
  ende.setUint32(12, zgroesse, true); ende.setUint32(16, offset, true);
  return new Blob([...teile, ...zentral, ende.buffer], { type: "application/zip" });
}

// ArrayBuffer -> {name: Uint8Array}; unterstützt "stored" und "deflate"
async function zipLesen(buf) {
  const dv = new DataView(buf);
  let e = buf.byteLength - 22;
  while (e >= 0 && dv.getUint32(e, true) !== 0x06054b50) e--;
  if (e < 0) throw new Error("Keine gültige ZIP-Datei");
  const anzahl = dv.getUint16(e + 10, true);
  let p = dv.getUint32(e + 16, true);
  const dec = new TextDecoder();
  const out = {};
  for (let k = 0; k < anzahl; k++) {
    const methode = dv.getUint16(p + 10, true);
    const csize = dv.getUint32(p + 20, true);
    const nlen = dv.getUint16(p + 28, true), xlen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
    const lho = dv.getUint32(p + 42, true);
    const name = dec.decode(new Uint8Array(buf, p + 46, nlen));
    const start = lho + 30 + dv.getUint16(lho + 26, true) + dv.getUint16(lho + 28, true);
    let daten = new Uint8Array(buf, start, csize);
    if (methode === 8) {
      const strom = new Blob([daten]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
      daten = new Uint8Array(await new Response(strom).arrayBuffer());
    }
    out[name] = daten;
    p += 46 + nlen + xlen + clen;
  }
  return out;
}
