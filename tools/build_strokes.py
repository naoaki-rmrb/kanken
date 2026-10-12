"""animCJK の日本語データ（graphicsJa.txt / dictionaryJa.txt）から、常用漢字（とひらがな・カタカナ。送りがなを手書きするため）の筆順データを
strokes/<コードポイント16進>.json に書き出す（Hanzi Writer の形式：strokes・medians）。
使い方：python3 tools/build_strokes.py <animCJK のフォルダ>"""
import json, os, sys
src = sys.argv[1]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strokes")
os.makedirs(out, exist_ok=True)
JOYO = {"g1", "g2", "g3", "g4", "g5", "g6", "g7"}
dic = {d["character"]: d for d in map(json.loads, open(os.path.join(src, "dictionaryJa.txt"), encoding="utf-8"))}
n = 0
for line in open(os.path.join(src, "graphicsJa.txt"), encoding="utf-8"):
    g = json.loads(line)
    c = g["character"]
    if c not in dic or not (JOYO & set(dic[c]["set"])):
        continue
    with open(os.path.join(out, "%x.json" % ord(c)), "w", encoding="utf-8") as f:
        json.dump({"strokes": g["strokes"], "medians": g["medians"]}, f, ensure_ascii=False, separators=(",", ":"))
    n += 1
# ひらがな・カタカナ（送りがなの手書き用）
# animCJK のかなは、輪の部分（る・み・ぬ・な・は・ま・お・む・よ・め・ほ など）が別の画になっていて、
# なぞる道筋（medians）が字のわくの外（y が -400 以下など）に置かれている。日本の書き方では輪も同じ画なので、
# 輪の形を直前の画にまとめ、その画は消す（る＝1画、み＝2画、ぬ＝2画…になる）
def merge_loops(g):
    strokes, medians = [], []
    for st, md in zip(g["strokes"], g["medians"]):
        off = any(x < -250 or y < -250 or x > 1250 or y > 1250 for x, y in md)
        if off and strokes:
            strokes[-1] = strokes[-1] + " " + st
        else:
            strokes.append(st); medians.append(md)
    g["strokes"], g["medians"] = strokes, medians
    return g
for line in open(os.path.join(src, "graphicsJaKana.txt"), encoding="utf-8"):
    g = merge_loops(json.loads(line))
    with open(os.path.join(out, "%x.json" % ord(g["character"])), "w", encoding="utf-8") as f:
        json.dump({"strokes": g["strokes"], "medians": g["medians"]}, f, ensure_ascii=False, separators=(",", ":"))
    n += 1
print(n, "字")
