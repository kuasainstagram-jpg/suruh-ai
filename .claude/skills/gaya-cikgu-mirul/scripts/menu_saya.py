# -*- coding: utf-8 -*-
"""Menu Gaya Saya — the user's own style menu, built from the videos Claude has edited for them.

After every finished edit, save a 5-second preview + the exact recipe (codes, tema, cahaya, plan) so next time the
user picks a card from THEIR OWN past videos and gets the same look again.

usage:
  python3 menu_saya.py add <project_dir> <final.mp4> "<nama>" [--out gaya-saya]
  python3 menu_saya.py build [--out gaya-saya]
Writes <out>/menu.json, <out>/clips/*.mp4|jpg and <out>/index.html (open it, or ask Claude to show it).
"""
import datetime, html, json, os, subprocess, sys

args = sys.argv[1:]
out = "gaya-saya"
if "--out" in args: k = args.index("--out"); out = args[k + 1]; del args[k:k + 2]
os.makedirs(f"{out}/clips", exist_ok=True)
MJ = f"{out}/menu.json"
menu = json.load(open(MJ)) if os.path.exists(MJ) else []


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


def recipe(plan):
    codes = sorted({i["code"] for i in plan.get("items", []) if not str(i.get("code", "")).startswith("B")})
    parts = []
    if plan.get("tema"): parts.append(f"Tema: {plan['tema']}")
    if plan.get("cahaya"): parts.append(f"Cahaya: {plan['cahaya']}")
    if codes: parts.append("Gaya: " + " ".join(codes))
    if plan.get("captions") and isinstance(plan["captions"], str): parts.append(f"Caption: {plan['captions']}")
    return parts


def add(proj, final, name):
    plan = json.load(open(f"{proj}/plan.json")) if os.path.exists(f"{proj}/plan.json") else {}
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); d = dur(final)
    start = max(0.0, min(d * .3, d - 5.2))                                     # a lively 5 s from the first third
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.2f}", "-i", final, "-t", "5", "-an", "-vf", "scale=360:640,fps=30",
                    "-c:v", "libx264", "-crf", "28", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{out}/clips/{stamp}.mp4"], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start + 1.5:.2f}", "-i", final, "-frames:v", "1", "-vf", "scale=360:640", "-q:v", "4", f"{out}/clips/{stamp}.jpg"], check=True)
    keep = {k: plan[k] for k in ("tema", "cahaya", "captions", "gold", "keywords", "bilik", "cta") if k in plan}
    keep["items"] = [{k: v for k, v in i.items() if k in ("code",)} for i in plan.get("items", [])]
    menu.insert(0, dict(id=stamp, name=name, date=datetime.date.today().isoformat(), recipe=recipe(plan), plan=keep))
    json.dump(menu, open(MJ, "w"), ensure_ascii=False, indent=1)


def build():
    e = html.escape
    cards = "".join(f'''<article class="card"><div class="vid"><video src="clips/{m['id']}.mp4" poster="clips/{m['id']}.jpg" muted loop playsinline preload="none"></video></div>
<div class="meta"><span class="date">{e(m['date'])}</span><h3>{e(m['name'])}</h3><p>{" · ".join(e(x) for x in m['recipe']) or "Gaya automatik"}</p>
<button type="button" data-p="{e(json.dumps(m, ensure_ascii=False))}">Salin arahan — buat sama</button></div></article>''' for m in menu)
    page = f'''<!doctype html><html lang="ms"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Menu Gaya Saya</title>
<style>:root{{--bg:#0A0B0F;--panel:#13151C;--line:#262A35;--ink:#F2F3F5;--mute:#9AA3B2;--gold:#F5B82E}}
@media (prefers-color-scheme:light){{:root:not([data-theme="dark"]){{--bg:#F6F5F1;--panel:#fff;--line:#E4E1D8;--ink:#14161D;--mute:#5E6573}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:22px 16px 60px}}h1{{font:900 32px/1.1 system-ui;margin:0}}h1 span{{color:var(--gold)}}.sub{{color:var(--mute);margin:8px 0 18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}}.card{{background:var(--panel);border:1.5px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column}}
.vid{{aspect-ratio:9/16;background:#000}}video{{width:100%;height:100%;object-fit:cover;display:block}}.meta{{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;flex:1}}
.date{{font:700 11px ui-monospace,monospace;color:var(--mute)}}h3{{margin:0;font-size:15px}}p{{margin:0;color:var(--mute);font-size:13px;flex:1}}
button{{min-height:44px;border-radius:12px;border:0;background:var(--gold);color:#111;font:800 13.5px system-ui;cursor:pointer}}.empty{{color:var(--mute);padding:40px 0;text-align:center}}
.toast{{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:12px;font-weight:700;opacity:0;transition:opacity .2s}}</style></head>
<body><div class="wrap"><h1>Menu <span>Gaya Saya</span></h1><p class="sub">{len(menu)} video yang Claude dah edit untuk anda. Pilih satu → <b>Salin arahan</b> → tampal dalam Claude bersama video baharu, hasilnya sama gaya.</p>
<div class="grid">{cards or '<p class="empty">Belum ada lagi — video pertama anda akan muncul di sini selepas siap diedit.</p>'}</div></div><div class="toast" id="t">Disalin ✓</div>
<script>
const io=new IntersectionObserver(es=>es.forEach(e=>{{const v=e.target;if(e.isIntersecting){{v.preload="auto";v.play().catch(()=>{{}})}}else v.pause()}}),{{rootMargin:"200px"}});
document.querySelectorAll("video").forEach(v=>io.observe(v));
document.querySelectorAll("button[data-p]").forEach(b=>b.onclick=async()=>{{const m=JSON.parse(b.dataset.p);
const msg=['Edit video saya guna skill "30 Gaya Video Cikgu Mirul", SAMA GAYA seperti video "'+m.name+'" ('+m.date+') dalam Menu Gaya Saya.'].concat(m.recipe).concat(["Resipi penuh: gaya-saya/menu.json → id "+m.id,"Video: (link Google Drive / saya upload dalam chat ini)"]).join("\\n");
try{{await navigator.clipboard.writeText(msg)}}catch(e){{prompt("Salin teks ini:",msg)}}const t=document.getElementById("t");t.style.opacity=1;setTimeout(()=>t.style.opacity=0,1400)}});
</script></body></html>'''
    open(f"{out}/index.html", "w").write(page)
    return f"{out}/index.html"


if __name__ == "__main__":
    if args and args[0] == "add": add(args[1], args[2], args[3] if len(args) > 3 else "Video saya"); print(build())
    else: print(build())
