#!/usr/bin/env python3
"""Adds hizb / rub / thumn positions to the DB.
CSV (UTF-8, no header):  kind,label,sura,aya     kind = hizb | rub | thumn
e.g.  hizb,الحزب 2,2,142
Usage: python3 import_marks.py marks.csv app/src/main/assets/mushaf.db [riwaya]   (then raise DB_VERSION)"""
import csv, sqlite3, sys
src, dbp = sys.argv[1:3]; rw = sys.argv[3] if len(sys.argv) > 3 else 'qalon'
db = sqlite3.connect(dbp); n = {}
for kind, label, su, ay in csv.reader(open(src, encoding='utf-8')):
    r = db.execute("SELECT page FROM verses WHERE riwaya=? AND sura=? AND aya=?", (rw, int(su), int(ay))).fetchone()
    if not r: sys.exit(f'verse not found: {su}:{ay}')
    n[kind] = n.get(kind, 0) + 1
    db.execute("INSERT OR REPLACE INTO marks VALUES(?,?,?,?,?,?,?)", (rw, kind, n[kind], label, int(su), int(ay), r[0]))
db.commit(); print(n)
