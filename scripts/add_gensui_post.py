import json

IMAGES = ["images/2026-09-gensui/01.jpg", "images/2026-09-gensui/02.jpg", "images/2026-09-gensui/03.jpg", "images/2026-09-gensui/04.jpg", "images/2026-09-gensui/05.jpg"]
CAPTION = "捨てられていた水を、主役に。\n\n青森ヒバを蒸留すると、精油と一緒に大量の蒸留水が生まれます。かつては捨てられていた水です。\n\n湯に注ぐと当たりがやわらぎ、湯気とともに香りが立つ。それだけの理由で、希釈も添加もせずそのまま瓶に詰めることにしました。\n\n成分は青森ひば蒸留水。ただ一つです。\n\n200Lの浴槽に200ml。1本で約9回分。\nオンラインストアは近日公開です。"
TAGS = ["#青森ヒバ", "#ひばの源水", "#芳香蒸留水", "#入浴剤", "#ひばの森", "#大間", "#無添加"]
POST = {"account": "hibanomori", "publish_at": "2026-09-01T12:00:00+09:00", "type": "carousel", "pillar": "A", "images": IMAGES, "caption": CAPTION, "hashtags": TAGS, "status": "approved"}
posts = json.load(open("posts-scheduled.json", encoding="utf-8"))
have = {p["images"][0] for p in posts if p.get("images")}
add = [] if POST["images"][0] in have else [POST]
posts.extend(add)
json.dump(posts, open("posts-scheduled.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("added", len(add), "total", len(posts))
