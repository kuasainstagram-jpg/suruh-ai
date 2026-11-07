# Katalog 30 Gaya — Gaya 2.0: kod, bila guna, parameter

Masa (`start`, `dur`) dalam **saat video sumber** (sama seperti `words.json`). `**perkataan**` dalam teks = warna emas.
Setiap gaya ialah satu entri dalam `items` di `plan.json`, kecuali **caption** (C01/C02/C03/C05/C06/C07 → medan `captions`) dan **X03** (medan `punch`).

## H · Hook (pembuka — letak pada `start: 0`)
| Kod | Nama | Bila guna | Parameter |
|---|---|---|---|
| H01 | Jangan Scroll | Hampir semua video sosial; frame pertama jadi thumbnail | `title` (wajib, guna `**` untuk emas), `badge` (lalai "JANGAN SCROLL DULU!") |
| H02 | Angka Besar | Video hasil / bukti — angka **sebenar** yang pengguna beri | `value` (nombor), `prefix` (lalai "RM"), `decimals`, `label`, `sub` |
| H03 | Soalan Kinetik | Video bermula dengan soalan | ambil perkataan dari transkrip dalam `[start, start+dur]` secara automatik; `gold_words` [senarai] |
| H04 | Freeze + Tajuk | Tutorial / bab; video bermula dengan tajuk | `title`, `kicker`; `dur` (lalai 1.5) — video ditunda sebanyak `dur` |
| H06 | Perkataan Besar Belakang Kepala | Satu perkataan paling penting (angka / benda yang dibincang) **duduk di belakang kepala**, pop tepat bila disebut. Badan dipotong keluar automatik (±1 minit bagi 4 s). Rakam dengan ruang di atas kepala | `word`, `start` (masa perkataan disebut), `dur` (lalai 3.5), `size`, `color` |
| H05 | Sebelum / Selepas | Transformasi; perlu **2 klip** | `before` (fail dalam assets/), `before_start`, `label1`, `sub1`, `label2`, `sub2` |

## C · Caption (biasanya **satu** untuk seluruh video → `"captions": "C01"`)
Boleh juga tukar gaya ikut masa: `"captions": [{"style": "C01", "from": 0, "to": 20}, {"style": "C03", "from": 20, "to": 40}]`.
| Kod | Nama | Bila guna |
|---|---|---|
| C01 | Kata Kunci Emas | Lalai terbaik untuk Reels/TikTok/Threads |
| C02 | Mesra Warga Emas | Penonton berusia, video testimoni, website |
| C03 | Karaoke | Ucapan perlahan & jelas; motivasi |
| C05 | Kotak Putih | Gaya TikTok, latar sibuk |
| C06 | Typewriter | Tips teknikal, AI, coding |
| C07 | Neon | Video malam / vibe teknologi |
| C04 | Punch Word | **Item**, bukan caption: satu perkataan besar pada satu saat. `word`, `start` (masa perkataan itu disebut), `dur` (lalai 1.4) |

`keywords`: senarai perkataan yang diwarnakan (emas). Nombor sentiasa diwarnakan.
`emoji`: (C01) `{"perkataan": "😀"}` — emoji pop di atas caption bila perkataan itu disebut. Guna 3–6 sahaja, pada kata kunci.

## T · Tajuk
| Kod | Nama | Parameter |
|---|---|---|
| T01 | Trailer Krom | `line1`, `line2` |
| T02 | Title Slam | `text` (guna `|` untuk baris baru) |
| T04 | Kad Bab (skrin penuh) | `num`, `line1`, `line2` |

## N · Angka & Bukti (angka **mesti** daripada pengguna atau skrin mereka — jangan reka)
| Kod | Nama | Parameter |
|---|---|---|
| N01 | Kaunter RM | `value`, `label`, `prefix` (lalai "RM "), `decimals` (lalai 2), `count` (false = terus papar angka tepat, untuk bukti) |
| N02 | Sorot Penyata | `asset` (rakaman skrin dalam assets/), `media_start`, `box` [x0,y0,x1,y1] dalam piksel aset, `box_width` (lebar aset), `tag` |
| N03 | Jalur Hari/Bulan | `steps` [[label, nilai], …] (2–5 langkah) |
| N04 | Carta Naik | `bars` [[nama, nilai, label_atau_""], …], `label`, `title`, `source` (cth. "Sumber: dashboard OnPay") |

## K · Kad & Grafik
| Kod | Nama | Parameter |
|---|---|---|
| K01 | Kad Kaca | `title`, `items` [2–4] |
| K02 | Sebelum/Selepas | `before_label`, `before`, `after_label`, `after` |
| K03 | Aliran Langkah | `steps` [3–5, pendek] |
| K04 | Checklist | `title`, `items` [2–4] |
| K05 | Lower-third | `name`, `role` — letak dalam 8 saat pertama |

## X · Transisi & Kamera
| Kod | Nama | Cara guna |
|---|---|---|
| X01 | Whip Pan | item `{"code":"X01","start":t}` — pada potongan / pertukaran topik |
| X02 | Flash Oren | item `{"code":"X02","start":t}` — pada potongan |
| X03 | Punch-in Auto | `"punch": [t1, t2, …]` — masa perkataan yang ditekankan (3–6 kali seminit) |

## E · Penutup (letak pada 4–5 saat terakhir)
| Kod | Nama | Parameter |
|---|---|---|
| E01 | CTA Produk | `image` (fail dalam assets/), `title`, `button`, `sub` |
| E02 | Follow Card | `name`, `handle`, `line`, `button` (lalai "+ FOLLOW"), `avatar_at` (saat sumber untuk wajah) |

## Gabungan yang disyorkan (mod auto)
- **Talking head biasa (30–60 s):** H01 + C01 + X03 + K03/K04 + E02
- **Testimoni / bukti hasil:** H02 + C02 + N02 (atau N01 `count:false`) + K05 + E01
- **Tutorial / tips:** H04 + C06 + T04 + K03 + K04 + E02
- **Promosi produk:** H01 + C01 + K01 + N04 + E01
- **Cerita perjalanan:** H05 + C03 + N03 + X02 + E02

## Lapisan Gaya 2.0 (automatik)
- `"pop": true` (lalai) — gred warna pop: lebih kontras & warna + vignette lembut. `false` untuk footage asal.
- `"progress": true` (lalai) — bar progres jingga di atas video (orang tonton sampai habis).
- `"sfx": true` (lalai) — bunyi: boom, riser, pop, ding, klik, whoosh, rewind — diletak automatik oleh setiap gaya.
- Gaya visual: sticker putih berbingkai hitam + bayang keras, outline tebal pada teks, lantunan & gegaran.
- Gabungan "wow" disyorkan untuk talking head: **H01 + C01 (dengan `emoji`) + X03 + N01/K04 + E02** (+ **P31 Preview Dulu** jika pek premium dipasang).
