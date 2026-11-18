package app.mushaf.arabi;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceResponse;
import java.io.ByteArrayInputStream;
import org.json.JSONObject;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView web;
    private MushafDb data;
    private boolean full = false;
    private ValueCallback<Uri[]> chooser;
    private static final int REQ_FILE = 7;
    private static final String INDEX = "file:///android_asset/www/index.html";

    private File fontFile(String rw) { return new File(getFilesDir(), "font_" + rw.replaceAll("[^a-z_]", "")); }

    /** Callable from the page as window.Android.xxx (runs on a background thread) */
    private class Bridge {
        @JavascriptInterface public String getMeta(String riwaya) { return data.meta(riwaya); }
        @JavascriptInterface public String getAbout() { return data.about(); }
        @JavascriptInterface public void openUrl(final String url) {
            if (url == null || !(url.startsWith("https://") || url.startsWith("mailto:"))) return;
            runOnUiThread(new Runnable() {
                public void run() {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception e) { /* no browser */ }
                }
            });
        }
        @JavascriptInterface public void setFullscreen(final boolean on) {
            runOnUiThread(new Runnable() { public void run() { applyFullscreen(on); } });
        }
        @JavascriptInterface public String getRiwayat() { return data.riwayat(); }
        @JavascriptInterface public int findPage(String riwaya, int sura, int aya) { return data.findPage(riwaya, sura, aya); }
        @JavascriptInterface public String getPage(String riwaya, int page) { return data.page(riwaya, page); }

        /** search runs on its own thread (it scans the whole riwaya); the answer comes back through window.__sr(id, json) */
        @JavascriptInterface public void searchAsync(final String riwaya, final String q, final int id) {
            new Thread(new Runnable() {
                public void run() {
                    final String res = data.search(riwaya, q);
                    runOnUiThread(new Runnable() {
                        public void run() {
                            if (web != null) web.evaluateJavascript("window.__sr&&window.__sr(" + id + "," + JSONObject.quote(res) + ")", null);
                        }
                    });
                }
            }).start();
        }
        @JavascriptInterface public void copyText(final String text) {
            runOnUiThread(new Runnable() {
                public void run() {
                    try {
                        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                        cm.setPrimaryClip(ClipData.newPlainText("quran", text));
                    } catch (Exception e) { /* ignore */ }
                }
            });
        }
        @JavascriptInterface public void shareText(final String text) {
            runOnUiThread(new Runnable() {
                public void run() {
                    try {
                        Intent i = new Intent(Intent.ACTION_SEND);
                        i.setType("text/plain");
                        i.putExtra(Intent.EXTRA_TEXT, text);
                        startActivity(Intent.createChooser(i, null));
                    } catch (Exception e) { /* no share target */ }
                }
            });
        }

        @JavascriptInterface public String getFont(String rw) {
            try {
                File f = fontFile(rw);
                if (!f.exists()) return "";
                FileInputStream in = new FileInputStream(f);
                byte[] b = new byte[(int) f.length()];
                int n = 0, r;
                while (n < b.length && (r = in.read(b, n, b.length - n)) > 0) n += r;
                in.close();
                return Base64.encodeToString(b, Base64.NO_WRAP);
            } catch (Exception e) { return ""; }
        }
        @JavascriptInterface public boolean saveFont(String rw, String b64) {
            try {
                if (b64 == null || b64.length() > 6000000) return false;   // ~4 MB font
                byte[] b = Base64.decode(b64, Base64.DEFAULT);
                FileOutputStream out = new FileOutputStream(fontFile(rw));
                out.write(b);
                out.close();
                return true;
            } catch (Exception e) { return false; }
        }
        @JavascriptInterface public void deleteFont(String rw) { fontFile(rw).delete(); }

        @JavascriptInterface public String getSetting(String key) {
            return getSharedPreferences("settings", Context.MODE_PRIVATE).getString(key, "");
        }
        @JavascriptInterface public void setSetting(String key, String value) {
            getSharedPreferences("settings", Context.MODE_PRIVATE).edit().putString(key, value).apply();
        }
        @JavascriptInterface public void keepScreenOn(final boolean on) {
            runOnUiThread(new Runnable() {
                public void run() {
                    if (on) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
            });
        }
    }

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        data = new MushafDb(this);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);     
        s.setAllowFileAccess(false);       // file system only; file:///android_asset/ keeps working
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setAllowContentAccess(false);
        s.setSupportZoom(false);
        s.setSupportMultipleWindows(false);
        s.setGeolocationEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setWebViewClient(new WebViewClient() {
            // the page never navigates away: block everything except our own index.html (reload included)
            @Override public boolean shouldOverrideUrlLoading(WebView w, String url) { return !INDEX.equals(url); }
            // no network at all, even if some page tried
            @Override public WebResourceResponse shouldInterceptRequest(WebView w, String url) {
                if (url != null && (url.startsWith("http:") || url.startsWith("https:") || url.startsWith("ftp:")))
                    return new WebResourceResponse("text/plain", "utf-8", new ByteArrayInputStream(new byte[0]));
                return null;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {   // lets <input type=file> open the system picker
            @Override public boolean onShowFileChooser(WebView w, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = cb;
                try {
                    Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                    i.addCategory(Intent.CATEGORY_OPENABLE);
                    i.setType("*/*");
                    startActivityForResult(Intent.createChooser(i, null), REQ_FILE);
                } catch (Exception e) { chooser = null; return false; }
                return true;
            }
        });
        web.addJavascriptInterface(new Bridge(), "Android");
        setContentView(web);
        web.loadUrl(INDEX);   // the page restores the position itself
    }

    @SuppressWarnings("deprecation")
    private void applyFullscreen(boolean on) {
        full = on;
        getWindow().getDecorView().setSystemUiVisibility(on
                ? View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                  | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                  | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                : View.SYSTEM_UI_FLAG_VISIBLE);
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus && full) applyFullscreen(true);   // immersive mode is lost when focus changes
    }

    @Override protected void onPause() {
        web.evaluateJavascript("window.__pause&&window.__pause()", null);  // stop scrolling + save position
        web.onPause();
        super.onPause();
    }

    @Override protected void onActivityResult(int req, int res, Intent d) {
        if (req == REQ_FILE) {
            if (chooser != null) {
                Uri[] r = (res == RESULT_OK && d != null && d.getData() != null) ? new Uri[]{d.getData()} : null;
                chooser.onReceiveValue(r);
                chooser = null;
            }
            return;
        }
        super.onActivityResult(req, res, d);
    }

    @Override protected void onResume() { super.onResume(); web.onResume(); }

    @Override public void onBackPressed() {
        web.evaluateJavascript("window.__back?window.__back():false", new ValueCallback<String>() {
            public void onReceiveValue(String r) { if (!"true".equals(r)) finish(); }
        });
    }

    @Override protected void onDestroy() {
        web.removeJavascriptInterface("Android");
        web.destroy();
        data.close();
        super.onDestroy();
    }
}
