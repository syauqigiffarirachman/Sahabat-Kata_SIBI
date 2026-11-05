// Kosakata sehari-hari anak: saran kata saat mengeja, kalimat wajar, dan saran kalimat.
// Port dari sibi/kosakata.py; data dari data/konten.json (kosakata, kalimat, kataKamera).

export const kunci = (t) => String(t).toUpperCase().replace(/[^A-Z]/g, "");
export const token = (t) => String(t).split(/[\s,.!?]+/).map(kunci).filter(Boolean);
export const judul = (k) => k.charAt(0).toUpperCase() + k.slice(1).toLowerCase();

let PETA = new Map();
let KALIMAT = [];
const TANYA = new Set(["APA", "SIAPA", "MANA", "KAPAN", "KENAPA", "BERAPA"]);

export function siapkan(K) {
  PETA = new Map();
  for (const [k, e] of K.kosakata) if (!PETA.has(kunci(k))) PETA.set(kunci(k), [k, e]);
  for (const [k, v] of Object.entries(K.kataKamera || {})) if (!PETA.has(kunci(k))) PETA.set(kunci(k), [judul(k), v.emoji]);
  KALIMAT = K.kalimat || [];
}

/** Kata kosakata yang ejaannya sama persis (abaikan spasi/tanda hubung). */
export const cari = (t) => PETA.get(kunci(t)) || null;

/** Saran kata untuk huruf yang sudah dieja: "MA" -> [["Main","🧸"], ["Makan","🍽️"], ...]. */
export function saranKata(awalan, n = 6) {
  const a = kunci(awalan);
  if (!a) return [];
  const cocok = [];
  for (const [k, v] of PETA) if (k.startsWith(a)) cocok.push([k, v]);
  cocok.sort((x, y) => (x[0] !== a) - (y[0] !== a) || x[0].length - y[0].length || (x[0] < y[0] ? -1 : 1));
  return cocok.slice(0, n).map((x) => x[1]);
}

/** "SAYA MAU MAKAN" -> "Saya mau makan." */
export function rapikan(teks) {
  const kata = String(teks).split(/\s+/).filter(Boolean);
  if (!kata.length) return "";
  let s = kata.map((t) => { const k = cari(t); return (k ? k[0] : t).toLowerCase(); }).join(" ");
  s = s.charAt(0).toUpperCase() + s.slice(1);
  if (!/[.!?]$/.test(s)) s += token(teks).some((t) => TANYA.has(t)) ? "?" : ".";
  return s;
}

/** Kalimat sehari-hari yang paling mirip dengan kata-kata yang sudah dikenali kamera. */
export function saranKalimat(teks, n = 3) {
  const ada = new Set(token(teks));
  if (!ada.size) return [];
  const perlu = ada.size === 1 ? 1 : 2;
  const nilai = [];
  KALIMAT.forEach(([kal, emoji], i) => {
    const kk = token(kal);
    const sama = new Set(kk.filter((t) => ada.has(t))).size;
    if (sama >= Math.min(perlu, kk.length)) nilai.push([-sama, kk.length - sama, i, [kal, emoji]]);
  });
  nilai.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
  return nilai.slice(0, n).map((v) => v[3]);
}
