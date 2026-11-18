#!/usr/bin/env python3
"""Builds app/src/main/assets/mushaf.db from
   1) quran_multi_riwaya.db  : verse texts of 8 riwayat + surah names
   2) mushaf-qalon-*.html    : page layout of the Tunisian Qalon edition (604 pages)
   3) meta_lists.py          : juz / hizb / rub' / thumn / sajda positions (quran-meta, MIT)
Usage: python3 build_db.py mushaf-qalon-4.html quran_multi_riwaya.db out.db"""
import re, json, sqlite3, sys, os, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lists as M

html_path, multi_path, out = sys.argv[1:4]
X = json.loads(re.search(r'<script id="d" type="application/json">(.*?)</script>', open(html_path, encoding='utf-8').read(), re.S).group(1))
src = sqlite3.connect(multi_path)
ORD = ['الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس', 'السابع', 'الثامن']
BS_QALON = 'بِسْمِ اِ۬للَّهِ اِ۬لرَّحْمَٰنِ اِ۬لرَّحِيمِ'
clean = lambda t: t.replace('\u200f', '')

def verses(t):  # [(sura, aya, text)] ordered; AyahId = index + 1
    return [(s, a, clean(x)) for s, a, x in src.execute(f"SELECT sura, aya, text FROM verses_{t} ORDER BY sura, aya")]

# ---- layouts: list of page-start AyahIds ----
qv = verses('qalun'); qid = {(s, a): i + 1 for i, (s, a, _) in enumerate(qv)}
cur = None; QALON_STARTS = []
for pi, page in enumerate(X['p']):
    s0 = None
    for v in page:
        if v[1] == 1 and len(v) > 2: cur = v[2] + 1
        if s0 is None: s0 = (cur, v[1]); QALON_STARTS.append(qid[s0])
assert len(QALON_STARTS) == 604 and QALON_STARTS == sorted(QALON_STARTS)

CFG = {  # id: (layout starts or None, bfat, basmala source, marks, note)
 'qalun':        (QALON_STARTS, 0, None, 'qalun', 'صفحات المصحف التونسي · الأحزاب والأثمان والسجدات'),
 'warsh':        (QALON_STARTS, 0, None, None,    'صفحات المصحف (نفس تقسيم قالون)'),
 'hafs_uthmani': (M.HAFS_PAGE,  1, 'own', 'hafs',  'صفحات المدينة · الأحزاب والسجدات'),
 'shubah':       (None,         1, 'own', 'hafs',  'عرض بالسور · الأحزاب والسجدات'),
 'duri':         (None,         0, 'qpc', None,    'عرض بالسور'),
 'susi':         (None,         0, 'qpc', None,    'عرض بالسور'),
}
if os.path.exists(out): os.remove(out)
db = sqlite3.connect(out)
db.executescript("""
CREATE TABLE riwaya(id TEXT PRIMARY KEY, name TEXT NOT NULL, note TEXT, mode TEXT NOT NULL, pages INTEGER NOT NULL, basmala TEXT NOT NULL, bfat INTEGER NOT NULL, source TEXT) WITHOUT ROWID;
CREATE TABLE verses(riwaya TEXT NOT NULL, sura INTEGER NOT NULL, aya INTEGER NOT NULL, text TEXT NOT NULL, page INTEGER NOT NULL, pos INTEGER NOT NULL, PRIMARY KEY(riwaya, sura, aya)) WITHOUT ROWID;
CREATE INDEX idx_verses_page ON verses(riwaya, page, pos);
CREATE TABLE surahs(riwaya TEXT NOT NULL, sura INTEGER NOT NULL, name TEXT NOT NULL, start_page INTEGER NOT NULL, PRIMARY KEY(riwaya, sura)) WITHOUT ROWID;
CREATE TABLE page_surah(riwaya TEXT NOT NULL, page INTEGER NOT NULL, sura INTEGER NOT NULL, PRIMARY KEY(riwaya, page)) WITHOUT ROWID;
CREATE TABLE about(idx INTEGER PRIMARY KEY, grp TEXT NOT NULL, title TEXT NOT NULL, source TEXT NOT NULL, links TEXT NOT NULL);
CREATE TABLE marks(riwaya TEXT NOT NULL, kind TEXT NOT NULL, idx INTEGER NOT NULL, label TEXT NOT NULL, sura INTEGER NOT NULL, aya INTEGER NOT NULL, page INTEGER NOT NULL, PRIMARY KEY(riwaya, kind, idx)) WITHOUT ROWID;
""")
names = dict(src.execute("SELECT sura, name_ar FROM surahs"))
assert sum(names[i + 1] != X['nm'][i] for i in range(114)) <= 8, "surah names differ too much from the html"  # only spelling variants (ابراهيم/إبراهيم...)
info = {r[0]: r for r in src.execute("SELECT id, name_ar, source FROM riwaya")}
qpc_basmala = clean(src.execute("SELECT text FROM verses_qpc_hafs WHERE sura=1 AND aya=1").fetchone()[0])

for rid, (starts, bfat, bsrc, mk, note) in CFG.items():
    V = verses(rid); n = len(V)
    if starts and rid == 'warsh':   # same per-surah counts as qalun -> same AyahId layout
        assert [(s, a) for s, a, _ in V] == [(s, a) for s, a, _ in qv]
    if starts is not None and rid == 'hafs_uthmani': assert n == 6236
    page_of = {}; posn = {}
    for i, (s, a, t) in enumerate(V):
        pg = bisect.bisect_right(starts, i + 1) if starts else s
        posn[pg] = posn.get(pg, -1) + 1; page_of[(s, a)] = (pg, posn[pg])
        db.execute("INSERT INTO verses VALUES(?,?,?,?,?,?)", (rid, s, a, t, pg, posn[pg]))
    npg = 604 if starts else 114
    first = {}
    for (s, a), (pg, p) in sorted(page_of.items(), key=lambda kv: kv[1]):
        if p == 0: first[pg] = s
    assert sorted(first) == list(range(1, npg + 1)), rid
    for pg in range(1, npg + 1): db.execute("INSERT INTO page_surah VALUES(?,?,?)", (rid, pg, first[pg]))
    for s in range(1, 115): db.execute("INSERT INTO surahs VALUES(?,?,?,?)", (rid, s, names[s], page_of[(s, 1)][0]))
    basmala = BS_QALON if bsrc is None else (V[0][2] if bsrc == 'own' else qpc_basmala)
    db.execute("INSERT INTO riwaya VALUES(?,?,?,?,?,?,?,?)", (rid, info[rid][1], note, 'pages' if starts else 'surah', npg, basmala, bfat, info[rid][2]))
    # ---- marks ----
    if mk:
        if mk == 'qalun': thumn, rub, juz, saj = M.QALUN_EIGHTH, M.QALUN_EIGHTH[0::2], M.QALUN_JUZ, M.QALUN_SAJDA
        else:
            assert n == 6236; thumn, rub, juz, saj = None, M.HAFS_QUARTER, M.HAFS_JUZ, M.HAFS_SAJDA
        def put(kind, ids, label):
            for k, i in enumerate(ids):
                s, a, _ = V[i - 1]; db.execute("INSERT INTO marks VALUES(?,?,?,?,?,?,?)", (rid, kind, k + 1, label(k), s, a, page_of[(s, a)][0]))
        put('juz', juz, lambda k: f'الجزء {k + 1}')
        put('hizb', rub[0::4], lambda k: f'الحزب {k + 1}')
        put('rub', rub, lambda k: f'الحزب {k // 4 + 1} · الربع {ORD[k % 4]}')
        if thumn: put('thumn', thumn, lambda k: f'الحزب {k // 8 + 1} · الثمن {ORD[k % 8]}')
        put('sajda', saj, lambda k: 'سجدة')
    print(f'{rid:13s} verses {n} pages {npg} mode {"pages" if starts else "surah"}')
# ---- "about" page: source + link(s) of every riwaya (edit here, then rebuild) ----
# NOTE: the about rows are written directly into mushaf.db (v6); keep this list in sync if you rebuild.
TANZIL = ['مشروع تنزيل Tanzil', 'https://tanzil.net']; TZL = ['رخصة تنزيل (CC BY 3.0)', 'https://creativecommons.org/licenses/by/3.0/']
QJ = ['quran-json (CC BY 4.0)', 'https://github.com/risan/quran-json']; QJL = ['رخصة CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/']
QP = ['الموسوعة القرآنية Quranpedia', 'https://quranpedia.net']
ABOUT = [
 ('riwaya', 'hafs_uthmani', 'النص العثماني من مشروع تنزيل (Tanzil Project)، يُستخدم كما هو دون تعديل على حروفه، برخصة CC BY 3.0. وصل إلى التطبيق عبر مكتبة quran-json.', [TANZIL, TZL, QJ]),
 ('riwaya', 'qalun', 'نص الرواية من الموسوعة القرآنية (Quranpedia) عبر quran-json، دون تعديل على حروفه. صفحات المصحف التونسي من ملف المصحف الأصلي للتطبيق.', [QP, QJ, QJL]),
 ('riwaya', 'warsh', 'نص الرواية من الموسوعة القرآنية (Quranpedia) عبر quran-json، دون تعديل على حروفه. الصفحات بتقسيم قالون.', [QP, QJ, QJL]),
 ('riwaya', 'duri', 'نص الرواية من الموسوعة القرآنية (Quranpedia) عبر quran-json، دون تعديل على حروفه.', [QP, QJ, QJL]),
 ('riwaya', 'susi', 'نص الرواية من الموسوعة القرآنية (Quranpedia) عبر quran-json، دون تعديل على حروفه.', [QP, QJ, QJL]),
 ('riwaya', 'shubah', 'نص الرواية من الموسوعة القرآنية (Quranpedia) عبر quran-json، دون تعديل على حروفه.', [QP, QJ, QJL]),
 ('data', 'الصفحات والأجزاء والأحزاب والأثمان والسجدات', 'مكتبة quran-meta (رخصة MIT) المبنية على بيانات الموسوعة القرآنية ومجمع الملك فهد.', [['quran-meta', 'https://github.com/quran-center/quran-meta']]),
 ('data', 'الخطوط', 'خطوط مجمع الملك فهد لطباعة المصحف الشريف لكل رواية، وهي مضمّنة كما هي دون تعديل، وحقوقها محفوظة للمجمع. وخط Scheherazade New مرخّص برخصة SIL Open Font License 1.1 (© SIL International).', [['مجمع الملك فهد لطباعة المصحف الشريف', 'https://qurancomplex.gov.sa'], ['خطوط المجمع', 'https://fonts.qurancomplex.gov.sa'], ['Scheherazade New', 'https://software.sil.org/scheherazade/'], ['رخصة SIL OFL 1.1', 'https://openfontlicense.org']]),
 ('data', 'حول النصوص والتلوين', 'لا يعدّل التطبيق حروف أي نص. تلوين أحكام التجويد والبحث وعلامات الأحزاب تُحسب وقت العرض فقط ولا تغيّر النص المخزّن. التطبيق مجاني، يعمل دون إنترنت، ولا يجمع أي بيانات.', []),
]
names_ar = {r[0]: r[1] for r in db.execute("SELECT id, name FROM riwaya")}
for i, (grp, title, source, links) in enumerate(ABOUT):
    db.execute("INSERT INTO about VALUES(?,?,?,?,?)", (i, grp, names_ar.get(title, title), source, json.dumps(links, ensure_ascii=False)))
db.commit(); db.execute("VACUUM"); db.close()
print('->', out, os.path.getsize(out) // 1024, 'KB')
