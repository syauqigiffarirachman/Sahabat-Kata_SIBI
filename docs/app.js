// Isyarat SIBI — aplikasi HP (berjalan offline di dalam WebView APK).
import { setManifest, audioUntuk, ucapkan, diam } from "./suara.js";
import pasangMulut from "./mulut.js";
import { siapkan as siapkanKosakata } from "./kosakata.js";

const VERSI = "1.1.0";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let K = null; // konten: huruf, contoh kata, kata isyarat, suara
const isi = $("#isi");
const JUDUL = { belajar: "Belajar huruf", kamus: "Kamus kata", kuis: "Kuis", eja: "Eja kata", kamera: "Kamera & suara" };

// ------------------------------------------------------------ penyimpanan
const simpan = {
  ambil(k, awal) { try { const v = localStorage.getItem(`sibi.${k}`); return v == null ? awal : JSON.parse(v); } catch (e) { return awal; } },
  taruh(k, v) { try { localStorage.setItem(`sibi.${k}`, JSON.stringify(v)); } catch (e) { /* abaikan */ } },
};

const S = {
  hal: "belajar",
  huruf: simpan.ambil("huruf", "A"),
  bisa: new Set(simpan.ambil("bisa", [])),
  kuis: null,
  // skor per jenis kuis; "skor" lama (versi 1.0) = skor kuis huruf
  skorKuis: Object.assign({
    huruf: simpan.ambil("skor", { benar: 0, soal: 0 }), kata: { benar: 0, soal: 0 }, kalimat: { benar: 0, soal: 0 },
  }, simpan.ambil("skorKuis", {})),
  jenisKuis: simpan.ambil("jenisKuis", "huruf"),
  kuisKata: null,
  kuisKal: null,
  kamusBag: "kata",
  kamusKat: "Semua",
  eja: simpan.ambil("eja", "APEL"),
  cari: "",
};

// ------------------------------------------------------------ bantuan UI
let toastT = 0;
function toast(pesan) {
  const t = $("#toast");
  t.textContent = pesan;
  t.classList.add("tampil");
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove("tampil"), 2200);
}

const foto = (h) => `foto/${h}.webp`;
// label=false menyembunyikan hurufnya (kuis), agar jawaban tidak terlihat.
function ubin(h, ukuran, label = true) {
  return `<div class="ubin" style="--u:${ukuran}px"><img src="${foto(h)}" alt="${label ? `Isyarat huruf ${h}` : "Isyarat huruf"}" loading="lazy" decoding="async" width="${ukuran}" height="${ukuran}">${label ? `<b>${h}</b>` : ""}</div>`;
}
function strip(kata, ukuran = 56, label = true) {
  const huruf = [...kata.toUpperCase()].filter((c) => K.hurufMap[c]);
  return `<div class="strip">${huruf.map((h) => ubin(h, ukuran, label)).join("")}</div>`;
}
const IKON_SUARA = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 9v6h4l5 5V4L7 9zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg>';
function kartuKata(kata, emoji) {
  return `<div class="kartu"><div class="emoji" aria-hidden="true">${emoji}</div><div class="kata">${esc(kata)}</div>${strip(kata)}
    <button type="button" class="btn lebar" data-ucap="${esc(kata)}">${IKON_SUARA}Dengarkan “${esc(kata)}”</button></div>`;
}

// ------------------------------------------------------------ wajah bicara (sibi/mulut.js)
const mulutAktif = new Set();
function track(label, say, nama, teksSuara, extra = {}) {
  return { label, say, nama, audio: audioUntuk(teksSuara), audioPelan: audioUntuk(teksSuara, true), ...extra };
}
const trackHuruf = (h) => track(h, K.hurufMap[h].ucap, true, K.hurufMap[h].suara || h);

function mulut(host, data) {
  if (!host.shadowRoot) {
    const sr = host.attachShadow({ mode: "open" });
    sr.innerHTML = '<link rel="stylesheet" href="mulut.css"><div class="mw"></div>';
  }
  host.__bersih = pasangMulut({ data, parentElement: host.shadowRoot });
  mulutAktif.add(host);
}
function bersihkanMulut() {
  for (const h of mulutAktif) { try { h.__bersih && h.__bersih(); } catch (e) { /* abaikan */ } }
  mulutAktif.clear();
}

// ------------------------------------------------------------ navigasi
let tutupHalaman = null;
async function buka(hal, { riwayat = true } = {}) {
  if (!JUDUL[hal]) hal = "belajar";
  if (tutupHalaman) { try { tutupHalaman(); } catch (e) { /* abaikan */ } tutupHalaman = null; }
  bersihkanMulut();
  diam();
  S.hal = hal;
  $("#subjudul").textContent = JUDUL[hal];
  document.querySelectorAll(".nav button").forEach((b) => {
    if (b.dataset.hal === hal) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  if (riwayat && location.hash !== `#${hal}`) history.pushState({ hal }, "", `#${hal}`);
  window.scrollTo(0, 0);
  isi.innerHTML = "";
  tutupHalaman = (await HALAMAN[hal]()) || null;
}
window.addEventListener("popstate", () => buka(location.hash.slice(1) || "belajar", { riwayat: false }));

// Tombol "kembali" Android: tutup dialog, lalu kembali ke Belajar, baru keluar aplikasi.
window.sibiKembali = () => {
  const d = $("#tentang");
  if (d.open) { d.close(); return true; }
  if (S.hal !== "belajar") { buka("belajar"); return true; }
  return false;
};

document.querySelector(".nav").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-hal]");
  if (b) buka(b.dataset.hal);
});
$("#btn-info").addEventListener("click", () => { $("#versi").textContent = `Versi ${VERSI}`; $("#tentang").showModal(); });

// tombol "Dengarkan" di mana pun
isi.addEventListener("click", (e) => {
  const b = e.target.closest("[data-ucap]");
  if (b) ucapkan(b.dataset.ucap);
});

// ------------------------------------------------------------ halaman: belajar
function belajar() {
  const h = S.huruf;
  const info = K.hurufMap[h];
  const contoh = K.contoh[h] || [];
  isi.innerHTML = `
    <div class="chips" role="group" aria-label="Pilih huruf">
      ${K.huruf.map((x) => `<button type="button" class="chip ${S.bisa.has(x.h) ? "bisa" : ""}" data-h="${x.h}" aria-pressed="${x.h === h}">${x.h}</button>`).join("")}
    </div>
    <div class="kemajuan" aria-hidden="true"><i style="width:${(S.bisa.size / K.huruf.length) * 100}%"></i></div>
    <div class="kemajuan-teks">${S.bisa.size} dari ${K.huruf.length} huruf sudah bisa</div>
    <div class="duo">
      <div class="kotak-tangan" id="tangan"><img src="${foto(h)}" alt="Bentuk tangan huruf ${h}" width="300" height="300"></div>
      <div><div class="huruf-besar">${h}</div><div class="dibaca">dibaca “${esc(info.ucap)}”</div></div>
    </div>
    <p class="kecil geser-tip">Usap foto ke kiri/kanan untuk ganti huruf.</p>
    <div class="mulut-host" id="mulut"></div>
    <div class="desk">${esc(info.deskripsi)}</div>
    ${h === "J" || h === "Z" ? '<div class="info">Huruf ini bergerak. Gambar menunjukkan posisi awal tangan.</div>' : ""}
    <div class="tip">💡 ${esc(info.tips)}</div>
    <div class="gerak">👄 <b>Gerak mulut:</b> ${esc(info.mulut)}</div>
    <div class="baris" style="margin-top:14px">
      <button type="button" class="btn" id="mundur">◀ Kembali</button>
      <button type="button" class="btn ${S.bisa.has(h) ? "bintang" : ""}" id="tandai">${S.bisa.has(h) ? "★ Bisa!" : "☆ Bisa"}</button>
      <button type="button" class="btn" id="maju">Lanjut ▶</button>
    </div>
    <h3>Kata yang diawali huruf ${h}</h3>
    ${contoh.map(([k, e]) => kartuKata(k, e)).join("")}`;

  const aktif = isi.querySelector(".chip[aria-pressed='true']");
  if (aktif) aktif.scrollIntoView({ block: "nearest", inline: "center" });

  const host = $("#mulut");
  mulut(host, {
    tracks: [trackHuruf(h)],
    extras: contoh.map(([k, e]) => track(k, k, false, k, { emoji: e })),
    size: 260, auto: true, tombol: "Dengarkan",
  });

  const ganti = (baru) => {
    if (baru === S.huruf) return;
    S.huruf = baru;
    simpan.taruh("huruf", baru);
    perbaruiHuruf(host);
  };
  isi.querySelector(".chips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (b) ganti(b.dataset.h);
  });
  const geser = (d) => {
    const i = K.huruf.findIndex((x) => x.h === S.huruf);
    ganti(K.huruf[(i + d + K.huruf.length) % K.huruf.length].h);
  };
  $("#mundur").onclick = () => geser(-1);
  $("#maju").onclick = () => geser(1);
  $("#tandai").onclick = () => {
    if (S.bisa.has(S.huruf)) S.bisa.delete(S.huruf); else { S.bisa.add(S.huruf); toast(`Hebat! Huruf ${S.huruf} sudah bisa ⭐`); }
    simpan.taruh("bisa", [...S.bisa]);
    perbaruiHuruf(host);
  };
  // usap foto tangan ke kiri/kanan untuk ganti huruf
  let x0 = null;
  const t = $("#tangan");
  t.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  t.addEventListener("touchend", (e) => {
    if (x0 == null) return;
    const dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 60) geser(dx < 0 ? 1 : -1);
  });
}

// Perbarui isi tanpa membangun ulang wajah (agar wajah langsung mengucapkan huruf baru).
function perbaruiHuruf(host) {
  const h = S.huruf;
  const info = K.hurufMap[h];
  const contoh = K.contoh[h] || [];
  isi.querySelectorAll(".chip").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.h === h));
    b.classList.toggle("bisa", S.bisa.has(b.dataset.h));
  });
  const aktif = isi.querySelector(".chip[aria-pressed='true']");
  if (aktif) aktif.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  isi.querySelector(".kemajuan i").style.width = `${(S.bisa.size / K.huruf.length) * 100}%`;
  isi.querySelector(".kemajuan-teks").textContent = `${S.bisa.size} dari ${K.huruf.length} huruf sudah bisa`;
  const img = isi.querySelector("#tangan img");
  img.src = foto(h);
  img.alt = `Bentuk tangan huruf ${h}`;
  isi.querySelector(".huruf-besar").textContent = h;
  isi.querySelector(".dibaca").textContent = `dibaca “${info.ucap}”`;
  isi.querySelector(".desk").textContent = info.deskripsi;
  const lama = isi.querySelector(".info");
  if (lama) lama.remove();
  if (h === "J" || h === "Z") isi.querySelector(".desk").insertAdjacentHTML("afterend", '<div class="info">Huruf ini bergerak. Gambar menunjukkan posisi awal tangan.</div>');
  isi.querySelector(".tip").textContent = `💡 ${info.tips}`;
  isi.querySelector(".gerak").innerHTML = `👄 <b>Gerak mulut:</b> ${esc(info.mulut)}`;
  const tb = $("#tandai");
  tb.className = `btn ${S.bisa.has(h) ? "bintang" : ""}`;
  tb.textContent = S.bisa.has(h) ? "★ Bisa!" : "☆ Bisa";
  const judul = [...isi.querySelectorAll("h3")].pop();
  judul.textContent = `Kata yang diawali huruf ${h}`;
  isi.querySelectorAll(".kartu").forEach((k) => k.remove());
  judul.insertAdjacentHTML("afterend", contoh.map(([k, e]) => kartuKata(k, e)).join(""));
  mulut(host, {
    tracks: [trackHuruf(h)],
    extras: contoh.map(([k, e]) => track(k, k, false, k, { emoji: e })),
    size: 260, auto: true, tombol: "Dengarkan",
  });
}

// ------------------------------------------------------------ halaman: kamus
const PER_HALAMAN = 40;
const judulKata = (k) => k.charAt(0) + k.slice(1).toLowerCase();

function kamus() {
  const BAGIAN = { kata: "🖼️ Kata", isyarat: "👋 Isyarat", kalimat: "💬 Kalimat" };
  isi.innerHTML = `
    <div class="segmen" role="group" aria-label="Bagian kamus">
      ${Object.entries(BAGIAN).map(([k, v]) => `<button type="button" data-bag="${k}" aria-pressed="${k === S.kamusBag}">${v}</button>`).join("")}
    </div>
    <input type="search" class="cari" id="cari" placeholder="Cari kata, mis. makan" aria-label="Cari kata" value="${esc(S.cari)}" autocomplete="off">
    <div class="chips kat-chips" id="kat" role="group" aria-label="Kategori"></div>
    <div id="hasil"></div>`;
  let batas = PER_HALAMAN;

  const tampil = () => {
    const q = S.cari.trim().toLowerCase();
    const out = $("#hasil");
    const kat = $("#kat");
    kat.hidden = S.kamusBag !== "kata";
    if (S.kamusBag === "kata") {
      kat.innerHTML = [["Semua", "🌈", K.kosakata.length], ...K.kategori].map(([n, ikon, jml]) =>
        `<button type="button" class="chip kat" data-kat="${esc(n)}" aria-pressed="${n === S.kamusKat}">${ikon} ${esc(n)} <small>${jml}</small></button>`).join("");
      const kata = K.kosakata.filter(([k, , kt]) => (S.kamusKat === "Semua" || kt === S.kamusKat) && (!q || k.toLowerCase().includes(q)));
      if (!kata.length) { out.innerHTML = '<div class="kosong">Kata tidak ditemukan. Coba kategori “Semua”.</div>'; return; }
      out.innerHTML = `<p class="kecil">${kata.length} kata bergambar</p>
        ${kata.slice(0, batas).map(([k, e]) => kartuKata(k, e)).join("")}
        ${kata.length > batas ? `<button type="button" class="btn lebar" id="lagi">Tampilkan ${Math.min(PER_HALAMAN, kata.length - batas)} kata lagi</button>` : ""}`;
      const lagi = $("#lagi");
      if (lagi) lagi.onclick = () => { batas += PER_HALAMAN; tampil(); };
      return;
    }
    if (S.kamusBag === "isyarat") {
      const isyarat = Object.entries(K.kataIsyarat).filter(([k, v]) => !q || k.toLowerCase().includes(q) || v.deskripsi.toLowerCase().includes(q));
      if (!isyarat.length) { out.innerHTML = '<div class="kosong">Isyarat kata tidak ditemukan.</div>'; return; }
      out.innerHTML = `<p class="kecil">${isyarat.length} isyarat kata sehari-hari. Tanda 📷 = bisa dikenali kamera.</p>
        ${isyarat.map(([k, v]) => { const kam = K.kataKamera[k]; return `
        <details class="isyarat"><summary>${esc(judulKata(k))}${kam ? " 📷" : ""}</summary>
          <div class="desk">${esc(v.deskripsi)}</div><div class="tip">💡 ${esc(v.tips)}</div>
          ${kam ? `<div class="info">📷 Di kamera: ${esc(kam.cara)}</div>` : ""}
          <button type="button" class="btn lebar" style="margin-top:10px" data-ucap="${esc(judulKata(k))}">${IKON_SUARA}Dengarkan</button>
        </details>`; }).join("")}`;
      return;
    }
    const kal = K.kalimat.filter(([k]) => !q || k.toLowerCase().includes(q));
    if (!kal.length) { out.innerHTML = '<div class="kosong">Kalimat tidak ditemukan.</div>'; return; }
    out.innerHTML = `<p class="kecil">${kal.length} kalimat sehari-hari. Buka untuk melihat isyarat tiap kata.</p>
      ${kal.map(([k, e]) => `
      <details class="isyarat kalimat"><summary><span class="em">${e}</span>${esc(k)}</summary>
        ${k.replace(/[.,?!]/g, "").split(/\s+/).map((t) => `<div class="kata-kecil">${esc(t)}</div>${strip(t, 44)}`).join("")}
        <button type="button" class="btn lebar" style="margin-top:6px" data-ucap="${esc(k)}">${IKON_SUARA}Dengarkan</button>
      </details>`).join("")}`;
  };

  isi.querySelector(".segmen").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-bag]");
    if (!b) return;
    S.kamusBag = b.dataset.bag;
    isi.querySelectorAll("[data-bag]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    batas = PER_HALAMAN;
    tampil();
  });
  $("#kat").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-kat]");
    if (!b) return;
    S.kamusKat = b.dataset.kat;
    batas = PER_HALAMAN;
    tampil();
    const aktif = isi.querySelector(".chip.kat[aria-pressed='true']");
    if (aktif) aktif.scrollIntoView({ block: "nearest", inline: "center" });
  });
  let t = 0;
  $("#cari").addEventListener("input", (e) => {
    S.cari = e.target.value;
    clearTimeout(t);
    t = setTimeout(() => { batas = PER_HALAMAN; tampil(); }, 150);
  });
  tampil();
}

// ------------------------------------------------------------ halaman: kuis
const KATA_KECIL = new Set(["DI", "KE", "DAN", "ITU", "INI", "DARI", "YA"]);
const acak = (a) => { const b = [...a]; for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
const ambil = (a) => a[Math.floor(Math.random() * a.length)];
const pecahKalimat = (k) => k.replace(/[.,?!]/g, "").split(/\s+/).filter(Boolean);
let kataKuis = null;
function daftarKataKuis() {
  // satu kata, 3-7 huruf: enak dieja di layar HP
  if (!kataKuis) kataKuis = K.kosakata.filter(([k]) => /^[A-Za-z]{3,7}$/.test(k));
  return kataKuis;
}

function soalBaru() {
  const semua = K.huruf.map((x) => x.h);
  const benar = semua[Math.floor(Math.random() * semua.length)];
  const lain = acak(semua.filter((x) => x !== benar)).slice(0, 3);
  S.kuis = { benar, pilihan: acak([...lain, benar]), jawab: null };
}

function soalKata() {
  const semua = daftarKataKuis();
  const [k, e, kat] = ambil(semua);
  const sama = acak(semua.filter((x) => x[2] === kat && x[0] !== k)).slice(0, 2);
  const lain = acak(semua.filter((x) => x[2] !== kat)).slice(0, 3 - sama.length);
  S.kuisKata = { benar: k, emoji: e, pilihan: acak([...sama, ...lain, [k, e]]).map((x) => [x[0], x[1]]), jawab: null };
}

function soalKalimat() {
  const [kalimat, emoji] = ambil(K.kalimat);
  const kata = pecahKalimat(kalimat);
  if (Math.random() < 0.5 && kata.length >= 2) {
    const calon = kata.map((t, i) => i).filter((i) => kata[i].length >= 3 && !KATA_KECIL.has(kata[i].toUpperCase()));
    const i = ambil(calon);
    const benar = judulKata(kata[i]);
    const lain = acak(daftarKataKuis().filter(([k]) => k.toUpperCase() !== benar.toUpperCase())).slice(0, 3).map((x) => x[0]);
    S.kuisKal = { jenis: "lengkapi", kalimat, emoji, kata, i, benar, pilihan: acak([...lain, benar]), jawab: null };
  } else {
    let urut = kata.map((_, i) => i);
    let acakan = acak(urut);
    while (kata.length > 1 && acakan.join() === urut.join()) acakan = acak(urut);
    S.kuisKal = { jenis: "susun", kalimat, emoji, kata, acak: acakan, susun: [], jawab: null };
  }
}

function konfeti() {
  const k = document.createElement("div");
  k.className = "konfeti";
  const e = ["🎉", "⭐", "🎈", "✨", "🌟"];
  for (let i = 0; i < 18; i++) {
    const s = document.createElement("span");
    s.textContent = e[i % e.length];
    s.style.left = `${Math.random() * 100}%`;
    s.style.animationDelay = `${Math.random() * 0.4}s`;
    k.appendChild(s);
  }
  document.body.appendChild(k);
  setTimeout(() => k.remove(), 2400);
}

function catat(jenis, ok) {
  const sk = S.skorKuis[jenis];
  sk.soal += 1;
  if (ok) { sk.benar += 1; konfeti(); }
  simpan.taruh("skorKuis", S.skorKuis);
}

const JENIS_KUIS = { huruf: "🔤 Huruf", kata: "🖼️ Kata", kalimat: "💬 Kalimat" };
function kuis() {
  isi.innerHTML = `
    <div class="segmen" role="group" aria-label="Jenis kuis">
      ${Object.entries(JENIS_KUIS).map(([k, v]) => `<button type="button" data-jk="${k}" aria-pressed="${k === S.jenisKuis}">${v}</button>`).join("")}
    </div>
    <div id="soal"></div>`;
  isi.querySelector(".segmen").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-jk]");
    if (!b || b.dataset.jk === S.jenisKuis) return;
    S.jenisKuis = b.dataset.jk;
    simpan.taruh("jenisKuis", S.jenisKuis);
    kuis();
  });
  ({ huruf: kuisHuruf, kata: kuisKata, kalimat: kuisKalimat })[S.jenisKuis]($("#soal"));
}

const skorHtml = (judul, jenis) => `<div class="skor"><span>${judul}</span><span>Skor <b>${S.skorKuis[jenis].benar}</b> / ${S.skorKuis[jenis].soal}</span></div>`;
function tombolLanjut(el, fn) {
  el.insertAdjacentHTML("beforeend", '<button type="button" class="btn utama lebar" id="lanjut" style="margin-top:10px">Soal berikutnya ▶</button>');
  $("#lanjut").onclick = () => { fn(); kuis(); };
}

function kuisHuruf(el) {
  if (!S.kuis) soalBaru();
  const q = S.kuis;
  el.innerHTML = `
    ${skorHtml("Huruf apa ini?", "huruf")}
    <div class="kotak-tangan"><img src="${foto(q.benar)}" alt="Tebak bentuk tangan ini" width="300" height="300"></div>
    <div class="pilihan">${q.pilihan.map((h) => {
      let kelas = "btn";
      if (q.jawab) { if (h === q.benar) kelas += " benar"; else if (h === q.jawab) kelas += " salah"; }
      return `<button type="button" class="${kelas}" data-j="${h}" ${q.jawab ? "disabled" : ""}>${h}</button>`;
    }).join("")}</div>
    <div id="umpan"></div>`;
  if (q.jawab) {
    const ok = q.jawab === q.benar;
    $("#umpan").innerHTML = `<div class="umpan ${ok ? "ok" : "no"}">${ok ? `Hebat! Ini huruf ${q.benar}. 🎉` : `Belum tepat. Jawabannya huruf ${q.benar}. Ayo coba lagi!`}</div>`;
    tombolLanjut($("#umpan"), soalBaru);
  }
  el.querySelector(".pilihan").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-j]");
    if (!b || S.kuis.jawab) return;
    S.kuis.jawab = b.dataset.j;
    catat("huruf", b.dataset.j === S.kuis.benar);
    const info = K.hurufMap[S.kuis.benar];
    ucapkan(info.suara || S.kuis.benar);
    kuis();
  });
}

function pilihanKata(q, daftar) {
  return `<div class="pilihan kata">${daftar.map(([label, nilai]) => {
    let kelas = "btn";
    if (q.jawab) { if (nilai === q.benar) kelas += " benar"; else if (nilai === q.jawab) kelas += " salah"; }
    return `<button type="button" class="${kelas}" data-j="${esc(nilai)}" ${q.jawab ? "disabled" : ""}>${label}</button>`;
  }).join("")}</div>`;
}

function kuisKata(el) {
  if (!S.kuisKata) soalKata();
  const q = S.kuisKata;
  el.innerHTML = `
    ${skorHtml("Kata apa ini?", "kata")}
    <p class="kecil" style="text-align:center;margin:0">Baca isyarat hurufnya satu per satu.</p>
    ${strip(q.benar, 64, false)}
    ${pilihanKata(q, q.pilihan.map(([k, e]) => [`<span class="em">${e}</span>${esc(k)}`, k]))}
    <div id="umpan"></div>`;
  if (q.jawab) {
    const ok = q.jawab === q.benar;
    $("#umpan").innerHTML = `<div class="umpan ${ok ? "ok" : "no"}">${ok ? `Hebat! Ini kata ${q.emoji} ${esc(q.benar)}. 🎉` : `Belum tepat. Jawabannya ${q.emoji} ${esc(q.benar)}. Ayo coba lagi!`}</div>`;
    tombolLanjut($("#umpan"), soalKata);
  }
  el.querySelector(".pilihan").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-j]");
    if (!b || S.kuisKata.jawab) return;
    S.kuisKata.jawab = b.dataset.j;
    catat("kata", b.dataset.j === S.kuisKata.benar);
    ucapkan(S.kuisKata.benar);
    kuis();
  });
}

function kuisKalimat(el) {
  if (!S.kuisKal) soalKalimat();
  const q = S.kuisKal;
  let ok = false;
  if (q.jenis === "lengkapi") {
    const kalimat = q.kata.map((t, i) => (i === q.i && !q.jawab ? '<u>?</u>' : esc(t))).join(" ");
    el.innerHTML = `
      ${skorHtml("Lengkapi kalimatnya!", "kalimat")}
      <div class="soal-kalimat"><span class="em">${q.emoji}</span>${kalimat}</div>
      <p class="kecil" style="text-align:center;margin:0">Isyarat kata yang hilang:</p>
      ${strip(q.benar, 56, false)}
      ${pilihanKata(q, q.pilihan.map((k) => [esc(k), k]))}
      <div id="umpan"></div>`;
    el.querySelector(".pilihan").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-j]");
      if (!b || S.kuisKal.jawab) return;
      S.kuisKal.jawab = b.dataset.j;
      catat("kalimat", b.dataset.j === S.kuisKal.benar);
      ucapkan(S.kuisKal.kalimat);
      kuis();
    });
    ok = q.jawab === q.benar;
  } else {
    const tersusun = q.susun.map((j) => q.kata[j]).join(" ");
    el.innerHTML = `
      ${skorHtml("Susun kalimatnya!", "kalimat")}
      <p class="kecil" style="text-align:center;margin:0">Baca isyarat tiap kata, lalu tekan kata sesuai urutan.</p>
      <div class="soal-kalimat"><span class="em">${q.emoji}</span></div>
      ${q.kata.map((t) => strip(t, 40, false)).join('<div class="pemisah-kata"></div>')}
      <div class="susun">${esc(tersusun) || "…"}</div>
      <div class="susun-pilihan">${q.acak.map((j) =>
        `<button type="button" class="btn" data-s="${j}" ${q.jawab || q.susun.includes(j) ? "disabled" : ""}>${esc(q.kata[j])}</button>`).join("")}</div>
      ${q.susun.length && !q.jawab ? '<button type="button" class="btn lebar" id="ulang" style="margin-top:8px">↺ Ulangi susunan</button>' : ""}
      <div id="umpan"></div>`;
    el.querySelector(".susun-pilihan").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-s]");
      const qq = S.kuisKal;
      if (!b || qq.jawab) return;
      qq.susun.push(Number(b.dataset.s));
      if (qq.susun.length === qq.kata.length) {
        qq.jawab = qq.susun.map((j) => qq.kata[j]).join(" ");
        catat("kalimat", qq.jawab === qq.kata.join(" "));
        ucapkan(qq.kalimat);
      }
      kuis();
    });
    const ulang = $("#ulang");
    if (ulang) ulang.onclick = () => { S.kuisKal.susun = []; kuis(); };
    ok = q.jawab === q.kata.join(" ");
  }
  if (q.jawab) {
    $("#umpan").innerHTML = `<div class="umpan ${ok ? "ok" : "no"}">${ok ? `Hebat! ${esc(q.kalimat)} 🎉` : `Belum tepat. Kalimatnya: ${esc(q.kalimat)} Ayo coba lagi!`}</div>`;
    tombolLanjut($("#umpan"), soalKalimat);
  }
}

// ------------------------------------------------------------ halaman: eja
function eja() {
  isi.innerHTML = `
    <div class="isian"><input class="cari" id="eja-in" maxlength="30" value="${esc(S.eja)}" placeholder="Ketik kata atau nama" aria-label="Ketik kata atau nama" autocapitalize="characters" autocomplete="off" style="padding-left:14px;background-image:none"></div>
    <div id="eja-hasil"></div>`;
  const tampil = () => {
    bersihkanMulut();
    const kata = S.eja.toUpperCase().replace(/[^A-Z ]/g, " ").split(/\s+/).filter(Boolean);
    const out = $("#eja-hasil");
    if (!kata.length) { out.innerHTML = '<div class="kosong">Ketik satu kata untuk melihat urutan isyarat hurufnya.</div>'; return; }
    out.innerHTML = kata.map((k, i) => `<h3>${esc(k)}</h3>${strip(k, 72)}<div class="mulut-host" id="eja-m${i}"></div>`).join("");
    kata.forEach((k, i) => {
      const huruf = [...k];
      const tracks = huruf.map(trackHuruf);
      if (huruf.length > 1) {
        const judul = k.charAt(0) + k.slice(1).toLowerCase();
        tracks.push(track(judul, k.toLowerCase(), false, judul));
      }
      mulut($(`#eja-m${i}`), { tracks, extras: [], size: 240, auto: false, tombol: "Eja", akhirKata: huruf.length > 1 });
    });
  };
  let t = 0;
  $("#eja-in").addEventListener("input", (e) => {
    S.eja = e.target.value;
    simpan.taruh("eja", S.eja);
    clearTimeout(t);
    t = setTimeout(tampil, 350);
  });
  tampil();
}

// ------------------------------------------------------------ halaman: kamera & suara
async function kamera() {
  isi.innerHTML = '<div class="memuat"><span class="putar"></span>Menyiapkan kamera…</div>';
  const m = await import("./kamera.js");
  if (S.hal !== "kamera") return null;
  return m.tampilkan(isi, { K, strip, mulut, bersihkanMulut, track, toast });
}

const HALAMAN = { belajar, kamus, kuis, eja, kamera };

// ------------------------------------------------------------ mulai
async function mulai() {
  try {
    K = await (await fetch("data/konten.json")).json();
  } catch (e) {
    isi.innerHTML = '<div class="kosong">Gagal memuat isi aplikasi. Tutup lalu buka lagi aplikasinya.</div>';
    return;
  }
  K.hurufMap = Object.fromEntries(K.huruf.map((x) => [x.h, x]));
  siapkanKosakata(K);
  if (!JENIS_KUIS[S.jenisKuis]) S.jenisKuis = "huruf";
  setManifest(K.suara);
  if (!K.hurufMap[S.huruf]) S.huruf = "A";
  const awal = location.hash.slice(1);
  history.replaceState({ hal: awal || "belajar" }, "", `#${JUDUL[awal] ? awal : "belajar"}`);
  buka(JUDUL[awal] ? awal : "belajar", { riwayat: false });
}

// Hentikan suara saat aplikasi ke latar belakang.
document.addEventListener("visibilitychange", () => { if (document.hidden) diam(); });

mulai();
