"""Phone page to post the Gemini reels by hand (Instagram has no draft API).

    python3 drafts_page.py      # -> out/drafts/reels-drafts.html

One card per unpublished reel: poster frame, video link (GitHub raw, pinned
commit), caption with a copy button, and a local "done" tick.
"""

from __future__ import annotations

import base64
import html
import json
import subprocess
from pathlib import Path

import reels_queue as Q
from make_variants import FF

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "drafts"
TREAT = {"original": "أصلي", "slow": "بطيء", "zoom": "زوم", "zoom-cool": "زوم بارد", "warm": "دافي",
         "cool-contrast": "بارد مع تباين", "fast": "سريع", "late-start": "بداية متأخرة",
         "zoom-warm": "زوم دافي", "fast-bright": "سريع مضوي"}


def poster(mp4):
    jpg = subprocess.run([FF, "-v", "error", "-ss", "1.5", "-i", str(mp4), "-frames:v", "1",
                          "-vf", "scale=160:-2", "-q:v", "7", "-f", "image2", "-"],
                         capture_output=True, check=True).stdout
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


def main():
    rows, _ = Q.load()
    todo = [r for r in rows if r["status"] != "published"]
    cards = []
    for r in todo:
        url = Q.raw_url(r["file"])
        e = html.escape
        cards.append(f"""
<article class="card" data-id="{r['id']}">
  <img class="thumb" src="{poster(HERE / 'out' / 'reels' / r['file'])}" alt="" width="160" height="284">
  <div class="body">
    <div class="meta"><span class="rid">{r['id']}</span><span class="chip">{e(TREAT.get(r['treatment'], r['treatment']))}</span><span class="dur">{r['duration']:.0f} ث</span></div>
    <p class="hook">{e(r['hook'])}</p>
    <pre class="cap" id="cap-{r['id']}">{e(r['caption'])}</pre>
    <div class="acts">
      <a class="btn" href="{e(url)}" target="_blank" rel="noopener">حمّل الفيديو</a>
      <button class="btn" type="button" data-copy="cap-{r['id']}">انسخ الكابشن</button>
      <label class="done"><input type="checkbox" id="done-{r['id']}"> تحط</label>
    </div>
  </div>
</article>""")
    tpl = (HERE / "drafts_page.tpl.html").read_text()
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / "reels-drafts.html"
    dst.write_text(tpl.replace("{{COUNT}}", str(len(todo))).replace("{{CARDS}}", "".join(cards)))
    print(dst, len(todo), f"{dst.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
