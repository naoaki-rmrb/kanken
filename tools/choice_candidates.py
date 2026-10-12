"""書き取り4択のひっかけ候補を集める（候補を出すだけ。どれを使うかは人が選ぶ）。
使い方：python3 tools/choice_candidates.py <kanji.json> <animCJK dictionaryJa.txt> <questions.json> > candidates.json
  kanji.json … davidluzgouveia/kanji-data（KANJIDIC 由来の読み）
  questions.json … [{id, a, r}]（a＝正解の漢字、r＝読み（カタカナ））
出力：問題ごとに、正解を1字ずつに区切った読みと、
  same … 同じ読みの常用漢字（その字と入れかえる候補）
  shape … 部品が同じ・形が似ている常用漢字"""
import json, sys

kd = json.load(open(sys.argv[1], encoding="utf-8"))
dic = {}
for line in open(sys.argv[2], encoding="utf-8"):
    d = json.loads(line); dic[d["character"]] = d
JOYO = {c for c, d in dic.items() if set(d["set"]) & {"g1","g2","g3","g4","g5","g6","g7"}}
qs = json.load(open(sys.argv[3], encoding="utf-8"))

kata2hira = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)
VOICE = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
VOICE.update(zip("はひふへほ", "ぱぴぷぺぽ"))

def readings(c):
    d = kd.get(c, {})
    out = set()
    for r in d.get("readings_on", []) + d.get("readings_kun", []):
        r = r.replace("-", "").split(".")[0]
        if not r: continue
        out.add(r)
        if r[0] in VOICE: out.add(VOICE[r[0]] + r[1:])
        if r[-1] in "つくちき": out.add(r[:-1] + "っ")
    return out

def split(a, r):
    """正解の漢字列 a と読み r を1字ずつ対応させる"""
    if not a: return [] if not r else None
    c = a[0]
    if not ("一" <= c <= "龥"):
        return [(c, c)] + split(a[1:], r[1:]) if r[:1] == c else None
    for rd in sorted(readings(c), key=len, reverse=True):
        if r.startswith(rd):
            rest = split(a[1:], r[len(rd):])
            if rest is not None: return [(c, rd)] + rest
    return None

by_read = {}
for c in JOYO:
    for rd in readings(c): by_read.setdefault(rd, set()).add(c)

def parts(c):
    dec = dic.get(c, {}).get("decomposition", "")
    return {p for p in dec if p not in "⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻？" and p != c}

part_index = {}
for c in JOYO:
    for p in parts(c): part_index.setdefault(p, set()).add(c)

out = []
for q in qs:
    r = kata2hira(q["r"])
    seg = split(q["a"], r)
    row = {"id": q["id"], "a": q["a"], "r": q["r"], "seg": seg, "pos": []}
    for i, ch in enumerate(q["a"]):
        if not ("一" <= ch <= "龥"): continue
        rd = seg[i][1] if seg else None
        same = sorted((by_read.get(rd, set()) - {ch}), key=lambda x: kd.get(x, {}).get("freq") or 9999)[:15] if rd else []
        shape = set()
        for p in parts(ch): shape |= part_index.get(p, set())
        shape = sorted(shape - {ch}, key=lambda x: kd.get(x, {}).get("freq") or 9999)[:12]
        row["pos"].append({"i": i, "ch": ch, "read": rd, "same": "".join(same), "shape": "".join(shape)})
    out.append(row)
json.dump(out, sys.stdout, ensure_ascii=False, indent=0)
