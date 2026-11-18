package app.mushaf.arabi;

import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** Read-only access to assets/mushaf.db (same SQL as tools/test_queries.py). */
public class MushafDb {
    static final String DB_NAME = "mushaf.db";
    /** bump when assets/mushaf.db changes so it is copied again on update */
    static final int DB_VERSION = 6;

    private final Context ctx;
    private SQLiteDatabase db;

    MushafDb(Context c) { ctx = c.getApplicationContext(); }

    private synchronized SQLiteDatabase db() throws Exception {
        if (db != null) return db;
        File f = ctx.getDatabasePath(DB_NAME);
        SharedPreferences p = ctx.getSharedPreferences("app", Context.MODE_PRIVATE);
        if (!f.exists() || p.getInt("dbv", 0) != DB_VERSION) {
            if (f.getParentFile() != null) f.getParentFile().mkdirs();
            File tmp = new File(f.getPath() + ".tmp");     // copy to a temp file, then rename: a killed copy never leaves a half database
            InputStream in = null;
            OutputStream out = null;
            try {
                in = ctx.getAssets().open(DB_NAME);
                out = new FileOutputStream(tmp);
                byte[] buf = new byte[65536];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            } finally {
                try { if (out != null) out.close(); } catch (Exception e) { /* ignore */ }
                try { if (in != null) in.close(); } catch (Exception e) { /* ignore */ }
            }
            if (f.exists()) f.delete();
            if (!tmp.renameTo(f)) throw new java.io.IOException("cannot install database");
            p.edit().putInt("dbv", DB_VERSION).apply();
        }
        // NO_LOCALIZED_COLLATORS: no ICU collators are created -> less RAM/CPU at open
        db = SQLiteDatabase.openDatabase(f.getPath(), null, SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        return db;
    }

    synchronized void close() { if (db != null) { db.close(); db = null; } }

    /** [[text, aya, suraIndex0 (only when aya==1)], ...] */
    String page(String riwaya, int page) {
        JSONArray out = new JSONArray();
        Cursor c = null;
        try {
            c = db().rawQuery("SELECT text, aya, sura FROM verses WHERE riwaya=? AND page=? ORDER BY pos",
                    new String[]{riwaya, String.valueOf(page)});
            while (c.moveToNext()) {
                JSONArray v = new JSONArray();
                v.put(c.getString(0)); v.put(c.getInt(1));
                if (c.getInt(1) == 1) v.put(c.getInt(2) - 1);
                out.put(v);
            }
        } catch (Exception e) { /* empty page */ } finally { if (c != null) c.close(); }
        return out.toString();
    }

    /** [[id, name, note, mode], ...] */
    String riwayat() {
        JSONArray out = new JSONArray();
        Cursor c = null;
        try {
            c = db().rawQuery("SELECT id, name, note, mode FROM riwaya ORDER BY CASE id WHEN 'qalun' THEN 0 WHEN 'warsh' THEN 1 WHEN 'hafs_uthmani' THEN 2 ELSE 3 END, name", null);
            while (c.moveToNext()) {
                JSONArray r = new JSONArray();
                r.put(c.getString(0)); r.put(c.getString(1));
                r.put(c.isNull(2) ? "" : c.getString(2)); r.put(c.getString(3));
                out.put(r);
            }
        } catch (Exception e) { /* empty */ } finally { if (c != null) c.close(); }
        return out.toString();
    }

    /** [[group, title, source, [[label, url], ...]], ...] */
    String about() {
        JSONArray out = new JSONArray();
        Cursor c = null;
        try {
            c = db().rawQuery("SELECT grp, title, source, links FROM about ORDER BY idx", null);
            while (c.moveToNext()) {
                JSONArray r = new JSONArray();
                r.put(c.getString(0)); r.put(c.getString(1)); r.put(c.getString(2));
                r.put(new JSONArray(c.getString(3)));
                out.put(r);
            }
        } catch (Exception e) { /* empty */ } finally { if (c != null) c.close(); }
        return out.toString();
    }

    /** 1-based page that holds (sura, aya); if aya does not exist the last aya of the sura is used; 0 if none */
    int findPage(String riwaya, int sura, int aya) {
        Cursor c = null;
        try {
            c = db().rawQuery("SELECT page FROM verses WHERE riwaya=? AND sura=? AND aya<=? ORDER BY aya DESC LIMIT 1",
                    new String[]{riwaya, String.valueOf(sura), String.valueOf(aya)});
            if (c.moveToFirst()) return c.getInt(0);
        } catch (Exception e) { /* 0 */ } finally { if (c != null) c.close(); }
        return 0;
    }

    /** Arabic letters only (no diacritics), hamza/alef forms folded, every alef dropped, ة->ه, ى->ي. */
    static String norm(String s) {
        StringBuilder b = new StringBuilder(s.length());
        boolean sp = false;
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '\u0623' || ch == '\u0625' || ch == '\u0622' || ch == '\u0671') ch = '\u0627';
            else if (ch == '\u0649') ch = '\u064A';
            else if (ch == '\u0629') ch = '\u0647';
            else if (ch == '\u0624') ch = '\u0648';
            else if (ch == '\u0626') ch = '\u064A';
            if (ch == '\u0627') continue;
            if ((ch >= '\u0621' && ch <= '\u063A') || (ch >= '\u0641' && ch <= '\u064A')) {
                if (sp && b.length() > 0) b.append(' ');
                sp = false; b.append(ch);
            } else if (ch == ' ') sp = true;
        }
        return b.toString();
    }

    /** [[sura, aya, page, text], ...] first 60 verses (in order) whose normalised text contains the normalised phrase.
     *  Normalisation is done here, so the database file needs no extra column. Runs only when the user presses Search. */
    String search(String riwaya, String q) {
        JSONArray out = new JSONArray();
        String n = norm(q == null ? "" : q);
        if (n.length() < 2) return out.toString();
        Cursor c = null;
        try {
            c = db().rawQuery("SELECT sura, aya, page, text FROM verses WHERE riwaya=? ORDER BY sura, aya", new String[]{riwaya});
            int hits = 0;
            while (hits < 60 && c.moveToNext()) {
                String t = c.getString(3);
                if (norm(t).indexOf(n) >= 0) {
                    JSONArray r = new JSONArray();
                    r.put(c.getInt(0)); r.put(c.getInt(1)); r.put(c.getInt(2)); r.put(t);
                    out.put(r);
                    hits++;
                }
            }
        } catch (Exception e) { /* empty */ } finally { if (c != null) c.close(); }
        return out.toString();
    }

    /** {np, md, bs, bf, nm, sp, ps, ac, mk:{kind:[[label, sura0, aya, page0],...]}} */
    String meta(String riwaya) {
        JSONObject o = new JSONObject();
        JSONArray nm = new JSONArray(), sp = new JSONArray(), ps = new JSONArray(), ac = new JSONArray();
        JSONObject mk = new JSONObject();
        String[] a = {riwaya};
        try {
            SQLiteDatabase d = db();
            Cursor c = d.rawQuery("SELECT mode, basmala, bfat FROM riwaya WHERE id=?", a);
            if (c.moveToFirst()) { o.put("md", c.getString(0)); o.put("bs", c.getString(1)); o.put("bf", c.getInt(2) == 1); }
            c.close();
            c = d.rawQuery("SELECT name, start_page-1 FROM surahs WHERE riwaya=? ORDER BY sura", a);
            while (c.moveToNext()) { nm.put(c.getString(0)); sp.put(c.getInt(1)); }
            c.close();
            c = d.rawQuery("SELECT sura-1 FROM page_surah WHERE riwaya=? ORDER BY page", a);
            while (c.moveToNext()) ps.put(c.getInt(0));
            c.close();
            c = d.rawQuery("SELECT count(*) FROM verses WHERE riwaya=? GROUP BY sura ORDER BY sura", a);
            while (c.moveToNext()) ac.put(c.getInt(0));
            c.close();
            c = d.rawQuery("SELECT kind, label, sura-1, aya, page-1 FROM marks WHERE riwaya=? ORDER BY kind, idx", a);
            while (c.moveToNext()) {
                String k = c.getString(0);
                JSONArray list = mk.optJSONArray(k);
                if (list == null) { list = new JSONArray(); mk.put(k, list); }
                JSONArray m = new JSONArray();
                m.put(c.getString(1)); m.put(c.getInt(2)); m.put(c.getInt(3)); m.put(c.getInt(4));
                list.put(m);
            }
            c.close();
            o.put("np", ps.length()); o.put("nm", nm); o.put("sp", sp);
            o.put("ps", ps); o.put("ac", ac); o.put("mk", mk);
        } catch (Exception e) { /* returns what we have */ }
        return o.toString();
    }
}
