#!/usr/bin/env python3
"""
Instagram投稿用画像を生成する。

会社サイト（www.aomori-hiba.com/images/）にある実写を取得し、
1080x1080に切り出し、ブランドカラーの帯と明朝体の見出しを載せて
images/2026-08/ に書き出す。

ローカル素材をアップロードできない環境でも、このスクリプトを
GitHub Actions 上で走らせれば同じ画像が再生成できる。
"""
import io
import os
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BASE = "https://www.aomori-hiba.com/images/"
OUTDIR = "images/2026-08"
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-JP-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
]

S = 1080
CREAM = (242, 240, 233)
COPPER = (174, 112, 66)
GREEN = (27, 43, 33)
BAND_H = 300
FEATHER = 90
PRECROP = {"hiba-cutting-boards.jpg": (0.24, 0.37, 0.78, 1.0)}

# (出力名, 元画像, 見出し行, 縦方向の切り出し位置 0=上 1=下)
ITEMS = [
    ("01-woodchips", "factory-woodchips.jpg",
     ["捨てるはずだった、", "かんな屑から。"], 0.45),
    ("02-leaf", "hiba-leaf-macro-1.jpg",
     ["ヒノキにはない。", "ヒバにだけある。"], 0.50),
    ("03-hq", "oma-northernmost-monument.jpg",
     ["本州の、", "いちばん北で作っています。"], 0.40),
    ("04-soap", "hiba-soap.jpg",
     ["全成分、", "そのまま載せています。"], 0.45),
    ("05-forest", "forest-grove-1.jpg",
     ["日本三大美林の", "ひとつです。"], 0.50),
    ("06-sealing", "factory-sealing-machine.jpg",
     ["一本ずつ、", "ここで詰めています。"], 0.45),
    ("07-blocks", "factory-timber-crate.jpg",
     ["端材も、", "まだ木です。"], 0.50),
    ("08-regeneration", "hiba-log-ferns.jpg",
     ["朽ちた木から、", "次が出る。"], 0.50),
    ("09-inspection", "factory-material-weighing.jpg",
     ["「検品後」と", "書いた箱があります。"], 0.45),
    ("10-trunk", "hiba-trunk-4.jpg",
     ["この太さに、", "200年。"], 0.50),
    ("11-bottles", "factory-spray-bottles.jpg",
          ["同じ釜から、", "油と水が採れます。"], 0.45),
    ("12-board", "hiba-cutting-boards.jpg",
     ["削れば、", "また新しい面が出る。"], 0.50),
]


def pick_font():
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("明朝体フォントが見つかりません。fonts-noto-cjk を入れてください。")


def load(name):
    src = os.environ.get("LOCAL_SRC_DIR")
    if src:
        return Image.open(os.path.join(src, name)).convert("RGB")
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "hiba-image-builder"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGB")


def square_crop(im, focus):
    w, h = im.size
    if w > h:
        left = (w - h) // 2
        return im.crop((left, 0, left + h, h))
    top = int((h - w) * focus)
    top = max(0, min(top, h - w))
    return im.crop((0, top, w, top + w))


def grade(im):
    im = ImageEnhance.Color(im).enhance(0.72)
    im = ImageEnhance.Contrast(im).enhance(1.05)
    a = np.array(im).astype(np.float32)
    a[:, :, 1] *= 0.96
    a[:, :, 0] *= 1.01
    a[:, :, 2] *= 1.02
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def band_and_text(im, lines, font_path):
    band = Image.new("RGB", (S, BAND_H), GREEN)
    mask = Image.new("L", (S, BAND_H), 255)
    px = mask.load()
    for y in range(FEATHER):
        v = int(255 * (y / FEATHER) ** 1.2)
        for x in range(S):
            px[x, y] = v
    im.paste(band, (0, S - BAND_H), mask)

    draw = ImageDraw.Draw(im)
    size = 60
    font = ImageFont.truetype(font_path, size)
    ascent, _ = font.getmetrics()
    line_h = int(size * 1.5)
    margin = 76
    total = line_h * len(lines)
    solid_top = S - BAND_H + FEATHER
    base_y = solid_top + (S - solid_top - total) // 2 + ascent - 6
    for i, line in enumerate(lines):
        draw.text((margin, base_y + i * line_h), line, font=font, fill=CREAM, anchor="ls")
    rule_y = base_y - ascent - 26
    draw.line([(margin, rule_y), (margin + 64, rule_y)], fill=COPPER, width=2)
    return im


def main():
    font_path = pick_font()
    os.makedirs(OUTDIR, exist_ok=True)
    for name, src, lines, focus in ITEMS:
        im = load(src)
        if src in PRECROP:
            l, t, r, b = PRECROP[src]
            im = im.crop((int(l * im.size[0]), int(t * im.size[1]), int(r * im.size[0]), int(b * im.size[1])))
        low = im.size[0] < 900
        im = square_crop(im, focus).resize((S, S), Image.LANCZOS)
        if low:
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=105, threshold=2))
        im = grade(im)
        im = band_and_text(im, lines, font_path)
        out = os.path.join(OUTDIR, name + ".jpg")
        im.save(out, quality=90, optimize=True)
        print("wrote", out, im.size)


if __name__ == "__main__":
    main()
