# -*- coding: utf-8 -*-
"""布依音项目体检：曲库完整性 + 封面/音频文件一致性 + 报告数字核对"""
import collections
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(P, "src", "data", "library.json")
COVERS = os.path.join(P, "src", "assets", "covers")
AUDIO = os.path.join(P, "src", "assets", "audio")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "布依音-曲库增删报告.md")

issues = []


def w(msg):
    print(msg, flush=True)


lib = json.load(io.open(LIB, encoding="utf-8"))
tracks = lib["tracks"]
w("曲库：%d 首，可播放 %d" % (len(tracks), lib["meta"]["available"]))

# 1. id 唯一
ids = [t["id"] for t in tracks]
dup = [k for k, v in collections.Counter(ids).items() if v > 1]
w("1) id 重复：%s" % (dup or "无"))
if dup:
    issues.append("id 重复 %s" % dup)

# 2. 必填字段
missing = collections.Counter()
for t in tracks:
    for f in ("id", "title", "artist", "album", "durationText", "cover", "source", "category"):
        if not t.get(f):
            missing[f] += 1
w("2) 字段缺失：%s" % (dict(missing) or "无"))
if missing:
    issues.append("字段缺失 %s" % dict(missing))

# 3. playable 必须有 url
bad = [t["id"] for t in tracks if t.get("playable") and not t.get("url")]
w("3) 标记可播放但无 url：%d 首 %s" % (len(bad), bad[:5]))
if bad:
    issues.append("可播放无 url %d 首" % len(bad))

# 4. 封面文件是否存在
nocover = []
for t in tracks:
    p = os.path.join(P, "src", t["cover"] if t["cover"].startswith("assets") else t["cover"])
    if not os.path.exists(p):
        nocover.append((t["id"], t["cover"]))
w("4) 封面文件缺失：%d 个 %s" % (len(nocover), nocover[:3]))
if nocover:
    issues.append("封面缺失 %d 个" % len(nocover))

# 5. 孤儿封面（有文件但无曲目引用）
used = set()
for t in tracks:
    b = os.path.basename(t["cover"])
    used.add(b)
orphan = [f for f in os.listdir(COVERS) if f not in used]
w("5) 孤儿封面文件：%d 个" % len(orphan))
if orphan:
    issues.append("孤儿封面 %d 个" % len(orphan))

# 6. 随包音频是否都有对应曲目
audio_ids = {f.split(".")[0] for f in os.listdir(AUDIO)} if os.path.exists(AUDIO) else set()
tid = set(ids)
orphan_a = audio_ids - tid
w("6) 孤儿音频文件：%d 个 %s" % (len(orphan_a), sorted(orphan_a)[:5]))
if orphan_a:
    issues.append("孤儿音频 %d 个" % len(orphan_a))

# 7. B 站曲目是否都有 bvid（运行时重解析依赖）
no_bv = [t["id"] for t in tracks if t["source"] == "B站" and not t.get("bvid")]
w("7) B 站曲目缺 bvid：%d 首 %s" % (len(no_bv), no_bv[:5]))
if no_bv:
    issues.append("B站缺 bvid %d 首" % len(no_bv))

# 8. 标题空白/异常
weird = [t["id"] for t in tracks if not t["title"].strip() or t["title"].strip() in ("未知曲目",)]
w("8) 标题异常：%d 首" % len(weird))
if weird:
    issues.append("标题异常 %d 首" % len(weird))

# 9. 分类分布
w("9) 分类：%s" % dict(collections.Counter(t["category"] for t in tracks)))
w("   来源：%s" % dict(collections.Counter(t["source"] for t in tracks)))

# 10. 报告数字核对
if os.path.exists(REPORT):
    txt = io.open(REPORT, encoding="utf-8").read()
    m_total = re.search(r"现曲目总数 \| \*\*(\d+)\*\*", txt)
    m_del = re.search(r"本次删除 \| \*\*-(\d+)\*\*", txt)
    m_add = re.search(r"本次新增 \| \*\*\+(\d+)\*\*", txt)
    m_avail = re.search(r"其中可播放 \| (\d+)", txt)
    ok = True
    if m_total and int(m_total.group(1)) != len(tracks):
        ok = False
        w("10) 报告总数不符：报告 %s vs 实际 %d" % (m_total.group(1), len(tracks)))
    if m_avail and int(m_avail.group(1)) != lib["meta"]["available"]:
        ok = False
        w("10) 报告可播放数不符：报告 %s vs 实际 %d" % (m_avail.group(1), lib["meta"]["available"]))
    if ok:
        w("10) 报告数字与曲库一致（总数 %d / 删除 %s / 新增 %s / 可播放 %d）"
          % (len(tracks), m_del.group(1) if m_del else "?", m_add.group(1) if m_add else "?",
             lib["meta"]["available"]))
else:
    w("10) 报告文件不存在")

w("")
w("=== 结论：%s ===" % ("发现 %d 类问题" % len(issues) if issues else "全部通过"))
for i in issues:
    w("  - " + i)
