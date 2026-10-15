# -*- coding: utf-8 -*-
"""布依音曲库增删：删除非布依族曲目 + 合入 B 站新增曲目，重建 library.json"""

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("BUYI_SRC_JSON", r"C:/Users/d'm'n/Downloads/e07_布依族.json")
LIB = os.path.join(PROJECT, "src", "data", "library.json")
COVER_DIR = os.path.join(PROJECT, "src", "assets", "covers")
AUDIO_DIR = os.path.join(PROJECT, "src", "assets", "audio")

# ---------------- 删除清单 ----------------
# 说明：括号内为删除理由分类
DELETE = {}

def add(idx, reason):
    DELETE["b%d" % idx] = reason

# A. 其他民族/流行歌曲（酷我检索噪声：彝族、藏族、蒙古草原、云南等）
for i in [37, 38, 39, 40, 41, 42]:
    add(i, "A-其他民族歌手作品（彝族等），与布依族无关")
for i in range(178, 213):
    add(i, "A-草原/藏族/云南风流行歌曲，检索噪声，与布依族无关")
for i in range(223, 248):
    add(i, "A-彝族/藏族/其他民族歌曲，与布依族无关")
add(172, "A-吴碧霞《一杯美酒》，非布依族民歌")

# B. 歌手名「布依」误命中（布衣乐队≠布依族）
add(248, "B-「布衣乐队」与布依族无关（名称误命中）")
add(249, "B-歌手/曲目与布依族无关联")

# C. 吴碧霞个人民歌专辑中的非布依族曲目
for i in [104, 105, 256, 257, 258, 259, 260, 261, 262, 264, 265]:
    add(i, "C-吴碧霞民歌专辑中的其他地区民歌，非布依族")

# D. 非歌曲内容（有声书 / 语言教学 / 航拍 / 纪录片 / 抖音原声）
for i in [18, 58, 60, 294, 295, 263, 106, 107]:
    add(i, "D-非布依族音乐内容（航拍/教学/纪录片/影视歌曲/外语歌曲）")
for i in [79, 81, 83, 84, 85, 86]:
    add(i, "D-有声书/长音频/朗读类内容，非歌曲")
add(169, "D-抖音原声片段，非完整歌曲")
for i in [87, 88, 89, 90, 93]:
    add(i, "D-平台原声/随机曲目，与布依族无实质关联")

# E. 咪咕检索噪声
for i in [72, 73, 74]:
    add(i, "E-咪咕检索噪声（卡拉OK/纯音乐片段）")

# F. 微信公众号合辑中的非布依族音频
for i in [297, 298, 299, 300, 301]:
    add(i, "F-微信合辑中的非布依族轻音乐/流行曲")

# G. 无法确认与布依族关联的同名条目
add(222, "G-曲名含游戏/同人设定，与布依族无实质关联")


def fmt_dur(sec):
    if not sec:
        return "--:--"
    sec = int(sec)
    return "%02d:%02d" % (sec // 60, sec % 60)


BATIK = [("#1B3A5C", "#2E6B8F"), ("#14394F", "#3C7A6E"), ("#22314F", "#5A4B8C"),
         ("#123A4A", "#2F6F8C"), ("#2A2A48", "#6B4A72"), ("#16324B", "#486E8C")]
PATTERNS = {
    "sun": '<circle cx="150" cy="150" r="46" fill="none" stroke="{c2}" stroke-width="6"/>'
           '<circle cx="150" cy="150" r="16" fill="{c2}"/>' +
           "".join('<line x1="150" y1="84" x2="150" y2="104" stroke="{c2}" stroke-width="5" '
                   'transform="rotate(%d 150 150)"/>' % (i * 30) for i in range(12)),
    "wave": "".join('<path d="M0 %d q37.5 -26 75 0 t75 0 t75 0 t75 0" fill="none" '
                    'stroke="{c2}" stroke-width="5" opacity="0.85"/>' % (60 + i * 26)
                    for i in range(6)),
    "diamond": "".join('<rect x="%d" y="%d" width="46" height="46" fill="none" stroke="{c2}" '
                       'stroke-width="5" transform="rotate(45 %d %d)" opacity="0.9"/>'
                       % (28 + i * 72, 28 + j * 72, 28 + i * 72 + 23, 28 + j * 72 + 23)
                       for i in range(4) for j in range(4)),
    "drum": '<circle cx="150" cy="150" r="104" fill="none" stroke="{c2}" stroke-width="6"/>'
            '<circle cx="150" cy="150" r="70" fill="none" stroke="{c2}" stroke-width="4"/>'
            '<circle cx="150" cy="150" r="30" fill="{c2}"/>' +
            "".join('<circle cx="150" cy="60" r="7" fill="{c2}" transform="rotate(%d 150 150)"/>'
                    % (i * 24) for i in range(15)),
}


def gen_cover_svg(title, idx, path):
    c1, c2 = BATIK[idx % len(BATIK)]
    pat = PATTERNS[list(PATTERNS.keys())[idx % len(PATTERNS)]].format(c2=c2)
    t = (title or "布依民歌").strip()
    t = t[:10] + ("…" if len(t) > 10 else "")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
           '</linearGradient></defs>'
           f'<rect width="300" height="300" fill="url(#g)"/>'
           f'<g opacity="0.55">{pat}</g>'
           f'<rect x="0" y="212" width="300" height="88" fill="#0d1b2a" opacity="0.55"/>'
           f'<text x="150" y="256" font-family="Microsoft YaHei, sans-serif" font-size="24" '
           f'fill="#F5EFE3" text-anchor="middle">{t}</text>'
           '<text x="150" y="284" font-family="Microsoft YaHei, sans-serif" font-size="14" '
           'fill="#C9A227" text-anchor="middle" letter-spacing="4">布 依 音</text></svg>')
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def classify(title, album=""):
    text = (title or "") + " " + (album or "")
    rules = [
        ("器乐", ["勒尤", "木叶", "唢呐", "铜鼓", "月琴", "二胡", "芦笙", "笛", "箫", "古筝",
                  "琵琶", "独奏", "演奏", "器乐", "伴奏", "纯音乐", "BGM", "钢琴", "吉他",
                  "民乐", "合奏", "八音", "笔管", "勒浪", "姊妹箫"]),
        ("童谣", ["儿歌", "童谣", "摇篮曲", "宝宝", "儿童", "早教", "幼儿", "小朋友", "亲子", "益智"]),
        ("婚俗酒歌", ["酒歌", "婚", "嫁", "迎亲", "接亲", "喜", "祝酒", "拦门", "敬酒", "留客",
                      "赶表", "浪哨", "讨八字"]),
        ("劳动生活", ["织布", "织锦", "纺织", "挑花", "蜡染", "枫香染", "耕作", "插秧", "打谷",
                      "采茶", "砍柴", "放牛", "赶集", "刺绣", "栽秧", "薅秧", "田间", "劳动", "农"]),
        ("舞蹈", ["舞蹈", "舞", "糠包", "竹竿", "花头帕", "踏歌"]),
        ("新创改编", ["Prod", "remix", "Remix", "DJ", "dj", "改编", "新编", "原创", "rap",
                      "Rap", "说唱", "流行", "cover", "Cover", "翻唱", "摇滚", "爵士", "古琴"]),
    ]
    for name, kws in rules:
        for k in kws:
            if k in text:
                return name
    return "山歌民谣"


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    tracks = lib["tracks"]
    before = len(tracks)

    # 0. 幂等：先移除上一轮新增的 n* 条目（便于重复执行）
    tracks = [t for t in tracks if not str(t["id"]).startswith("n")]

    # 0.1 为 B 站条目补回 bvid（供应用运行时重新解析过期音源）
    try:
        orig = json.load(io.open(SRC, encoding="utf-8"))["tracks"]
        for t in tracks:
            if t["source"] != "B站":
                continue
            m = re.match(r"b(\d+)$", str(t["id"]))
            if not m:
                continue
            i = int(m.group(1))
            if i < len(orig):
                alb = str(orig[i].get("album") or "")
                if re.match(r"^BV[0-9A-Za-z]{10}$", alb):
                    t["bvid"] = alb
    except Exception as e:
        print("[warn] 补 bvid 失败:", e)

    # 1. 删除
    removed = [t for t in tracks if t["id"] in DELETE]
    kept = [t for t in tracks if t["id"] not in DELETE]
    print("删除 %d 首，保留 %d 首" % (len(removed), len(kept)))

    # 清理被删除曲目的封面与随包音频
    for t in removed:
        m = re.match(r"b(\d+)$", t["id"])
        if m:
            n = m.group(1)
            for ext in (".jpg", ".svg"):
                p = os.path.join(COVER_DIR, "c%s%s" % (n, ext))
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
        for f in os.listdir(AUDIO_DIR):
            if f.startswith(t["id"] + "."):
                try:
                    os.remove(os.path.join(AUDIO_DIR, f))
                except Exception:
                    pass

    # 2. 新增（B 站解析结果，由 add_new_songs.py 生成）
    new_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "new_songs.json"))
    added = []
    if os.path.exists(new_file):
        added += json.load(io.open(new_file, encoding="utf-8"))
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extra_songs.json")):
        for e in json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extra_songs.json"), encoding="utf-8")):
            e.setdefault("author", e.get("artist", ""))
            e.setdefault("bvid", "")
            e.setdefault("cover", "")
            e.setdefault("album", "布依族民歌")
            added.append(e)
    print("新增 %d 首" % len(added))

    start_idx = 1000
    for k, item in enumerate(added):
        tid = "n%d" % (start_idx + k)
        cover = item.get("cover")
        if cover:
            cp = os.path.join(COVER_DIR, "%s.jpg" % tid)
            if os.path.exists(cp) and os.path.getsize(cp) > 2000:
                cover = "assets/covers/%s.jpg" % tid
            else:
                gen_cover_svg(item["title"], k, os.path.join(COVER_DIR, "%s.svg" % tid))
                cover = "assets/covers/%s.svg" % tid
        else:
            gen_cover_svg(item["title"], k, os.path.join(COVER_DIR, "%s.svg" % tid))
            cover = "assets/covers/%s.svg" % tid
        dur = item.get("duration") or 0
        added[k] = {
            "id": tid,
            "title": item["title"],
            "artist": item.get("author") or "布依族民间歌手",
            "album": item.get("album") or "B站 · 布依族音乐",
            "duration": int(dur),
            "durationText": fmt_dur(dur),
            "cover": cover,
            "source": (item.get("source") or "B站").replace("音乐", "") if item.get("source", "").startswith("咪咕") else (item.get("source") or "B站"),
            "playable": bool(item.get("url")),
            "url": item.get("url") or "",
            "refresh": None,
            "category": classify(item["title"], ""),
            "bvid": item.get("bvid", ""),
        }

    # 统一用最新分类规则重新归类（新增了「舞蹈」等类目）
    for t in kept:
        t["category"] = classify(t["title"], t.get("album", ""))

    final = kept + added
    for t in final:
        t.pop("cached", None)

    lib["meta"]["total"] = len(final)
    lib["meta"]["available"] = sum(1 for t in final if t.get("playable"))
    lib["meta"]["removed"] = len(removed)
    lib["meta"]["added"] = len(added)
    lib["tracks"] = final

    with io.open(LIB, "w", encoding="utf-8") as f:
        f.write(json.dumps(lib, ensure_ascii=False))

    # 导出报告所需数据
    report = {
        "before": before,
        "removed": [{"id": t["id"], "title": t["title"], "artist": t["artist"],
                     "source": t["source"], "reason": DELETE[t["id"]]} for t in removed],
        "added": [{"id": t["id"], "title": t["title"], "artist": t["artist"],
                   "source": t["source"], "duration": t["durationText"],
                   "playable": t["playable"], "bvid": t.get("bvid", "")} for t in added],
        "after": len(final),
        "available": lib["meta"]["available"],
    }
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "change_log.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=1))
    print("完成：%d -> 删除 %d -> 新增 %d -> 最终 %d（可播放 %d）"
          % (before, len(removed), len(added), len(final), lib["meta"]["available"]))


if __name__ == "__main__":
    main()
