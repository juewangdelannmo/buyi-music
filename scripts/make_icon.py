# -*- coding: utf-8 -*-
"""生成应用图标（布依族铜鼓纹 + 好花红），输出 build/icon.ico 与 src/assets/icon.ico"""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
ASSETS = os.path.join(ROOT, "src", "assets")
os.makedirs(BUILD, exist_ok=True)
os.makedirs(ASSETS, exist_ok=True)

INDIGO = (16, 36, 54, 255)
INDIGO2 = (46, 107, 143, 255)
GOLD = (201, 162, 39, 255)
RED = (200, 54, 47, 255)
CREAM = (247, 242, 232, 255)


def render(size):
    """返回 RGBA 字节序列（自左上角起，逐行）"""
    px = bytearray()
    cx = cy = (size - 1) / 2.0
    r_out = size / 2.0 - 0.5
    r_ring1 = r_out * 0.62
    r_ring2 = r_out * 0.30
    r_core = r_out * 0.115
    rays = 12
    ray_len_in = r_out * 0.62
    ray_len_out = r_out * 0.86
    ray_w = max(1.0, size * 0.030)

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            d = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            # 默认：圆外的底色（靛蓝渐变圆形图标）
            if d > r_out:
                px += bytes(CREAM[:3]) + b"\x00"
                continue
            t = d / r_out
            col = (
                int(INDIGO[0] + (INDIGO2[0] - INDIGO[0]) * t),
                int(INDIGO[1] + (INDIGO2[1] - INDIGO[1]) * t),
                int(INDIGO[2] + (INDIGO2[2] - INDIGO[2]) * t),
                255,
            )
            # 铜鼓太阳芒线
            if ray_len_in <= d <= ray_len_out:
                for k in range(rays):
                    ang = k * (2 * math.pi / rays)
                    diff = abs((a - ang + math.pi) % (2 * math.pi) - math.pi)
                    if diff < ray_w / max(d, 1):
                        col = CREAM
                        break
            # 金环
            if abs(d - r_ring1) < max(1.0, size * 0.022):
                col = GOLD
            elif abs(d - r_ring2) < max(1.0, size * 0.014):
                col = GOLD
            # 红花心
            if d <= r_core:
                col = RED
            px += bytes(col)
    return bytes(px)


def png_bytes(size):
    raw = render(size)
    rows = bytearray()
    stride = size * 4
    for y in range(size):
        rows.append(0)
        rows += raw[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [(s, png_bytes(s)) for s in sizes]
    n = len(images)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16 * n
    entries = b""
    data = b""
    for s, img in images:
        entries += struct.pack("<BBBBHHII", s if s < 256 else 0, s if s < 256 else 0,
                               0, 0, 1, 32, len(img), offset)
        offset += len(img)
        data += img
    ico = header + entries + data
    for p in (os.path.join(BUILD, "icon.ico"), os.path.join(ASSETS, "icon.ico")):
        with open(p, "wb") as f:
            f.write(ico)
        print("已生成:", p, len(ico), "bytes")

    with open(os.path.join(ASSETS, "icon.png"), "wb") as f:
        f.write(png_bytes(256))
    print("已生成: icon.png")


if __name__ == "__main__":
    main()
