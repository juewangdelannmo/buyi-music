# -*- coding: utf-8 -*-
"""从 B 站检索布依族相关音视频，输出候选清单（去重、过滤）"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
H = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}

KEYWORDS = [
    "布依族民歌", "布依族歌曲", "布依山歌", "好花红", "布依族八音坐唱",
    "布依族勒尤", "布依语歌曲", "布依族酒歌", "布依族婚礼", "布依族童谣",
    "布依族唢呐", "布依族木叶", "布依族对歌", "布依族古歌", "贵州布依族",
    "布依族舞蹈", "布依族乐器", "惠水好花红", "布依族情歌",
]

TAG = re.compile(r"</?em[^>]*>")


def search(kw, page=1):
    u = ("https://api.bilibili.com/x/web-interface/search/type?search_type=video"
         "&keyword=%s&page=%d&order=totalrank" % (urllib.parse.quote(kw), page))
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25)
        j = json.loads(r.read().decode("utf-8", "ignore"))
        if j.get("code") != 0:
            return []
        return j["data"].get("result", [])
    except Exception as e:
        print("  [warn] %s p%d: %s" % (kw, page, str(e)[:50]), flush=True)
        return []


def main():
    lib = json.load(io.open(os.path.join(PROJECT, "src", "data", "library.json"), encoding="utf-8"))
    have_bv = set()
    have_title = set()
    for t in lib["tracks"]:
        if t["source"] == "B站":
            m = re.search(r"(BV[0-9A-Za-z]{10})", t.get("album") or "")
            if m:
                have_bv.add(m.group(1))
        have_title.add(re.sub(r"\s+", "", t["title"])[:16])

    found = {}
    for kw in KEYWORDS:
        for page in (1, 2):
            res = search(kw, page)
            for it in res:
                bv = it.get("bvid")
                if not bv or bv in have_bv:
                    continue
                title = TAG.sub("", it.get("title") or "").strip()
                if not re.search(r"布依|好花红|Bouyei|布越| Buyi|布依族|濮越", title, re.I):
                    continue
                key = re.sub(r"\s+", "", title)[:16]
                if key in have_title:
                    continue
                found.setdefault(bv, {
                    "bvid": bv, "title": title, "author": it.get("author", ""),
                    "duration": it.get("duration", ""), "aid": it.get("aid"),
                    "pic": (it.get("pic") or "").replace("http://", "https://"),
                    "pubdate": it.get("pubdate", 0), "kw": kw
                })
            print("%-12s p%d -> 累计 %d" % (kw, page, len(found)), flush=True)
            time.sleep(2.5)

    items = sorted(found.values(), key=lambda x: -(x.get("pubdate") or 0))
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "candidates.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(items, ensure_ascii=False, indent=1))
    print("\n候选总数:", len(items))
    for i, it in enumerate(items):
        print("%3d | %s | %s | %s" % (i, it["bvid"], it["author"][:12], it["title"][:46]))


if __name__ == "__main__":
    main()
