import json

DATES = ["2026-08-19", "2026-08-23", "2026-08-26", "2026-08-30", "2026-09-02", "2026-09-06", "2026-09-09", "2026-09-13", "2026-09-16", "2026-09-20", "2026-09-23"]
posts = json.load(open("posts-scheduled.json", encoding="utf-8"))
targets = [p for p in posts if p["account"] == "hibasoken" and p["status"] == "approved"]
pairs = list(zip(targets, DATES))
noop = [p.__setitem__("publish_at", d + "T12:00:00+09:00") for p, d in pairs]
json.dump(posts, open("posts-scheduled.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("rescheduled", len(pairs), "of", len(targets))
