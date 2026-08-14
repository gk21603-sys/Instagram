import json

extra = json.load(open("posts-nomori.json", encoding="utf-8"))
posts = json.load(open("posts-scheduled.json", encoding="utf-8"))
have = {p["images"][0] for p in posts if p.get("images")}
add = [e for e in extra if e["images"][0] not in have]
posts.extend(add)
json.dump(posts, open("posts-scheduled.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("added", len(add), "total", len(posts))
