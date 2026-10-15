# -*- coding: utf-8 -*-
"""为筛出的 B 站候选曲目解析音频流与封面，输出 new_songs.json
   采用网页直取 window.__playinfo__（单次请求，规避 API 的 -352/412 频控）
"""

import gzip
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVER_DIR = os.path.join(PROJECT, "src", "assets", "covers")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "new_resolve_cache.json")

# 人工甄别后保留的音乐类候选（candidates.json 中的下标）
KEEP = [2, 3, 4, 6, 8, 10, 11, 12, 14, 15, 16, 17, 19, 20, 23, 24, 26, 27, 28,
        31, 32, 33, 34, 36, 37, 38, 39, 40, 42, 43, 44, 45, 48, 50, 52, 53, 54,
        55, 56, 57, 58, 59, 62, 64, 65, 66, 67, 68, 70, 71, 73, 74, 75, 77, 79,
        80, 81, 82, 83, 84, 87, 88, 91, 92, 93, 96]


def http(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if headers:
        h.update(headers)
    r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
    data = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    return data


def buvid():
    j = json.loads(http("https://api.bilibili.com/x/frontend/finger/spi").decode("utf-8", "ignore"))
    return j["data"]["b_3"]


def from_page(bv, cookie):
    """从视频网页里取 window.__playinfo__，返回 (url, duration, hasDash)"""
    html = http("https://www.bilibili.com/video/" + bv, {
        "Cookie": "buvid3=" + cookie,
        "Referer": "https://www.bilibili.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }).decode("utf-8", "ignore")
    m = re.search(r"window\.__playinfo__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if not m:
        return None, None, False
    j = json.loads(m.group(1))
    d = j.get("data") or {}
    dur = (d.get("timelength") or 0) // 1000
    dash = d.get("dash") or {}
    aud = dash.get("audio") or []
    if aud:
        best = max(aud, key=lambda a: a.get("bandwidth", 0))
        return (best.get("baseUrl") or best.get("base_url")), dur or (dash.get("duration") or 0), True
    if d.get("durl"):
        return d["durl"][0].get("url"), dur, False
    return None, None, False


def from_api(bv, cookie):
    """兜底：走 API 两连请求"""
    h = {"Cookie": "buvid3=" + cookie, "Referer": "https://www.bilibili.com/"}
    try:
        v = json.loads(http("https://api.bilibili.com/x/web-interface/view?bvid=%s" % bv, h)
                       .decode("utf-8", "ignore"))
        if v.get("code") != 0:
            return None, None, False
        cid = v["data"]["cid"]
        dur = v["data"].get("duration", 0)
        p = json.loads(http("https://api.bilibili.com/x/player/playurl?bvid=%s&cid=%s&qn=16"
                            "&fnval=16&fourk=1&otype=json" % (bv, cid), h).decode("utf-8", "ignore"))
        if p.get("code") != 0:
            return None, None, False
        d = p["data"]
        if d.get("dash") and d["dash"].get("audio"):
            best = max(d["dash"]["audio"], key=lambda a: a.get("bandwidth", 0))
            return (best.get("baseUrl") or best.get("base_url")), dur, True
        if d.get("durl"):
            return d["durl"][0]["url"], dur, False
    except Exception as e:
        print("   [apiwarn] %s" % str(e)[:50], flush=True)
    return None, None, False


def dl_cover(url, path):
    try:
        if url.startswith("//"):
            url = "https:" + url
        data = http(url, {"Referer": "https://www.bilibili.com/"})
        if len(data) > 2000:
            with open(path, "wb") as f:
                f.write(data)
            return True
    except Exception:
        pass
    return False


def main():
    cands = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "candidates.json"), encoding="utf-8"))
    items = [cands[i] for i in KEEP if i < len(cands)]
    print("待解析:", len(items), flush=True)

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(io.open(CACHE, encoding="utf-8"))
            print("命中缓存:", len(cache), flush=True)
        except Exception:
            cache = {}

    cookie = buvid()
    out = []
    n_dash = 0
    for k, it in enumerate(items):
        bv = it["bvid"]
        tid = "n%d" % (1000 + k)
        if bv in cache and (cache[bv].get("url") or cache[bv].get("tried")):
            ent = cache[bv]
            u, dur = ent.get("url"), ent.get("duration")
        else:
            u, dur, dash = from_page(bv, cookie)
            if not u:
                time.sleep(2)
                u, dur, dash = from_api(bv, cookie)
            if u and dash:
                n_dash += 1
            cache[bv] = {"url": u, "duration": dur, "tried": True}
            with io.open(CACHE, "w", encoding="utf-8") as f:
                f.write(json.dumps(cache, ensure_ascii=False))
            time.sleep(5)

        cover_ok = dl_cover(it["pic"], os.path.join(COVER_DIR, "%s.jpg" % tid)) if it.get("pic") else False
        print("  %s %s | %s" % ("✓" if u else "×", bv, it["title"][:34]), flush=True)
        out.append({
            "title": it["title"], "author": it["author"], "bvid": bv,
            "duration": dur or 0, "url": u or "",
            "cover": "assets/covers/%s.jpg" % tid if cover_ok else "",
            "album": "B站音视频",
        })

    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "new_songs.json")), "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))
    ok = sum(1 for x in out if x["url"])
    print("解析完成：%d/%d 成功（其中 dash 音频 %d）" % (ok, len(out), n_dash))


if __name__ == "__main__":
    main()
