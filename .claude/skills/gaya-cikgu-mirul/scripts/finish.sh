#!/bin/bash
# Loudness-normalise the render to -14 LUFS (true-peak safe) and make a WhatsApp copy under 16 MB.
# bash finish.sh <render.mp4> <out_basename_without_ext>
set -e
IN="$1"; OUT="$2"
# voice clean-up first (remove rumble + gentle denoise); BERSIH=0 to skip. Loudness is measured AFTER the clean-up.
CLEAN="highpass=f=80,afftdn=nr=10:nf=-42:tn=1,"; [ "${BERSIH:-1}" = "0" ] && CLEAN=""
J=$(ffmpeg -nostdin -hide_banner -i "$IN" -af ${CLEAN}loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
g(){ echo "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
AF="${CLEAN}loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,alimiter=limit=0.84:attack=5:release=60:level=false,aresample=48000"
ffmpeg -nostdin -v error -y -i "$IN" -c:v libx264 -preset slow -crf 21 -maxrate 9M -bufsize 18M -pix_fmt yuv420p -af "$AF" -c:a aac -b:a 160k -movflags +faststart "$OUT.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT.mp4")
SIZE=$(stat -c %s "$OUT.mp4")
if [ "$SIZE" -gt 15500000 ]; then   # two-pass to ~15 MB total
  VB=$(python3 -c "print(max(400, int(15.0e6*8/float('$DUR')/1000) - 110))")
  ffmpeg -nostdin -v error -y -i "$OUT.mp4" -vf scale=720:1280 -c:v libx264 -preset slow -b:v ${VB}k -pass 1 -passlogfile /tmp/wa2p -an -f mp4 /dev/null
  ffmpeg -nostdin -v error -y -i "$OUT.mp4" -vf scale=720:1280 -c:v libx264 -preset slow -b:v ${VB}k -pass 2 -passlogfile /tmp/wa2p -c:a aac -b:a 96k -movflags +faststart "$OUT-WA.mp4"
fi
for f in "$OUT.mp4" "$OUT-WA.mp4"; do [ -f "$f" ] && echo "$f $(du -h "$f" | cut -f1) $(ffmpeg -nostdin -hide_banner -i "$f" -af ebur128=peak=true -f null - 2>&1 | grep -E '^\s+(I|Peak):' | tr -s ' ' | tr '\n' ' ')"; done
