#!/usr/bin/env python3
"""
ストーリーズ（1080x1920）用のカード画像を生成する。

2種類のレイアウト:
  photo … 上に写真、下に深緑の帯＋明朝の本文（ハイライトの表紙・場面カード向け）
  text  … クリーム地に明朝（Q&A・説明カード向け）

ハイライトの束ごとに CARDS を定義して実行する。
出力は images/stories/<slug>.jpg。
"""
import os
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

W, H = 1080, 1920
CREAM = (245, 240, 232)
GREEN = (27, 52, 32)
GOLD = (196, 168, 130)
SUB = (111, 106, 94)
SRC = os.environ.get("LOCAL_SRC_DIR", "/home/claude/hiba-website/images")
OUT = "images/stories"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SERIF_M = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# ストーリーズはUIが上下に被るので、安全領域は上下250pxを空ける
SAFE_TOP, SAFE_BOTTOM = 250, 250


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(text, n):
    """行末に句読点だけが取り残されるのを防ぐ簡易禁則付きの折り返し。"""
    if not text:
        return []
    lines = textwrap.wrap(text, n)
    out = []
    for line in lines:
        if out and line.strip() and all(c in "。、）」！？" for c in line):
            out[-1] += line
        else:
            out.append(line)
    fixed = []
    for line in out:
        while len(line) > n and line[n] in "。、）」！？":
            n_line, line = line[: n + 1], line[n + 1 :]
            fixed.append(n_line)
            break
        else:
            fixed.append(line)
            continue
        if line:
            fixed.append(line)
    return fixed


BASE_URL = "https://www.aomori-hiba.com/images/"


def open_source(name):
    """ローカルの素材ディレクトリになければ会社サイトから取得する。
    GitHub Actions 上ではローカルに素材が無いので、こちらの経路を通る。"""
    local = os.path.join(SRC, name)
    if os.path.exists(local):
        return Image.open(local)
    import io
    import urllib.request
    with urllib.request.urlopen(BASE_URL + name, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def photo_bg(name, focus=0.5):
    im = open_source(name).convert("RGB")
    if min(im.size) < 1080:
        raise SystemExit(f"解像度不足のためストーリーに使えません: {name} {im.size}")
    # 1080x1920 に被せる（縦長にクロップ）
    tw, th = W, H
    scale = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * scale + 0.5), int(im.height * scale + 0.5)), Image.LANCZOS)
    top = int((im.height - th) * focus)
    im = im.crop((max(0, (im.width - tw) // 2), max(0, top), max(0, (im.width - tw) // 2) + tw, max(0, top) + th))
    im = ImageEnhance.Color(im).enhance(0.75)
    return im


def gradient_band(im, height, feather=260):
    band = Image.new("RGB", (W, height), GREEN)
    mask = Image.new("L", (W, height), 255)
    px = mask.load()
    for y in range(feather):
        v = int(255 * (y / feather) ** 1.25)
        for x in range(W):
            px[x, y] = v
    im.paste(band, (0, H - height), mask)
    return im


def render(card):
    slug = card["slug"]
    kicker = card.get("kicker", "")
    title = card.get("title", "")
    body = card.get("body", "")
    note = card.get("note", "")

    if card.get("photo"):
        im = photo_bg(card["photo"], card.get("focus", 0.5))
        im = gradient_band(im, 980)
        fg, sub_fg = CREAM, (200, 208, 198)
        y = H - 980 + 300
    else:
        im = Image.new("RGB", (W, H), CREAM)
        fg, sub_fg = GREEN, SUB
        y = SAFE_TOP + 180

    d = ImageDraw.Draw(im)
    m = 92

    if kicker:
        d.text((m, y), kicker, font=font(SANS, 30), fill=GOLD, anchor="ls")
        y += 34
    d.line([(m, y), (m + 72, y)], fill=GOLD, width=2)
    y += 96

    if title:
        size, per, lh = (74, 12, 108) if len(title) <= 13 else (58, 16, 88)
        f = font(SERIF_M, size)
        for line in wrap(title, per):
            d.text((m, y), line, font=f, fill=fg, anchor="ls")
            y += lh
        y += 40

    if body:
        f = font(SERIF, 42)
        for para in body.split("\n"):
            if not para:
                y += 34
                continue
            for line in wrap(para, 21):
                d.text((m, y), line, font=f, fill=fg, anchor="ls")
                y += 76
            y += 22

    if note:
        f = font(SANS, 30)
        ny = max(y + 70, H - SAFE_BOTTOM - 40)
        for line in reversed(wrap(note, 30)):
            d.text((m, ny), line, font=f, fill=sub_fg, anchor="ls")
            ny -= 48

    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/{slug}.jpg"
    im.save(path, "JPEG", quality=90, optimize=True, progressive=True)
    return path


if __name__ == "__main__":
    import json
    import sys

    cards = json.load(open(sys.argv[1], encoding="utf-8"))
    for c in cards:
        print(render(c))
