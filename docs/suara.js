// Suara aplikasi HP: file MP3 suara manusia (neural "Gadis"), TTS Android untuk
// teks lain, dan pengenalan ucapan (STT) Android.
//
// Di dalam APK, MainActivity menyediakan objek `SibiAndroid` (TextToSpeech +
// SpeechRecognizer bawaan Android). WebView Android tidak punya Web Speech API,
// jadi `speechSynthesis` di-polyfill ke TTS Android agar sibi/mulut.js tetap bisa
// menyelaraskan gerak mulut (onstart/onend) untuk teks yang belum punya file suara.

const A = window.SibiAndroid;

// ------------------------------------------------------------ polyfill TTS
if (A && A.ttsSpeak) {
  const antre = new Map();
  let n = 0;
  class Ucapan {
    constructor(text) {
      this.text = text; this.lang = "id-ID"; this.rate = 1; this.pitch = 1; this.voice = null;
      this.onstart = null; this.onend = null; this.onerror = null;
    }
  }
  const ss = {
    speaking: false, pending: false, paused: false,
    speak(u) {
      const id = `u${++n}`;
      antre.set(id, u);
      ss.speaking = true;
      A.ttsSpeak(id, String(u.text || ""), Number(u.rate) || 1, Number(u.pitch) || 1);
    },
    cancel() {
      A.ttsStop();
      const lama = [...antre.values()];
      antre.clear();
      ss.speaking = false;
      lama.forEach((u) => { try { (u.onerror || u.onend || (() => {}))({ error: "interrupted" }); } catch (e) { /* abaikan */ } });
    },
    getVoices() { return A.ttsReady() ? [{ name: "Android", lang: "id-ID", default: true, localService: true }] : []; },
    pause() {}, resume() {}, addEventListener() {}, removeEventListener() {},
  };
  window.__sibiTts = (id, jenis) => {
    const u = antre.get(id);
    if (!u) return;
    if (jenis === "start") { if (u.onstart) u.onstart({}); return; }
    antre.delete(id);
    ss.speaking = antre.size > 0;
    const f = jenis === "end" ? u.onend : (u.onerror || u.onend);
    if (f) f({});
  };
  try { Object.defineProperty(window, "speechSynthesis", { value: ss, configurable: true }); } catch (e) { window.speechSynthesis = ss; }
  window.SpeechSynthesisUtterance = Ucapan;
}

// ------------------------------------------------------------ file suara
let manifest = { normal: {}, pelan: {} };
export function setManifest(m) { manifest = m || manifest; }

const rapikan = (t) => String(t || "").split(/\s+/).filter(Boolean).join(" ");

/** Info file suara {url, mulai, lama} untuk teks, atau null bila belum ada. */
export function audioUntuk(teks, pelan = false) {
  const t = rapikan(teks);
  const m = manifest[pelan ? "pelan" : "normal"];
  return m[t] || m[t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()] || null;
}

let pemutar = null;
/** Ucapkan teks: file suara manusia bila ada, selain itu TTS perangkat. */
export function ucapkan(teks, { pelan = false } = {}) {
  const t = rapikan(teks);
  if (!t) return;
  diam();
  const info = audioUntuk(t, pelan);
  if (info) {
    pemutar = new Audio(info.url);
    pemutar.play().catch(() => ttsPerangkat(t, pelan));
    return;
  }
  ttsPerangkat(t, pelan);
}

function ttsPerangkat(t, pelan) {
  const ss = window.speechSynthesis;
  if (!ss || !window.SpeechSynthesisUtterance) return;
  const u = new SpeechSynthesisUtterance(t);
  u.lang = "id-ID";
  u.rate = pelan ? 0.6 : 0.95;
  ss.speak(u);
}

export function diam() {
  if (pemutar) { try { pemutar.pause(); } catch (e) { /* abaikan */ } pemutar = null; }
  if (window.speechSynthesis) { try { window.speechSynthesis.cancel(); } catch (e) { /* abaikan */ } }
}

// ------------------------------------------------------------ dengar (STT)
export function bisaDengar() {
  return !!((A && A.sttStart) || window.SpeechRecognition || window.webkitSpeechRecognition);
}

/** Mulai mendengarkan; panggil fungsi kembalian untuk berhenti. */
export function dengar({ sebagian, hasil, galat, selesai }) {
  if (A && A.sttStart) {
    window.__sibiStt = (jenis, teks) => {
      if (jenis === "partial" && sebagian) sebagian(teks);
      else if (jenis === "final" && hasil) hasil(teks);
      else if (jenis === "error" && galat) galat(teks);
      if (jenis === "final" || jenis === "error" || jenis === "end") { if (selesai) selesai(); }
    };
    A.sttStart("id-ID");
    return () => A.sttStop();
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { if (galat) galat("Pengenalan suara tidak tersedia di perangkat ini."); return () => {}; }
  const r = new SR();
  r.lang = "id-ID";
  r.interimResults = true;
  r.onresult = (e) => {
    const res = e.results[e.results.length - 1];
    const t = res[0].transcript;
    if (res.isFinal) { if (hasil) hasil(t); } else if (sebagian) sebagian(t);
  };
  r.onerror = (e) => { if (galat) galat(e.error === "not-allowed" ? "Izin mikrofon ditolak." : "Suara tidak terdengar jelas. Coba lagi."); };
  r.onend = () => { if (selesai) selesai(); };
  r.start();
  return () => r.stop();
}
