"""KanjiVG（日本の教科書体に近い字形・筆順）から、Hanzi Writer 用の書き順データを作る。
KanjiVG は画の中心線（ペンの通り道）だけを持つので、中心線に太さを付けて画の形（輪郭）を作る。
縦画は太く横画は細め（明朝に近い形）、はらい（㇒㇏など）は終わりを細く描く。
使い方：python3 tools/build_strokes_kvg.py <kanjivg の kanji フォルダ> <文字の一覧ファイル（1行に1字でも、つなげても可）>
出力：strokes/<コードポイント16進>.json（strokes＝輪郭、medians＝中心線の点）"""
import json, math, os, re, sys

src, listfile = sys.argv[1], sys.argv[2]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strokes")
chars = [c for c in open(listfile, encoding="utf-8").read() if not c.isspace()]

S = 1024 / 109                      # KanjiVG の 109×109 を Hanzi Writer の 1024 に
tx = lambda x, y: (x * S, 900 - y * S)   # Hanzi Writer は y が上向き（900 が上端）
W = 8.2 * S / 2                     # 画の太さの半分（縦画の太さ）
TAPER = set("㇒㇏㇀㇓㇇㇋㇢")         # 終わりを細くする画（はらい・はね上げ）

def bez(p0, p1, p2, p3, n=14):
    return [((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t*t*p2[0]+t**3*p3[0],
             (1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t*t*p2[1]+t**3*p3[1]) for t in [i/n for i in range(1, n+1)]]

def parse(d):
    toks = re.findall(r"[MmCcSsLlZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    pts, cur, start, last_c2, cmd, i = [], (0, 0), (0, 0), None, None, 0
    nums = lambda k: [float(t) for t in toks[i:i+k]]
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]): cmd = toks[i]; i += 1
        if cmd in "Mm":
            x, y = nums(2); i += 2
            cur = (cur[0]+x, cur[1]+y) if cmd == "m" and pts else (x, y); start = cur; pts.append(cur); last_c2 = None
            cmd = "l" if cmd == "m" else "L"
        elif cmd in "Cc":
            a = nums(6); i += 6
            if cmd == "c": a = [a[k] + (cur[0] if k % 2 == 0 else cur[1]) for k in range(6)]
            c1, c2, e = (a[0], a[1]), (a[2], a[3]), (a[4], a[5])
            pts += bez(cur, c1, c2, e); last_c2, cur = c2, e
        elif cmd in "Ss":
            a = nums(4); i += 4
            if cmd == "s": a = [a[k] + (cur[0] if k % 2 == 0 else cur[1]) for k in range(4)]
            c1 = (2*cur[0]-last_c2[0], 2*cur[1]-last_c2[1]) if last_c2 else cur
            c2, e = (a[0], a[1]), (a[2], a[3])
            pts += bez(cur, c1, c2, e); last_c2, cur = c2, e
        elif cmd in "Ll":
            x, y = nums(2); i += 2
            e = (cur[0]+x, cur[1]+y) if cmd == "l" else (x, y)
            pts += [(cur[0]+(e[0]-cur[0])*t/6, cur[1]+(e[1]-cur[1])*t/6) for t in range(1, 7)]; cur = e; last_c2 = None
        elif cmd in "Zz":
            pts.append(start); cur = start; i += 0; cmd = None
        else:
            i += 1
    return pts

def resample(pts, step):
    out_, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        while acc + seg >= step and seg > 0:
            t = (step - acc) / seg
            a = (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t); out_.append(a); seg = math.dist(a, b); acc = 0.0
        acc += seg
    if math.dist(out_[-1], pts[-1]) > 1e-6: out_.append(pts[-1])
    return out_

def outline(pts, kind):
    pts = resample(pts, 14)
    if len(pts) < 2: pts = [pts[0], (pts[0][0]+1, pts[0][1])]
    n = len(pts)
    taper = any(k in TAPER for k in kind)
    L, R = [], []
    for k, p in enumerate(pts):
        a, b = pts[max(k-1, 0)], pts[min(k+1, n-1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; m = math.hypot(dx, dy) or 1
        nx, ny = -dy/m, dx/m
        t = k / (n-1)
        # 明朝に近い形：縦画は太く、横画は細め。はらいは終わりを細く
        w = W * (0.45 + 0.7*abs(dy/m))
        if taper and t > 0.45: w *= max(0.15, 1 - (t-0.45)/0.55*0.85)
        L.append((p[0]+nx*w, p[1]+ny*w)); R.append((p[0]-nx*w, p[1]-ny*w))
    def cap(c, d, w):     # 半円で端を丸める
        ang = math.atan2(d[1], d[0])
        return [(c[0]+w*math.cos(ang+math.pi/2 - math.pi*j/6), c[1]+w*math.sin(ang+math.pi/2 - math.pi*j/6)) for j in range(1, 6)]
    end_w = math.dist(L[-1], R[-1]) / 2; st_w = math.dist(L[0], R[0]) / 2
    de = (pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1]); ds = (pts[0][0]-pts[1][0], pts[0][1]-pts[1][1])
    poly = L + cap(pts[-1], de, end_w) + R[::-1] + cap(pts[0], ds, st_w)
    return "M" + " L".join("%d %d" % (round(x), round(y)) for x, y in poly) + " Z"

n = 0; miss = []
for c in chars:
    f = os.path.join(src, "%05x.svg" % ord(c))
    if not os.path.exists(f): miss.append(c); continue
    svg = open(f, encoding="utf-8").read()
    strokes, medians = [], []
    for m in re.finditer(r'<path id="kvg:[0-9a-f]+-s\d+"(?: kvg:type="([^"]*)")? d="([^"]+)"', svg):
        kind, d = m.group(1) or "", m.group(2)
        pts = [tx(x, y) for x, y in parse(d)]
        strokes.append(outline(pts, kind))
        md = resample(pts, 60)
        # 最後の点がすぐ手前の点に近すぎると、判定（向きの比較）が不安定になるので、手前の点を除く
        if len(md) > 2 and math.dist(md[-1], md[-2]) < 30: del md[-2]
        medians.append([[round(x), round(y)] for x, y in md])
    with open(os.path.join(out, "%x.json" % ord(c)), "w", encoding="utf-8") as fo:
        json.dump({"strokes": strokes, "medians": medians, "src": "KanjiVG"}, fo, ensure_ascii=False, separators=(",", ":"))
    n += 1
print(n, "字", "見つからない:", "".join(miss))
