"""Render the 100-reel publishing plan as one RTL HTML page.

    python3 schedule_page.py OUT.html

Planned times replay the Routine: a slot at HH:07 (Africa/Algiers) for HH in
SLOT_HOURS, each slot publishes the first ready reel whose day <= campaign day.
"""

from __future__ import annotations

import html
import sys
from datetime import datetime, timedelta

import make_100 as X
import reels_queue as Q

SLOT_HOURS = range(10, 24)
ANGLE_AR = {
    "luxury": "فخامة", "price-value": "سعر / قيمة", "unique": "تميّز",
    "social-proof": "شهادة الناس", "craft-cnc": "صنعة CNC", "cheap-makeover": "تجديد بلا مصاريف",
    "workshop-direct": "من الورشة مباشرة", "price-compare": "مقارنة بالماركات",
    "curiosity": "فضول", "problem": "مشكل الزبون",
}
TREAT_AR = {
    "original": "أصلي", "slow": "بطيء", "zoom": "زوم", "zoom-cool": "زوم + بارد",
    "warm": "دافي", "cool-contrast": "بارد + كونتراست", "fast": "سريع", "late-start": "بداية متأخرة",
    "zoom-warm": "زوم + دافي", "fast-bright": "سريع + ضاوي",
}
DAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def plan(rows, now):
    """Replay future slots; return {id: datetime} for unpublished reels."""
    ready = [r for r in rows if r["status"] != "published"]
    out, t = {}, now.replace(minute=7, second=0, microsecond=0)
    if t <= now:
        t += timedelta(hours=1)
    while ready:
        if t.hour in SLOT_HOURS:
            day = (t.date() - Q.START).days + 1
            due = [r for r in ready if r["day"] <= day]
            if due:
                out[due[0]["id"]] = t
                ready.remove(due[0])
        t += timedelta(hours=1)
    return out


def main():
    rows, _ = Q.load()
    now = datetime.now(Q.ALGIERS)
    when = plan(rows, now)
    for r in rows:
        r["angle"] = X.ANGLES[r["slot"] - 1][0]
        r["hook"] = X.ANGLES[r["slot"] - 1][1] if r["status"] != "published" else r["hook"]
        if r["status"] == "published":
            r["at"] = datetime.fromisoformat(r["published_at"]).astimezone(Q.ALGIERS)
        else:
            r["at"] = when[r["id"]]
    rows.sort(key=lambda r: r["at"])
    done = sum(r["status"] == "published" for r in rows)
    last = rows[-1]["at"]

    groups: dict = {}
    for r in rows:
        groups.setdefault(r["at"].date(), []).append(r)

    parts = []
    for d, items in groups.items():
        pub = sum(i["status"] == "published" for i in items)
        parts.append(f'<section class="day"><header><h2>{DAYS_AR[d.weekday()]} '
                     f'<span class="num">{d:%d/%m}</span></h2>'
                     f'<span class="meta">{len(items)} فيديو · {pub} منشور</span></header><ol>')
        for i in items:
            live = i["status"] == "published"
            link = (f'<a href="{html.escape(i["permalink"])}">شوف الـ Reel</a>' if live
                    else '<span class="wait">مبرمج</span>')
            parts.append(
                f'<li class="{"live" if live else ""}">'
                f'<time class="num">{i["at"]:%H:%M}</time>'
                f'<div class="body"><p class="hook">{html.escape(i["hook"])}</p>'
                f'<p class="tags"><span class="angle">{ANGLE_AR[i["angle"]]}</span>'
                f'<span>{TREAT_AR.get(i["treatment"], i["treatment"])}</span>'
                f'<span class="num">#{i["id"]}</span></p></div>'
                f'<div class="state">{link}</div></li>')
        parts.append("</ol></section>")

    page = f"""<title>جدول الـ Reels</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Readex+Pro:wght@500;700&display=swap">
<style>
/* layout: one reading column, days as sections, each reel a time-stamped row */
:root {{
  --bg: #f6f4f1; --surface: #ffffff; --fg: #231d18; --muted: #75695e;
  --line: #e4ddd4; --accent: #9a5b2e; --live: #2f7a4f; --live-bg: #e6f2ea;
  --f-display: "Readex Pro", "IBM Plex Sans Arabic", system-ui, sans-serif;
  --f-body: "IBM Plex Sans Arabic", system-ui, sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #171412; --surface: #211c19; --fg: #efe8e1; --muted: #a89a8d;
  --line: #342c26; --accent: #d9955f; --live: #6fca94; --live-bg: #1d2e24; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #171412; --surface: #211c19; --fg: #efe8e1; --muted: #a89a8d;
  --line: #342c26; --accent: #d9955f; --live: #6fca94; --live-bg: #1d2e24; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-body); font-size: 15px; line-height: 1.6; }}
main {{ max-width: 720px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 48px; display: grid; gap: 28px; }}
h1, h2 {{ font-family: var(--f-display); text-wrap: balance; margin: 0; }}
h1 {{ font-size: 1.7rem; }}
.lead {{ color: var(--muted); margin: 6px 0 0; }}
.num {{ font-variant-numeric: tabular-nums; direction: ltr; unicode-bidi: isolate; }}
.summary {{ display: flex; flex-wrap: wrap; gap: 10px 24px; margin-top: 14px; }}
.summary b {{ font-family: var(--f-display); font-size: 1.25rem; color: var(--accent); }}
.progress {{ height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; margin-top: 12px; }}
.progress i {{ display: block; height: 100%; background: var(--live); width: {done}%; }}
.day header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
  border-bottom: 1px solid var(--line); padding-bottom: 6px; }}
.day h2 {{ font-size: 1.15rem; }}
.meta {{ color: var(--muted); font-size: .85rem; }}
ol {{ list-style: none; margin: 0; padding: 0; }}
li {{ display: grid; grid-template-columns: 3.4rem 1fr auto; gap: 12px; align-items: start;
  padding: 12px 0; border-bottom: 1px solid var(--line); }}
li.live {{ background: var(--live-bg); margin-inline: -10px; padding-inline: 10px; border-radius: 8px; border-bottom-color: transparent; }}
time {{ color: var(--muted); font-weight: 600; padding-top: 2px; }}
.body {{ min-width: 0; }}
.hook {{ margin: 0; font-weight: 500; }}
.tags {{ margin: 4px 0 0; display: flex; flex-wrap: wrap; gap: 6px; font-size: .78rem; color: var(--muted); }}
.tags span {{ border: 1px solid var(--line); border-radius: 999px; padding: 0 8px; }}
.tags .angle {{ color: var(--accent); border-color: var(--accent); }}
.state {{ font-size: .82rem; padding-top: 2px; white-space: nowrap; }}
.state a {{ color: var(--live); font-weight: 600; }}
.state a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.wait {{ color: var(--muted); }}
.note {{ color: var(--muted); font-size: .85rem; margin: 0; }}
</style>
<main dir="rtl" lang="ar">
  <div>
    <h1>جدول الـ 100 Reel</h1>
    <p class="lead">nouvella_casa · Trial Reels · فيديو كل ساعة من 10:07 حتى 23:07 بتوقيت الجزائر</p>
    <div class="summary">
      <span>تنشرو: <b class="num">{done}</b> من <b class="num">100</b></span>
      <span>آخر فيديو: <b class="num">{last:%d/%m}</b></span>
    </div>
    <div class="progress" role="img" aria-label="{done} من 100 منشور"><i></i></div>
  </div>
  {''.join(parts)}
  <p class="note">الأوقات المبرمجة تقديرية: إذا تفوت موعد، الفيديوهات لي بعدو يتأخرو بموعد. آخر تحديث <span class="num">{now:%d/%m %H:%M}</span>.</p>
</main>
"""
    open(sys.argv[1], "w").write(page)
    print(done, "published; last", last)


if __name__ == "__main__":
    main()
