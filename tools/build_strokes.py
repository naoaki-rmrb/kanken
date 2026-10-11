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
for line in open(os.path.join(src, "graphicsJaKana.txt"), encoding="utf-8"):
    g = json.loads(line)
    with open(os.path.join(out, "%x.json" % ord(g["character"])), "w", encoding="utf-8") as f:
        json.dump({"strokes": g["strokes"], "medians": g["medians"]}, f, ensure_ascii=False, separators=(",", ":"))
    n += 1
print(n, "字")
