// ===== 3D-Vorschau (WebGL2, ohne Bibliothek) =====
function mat4Perspektive(fov, asp, near, far) {
  const f = 1 / Math.tan(fov / 2), nf = 1 / (near - far);
  return new Float32Array([f / asp, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0]);
}
function mat4LookAt(e, z, u) {
  let fx = e[0] - z[0], fy = e[1] - z[1], fz = e[2] - z[2];
  let l = Math.hypot(fx, fy, fz); fx /= l; fy /= l; fz /= l;
  let sx = u[1] * fz - u[2] * fy, sy = u[2] * fx - u[0] * fz, sz = u[0] * fy - u[1] * fx;
  l = Math.hypot(sx, sy, sz); sx /= l; sy /= l; sz /= l;
  const ux = fy * sz - fz * sy, uy = fz * sx - fx * sz, uz = fx * sy - fy * sx;
  return new Float32Array([sx, ux, fx, 0, sy, uy, fy, 0, sz, uz, fz, 0,
    -(sx * e[0] + sy * e[1] + sz * e[2]), -(ux * e[0] + uy * e[1] + uz * e[2]), -(fx * e[0] + fy * e[1] + fz * e[2]), 1]);
}
function mat4Mul(a, b) {
  const o = new Float32Array(16);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
    let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
    o[i * 4 + j] = s;
  }
  return o;
}

class Vorschau3D {
  constructor(canvas) {
    this.c = canvas;
    const gl = canvas.getContext("webgl2", { antialias: true, alpha: false });
    if (!gl) { this.fehler = "WebGL2 nicht verfügbar"; return; }
    this.gl = gl;
    const vs = `#version 300 es
      in vec3 pos; in vec3 nrm; in vec3 col;
      uniform mat4 mvp; uniform float ueberh;
      out vec3 vN; out vec3 vC; out float vD; out float vH;
      void main(){ vec3 p = vec3(pos.x, pos.y * ueberh, pos.z); gl_Position = mvp * vec4(p,1.0);
        vN = normalize(vec3(nrm.x, nrm.y / max(ueberh,0.01), nrm.z)); vC = col; vD = gl_Position.w; vH = pos.y; }`;
    const fs = `#version 300 es
      precision highp float;
      in vec3 vN; in vec3 vC; in float vD; in float vH;
      uniform vec3 licht; uniform vec4 farbe; uniform float nebel;
      out vec4 o;
      void main(){
        bool gelaende = farbe.a > 0.99;
        vec3 c = gelaende ? vC : farbe.rgb;
        float l = gelaende ? max(dot(normalize(vN), licht), 0.0) * 0.85 + 0.3 : 1.0;
        vec3 r = c * l;
        float f = 1.0 - exp(-vD * nebel);
        r = mix(r, vec3(0.62,0.7,0.8), clamp(f,0.0,0.8));
        o = vec4(r, gelaende ? 1.0 : farbe.a);
      }`;
    const sh = (t, s) => { const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x);
      if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; };
    const pr = gl.createProgram();
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr);
    this.pr = pr;
    this.loc = {};
    for (const n of ["mvp", "ueberh", "licht", "farbe", "nebel"]) this.loc[n] = gl.getUniformLocation(pr, n);
    this.attr = { pos: gl.getAttribLocation(pr, "pos"), nrm: gl.getAttribLocation(pr, "nrm"), col: gl.getAttribLocation(pr, "col") };
    this.buf = { pos: gl.createBuffer(), nrm: gl.createBuffer(), col: gl.createBuffer(), idx: gl.createBuffer(), wasser: gl.createBuffer() };
    this.vao = gl.createVertexArray();
    this.vaoW = gl.createVertexArray();
    // Wasserfläche
    gl.bindVertexArray(this.vaoW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf.wasser);
    const W = 8000;
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-W, 0, -W, W, 0, -W, W, 0, W, -W, 0, -W, W, 0, W, -W, 0, W]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(this.attr.pos); gl.vertexAttribPointer(this.attr.pos, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    this.kam = { yaw: 0.6, pitch: 0.75, dist: 5200, ziel: [0, 0, 0] };
    this.ueberh = 1.5;
    this._maus();
  }

  // H: Höhen (N x N), farben: Uint8 RGBA (N x N), M: Gitterauflösung der Vorschau
  setzeGelaende(H, N, zelle, farben, M = 512) {
    if (!this.gl) return;
    const gl = this.gl, schritt = N / M, groesse = N * zelle;
    const pos = new Float32Array(M * M * 3), nrm = new Float32Array(M * M * 3), col = new Float32Array(M * M * 3);
    const h = (i, j) => H[Math.min(N - 1, Math.round(j * schritt)) * N + Math.min(N - 1, Math.round(i * schritt))];
    for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
      const k = j * M + i, hh = h(i, j);
      pos[k * 3] = i / (M - 1) * groesse - groesse / 2; pos[k * 3 + 1] = Math.max(hh, -60); pos[k * 3 + 2] = j / (M - 1) * groesse - groesse / 2;
      const gx = (h(Math.min(M - 1, i + 1), j) - h(Math.max(0, i - 1), j)) / (2 * schritt * zelle);
      const gz = (h(i, Math.min(M - 1, j + 1)) - h(i, Math.max(0, j - 1))) / (2 * schritt * zelle);
      const l = Math.hypot(gx, 1, gz);
      nrm[k * 3] = -gx / l; nrm[k * 3 + 1] = 1 / l; nrm[k * 3 + 2] = -gz / l;
      const q = (Math.min(N - 1, Math.round(j * schritt)) * N + Math.min(N - 1, Math.round(i * schritt))) * 4;
      col[k * 3] = farben[q] / 255; col[k * 3 + 1] = farben[q + 1] / 255; col[k * 3 + 2] = farben[q + 2] / 255;
    }
    if (this.M !== M) {
      const idx = new Uint32Array((M - 1) * (M - 1) * 6); let t = 0;
      for (let j = 0; j < M - 1; j++) for (let i = 0; i < M - 1; i++) {
        const a = j * M + i; idx[t++] = a; idx[t++] = a + M; idx[t++] = a + 1; idx[t++] = a + 1; idx[t++] = a + M; idx[t++] = a + M + 1;
      }
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buf.idx);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
      this.anzahl = idx.length; this.M = M;
    }
    gl.bindVertexArray(this.vao);
    for (const [n, d] of [["pos", pos], ["nrm", nrm], ["col", col]]) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buf[n]); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(this.attr[n]); gl.vertexAttribPointer(this.attr[n], 3, gl.FLOAT, false, 0, 0);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buf.idx);
    gl.bindVertexArray(null);
    this.zeichne();
  }

  zeichne() {
    const gl = this.gl; if (!gl || !this.anzahl) return;
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(this.c.clientWidth * dpr)), hgt = Math.max(1, Math.round(this.c.clientHeight * dpr));
    if (this.c.width !== w || this.c.height !== hgt) { this.c.width = w; this.c.height = hgt; }
    gl.viewport(0, 0, w, hgt);
    gl.clearColor(0.62, 0.7, 0.8, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    const k = this.kam;
    const auge = [k.ziel[0] + Math.cos(k.pitch) * Math.sin(k.yaw) * k.dist, k.ziel[1] + Math.sin(k.pitch) * k.dist, k.ziel[2] + Math.cos(k.pitch) * Math.cos(k.yaw) * k.dist];
    const mvp = mat4Mul(mat4Perspektive(0.8, w / hgt, 5, 30000), mat4LookAt(auge, k.ziel, [0, 1, 0]));
    gl.useProgram(this.pr);
    gl.uniformMatrix4fv(this.loc.mvp, false, mvp);
    gl.uniform1f(this.loc.ueberh, this.ueberh);
    const L = [-0.5, 0.75, -0.45], ll = Math.hypot(...L);
    gl.uniform3f(this.loc.licht, L[0] / ll, L[1] / ll, L[2] / ll);
    gl.uniform1f(this.loc.nebel, 0.00006);
    gl.uniform4f(this.loc.farbe, 1, 1, 1, 1);
    gl.bindVertexArray(this.vao);
    gl.drawElements(gl.TRIANGLES, this.anzahl, gl.UNSIGNED_INT, 0);
    // Wasser
    gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
    gl.uniform4f(this.loc.farbe, 0.16, 0.38, 0.58, 0.9);
    gl.bindVertexArray(this.vaoW);
    gl.disableVertexAttribArray(this.attr.nrm); gl.disableVertexAttribArray(this.attr.col);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.disable(gl.BLEND);
    gl.bindVertexArray(null);
  }

  _maus() {
    let ziehen = null;
    this.c.addEventListener("contextmenu", (e) => e.preventDefault());
    this.c.addEventListener("pointerdown", (e) => { ziehen = { x: e.clientX, y: e.clientY, b: e.button }; this.c.setPointerCapture(e.pointerId); });
    this.c.addEventListener("pointerup", () => (ziehen = null));
    this.c.addEventListener("pointermove", (e) => {
      if (!ziehen) return;
      const dx = e.clientX - ziehen.x, dy = e.clientY - ziehen.y;
      ziehen.x = e.clientX; ziehen.y = e.clientY;
      const k = this.kam;
      if (ziehen.b === 0) {
        k.yaw -= dx * 0.005; k.pitch = Math.min(1.5, Math.max(0.08, k.pitch + dy * 0.005));
      } else {
        const s = k.dist * 0.0012;
        k.ziel[0] -= (Math.cos(k.yaw) * dx - Math.sin(k.yaw) * dy) * s;
        k.ziel[2] -= (-Math.sin(k.yaw) * dx - Math.cos(k.yaw) * dy) * s;
      }
      this.zeichne();
    });
    this.c.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.kam.dist = Math.min(14000, Math.max(150, this.kam.dist * Math.exp(e.deltaY * 0.001)));
      this.zeichne();
    }, { passive: false });
  }
}
