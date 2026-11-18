#!/usr/bin/env python3
"""Runs the SAME SQL as MushafDb.java, checks the data, and dumps /tmp/bridge.json for the browser test.
Usage: test_queries.py old_mushaf.html mushaf.db"""
import re, json, sqlite3, sys
html, db_path = sys.argv[1:3]
X = json.loads(re.search(r'<script id="d" type="application/json">(.*?)</script>', open(html, encoding='utf-8').read(), re.S).group(1))
db = sqlite3.connect(db_path); J = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))

def riwayat(): return [list(r) for r in db.execute("SELECT id, name, note, mode FROM riwaya ORDER BY CASE id WHEN 'qalun' THEN 0 WHEN 'warsh' THEN 1 WHEN 'hafs_uthmani' THEN 2 ELSE 3 END, name")]
def page(rw, p):
    out = []
    for text, aya, sura in db.execute("SELECT text, aya, sura FROM verses WHERE riwaya=? AND page=? ORDER BY pos", (rw, str(p))):
        v = [text, aya]
        if aya == 1: v.append(sura - 1)
        out.append(v)
    return J(out)
def meta(rw):
    md, bs, bf = db.execute("SELECT mode, basmala, bfat FROM riwaya WHERE id=?", (rw,)).fetchone()
    nm, sp = [], []
    for n, s in db.execute("SELECT name, start_page-1 FROM surahs WHERE riwaya=? ORDER BY sura", (rw,)): nm.append(n); sp.append(s)
    ps = [r[0] for r in db.execute("SELECT sura-1 FROM page_surah WHERE riwaya=? ORDER BY page", (rw,))]
    ac = [r[0] for r in db.execute("SELECT count(*) FROM verses WHERE riwaya=? GROUP BY sura ORDER BY sura", (rw,))]
    mk = {}
    for k, l, su, ay, pg in db.execute("SELECT kind, label, sura-1, aya, page-1 FROM marks WHERE riwaya=? ORDER BY kind, idx", (rw,)): mk.setdefault(k, []).append([l, su, ay, pg])
    return J({"md": md, "bs": bs, "bf": bf == 1, "np": len(ps), "nm": nm, "sp": sp, "ps": ps, "ac": ac, "mk": mk})
def find_page(rw, s, a):
    r = db.execute("SELECT page FROM verses WHERE riwaya=? AND sura=? AND aya<=? ORDER BY aya DESC LIMIT 1", (rw, s, a)).fetchone(); return r[0] if r else 0

# 1) the Qalun layout equals the old embedded Tunisian data (text modulo the invisible RLM mark)
bad = [k for k in range(604) if [[x[0].replace('\u200f', '') for x in [v]][0] if False else v for v in json.loads(page('qalun', k + 1))] and
       [[v[0].replace('\u200f', ''), *v[1:]] for v in json.loads(page('qalun', k + 1))] != X['p'][k]]
assert not bad, f"qalun pages differ: {bad[:10]}"
print("OK  qalun: 604 pages identical to the old Tunisian layout")
out = {"riwayat": riwayat(), "rw": {}, "vp": {}, "about": [[g, t, so, json.loads(l)] for g, t, so, l in db.execute("SELECT grp, title, source, links FROM about ORDER BY idx")]}
total = {}
for rw, name, note, mode in riwayat():
    m = json.loads(meta(rw)); np_ = m['np']
    pages = [page(rw, p + 1) for p in range(np_)]
    n = sum(len(json.loads(p)) for p in pages); tv = db.execute("SELECT count(*) FROM verses WHERE riwaya=?", (rw,)).fetchone()[0]
    assert n == tv == sum(m['ac']), (rw, n, tv)                       # every verse in exactly one page
    assert all(m['ps'][k] == (json.loads(pages[k])[0][2]) for k in range(np_) if json.loads(pages[k])[0][1] == 1), rw
    cnt = {k: len(v) for k, v in m['mk'].items()}
    out['rw'][rw] = {"meta": meta(rw), "pages": pages}
    out['vp'][rw] = {f"{s}_{a}": p for s, a, p in db.execute("SELECT sura, aya, page FROM verses WHERE riwaya=?", (rw,))}
    print(f"OK  {rw:13s} {mode:5s} pages {np_:3d} verses {n}  bf={m['bf']}  marks {cnt}")
assert find_page('qalun', 2, 255) == db.execute("SELECT page FROM verses WHERE riwaya='qalun' AND sura=2 AND aya=255").fetchone()[0]
json.dump(out, open('/tmp/bridge.json', 'w', encoding='utf-8'), ensure_ascii=False)
