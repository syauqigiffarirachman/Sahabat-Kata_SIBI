// Gerak mulut + suara huruf (komponen Streamlit v2, tanpa iframe).
//
// Teks yang diucapkan diubah menjadi deretan fonem Bahasa Indonesia (ejaan
// Indonesia hampir fonemis), tiap fonem dipetakan ke bentuk mulut (visem):
// buka rahang, lebar bibir, bibir membulat, gigi, posisi lidah, bibir bawah
// di gigi atas (f/v), bibir rapat (b/p/m), aliran udara, dan getar hidung.
// Parameter bergerak halus (filter eksponensial + antisipasi), sehingga
// peralihan antarbunyi tampak alami seperti koartikulasi pada mulut asli.
// Suara memakai speechSynthesis browser (id-ID); animasi dimulai saat suara
// benar-benar mulai, menahan bunyi terakhir sampai suara selesai, dan
// kecepatannya dikalibrasi otomatis dari durasi suara sebelumnya.

const BASE = { open: 0.04, wide: 0, round: 0, tu: 0, tl: 0, tongue: 0, tuck: 0, press: 0, air: 0, nasal: 0 };
const KEYS = Object.keys(BASE);

// Bentuk mulut (visem). Nilai yang tidak disebut = BASE.
const VIS = {
  rest: {},
  a: { open: 1, wide: 0.15, tu: 0.55, tl: 0.2, tongue: 0.05 },
  e: { open: 0.55, wide: 0.6, tu: 0.85, tl: 0.5, tongue: 0.2 },   // é (nama huruf)
  E: { open: 0.42, wide: 0.28, tu: 0.6, tl: 0.35, tongue: 0.15 }, // e di dalam kata (é / ə)
  i: { open: 0.2, wide: 1, tu: 1, tl: 0.85, tongue: 0.3 },
  o: { open: 0.62, wide: -0.55, round: 0.75, tu: 0.25, tongue: 0.05 },
  u: { open: 0.24, wide: -1, round: 1, tongue: 0.05 },
  P: { open: 0, wide: 0.05, press: 1 },                                   // b p m
  F: { open: 0.1, wide: 0.2, tu: 1, tuck: 1, air: 0.8 },                  // f v: gigi atas di bibir bawah
  T: { open: 0.34, wide: 0.35, tu: 0.45, tl: 0.15, tongue: 1 },           // t d n: ujung lidah di gigi atas
  L: { open: 0.5, wide: 0.35, tu: 0.4, tl: 0.1, tongue: 1 },              // l
  S: { open: 0.2, wide: 0.6, tu: 1, tl: 1, air: 0.9 },                    // s z: gigi rapat, bibir terbuka
  C: { open: 0.22, wide: 0.1, round: 0.42, tu: 1, tl: 1, air: 0.45 },     // c j sy
  K: { open: 0.34, wide: 0.25, tu: 0.5, tl: 0.4, tongue: 0.55 },          // k g q ng
  H: { open: 0.55, wide: 0.2, tu: 0.4, tl: 0.2, air: 0.75 },              // h kh
  R: { open: 0.4, wide: 0.3, tu: 0.45, tl: 0.15, tongue: 0.85 },          // r (bergetar)
  W: { open: 0.14, wide: -0.9, round: 0.95 },
  Y: { open: 0.2, wide: 0.85, tu: 0.9, tl: 0.8, tongue: 0.4 },
};

// Fonem -> [visem, durasi dasar (ms), tambahan]
const PH = {
  a: ["a", 175], i: ["i", 165], u: ["u", 170], o: ["o", 175], e: ["E", 160],
  b: ["P", 95], p: ["P", 105, { air: 0.25 }], m: ["P", 110, { nasal: 1 }],
  f: ["F", 125], v: ["F", 115],
  t: ["T", 85], d: ["T", 85], n: ["T", 100, { nasal: 1 }], l: ["L", 95],
  s: ["S", 135], z: ["S", 120], c: ["C", 110], j: ["C", 105], sy: ["C", 135],
  k: ["K", 90], g: ["K", 90], q: ["K", 90], kh: ["H", 110], ng: ["K", 105, { nasal: 1 }],
  ny: ["Y", 105, { nasal: 1 }], h: ["H", 85], r: ["R", 125, { trill: 1 }],
  w: ["W", 80], y: ["Y", 75],
};
const VOKAL = "aiueo";

// Teks -> fonem dengan rentang huruf (untuk menyorot huruf yang sedang diucapkan).
function g2p(text, nama) {
  const s = (text || "").toLowerCase();
  const out = [];
  let i = 0;
  while (i < s.length) {
    const two = s.slice(i, i + 2);
    const ch = s[i];
    const awalKata = i === 0 || !/[a-z]/.test(s[i - 1]);
    if (["ng", "ny", "sy", "kh"].includes(two)) {
      out.push(tok(two, i, i + 2));
      i += 2;
    } else if (ch === "x") {
      if (awalKata) out.push(tok("s", i, i + 1));
      else { out.push(tok("k", i, i + 1)); out.push(tok("s", i, i + 1)); }
      i += 1;
    } else if (PH[ch]) {
      const t = tok(ch, i, i + 1);
      if (ch === "e" && nama) t.v = "e";
      out.push(t);
      i += 1;
    } else {
      if (/[\s\-,.]/.test(ch) && out.length && out[out.length - 1].v !== "rest") {
        out.push({ key: "_", v: "rest", dur: ch === "-" ? 90 : 140, extra: {}, s: i, e: i + 1 });
      }
      i += 1;
    }
  }
  while (out.length && out[out.length - 1].v === "rest") out.pop();
  // Vokal terakhir (dan bunyi kata satu suku) sedikit lebih panjang, seperti ucapan asli.
  if (out.length) out[out.length - 1].dur *= VOKAL.includes(out[out.length - 1].key) ? 1.45 : 1.2;
  return out;
}

function tok(k, s, e) {
  const [v, dur, extra] = PH[k];
  return { key: k, v, dur, extra: extra || {}, s, e };
}

function timeline(tokens) {
  const segs = [];
  let t = 45; // ancang-ancang: mulut mulai bergerak sedikit sebelum bunyi
  for (const tk of tokens) { segs.push({ t0: t, t1: t + tk.dur, tk }); t += tk.dur; }
  return { segs, end: t };
}

function targetAt(tl, line, now) {
  const p = { ...BASE };
  const seg = line.segs.find((g) => tl >= g.t0 && tl < g.t1);
  if (!seg) return { p, seg: null };
  Object.assign(p, VIS[seg.tk.v], seg.tk.extra);
  if (seg.tk.extra.trill) p.tongue = 0.72 + 0.22 * Math.sin(now / 11); // ujung lidah bergetar
  return { p, seg };
}

// ------------------------------------------------------------ suara (TTS)
const KAL = { nf: 1.3, ns: 2.2, kf: 1.15, ks: 2.0 }; // ms nyata per ms dasar, dikalibrasi
try { Object.assign(KAL, JSON.parse(localStorage.getItem("sibi-mulut-kal") || "{}")); } catch (e) { /* abaikan */ }
function simpanKal() { try { localStorage.setItem("sibi-mulut-kal", JSON.stringify(KAL)); } catch (e) { /* abaikan */ } }

let suaraId = null;
function pilihSuara() {
  const ss = window.speechSynthesis;
  if (!ss) return null;
  const vs = ss.getVoices() || [];
  const id = vs.filter((v) => (v.lang || "").toLowerCase().replace("_", "-").startsWith("id"));
  suaraId = id.find((v) => /google/i.test(v.name)) || id.find((v) => /natural|online/i.test(v.name)) || id[0] || null;
  return suaraId;
}
if (window.speechSynthesis) {
  pilihSuara();
  try { window.speechSynthesis.addEventListener("voiceschanged", pilihSuara); } catch (e) { /* abaikan */ }
}
window.__sibiUtter = window.__sibiUtter || []; // cegah utterance dibuang GC (bug Chrome: onend hilang)

// ------------------------------------------------------------ suara manusia (file MP3)
// File suara dibuat dari suara neural Bahasa Indonesia (lihat sibi/suara.py). Amplop
// kenyaringan (per 10 ms) dihitung dari file itu sendiri, lalu dipakai untuk membuka
// rahang sesuai kerasnya suara pada saat itu, sehingga gerak mulut ikut "napas" suara asli.
const AUDIO = new Map();   // url -> HTMLAudioElement
const AMPLOP = new Map();  // url -> Promise<Float32Array|null>

function ambilAudio(url) {
  let a = AUDIO.get(url);
  if (!a) {
    a = new Audio(url);
    a.preload = "auto";
    AUDIO.set(url, a);
  }
  return a;
}

function amplop(url) {
  if (AMPLOP.has(url)) return AMPLOP.get(url);
  const pr = (async () => {
    try {
      const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
      if (!OAC) return null;
      const buf = await (await fetch(url)).arrayBuffer();
      const audio = await new OAC(1, 1, 24000).decodeAudioData(buf);
      const d = audio.getChannelData(0);
      const n = Math.max(1, Math.round(audio.sampleRate / 100));
      const env = new Float32Array(Math.ceil(d.length / n));
      let maks = 1e-6;
      for (let i = 0; i < env.length; i++) {
        let s = 0;
        const a = i * n, b = Math.min(d.length, a + n);
        for (let j = a; j < b; j++) s += d[j] * d[j];
        env[i] = Math.sqrt(s / Math.max(1, b - a));
        maks = Math.max(maks, env[i]);
      }
      for (let i = 0; i < env.length; i++) env[i] = Math.min(1, env[i] / (maks * 0.8));
      return env;
    } catch (e) {
      return null;
    }
  })();
  AMPLOP.set(url, pr);
  return pr;
}

// Awal & akhir bunyi sebenarnya (ms) dari amplop: lebih tepat daripada catatan TTS.
function batasBunyi(env) {
  let a = -1, b = -1;
  for (let i = 0; i < env.length; i++) if (env[i] > 0.12) { if (a < 0) a = i; b = i; }
  if (a < 0 || b - a < 5) return null;
  return { mulai: a * 10, lama: (b - a + 1) * 10 };
}

function siapkan(track) {
  for (const info of [track.audio, track.audioPelan]) {
    if (info && info.url) { ambilAudio(info.url); amplop(info.url); }
  }
}

// ------------------------------------------------------------ gambar
const SKIN = "#F4C7A1", SKIN_D = "#C98B61", SKIN_L = "#FBE0C8";
const f = (n) => n.toFixed(2);
const lerp = (a, b, t) => a + (b - a) * t;

function svgMarkup(u) {
  return `
<svg viewBox="0 0 240 236" role="img" aria-label="Animasi gerak mulut" xmlns="http://www.w3.org/2000/svg">
 <defs>
  <linearGradient id="sk${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${SKIN_L}"/><stop offset=".55" stop-color="${SKIN}"/><stop offset="1" stop-color="#EDB98F"/></linearGradient>
  <radialGradient id="ns${u}" cx=".45" cy=".35" r=".7"><stop offset="0" stop-color="#FDE7D3"/><stop offset="1" stop-color="${SKIN}"/></radialGradient>
  <radialGradient id="cv${u}" cx=".5" cy=".55" r=".6"><stop offset="0" stop-color="#3B0D16"/><stop offset="1" stop-color="#6B2430"/></radialGradient>
  <linearGradient id="ul${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B9585D"/><stop offset="1" stop-color="#CF6E6E"/></linearGradient>
  <linearGradient id="ll${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D98380"/><stop offset="1" stop-color="#BF5E60"/></linearGradient>
  <linearGradient id="tg${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9868B"/><stop offset="1" stop-color="#B9505C"/></linearGradient>
  <linearGradient id="th${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#ECE5D8"/></linearGradient>
  <clipPath id="cl${u}"><path class="clip"/></clipPath>
 </defs>
 <path class="face" fill="url(#sk${u})" stroke="${SKIN_D}" stroke-width="1.2"/>
 <ellipse class="blushL" rx="22" ry="12" fill="#F08A8A" opacity=".2"/>
 <ellipse class="blushR" rx="22" ry="12" fill="#F08A8A" opacity=".2"/>
 <path d="M111 0 C111 28 108 46 105 60" fill="none" stroke="${SKIN_D}" stroke-width="1.3" opacity=".28"/>
 <path d="M129 0 C129 28 132 46 135 60" fill="none" stroke="${SKIN_D}" stroke-width="1.3" opacity=".22"/>
 <ellipse cx="120" cy="86" rx="24" ry="4.5" fill="${SKIN_D}" opacity=".22"/>
 <ellipse cx="103" cy="76" rx="9" ry="7" fill="${SKIN}" stroke="${SKIN_D}" stroke-width=".9"/>
 <ellipse cx="137" cy="76" rx="9" ry="7" fill="${SKIN}" stroke="${SKIN_D}" stroke-width=".9"/>
 <ellipse cx="120" cy="70" rx="14" ry="12" fill="url(#ns${u})" stroke="${SKIN_D}" stroke-width=".7" stroke-opacity=".5"/>
 <ellipse cx="111.5" cy="80.5" rx="4.4" ry="2.3" fill="#7A4632" transform="rotate(12 111.5 80.5)"/>
 <ellipse cx="128.5" cy="80.5" rx="4.4" ry="2.3" fill="#7A4632" transform="rotate(-12 128.5 80.5)"/>
 <g class="nasal" fill="none" stroke="#7B5CFF" stroke-width="2.2" stroke-linecap="round" opacity="0">
  <path d="M86 64 q-6 7 0 14"/><path d="M78 59 q-10 12 0 24"/>
  <path d="M154 64 q6 7 0 14"/><path d="M162 59 q10 12 0 24"/>
 </g>
 <path class="fold" fill="none" stroke="${SKIN_D}" stroke-width="1.4" stroke-linecap="round"/>
 <path class="philt" fill="none" stroke="${SKIN_D}" stroke-width="1" opacity=".25"/>
 <path class="chin" fill="none" stroke="${SKIN_D}" stroke-width="1.3" stroke-linecap="round" opacity=".22"/>
 <path class="cavity" fill="url(#cv${u})"/>
 <g clip-path="url(#cl${u})">
  <path class="tongue" fill="url(#tg${u})"/>
  <path class="tgline" fill="none" stroke="#A8434F" stroke-width=".9" opacity=".55"/>
  <g class="upT"><rect x="91" width="58" rx="3.5" fill="url(#th${u})" stroke="#D9D0C2" stroke-width=".5"/>
   <path class="upSep" fill="none" stroke="#D2C8B8" stroke-width=".7"/></g>
  <g class="loT"><rect x="94" width="52" rx="3" fill="url(#th${u})" stroke="#D9D0C2" stroke-width=".5"/>
   <path class="loSep" fill="none" stroke="#D2C8B8" stroke-width=".7"/></g>
 </g>
 <path class="lipU" fill="url(#ul${u})" stroke="#A44A50" stroke-width=".7" stroke-linejoin="round"/>
 <path class="lipL" fill="url(#ll${u})" stroke="#A44A50" stroke-width=".7" stroke-linejoin="round"/>
 <ellipse class="shine" fill="#fff" opacity=".28"/>
 <path class="line" fill="none" stroke="#7A2C33" stroke-width="1.1" stroke-linecap="round"/>
 <g class="air" fill="none" stroke="#4C6FFF" stroke-width="2" stroke-linecap="round" opacity="0">
  <path class="a1"/><path class="a2"/><path class="a3"/>
 </g>
</svg>`;
}

function draw(el, p, now) {
  const cx = 120, cy = 132;
  const wp = Math.max(0, p.wide);
  const W = 80 * (1 + 0.2 * p.wide - 0.36 * p.round);
  const H = 44 * p.open;
  const IW = W * (0.88 - 0.34 * p.round);
  const Cy = cy - 3.2 * wp + 1.5 * p.round;
  let yTop = cy - H * 0.4 - 9 * p.tuck;
  let yBot = lerp(cy + H * 0.6, cy - 0.5, p.tuck); // f/v: bibir bawah naik ke gigi atas
  if (yBot < yTop) yBot = yTop;
  const tU = (9 + 4 * p.round - 1.8 * p.press) * (1 - 0.15 * wp);
  const tL = (11.5 + 4.5 * p.round - 2.5 * p.press - 3 * p.tuck) * (1 - 0.15 * wp);
  const Lx = cx - W / 2, Rx = cx + W / 2, lx = cx - IW / 2, rx = cx + IW / 2;
  const ty = Cy - (Cy - yTop) / 0.75, by = Cy + (yBot - Cy) / 0.75;
  const a = 0.28 + 0.22 * p.round;
  const oc = 0.36 + 0.13 * p.round; // kendali sudut luar: makin bulat, makin tumpul

  const innerTopLR = `M${f(lx)} ${f(Cy)} C${f(cx - IW * a)} ${f(ty)} ${f(cx + IW * a)} ${f(ty)} ${f(rx)} ${f(Cy)}`;
  const innerBotRL = `C${f(cx + IW * a)} ${f(by)} ${f(cx - IW * a)} ${f(by)} ${f(lx)} ${f(Cy)}`;
  const inner = `${innerTopLR} ${innerBotRL}Z`;
  el.cavity.setAttribute("d", inner);
  el.clip.setAttribute("d", inner);
  el.line.setAttribute("d", innerTopLR);
  el.line.setAttribute("opacity", f(Math.max(0.25, 1 - p.open * 3)));

  const sh = Cy - (Cy - yTop) * 0.55 - tU * 0.45;
  el.lipU.setAttribute("d",
    `M${f(Lx)} ${f(Cy)} C${f(cx - W * oc)} ${f(sh)} ${f(cx - W * 0.22)} ${f(yTop - tU)} ${f(cx - W * 0.115)} ${f(yTop - tU * 1.06)}` +
    ` C${f(cx - W * 0.06)} ${f(yTop - tU * 1.08)} ${f(cx - W * 0.035)} ${f(yTop - tU * 0.8)} ${f(cx)} ${f(yTop - tU * 0.8)}` +
    ` C${f(cx + W * 0.035)} ${f(yTop - tU * 0.8)} ${f(cx + W * 0.06)} ${f(yTop - tU * 1.08)} ${f(cx + W * 0.115)} ${f(yTop - tU * 1.06)}` +
    ` C${f(cx + W * 0.22)} ${f(yTop - tU)} ${f(cx + W * oc)} ${f(sh)} ${f(Rx)} ${f(Cy)}` +
    ` L${f(rx)} ${f(Cy)} C${f(cx + IW * a)} ${f(ty)} ${f(cx - IW * a)} ${f(ty)} ${f(lx)} ${f(Cy)}Z`);
  const lo = yBot + tL * 1.12, ls = Cy + (yBot - Cy) * 0.6 + tL * 0.7;
  el.lipL.setAttribute("d",
    `M${f(Lx)} ${f(Cy)} C${f(cx - W * (oc - 0.02))} ${f(ls)} ${f(cx - W * 0.2)} ${f(lo)} ${f(cx)} ${f(lo)}` +
    ` C${f(cx + W * 0.2)} ${f(lo)} ${f(cx + W * (oc - 0.02))} ${f(ls)} ${f(Rx)} ${f(Cy)}` +
    ` L${f(rx)} ${f(Cy)} ${innerBotRL}Z`);
  el.shine.setAttribute("cx", f(cx));
  el.shine.setAttribute("cy", f(yBot + tL * 0.5));
  el.shine.setAttribute("rx", f(W * 0.15));
  el.shine.setAttribute("ry", f(tL * 0.2));

  // gigi atas & bawah
  const upH = 2 + p.tu * 11 + p.tuck * 8;
  const upY = yTop - 3;
  el.upR.setAttribute("y", f(upY));
  el.upR.setAttribute("height", f(upH + 3));
  el.upSep.setAttribute("d", [0, -8, 8, -15.5, 15.5, -22, 22].map((d) => `M${f(cx + d)} ${f(upY)} V${f(upY + upH + 2)}`).join(" "));
  const loH = 2 + p.tl * 7;
  const loY = yBot - loH;
  el.loR.setAttribute("y", f(loY));
  el.loR.setAttribute("height", f(loH + 4));
  el.loSep.setAttribute("d", [0, -7, 7, -14, 14, -20, 20].map((d) => `M${f(cx + d)} ${f(loY - 1)} V${f(loY + loH + 4)}`).join(" "));

  // lidah: ujungnya naik ke belakang gigi atas untuk t/d/n/l/r
  const tw = Math.min(58, IW * 0.8 + 10);
  const yb = yBot + 10;
  const tt = lerp(yBot - 2 - H * 0.12, yTop + p.tu * 11 - 1, Math.min(1, p.tongue));
  const k = 0.42 - 0.22 * p.tongue;
  const side = tt + (yb - tt) * 0.25;
  el.tongue.setAttribute("d",
    `M${f(cx - tw / 2)} ${f(yb)} C${f(cx - tw / 2)} ${f(side)} ${f(cx - tw * k)} ${f(tt)} ${f(cx)} ${f(tt)}` +
    ` C${f(cx + tw * k)} ${f(tt)} ${f(cx + tw / 2)} ${f(side)} ${f(cx + tw / 2)} ${f(yb)}Z`);
  el.tgline.setAttribute("d", `M${f(cx)} ${f(tt + 3)} V${f(yb)}`);

  // wajah: rahang turun saat mulut terbuka
  const j = p.open;
  const chinY = 214 + 13 * j;
  el.face.setAttribute("d",
    `M14 -2 L226 -2 C230 70 222 142 196 ${f(180 + 6 * j)} C174 ${f(208 + 10 * j)} 148 ${f(chinY)} 120 ${f(chinY)}` +
    ` C92 ${f(chinY)} 66 ${f(208 + 10 * j)} 44 ${f(180 + 6 * j)} C18 142 10 70 14 -2Z`);
  el.blushL.setAttribute("cx", "58"); el.blushL.setAttribute("cy", f(116 - 7 * wp));
  el.blushR.setAttribute("cx", "182"); el.blushR.setAttribute("cy", f(116 - 7 * wp));
  el.fold.setAttribute("d",
    `M97 82 C88 96 ${f(Lx - 9)} ${f(Cy - 10)} ${f(Lx - 5)} ${f(Cy + 12)} M143 82 C152 96 ${f(Rx + 9)} ${f(Cy - 10)} ${f(Rx + 5)} ${f(Cy + 12)}`);
  el.fold.setAttribute("opacity", f(0.12 + 0.3 * wp));
  const pk = yTop - tU * 1.06;
  el.philt.setAttribute("d", `M115 88 L${f(cx - W * 0.1)} ${f(pk - 1)} M125 88 L${f(cx + W * 0.1)} ${f(pk - 1)}`);
  const cz = lo + 15 + 4 * j;
  el.chin.setAttribute("d", `M${f(cx - 15)} ${f(cz)} Q${f(cx)} ${f(cz + 5)} ${f(cx + 15)} ${f(cz)}`);

  // bantuan visual: getar hidung (m/n/ng/ny) dan aliran udara (s/f/h/c)
  el.nasal.setAttribute("opacity", f(p.nasal * (0.6 + 0.4 * Math.sin(now / 45))));
  el.air.setAttribute("opacity", f(Math.min(1, p.air) * 0.75));
  if (p.air > 0.02) {
    const ph = (now / 420) % 1;
    [el.a1, el.a2, el.a3].forEach((path, i) => {
      const x = Rx + 6 + ((ph + i / 3) % 1) * 26;
      const y = Cy - 8 + i * 8;
      path.setAttribute("d", `M${f(x)} ${f(y)} q4 -3 8 0 t8 0`);
      path.setAttribute("opacity", f(1 - ((ph + i / 3) % 1)));
    });
  }
}

// ------------------------------------------------------------ komponen
const PLAY_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>';
const STOP_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/></svg>';
const SLOW_ICON = '<span class="ic" aria-hidden="true">🐢</span>';

const INST = new WeakMap();
let nomor = 0;

function setup(root) {
  const u = `m${++nomor}`;
  const box = root.querySelector(".mw");
  box.innerHTML = `
    <div class="stage">${svgMarkup(u)}</div>
    <div class="seq"></div>
    <div class="cap" aria-live="polite"></div>
    <div class="ctl">
      <button type="button" class="play"></button>
      <button type="button" class="slow" aria-pressed="false" title="Ucapkan pelan-pelan">${SLOW_ICON}<span>Pelan</span></button>
    </div>
    <div class="extra"></div>
    <div class="note"></div>`;
  const q = (s) => box.querySelector(s);
  const el = {};
  for (const c of ["clip", "cavity", "tongue", "tgline", "upSep", "loSep", "lipU", "lipL", "shine", "line", "face",
    "blushL", "blushR", "fold", "philt", "chin", "nasal", "air", "a1", "a2", "a3"]) el[c] = q(`.${c}`);
  el.upR = q(".upT rect");
  el.loR = q(".loT rect");
  const st = {
    el, box, u, p: { ...BASE }, anim: null, raf: 0, last: 0, run: 0, slow: false, busy: false,
    data: null, sig: null,
    playBtn: q(".play"), slowBtn: q(".slow"), seq: q(".seq"), cap: q(".cap"), extra: q(".extra"), note: q(".note"),
  };
  st.slowBtn.onclick = () => {
    st.slow = !st.slow;
    st.slowBtn.setAttribute("aria-pressed", String(st.slow));
  };
  draw(el, st.p, 0);
  return st;
}

function loop(st) {
  if (st.raf) return;
  st.last = performance.now();
  const step = (now) => {
    const dt = Math.min(50, now - st.last);
    st.last = now;
    const A = st.anim;
    let target = BASE, seg = null;
    const tau = st.slow ? 55 : 38;
    if (A && A.began != null && A.audio) {
      // suara manusia: posisi animasi = posisi suara (currentTime), tepat per milidetik
      const a = A.audio, info = A.batas || A.info;
      const ms = a.currentTime * 1000;
      const tl = 45 + ((ms - info.mulai) / info.lama) * (A.line.end - 45);
      A.tl = tl;
      const r = targetAt(tl + tau * 0.9 * (A.line.end - 45) / info.lama, A.line, now);
      target = r.p;
      if (A.env && target.open > 0.1) {
        const e = A.env[Math.min(A.env.length - 1, Math.floor(ms / 10))] || 0;
        target = { ...target, open: Math.min(1.1, target.open * (0.55 + 0.7 * e)) };
      }
      seg = targetAt(tl, A.line, now).seg;
      if (A.ended || (a.paused && now - A.began > 400) || tl >= A.line.end + 400) {
        st.anim = null;
        A.done();
      }
    } else if (A && A.began != null) {
      // waktu animasi (ms dasar) mengikuti suara: tahan bunyi terakhir sampai suara selesai,
      // dan percepat sisa bunyi bila suara sudah selesai lebih dulu.
      let tl = A.anchorTl + (now - A.anchorReal) * A.speed;
      if (A.speaking && tl >= A.line.end - 1 && now - A.began < A.line.end * A.k * 2.5 + 900) {
        tl = A.line.end - 1;
        A.anchorTl = tl;
        A.anchorReal = now;
      }
      A.tl = tl;
      const r = targetAt(tl + tau * 0.9, A.line, now); // antisipasi: mulut bersiap sebelum bunyi
      target = r.p;
      seg = targetAt(tl, A.line, now).seg;
      const lewatBatas = now - A.began > A.line.end * A.k * 2.5 + 900;
      if (tl >= A.line.end + 160 && (!A.speaking || lewatBatas)) { st.anim = null; A.done(); }
    }
    const kf = 1 - Math.exp(-dt / tau);
    let diff = 0;
    for (const key of KEYS) {
      const d = target[key] - st.p[key];
      st.p[key] += d * kf;
      diff = Math.max(diff, Math.abs(d));
    }
    draw(st.el, st.p, now);
    highlight(st, seg);
    if (st.anim || diff > 0.002) st.raf = requestAnimationFrame(step);
    else st.raf = 0;
  };
  st.raf = requestAnimationFrame(step);
}

function caption(st, track) {
  const say = track.say;
  st.cap.innerHTML = "";
  st.capSpans = [...say].map((ch) => {
    const s = document.createElement("span");
    s.textContent = ch;
    st.cap.appendChild(s);
    return s;
  });
}

function highlight(st, seg) {
  if (!st.capSpans) return;
  const on = seg && seg.tk.v !== "rest" ? seg.tk : null;
  const tl = st.anim ? st.anim.tl : Infinity;
  const tokens = st.anim ? st.anim.line.segs : [];
  st.capSpans.forEach((s, i) => {
    const aktif = on && i >= on.s && i < on.e;
    const lewat = tokens.some((g) => g.t1 <= tl && i >= g.tk.s && i < g.tk.e);
    s.className = aktif ? "on" : lewat ? "done" : "";
  });
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

// Ucapkan satu teks + animasikan mulut. Selesai saat mulut kembali diam.
function say(st, track, run) {
  return new Promise((resolve) => {
    const tokens = g2p(track.say, track.nama);
    if (!tokens.length) return resolve();
    const line = timeline(tokens);
    const kk = (track.nama ? "n" : "k") + (st.slow ? "s" : "f");
    const k = KAL[kk];
    const A = { line, k, speed: 1 / k, anchorTl: 0, anchorReal: 0, began: null, speaking: true, tl: 0, done: resolve };
    caption(st, track);
    const info = st.slow ? track.audioPelan : track.audio;
    if (info && info.url) return sayAudio(st, track, A, info, run);
    sayBrowser(st, track, A, run);
  });
}

// Putar file suara manusia; bila gagal, pakai suara browser.
function sayAudio(st, track, A, info, run) {
  const a = ambilAudio(info.url);
  let gagal = false;
  const cadangan = () => {
    if (gagal || A.began != null) return;
    gagal = true;
    A.audio = null;
    sayBrowser(st, track, A, run);
  };
  if (run !== st.run) return A.done();
  A.audio = a;
  A.info = info;
  A.ended = false;
  amplop(info.url).then((env) => { A.env = env; A.batas = env && batasBunyi(env); });
  a.onended = () => { A.ended = true; };
  a.onerror = cadangan;
  a.onplaying = () => {
    if (A.began != null) return;
    A.began = performance.now();
    st.anim = A;
    st.note.textContent = "";
    loop(st);
    setTimeout(() => { if (st.anim === A) { st.anim = null; A.done(); } }, (a.duration || 4) * 1000 + 2000);
  };
  st.audioAktif = a;
  try { a.pause(); a.currentTime = 0; } catch (e) { /* abaikan */ }
  a.play().catch(cadangan);
}

// Suara bawaan browser (cadangan bila file suara tidak ada / tanpa internet).
function sayBrowser(st, track, A, run) {
  const line = A.line, k = A.k;
  const kk = (track.nama ? "n" : "k") + (st.slow ? "s" : "f");
  {
    const resolve = A.done;
    const begin = () => {
      if (A.began != null) return;
      A.began = A.anchorReal = performance.now();
      st.anim = A;
      loop(st);
      // pengaman: bila tab di latar (requestAnimationFrame berhenti), jangan macet
      setTimeout(() => {
        if (st.anim === A) { st.anim = null; A.done(); }
      }, line.end * k * 3 + 2500);
    };
    const ss = window.speechSynthesis;
    if (!ss || !window.SpeechSynthesisUtterance) {
      A.speaking = false;
      st.note.textContent = "Perangkat ini tidak punya suara bawaan. Gerak mulut tetap bisa dilihat.";
      return begin();
    }
    const ut = new SpeechSynthesisUtterance(track.say);
    ut.lang = "id-ID";
    const v = suaraId || pilihSuara();
    if (v) ut.voice = v;
    ut.rate = st.slow ? 0.55 : 0.9;
    ut.pitch = 1.05;
    st.note.textContent = v || (ss.getVoices() || []).length === 0 ? ""
      : "Suara Bahasa Indonesia belum terpasang di perangkat ini, jadi pengucapan bisa kurang tepat.";
    const fallback = setTimeout(() => { A.speaking = false; begin(); }, 1100);
    ut.onstart = () => { clearTimeout(fallback); begin(); };
    const selesai = () => {
      clearTimeout(fallback);
      if (A.began == null) { A.speaking = false; return begin(); }
      if (!A.speaking) return;
      const now = performance.now();
      A.speaking = false;
      // kalibrasi: berapa ms nyata per ms dasar pada suara perangkat ini
      const ukur = (now - A.began) / line.end;
      if (ukur > 0.5 && ukur < 4) { KAL[kk] = Math.min(3.5, Math.max(0.7, KAL[kk] * 0.5 + ukur * 0.5)); simpanKal(); }
      const tl = A.anchorTl + (now - A.anchorReal) * A.speed;
      const sisa = line.end - tl;
      if (sisa > 120) { A.anchorTl = tl; A.anchorReal = now; A.speed = sisa / 160; }
    };
    ut.onend = selesai;
    ut.onerror = selesai;
    window.__sibiUtter.push(ut);
    if (window.__sibiUtter.length > 8) window.__sibiUtter.shift();
    if (run !== st.run) return resolve();
    try { ss.resume(); } catch (e) { /* abaikan */ }
    ss.speak(ut);
  }
}

async function playAll(st, tracks, startIdx) {
  const run = ++st.run;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (st.audioAktif) { try { st.audioAktif.pause(); } catch (e) { /* abaikan */ } }
  st.busy = true;
  renderButtons(st);
  await sleep(60); // Chrome: beri jeda setelah cancel() agar speak() tidak hilang
  for (let i = 0; i < tracks.length; i++) {
    if (run !== st.run) return;
    setActive(st, startIdx + i);
    await say(st, tracks[i], run);
    if (run !== st.run) return;
    if (i < tracks.length - 1) await sleep(st.slow ? 420 : 180);
  }
  if (run !== st.run) return;
  st.busy = false;
  setActive(st, -1);
  renderButtons(st);
}

function stop(st) {
  st.run++;
  st.busy = false;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (st.audioAktif) { try { st.audioAktif.pause(); } catch (e) { /* abaikan */ } }
  if (st.anim) { const A = st.anim; st.anim = null; A.done(); }
  setActive(st, -1);
  renderButtons(st);
  loop(st);
}

function setActive(st, idx) {
  st.seq.querySelectorAll("button").forEach((b, i) => b.classList.toggle("on", i === idx));
  st.extra.querySelectorAll("button").forEach((b) => b.classList.toggle("on", Number(b.dataset.i) === idx));
}

function renderButtons(st) {
  const label = (st.data && st.data.tombol) || "Dengarkan";
  st.playBtn.innerHTML = st.busy ? `${STOP_ICON}<span>Berhenti</span>` : `${PLAY_ICON}<span>${label}</span>`;
  st.playBtn.classList.toggle("busy", st.busy);
}

function build(st) {
  const d = st.data;
  const tracks = d.tracks || [];
  const extras = d.extras || [];
  st.box.style.setProperty("--mw-size", `${d.size || 280}px`);
  st.seq.innerHTML = "";
  if (tracks.length > 1) {
    tracks.forEach((t, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = t.label;
      b.className = i === tracks.length - 1 && d.akhirKata ? "word" : "";
      b.onclick = () => playAll(st, [t], i);
      st.seq.appendChild(b);
    });
  }
  st.extra.innerHTML = "";
  if (extras.length) {
    const lbl = document.createElement("span");
    lbl.textContent = "Coba kata:";
    st.extra.appendChild(lbl);
    extras.forEach((t, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.i = String(1000 + i);
      b.textContent = `${t.emoji ? t.emoji + " " : ""}${t.label}`;
      b.onclick = () => playAll(st, [t], 1000 + i);
      st.extra.appendChild(b);
    });
  }
  tracks.forEach(siapkan);
  extras.forEach(siapkan);
  st.playBtn.onclick = () => (st.busy ? stop(st) : playAll(st, tracks, 0));
  renderButtons(st);
  if (tracks.length) caption(st, tracks[0]);
  highlight(st, null);
}

export default function (component) {
  const { data, parentElement } = component;
  let st = INST.get(parentElement);
  if (!st) { st = setup(parentElement); INST.set(parentElement, st); }
  st.data = data || {};
  const sig = JSON.stringify(st.data);
  if (sig !== st.sig) {
    const hurufBerubah = st.sig != null && JSON.stringify(JSON.parse(st.sig).tracks) !== JSON.stringify(st.data.tracks);
    if (st.busy) stop(st);
    st.sig = sig;
    build(st);
    // putar otomatis saat huruf diganti (bukan saat pertama kali tampil)
    const aktif = !navigator.userActivation || navigator.userActivation.hasBeenActive;
    if (hurufBerubah && st.data.auto && aktif) setTimeout(() => playAll(st, st.data.tracks || [], 0), 120);
  }
  return () => {
    st.run++;
    if (st.raf) cancelAnimationFrame(st.raf);
    st.raf = 0;
    if (st.busy && window.speechSynthesis) window.speechSynthesis.cancel();
    INST.delete(parentElement);
  };
}
