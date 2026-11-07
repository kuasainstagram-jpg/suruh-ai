"""Download a video from a Google Drive share link (file must be 'Anyone with the link').
python3 fetch.py <drive link or file id> <out.mp4>"""
import re, subprocess, sys
link, out = sys.argv[1], sys.argv[2]
m = re.search(r"/d/([A-Za-z0-9_-]{20,})", link) or re.search(r"[?&]id=([A-Za-z0-9_-]{20,})", link) or re.fullmatch(r"([A-Za-z0-9_-]{20,})", link)
if not m:
    sys.exit("Link Google Drive tidak dikenali. Guna link fail (…/file/d/<ID>/view), bukan link folder.")
fid = m.group(1)
url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
subprocess.run(["curl", "-sSL", "--fail", "--retry", "2", "--max-time", "1800", url, "-o", out], check=True)
head = open(out, "rb").read(512)
if head.lstrip().startswith(b"<"):
    sys.exit("Drive memulangkan halaman web, bukan video. Pastikan akses fail = 'Sesiapa yang ada pautan' (Anyone with the link).")
print("ok", out)
