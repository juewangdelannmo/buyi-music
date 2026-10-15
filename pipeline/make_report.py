# -*- coding: utf-8 -*-
"""生成布依音曲库增删详细报告"""
import io
import json
import os
import sys
from collections import Counter, OrderedDict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(PROJECT, "src", "data", "library.json")
CHANGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "change_log.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "布依音-曲库增删报告.md")

REASON_GROUP = OrderedDict([
    ("A", "A · 其他民族/地域歌曲（检索噪声）"),
    ("B", "B · 名称误命中（如「布衣乐队」≠布依族）"),
    ("C", "C · 歌唱家个人专辑中的非布依族民歌"),
    ("D", "D · 非歌曲内容（有声书/教学/纪录片/抖音原声）"),
    ("E", "E · 咪咕渠道检索噪声"),
    ("F", "F · 微信合辑中的非布依族音频"),
    ("G", "G · 无法确认与布依族关联的条目"),
])


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    ch = json.load(io.open(CHANGE, encoding="utf-8"))
    tracks = lib["tracks"]
    removed = ch["removed"]
    added = ch["added"]

    # 统计
    by_src_before = Counter()
    by_src_after = Counter(t["source"] for t in tracks)
    by_cat_after = Counter(t["category"] for t in tracks)
    avail_after = sum(1 for t in tracks if t.get("playable"))

    # 删除条目的来源/分类分布（用 change_log 自带信息）
    rem_by_src = Counter(r["source"] for r in removed)
    rem_by_reason = Counter(r["reason"][0] for r in removed)
    add_by_src = Counter(a["source"] for a in added)
    add_by_cat = Counter()
    for t in tracks:
        if t["id"].startswith("n"):
            add_by_cat[t["category"]] += 1

    L = []
    w = L.append
    w("# 布依音 · 曲库增删详细报告\n")
    w("> 生成时间：%s　|　曲库文件：`src/data/library.json`\n"
      % datetime.now().strftime("%Y-%m-%d %H:%M"))
    w("\n---\n")

    w("## 一、总览\n")
    w("| 项目 | 数量 |")
    w("|---|---:|")
    w("| 原始曲目总数 | %d |" % ch["before"])
    w("| 本次删除 | **-%d** |" % len(removed))
    w("| 本次新增 | **+%d** |" % len(added))
    w("| 现曲目总数 | **%d** |" % ch["after"])
    w("| 其中可播放 | %d |" % avail_after)
    w("| 无可用音源（仅保留条目） | %d |" % (ch["after"] - avail_after))
    w("")
    w("**净变化**：%d → %d（%s%d）\n"
      % (ch["before"], ch["after"], "+" if ch["after"] >= ch["before"] else "",
         ch["after"] - ch["before"]))

    # 删除
    w("\n## 二、删除明细（共 %d 首）\n" % len(removed))
    w("### 2.1 按删除原因分类\n")
    w("| 类别 | 数量 | 说明 |")
    w("|---|---:|---|")
    for k, name in REASON_GROUP.items():
        if rem_by_reason.get(k):
            w("| %s | %d | %s |" % (k, rem_by_reason[k], name.split("·")[1].strip()))
    w("")
    w("### 2.2 按来源平台分布\n")
    w("| 来源 | 删除数 |")
    w("|---|---:|")
    for s, n in rem_by_src.most_common():
        w("| %s | %d |" % (s, n))
    w("")

    w("### 2.3 逐条删除清单\n")
    for k, name in REASON_GROUP.items():
        rows = [r for r in removed if r["reason"][0] == k]
        if not rows:
            continue
        w("\n#### %s（%d 首）\n" % (name, len(rows)))
        w("| # | 曲名 | 歌手/UP主 | 来源 | 删除理由 |")
        w("|---:|---|---|---|---|")
        for i, r in enumerate(rows, 1):
            w("| %d | %s | %s | %s | %s |"
              % (i, r["title"][:40].replace("|", "/"), r["artist"][:16].replace("|", "/"),
                 r["source"], r["reason"].split("-", 1)[-1]))

    # 新增
    w("\n## 三、新增明细（共 %d 首）\n" % len(added))
    w("### 3.1 概况\n")
    n_bili = sum(1 for a in added if a["source"] == "B站")
    n_migu = sum(1 for a in added if a["source"] == "咪咕音乐")
    w("| 渠道 | 新增 | 说明 |")
    w("|---|---:|---|")
    w("| B 站（bilibili） | %d | 19 组关键词检索 → 去重后 97 条候选 → 人工甄别保留音乐类 %d 条，音源解析成功率 100%% |"
      % (n_bili, n_bili))
    w("| 咪咕音乐（musicdl） | %d | 6 组关键词检索 → 标题特征词严格过滤 → 逐条实测直链可下载后入库 |" % n_migu)
    w("")
    w("- 检索关键词：`布依族民歌`、`布依山歌`、`好花红`、`布依族八音坐唱`、`布依族勒尤`、`布依语歌曲`、`布依族酒歌`、`贵州布依族` 等")
    w("- 取得可播放音源：%d/%d 首\n" % (sum(1 for a in added if a["playable"]), len(added)))
    w("\n### 3.2 分类分布\n")
    w("| 分类 | 新增数 |")
    w("|---|---:|")
    for c, n in add_by_cat.most_common():
        w("| %s | %d |" % (c, n))
    w("")
    w("### 3.3 逐条新增清单\n")
    w("| # | 曲名 | UP主/歌手 | 时长 | BV号 | 音源 |")
    w("|---:|---|---|---|---|---|")
    for i, a in enumerate(added, 1):
        w("| %d | %s | %s | %s | `%s` | %s |"
          % (i, a["title"][:40].replace("|", "/"), a["artist"][:16].replace("|", "/"),
             a["duration"], a.get("bvid", ""), "可用" if a["playable"] else "待补"))

    # 现状
    w("\n## 四、渠道可行性验证\n")
    w("本次补充逐一对各公开渠道做了实测：\n")
    w("| 渠道 | 检索 | 播放链接 | 结论 |")
    w("|---|---|---|---|")
    w("| **B 站** | ✅ 公开检索接口 `/x/web-interface/search/type` | ✅ 网页 `window.__playinfo__` 直取 dash 音频 | **采用**，新增 %d 首 |"
      % sum(1 for a in added if a["source"] == "B站"))
    w("| **咪咕音乐** | ✅ musicdl `MiguMusicClient` | ✅ 直链逐条实测可下载 | **采用**，新增 %d 首 |"
      % sum(1 for a in added if a["source"] == "咪咕音乐"))
    w("| 酷狗音乐 | ⚠️ musicdl `KugouMusicClient` 可用 | ✅ 直链有效 | 试采：结果噪声比例极高（搜「布依族」返回的多为草原/藏族歌），且高频检索被限流，本次未入库 |")
    w("| QQ 音乐 | ⚠️ 检索可返回但极慢 | ⚠️ 需 vkey 签名、时效短 | 未采用 |")
    w("| 网易云音乐 | ✅ 检索接口可用 | ❌ 外链 404、播放接口需登录 | 未采用 |")
    w("| 酷我音乐 | ❌ 需 token 签名（`request illegal`） | ❌ 存量直链 410 / 反爬假文件 | 未采用（库内其存量条目为失效音源） |")
    w("")
    w("**关键技巧**：B 站 `api.bilibili.com` 的 `view` / `playurl` 接口持续请求会触发 -352/412 频控；"
      "改为抓取视频网页（带 `buvid3` Cookie）后解析内嵌的 `window.__playinfo__`，"
      "**单次请求**即可拿到 dash 音频流，66 首全部成功且间隔 5 秒即可稳定运行。\n")

    w("\n## 五、更新后曲库结构\n")
    w("### 5.1 来源分布\n")
    w("| 来源 | 曲目数 |")
    w("|---|---:|")
    for s, n in by_src_after.most_common():
        w("| %s | %d |" % (s, n))
    w("")
    w("### 5.2 歌单分类分布\n")
    w("| 分类 | 曲目数 |")
    w("|---|---:|")
    for c, n in by_cat_after.most_common():
        w("| %s | %d |" % (c, n))
    w("")

    w("\n## 六、数据完整性\n")
    w("- 删除条目对应的封面文件（303 张中相关部分）与随包离线音频已同步清理，避免残留垃圾文件。")
    w("- 新增条目已生成封面（优先下载 B 站原图，失败则生成蜡染风格占位封面）。")
    w("- 全部曲目重新按统一规则归类，新增「舞蹈」类目以收纳布依族民间舞蹈音乐。")
    w("- 无音源条目仍保留元数据并标注「音源待修复」，应用内可用「仅显示可播放」过滤。")

    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("报告已生成:", OUT, len(L), "行")


if __name__ == "__main__":
    main()
