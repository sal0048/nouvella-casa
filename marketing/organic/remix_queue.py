"""Publishing queue for the organic remixes (10 per campaign day).

    python3 remix_queue.py next        # render + commit + push the due recipe; JSON or {}
    python3 remix_queue.py mark ID MEDIA_ID PERMALINK
    python3 remix_queue.py status

Every unpublished recipe is due now (the user dropped the 10-a-day cap). `next`
renders it, commits and pushes the mp4, and pins the video URL to that commit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import make_remix as R

HERE = Path(__file__).resolve().parent
MAN = R.OUT / "remix_manifest.json"
PUB = R.OUT / "remix_published.json"
REPO = "sal0048/nouvella-casa"
BRANCH = "claude/scrapling-anasghalion-ez2ljy"
START = date(2026, 9, 29)
ALGIERS = timezone(timedelta(hours=1))


def git(*a):
    return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()


def load():
    rows = json.loads(MAN.read_text())
    pub = json.loads(PUB.read_text()) if PUB.exists() else {}
    for r in rows:
        r["status"] = "published" if r["id"] in pub else "ready"
        r.update(pub.get(r["id"], {}))
    return rows, pub


def today_day():
    return (datetime.now(ALGIERS).date() - START).days + 1


def ensure_pushed(rec):
    dst = R.OUT / "remix" / rec["file"]
    rel = str(dst.relative_to(Path(git("rev-parse", "--show-toplevel"))))
    if not dst.exists():
        R.render(rec["id"])
    if git("status", "--porcelain", "--", ":(top)" + rel) or not git("log", "-1", "--format=%h", "--", ":(top)" + rel):
        git("add", ":(top)" + rel)
        git("commit", "-qm", f"Remix: render {rec['id']} for publishing")
        git("push", "-q", "origin", BRANCH)
    sha = git("log", "-1", "--format=%h", "--", ":(top)" + rel)
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
        print(json.dumps({"id": r["id"], "video_url": ensure_pushed(r), "caption": r["caption"]},
                         ensure_ascii=False))
    elif cmd == "mark":
        rid, media_id, link = sys.argv[2:5]
        assert any(r["id"] == rid for r in rows), rid
        pub[rid] = {"media_id": media_id, "permalink": link,
                    "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1))
    else:
        print(f"remix day {today_day()}: {len(pub)}/{len(rows)} published")


if __name__ == "__main__":
    main()
