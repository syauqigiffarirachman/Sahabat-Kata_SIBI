// Kamera & suara (HP): penerjemah isyarat -> teks dan suara/teks -> isyarat.
//
// Isyarat -> teks: MediaPipe HandLandmarker (WASM, offline) mendeteksi 21 titik
// tangan, lalu model huruf ringan (model/huruf.json, dilatih dari dataset yang
// sama dengan versi desktop, lihat tools/build_model_mobile.py) menebak hurufnya.
// Normalisasi sama persis dengan sibi/core/normalize.py.
import { ucapkan, diam, bisaDengar, dengar } from "./suara.js";
import { kunci, token, judul as judulKata, saranKata, saranKalimat, rapikan } from "./kosakata.js";

const $ = (s, el = document) => el.querySelector(s);
const getar = (ms) => {
  try {
    if (window.SibiAndroid && window.SibiAndroid.getar) window.SibiAndroid.getar(ms);
    else if (navigator.vibrate) navigator.vibrate(ms);
  } catch (e) { /* abaikan */ }
};
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const TAHAN_MS = 550;      // tahan isyarat sekian lama agar huruf diketik
const ULANG_MS = 2000;     // tahan lebih lama untuk mengetik huruf yang sama lagi
const MIN_YAKIN = 0.65;
const MAKS_FPS = 24;
const SAMBUNGAN = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];

// ------------------------------------------------------------ model
let modelHuruf = null;
async function muatModel() {
  if (modelHuruf) return modelHuruf;
  const m = await (await fetch("model/huruf.json")).json();
  m.L = m.lapisan.map(({ W, b }) => {
    const nIn = W.length, nOut = b.length, w = new Float32Array(nIn * nOut);
    for (let i = 0; i < nIn; i++) for (let j = 0; j < nOut; j++) w[i * nOut + j] = W[i][j];
    return { w, b: Float32Array.from(b), nIn, nOut };
  });
  delete m.lapisan;
  modelHuruf = m;
  return m;
}

function prediksi(m, x) {
  let a = x;
  m.L.forEach((L, li) => {
    const o = new Float32Array(L.nOut);
    for (let j = 0; j < L.nOut; j++) o[j] = L.b[j];
    for (let i = 0; i < L.nIn; i++) {
      const ai = a[i];
      if (ai === 0) continue;
      const base = i * L.nOut;
      for (let j = 0; j < L.nOut; j++) o[j] += ai * L.w[base + j];
    }
    if (li < m.L.length - 1) for (let j = 0; j < L.nOut; j++) o[j] = Math.max(0, o[j]);
    a = o;
  });
  let maks = -Infinity;
  for (const v of a) maks = Math.max(maks, v);
  let jml = 0;
  const p = a.map((v) => { const e = Math.exp(v - maks); jml += e; return e; });
  return p.map((v) => v / jml);
}

/** 21 titik MediaPipe -> 63 fitur, sama dengan sibi/core/normalize.py.
 *  Gambar dicerminkan (data latih direkam dengan tampilan cermin) dan rasio
 *  sumbu x/y disesuaikan dengan rasio kamera saat data dilatih. */
export function fitur(lm, lebar, tinggi, rasioLatih) {
  const r = (lebar / tinggi) / rasioLatih;
  const P = lm.map((p) => [(1 - p.x) * r, p.y, p.z * r]);
  const [x0, y0, z0] = P[0];
  let maks = 0;
  for (const p of P) { p[0] -= x0; p[1] -= y0; p[2] -= z0; maks = Math.max(maks, Math.hypot(p[0], p[1], p[2])); }
  if (maks < 1e-6) maks = 1;
  const out = new Float32Array(63);
  P.forEach((p, i) => { out[i * 3] = p[0] / maks; out[i * 3 + 1] = p[1] / maks; out[i * 3 + 2] = p[2] / maks; });
  return out;
}

// ------------------------------------------------------------ penstabil (dari sibi/core/sequence_buffer.py)
class PenstabilHuruf {
  constructor() { this.teks = ""; this.reset(); }
  reset() { this.cur = ""; this.mulai = 0; this.terakhir = ""; this.diketik = false; this.waktuKetik = 0; this.kosongSejak = 0; }
  update(h, yakin, now) {
    if (h === "-" || yakin < MIN_YAKIN) {
      if (!this.kosongSejak) this.kosongSejak = now;
      if (now - this.kosongSejak > 260) { this.cur = ""; this.terakhir = ""; this.diketik = false; }
      return null;
    }
    this.kosongSejak = 0;
    if (h !== this.cur) { this.cur = h; this.mulai = now; this.diketik = false; }
    const lama = now - this.mulai;
    if (!this.diketik && lama >= TAHAN_MS && (h !== this.terakhir || lama >= ULANG_MS)) {
      this.teks += h; this.terakhir = h; this.diketik = true; this.waktuKetik = now; return h;
    }
    if (this.diketik && now - this.waktuKetik >= ULANG_MS) { this.teks += h; this.waktuKetik = now; return h; }
    return null;
  }
  kemajuan(now) {
    if (!this.cur) return 0;
    return this.diketik ? Math.min(1, (now - this.waktuKetik) / ULANG_MS) : Math.min(1, (now - this.mulai) / TAHAN_MS);
  }
}

// Isyarat kata: bentuk jari (pose diam) + lintasan pergelangan (gerak).
// Port sibi/core/classifier_word.py (tebak_dengan_gerak); jaga keduanya tetap sejalan.
const JENDELA = 20;
const POLA_DIAM = {
  "11001": "SAYANG", "10001": "TELEPON", "01000": "SATU", "01100": "DUA",
  "01110": "TIGA", "11100": "TIGA", "01111": "EMPAT", "11111": "LIMA",
};
const jarak = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);

export function bentukTangan(f) {
  const X = (i) => f[i * 3], Y = (i) => f[i * 3 + 1];
  const telapak = Math.hypot(X(9), Y(9)) || 1;
  const jari = [
    jarak(X(4), Y(4), X(5), Y(5)) > 0.6 * telapak && jarak(X(4), Y(4), X(9), Y(9)) > 0.75 * telapak ? 1 : 0,
  ];
  for (const [u, s] of [[8, 6], [12, 10], [16, 14], [20, 18]]) jari.push(Math.hypot(X(u), Y(u)) > Math.hypot(X(s), Y(s)) * 1.15 ? 1 : 0);
  let minY = Infinity;
  for (let i = 5; i < 21; i++) minY = Math.min(minY, Y(i));
  const jempolAtas = Y(4) < minY - 0.15 * telapak;
  const ujung = [4, 8, 12, 16, 20];
  const cx = ujung.reduce((a, i) => a + X(i), 0) / 5, cy = ujung.reduce((a, i) => a + Y(i), 0) / 5;
  const sebar = Math.max(...ujung.map((i) => jarak(X(i), Y(i), cx, cy)));
  const kuncup = sebar < 0.4 * telapak && Math.hypot(X(8), Y(8)) > 1.2 * telapak;
  return { jari, jempolAtas, kuncup };
}

function jenisTangan(f) {
  const b = bentukTangan(f), j = b.jari, n = j[1] + j[2] + j[3] + j[4];
  if (b.kuncup) return "kuncup";
  if (n === 0) return j[0] && b.jempolAtas ? "jempol" : "kepal";
  if (n >= 4 || (n === 3 && j[0])) return "terbuka";
  if (j[1] && !j[3] && !j[4]) return "tunjuk";
  return "lain";
}

export function poseDiam(f) {
  const b = bentukTangan(f);
  if (b.kuncup) return null;
  const k = b.jari.join("");
  if (k === "10000" && b.jempolAtas) return "BAGUS";
  return POLA_DIAM[k] || null;
}

export function bolakBalik(nilai, ambang) {
  if (nilai.length < 3) return 0;
  let rendah = nilai[0], tinggi = nilai[0], arah = 0, ekstrem = 0, balik = 0;
  for (const v of nilai.slice(1)) {
    if (arah === 0) {
      rendah = Math.min(rendah, v); tinggi = Math.max(tinggi, v);
      if (v - rendah >= ambang) { arah = 1; ekstrem = v; } else if (tinggi - v >= ambang) { arah = -1; ekstrem = v; }
    } else if (arah === 1) {
      if (v > ekstrem) ekstrem = v; else if (ekstrem - v >= ambang) { arah = -1; ekstrem = v; balik++; }
    } else if (v < ekstrem) ekstrem = v; else if (v - ekstrem >= ambang) { arah = 1; ekstrem = v; balik++; }
  }
  return balik;
}

function mayoritas(daftar) {
  const n = new Map();
  for (const v of daftar) n.set(v, (n.get(v) || 0) + 1);
  let terbaik = "", jml = 0;
  for (const [v, c] of n) if (c > jml) { terbaik = v; jml = c; }
  return [terbaik, daftar.length ? jml / daftar.length : 0];
}

const rentang = (a) => Math.max(...a) - Math.min(...a);

/** frames: N x 63 fitur; gerak: N x [x, y, ukuranTelapak] pergelangan di gambar (0..1). */
export function tebakKata(frames, gerak) {
  if (frames.length < 8 || gerak.length !== frames.length) return ["-", 0];
  const x = gerak.map((g) => g[0]), y = gerak.map((g) => g[1]), s = gerak.map((g) => g[2]);
  const urut = [...s].sort((a, b) => a - b);
  const ukuran = (urut.length % 2 ? urut[urut.length >> 1] : (urut[urut.length / 2 - 1] + urut[urut.length / 2]) / 2) || 0.1;
  const rx = rentang(x), ry = rentang(y);
  let jalur = 0;
  for (let i = 1; i < x.length; i++) jalur += Math.hypot(x[i] - x[i - 1], y[i] - y[i - 1]);
  const bersih = Math.hypot(x[x.length - 1] - x[0], y[y.length - 1] - y[0]);

  const [jenis, porsi] = mayoritas(frames.map(jenisTangan));
  const ujungX = frames.map((f) => f[24]);
  const balikX = bolakBalik(x, 0.25 * ukuran), balikY = bolakBalik(y, 0.2 * ukuran);
  const balikS = bolakBalik(s, 0.08 * ukuran), balikUjung = bolakBalik(ujungX, 0.15);

  if (porsi >= 0.6) {
    if (jenis === "kuncup" && (balikY >= 2 || balikS >= 2 || balikX >= 2)) return ["MAKAN", 0.84];
    if (jenis === "terbuka" && (balikX >= 2 || balikUjung >= 2)) return ["HALO", Math.min(0.93, 0.8 + 0.03 * Math.max(balikX, balikUjung))];
    if (jenis === "tunjuk" && (balikX >= 2 || balikUjung >= 2)) return ["TIDAK", 0.86];
    const besar = Math.max(rx, ry);
    const melingkar = rx > 0.3 * ukuran && ry > 0.3 * ukuran && rx / Math.max(ry, 1e-6) > 0.4 && rx / Math.max(ry, 1e-6) < 2.5
      && jalur > 2.2 * besar && bersih < 0.5 * besar;
    if (jenis === "kepal" && melingkar) return ["MAAF", 0.84];
    if (jenis === "kepal" && balikY >= 2 && rx < ry * 0.6) return ["YA", 0.85];
    const turun = y[y.length - 1] - y[0];
    if (jenis === "terbuka" && turun > 0.5 * ukuran && turun > 0.7 * ry && balikX < 2) return ["TERIMA KASIH", 0.82];
    if (jenis === "tunjuk" && turun > 0.45 * ukuran && turun > 0.7 * ry) return ["SAYA", 0.8];
  }
  if (rx < 0.18 * ukuran && ry < 0.18 * ukuran && rentang(s) < 0.15 * ukuran) {
    const [kata, p] = mayoritas(frames.map((f) => poseDiam(f) || "-"));
    if (kata !== "-" && p >= 0.75) return [kata, 0.8 + 0.12 * p];
  }
  return ["-", 0];
}

class PenstabilKata {
  constructor() { this.frames = []; this.gerak = []; this.jeda = 0; this.ditahan = ""; }
  update(f, g) {
    if (this.jeda > 0) {
      this.jeda--; this.frames = []; this.gerak = [];
      if (!f) this.ditahan = "";
      return null;
    }
    if (!f) { this.frames = []; this.gerak = []; this.ditahan = ""; return null; }
    this.frames.push(f); this.gerak.push(g);
    if (this.frames.length > JENDELA) { this.frames.shift(); this.gerak.shift(); }
    if (this.frames.length < JENDELA) return null;
    const [kata, yakin] = tebakKata(this.frames, this.gerak);
    if (kata !== this.ditahan) this.ditahan = "";
    if (kata !== "-" && yakin >= 0.75 && kata !== this.ditahan) {
      this.ditahan = kata; this.jeda = 25; this.frames = []; this.gerak = [];
      return [kata, yakin];
    }
    return null;
  }
}

// ------------------------------------------------------------ MediaPipe
let pendeteksi = null;
async function muatPendeteksi() {
  if (pendeteksi) return pendeteksi;
  const { FilesetResolver, HandLandmarker } = await import("./vendor/mediapipe/vision_bundle.js");
  const fileset = await FilesetResolver.forVisionTasks(new URL("vendor/mediapipe/wasm", location.href).href.replace(/\/$/, ""));
  const opsi = (delegate) => ({
    baseOptions: { modelAssetPath: new URL("model/hand_landmarker.task", location.href).href, delegate },
    runningMode: "VIDEO", numHands: 1,
    minHandDetectionConfidence: 0.6, minHandPresenceConfidence: 0.5, minTrackingConfidence: 0.5,
  });
  try { pendeteksi = await HandLandmarker.createFromOptions(fileset, opsi("GPU")); }
  catch (e) { pendeteksi = await HandLandmarker.createFromOptions(fileset, opsi("CPU")); }
  return pendeteksi;
}

// Untuk pengujian: tebak huruf dari sebuah gambar (mode IMAGE).
window.__sibiUjiGambar = async (src) => {
  const { FilesetResolver, HandLandmarker } = await import("./vendor/mediapipe/vision_bundle.js");
  const fileset = await FilesetResolver.forVisionTasks(new URL("vendor/mediapipe/wasm", location.href).href);
  const hl = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: new URL("model/hand_landmarker.task", location.href).href, delegate: "CPU" },
    runningMode: "IMAGE", numHands: 1,
  });
  const m = await muatModel();
  const img = new Image();
  img.src = src;
  await img.decode();
  const res = hl.detect(img);
  hl.close();
  if (!res.landmarks.length) return null;
  // Foto sudah berupa tampilan "cermin"? Kirim apa adanya; fitur() mencerminkan seperti video kamera depan.
  const p = prediksi(m, fitur(res.landmarks[0], img.naturalWidth, img.naturalHeight, m.rasio_latih));
  const urut = [...p].map((v, i) => [m.kelas[i], v]).sort((a, b) => b[1] - a[1]).slice(0, 3);
  return { landmarks: res.landmarks[0].map((q) => [q.x, q.y, q.z]), top: urut };
};

// ------------------------------------------------------------ tampilan
export function tampilkan(isi, alat) {
  const st = { sub: "kamera" };
  isi.innerHTML = `
    <div class="segmen" role="group" aria-label="Pilih fitur">
      <button type="button" data-sub="kamera" aria-pressed="true">🤟 Isyarat → teks</button>
      <button type="button" data-sub="suara" aria-pressed="false">🎤 Suara → isyarat</button>
    </div>
    <div id="sub"></div>`;
  let tutupSub = null;
  const buka = (sub) => {
    if (tutupSub) tutupSub();
    alat.bersihkanMulut();
    diam();
    st.sub = sub;
    isi.querySelectorAll(".segmen button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sub === sub)));
    tutupSub = sub === "kamera" ? subKamera($("#sub", isi), alat) : subSuara($("#sub", isi), alat);
  };
  isi.querySelector(".segmen").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-sub]");
    if (b && b.dataset.sub !== st.sub) buka(b.dataset.sub);
  });
  buka("kamera");
  return () => { if (tutupSub) tutupSub(); };
}

const IKON = {
  balik: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 3 7.2 5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3zm3 4.5c1.7 0 3.2.9 4 2.3l1.3-1.3V12h-3.5l1.2-1.2A3 3 0 0 0 9 12H7.5a4.5 4.5 0 0 1 4.5-4.5zm-3.8 6.5h3.5l-1.2 1.2A3 3 0 0 0 15 14h1.5A4.5 4.5 0 0 1 8 16.2L6.7 17.5V14z"/></svg>',
  spasi: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 10h2v4h14v-4h2v6H3z"/></svg>',
  hapus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 5h11a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-7-7zm3.4 3L11 9.4l2.6 2.6-2.6 2.6 1.4 1.4 2.6-2.6 2.6 2.6 1.4-1.4-2.6-2.6 2.6-2.6L18.6 8 16 10.6z"/></svg>',
  bersih: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 7h12l-1 14H7zm3-4h6l1 2h4v2H4V5h4z"/></svg>',
  suara: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 9v6h4l5 5V4L7 9zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg>',
  mic: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 15a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v7a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V22h2v-3.1A7 7 0 0 0 19 12z"/></svg>',
};

function subKamera(el, alat) {
  const daftarKamera = Object.entries(alat.K.kataKamera || {});
  el.innerHTML = `
    <div class="segmen" role="group" aria-label="Mode">
      <button type="button" data-mode="huruf" aria-pressed="true">🔤 Eja huruf</button>
      <button type="button" data-mode="kata" aria-pressed="false">🤟 Isyarat kata</button>
    </div>
    <div class="layar-kamera cermin" id="layar">
      <div class="pesan" id="pesan">Tekan <b>Mulai kamera</b>, lalu eja kata dengan isyarat huruf atau tunjukkan isyarat kata.</div>
    </div>
    <div class="baris" style="margin-top:10px">
      <button type="button" class="btn utama" id="mulai">▶ Mulai kamera</button>
    </div>
    <div class="hasil-teks" id="teks" aria-live="polite"></div>
    <div class="kalimat-rapi" id="rapi" aria-live="polite"></div>
    <div id="saran-kata"></div>
    <div id="saran-kal"></div>
    <div class="alat">
      <button type="button" class="btn" id="spasi">${IKON.spasi}Spasi</button>
      <button type="button" class="btn" id="hapus">${IKON.hapus}Hapus</button>
      <button type="button" class="btn" id="bersih">${IKON.bersih}Bersihkan</button>
      <button type="button" class="btn utama" id="ucap">${IKON.suara}Suarakan</button>
    </div>
    <details class="isyarat daftar-kamera">
      <summary>${daftarKamera.length} isyarat kata yang dikenali kamera</summary>
      ${daftarKamera.map(([k, v]) => `<div class="kk-baris"><span>${v.emoji}</span><div><b>${esc(judulKata(k))}</b>
        <small>${v.jenis === "diam" ? "tahan diam" : "bergerak"}</small><br>${esc(v.cara)}</div></div>`).join("")}
      <p class="kecil">Kata lain (${alat.K.kosakata.length} kosakata anak) bisa dieja huruf demi huruf; saran kata muncul otomatis.</p>
    </details>
    <p class="kecil" id="tip-mode"></p>`;

  const TIP = {
    huruf: "Eja huruf demi huruf (tahan ± setengah detik per huruf). Saran kata muncul di bawah; tekan untuk memakainya. Untuk huruf ganda, turunkan tangan sebentar lalu ulangi.",
    kata: "Lakukan isyarat kata (lihat daftar di atas). Isyarat diam: tahan ±1 detik. Kata masuk ke kalimat yang sama dengan ejaan huruf.",
  };
  const s = {
    mode: "huruf", depan: true, aktif: false, stream: null, raf: 0, terakhir: 0, prob: null, teks: "",
    huruf: new PenstabilHuruf(), kata: new PenstabilKata(), model: null, det: null,
  };
  const layar = $("#layar", el), teksEl = $("#teks", el), btnMulai = $("#mulai", el);
  let video = null, kanvas = null, ctx = null, tebakan = null;

  const tulis = () => {
    teksEl.textContent = s.teks;
    $("#rapi", el).textContent = s.teks.trim() ? `💬 ${rapikan(s.teks)}` : "";
    // saran kata untuk huruf yang sedang dieja (belum diberi spasi)
    const sedang = !s.teks || s.teks.endsWith(" ") ? "" : s.teks.split(" ").pop();
    let saran = sedang ? saranKata(sedang, 6) : [];
    if (saran.length === 1 && kunci(saran[0][0]) === sedang) saran = [];
    $("#saran-kata", el).innerHTML = saran.length
      ? `<p class="kecil judul-saran">Maksudnya kata ini? Tekan untuk memakai:</p><div class="saran">${saran.map(([k, e]) =>
        `<button type="button" class="btn saran-btn" data-kata="${esc(k)}">${e} ${esc(k)}</button>`).join("")}</div>` : "";
    const kal = saranKalimat(s.teks, 3);
    $("#saran-kal", el).innerHTML = kal.length
      ? `<p class="kecil judul-saran">Kalimat yang mirip:</p>${kal.map(([k, e]) =>
        `<button type="button" class="btn lebar saran-kal" data-kal="${esc(k)}">${e} ${esc(k)}</button>`).join("")}` : "";
    $("#tip-mode", el).textContent = TIP[s.mode];
  };
  const tambahKata = (kata) => { s.teks = (s.teks.trimEnd() ? `${s.teks.trimEnd()} ` : "") + `${kata} `; };

  const pesan = (html) => {
    layar.innerHTML = `<div class="pesan">${html}</div>`;
    video = kanvas = ctx = tebakan = null;
  };

  async function mulai() {
    btnMulai.disabled = true;
    btnMulai.textContent = "Memuat…";
    pesan('<span class="putar" style="display:inline-block;vertical-align:middle"></span> Menyiapkan pendeteksi tangan…');
    try {
      [s.model, s.det] = await Promise.all([muatModel(), muatPendeteksi()]);
    } catch (e) {
      pesan("Pendeteksi tangan gagal dimuat di perangkat ini.");
      btnMulai.disabled = false; btnMulai.textContent = "▶ Coba lagi";
      return;
    }
    try {
      s.stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: s.depan ? "user" : "environment", width: { ideal: 640 }, height: { ideal: 480 } },
      });
    } catch (e) {
      const ditolak = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
      pesan(ditolak ? "Izin kamera ditolak. Izinkan kamera untuk aplikasi ini di Pengaturan HP, lalu coba lagi."
        : "Kamera tidak bisa dibuka. Pastikan tidak sedang dipakai aplikasi lain.");
      btnMulai.disabled = false; btnMulai.textContent = "▶ Coba lagi";
      return;
    }
    layar.innerHTML = `<video playsinline muted></video><canvas></canvas>
      <div class="tebakan" aria-live="off"><b>–</b><small>siap</small><div class="tahan"><i></i></div></div>
      <button type="button" class="balik" aria-label="Ganti kamera depan/belakang">${IKON.balik}</button>`;
    video = $("video", layar); kanvas = $("canvas", layar); ctx = kanvas.getContext("2d");
    tebakan = $(".tebakan", layar);
    layar.classList.toggle("cermin", s.depan);
    $(".balik", layar).onclick = () => { berhenti(); s.depan = !s.depan; mulai(); };
    video.srcObject = s.stream;
    await video.play().catch(() => {});
    s.aktif = true;
    btnMulai.disabled = false;
    btnMulai.textContent = "■ Berhenti";
    btnMulai.classList.remove("utama");
    s.raf = requestAnimationFrame(langkah);
  }

  function berhenti() {
    s.aktif = false;
    cancelAnimationFrame(s.raf);
    if (s.stream) s.stream.getTracks().forEach((t) => t.stop());
    s.stream = null;
    s.prob = null;
    btnMulai.textContent = "▶ Mulai kamera";
    btnMulai.classList.add("utama");
    btnMulai.disabled = false;
  }

  function langkah(now) {
    if (!s.aktif) return;
    s.raf = requestAnimationFrame(langkah);
    if (!video || video.readyState < 2 || now - s.terakhir < 1000 / MAKS_FPS) return;
    s.terakhir = now;
    const vw = video.videoWidth, vh = video.videoHeight;
    if (kanvas.width !== vw) { kanvas.width = vw; kanvas.height = vh; }
    let res;
    try { res = s.det.detectForVideo(video, now); } catch (e) { return; }
    ctx.clearRect(0, 0, vw, vh);
    const lm = res.landmarks && res.landmarks[0];
    if (lm) gambar(lm, vw, vh);
    if (s.mode === "huruf") prosesHuruf(lm, vw, vh, now);
    else prosesKata(lm, vw, vh);
  }

  function gambar(lm, w, h) {
    ctx.lineWidth = Math.max(2, w / 160);
    ctx.strokeStyle = "rgba(61,220,132,.9)";
    ctx.beginPath();
    for (const [a, b] of SAMBUNGAN) { ctx.moveTo(lm[a].x * w, lm[a].y * h); ctx.lineTo(lm[b].x * w, lm[b].y * h); }
    ctx.stroke();
    ctx.fillStyle = "#FF5A79";
    const r = Math.max(3, w / 110);
    for (const p of lm) { ctx.beginPath(); ctx.arc(p.x * w, p.y * h, r, 0, Math.PI * 2); ctx.fill(); }
  }

  function prosesHuruf(lm, vw, vh, now) {
    let h = "-", yakin = 0;
    if (lm) {
      const p = prediksi(s.model, fitur(lm, vw, vh, s.model.rasio_latih));
      // haluskan antar-frame agar tebakan tidak berkedip
      s.prob = s.prob ? s.prob.map((v, i) => v * 0.55 + p[i] * 0.45) : p;
      let bi = 0;
      s.prob.forEach((v, i) => { if (v > s.prob[bi]) bi = i; });
      h = s.model.kelas[bi]; yakin = s.prob[bi];
    } else s.prob = null;
    const baru = s.huruf.update(h, yakin, now);
    if (baru) { s.teks += baru; tulis(); getar(30); }
    tebakan.querySelector("b").textContent = h === "-" ? "–" : h;
    tebakan.querySelector("small").textContent = h === "-" ? "tunjukkan tangan" : `yakin ${Math.round(yakin * 100)}%`;
    tebakan.querySelector(".tahan i").style.width = `${Math.round(s.huruf.kemajuan(now) * 100)}%`;
  }

  function prosesKata(lm, vw, vh) {
    let f = null, g = null;
    if (lm) {
      f = fitur(lm, vw, vh, s.model.rasio_latih);
      // pergelangan di gambar (dicerminkan seperti fitur) + panjang telapak sebagai skala
      g = [1 - lm[0].x, lm[0].y, Math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y)];
    }
    const hasil = s.kata.update(f, g);
    const b = tebakan.querySelector("b");
    if (hasil) {
      tambahKata(hasil[0]); tulis(); getar(40);
      const info = alat.K.kataKamera[hasil[0]];
      b.textContent = `${info ? info.emoji + " " : ""}${hasil[0]}`;
    } else if (!lm) b.textContent = "–";
    b.classList.toggle("kata", b.textContent.length > 2);
    tebakan.querySelector("small").textContent = lm ? "isyaratkan kata" : "tunjukkan tangan";
    tebakan.querySelector(".tahan i").style.width = `${Math.round((s.kata.frames.length / 20) * 100)}%`;
  }

  btnMulai.onclick = () => (s.aktif ? berhenti() : mulai());
  el.querySelector(".segmen").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-mode]");
    if (!b) return;
    s.mode = b.dataset.mode;
    el.querySelectorAll("[data-mode]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    s.huruf.reset();
    s.kata = new PenstabilKata();
    tulis();
  });
  $("#saran-kata", el).addEventListener("click", (e) => {
    const b = e.target.closest("[data-kata]");
    if (!b) return;
    const kata = s.teks.split(" ");
    kata.pop();
    s.teks = kata.join(" ");
    tambahKata(b.dataset.kata.toUpperCase());
    s.huruf.reset();
    tulis();
    ucapkan(b.dataset.kata);
  });
  $("#saran-kal", el).addEventListener("click", (e) => {
    const b = e.target.closest("[data-kal]");
    if (!b) return;
    s.teks = `${token(b.dataset.kal).join(" ")} `;
    s.huruf.reset();
    tulis();
    ucapkan(b.dataset.kal);
  });
  $("#spasi", el).onclick = () => { if (s.teks && !s.teks.endsWith(" ")) s.teks += " "; s.huruf.terakhir = " "; tulis(); };
  $("#hapus", el).onclick = () => {
    if (s.mode === "huruf") s.teks = s.teks.slice(0, -1);
    else { const k = s.teks.trim().split(/\s+/).slice(0, -1).join(" "); s.teks = k ? `${k} ` : ""; }
    s.huruf.terakhir = "";
    tulis();
  };
  $("#bersih", el).onclick = () => { s.teks = ""; s.huruf.reset(); tulis(); };
  $("#ucap", el).onclick = () => {
    const t = rapikan(s.teks);
    if (!t) { alat.toast("Belum ada teks untuk disuarakan."); return; }
    ucapkan(t);
  };
  tulis();

  // Hemat baterai: matikan kamera saat aplikasi ke latar belakang.
  const sembunyi = () => { if (document.hidden && s.aktif) berhenti(); };
  const jeda = () => { if (s.aktif) berhenti(); };
  document.addEventListener("visibilitychange", sembunyi);
  window.addEventListener("sibi-jeda", jeda); // dikirim MainActivity saat aplikasi dijeda
  return () => { berhenti(); document.removeEventListener("visibilitychange", sembunyi); window.removeEventListener("sibi-jeda", jeda); };
}

function subSuara(el, alat) {
  el.innerHTML = `
    <label for="kalimat" class="kecil" style="font-weight:800">Ketik atau ucapkan kalimat</label>
    <textarea id="kalimat" class="isian-teks" maxlength="200" placeholder="Contoh: Halo, nama saya Budi"></textarea>
    <div class="baris" style="margin:8px 0 4px">
      <button type="button" class="btn mic" id="mic">${IKON.mic}Bicara</button>
      <button type="button" class="btn utama" id="tampil">🤟 Tampilkan isyarat</button>
    </div>
    <p class="kecil" id="status-mic"></p>
    <div id="hasil"></div>`;
  const kalimat = $("#kalimat", el), mic = $("#mic", el), status = $("#status-mic", el);
  let stop = null;
  if (!bisaDengar()) { mic.disabled = true; status.textContent = "Pengenalan suara tidak tersedia di perangkat ini; silakan ketik kalimatnya."; }

  const tampil = () => {
    alat.bersihkanMulut();
    const teks = kalimat.value.trim();
    const kata = teks.toUpperCase().replace(/[^A-Z ]/g, " ").split(/\s+/).filter(Boolean);
    const out = $("#hasil", el);
    if (!kata.length) { out.innerHTML = '<div class="kosong">Belum ada kalimat.</div>'; return; }
    out.innerHTML = `<div class="mulut-host" id="m-kalimat"></div>${kata.map((k) => `<h3>${esc(k)}</h3>${alat.strip(k, 60)}`).join("")}`;
    const t = teks.replace(/\s+/g, " ");
    alat.mulut($("#m-kalimat", el), { tracks: [alat.track(t, t.toLowerCase(), false, t)], extras: [], size: 240, auto: false, tombol: "Ucapkan" });
  };
  $("#tampil", el).onclick = tampil;
  mic.onclick = () => {
    if (stop) { stop(); return; }
    mic.classList.add("aktif");
    mic.lastChild.textContent = "Berhenti";
    status.textContent = "Mendengarkan… silakan bicara.";
    stop = dengar({
      sebagian: (t) => { kalimat.value = t; },
      hasil: (t) => { kalimat.value = t; status.textContent = ""; tampil(); },
      galat: (m) => { status.textContent = m || "Suara tidak terdengar jelas. Coba lagi."; },
      selesai: () => { stop = null; mic.classList.remove("aktif"); mic.lastChild.textContent = "Bicara"; if (status.textContent.startsWith("Mendengarkan")) status.textContent = ""; },
    });
  };
  return () => { if (stop) stop(); };
}
