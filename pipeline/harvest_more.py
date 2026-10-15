# -*- coding: utf-8 -*-
"""用 musicdl 从酷狗/咪咕/QQ音乐/酷我补充布依族歌曲
   严格过滤：标题必须命中布依族特征词；逐条实测直链可下载；与现有曲库去重
"""
import io
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(k, None)

from musicdl import musicdl  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(PROJECT, "src", "data", "library.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SOURCES = {
    "MiguMusicClient": "咪咕音乐",
}
KEYWORDS = ["好花红", "布依族", "布依族民歌", "布依", "布依山歌", "贵州布依族"]

# 相关性判定：标题命中
MUST = re.compile(r"布依|布越|好花红|Bouyei|Buyi", re.I)
# 明确的噪声（其他民族/地区）
NOISE = re.compile(r"彝|藏|蒙古|草原|高原|雪山|九寨|青藏|维吾尔|朝鲜族|苗族(?!.*布依)|壮族(?!.*布依)")


def norm(s):
    return re.sub(r"[\s\(\)（）\[\]【】·・\-—_,，。!！?？'\"“”《》]", "", (s or "")).lower()


def head_ok(url, timeout=20):
    """实测直链能否取到音频数据"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-2048"})
        r = urllib.request.urlopen(req, timeout=timeout)
        if r.status >= 400:
            return False
        ct = (r.headers.get("Content-Type") or "").lower()
        data = r.read(2048)
        if len(data) < 100:
            return False
        if ct and not any(k in ct for k in ("audio", "octet", "mpeg", "mp4", "video", "flac", "x-flac")):
            return False
        return True
    except Exception:
        return False


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    have = set()
    for t in lib["tracks"]:
        have.add(norm(t["title"])[:18])
        have.add(norm(t["artist"]) + "|" + norm(t["title"])[:14])

    cfg = {s: {"work_dir": "downloads", "search_size_per_source": 20, "max_retries": 1}
           for s in SOURCES}
    client = musicdl.MusicClient(music_sources=list(SOURCES), init_music_clients_cfg=cfg)

    candidates = {}
    for src, cn in SOURCES.items():
        for kw in KEYWORDS:
            try:
                songs = client.music_clients[src].search(keyword=kw) or []
            except Exception as e:
                print("  [err] %s %s: %s" % (cn, kw, str(e)[:50]), flush=True)
                continue
            for s in songs:
                name = (s.song_name or "").strip()
                if not name or not MUST.search(name):
                    continue
                if NOISE.search(name) and not re.search(r"布依", name):
                    continue
                key = norm(name)[:18]
                if key in have:
                    continue
                if key in candidates:
                    continue
                candidates[key] = {
                    "title": name,
                    "artist": (s.singers or "").strip(),
                    "album": (s.album or "").strip(),
                    "ext": s.ext or "mp3",
                    "duration": getattr(s, "duration_s", None) or 0,
                    "url": s.download_url or "",
                    "source": cn,
                }
            print("%-8s %-10s -> 累计 %d" % (cn, kw, len(candidates)), flush=True)

    # 断点保存：采集完就落盘，避免后续阶段被中断时丢失
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "candidates_extra.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(list(candidates.values()), ensure_ascii=False, indent=1))
    print("\n候选 %d 首（已存 candidates_extra.json），开始实测直链…" % len(candidates), flush=True)
    out = []
    for key, c in candidates.items():
        if not c["url"]:
            continue
        ok = head_ok(c["url"])
        print("  %s %s | %s | %s" % ("✓" if ok else "×", c["source"],
                                     c["title"][:26], c["artist"][:12]), flush=True)
        if ok:
            out.append(c)

    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extra_songs.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))
    from collections import Counter
    print("\n可用新增 %d 首：%s" % (len(out), dict(Counter(x["source"] for x in out))))


if __name__ == "__main__":
    main()
