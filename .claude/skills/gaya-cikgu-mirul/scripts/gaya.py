"""Gaya Cikgu Mirul (Gaya 2.0) — build a HyperFrames project from an edit plan.

python3 gaya.py <project dir> <plan.json>

The project dir must already hold assets/main.mp4 + assets/main.wav (prep.py) and words.json (transcribe.py).
Plan times are in SOURCE seconds (as in words.json). See ../catalog.md for every style and its params.
"""
import json, math, os, re, shutil, subprocess, sys, wave

import numpy as np

HERE = os.environ.get("GAYA_HOME", os.path.dirname(os.path.abspath(__file__)))
PROJ, PLANF = sys.argv[1], sys.argv[2]
PLAN = json.load(open(PLANF))
WORDS = json.load(open(f"{PROJ}/words.json")) if os.path.exists(f"{PROJ}/words.json") else []
PROBE = json.load(open(f"{PROJ}/probe.json"))
COMP = f"{PROJ}/compositions"; A = f"{PROJ}/assets"
os.makedirs(COMP, exist_ok=True)
for f in ("hyperframes.json",):
    shutil.copy(f"{HERE}/../template/{f}", f"{PROJ}/{f}")
shutil.copy(f"{HERE}/../template/assets/gsap.min.js", f"{A}/gsap.min.js")
if os.path.isdir(f"{HERE}/../template/assets/fonts"): shutil.copytree(f"{HERE}/../template/assets/fonts", f"{A}/fonts", dirs_exist_ok=True)
json.dump({"id": "gaya", "name": PLAN.get("title", "gaya")}, open(f"{PROJ}/meta.json", "w"))

W, H = 1080, 1920
GOLD, ORANGE, INK = PLAN.get("gold", "#F5B82E"), PLAN.get("accent", "#FF5A1F"), "#F5F7FA"
SRC_DUR = PROBE["duration"]
def r(x): return round(float(x), 3)
def J(o): return json.dumps(o, ensure_ascii=False)
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def gold(s): return re.sub(r"\*\*(.+?)\*\*", rf'<span style="color:{GOLD}">\1</span>', esc(s))   # **word** -> gold


# ---------------------------------------------------------------- timeline offset (H04 freeze delays the footage)
PREROLL = {"H04", "P31"}   # styles that play before the footage starts (P31 lives in the premium pack)
FREEZE = next((i for i in PLAN.get("items", []) if i["code"] in PREROLL), None)
OFF = float(FREEZE.get("dur", 1.5 if FREEZE["code"] == "H04" else 1.8)) if FREEZE else 0.0
def T(s): return r(float(s) + OFF)                 # source time -> output time
# free version ends with a short sign-off card "Diedit dengan Suruh AI · suruhaieditvideogunaphone.com" (an add-on pack can turn it off)
PENUTUP = PLAN.get("penutup", not os.path.exists(f"{HERE}/advanced.py"))
OUTRO = 1.8 if PENUTUP else 0.0
TOTAL = r(SRC_DUR + OFF + OUTRO)

CSS = f"""
@font-face{{font-family:'Noto Color Emoji';src:local('Noto Color Emoji')}}
#root{{position:absolute;inset:0;overflow:hidden;font-family:'Inter',sans-serif;color:{INK}}}
.ab{{position:absolute}}
.glass{{position:absolute;border-radius:32px;background:rgba(12,14,20,.86);border:1.5px solid rgba(255,255,255,.14);box-shadow:0 30px 80px rgba(0,0,0,.55);backdrop-filter:blur(22px)}}
.mont{{font-family:'Montserrat',sans-serif;font-weight:800;letter-spacing:-.01em;line-height:1.04}}
.mono{{font-family:'Space Mono',monospace;letter-spacing:.16em;text-transform:uppercase}}
.scrimT{{position:absolute;left:0;right:0;top:0;height:640px;background:linear-gradient(180deg,rgba(5,6,10,.85),rgba(5,6,10,0))}}
.scrimB{{position:absolute;left:0;right:0;bottom:0;height:820px;background:linear-gradient(180deg,rgba(5,6,10,0),rgba(5,6,10,.9) 55%)}}
.dim{{position:absolute;inset:0;background:rgba(5,6,10,.62)}}
.cap{{position:absolute;left:40px;right:40px;text-align:center}}
.ol{{-webkit-text-stroke:14px #000;paint-order:stroke fill}}
.sticker{{position:absolute;background:#fff;color:#0b0b0b;border:8px solid #0b0b0b;border-radius:34px;box-shadow:14px 16px 0 #0b0b0b}}
.emo{{font-family:'Noto Color Emoji',sans-serif;line-height:1}}
"""
# "pop" grade: a bit more contrast, colour and a soft vignette so phone footage looks expensive
BASE = "main.mp4"
if PLAN.get("pop", True):
    BASE = "main_pop.mp4"
    if not os.path.exists(f"{A}/{BASE}") or os.path.getmtime(f"{A}/{BASE}") < os.path.getmtime(f"{A}/main.mp4"):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f"{A}/main.mp4", "-an", "-vf", "eq=contrast=1.10:saturation=1.25:brightness=0.012,vignette=angle=PI/5,format=yuv420p",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-g", "30", f"{A}/{BASE}"], check=True)
HOSTS = []      # (cid, start, dur, z)
SFX = []        # (kind, out_time, gain)


def scene(cid, start, dur, body, js, z=20, css=""):
    js = [l.replace("#R", f"#{cid}-w") for l in js if l]
    open(f"{COMP}/{cid}.html", "w").write(f"""<template>
  <style>{CSS}{css}</style>
  <div id="root" data-composition-id="{cid}" data-start="0" data-duration="{r(dur)}" data-width="{W}" data-height="{H}">
   <div id="{cid}-w" class="ab" style="inset:0">
{body}
   </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join("    " + l for l in js)}
    window.__timelines["{cid}"] = tl;
  </script>
</template>
""")
    HOSTS.append((cid, r(start), r(dur), z))


def fin(sel, at, y=30, d=.45, s=None):
    a = {"opacity": 0, "y": y}; b = {"opacity": 1, "y": 0, "duration": d, "ease": "power3.out"}
    if s is not None: a["scale"] = s; b["scale"] = 1
    return f'tl.fromTo("{sel}", {J(a)}, {J(b)}, {r(at)});'
def fout(sel, at, d=.3): return f'tl.to("{sel}", {J({"opacity": 0, "duration": d, "ease": "power2.in"})}, {r(max(0, at))});'
def pulse(sel, d, every=.35, prop="scale", a=1, b=1.06):
    n = max(1, int(d / every) - 1)
    return f'tl.fromTo("{sel}", {{{prop}:{a}}}, {{{prop}:{b},duration:{every},yoyo:true,repeat:{n},ease:"sine.inOut"}}, 0);'
def exit_all(d): return f'tl.to("#R", {{opacity:0,duration:.25,ease:"power2.in"}}, {r(d - .27)});'
def money(v, dec=2, prefix="RM "): return prefix + (f"{v:,.{dec}f}")
def words_in(a, b): return [w for w in WORDS if a - .02 <= w[1] < b]



# ---------------------------------------------------------------- Gaya 2.0 helpers
def slam(sel, at, rot=-2, s0=2.2):
    return f'tl.fromTo("{sel}", {{opacity:0,scale:{s0},rotation:{rot - 10}}}, {{opacity:1,scale:1,rotation:{rot},duration:.32,ease:"back.out(2.2)"}}, {r(at)});'
def shake(at, n=6, amp=12): return f'tl.fromTo("#R", {{x:0,y:0}}, {{x:{amp},y:{-amp * .6},duration:.04,yoyo:true,repeat:{n | 1},ease:"none",immediateRender:false}}, {r(at)});'
def bop(sel, at, k=.25): return f'tl.fromTo("{sel}", {{opacity:0,scale:.3,y:20}}, {{opacity:1,scale:1,y:0,duration:{k},ease:"back.out(3)"}}, {r(at)});'
def confetti(cid, at, x=540, y=1000, n=24):
    cols = [GOLD, ORANGE, "#3DD68C", "#3EC5FF", "#FF4FD8", "#fff"]
    html = "".join(f'<div id="{cid}-cf{k}" class="ab" style="left:{x}px;top:{y}px;width:{14 + k % 3 * 6}px;height:{22 + k % 4 * 5}px;background:{cols[k % 6]};border-radius:3px;opacity:0"></div>' for k in range(n))
    js = [f'tl.fromTo("#{cid}-cf{k}", {{opacity:1,x:0,y:0,rotation:0}}, {{opacity:0,x:{int(math.cos(k * 2.4) * (260 + k * 11))},y:{int(math.sin(k * 2.4) * 300 - 220)},rotation:{(k * 67) % 540 - 270},duration:1.1,ease:"power2.out"}}, {r(at)});' for k in range(n)]
    return html, js
def pill(txt, bg, fg="#111", size=44, rot=-2, id_=""):
    inner = f'<span class="mont" style="display:inline-block;background:{bg};color:{fg};font-size:{size}px;font-weight:900;padding:10px 28px 6px;border-radius:14px;border:5px solid #0b0b0b;box-shadow:6px 7px 0 #0b0b0b;transform:rotate({rot}deg)">{txt}</span>'
    return f'<span id="{id_}" style="display:inline-block">{inner}</span>' if id_ else inner

# ---------------------------------------------------------------- cut-out (person) + head-top finder
def cutout(s, d):
    """cut the person out of BASE for [s, s+d] once (cached, local free model); returns the asset file name"""
    tag = "" if BASE in ("main.mp4", "main_pop.mp4") else BASE.rsplit(".", 1)[0] + "_"
    name = tag + f"cut_{s:.2f}_{d:.2f}.webm".replace(".", "_", 2)
    out = f"{A}/{name}"
    if not os.path.exists(out):
        seg = f"{A}/_seg_{s:.2f}.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(s), "-i", f"{A}/{BASE}", "-t", str(d), "-an", "-c:v", "libx264", "-crf", "14", seg], check=True)
        subprocess.run(["npx", "hyperframes", "remove-background", seg, "-o", out, "--quality", "best"], check=True)
        os.remove(seg)
    return name


def head_top(cut_file, at=0.0):
    """y (px) of the top of the head in the cut-out, looking only at the middle 40% so a raised hand doesn't count"""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-c:v", "libvpx-vp9", "-ss", str(at), "-i", f"{A}/{cut_file}", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)[:, int(W * .3):int(W * .7), 3]
    rows = np.where((a > 128).sum(1) > 6)[0]
    return int(rows[0]) if len(rows) else int(H * .3)


# ================================================================ STYLE BLOCKS (overlay scenes)
def H01(i, cid, d):
    SFX.append(("boom", T(i["start"]), .45)); SFX.append(("riser", max(0, T(i["start"]) + d - .9), .18))
    words = re.findall(r"\*\*.+?\*\*|\S+", i["title"])
    spans = "".join(f'<span id="{cid}-w{k}" style="display:inline-block;margin:0 12px 10px;{"background:" + GOLD + ";color:#111;padding:2px 18px 0;border-radius:14px;-webkit-text-stroke:0" if w.startswith("**") else ""}">{esc(w.strip("*"))}</span>' for k, w in enumerate(words))
    js = [f'tl.fromTo("#{cid}-fl", {{opacity:1}}, {{opacity:0,duration:.35,ease:"power2.out"}}, 0);',
          f'tl.fromTo("#{cid}-b", {{opacity:0,scale:3,rotation:-14}}, {{opacity:1,scale:1,rotation:-3,duration:.28,ease:"back.out(2)"}}, .05);',
          f'tl.to("#{cid}-b", {{x:"+=8",duration:.05,yoyo:true,repeat:{max(1, int(d / .05) - 12)},ease:"none"}}, .4);',
          f'tl.fromTo("#{cid}-b", {{backgroundColor:"#FF2B2B"}}, {{backgroundColor:"{ORANGE}",duration:.18,yoyo:true,repeat:{max(1, int(d / .18) - 3)},ease:"none"}}, .4);']
    for k in range(len(words)):
        t = .35 + k * min(.16, 1.2 / max(1, len(words)))
        js.append(f'tl.fromTo("#{cid}-w{k}", {{opacity:0,scale:2.4,y:-30}}, {{opacity:1,scale:1,y:0,duration:.2,ease:"power4.out"}}, {r(t)});')
        SFX.append(("pop", T(i["start"]) + t, .14))
    js += [f'tl.to("#{cid}-t", {{scale:1.04,duration:{r(max(.4, d - 1.5))},ease:"none"}}, 1.4);', exit_all(d)]
    return f"""<div class="scrimT"></div><div class="scrimB"></div>
<div class="ab" style="left:0;right:0;top:190px;display:flex;justify-content:center"><div id="{cid}-b" class="mont" style="background:{ORANGE};color:#fff;font-size:66px;padding:16px 44px 12px;border-radius:18px;border:6px solid #fff;box-shadow:0 0 0 8px rgba(0,0,0,.35),0 20px 60px rgba(255,43,43,.6)"><span class="emo">🚨</span> {esc(i.get("badge", "JANGAN SCROLL DULU!"))}</div></div>
<div id="{cid}-t" class="ab mont ol" style="left:30px;right:30px;top:1240px;text-align:center;font-size:{i.get("size", 100)}px;font-weight:900;text-transform:uppercase;line-height:1.08">{spans}</div>
<div id="{cid}-fl" class="ab" style="inset:0;background:#fff"></div>""", js


def H02(i, cid, d):
    v = float(i["value"]); dec = int(i.get("decimals", 0)); pre = i.get("prefix", "RM")
    SFX.append(("riser", T(i["start"]), .16)); SFX.append(("boom", T(i["start"]) + 1.6, .4)); SFX.append(("ding", T(i["start"]) + 1.62, .3))
    ch, cj = confetti(cid, 1.6, 540, 520)
    return f"""<div class="dim" style="background:rgba(5,6,10,.6)"></div>{ch}
<div class="ab" style="left:0;right:0;top:300px;text-align:center">{pill(esc(i.get("label", "")), "#fff", size=40, id_=cid + "-l")}</div>
<div id="{cid}-n" class="ab mont ol" style="left:0;right:0;top:420px;text-align:center;font-size:{i.get("size", 190)}px;font-weight:900;color:{GOLD};white-space:nowrap">{pre}0</div>
<div id="{cid}-s" class="ab mont" style="left:40px;right:40px;top:680px;text-align:center;font-size:44px;color:#fff;text-shadow:0 4px 14px #000">{esc(i.get("sub", ""))}</div>""", \
        [bop(f"#{cid}-l", .05), fin(f"#{cid}-n", .05, y=0, d=.2, s=.6), fin(f"#{cid}-s", .4, y=20),
         f'(function(){{const o={{v:0}};const el=document.querySelector("#{cid}-n");const f=v=>"{pre}"+v.toLocaleString("en-US",{{minimumFractionDigits:{dec},maximumFractionDigits:{dec}}});'
         f'tl.set(o,{{v:0,onUpdate:()=>el.textContent=f(o.v)}},0);tl.to(o,{{v:{v},duration:1.5,ease:"power3.out",onUpdate:()=>el.textContent=f(o.v)}},.1);}})();',
         f'tl.to("#{cid}-n", {{scale:1.16,rotation:-3,duration:.12,yoyo:true,repeat:1,ease:"power2.out"}}, 1.6);', shake(1.6)] + cj + [exit_all(d)]


def H03(i, cid, d):
    ws = words_in(i["start"], i["start"] + d)
    gk = set(i.get("gold_words", []))
    isg = lambda w: re.sub(r"[^\w]", "", w).lower() in gk
    sp = "".join(f'<span id="{cid}-w{k}" class="ol" style="display:inline-block;margin:0 10px 12px;opacity:0;{"background:" + GOLD + ";color:#111;padding:0 16px;border-radius:14px;-webkit-text-stroke:0" if isg(w) else ""}">{esc(w)}</span>' for k, (w, _, _) in enumerate(ws))
    js = [slam(f"#{cid}-w{k}", t - i["start"] - .02, rot=0, s0=1.8) for k, (w, t, _) in enumerate(ws)]
    for k, (w, t, _) in enumerate(ws): SFX.append(("pop", t + OFF, .12))
    if ws: SFX.append(("boom", ws[0][1] + OFF, .3))
    q = f'<div id="{cid}-q" class="ab emo" style="right:70px;top:120px;font-size:160px;opacity:0">❓</div>' if i.get("emoji", True) else ""
    if q: js.append(f'tl.fromTo("#{cid}-q", {{opacity:0,scale:.2,rotation:-30}}, {{opacity:1,scale:1,rotation:12,duration:.35,ease:"back.out(3)"}}, {r(max(.2, (ws[-1][1] - i["start"]) if ws else .3))});')
    return f"""<div class="scrimT" style="height:900px"></div>{q}
<div class="ab mont" style="left:40px;right:40px;top:230px;text-align:center;font-size:{i.get("size", 88)}px;font-weight:900;text-transform:uppercase;line-height:1.1">{sp}</div>""", js + [exit_all(d)]


def H04(i, cid, d):
    SFX.append(("click", .02, .5)); SFX.append(("boom", .2, .35)); SFX.append(("whoosh", d - .3, .25))
    return f"""<img class="clip ab" src="assets/freeze.png" data-start="0" data-duration="{r(d)}" style="left:0;top:0;width:1080px;height:1920px" id="{cid}-img" />
<div class="dim" style="background:rgba(5,6,10,.5)"></div>
<div id="{cid}-t" class="ab" style="left:30px;right:30px;top:660px;text-align:center">
  <div>{pill(esc(i.get("kicker", "")), GOLD, size=40, rot=-3, id_=cid + "-k") if i.get("kicker") else ""}</div>
  <div id="{cid}-h" class="mont ol" style="font-size:{i.get("size", 120)}px;font-weight:900;text-transform:uppercase;margin-top:22px;line-height:1.02">{gold(i["title"])}</div></div>
<div id="{cid}-fl" class="ab" style="inset:0;background:#fff"></div>""", \
        [f'tl.fromTo("#{cid}-fl", {{opacity:1}}, {{opacity:0,duration:.3}}, 0);', f'tl.fromTo("#{cid}-img", {{scale:1}}, {{scale:1.14,duration:{r(d)},ease:"power2.out"}}, 0);',
         bop(f"#{cid}-k", .2) if i.get("kicker") else "", slam(f"#{cid}-h", .25, rot=-1), shake(.5, 4, 10), exit_all(d)]


def H05(i, cid, d):
    s = i["start"]
    SFX.append(("whoosh", T(s), .3)); SFX.append(("boom", T(s) + .9, .35))
    vid = lambda id_, src, ms, top: (f'<div class="ab" style="left:0;top:{top}px;width:1080px;height:956px;overflow:hidden"><video id="{id_}" class="clip" src="assets/{src}" data-start="0" data-duration="{r(d)}" data-media-start="{ms}" muted playsinline '
                                    f'style="position:absolute;left:0;top:0;width:1080px;height:956px;object-fit:cover;object-position:50% 30%"></video></div>')
    return f"""<div class="ab" style="inset:0;background:#000"></div>
{vid(cid + "-a", i["before"], i.get("before_start", 0), 0)}{vid(cid + "-b", BASE, s, 964)}
<div class="ab" style="left:0;top:946px;width:1080px;height:28px;background:#0b0b0b"></div><div class="ab" style="left:0;top:952px;width:1080px;height:16px;background:{GOLD}"></div>
<div id="{cid}-vs" class="ab emo" style="left:470px;top:890px;font-size:140px;opacity:0">⚡</div>
<div class="ab" style="left:40px;top:70px">{pill(esc(i.get("label1", "DULU")), "#2a2d35", "#fff", 70, -3, cid + "-l1")}</div>
<div id="{cid}-s1" class="ab mont ol" style="left:40px;top:200px;font-size:50px;font-weight:900">{esc(i.get("sub1", ""))}</div>
<div class="ab" style="left:40px;top:1030px">{pill(esc(i.get("label2", "SEKARANG")), GOLD, "#111", 70, 2, cid + "-l2")}</div>
<div id="{cid}-s2" class="ab mont ol" style="left:40px;top:1160px;font-size:50px;font-weight:900">{esc(i.get("sub2", ""))}</div>""", \
        [f'tl.fromTo("#{cid}-a", {{x:-1080}}, {{x:0,duration:.45,ease:"power3.out"}}, 0);', f'tl.fromTo("#{cid}-b", {{x:1080}}, {{x:0,duration:.45,ease:"power3.out"}}, .1);',
         slam(f"#{cid}-l1", .35, -3), fin(f"#{cid}-s1", .55, y=-10), slam(f"#{cid}-l2", .9, 2), fin(f"#{cid}-s2", 1.1, y=-10),
         f'tl.fromTo("#{cid}-vs", {{opacity:0,scale:.2,rotation:-40}}, {{opacity:1,scale:1,rotation:0,duration:.35,ease:"back.out(3)"}}, .6);', shake(.9, 4, 10), exit_all(d)]


def H06(i, cid, d):
    """big word BEHIND your head: pops in when you say it, the head covers ~60% of the letters"""
    s = float(i["start"]); word = esc(i["word"]).upper(); f = cutout(s, d); top = head_top(f, .1)
    fs = int(max(150, min(i.get("size", 420), W * .86 / (max(1, len(i["word"])) * .78))))
    box_top = int(max(60, top - .36 * fs))       # head top lands just over halfway up the letters
    SFX.append(("boom", T(s), .4)); SFX.append(("whoosh", T(s) - .12, .2))
    color = i.get("color", "#ffffff")
    return f"""<div id="{cid}-t" class="ab mont" style="left:0;right:0;top:{box_top}px;text-align:center;font-size:{fs}px;font-weight:900;line-height:1;letter-spacing:-.02em;color:{color};text-shadow:0 12px 40px rgba(0,0,0,.35);white-space:nowrap">{word}</div>
<video id="{cid}-v" class="clip" src="assets/{f}" data-start="0" data-duration="{r(d)}" muted playsinline style="position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover"></video>""", \
        [f'tl.fromTo("#{cid}-t", {{opacity:0,scale:.8}}, {{opacity:1,scale:1.05,duration:.14,ease:"power2.out"}}, 0);', f'tl.to("#{cid}-t", {{scale:1,duration:.08,ease:"power1.out"}}, .14);',
         f'tl.to("#R", {{opacity:0,duration:.2}}, {r(d - .22)});']


CHROME = "background-image:linear-gradient(180deg,#fff 0%,#e9e4da 38%,#8d8478 52%,#f4efe6 70%,#b9b0a3 100%);-webkit-background-clip:text;background-clip:text;color:transparent"


def T01(i, cid, d):
    SFX.append(("boom", T(i["start"]) + .05, .4)); SFX.append(("whoosh", T(i["start"]) + .8, .2))
    return f"""<div class="dim" style="background:rgba(4,5,8,.72)"></div>
<div id="{cid}-t" class="ab mont" style="left:20px;right:20px;top:740px;text-align:center;font-size:{i.get("size", 150)}px;font-weight:900;line-height:1"><div style="{CHROME}">{esc(i["line1"])}</div><div style="{CHROME};font-size:{int(i.get("size", 150) * .66)}px;margin-top:10px">{esc(i.get("line2", ""))}</div></div>
<div id="{cid}-sw" class="ab" style="left:-400px;top:680px;width:300px;height:460px;background:linear-gradient(100deg,transparent,rgba(255,255,255,.7),transparent);mix-blend-mode:overlay"></div>
<div id="{cid}-fl" class="ab" style="inset:0;background:#fff;opacity:0"></div>""", \
        [f'tl.fromTo("#{cid}-fl", {{opacity:.9}}, {{opacity:0,duration:.35}}, .05);', slam(f"#{cid}-t", .05, rot=0, s0=1.6), shake(.3, 4, 8),
         f'tl.to("#{cid}-t", {{scale:.95,duration:{r(max(.5, d - 1.2))},ease:"none"}}, 1.0);', f'tl.fromTo("#{cid}-sw", {{x:0}}, {{x:1700,duration:1.1,ease:"power2.inOut"}}, .7);', exit_all(d)]


def T02(i, cid, d):
    SFX.append(("boom", T(i["start"]) + .3, .45))
    return f"""<div class="dim" style="background:rgba(4,5,8,.5)"></div>
<div class="ab" style="left:0;right:0;top:800px;display:flex;justify-content:center"><div id="{cid}-b" class="mont" style="background:#fff;color:#0b0b0b;font-size:{i.get("size", 110)}px;font-weight:900;text-transform:uppercase;padding:26px 46px 14px;border-radius:24px;border:10px solid #0b0b0b;box-shadow:16px 18px 0 {ORANGE};text-align:center;line-height:1.02">{gold(i["text"]).replace("|", "<br>")}</div></div>""", \
        [slam(f"#{cid}-b", .3, rot=-3, s0=2.6), shake(.55, 7, 16), f'tl.to("#{cid}-b", {{scale:.95,duration:{r(max(.5, d - 1))},ease:"none"}}, .7);', exit_all(d)]


def T04(i, cid, d):
    SFX.append(("whoosh", T(i["start"]), .25)); SFX.append(("boom", T(i["start"]) + .15, .35))
    return f"""<div class="ab" style="inset:0;background:radial-gradient(ellipse 90% 60% at 50% 40%,#1c2233,#07090d 70%)"></div>
<div id="{cid}-n" class="ab mont" style="left:0;right:0;top:500px;text-align:center;font-size:330px;font-weight:900;color:{GOLD};-webkit-text-stroke:12px #0b0b0b;paint-order:stroke fill;text-shadow:16px 18px 0 #0b0b0b">{esc(i.get("num", "01"))}</div>
<div class="ab" style="left:40px;right:40px;top:900px;text-align:center">{pill(esc(i["line1"]), "#fff", "#0b0b0b", 92, -2, cid + "-t")}</div>
<div class="ab" style="left:40px;right:40px;top:1060px;text-align:center">{pill(esc(i.get("line2", "")), GOLD, "#0b0b0b", 92, 2, cid + "-t2") if i.get("line2") else ""}</div>""", \
        [slam(f"#{cid}-n", .1, rot=-4, s0=2.4), slam(f"#{cid}-t", .4, -2), slam(f"#{cid}-t2", .6, 2) if i.get("line2") else "", shake(.15, 4, 10),
         f'tl.to("#R", {{opacity:0,scale:.92,duration:.35}}, {r(d - .4)});']


def N01(i, cid, d):
    v = float(i["value"]); dec = int(i.get("decimals", 2)); pre = i.get("prefix", "RM ")
    SFX.append(("pop", T(i["start"]) + .1, .25)); SFX.append(("ding", T(i["start"]) + (2.0 if i.get("count", True) else .6), .3))
    cols = [GOLD, ORANGE, "#3DD68C", "#3EC5FF", "#FF4FD8", "#fff"]
    conf = "".join(f'<div id="{cid}-cf{k}" class="ab" style="left:530px;top:1420px;width:{14 + k % 3 * 6}px;height:{22 + k % 4 * 5}px;background:{cols[k % 6]};border-radius:3px;opacity:0"></div>' for k in range(26))
    t_hit = 2.0 if i.get("count", True) else .6
    cjs = [f'tl.fromTo("#{cid}-cf{k}", {{opacity:1,x:0,y:0,rotation:0}}, {{opacity:0,x:{int(math.cos(k * 2.4) * (260 + k * 11))},y:{int(math.sin(k * 2.4) * 300 - 220)},rotation:{(k * 67) % 540 - 270},duration:1.1,ease:"power2.out"}}, {r(t_hit)});' for k in range(26)]
    return f"""<div class="scrimB"></div>{conf}
<div id="{cid}-c" class="sticker" style="left:110px;right:110px;top:1270px;padding:26px 30px 32px;text-align:center">
  <div class="mono" style="font-size:30px;font-weight:700;color:#444">{esc(i.get("label", ""))}</div>
  <div id="{cid}-n" class="mont" style="font-size:{i.get("size", 120)}px;font-weight:900;white-space:nowrap;margin-top:6px;color:#0b0b0b">{pre}0</div>
  <div style="height:16px;margin:-8px 40px 0;background:{GOLD};border-radius:8px"></div></div>""", \
        [f'tl.fromTo("#{cid}-c", {{opacity:0,scale:.2,rotation:-18}}, {{opacity:1,scale:1,rotation:-3,duration:.45,ease:"back.out(2.2)"}}, .05);',
         (f'(function(){{const o={{v:0}};const el=document.querySelector("#{cid}-n");const f=v=>"{pre}"+v.toLocaleString("en-US",{{minimumFractionDigits:{dec},maximumFractionDigits:{dec}}});'
          f'tl.set(o,{{v:0,onUpdate:()=>el.textContent=f(o.v)}},0);tl.to(o,{{v:{v},duration:1.5,ease:"power2.out",onUpdate:()=>el.textContent=f(o.v)}},.45);}})();') if i.get("count", True) else
         f'tl.set("#{cid}-n", {{textContent:"{money(v, dec, pre)}"}}, 0);',
         f'tl.to("#{cid}-c", {{scale:1.12,duration:.12,yoyo:true,repeat:1,ease:"power2.out"}}, {r(t_hit)});'] + cjs + [exit_all(d)]


def screen_asset(name):
    """scale a screen recording to 1080 wide once; returns (file, w, h)"""
    out = f"{A}/scr_{os.path.splitext(os.path.basename(name))[0]}.mp4"
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f"{A}/{name}", "-an", "-vf", "fps=30,scale=1080:-2,format=yuv420p", "-c:v", "libx264", "-crf", "17", "-g", "30", out], check=True)
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", out], capture_output=True, text=True).stdout)["streams"][0]
    return os.path.basename(out), pr["width"], pr["height"]


def N02(i, cid, d):
    f, vw, vh = screen_asset(i["asset"])
    x0, y0, x1, y1 = [v * 1080 / i.get("box_width", 1080) for v in i["box"]]
    s_ = min(1.6, 980 / max(60, x1 - x0)); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x = min(0, max(W - vw * s_, 540 - cx * s_)); y = min(0, max(H - vh * s_, 820 - cy * s_))
    y_start = min(0, max(H - vh, 960 - cy))
    SFX.append(("whoosh", T(i["start"]) + .4, .25)); SFX.append(("ding", T(i["start"]) + 1.45, .3))
    return f"""<div class="ab" style="inset:0;background:#0b0d12"></div>
<div id="{cid}-cam" class="ab" style="left:0;top:0;width:{vw}px;height:{vh}px;transform-origin:0 0">
  <video id="{cid}-v" class="clip" src="assets/{f}" data-start="0" data-duration="{r(d)}" data-media-start="{i.get("media_start", 0)}" muted playsinline style="position:absolute;left:0;top:0;width:{vw}px;height:{vh}px"></video>
  <div id="{cid}-hl" class="ab" style="left:{r(x0 - 26)}px;top:{r(y0 - 22)}px;width:{r(x1 - x0 + 52)}px;height:{r(y1 - y0 + 44)}px;border-radius:50%;border:{r(9 / s_)}px solid {ORANGE};transform:rotate(-3deg);opacity:0"></div></div>
<div class="ab" style="left:0;right:0;top:{int(max(140, 820 - (y1 - y0) * s_ / 2 - 170))}px;text-align:center">{pill("✓ " + esc(i.get("tag", "BUKTI SEBENAR")), GOLD, "#0b0b0b", 58, -3, cid + "-tag")}</div>""", \
        [f'tl.set("#{cid}-cam", {{x:0,y:{r(y_start)},scale:1}}, 0);', f'tl.to("#{cid}-cam", {{x:{r(x)},y:{r(y)},scale:{r(s_)},duration:.9,ease:"power3.inOut"}}, .35);',
         f'tl.fromTo("#{cid}-hl", {{opacity:0,scale:1.6}}, {{opacity:1,scale:1,duration:.3,ease:"back.out(2)"}}, 1.3);', slam(f"#{cid}-tag", 1.45, -3), exit_all(d)]


def N03(i, cid, d):
    steps = i["steps"]; n = len(steps); gap = (d - 1.0) / max(1, n)
    chips = "".join(f'<div id="{cid}-m{k}" style="flex:1;text-align:center;padding:16px 6px 18px;border-radius:22px;background:#fff;color:#0b0b0b;border:6px solid #0b0b0b;box-shadow:6px 7px 0 #0b0b0b"><div class="mono" style="font-size:28px;font-weight:700;color:#555">{esc(a)}</div><div id="{cid}-v{k}" class="mont" style="font-size:42px;font-weight:900;margin-top:4px;opacity:0">{esc(b)}</div></div>' for k, (a, b) in enumerate(steps))
    js = [bop(f"#{cid}-s", .1)]
    for k in range(n):
        t = .5 + k * gap
        js += [f'tl.to("#{cid}-m{k}", {{backgroundColor:"{GOLD}",scale:1.08,duration:.18,ease:"back.out(3)"}}, {r(t)});', bop(f"#{cid}-v{k}", t + .05)]
        if k: js.append(f'tl.to("#{cid}-m{k - 1}", {{backgroundColor:"#fff",scale:1,duration:.2}}, {r(t)});')
        SFX.append(("pop", T(i["start"]) + t, .2))
    SFX.append(("ding", T(i["start"]) + .5 + (n - 1) * gap + .1, .25))
    return f"""<div class="ab" style="left:0;right:0;top:0;height:460px;background:linear-gradient(180deg,rgba(5,6,10,.9),rgba(5,6,10,0))"></div>
<div id="{cid}-s" class="ab" style="left:44px;right:44px;top:120px;display:flex;gap:16px">{chips}</div>""", js + [exit_all(d)]


def N04(i, cid, d):
    bars = i["bars"]; mx = max(float(b[1]) for b in bars); bw = min(200, int(820 / len(bars)) - 30); nb = len(bars)
    bh = "".join(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:760px;min-width:0"><div id="{cid}-l{k}" style="margin-bottom:16px;opacity:0;white-space:nowrap">{pill(esc(b[2]), GOLD if k == nb - 1 else "#fff", "#0b0b0b", 40, -3) if len(b) > 2 and b[2] else ""}</div>'
                 f'<div id="{cid}-b{k}" style="width:{bw}px;height:{int(float(b[1]) / mx * 620)}px;border-radius:18px 18px 6px 6px;background:{GOLD if k == nb - 1 else "#C9D0DC"};border:6px solid #0b0b0b;box-shadow:8px 0 0 #0b0b0b;transform-origin:50% 100%"></div><div class="mont" style="font-size:36px;margin-top:16px;white-space:nowrap">{esc(b[0])}</div></div>' for k, b in enumerate(bars))
    js = []
    for k in range(nb):
        js.append(f'tl.fromTo("#{cid}-b{k}", {{scaleY:0}}, {{scaleY:1,duration:.55,ease:"back.out(1.8)"}}, {r(.3 + k * .35)});'); SFX.append(("pop", T(i["start"]) + .3 + k * .35, .18))
        js.append(bop(f"#{cid}-l{k}", .75 + k * .35))
    tlast = .75 + (nb - 1) * .35; SFX.append(("ding", T(i["start"]) + tlast, .3))
    js.append(f'tl.fromTo("#{cid}-up", {{opacity:0,scale:.2,rotation:-30}}, {{opacity:1,scale:1,rotation:0,duration:.35,ease:"back.out(3)"}}, {r(tlast)});')
    return f"""<div class="ab" style="inset:0;background:radial-gradient(ellipse 90% 60% at 50% 40%,#1c2233,#07090d 70%)"></div>
<div class="ab mono" style="left:0;right:0;top:330px;text-align:center;font-size:32px;color:{GOLD}">{esc(i.get("label", ""))}</div>
<div class="ab mont ol" style="left:40px;right:40px;top:390px;text-align:center;font-size:84px;font-weight:900">{esc(i.get("title", ""))}</div>
<div id="{cid}-up" class="ab emo" style="right:70px;top:560px;font-size:150px;opacity:0">📈</div>
<div class="ab" style="left:90px;right:90px;top:620px;display:flex;gap:30px">{bh}</div>
<div class="ab" style="left:80px;right:80px;top:1380px;height:8px;border-radius:4px;background:#0b0b0b;box-shadow:0 -2px 0 rgba(255,255,255,.3)"></div>
<div class="ab" style="left:60px;right:60px;top:1560px;text-align:center;font-weight:600;font-size:30px;color:#9AA3B2">{esc(i.get("source", ""))}</div>""", js + [exit_all(d)]


def card_list(cid, title, items, top=1160, mark="num"):
    rows = []
    for k, t in enumerate(items):
        if mark == "num":
            ic = f'<div class="mont" style="flex:none;width:66px;height:66px;border-radius:50%;background:#0b0b0b;color:{GOLD};display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:900">{k + 1}</div>'
        else:
            ic = f'<div id="{cid}-x{k}" style="flex:none;width:62px;height:62px;border-radius:14px;border:6px solid #0b0b0b;background:#fff;position:relative"><div id="{cid}-t{k}" style="position:absolute;left:16px;top:2px;width:18px;height:34px;border-right:8px solid #12A150;border-bottom:8px solid #12A150;transform:rotate(45deg);opacity:0"></div></div>'
        rows.append(f'<div id="{cid}-i{k}" style="display:flex;align-items:center;gap:22px;margin-top:20px">{ic}<div style="font-weight:800;font-size:48px;line-height:1.12;color:#0b0b0b">{esc(t)}</div></div>')
    return f'<div class="scrimB"></div><div id="{cid}-c" class="sticker" style="left:70px;right:70px;top:{top}px;padding:30px 44px 40px">{pill(esc(title), GOLD, "#0b0b0b", 34, -2) if title else ""}{"".join(rows)}</div>'


def K01(i, cid, d):
    SFX.append(("pop", T(i["start"]) + .1, .25))
    js = [slam(f"#{cid}-c", .1, rot=-1.5, s0=.4)]
    for k in range(len(i["items"])): js.append(bop(f"#{cid}-i{k}", .6 + k * .45)); SFX.append(("pop", T(i["start"]) + .6 + k * .45, .16))
    return card_list(cid, i.get("title", ""), i["items"]), js + [exit_all(d)]


def K04(i, cid, d):
    n = len(i["items"]); step = min(.8, (d - 1.2) / max(1, n))
    js = [slam(f"#{cid}-c", .1, rot=-1.5, s0=.4)]
    for k in range(n):
        t = .7 + k * step; SFX.append(("pop", T(i["start"]) + t, .2))
        js += [f'tl.fromTo("#{cid}-t{k}", {{opacity:0,scale:.2}}, {{opacity:1,scale:1,duration:.25,ease:"back.out(3)"}}, {r(t)});', f'tl.to("#{cid}-x{k}", {{backgroundColor:"#D7FBE6",duration:.2}}, {r(t)});',
               f'tl.fromTo("#{cid}-i{k}", {{x:0}}, {{x:14,duration:.08,yoyo:true,repeat:1}}, {r(t)});']
    SFX.append(("ding", T(i["start"]) + .7 + (n - 1) * step + .2, .25))
    return card_list(cid, i.get("title", ""), i["items"], mark="check"), js + [exit_all(d)]


def K02(i, cid, d):
    t2 = min(1.3, d * .35)
    SFX.append(("pop", T(i["start"]) + .1, .2)); SFX.append(("boom", T(i["start"]) + t2, .35))
    return f"""<div class="scrimB" style="height:1000px"></div>
<div id="{cid}-a" class="sticker" style="left:60px;right:60px;top:1030px;padding:24px 34px;background:#FFE8E8"><div class="mont" style="font-size:34px;font-weight:900;color:#D32F2F">✕ {esc(i.get("before_label", "Sebelum"))}</div><div style="font-weight:700;font-size:42px;margin-top:8px;color:#333">{esc(i["before"])}</div>
  <div id="{cid}-x" class="ab" style="left:20px;right:20px;top:50%;height:10px;background:#D32F2F;border-radius:5px;transform-origin:0 50%"></div></div>
<div id="{cid}-b" class="sticker" style="left:60px;right:60px;top:1390px;padding:24px 34px;background:#E3FCEF"><div class="mont" style="font-size:34px;font-weight:900;color:#12A150">✓ {esc(i.get("after_label", "Selepas"))}</div><div style="font-weight:800;font-size:46px;margin-top:8px;color:#0b0b0b">{esc(i["after"])}</div></div>""", \
        [bop(f"#{cid}-a", .1, .3), f'tl.fromTo("#{cid}-x", {{scaleX:0}}, {{scaleX:1,duration:.25,ease:"power2.out"}}, {r(t2 - .25)});', slam(f"#{cid}-b", t2, 1.5, 1.8), shake(t2 + .05, 4, 10), exit_all(d)]


def K03(i, cid, d):
    st = i["steps"]; step = min(.6, (d - 1.0) / max(1, len(st)))
    html = "".join((f'<span id="{cid}-a{k}" class="mont ol" style="color:{GOLD};font-size:56px;font-weight:900;opacity:0">→</span>' if k else "") + f'<span id="{cid}-s{k}" style="display:inline-block;padding:16px 26px 12px;border-radius:20px;background:#fff;color:#0b0b0b;border:6px solid #0b0b0b;box-shadow:6px 7px 0 #0b0b0b;font-weight:900;font-size:42px;opacity:0">{esc(s_)}</span>' for k, s_ in enumerate(st))
    js = []
    for k in range(len(st)):
        t = .3 + k * step; SFX.append(("pop", T(i["start"]) + t, .2))
        js += [bop(f"#{cid}-s{k}", t), f'tl.to("#{cid}-s{k}", {{backgroundColor:"{GOLD}",duration:.15}}, {r(t + .1)});']
        if k: js += [bop(f"#{cid}-a{k}", t - .1, .2), f'tl.to("#{cid}-s{k - 1}", {{backgroundColor:"#fff",duration:.2}}, {r(t + .1)});']
    return f'<div class="scrimB"></div><div class="ab" style="left:36px;right:36px;top:1320px;display:flex;flex-wrap:wrap;gap:20px 12px;justify-content:center;align-items:center">{html}</div>', js + [exit_all(d)]


def K05(i, cid, d):
    SFX.append(("whoosh", T(i["start"]) + .05, .25)); SFX.append(("pop", T(i["start"]) + .45, .2))
    return f"""<div id="{cid}-l" class="ab" style="left:50px;top:1300px">
  <div id="{cid}-n" class="sticker mont" style="position:relative;display:inline-block;font-size:76px;font-weight:900;padding:16px 36px 8px">{esc(i["name"])}</div><br>
  <div style="margin:18px 0 0 30px;display:inline-block">{pill(esc(i.get("role", "")), GOLD, "#0b0b0b", 40, 1.5, cid + "-r")}</div></div>""", \
        [f'tl.fromTo("#{cid}-n", {{opacity:0,x:-700}}, {{opacity:1,x:0,duration:.4,ease:"back.out(1.6)"}}, .05);', bop(f"#{cid}-r", .45), exit_all(d)]


def E01(i, cid, d):
    tap = min(2.2, d - 1.3)
    SFX.append(("pop", T(i["start"]) + .2, .25)); SFX.append(("click", T(i["start"]) + tap, .45)); SFX.append(("ding", T(i["start"]) + tap + .08, .25))
    return f"""<div class="ab" style="inset:0;background:radial-gradient(ellipse 90% 60% at 50% 40%,#2a1408,#07090d 70%)"></div>
<div class="ab" style="left:190px;top:330px;width:700px;height:700px;border-radius:50%;background:{ORANGE};filter:blur(150px);opacity:.4"></div>
<img id="{cid}-p" class="ab" src="assets/{i["image"]}" style="left:140px;top:260px;width:800px;height:820px;object-fit:contain" />
<div id="{cid}-t" class="ab mont ol" style="left:40px;right:40px;top:1120px;text-align:center;font-size:78px;font-weight:900">{gold(i.get("title", ""))}</div>
<div class="ab" style="left:0;right:0;top:1310px;display:flex;justify-content:center"><div style="position:relative">
  <div id="{cid}-btn" class="mont" style="background:{GOLD};color:#0b0b0b;font-size:62px;font-weight:900;padding:26px 60px 18px;border-radius:999px;border:8px solid #0b0b0b;box-shadow:10px 12px 0 #0b0b0b">{esc(i.get("button", "DAFTAR SEKARANG"))}</div>
  <div id="{cid}-ring" style="position:absolute;left:50%;top:50%;width:140px;height:140px;margin:-70px 0 0 -70px;border-radius:50%;border:8px solid #fff;opacity:0"></div>
  <div id="{cid}-hand" class="emo" style="position:absolute;left:60%;top:50px;font-size:130px;opacity:0">👆</div></div></div>
<div class="ab" style="left:60px;right:60px;top:1500px;text-align:center;font-weight:700;font-size:38px;color:#E5E8EE">{esc(i.get("sub", ""))}</div>""", \
        [f'tl.fromTo("#{cid}-p", {{opacity:0,y:120,scale:.6,rotation:-8}}, {{opacity:1,y:0,scale:1,rotation:0,duration:.6,ease:"back.out(1.8)"}}, .1);',
         f'tl.to("#{cid}-p", {{y:-24,duration:.9,yoyo:true,repeat:{max(1, int((d - 1) / .9))},ease:"sine.inOut"}}, .8);',
         slam(f"#{cid}-t", .45, 0, 1.6), bop(f"#{cid}-btn", .8, .3),
         f'tl.fromTo("#{cid}-hand", {{opacity:0,x:260,y:260}}, {{opacity:1,x:0,y:0,duration:.6,ease:"power3.out"}}, {r(tap - .7)});',
         f'tl.to("#{cid}-hand", {{scale:.85,duration:.08,yoyo:true,repeat:1}}, {r(tap - .05)});', f'tl.to("#{cid}-btn", {{scale:.92,duration:.08,yoyo:true,repeat:1}}, {r(tap - .05)});',
         f'tl.fromTo("#{cid}-ring", {{opacity:1,scale:.4}}, {{opacity:0,scale:3.4,duration:.6,ease:"power2.out"}}, {r(tap)});', f'tl.to("#{cid}-hand", {{opacity:0,y:120,duration:.4}}, {r(tap + .5)});', exit_all(d)]


def E02(i, cid, d):
    tap = min(2.0, d - 1.2)
    SFX.append(("pop", T(i["start"]) + .15, .2)); SFX.append(("click", T(i["start"]) + tap, .45)); SFX.append(("ding", T(i["start"]) + tap + .08, .22))
    return f"""<div class="dim" style="background:rgba(5,6,10,.72)"></div>
<div id="{cid}-c" class="sticker" style="left:90px;right:90px;top:480px;padding:46px 40px 54px;text-align:center">
  <div style="width:300px;height:300px;margin:0 auto;border-radius:50%;overflow:hidden;border:8px solid #0b0b0b;box-shadow:0 0 0 8px {GOLD};position:relative"><video id="{cid}-av" class="clip" src="assets/{BASE}" data-start="0" data-duration="{r(d)}" data-media-start="{r(i.get("avatar_at", max(0, i["start"] - 2)))}" muted playsinline style="position:absolute;left:0;top:-60px;width:300px;height:533px;object-fit:cover"></video></div>
  <div class="mont" style="font-size:78px;font-weight:900;margin-top:30px">{esc(i["name"])}</div>
  <div style="font-weight:800;font-size:44px;color:#B47A00;margin-top:4px">{esc(i.get("handle", ""))}</div>
  <div style="font-weight:600;font-size:38px;color:#444;margin-top:14px">{esc(i.get("line", ""))}</div>
  <div style="position:relative;display:inline-block;margin-top:34px">
    <div id="{cid}-btn" class="mont" style="background:{ORANGE};color:#fff;font-size:56px;padding:22px 60px 16px;border-radius:999px;border:6px solid #0b0b0b">{esc(i.get("button", "+ FOLLOW"))}</div>
    <div id="{cid}-ok" class="mont" style="position:absolute;left:50%;top:0;transform:translateX(-50%);background:#3DD68C;color:#0b0b0b;font-size:56px;padding:22px 44px 16px;border-radius:999px;border:6px solid #0b0b0b;opacity:0;white-space:nowrap">✓ FOLLOWING</div>
    <div id="{cid}-ring" style="position:absolute;left:50%;top:50%;width:120px;height:120px;margin:-60px 0 0 -60px;border-radius:50%;border:8px solid {GOLD};opacity:0"></div>
    <div id="{cid}-hand" class="emo" style="position:absolute;left:62%;top:40px;font-size:130px;opacity:0">👆</div></div></div>""", \
        [f'tl.fromTo("#{cid}-c", {{opacity:0,y:120,rotation:4,scale:.85}}, {{opacity:1,y:0,rotation:-2,scale:1,duration:.55,ease:"back.out(1.8)"}}, .05);',
         f'tl.fromTo("#{cid}-hand", {{opacity:0,x:260,y:260}}, {{opacity:1,x:0,y:0,duration:.6,ease:"power3.out"}}, {r(tap - .7)});',
         f'tl.to("#{cid}-hand", {{scale:.85,duration:.08,yoyo:true,repeat:1}}, {r(tap - .05)});',
         f'tl.to("#{cid}-btn", {{scale:.9,duration:.08,yoyo:true,repeat:1}}, {r(tap - .05)});',
         f'tl.set("#{cid}-ok", {{opacity:1}}, {r(tap + .08)});',
         f'tl.fromTo("#{cid}-ring", {{opacity:1,scale:.4}}, {{opacity:0,scale:3.2,duration:.6,ease:"power2.out"}}, {r(tap)});',
         f'tl.to("#{cid}-hand", {{opacity:0,y:120,duration:.4}}, {r(tap + .5)});', exit_all(d)]


def C04(i, cid, d):
    SFX.append(("boom", T(i["start"]), .4))
    return f"""<div id="{cid}-fl" class="ab" style="inset:0;background:rgba(255,255,255,.85);opacity:0"></div>
<div id="{cid}-pw" class="ab mont" style="left:0;right:0;top:660px;text-align:center;font-size:{i.get("size", 220)}px;font-weight:900;color:{GOLD};white-space:nowrap;-webkit-text-stroke:16px #0b0b0b;paint-order:stroke fill;text-shadow:14px 16px 0 #0b0b0b">{esc(i["word"])}</div>""", \
        [f'tl.fromTo("#{cid}-fl", {{opacity:.8}}, {{opacity:0,duration:.25}}, 0);', slam(f"#{cid}-pw", 0, rot=-4, s0=2.6), shake(.15, 5, 14), fout(f"#{cid}-pw", d - .3)]


def X01(i, cid, d):
    SFX.append(("whoosh", T(i["start"]) - .2, .35)); SFX.append(("boom", T(i["start"]), .2))
    return f'<div id="{cid}-f" class="ab" style="inset:0;background:radial-gradient(circle at 50% 45%,#fff,rgba(255,255,255,.6) 35%,transparent 70%);opacity:0"></div>', \
        [f'tl.fromTo("#{cid}-f", {{opacity:0}}, {{opacity:1,duration:.1,ease:"power2.in"}}, 0);', f'tl.to("#{cid}-f", {{opacity:0,duration:.3,ease:"power2.out"}}, .12);']


def X02(i, cid, d):
    SFX.append(("whoosh", T(i["start"]) - .15, .25)); SFX.append(("boom", T(i["start"]), .25))
    return f'<div id="{cid}-f" class="ab" style="inset:0;background:radial-gradient(ellipse 70% 55% at 50% 45%,rgba(255,200,120,1),rgba(255,90,31,.7) 45%,rgba(255,43,43,.2) 75%);mix-blend-mode:screen;opacity:0"></div>', \
        [f'tl.fromTo("#{cid}-f", {{opacity:0}}, {{opacity:1,duration:.1,ease:"power2.in"}}, 0);', f'tl.to("#{cid}-f", {{opacity:0,duration:.45,ease:"power2.out"}}, .12);']


BLOCKS = dict(H06=H06, H01=H01, H02=H02, H03=H03, H04=H04, H05=H05, T01=T01, T02=T02, T04=T04, N01=N01, N02=N02, N03=N03, N04=N04,
              K01=K01, K02=K02, K03=K03, K04=K04, K05=K05, E01=E01, E02=E02, C04=C04, X01=X01, X02=X02)
DEFAULT_DUR = dict(H06=3.5, H01=3.5, H02=3.0, H03=4.0, H04=1.5, H05=3.5, T01=3.2, T02=2.8, T04=2.6, N01=3.6, N02=4.2, N03=4.5, N04=4.2,
                   K01=4.5, K02=4.5, K03=4.5, K04=4.2, K05=4.0, E01=4.5, E02=4.5, C04=1.4, X01=.5, X02=.6)
FULLSCREEN = {"H05", "T04", "N02", "N04", "E01", "E02"}      # cover the footage (sit above captions)
BOTTOM = {"N01", "K01", "K02", "K03", "K04", "K05"}          # occupy the caption band -> captions move up
OWN_TEXT = {"H01", "H03", "C04", "T01", "T02"}           # carry their own words -> captions pause
UNDERCAP = set()                                              # full-screen B-roll that keeps captions on top (Tema Wow)

# optional premium pack (P01–P30): scripts/premium.py, delivered after unlock
if os.path.exists(f"{HERE}/premium.py"):
    sys.path.insert(0, HERE)
    import premium
    premium.install(globals())

# optional theme pack (Tema Wow): scripts/tema.py, delivered as a reward
if os.path.exists(f"{HERE}/tema.py"):
    sys.path.insert(0, HERE)
    import tema
    tema.install(globals())
# optional add-on pack: scripts/advanced.py
if os.path.exists(f"{HERE}/advanced.py"):
    sys.path.insert(0, HERE)
    import advanced
    advanced.install(globals())

# ---------------------------------------------------------------- build item scenes
items = sorted(PLAN.get("items", []), key=lambda i: i.get("start", 0))
if FREEZE and FREEZE["code"] == "H04":
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "0.05", "-i", f"{A}/{BASE}", "-frames:v", "1", f"{A}/freeze.png"], check=True)
busy_bottom, busy_full = [], []
for k, it in enumerate(items):
    code = it["code"]
    if code not in BLOCKS: sys.exit(f"Kod tidak dikenali dalam items: {code}")
    d = float(it.get("dur", DEFAULT_DUR[code]))
    start_out = 0.0 if code in PREROLL else T(it.get("start", 0))
    d = min(d, TOTAL - start_out)
    cid = f"{code.lower()}-{k}"
    body, js = BLOCKS[code](it, cid, d)
    z = 45 if code in UNDERCAP else 60 if code in FULLSCREEN or code in PREROLL else 30
    scene(cid, start_out, d, body, js, z)
    if code in BOTTOM: busy_bottom.append((start_out, start_out + d))
    if code not in UNDERCAP and (code in FULLSCREEN or code in OWN_TEXT or code in PREROLL): busy_full.append((start_out, start_out + d))

# ---------------------------------------------------------------- captions (one style for the whole video)
CAPSTYLE = PLAN.get("captions")
CAPRANGES = CAPSTYLE if isinstance(CAPSTYLE, list) else None
def style_at(t):
    if not CAPRANGES: return CAPSTYLE
    return next((c["style"] for c in CAPRANGES if c["from"] - .05 <= t < c["to"]), None)
KEYS = {re.sub(r"[^\w]", "", k).lower() for k in PLAN.get("keywords", [])}
def is_key(w): x = re.sub(r"[^\w]", "", w).lower(); return x in KEYS or bool(re.search(r"\d", x))


def cap_html(style, ws, kid):
    def kw(w, color=GOLD): return f'<span style="color:{color}">{esc(w)}</span>' if is_key(w) else esc(w)
    if style == "C01":
        inner = "".join(f'<span id="{kid}w{j}" class="ol" style="display:inline-block;margin:0 10px;padding:0 14px;border-radius:14px;opacity:0;{"color:" + GOLD if is_key(w) else ""}">{esc(w)}</span>' for j, (w, _, _) in enumerate(ws))
        return f'<span class="mont" style="font-size:92px;font-weight:900;text-transform:uppercase;line-height:1.12">{inner}</span>'
    if style == "C02": return f'<span style="display:inline-block;padding:18px 36px 22px;border-radius:26px;background:#0b0b0b;border:6px solid #fff;box-shadow:10px 12px 0 rgba(0,0,0,.5);font-weight:800;font-size:68px;line-height:1.2">{" ".join(kw(w) for w, _, _ in ws)}</span>'
    if style == "C05": return f'<span class="mont" style="display:inline-block;padding:14px 32px 12px;border-radius:20px;background:#fff;color:#0b0b0b;font-weight:900;font-size:66px;border:7px solid #0b0b0b;box-shadow:10px 12px 0 #0b0b0b;transform:rotate(-1.5deg)">{" ".join(kw(w, ORANGE) for w, _, _ in ws)}</span>'
    if style == "C07":
        pink = "text-shadow:0 0 6px #fff,0 0 18px #FF4FD8,0 0 40px #FF4FD8,0 0 80px #B01EFF"
        inner = " ".join('<span style="%s">%s</span>' % (pink, esc(w)) if is_key(w) else esc(w) for w, _, _ in ws)
        return f'<span class="mont" style="font-size:82px;text-transform:uppercase;color:#fff;text-shadow:0 0 6px #fff,0 0 18px #3EC5FF,0 0 40px #3EC5FF,0 0 80px #1E6BFF">{inner}</span>'
    if style == "C03":
        inner = "".join('<span id="%sw%d" class="ol" style="display:inline-block;margin:0 8px 8px;padding:0 12px;border-radius:12px;color:rgba(255,255,255,.62)">%s</span>' % (kid, j, esc(w)) for j, (w, _, _) in enumerate(ws))
        return f'<span class="mont" style="font-size:82px;font-weight:900;text-transform:uppercase;line-height:1.14">{inner}</span>'
    if style == "C06":
        chars = "".join(f'<span id="{kid}k{j}" style="opacity:0">{esc(ch)}</span>' for j, ch in enumerate(" ".join(w for w, _, _ in ws)))
        return (f'<span style="display:inline-block;max-width:980px;text-align:left;border-radius:18px;background:#0d1117;border:5px solid #30363d;box-shadow:10px 12px 0 rgba(0,0,0,.55);overflow:hidden">'
                f'<span style="display:block;padding:10px 18px;background:#161b22"><span style="color:#FF5F57">●</span> <span style="color:#FEBC2E">●</span> <span style="color:#28C840">●</span></span>'
                f'<span style="display:block;white-space:pre-wrap;padding:14px 28px 18px;font-family:\'Space Mono\',monospace;font-weight:700;font-size:52px;line-height:1.3;color:#7EE787"><span style="color:{GOLD}">&gt; </span>{chars}<span style="color:{GOLD}">▍</span></span></span>')
    raise SystemExit(f"Gaya caption tidak dikenali: {style}")


# the big word behind the head (H06) is not captioned twice
_big = [(float(i["start"]), re.sub(r"[^\w]", "", str(i.get("word", ""))).lower()) for i in items if i["code"] == "H06"]
if _big:
    WORDS = [w for w in WORDS if not any(abs(w[1] - t) < .4 and re.sub(r"[^\w]", "", w[0]).lower() == bw for t, bw in _big)]
if CAPSTYLE and WORDS:
    NS = dict(C01=3, C02=5, C03=6, C05=3, C06=5, C07=3)
    EMO = {re.sub(r"[^\w]", "", k).lower(): v for k, v in PLAN.get("emoji", {}).items()}
    groups, cur = [], []
    for w in WORDS:
        if cur and style_at(w[1]) != style_at(cur[0][1]): groups.append(cur); cur = []
        N = NS.get(style_at(w[1]) or "C01", 3)
        if cur and (len(cur) >= N or w[1] - cur[-1][2] > .6): groups.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w[0]): groups.append(cur); cur = []
    if cur: groups.append(cur)
    body, js = [], []
    for k, g in enumerate(groups):
        CS = style_at(g[0][1])
        if not CS: continue
        st = max(0, T(g[0][1]) - .05); en = min(T(groups[k + 1][0][1]) - .06 if k + 1 < len(groups) else TOTAL, T(g[-1][2]) + .5)
        if any(a - .05 <= st < b for a, b in busy_full): continue
        for a, b in busy_full:                       # a caption running into a text-carrying style ends where it begins
            if st < a < en: en = a
        if en - st < .25: continue
        top = 250 if any(a - .2 <= st < b for a, b in busy_bottom) or any(a < en and st < b for a, b in busy_bottom) else (PLAN.get("cap_top") or (1150 if CS == "C01" else 1170))   # safe zone: below the eyes, above the bottom third that Reels/TikTok cover
        kid = f"cp{k}"
        body.append(f'<div id="{kid}" class="cap" style="top:{top}px;opacity:0">{cap_html(CS, g, kid)}</div>')
        if CS == "C07":   # neon tube flicker on
            js += [f'tl.set("#{kid}", {{opacity:1}}, {r(st)});', f'tl.set("#{kid}", {{opacity:.2}}, {r(st + .05)});', f'tl.set("#{kid}", {{opacity:1}}, {r(st + .1)});', f'tl.set("#{kid}", {{opacity:.4}}, {r(st + .16)});', f'tl.set("#{kid}", {{opacity:1}}, {r(st + .2)});']
        elif CS in ("C02", "C05"):
            js.append(f'tl.fromTo("#{kid}", {{opacity:0,y:30,scale:.7}}, {{opacity:1,y:0,scale:1,duration:.22,ease:"back.out(2.5)"}}, {r(st)});')
        else:
            js.append(f'tl.fromTo("#{kid}", {{opacity:0,y:14,scale:.96}}, {{opacity:1,y:0,scale:1,duration:.14,ease:"power2.out"}}, {r(st)});')
        js.append(f'tl.set("#{kid}", {{opacity:0}}, {r(en)});')
        if CS == "C01":
            for j, w in enumerate(g):
                tw = T(w[1]); nxt = T(g[j + 1][1]) if j + 1 < len(g) else en
                js += [f'tl.fromTo("#{kid}w{j}", {{opacity:0,scale:.55,y:18}}, {{opacity:1,scale:1,y:0,duration:.16,ease:"back.out(3)"}}, {r(max(st, tw - .03))});',
                       f'tl.set("#{kid}w{j}", {{backgroundColor:"{GOLD}",color:"#111",webkitTextStrokeWidth:0,rotation:-2}}, {r(max(st, tw - .03))});',
                       f'tl.set("#{kid}w{j}", {{backgroundColor:"rgba(0,0,0,0)",color:"{GOLD if is_key(w[0]) else INK}",webkitTextStrokeWidth:14,rotation:0}}, {r(min(en, nxt) - .01)});']
                e = EMO.get(re.sub(r"[^\w]", "", w[0]).lower())
                if e:
                    eid = f"{kid}e{j}"; body.append(f'<div id="{eid}" class="ab emo" style="left:0;right:0;top:{top - 210}px;text-align:center;font-size:170px;opacity:0">{e}</div>')
                    js += [f'tl.fromTo("#{eid}", {{opacity:0,scale:.2,rotation:-25}}, {{opacity:1,scale:1,rotation:0,duration:.3,ease:"back.out(3)"}}, {r(tw)});', f'tl.to("#{eid}", {{opacity:0,scale:.6,duration:.2}}, {r(tw + 1.1)});']
                    SFX.append(("pop", tw, .18))
        if CS == "C03":
            for j, w in enumerate(g):
                nxt = T(g[j + 1][1]) if j + 1 < len(g) else en
                js += [f'tl.set("#{kid}w{j}", {{backgroundColor:"{GOLD}",color:"#111",webkitTextStrokeWidth:0}}, {T(w[1])});tl.fromTo("#{kid}w{j}", {{scale:1}}, {{scale:1.12,duration:.1,yoyo:true,repeat:1}}, {T(w[1])});',
                       f'tl.set("#{kid}w{j}", {{backgroundColor:"rgba(0,0,0,0)",color:"#fff",webkitTextStrokeWidth:14}}, {r(min(en, nxt) - .01)});']
        if CS == "C06":
            text = " ".join(w for w, _, _ in g); pos = 0
            for w, s_, e_ in g:
                SFX.append(("click", T(s_), .12))
                for c in range(len(w)): js.append(f'tl.set("#{kid}k{pos + c}", {{opacity:1}}, {r(T(s_) + (e_ - s_) * c / max(1, len(w)))});')
                pos += len(w)
                if pos < len(text): js.append(f'tl.set("#{kid}k{pos}", {{opacity:1}}, {r(T(e_))});'); pos += 1
    scene("caps", 0, TOTAL, "\n".join(body), js, 50)

# ---------------------------------------------------------------- retention progress bar (top edge)
if PLAN.get("progress", True):
    scene("prog", 0, TOTAL, f'<div class="ab" style="left:0;right:0;top:0;height:14px;background:rgba(0,0,0,.35)"></div><div id="prog-b" class="ab" style="left:0;width:1080px;top:0;height:14px;background:linear-gradient(90deg,{GOLD},{ORANGE});transform-origin:0 50%"></div>',
          [f'tl.fromTo("#prog-b", {{scaleX:0}}, {{scaleX:1,duration:{TOTAL},ease:"none"}}, 0);'], 70)

# ---------------------------------------------------------------- sign-off card (free version)
if OUTRO:
    o0 = r(TOTAL - OUTRO)
    scene("penutup", o0, OUTRO, f"""<div class="ab" style="inset:0;background:radial-gradient(circle at 50% 42%,#1d2233,#0a0b10 70%)"></div>
<div id="pn-in" class="ab" style="left:60px;right:60px;top:700px;text-align:center">
  <div style="font-family:'Montserrat',sans-serif;font-weight:700;font-size:44px;color:rgba(255,255,255,.75)">Diedit dengan</div>
  <div style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:150px;line-height:1.05;letter-spacing:-.03em;color:#fff">Suruh <span style="color:{GOLD}">AI</span></div>
  <div id="pn-l" style="height:8px;width:420px;margin:26px auto;border-radius:4px;background:linear-gradient(90deg,{GOLD},{ORANGE})"></div>
  <div style="font-family:'Montserrat',sans-serif;font-weight:800;font-size:46px;color:#fff">suruhaieditvideogunaphone.com</div>
  <div style="font-family:'Montserrat',sans-serif;font-weight:600;font-size:34px;color:rgba(255,255,255,.6);margin-top:14px">Edit video guna phone · percuma</div>
</div>""", ['tl.fromTo("#R", {opacity:0}, {opacity:1,duration:.25}, 0);', 'tl.fromTo("#pn-in", {y:40,opacity:0}, {y:0,opacity:1,duration:.45,ease:"power3.out"}, .1);',
            'tl.fromTo("#pn-l", {scaleX:0}, {scaleX:1,duration:.5,ease:"power2.out"}, .35);'], 90)
    SFX.append(("ding", o0 + .35, .25))

# ---------------------------------------------------------------- camera moves on the footage (root timeline)
cam_js = []
_pl = []
_cutwin = [(float(i["start"]) - .3, float(i["start"]) + float(i.get("dur", 3.5)) + .8) for i in items if i["code"] in ("H06", "B06")]
for t in sorted(t for t in PLAN.get("punch", []) if not any(a <= t <= b for a, b in _cutwin)):                  # keep punches at least 1.3 s apart so their moves never overlap
    if not _pl or t - _pl[-1] >= 1.3: _pl.append(t)
for t in _pl:                                            # X03: punch-in on emphasis (source times)
    cam_js += [f'tl.to("#cam", {{scale:1.17,rotation:1.2,duration:.12,ease:"power4.out"}}, {r(T(t) - .05)});',
               f'tl.fromTo("#cam", {{x:0,y:0}}, {{x:10,y:-6,duration:.04,yoyo:true,repeat:5,ease:"none",immediateRender:false}}, {r(T(t) + .07)});',
               f'tl.to("#cam", {{scale:1,rotation:0,x:0,y:0,duration:.5,ease:"power2.inOut"}}, {r(T(t) + .75)});']
    SFX.append(("boom", T(t) - .03, .16))
for it in items:
    if it["code"] == "X01":                              # whip: footage slides out and back in at the cut
        t = T(it["start"]); cam_js += [f'tl.to("#cam", {{scale:2.3,duration:.2,ease:"power4.in"}}, {r(t - .2)});', f'tl.set("#cam", {{scale:1.6}}, {r(t)});', f'tl.to("#cam", {{scale:1,duration:.35,ease:"power3.out"}}, {r(t)});']
    if it["code"] == "X02":
        t = T(it["start"]); cam_js += [f'tl.fromTo("#cam", {{scale:1.15}}, {{scale:1,duration:.6,ease:"power3.out",immediateRender:false}}, {r(t + .1)});']

# ---------------------------------------------------------------- SFX (synthesised, quiet)
SR = 48000; rng = np.random.default_rng(1)
def lp(x, k): ker = np.exp(-np.linspace(0, 6, k)); ker /= ker.sum(); return np.convolve(x, ker, "same")
def gen(kind):
    if kind == "whoosh": n = int(SR * .5); x = rng.standard_normal(n); x = x - lp(x, 18); return x * np.sin(np.pi * np.arange(n) / n) ** 2 * .5
    if kind == "hit": n = int(SR * 1.2); t = np.arange(n) / SR; return np.sin(2 * np.pi * 52 * t * (1 - .2 * t)) * np.exp(-t * 3.5) + .3 * lp(rng.standard_normal(n), 25) * np.exp(-t * 14)
    if kind == "boom": n = int(SR * .7); t = np.arange(n) / SR; return np.sin(2 * np.pi * (75 - 40 * t) * t) * np.exp(-t * 7) + .35 * lp(rng.standard_normal(n), 12) * np.exp(-t * 40)
    if kind == "ding": n = int(SR * 1.0); t = np.arange(n) / SR; return sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1568, 1), (3136, .35), (4704, .15))) * np.exp(-t * 5)
    if kind == "click": n = int(SR * .06); t = np.arange(n) / SR; return (rng.standard_normal(n) * .6 + np.sin(2 * np.pi * 2200 * t)) * np.exp(-t * 120)
    if kind == "riser": n = int(SR * .9); t = np.arange(n) / SR; x = rng.standard_normal(n); x = x - lp(x, 6); return x * (t / t[-1]) ** 2 * .6 + .3 * np.sin(2 * np.pi * (200 + 900 * t) * t) * (t / t[-1])
    if kind == "rewind": n = int(SR * .45); t = np.arange(n) / SR; return np.sin(2 * np.pi * (1800 - 2600 * t) * t * (1 + .3 * np.sin(2 * np.pi * 30 * t))) * .5 * np.exp(-t * 2)
    n = int(SR * .12); t = np.arange(n) / SR; return np.sin(2 * np.pi * (950 - 2600 * t) * t) * np.exp(-t * 38) * .8
for kind in ("whoosh", "hit", "pop", "boom", "ding", "click", "riser", "rewind"):
    x = gen(kind); x = x / np.abs(x).max() * .9
    with wave.open(f"{A}/sfx_{kind}.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.repeat(x[:, None], 2, 1) * 32767).astype(np.int16).tobytes())
SFXLEN = dict(whoosh=.5, hit=1.2, pop=.12, boom=.7, ding=1.0, click=.06, riser=.9, rewind=.45)
sfx_tags, lanes = [], {}          # each sound gets the first free track (3–9) so nothing overlaps on one track
for k, (kind, t, g) in enumerate(sorted(SFX, key=lambda x: x[1])):
    if not (PLAN.get("sfx", True) and 0 <= t < TOTAL - .1): continue
    t0 = r(max(0, t)); lane = next((n for n in range(3, 10) if lanes.get(n, -1) <= t0), None)
    if lane is None: continue
    lanes[lane] = t0 + SFXLEN[kind] + .01
    sfx_tags.append(f'<audio id="sfx{k}" class="clip" src="assets/sfx_{kind}.wav" data-start="{t0}" data-duration="{SFXLEN[kind]}" data-track-index="{lane}" data-volume="{g}"></audio>')

# ---------------------------------------------------------------- root
hosts = "\n".join(f'      <div id="{c}" data-composition-id="{c}" data-composition-src="compositions/{c}.html" data-start="{s}" data-duration="{d}" data-track-index="{10 + n}" data-track-kind="{"captions" if c == "caps" else "graphics"}" data-width="{W}" data-height="{H}" style="position:absolute;inset:0;z-index:{z}"></div>'
                  for n, (c, s, d, z) in enumerate(HOSTS))
def wav_len(p): w = wave.open(p); return w.getnframes() / w.getframerate()
voice = f'<audio id="voice" class="clip" src="assets/main.wav" data-start="{r(OFF)}" data-duration="{r(min(SRC_DUR, wav_len(f"{A}/main.wav")) - .01)}" data-track-index="1" data-volume="1"></audio>' if PROBE.get("has_audio") else ""
open(f"{PROJ}/index.html", "w").write(f"""<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" /><script src="assets/gsap.min.js"></script>
    <style>* {{ margin:0; padding:0; box-sizing:border-box; }} html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#000; }}</style></head>
  <body>
    <div id="main" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}" style="position:relative;width:{W}px;height:{H}px;background:#000">
      <div id="cam" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform-origin:540px 820px">
        <video id="base" class="clip" src="assets/{BASE}" data-start="{r(OFF)}" data-duration="{r(SRC_DUR)}" data-track-index="0" muted playsinline style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover"></video>
      </div>
      {voice}
      {chr(10).join("      " + s for s in sfx_tags)}
{hosts}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.set("#cam", {{x:0,y:0,scale:1,rotation:0}}, 0);
      {chr(10).join("      " + l for l in cam_js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""")
print(f"ok · {len(HOSTS)} scenes · {len(sfx_tags)} sfx · total {TOTAL}s" + (f" (H04 freeze +{OFF}s)" if OFF else ""))
