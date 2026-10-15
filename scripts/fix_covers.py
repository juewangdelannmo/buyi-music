# -*- coding: utf-8 -*-
"""修复封面：处理微信防盗链占位图与各站点 Referer 差异"""
import collections
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVER_DIR = os.path.join(ROOT, "src", "assets", "covers")
LIB = os.path.join(ROOT, "src", "data", "library.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"


def fetch(url, referer=None, timeout=20):
    h = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    tracks = lib["tracks"]
    orig = json.load(io.open(r"C:/Users/d'm'n/Downloads/e07_布依族.json", encoding="utf-8"))
    otracks = orig["tracks"]

    # 1. 找出出现次数最多的文件 -> 微信占位图
    hashes = {}
    for fn in os.listdir(COVER_DIR):
        if fn.endswith(".jpg"):
            with open(os.path.join(COVER_DIR, fn), "rb") as f:
                hashes[fn] = hashlib.md5(f.read()).hexdigest()
    common = collections.Counter(hashes.values()).most_common(3)
    print("最常见封面哈希:", [(h[:8], c) for h, c in common])
    ph_hashes = {h for h, c in common if c >= 3}
    ph_files = {fn for fn, h in hashes.items() if h in ph_hashes}
    print("疑似占位图数量:", len(ph_files))

    bad_idx = set()
    for fn in ph_files:
        m = re.match(r"c(\d+)\.jpg", fn)
        if m:
            bad_idx.add(int(m.group(1)))

    # 2. 找出封面 URL 是 qpic.cn / 下载失败的
    for i, t in enumerate(tracks):
        host = ""
        m = re.match(r"https?://([^/]+)/", otracks[i].get("cover_url") or "")
        if m:
            host = m.group(1)
        if "qpic.cn" in host or i in bad_idx:
            bad_idx.add(i)
    print("需重下封面:", len(bad_idx))

    def redownload(i):
        url = otracks[i].get("cover_url") or ""
        jpg = os.path.join(COVER_DIR, "c%d.jpg" % i)
        svg = os.path.join(COVER_DIR, "c%d.svg" % i)
        try:
            if os.path.exists(jpg):
                os.remove(jpg)
            if os.path.exists(svg):
                os.remove(svg)
            ref = None
            if "hdslb.com" in url:
                ref = "https://www.bilibili.com/"
            data = fetch(url, ref)
            if len(data) > 3000:
                with open(jpg, "wb") as f:
                    f.write(data)
                return i, "assets/covers/c%d.jpg" % i
        except Exception:
            pass
        return i, None

    with ThreadPoolExecutor(8) as ex:
        results = dict(ex.map(redownload, sorted(bad_idx)))

    # 3. 更新 library.json
    fixed = 0
    for i, path in results.items():
        if path:
            tracks[i]["cover"] = path
            fixed += 1
        else:
            tracks[i]["cover"] = ""  # 前端用渐变占位
    with io.open(LIB, "w", encoding="utf-8") as f:
        f.write(json.dumps(lib, ensure_ascii=False))
    print("修复完成:", fixed, "/", len(bad_idx))


if __name__ == "__main__":
    main()
