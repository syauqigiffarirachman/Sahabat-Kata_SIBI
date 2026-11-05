package id.sibi.isyarat;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.res.AssetFileDescriptor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.View;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Isyarat SIBI: aplikasi web offline (assets/www) di dalam WebView.
 *
 * - Semua file disajikan dari dalam APK lewat https://appassets.androidplatform.net/assets/
 *   (konteks aman, sehingga kamera/WebAssembly MediaPipe boleh dipakai), termasuk
 *   permintaan Range untuk audio.
 * - Jembatan "SibiAndroid" memberi JavaScript akses ke TextToSpeech, SpeechRecognizer,
 *   dan getar bawaan Android (WebView tidak punya Web Speech API).
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String AWAL = "https://" + HOST + "/assets/www/index.html";
    private static final int REQ_KAMERA = 11;
    private static final int REQ_MIC = 12;

    private WebView web;
    private TextToSpeech tts;
    private volatile boolean ttsSiap = false;
    private SpeechRecognizer pengenal;
    private PermissionRequest izinTertunda;
    private String bahasaStt = "id-ID";

    @Override
    protected void onCreate(Bundle simpanan) {
        super.onCreate(simpanan);
        Window w = getWindow();
        w.setStatusBarColor(Color.parseColor("#4C6FFF"));
        w.setNavigationBarColor(Color.WHITE);
        w.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);

        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#F4F6FF"));
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        // Ikuti ukuran huruf sistem, tapi batasi agar tata letak anak tetap rapi.
        float skala = getResources().getConfiguration().fontScale;
        s.setTextZoom(Math.max(85, Math.min(130, Math.round(skala * 100))));

        web.setWebViewClient(new KlienWeb());
        web.setWebChromeClient(new KlienChrome());
        web.addJavascriptInterface(new Jembatan(), "SibiAndroid");

        tts = new TextToSpeech(this, status -> {
            if (status != TextToSpeech.SUCCESS) return;
            int r = tts.setLanguage(new Locale("id", "ID"));
            ttsSiap = r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED;
            tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override public void onStart(String id) { kirimTts(id, "start"); }
                @Override public void onDone(String id) { kirimTts(id, "end"); }
                @Override public void onError(String id) { kirimTts(id, "error"); }
                @Override public void onStop(String id, boolean disela) { kirimTts(id, "error"); }
            });
        });

        if (simpanan != null) web.restoreState(simpanan);
        else web.loadUrl(AWAL);
    }

    // ------------------------------------------------------------ penyajian aset
    private class KlienWeb extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest req) {
            Uri u = req.getUrl();
            String path = u.getPath();
            if (!HOST.equals(u.getHost()) || path == null || !path.startsWith("/assets/")) return null;
            return aset(path.substring("/assets/".length()), req.getRequestHeaders());
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
            Uri u = req.getUrl();
            if (HOST.equals(u.getHost())) return false;
            try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) { }
            return true;
        }
    }

    private static final Map<String, String> MIME = new HashMap<>();
    static {
        MIME.put("html", "text/html"); MIME.put("js", "text/javascript"); MIME.put("mjs", "text/javascript");
        MIME.put("css", "text/css"); MIME.put("json", "application/json"); MIME.put("wasm", "application/wasm");
        MIME.put("webp", "image/webp"); MIME.put("png", "image/png"); MIME.put("svg", "image/svg+xml");
        MIME.put("mp3", "audio/mpeg"); MIME.put("woff2", "font/woff2"); MIME.put("txt", "text/plain");
        MIME.put("task", "application/octet-stream");
    }

    private WebResourceResponse aset(String path, Map<String, String> header) {
        if (path.contains("..")) return tidakAda();
        int titik = path.lastIndexOf('.');
        String ext = titik >= 0 ? path.substring(titik + 1).toLowerCase(Locale.ROOT) : "";
        String mime = MIME.containsKey(ext) ? MIME.get(ext) : "application/octet-stream";
        String enc = mime.startsWith("text/") || mime.equals("application/json") ? "utf-8" : null;
        Map<String, String> h = new HashMap<>();
        h.put("Accept-Ranges", "bytes");
        h.put("Cache-Control", "no-cache");
        String range = null;
        for (Map.Entry<String, String> e : header.entrySet()) {
            if ("range".equalsIgnoreCase(e.getKey())) range = e.getValue();
        }
        try {
            if (range != null && range.startsWith("bytes=")) {
                byte[] semua = bacaSemua(getAssets().open(path));
                String[] bagian = range.substring(6).split("-", -1);
                long total = semua.length;
                long awal = bagian[0].isEmpty() ? 0 : Long.parseLong(bagian[0].trim());
                long akhir = bagian.length > 1 && !bagian[1].isEmpty() ? Long.parseLong(bagian[1].trim()) : total - 1;
                akhir = Math.min(akhir, total - 1);
                if (awal > akhir || awal >= total) awal = 0;
                int n = (int) (akhir - awal + 1);
                h.put("Content-Range", "bytes " + awal + "-" + akhir + "/" + total);
                h.put("Content-Length", String.valueOf(n));
                return new WebResourceResponse(mime, enc, 206, "Partial Content", h,
                        new ByteArrayInputStream(semua, (int) awal, n));
            }
            long panjang = panjangAset(path);
            if (panjang >= 0) h.put("Content-Length", String.valueOf(panjang));
            return new WebResourceResponse(mime, enc, 200, "OK", h, getAssets().open(path));
        } catch (IOException | NumberFormatException e) {
            return tidakAda();
        }
    }

    private long panjangAset(String path) {
        try (AssetFileDescriptor fd = getAssets().openFd(path)) {
            return fd.getLength();
        } catch (IOException e) {
            return -1; // aset terkompresi: panjang tidak diketahui, kirim tanpa Content-Length
        }
    }

    private static byte[] bacaSemua(InputStream in) throws IOException {
        try (InputStream i = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[16384];
            int n;
            while ((n = i.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        }
    }

    private static WebResourceResponse tidakAda() {
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", new HashMap<>(),
                new ByteArrayInputStream(new byte[0]));
    }

    // ------------------------------------------------------------ izin kamera untuk getUserMedia
    private class KlienChrome extends WebChromeClient {
        @Override
        public void onPermissionRequest(PermissionRequest req) {
            runOnUiThread(() -> {
                boolean minta = false;
                for (String r : req.getResources()) {
                    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(r)) minta = true;
                }
                if (!minta) { req.deny(); return; }
                if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                    req.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
                } else {
                    izinTertunda = req;
                    requestPermissions(new String[]{Manifest.permission.CAMERA}, REQ_KAMERA);
                }
            });
        }

        @Override
        public void onPermissionRequestCanceled(PermissionRequest req) {
            if (req == izinTertunda) izinTertunda = null;
        }
    }

    @Override
    public void onRequestPermissionsResult(int kode, String[] izin, int[] hasil) {
        super.onRequestPermissionsResult(kode, izin, hasil);
        boolean boleh = hasil.length > 0 && hasil[0] == PackageManager.PERMISSION_GRANTED;
        if (kode == REQ_KAMERA && izinTertunda != null) {
            if (boleh) izinTertunda.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
            else izinTertunda.deny();
            izinTertunda = null;
        } else if (kode == REQ_MIC) {
            if (boleh) mulaiDengar();
            else { kirimStt("error", "Izin mikrofon ditolak. Izinkan di Pengaturan HP untuk memakai fitur ini."); kirimStt("end", ""); }
        }
    }

    // ------------------------------------------------------------ jembatan JavaScript
    private class Jembatan {
        @JavascriptInterface public boolean ttsReady() { return ttsSiap; }

        @JavascriptInterface
        public void ttsSpeak(String id, String teks, double laju, double nada) {
            if (!ttsSiap) { kirimTts(id, "error"); return; }
            tts.setSpeechRate((float) Math.max(0.3, Math.min(2.0, laju)));
            tts.setPitch((float) Math.max(0.5, Math.min(2.0, nada)));
            Bundle p = new Bundle();
            p.putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, id);
            tts.speak(teks, TextToSpeech.QUEUE_ADD, p, id);
        }

        @JavascriptInterface public void ttsStop() { if (tts != null) tts.stop(); }

        @JavascriptInterface
        public void sttStart(String bahasa) {
            bahasaStt = bahasa == null || bahasa.isEmpty() ? "id-ID" : bahasa;
            runOnUiThread(() -> {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) mulaiDengar();
                else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);
            });
        }

        @JavascriptInterface public void sttStop() { runOnUiThread(() -> { if (pengenal != null) pengenal.stopListening(); }); }

        @JavascriptInterface
        public void getar(int ms) {
            Vibrator v = (Vibrator) getSystemService(VIBRATOR_SERVICE);
            if (v == null || !v.hasVibrator()) return;
            v.vibrate(VibrationEffect.createOneShot(Math.max(10, Math.min(500, ms)), VibrationEffect.DEFAULT_AMPLITUDE));
        }

        @JavascriptInterface
        public String versi() {
            try { return getPackageManager().getPackageInfo(getPackageName(), 0).versionName; }
            catch (Exception e) { return ""; }
        }
    }

    private void mulaiDengar() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            kirimStt("error", "Pengenalan suara tidak tersedia. Pasang/aktifkan aplikasi Google di HP ini.");
            kirimStt("end", "");
            return;
        }
        if (pengenal != null) pengenal.destroy();
        pengenal = SpeechRecognizer.createSpeechRecognizer(this);
        pengenal.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle b) { }
            @Override public void onBeginningOfSpeech() { }
            @Override public void onRmsChanged(float rms) { }
            @Override public void onBufferReceived(byte[] buf) { }
            @Override public void onEndOfSpeech() { }
            @Override public void onEvent(int jenis, Bundle b) { }
            @Override public void onPartialResults(Bundle b) { String t = teksPertama(b); if (t != null) kirimStt("partial", t); }
            @Override public void onResults(Bundle b) {
                String t = teksPertama(b);
                if (t != null) kirimStt("final", t); else kirimStt("error", "Suara tidak dikenali. Coba lagi.");
                kirimStt("end", "");
            }
            @Override public void onError(int kode) {
                String pesan;
                switch (kode) {
                    case SpeechRecognizer.ERROR_NO_MATCH:
                    case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: pesan = "Suara tidak terdengar jelas. Coba lagi lebih dekat ke HP."; break;
                    case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: pesan = "Izin mikrofon ditolak."; break;
                    case SpeechRecognizer.ERROR_NETWORK:
                    case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: pesan = "Butuh internet, atau unduh paket bahasa Indonesia offline di pengaturan Google."; break;
                    default: pesan = "Pengenalan suara gagal (kode " + kode + "). Coba lagi.";
                }
                kirimStt("error", pesan);
                kirimStt("end", "");
            }
        });
        Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, bahasaStt);
        i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        pengenal.startListening(i);
    }

    private static String teksPertama(Bundle b) {
        ArrayList<String> r = b == null ? null : b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        return r == null || r.isEmpty() ? null : r.get(0);
    }

    private void kirimTts(String id, String jenis) {
        jalankanJs("window.__sibiTts && window.__sibiTts(" + JSONObject.quote(id) + "," + JSONObject.quote(jenis) + ")");
    }

    private void kirimStt(String jenis, String teks) {
        jalankanJs("window.__sibiStt && window.__sibiStt(" + JSONObject.quote(jenis) + "," + JSONObject.quote(teks) + ")");
    }

    private void jalankanJs(String kode) {
        if (web != null) web.post(() -> { if (web != null) web.evaluateJavascript(kode, null); });
    }

    // ------------------------------------------------------------ siklus hidup
    @Override
    public void onBackPressed() {
        web.evaluateJavascript("window.sibiKembali ? window.sibiKembali() : false", v -> {
            if (!"true".equals(v)) finish();
        });
    }

    @Override
    protected void onPause() {
        web.evaluateJavascript("window.dispatchEvent(new Event('sibi-jeda'))", null);
        if (tts != null) tts.stop();
        if (pengenal != null) pengenal.cancel();
        web.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }

    @Override
    protected void onSaveInstanceState(Bundle keluar) {
        super.onSaveInstanceState(keluar);
        web.saveState(keluar);
    }

    @Override
    protected void onDestroy() {
        if (tts != null) tts.shutdown();
        if (pengenal != null) pengenal.destroy();
        if (web != null) {
            web.removeJavascriptInterface("SibiAndroid");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
