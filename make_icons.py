# -*- coding: utf-8 -*-
"""アプリアイコン生成 — てんきとくらす風の「白ベース＋指数Aバッジ」

web/img/mnt1.gif（50x36・白背景の緑の山＋A）を高解像度化して、
白い背景にそのまま置いた PNG を作る（原画が白背景なので継ぎ目が出ない）。

    python make_icons.py

出力: web/icon-192.png, web/icon-512.png, web/icon-maskable-512.png,
      web/apple-touch-icon.png

Pillow だけで動く（numpy 不要）。
"""
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SRC = os.path.join(WEB, "img", "mnt1.gif")
BG = (255, 255, 255)       # 白ベース（てんきとくらすのページと同じ）
SS = 4                     # スーパーサンプリング倍率
RESAMPLE = Image.Resampling.LANCZOS

BADGE = Image.open(SRC).convert("RGB")


def compose(size, fill=0.78, radius=0.22):
    """size角のアイコンを作る。

    fill   = バッジが占める割合（0.78＝白フチを広めに取る）
    radius = 角丸の比率（0＝全面ベタ。maskable と iOS は 0）
    """
    S = size * SS
    img = Image.new("RGB", (S, S), BG)

    bw, bh = BADGE.size
    k = min(S * fill / bw, S * fill / bh)
    badge = BADGE.resize((max(1, round(bw * k)), max(1, round(bh * k))), RESAMPLE)
    # 小さい原画の拡大でぼけるので、軽く輪郭を立てる
    badge = badge.filter(ImageFilter.UnsharpMask(radius=S / 200, percent=60, threshold=2))
    img.paste(badge, ((S - badge.width) // 2, (S - badge.height) // 2))

    if not radius:
        return img.resize((size, size), RESAMPLE)

    # 角丸の外側は透明（白い四角が浮いて見えるように）
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, S - 1, S - 1], radius=int(S * radius), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out.resize((size, size), RESAMPLE)


def main():
    jobs = [
        # 角丸＋透明の角（ホーム画面・タブ用）
        ("icon-192.png", 192, 0.78, 0.22),
        ("icon-512.png", 512, 0.78, 0.22),
        # maskable: 全面ベタ白・セーフゾーン（中央80%の円）に収まる大きさ
        ("icon-maskable-512.png", 512, 0.66, 0),
        # iOS はOS側で角丸に切るので全面ベタ
        ("apple-touch-icon.png", 180, 0.72, 0),
    ]
    for name, size, fill, radius in jobs:
        out = compose(size, fill=fill, radius=radius)
        path = os.path.join(WEB, name)
        out.save(path, optimize=True)
        print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    main()
