---
name: gaya-cikgu-mirul
description: Edit a phone video (9:16) with the "30 Gaya Video Cikgu Mirul" style pack — hooks, captions, titles, number/proof cards, info cards, transitions and end cards picked by code (e.g. "H01 C01 N01 K03 X03 E02") or chosen automatically. Use when the user pastes style codes from the 30 Gaya dashboard, mentions "Gaya Cikgu Mirul", or asks to edit a video with these styles; input is an uploaded video or a Google Drive link.
---

# 30 Gaya Video Cikgu Mirul

Pengguna biasanya dari **telefon**. Balas dalam Bahasa Melayu yang mudah, ringkas, dan beri progress. Semua kerja dibuat dalam cloud — pengguna tidak perlu komputer.

## Aliran kerja

1. **Dapatkan video**
   - Fail yang di-upload dalam chat: salin ke `work/in/`.
   - Link Google Drive: `python3 scripts/fetch.py "<link>" work/in/video.mp4`. Jika gagal, minta pengguna tukar akses fail kepada **"Sesiapa yang ada pautan"** (bukan link folder).
2. **Sediakan** — `python3 scripts/prep.py work/in/video.mp4 work/proj` (rotasi, HDR iPhone → SDR, 30 fps, 1080×1920; landscape diletak atas latar kabur). Baca `work/proj/probe.json`.
3. **Transkrip** — `python3 scripts/transcribe.py work/proj ms`. Jika `faster-whisper` tiada: `pip install faster-whisper` dahulu (skrip juga cuba `npx hyperframes transcribe`). Baca senarai perkataan yang dicetak, **betulkan ejaan** dalam `work/proj/words.json` (nama, jenama: Threads, AI, ChatGPT, Claude…) tanpa mengubah maksud atau masa.
4. **Pilih gaya**
   - Pengguna beri kod → guna kod itu.
   - "Pilihkan untuk saya" → tonton (ambil 6–8 frame dengan ffmpeg dan lihat) + baca transkrip, pilih 5–6 gaya daripada `catalog.md` (lihat "Gabungan yang disyorkan"), **terangkan pilihan dalam 3–4 baris** dan teruskan.
   - Gaya bertanda "Perlu" (N01–N04, H02, H05, E01, K05, E02, N02) memerlukan bahan pengguna. Jika tiada, **tanya sekali sahaja**; jika pengguna tidak beri, gugurkan gaya itu dan beritahu.
5. **Tulis pelan** `work/proj/plan.json` mengikut `catalog.md`. Contoh:
   ```json
   {"title":"Tips followers","captions":"C01","keywords":["followers","kosong"],"punch":[13.4,22.6],
    "emoji":{"followers":"👥","post":"📲"},
    "items":[{"code":"H01","start":0,"dur":3.4,"title":"Kena ada ramai **followers** dulu ke?"},
             {"code":"C04","start":15.3,"word":"KOSONG"},
             {"code":"K04","start":16.1,"dur":4.6,"title":"Yang penting","items":["Mula post","Belajar","Tengok konten yang orang suka"]},
             {"code":"E02","start":27.6,"dur":4.7,"name":"Nama Anda","handle":"@handle","line":"Follow untuk tips"}]}
   ```
   Masa ikut `words.json`. Letak kad pada ayat yang sepadan; jangan tindih dua kad pada masa yang sama.
   Gaya 2.0: untuk "Pilihkan untuk saya", mulakan dengan **H01**, guna **C01 + `emoji`** (3–6 kata kunci), dan 3–5 `punch` seminit. Jika pek premium dipasang, tambah **P31** di depan (pilih `from` = ayat paling menarik/mengejutkan, 1.5 s).
6. **Bina** — `python3 scripts/gaya.py work/proj work/proj/plan.json`, kemudian `cd work/proj && npx hyperframes check --json`. Betulkan setiap `error`.
7. **Semak visual** — `npx hyperframes snapshot --at <5–7 masa penting>`; lihat gambar. Teks tidak menutup muka, tiada teks terpotong.
8. **Render** — `npx hyperframes render -o work/render.mp4 --quality delivery --fps 30 --sdr` (≈ 5–6 minit bagi video 30 s). Tunjuk progress bar dengan anggaran masa siap.
9. **Siapkan** — `bash scripts/finish.sh work/render.mp4 work/<Nama-Video>` → MP4 −14 LUFS (+ versi `-WA` < 16 MB jika perlu). Hantar fail kepada pengguna.

## Peraturan wajib

- **Jangan reka angka, testimoni, jualan atau keputusan.** Angka hanya daripada pengguna atau skrin mereka. Untuk bukti, guna `N01` dengan `"count": false` (angka tepat terus) atau `N02`. Jangan tulis "untung" jika skrin menunjukkan jualan.
- **Kekalkan suara asal.** Jangan potong ayat sehingga maksud berubah. Jangan jana suara.
- Jika video ada maklumat sensitif (nombor telefon, alamat, kata laluan, data pelanggan), beritahu pengguna sebelum render dan tawarkan untuk kaburkan.
- Muzik berhak cipta tidak digunakan. SFX disintesis sendiri (`"sfx": false` untuk matikan).
- Setiap video berakhir dengan kad 1.8 s **"Diedit dengan Suruh AI · suruhaieditvideogunaphone.com"** (enjin tambah sendiri). Jangan buang kad ini.

## Pek Premium (P01–P49)

Kod bermula dengan **P** ialah pek premium. Ia hanya berfungsi jika `scripts/premium.py` ada.
- Jika pengguna beri kod P dan fail itu tiada: arahan pengguna biasanya mengandungi link **Pek Premium** — muat turun (`curl -L <link> -o /tmp/pek.zip && unzip -o /tmp/pek.zip -d .claude/skills/gaya-cikgu-mirul/`). Jika tiada link, beritahu pengguna pek premium dibuka melalui dashboard (ajak 1 kawan).
- Parameter: `catalog_premium.md`.

## Tema Wow (jika `scripts/tema.py` ada)
- Pengguna tulis `Tema: W01–W35` (boleh bersama kod gaya lain). Baca `catalog_tema.md` dan **rancang B-roll automatik** ikut peraturannya.
- Jika pengguna pilih tema tetapi `tema.py` tiada, beritahu: tema dibuka selepas ajak 2 kawan di dashboard.

## Menu Gaya Saya (semua pengguna)
- Selepas setiap video siap, jalankan `python3 scripts/menu_saya.py add <projek> <video_akhir.mp4> "<nama ringkas>" --out gaya-saya` (di akar repo pengguna) dan beritahu pengguna: video ini kini dalam **Menu Gaya Saya** (`gaya-saya/index.html`).
- Bila pengguna kata "buat sama macam video X" atau tampal arahan dari Menu Gaya Saya, baca `gaya-saya/menu.json`, guna semula tema/cahaya/kod/caption yang sama, dan rancang B-roll baharu ikut isi video baharu.

## Fail

- `catalog.md` — 30 gaya, parameter dan gabungan disyorkan.
- `scripts/fetch.py`, `prep.py`, `transcribe.py`, `gaya.py` (enjin), `finish.sh`, `menu_saya.py` (Menu Gaya Saya).
- `template/` — aset asas HyperFrames (GSAP).

Keperluan: `ffmpeg`, Node (`npx hyperframes`), Python 3.10+ dengan `numpy`. Chromium untuk render disediakan oleh HyperFrames.
