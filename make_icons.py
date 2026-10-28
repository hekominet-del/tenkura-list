# -*- coding: utf-8 -*-
"""アプリアイコン生成 — 登山指数「A」バッジ（img/mnt1.gif）をそのまま使う

web/img/mnt1.gif（50x36・白背景の緑の山＋A）を高解像度化して、
アプリのテーマ色 #0b1220 の上に配置した PNG を作る。

    python make_icons.py

出力: web/icon-192.png, web/icon-512.png, web/icon-maskable-512.png,
      web/apple-touch-icon.png

Pillow だけで動く（numpy 不要）。
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SRC = os.path.join(WEB, "img", "mnt1.gif")
BG = (11, 18, 32)          # --bg (#0b1220) アプリのテーマ色
BLEED = (110, 155, 8)      # 透過部分ににじませる色（山の緑。白フチ防止）
SS = 4                     # スーパーサンプリング倍率（角丸・輪郭を滑らかに）
RESAMPLE = Image.Resampling.LANCZOS


def badge_rgba():
    """白背景を透過にしたバッジ画像（原寸）を返す"""
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    src = im.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            if min(r, g, b) >= 240:          # 白＝背景 → 透明（緑をにじませる）
                dst[x, y] = BLEED + (0,)
            else:
                dst[x, y] = (r, g, b, 255)
    return out.crop(out.split()[3].getbbox())


BADGE = badge_rgba()


def compose(size, fill=0.72, radius=0.22):
    """size角のアイコンを作る。fill=バッジが占める割合, radius=角丸の比率"""
    S = size * SS
    base = Image.new("RGB", (S, S), BG)

    mask = Image.new("L", (S, S), 255)
    if radius:
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, S - 1, S - 1], radius=int(S * radius), fill=255)

    bw, bh = BADGE.size
    k = min(S * fill / bw, S * fill / bh)
    badge = BADGE.resize((max(1, round(bw * k)), max(1, round(bh * k))), RESAMPLE)

    base.paste(badge, ((S - badge.width) // 2, (S - badge.height) // 2), badge)

    out = Image.new("RGB", (S, S), BG)
    out.paste(base, (0, 0), mask)
    return out.resize((size, size), RESAMPLE)


def main():
    jobs = [
        ("icon-192.png", 192, 0.72, 0.22),
        ("icon-512.png", 512, 0.72, 0.22),
        # maskable: 角丸なし・セーフゾーン（中央80%の円）に収まる大きさ
        ("icon-maskable-512.png", 512, 0.62, 0),
        # iOS はOS側で角丸に切るので全面塗り
        ("apple-touch-icon.png", 180, 0.68, 0),
    ]
    for name, size, fill, radius in jobs:
        out = compose(size, fill=fill, radius=radius)
        path = os.path.join(WEB, name)
        out.save(path, optimize=True)
        print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    main()
