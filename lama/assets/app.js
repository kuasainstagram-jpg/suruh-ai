// Shared helpers for the landing page and the member dashboard.
const C = window.CONFIG;
const $ = id => document.getElementById(id);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  del(k) { try { localStorage.removeItem(k); } catch (e) {} },
};

async function rpc(fn, args) {
  const r = await fetch(`${C.SUPABASE_URL}/rest/v1/rpc/${fn}`, {
    method: "POST",
    // new "sb_publishable_…" keys go in the apikey header only; legacy JWT anon keys ("eyJ…") also as Bearer
    headers: Object.assign({ apikey: C.SUPABASE_ANON_KEY, "Content-Type": "application/json" }, String(C.SUPABASE_ANON_KEY).startsWith("eyJ") ? { Authorization: `Bearer ${C.SUPABASE_ANON_KEY}` } : {}),
    body: JSON.stringify(args),
  });
  if (!r.ok) throw new Error(`Pelayan tidak dapat dihubungi (${r.status}). Cuba lagi sebentar.`);
  return r.json();
}

const ERR = {
  NAME: "Sila isi nama penuh anda.",
  EMAIL: "Format email tidak betul.",
  EMAIL_TEMP: "Email sementara tidak diterima. Guna email biasa anda (Gmail, Yahoo, dll).",
  PHONE: "Nombor telefon Malaysia tidak betul. Contoh: 012-345 6789.",
  CONSENT: "Sila tanda kotak persetujuan untuk teruskan.",
  EXISTS: "Email atau nombor ini sudah berdaftar. Tekan “Dah daftar? Log masuk”.",
  RATE: "Terlalu banyak pendaftaran dari rangkaian ini. Cuba lagi selepas sejam.",
  CODE: "Kod tidak sepadan. Semak mesej yang di-pin dalam grup WhatsApp anda.",
  LOCKED: "Terlalu banyak cubaan. Cuba lagi selepas sejam.",
  TOKEN: "Sesi tidak dijumpai. Sila log masuk semula.",
  NOTFOUND: "Tiada pendaftaran dengan email dan nombor ini.",
};
const errText = e => ERR[e] || "Ada masalah. Cuba lagi.";

function toast(msg) {
  const t = $("toast"); if (!t) return;
  t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 2400);
}

function copyText(text, fallbackId) {
  const fb = fallbackId && $(fallbackId);
  navigator.clipboard.writeText(text)
    .then(() => { if (fb) fb.hidden = true; toast("Disalin ✓"); })
    .catch(() => { if (fb) { fb.value = text; fb.hidden = false; fb.focus(); fb.select(); } toast("Tekan lama & salin teks"); });
}

function autoplayVisible(root = document) {
  const io = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target;
    if (e.isIntersecting) { if (v.preload !== "auto") v.preload = "auto"; const p = v.play(); if (p) p.catch(() => {}); } else v.pause();
  }), { rootMargin: "200px 0px" });
  root.querySelectorAll("video").forEach(v => io.observe(v));
}

function utm() {
  const q = new URLSearchParams(location.search); const o = {};
  ["utm_source", "utm_medium", "utm_campaign"].forEach(k => q.get(k) && (o[k] = q.get(k)));
  return Object.keys(o).length ? o : null;
}

// Short, trustworthy links: https://domain.com/CODE (404.html turns the path into ?ref=)
function siteBase() { return (C.SITE_URL || new URL(".", location.href).href).replace(/\/+$/, ""); }
function refLink(code) { return `${siteBase()}/${code}`; }
const pretty = u => u.replace(/^https?:\/\//, "");

// ===== Launch game: community meter + reward ladder (shared by landing, dashboard, game plan) =====
const num = n => Number(n || 0).toLocaleString("en-US");
const escH = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const KIND_BTN = { access: "Buka", class: "Masuk kelas live", pack: "Muat turun pek", storyboard_lite: "Buka Storyboard Lite", theme: "Buka Tema Wow", storyboard: "Buka Storyboard Pro", other: "Buka" };
const KIND_STOP = { access: "Pelancaran serentak", class: "Kelas live + hadiah kejutan", pack: "Pek gaya baharu", storyboard_lite: "Storyboard Lite", theme: "Tema Wow", storyboard: "Storyboard Pro", surprise: "Hadiah kejutan", other: "Hadiah baharu" };

function stops(c) {
  const by = {};
  (c.rewards || []).forEach(r => { if (r.release_at > 0) (by[r.release_at] = by[r.release_at] || []).push(r); });
  const list = Object.keys(by).map(Number).sort((a, b) => a - b).map(at => ({ at, label: KIND_STOP[by[at][0].kind] || KIND_STOP.other, items: by[at] }));
  if (!list.length || list[list.length - 1].at < c.final_goal) list.push({ at: c.final_goal, label: "Matlamat komuniti", items: [] });
  return list;
}

function journeyHTML(c) {
  const st = stops(c), max = Math.max(c.final_goal, st[st.length - 1].at), pct = Math.min(100, 100 * c.total / max);
  const nx = st.find(s => s.at > c.total);
  const k = n => (n >= 1000 ? (n / 1000).toString().replace(/\.0$/, "") + "K" : n);
  return `<div class="journey">
    <div class="j-head"><div><b class="j-total">${num(c.total)}</b> <span class="muted">ahli komuniti</span></div>
      ${nx ? `<span class="j-left">Lagi <b>${num(nx.at - c.total)}</b> → ${escH(nx.label)}</span>` : `<span class="j-left">🎉 Matlamat dicapai</span>`}</div>
    <div class="j-track" role="img" aria-label="${num(c.total)} daripada ${num(max)} ahli"><i style="width:${pct}%"></i>
      ${st.map(s => `<span class="j-dot${c.total >= s.at ? " on" : ""}" style="left:${100 * s.at / max}%"><em>${k(s.at)}</em></span>`).join("")}</div>
    <ol class="j-stops">${st.map(s => { const m = (c.milestones || []).find(x => x.at === s.at); const d = m && m.reached_at ? dateMY(m.reached_at) : "";
      return `<li class="${c.total >= s.at ? "on" : nx && s.at === nx.at ? "now" : ""}"><b>${num(s.at)}</b><span>${escH(s.label)}${d ? ` · dicapai ${d}` : ""}${s.items.length ? `<small>${s.items.map(r => escH(r.name)).join(" · ")}</small>` : ""}</span></li>`; }).join("")}</ol>
  </div>`;
}

const dateMY = d => new Date(d).toLocaleDateString("ms-MY", { day: "numeric", month: "short", year: "numeric" });

// Public celebration — like "our first million users": only milestones already reached, never the next target.
function celebrateHTML(c) {
  const hit = (c.milestones || []).filter(m => m.reached).sort((a, b) => b.at - a.at)[0];
  if (!hit) return "";
  return `<div class="celebrate"><span class="cb-n">${num(hit.at)}</span><div><b>🎉 ${num(hit.at)} ahli pertama!</b>
    <span>Terima kasih kerana bersama kami${hit.reached_at ? " · " + dateMY(hit.reached_at) : ""}.</span></div></div>`;
}

function rewardState(r, s) {
  if (r.unlocked) return { cls: "on", ic: "✓", text: "Terbuka" };
  // later rewards never show how to get them; that is revealed once the reward before is unlocked
  if (r.later) return { cls: "wait", ic: "🎁", text: "Caranya didedahkan selepas anda buka hadiah di atas" };
  const friends = Math.max(0, r.needed - r.have);
  const ask = r.needed === 0 ? "" : friends > 0 ? ` · ajak ${friends} lagi kawan` : " · syarat kawan ✓";
  if (r.surprise && !r.released) return { cls: "wait", ic: "🎁", text: "Didedahkan tidak lama lagi" + (r.needed === 0 ? " · untuk semua ahli" : ask) };
  if (!r.released) return { cls: "wait", ic: "⏳", text: "Akan dibuka tidak lama lagi" + (r.needed === 0 ? " · percuma untuk anda" : ask) };
  if (!s.verified) return { cls: "need", ic: "🔒", text: "Sahkan grup WhatsApp anda dahulu" };
  return { cls: "need", ic: "👥", text: `Ajak ${friends} lagi kawan` };
}

function ladderHTML(s) {
  return `<ul class="ladder2">${(s.rewards || []).map(r => { const st = rewardState(r, s);
    return `<li class="${st.cls}"><span class="ic" aria-hidden="true">${st.ic}</span><div class="lx"><b>${escH(r.name)}</b>${r.value ? ` <span class="val">nilai ${escH(r.value)}</span>` : ""}
      <div class="muted">${escH(st.text)}</div>${r.released && r.note ? `<div class="note">${escH(r.note)}</div>` : ""}${r.unlocked && r.url ? `<a class="btn ghost sm" href="${escH(r.url)}" target="_blank" rel="noopener">${KIND_BTN[r.kind] || KIND_BTN.other}</a>` : ""}</div></li>`; }).join("")}</ul>`;
}

// One headline for "what should I do now". Personal goals only — community targets stay on the admin page.
function nowCard(s) {
  if (s.flagged) return { eb: "Akaun disemak", title: "Akaun anda ditanda untuk semakan", text: "Hadiah digantung sementara. Hubungi admin dalam grup WhatsApp jika ini satu kesilapan.", btn: "" };
  const acc = (s.rewards || [])[0] || {};
  const firstName = acc.name || "akses";
  if (!s.access && !acc.released)
    return { eb: s.founding ? `Ahli #${num(s.member_no)} · Founding` : `Ahli #${num(s.member_no)}`,
             title: s.founding ? "Tempat percuma anda sudah dikunci 🎉" : "Anda dalam senarai menunggu",
             text: `${firstName}${acc.value ? " (nilai " + acc.value + ")" : ""} dibuka serentak tidak lama lagi. Kami maklumkan dalam grup WhatsApp.` +
                   (s.founding ? "" : ` Ajak ${acc.needed} kawan untuk akses percuma.`),
             btn: s.founding ? "Ajak kawan dapat tempat juga →" : "Ajak kawan →" };
  if (!s.access)
    return { eb: `Ahli #${num(s.member_no)}`, title: "Tempat Founding sudah penuh",
             text: s.verified ? `Ajak ${Math.max(0, acc.needed - acc.have)} kawan daftar & sahkan grup untuk akses percuma ${firstName}${acc.value ? " (nilai " + acc.value + ")" : ""}.` : "Sahkan grup WhatsApp anda dahulu, kemudian ajak kawan.",
             btn: "Ajak kawan →" };
  const nx = s.next;
  if (!nx) return { eb: "Semua hadiah", title: "🎉 Semua hadiah terbuka", text: s.vip ? "Akses VIP." : "Terima kasih kerana bersama kami.", btn: "" };
  if (nx.need_verify) return { eb: "Hadiah seterusnya", title: nx.name, text: "Sahkan grup WhatsApp anda dahulu.", btn: "" };
  if (nx.remaining > 0)
    return { eb: "Hadiah seterusnya", title: nx.name, text: `Ajak ${nx.remaining} lagi kawan daftar & sahkan grup.` + (nx.released ? "" : " Hadiah ini akan dibuka tidak lama lagi."), btn: "Ajak kawan →" };
  return { eb: "Hadiah seterusnya", title: nx.name, text: "Syarat anda sudah lengkap ✓ Hadiah ini dibuka tidak lama lagi — kami maklumkan dalam grup.", btn: "" };
}

// ===== Anti-dummy =====
// A random id kept in this browser (survives log out). Used to spot many accounts made on one phone.
function deviceId() {
  let d = store.get("dev");
  if (!d) { d = (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)); store.set("dev", d); }
  return d;
}

function rulesHTML() {
  return `<div class="rules" id="peraturan">
    <h3>Kawan yang dikira</h3>
    <ul class="rl">
      <li class="y">Kawan daftar guna link anda dengan nama, email dan nombor WhatsApp <b>mereka sendiri</b>.</li>
      <li class="y">Kawan masuk grup WhatsApp dan masukkan kod pengesahan <b>dari telefon mereka sendiri</b>.</li>
      <li class="n">Tidak dikira: nombor atau email palsu, email sementara, akaun yang didaftar atau disahkan dari telefon anda, dan banyak akaun dari satu telefon.</li>
    </ul>
    <details><summary>Bagaimana kami kesan pendaftaran palsu?</summary>
      <ol>
        <li>Setiap nombor telefon dan email hanya boleh daftar sekali (alias Gmail seperti <i>a.b+1@gmail.com</i> dikira sama).</li>
        <li>Email sementara ditolak.</li>
        <li>Kod pengesahan hanya diberi dalam grup WhatsApp, dan kami boleh semak sama ada nombor itu benar-benar ada dalam grup.</li>
        <li>Sistem mengenal pasti peranti dan rangkaian bagi setiap pendaftaran dan pengesahan.</li>
        <li>Admin menyemak senarai pendaftaran yang mencurigakan.</li>
      </ol>
    </details>
    <p class="warn">Akaun palsu akan dibatalkan. Hadiah yang dibuka melalui akaun palsu ditarik balik.</p>
  </div>`;
}

function friendsLine(s) {
  const p = [`<b>${s.referrals_verified}</b> kawan sah`];
  if (s.referrals_pending) p.push(`${s.referrals_pending} belum sahkan grup`);
  if (s.referrals_rejected) p.push(`<span class="bad">${s.referrals_rejected} tidak dikira</span>`);
  return p.join(" · ");
}

// ===== One-tap sharing =====
function waShare(text) { location.href = "https://wa.me/?text=" + encodeURIComponent(text); }
function canNativeShare() { return !!(navigator.share); }
function nativeShare(text, url) { navigator.share({ text, url }).catch(() => {}); }
function shareText(link, after) {
  const bank = (after && window.COPY_AFTER && COPY_AFTER.WhatsApp) || (window.COPY && COPY.WhatsApp) || ["Edit video macam pro guna phone je. Daftar: {link}"];
  return bank[0].replaceAll("{link}", pretty(link)).replaceAll("{brand}", C.BRAND);
}

// "🎉 Aina baru daftar guna link anda" — shown once per new verified friend
function friendNotice(s) {
  const f = (s.recent_friends || [])[0]; if (!f) return "";
  let seen = ""; try { seen = localStorage.getItem("friend_seen") || ""; } catch (e) {}
  const isNew = !seen || f.at > seen;
  try { localStorage.setItem("friend_seen", f.at); } catch (e) {}
  return `<div class="fnote${isNew ? " new" : ""}"><span class="emo-i">🎉</span><div><b>${escH(f.name)}</b> ${isNew ? "baru " : ""}daftar & sahkan grup guna link anda!<span class="muted"> Kawan sah anda: ${s.referrals_verified}</span></div></div>`;
}
