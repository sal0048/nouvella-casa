"""Publishing queue for out/reels (10 reels per campaign day).

    python3 reels_queue.py next              # JSON of the reel to publish now, or {} if none
    python3 reels_queue.py mark ID MEDIA_ID PERMALINK
    python3 reels_queue.py status

Every unpublished reel is due now (the user dropped the 10-a-day cap); pacing
comes from the routine and Instagram's 100-posts-per-24h quota. The video URL is
pinned to the last commit that changed the file (Meta fetches it from GitHub raw).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAN = HERE / "out" / "reels" / "manifest.json"
PUB = HERE / "out" / "reels" / "published.json"   # kept apart: make_100 rewrites MAN
REPO = "sal0048/nouvella-casa"
START = date(2026, 9, 28)
ALGIERS = timezone(timedelta(hours=1))


def load():
    rows = json.loads(MAN.read_text())
    pub = json.loads(PUB.read_text()) if PUB.exists() else {}
    for r in rows:
        if r["id"] in pub:
            r.update(pub[r["id"]], status="published")
    return rows, pub


def today_day():
    return (datetime.now(ALGIERS).date() - START).days + 1


def raw_url(fname):
    rel = f"marketing/video-variants/out/reels/{fname}"
    sha = subprocess.run(["git", "log", "-1", "--format=%h", "--", ":(top)" + rel],
                         cwd=HERE, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", ":(top)" + rel],
                           cwd=HERE, capture_output=True, text=True).stdout.strip()
    if not sha or dirty:
        raise SystemExit(f"{fname} is not committed and pushed in its final version yet")
    return f"https://raw.githubusercontent.com/{REPO}/{sha}/{rel}"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    rows, pub = load()
    if cmd == "next":
        due = [r for r in rows if r["status"] == "ready"]   # user: publish all, no daily cap
        if not due:
            print("{}")
            return
        r = due[0]
        print(json.dumps({"id": r["id"], "video_url": raw_url(r["file"]), "caption": r["caption"]},
                         ensure_ascii=False))
    elif cmd == "mark":
        rid, media_id, link = sys.argv[2:5]
        assert any(r["id"] == rid for r in rows), rid
        pub[rid] = {"media_id": media_id, "permalink": link,
                    "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1))
    else:
        pub = [r for r in rows if r["status"] == "published"]
        print(f"day {today_day()}: {len(pub)}/{len(rows)} published")
        for r in pub[-10:]:
            print(r["id"], r["treatment"], r.get("permalink"))


if __name__ == "__main__":
    main()
