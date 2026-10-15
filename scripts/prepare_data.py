# -*- coding: utf-8 -*-
"""
布依族曲库导入脚本
- 读取原始 e07_布依族.json
- 重新解析失效音源（B 站按 BV 号重新取流）
- 下载封面 / 生成蜡染风格占位封面
- 输出 src/data/library.json 供应用使用
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:/Users/d'm'n/Downloads/e07_布依族.json"
OUT_DATA = os.path.join(ROOT, "src", "data")
OUT_COVER = os.path.join(ROOT, "src", "assets", "covers")
os.makedirs(OUT_DATA, exist_ok=True)
os.makedirs(OUT_COVER, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def http_get(url, headers=None, timeout=25):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)


def http_json(url, headers=None, timeout=25):
    return json.loads(http_get(url, headers, timeout).read().decode("utf-8", "ignore"))


# ---------------- Bilibili 音源重解析 ----------------
BILI_HEADERS = {"Referer": "https://www.bilibili.com/"}


def bili_buvid():
    try:
        j = http_json("https://api.bilibili.com/x/frontend/finger/spi", BILI_HEADERS, 20)
        return j["data"]["b_3"]
    except Exception as e:
        print("[warn] buvid 获取失败:", e)
        return ""


def bili_resolve_cid(bvid, cid, cookie):
    """已知 cid 时只请求 playurl —— 请求量减半，降低 -352 风控概率"""
    for attempt in range(3):
        try:
            p = http_json(
                f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=16"
                f"&fnval=16&fourk=1&otype=json",
                dict(BILI_HEADERS, Cookie=f"buvid3={cookie}"), 20)
            code = p.get("code")
            if code == 0:
                d = p["data"]
                if d.get("dash") and d["dash"].get("audio"):
                    best = max(d["dash"]["audio"], key=lambda a: a.get("bandwidth", 0))
                    return (best.get("baseUrl") or best.get("base_url")), None
                if d.get("durl"):
                    return d["durl"][0]["url"], None
                return None, None
            time.sleep(15 + attempt * 15)
        except Exception as e:
            time.sleep(8)
    return None, None


def bili_resolve(bvid, cookie):
    """返回 (audio_url, duration_s)；带重试，避免 412/-352 风控"""
    for attempt in range(2):
        try:
            v = http_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                          dict(BILI_HEADERS, Cookie=f"buvid3={cookie}"), 20)
            if v.get("code") in (412, -352, -509):
                time.sleep(20 + attempt * 20)
                continue
            if v.get("code") == 412:
                time.sleep(20 + attempt * 20)
                continue
            if v.get("code") != 0:
                return None, None
            cid = v["data"]["cid"]
            dur = v["data"].get("duration", 0)
            p = http_json(
                f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=16"
                f"&fnval=16&fourk=1&otype=json",
                dict(BILI_HEADERS, Cookie=f"buvid3={cookie}"), 20)
            if p.get("code") == 412:
                time.sleep(20 + attempt * 20)
                continue
            if p.get("code") != 0:
                return None, None
            d = p["data"]
            if d.get("dash") and d["dash"].get("audio"):
                best = max(d["dash"]["audio"], key=lambda a: a.get("bandwidth", 0))
                return best.get("baseUrl") or best.get("base_url"), dur
            if d.get("durl"):
                return d["durl"][0]["url"], dur
            return None, None
        except urllib.error.HTTPError as e:
            if e.code == 412:
                time.sleep(20 + attempt * 20)
                continue
            return None, None
        except Exception as e:
            print("  [warn] bili %s: %s" % (bvid, str(e)[:60]), flush=True)
            return None, None
    return None, None


# ---------------- 分类 ----------------
CATEGORY_RULES = [
    ("器乐", ["勒尤", "木叶", "唢呐", "铜鼓", "月琴", "二胡", "芦笙", "笛", "萧", "箫",
              "古筝", "琵琶", "独奏", "演奏", "器乐", "伴奏", "纯音乐", "BGM",
              "钢琴", "吉他", "民乐", "合奏"]),
    ("童谣", ["儿歌", "童谣", "摇篮曲", "宝宝", "儿童", "早教", "幼儿", "小朋友"]),
    ("婚俗酒歌", ["酒歌", "婚", "嫁", "迎亲", "接亲", "喜", "祝酒", "拦门", "敬酒"]),
    ("劳动生活", ["织布", "织锦", "纺织", "挑花", "蜡染", "枫香染", "耕作", "插秧",
                  "打谷", "采茶", "砍柴", "放牛", "赶集", "刺绣", "栽秧", "薅秧",
                  "田间", "劳动", "农"]),
    ("新创改编", ["Prod", "remix", "Remix", "DJ", "dj", "改编", "新编", "原创",
                  "rap", "Rap", "说唱", "流行", "版", "cover", "Cover", "翻唱"]),
]


def classify(title, album=""):
    text = (title or "") + " " + (album or "")
    for name, kws in CATEGORY_RULES:
        for k in kws:
            if k in text:
                return name
    return "山歌民谣"


def fmt_dur(sec):
    if not sec:
        return "--:--"
    sec = int(sec)
    return "%02d:%02d" % (sec // 60, sec % 60)


# ---------------- 封面 ----------------
BATIK_COLORS = [
    ("#1B3A5C", "#2E6B8F"), ("#14394F", "#3C7A6E"), ("#22314F", "#5A4B8C"),
    ("#123A4A", "#2F6F8C"), ("#2A2A48", "#6B4A72"), ("#16324B", "#486E8C"),
]
PATTERN_SVG = {
    "sun": '<circle cx="150" cy="150" r="46" fill="none" stroke="{c2}" stroke-width="6"/>'
           '<circle cx="150" cy="150" r="16" fill="{c2}"/>'
           + "".join('<line x1="150" y1="84" x2="150" y2="104" stroke="{c2}" stroke-width="5" '
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
            '<circle cx="150" cy="150" r="30" fill="{c2}"/>'
            + "".join('<circle cx="150" cy="%d" r="7" fill="{c2}" transform="rotate(%d 150 150)"/>'
                      % (60, i * 24) for i in range(15)),
}


def gen_cover_svg(title, idx):
    c1, c2 = BATIK_COLORS[idx % len(BATIK_COLORS)]
    pat_name = list(PATTERN_SVG.keys())[idx % len(PATTERN_SVG)]
    pat = PATTERN_SVG[pat_name].format(c2=c2)
    t = (title or "布依民歌").strip()
    t = t[:10] + ("…" if len(t) > 10 else "")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        '</linearGradient></defs>'
        f'<rect width="300" height="300" fill="url(#g)"/>'
        f'<g opacity="0.55">{pat}</g>'
        f'<rect x="0" y="212" width="300" height="88" fill="#0d1b2a" opacity="0.55"/>'
        f'<text x="150" y="256" font-family="Microsoft YaHei, sans-serif" font-size="24" '
        f'fill="#F5EFE3" text-anchor="middle">{t}</text>'
        '<text x="150" y="284" font-family="Microsoft YaHei, sans-serif" font-size="14" '
        'fill="#C9A227" text-anchor="middle" letter-spacing="4">布 依 音</text>'
        '</svg>'
    )


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\r\n]+', "_", s)[:60]


def download_cover(args):
    idx, url, title = args
    path = os.path.join(OUT_COVER, f"c{idx}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return f"assets/covers/c{idx}.jpg"
    sp = os.path.join(OUT_COVER, f"c{idx}.svg")
    if os.path.exists(sp):
        return f"assets/covers/c{idx}.svg"
    if url and url.startswith("http"):
        try:
            r = http_get(url, {"Referer": "https://www.bilibili.com/"}, 20)
            data = r.read()
            if len(data) > 2000:
                with open(path, "wb") as f:
                    f.write(data)
                return f"assets/covers/c{idx}.jpg"
        except Exception:
            pass
    svg = gen_cover_svg(title, idx)
    spath = os.path.join(OUT_COVER, f"c{idx}.svg")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(svg)
    return f"assets/covers/c{idx}.svg"


def main():
    raw = json.load(io.open(SRC, encoding="utf-8"))
    tracks = raw["tracks"]
    print("原始曲目:", len(tracks))

    buvid = bili_buvid()
    bili_items = [(i, x) for i, x in enumerate(tracks) if x["source"] == "Bilibili"]
    print("待重解析 B 站音源:", len(bili_items))

    cache_path = os.path.join(ROOT, "scripts", ".bili_cache.json")
    resolved = {}
    if os.path.exists(cache_path):
        try:
            resolved = {int(k): tuple(v) for k, v in
                        json.load(io.open(cache_path, encoding="utf-8")).items()}
            print("命中缓存:", len(resolved))
        except Exception:
            resolved = {}

    n = 0
    fail_streak = 0
    for i, x in bili_items:
        if i in resolved and resolved[i][0]:
            continue
        bvid = str(x.get("album") or "").strip()
        if not re.match(r"^BV[0-9A-Za-z]{10}$", bvid):
            resolved[i] = (None, None)
            continue
        cid = str((x.get("_song") or {}).get("identifier") or "")
        if cid.isdigit():
            u, dur = bili_resolve_cid(bvid, cid, buvid)
        else:
            u, dur = bili_resolve(bvid, buvid)
        resolved[i] = (u, dur)
        n += 1
        print("  %s %s" % ("✓" if u else "×", tracks[i]["song_name"][:32]), flush=True)
        if n % 3 == 0:
            with io.open(cache_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(resolved, ensure_ascii=False))
        if u:
            fail_streak = 0
            time.sleep(18)
        else:
            fail_streak += 1
            time.sleep(45 if fail_streak < 3 else 120)

    with io.open(cache_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(resolved, ensure_ascii=False))
    ok = sum(1 for v in resolved.values() if v[0])
    print("B 站解析成功: %d/%d" % (ok, len(bili_items)))

    # 封面
    cover_jobs = [(i, x.get("cover_url"), x.get("song_name")) for i, x in enumerate(tracks)]
    covers = {}
    with ThreadPoolExecutor(12) as ex:
        for i, p in zip(range(len(tracks)), ex.map(download_cover, cover_jobs)):
            covers[i] = p
    print("封面完成:", len(covers))

    lib = []
    for i, x in enumerate(tracks):
        dur = x.get("duration_s") or 0
        url = (x.get("_song") or {}).get("download_url") or ""
        playable = bool(url)
        refresh = None
        if x["source"] == "Bilibili":
            u, d = resolved.get(i, (None, None))
            if u:
                url = u
                if d:
                    dur = d
                playable = True
            else:
                playable = False
        elif x["source"] in ("Kuwo", "MyFreeMP3"):
            # 原始直链已失效（酷我 410 / 网易 403），保留元数据，运行时再尝试解析
            playable = False
            refresh = x["source"]

        singer = (x.get("singers") or "").strip() or "布依族民间歌手"
        title = (x.get("song_name") or "").strip()
        album = (x.get("album") or "").strip()
        if album and re.match(r"^BV[0-9A-Za-z]{10}$", album):
            album = "B站音视频"
        lib.append({
            "id": "b%d" % i,
            "title": title,
            "artist": singer,
            "album": album or "布依族民歌",
            "duration": int(dur or 0),
            "durationText": fmt_dur(dur),
            "cover": covers.get(i, "assets/covers/c0.svg"),
            "source": x.get("source_cn") or x.get("source"),
            "playable": playable,
            "url": url,
            "refresh": refresh,
            "category": classify(title, album),
        })

    available = sum(1 for t in lib if t["playable"])
    print("可播放: %d / %d" % (available, len(lib)))

    cats = {}
    for t in lib:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    print("分类:", cats)

    out = {
        "meta": {
            "name": raw.get("name"),
            "group": raw.get("group"),
            "keywords": raw.get("kws"),
            "builtAt": raw.get("built_at"),
            "total": len(lib),
            "available": available,
        },
        "tracks": lib,
    }
    with io.open(os.path.join(OUT_DATA, "library.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False))
    print("已写入:", os.path.join(OUT_DATA, "library.json"))


if __name__ == "__main__":
    main()
