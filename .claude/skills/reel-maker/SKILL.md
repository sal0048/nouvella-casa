---
name: reel-maker
description: Make a professional 9:16 product Reel for Nouvella Casa from Sal's real phone footage, using Remotion (motion text, callouts, punch-in cuts, animated end card) and ffmpeg (stabilize, grade). Use when Sal sends a product video or asks for a reel, ad video, or "مونتاج".
---

# Reel maker (Remotion + ffmpeg)

Template project: `tools/reel-remotion/` (Remotion 4, React). Last output: `videos/nouvella_table_v3.mp4`.

## 1. Prepare footage (ffmpeg)
```bash
ffmpeg -i in.mp4 -vf vidstabdetect=shakiness=6:result=tr.trf -f null -
ffmpeg -i in.mp4 -vf "vidstabtransform=input=tr.trf:smoothing=30:zoom=4,scale=1080:1920:flags=lanczos,eq=contrast=1.08:saturation=1.15,unsharp=5:5:0.6" -an main.mp4
```
Then look at a contact sheet (`fps=1,scale=180:-2,tile=6x2`) and pick shot start times.

## 2. Build
```bash
cd <scratch>/rm && npm init -y && npm i remotion @remotion/cli @remotion/renderer @remotion/bundler react react-dom
cp -r tools/reel-remotion/src . ; mkdir public; cp main.mp4 public/table.mp4
cp fonts/Cairo-Bold.ttf fonts/Cairo.ttf fonts/Playfair.ttf public/   # Cairo from npm @fontsource/cairo
```
Edit `src/Reel.tsx`: shot times (`from` in seconds), callout coordinates (1080x1920 space), texts.

## 3. Check, then render
```bash
B=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
npx remotion still src/index.ts TableReel out/s.png --frame=130 --browser-executable=$B
npx remotion render src/index.ts TableReel out/reel.mp4 --browser-executable=$B --codec=h264 --crf=18
```
Always view stills before the full render: callout dots must sit ON the product.

## Rules
- Structure: hook (0–2.7s) → 2 detail shots with callouts → benefit line → end card CTA "ابعتلنا مساج" + "الدفع عند الاستلام".
- Brand: NAVY #1B2A4A, GOLD #C9A84C, CREAM #F7F3EE, Cairo (Arabic), Playfair (logo).
- Only true claims: never write a material (marble, solid wood), stock, delivery time or discount that Sal has not confirmed.
- No music baked in: Sal adds a trending sound in Instagram (better reach).
- Remotion license: free for companies with ≤3 employees; above that a company license is needed.
