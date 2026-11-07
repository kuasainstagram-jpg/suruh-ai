"""Word-level transcript (Malay by default). Tries faster-whisper, then `npx hyperframes transcribe`.
python3 transcribe.py <project dir> [lang]  ->  <project>/words.json  [[word, start, end], ...]"""
import json, os, subprocess, sys, wave
proj = sys.argv[1]; lang = sys.argv[2] if len(sys.argv) > 2 else "ms"
wav = f"{proj}/assets/main.wav"; out = f"{proj}/words.json"
mono = f"{proj}/asr16k.wav"
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", mono], check=True)
words = None
try:
    import numpy as np
    from faster_whisper import WhisperModel
    w = wave.open(mono); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    segs, _ = WhisperModel("small", compute_type="int8").transcribe(a, language=lang, word_timestamps=True, beam_size=5)
    words = [[x.word.strip(), round(x.start, 3), round(x.end, 3)] for s in segs for x in s.words]
except Exception as e:
    print("faster-whisper tidak tersedia:", e, file=sys.stderr)
if words is None:
    r = subprocess.run(["npx", "--yes", "hyperframes", "transcribe", mono, "--model", "small", "--language", lang, "--json"], capture_output=True, text=True, cwd=proj)
    path = f"{proj}/assets/transcript.json"
    data = json.load(open(path)) if os.path.exists(path) else json.loads(r.stdout or "[]")
    items = data.get("words", data) if isinstance(data, dict) else data
    words = [[i.get("text", i.get("word", "")).strip(), round(i["start"], 3), round(i["end"], 3)] for i in items]
words = [w for w in words if w[0]]


def snap_onsets(words, mono_path):
    """Whisper tends to start words ~0.1 s early. Move each start to where the voice actually gets loud,
    so captions land on the exact frame the word is heard (forward only, at most 0.25 s, never past the word's end)."""
    import numpy as np
    w = wave.open(mono_path); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = int(sr * .005); env = np.sqrt(np.convolve(a * a, np.ones(hop * 4) / (hop * 4), "same"))[::hop]   # 5 ms RMS envelope
    peak = float(np.percentile(env, 99)) or 1e-6
    out = []
    for k, (word, s, e) in enumerate(words):
        i0 = max(0, int((s - .06) / .005)); i1 = min(len(env) - 1, int(min(s + .25, e - .04) / .005))
        floor = float(np.percentile(env[max(0, i0 - 40):i0 + 1], 20)) if i0 > 0 else 0.0
        thr = max(floor * 3, peak * .08)
        hit = next((j for j in range(i0, i1 + 1) if env[j] >= thr), None)
        ns = s if hit is None else max(s, round(hit * .005, 3))
        if out and ns < out[-1][1] + .03: ns = out[-1][1] + .03
        out.append([word, round(min(ns, e - .03), 3), e])
    return out


try:
    moved = snap_onsets(words, mono)
    shift = [b[1] - a_[1] for a_, b in zip(words, moved)]
    words = moved
    print(f"masa perkataan dilaras ikut suara: purata +{sum(shift) / max(1, len(shift)):.3f}s")
except Exception as ex:
    print("laras masa dilangkau:", ex, file=sys.stderr)
json.dump(words, open(out, "w"), ensure_ascii=False)
print(len(words), "words ->", out)
print(" ".join(f"{w}@{s:.2f}" for w, s, _ in words))
