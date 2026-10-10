#!/usr/bin/env python3
"""
フィードのカルーセル画像（1080x1350・4:5）を生成する。

定義JSON（posts/carousels-*.json）の各投稿について、slides の順に画像を作り
images/<月>/c-<日付>-<n>.jpg に書き出す。スライドの種類:

  photo   … 写真全面＋下に深緑のグラデーション帯、kicker と見出し（1枚目・場面）
  cover   … 深緑地に大きな明朝の見出し（写真を使わない1枚目。写真表紙との比較用）
  text    … クリーム地。見出し＋手順（items）か本文（body）、下に注記（note）
  product … 上に商品写真、下にクリーム帯で商品名・ひとこと・ストアへの誘導

見出し・本文の折り返しは build_story_cards.wrap（禁則・\\n 改行対応）を使う。
写真は LOCAL_SRC_DIR（既定 /home/claude/hiba-website/images）か、
このリポジトリ内のパス（images/ で始まるもの）から読む。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from build_story_cards import wrap  # noqa: E402

W, H = 1080, 1350
CREAM = (245, 240, 232)
GREEN = (27, 52, 32)
GOLD = (196, 168, 130)
SUB = (111, 106, 94)
INK = (33, 44, 35)
SRC = os.environ.get("LOCAL_SRC_DIR", "/home/claude/hiba-website/images")
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SERIF_M = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
M = 88
BRAND = "ひばの森｜青森県大間町"


def F(path, size):
    return ImageFont.truetype(path, size)


def open_photo(name, box=None):
    """box=[x0,y0,x1,y1]（0〜1の割合）で先に切り抜く。焼き込み文字や値札を外すとき用"""
    path = name if name.startswith("images/") else os.path.join(SRC, name)
    im = Image.open(path).convert("RGB")
    if box:
        w, h = im.size
        im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    return im


def cover_crop(im, w, h, focus=0.5, focus_x=0.5):
    scale = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left = int((im.width - w) * focus_x)
    top = int((im.height - h) * focus)
    return im.crop((left, top, left + w, top + h))


def bottom_gradient(im, height, feather=240, alpha=235):
    band = Image.new("RGB", (W, height), GREEN)
    mask = Image.new("L", (W, height), alpha)
    px = mask.load()
    for y in range(feather):
        v = int(alpha * (y / feather) ** 1.3)
        for x in range(W):
            px[x, y] = v
    im.paste(band, (0, H - height), mask)
    return im


def pager(d, i, n, color):
    d.text((W - M, 92), f"{i} / {n}", font=F(SANS, 26), fill=color, anchor="rs")


def swipe(d, color):
    d.text((W - M, H - 72), "→", font=F(SANS, 40), fill=color, anchor="rs")


def lines_of(text, per):
    return wrap(text, per) if text else []


def slide_photo(s, i, n):
    im = cover_crop(open_photo(s["photo"], s.get("box")), W, H, s.get("focus", 0.5), s.get("focus_x", 0.5))
    im = ImageEnhance.Color(im).enhance(0.85)
    title = lines_of(s.get("title", ""), 14)
    body = lines_of(s.get("body", ""), 22)
    block = 34 + 70 + len(title) * 92 + (24 + len(body) * 62 if body else 0)
    top = s.get("band") == "top"  # 被写体が下にある写真は、文字帯を上に置く
    if top:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        im = bottom_gradient(im, block + 300)
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        im = bottom_gradient(im, block + 300)
    d = ImageDraw.Draw(im)
    y = 150 if top else H - 120 - block
    d.text((M, y + 30), s.get("kicker", ""), font=F(SANS, 30), fill=GOLD, anchor="ls")
    d.line([(M, y + 58), (M + 72, y + 58)], fill=GOLD, width=2)
    y += 58 + 92
    for ln in title:
        d.text((M, y), ln, font=F(SERIF_M, 64), fill=CREAM, anchor="ls")
        y += 92
    if body:
        y += 10
        for ln in body:
            d.text((M, y), ln, font=F(SERIF, 38), fill=(214, 220, 210), anchor="ls")
            y += 62
    pager(d, i, n, CREAM)
    if i == 1:
        swipe(d, GOLD)
    return im


def slide_cover(s, i, n):
    im = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(im)
    y = 330
    d.text((M, y), s.get("kicker", ""), font=F(SANS, 32), fill=GOLD, anchor="ls")
    d.line([(M, y + 34), (M + 80, y + 34)], fill=GOLD, width=2)
    y += 34 + 150
    for ln in lines_of(s.get("title", ""), 9):
        d.text((M, y), ln, font=F(SERIF_M, 92), fill=CREAM, anchor="ls")
        y += 136
    if s.get("sub"):
        y += 40
        for ln in lines_of(s["sub"], 22):
            d.text((M, y), ln, font=F(SERIF, 40), fill=(205, 212, 200), anchor="ls")
            y += 66
    d.text((M, H - 72), BRAND, font=F(SANS, 26), fill=GOLD, anchor="ls")
    pager(d, i, n, (205, 212, 200))
    if i == 1:
        swipe(d, GOLD)
    return im


def slide_text(s, i, n):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    y = 200
    d.text((M, y), s.get("kicker", ""), font=F(SANS, 30), fill=GOLD, anchor="ls")
    d.line([(M, y + 30), (M + 72, y + 30)], fill=GOLD, width=2)
    y += 30 + 110
    for ln in lines_of(s.get("title", ""), 14):
        d.text((M, y), ln, font=F(SERIF_M, 62), fill=GREEN, anchor="ls")
        y += 90
    y += 50
    fb = F(SERIF, 40)
    if s.get("items"):
        for k, item in enumerate(s["items"], 1):
            cx, cy = M + 26, y - 14
            d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=GOLD, width=2)
            d.text((cx, cy + 1), str(k), font=F(SERIF_M, 32), fill=GREEN, anchor="mm")
            for ln in lines_of(item, 19):
                d.text((M + 76, y), ln, font=fb, fill=INK, anchor="ls")
                y += 68
            y += 34
    for para in (s.get("body") or "").split("\n\n") if s.get("body") else []:
        for ln in lines_of(para, 21):
            d.text((M, y), ln, font=fb, fill=INK, anchor="ls")
            y += 70
        y += 30
    if s.get("note"):
        ny = max(y + 30, H - 150 - 46 * (len(lines_of(s["note"], 30)) - 1))
        for ln in lines_of(s["note"], 30):
            d.text((M, ny), ln, font=F(SANS, 28), fill=SUB, anchor="ls")
            ny += 46
    d.text((M, H - 72), BRAND, font=F(SANS, 26), fill=GOLD, anchor="ls")
    pager(d, i, n, SUB)
    return im


def slide_product(s, i, n):
    im = Image.new("RGB", (W, H), CREAM)
    ph = 800
    photo = cover_crop(open_photo(s["photo"], s.get("box")), W, ph, s.get("focus", 0.5), s.get("focus_x", 0.5))
    im.paste(photo, (0, 0))
    d = ImageDraw.Draw(im)
    y = ph + 86
    d.text((M, y), s.get("kicker", "今回使ったもの"), font=F(SANS, 28), fill=GOLD, anchor="ls")
    y += 70
    for ln in lines_of(s["name"], 19):
        d.text((M, y), ln, font=F(SERIF_M, 46), fill=GREEN, anchor="ls")
        y += 66
    if s.get("sub"):
        y += 6
        for ln in lines_of(s["sub"], 26):
            d.text((M, y), ln, font=F(SERIF, 32), fill=SUB, anchor="ls")
            y += 52
    bx0, by0, bx1, by1 = M, H - 168, W - M, H - 76
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=46, fill=GREEN)
    d.text(((bx0 + bx1) // 2, (by0 + by1) // 2), s.get("cta", "ストアはプロフィールのリンクから"),
           font=F(SANS, 32), fill=CREAM, anchor="mm")
    pager(d, i, n, CREAM)
    return im


RENDER = {"photo": slide_photo, "cover": slide_cover, "text": slide_text, "product": slide_product}


def build(post):
    out = []
    n = len(post["slides"])
    month = post["date"][:7]
    os.makedirs(f"images/{month}", exist_ok=True)
    for i, s in enumerate(post["slides"], 1):
        im = RENDER[s["kind"]](s, i, n)
        path = f"images/{month}/c-{post['date']}-{i}.jpg"
        im.save(path, "JPEG", quality=90, optimize=True, progressive=True)
        out.append(path)
    return out


if __name__ == "__main__":
    for post in json.load(open(sys.argv[1], encoding="utf-8")):
        print(post["date"], build(post))
