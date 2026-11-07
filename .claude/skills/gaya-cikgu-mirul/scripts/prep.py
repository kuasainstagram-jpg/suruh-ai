"""Normalise a phone video for editing: honour rotation, tone-map HDR (iPhone HLG/PQ) to SDR,
30 fps CFR, 1080x1920 (cover-crop or blurred-fit for landscape), clean voice track.
python3 prep.py <in> <project dir>   ->  <project>/assets/main.mp4 (silent) + main.wav + probe.json"""
import json, subprocess, sys
src, proj = sys.argv[1], sys.argv[2]
A = f"{proj}/assets"
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", src], capture_output=True, text=True, check=True).stdout)
v = next(s for s in pr["streams"] if s["codec_type"] == "video")
rot = 0
for sd in v.get("side_data_list", []):
    if "rotation" in sd: rot = int(sd["rotation"])
rot = int(v.get("tags", {}).get("rotate", rot) or rot)
w, h = int(v["width"]), int(v["height"])
if abs(rot) in (90, 270): w, h = h, w            # ffmpeg auto-rotates on decode; this is the displayed size
hdr = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
dur = float(pr["format"]["duration"])
has_audio = any(s["codec_type"] == "audio" for s in pr["streams"])
TM = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if hdr else ""
portrait = h >= w
if portrait:
    vf = f"{TM}fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"
    fc = None
else:   # landscape: sharp video centred over a blurred, darkened copy
    fc = (f"[0:v]{TM}fps=30,split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.2[bg];"
          f"[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]")
cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src]
cmd += (["-vf", vf, "-map", "0:v:0"] if fc is None else ["-filter_complex", fc, "-map", "[v]"])
cmd += ["-an", "-c:v", "libx264", "-crf", "17", "-g", "30", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", f"{A}/main.mp4"]
subprocess.run(cmd, check=True)
if has_audio:
    CH = "highpass=f=80,afftdn=nf=-28,acompressor=threshold=-22dB:ratio=3:attack=8:release=150:makeup=2,loudnorm=I=-16:TP=-2:LRA=9"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vn", "-af", CH, "-ar", "48000", "-ac", "2", f"{A}/main.wav"], check=True)
info = dict(duration=round(dur, 3), width=w, height=h, rotation=rot, hdr=hdr, portrait=portrait, has_audio=has_audio)
json.dump(info, open(f"{proj}/probe.json", "w"), indent=1)
print(json.dumps(info))
