# -*- coding: utf-8 -*-
"""把可播放曲目的音频下载到 src/assets/audio/，随安装包一起分发（离线可听）"""
import io
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "src", "data", "library.json")
OUT = os.path.join(ROOT, "src", "assets", "audio")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def ext_of(url):
    clean = (url or "").split("?")[0]
    ext = os.path.splitext(clean)[1].lower()
    return ext if ext in (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".mp4") else ".mp3"


def fetch(t):
    url = t.get("url") or ""
    if not url:
        return t["id"], 0, "无链接"
    ext = ".m4a" if "bilivideo" in url else ext_of(url)
    target = os.path.join(OUT, t["id"] + ext)
    if os.path.exists(target) and os.path.getsize(target) > 20000:
        return t["id"], os.path.getsize(target), "已存在"
    h = {"User-Agent": UA}
    if "bilivideo" in url or "hdslb" in url:
        h["Referer"] = "https://www.bilibili.com/"
    try:
        req = urllib.request.Request(url, headers=h)
        r = urllib.request.urlopen(req, timeout=180)
        data = r.read()
        if len(data) < 20000:
            return t["id"], 0, "文件过小"
        with open(target, "wb") as f:
            f.write(data)
        return t["id"], len(data), "OK"
    except Exception as e:
        return t["id"], 0, str(e)[:50]


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    tracks = [t for t in lib["tracks"] if t.get("playable") and t.get("url")]
    print("待下载:", len(tracks), flush=True)
    ok = 0
    total = 0
    with ThreadPoolExecutor(4) as ex:
        for tid, size, msg in ex.map(fetch, tracks):
            if size > 0:
                ok += 1
                total += size
                print("  ✓ %-8s %6.2f MB  %s" % (tid, size / 1048576, msg), flush=True)
            else:
                print("  × %-8s %s" % (tid, msg), flush=True)
    print("完成: %d/%d, 合计 %.1f MB" % (ok, len(tracks), total / 1048576))


if __name__ == "__main__":
    main()
