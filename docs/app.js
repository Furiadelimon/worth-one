/* Worth One - shared site script: anonymous session id, event beacons, share panel, support intent, car fund, cross-drop. */
(function () {
  const API = (window.WO_API || "").replace(/\/$/, "");
  const SITE = (window.WO_SITE || "").replace(/\/$/, "");
  const P = new URLSearchParams(location.search);
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
  const rnd = () => { const a = new Uint8Array(12); if (window.crypto && crypto.getRandomValues) crypto.getRandomValues(a); else for (let i = 0; i < 12; i++) a[i] = Math.random() * 256; return Array.from(a, b => b.toString(16).padStart(2, "0")).join(""); };
  let sid = store("wo_sid"); if (!sid) { sid = rnd(); store("wo_sid", sid); }
  let refHost = ""; try { refHost = document.referrer ? new URL(document.referrer).hostname.replace(/^www\./, "") : ""; } catch (e) {}
  const ownHost = location.hostname;
  const src = P.get("src") || P.get("utm_source") || store("wo_src") || (refHost && refHost !== ownHost ? refHost : "");
  if (src && !store("wo_src")) store("wo_src", src.slice(0, 40));
  const camp = P.get("c") || P.get("utm_campaign") || store("wo_c") || ""; if (camp && !store("wo_c")) store("wo_c", camp.slice(0, 40));
  const ref = P.get("r") || store("wo_ref") || ""; if (ref && !store("wo_ref") && ref !== sid) store("wo_ref", ref.slice(0, 64));
  const drop = document.body.dataset.drop || "";
  const inFrame = window.top !== window.self;
  const LANG = document.body.dataset.lang || document.documentElement.lang || "en";
  const ES = LANG.startsWith("es");
  const T = ES ? { share: "Compartir ticket", copy: "Copiar enlace", copied: "Copiado. Pégalo donde quieras.", dl: "Imagen descargada + enlace copiado", q: "¿Te ha valido al menos 1 €?", qsub: "Respuesta sincera. No se cobra nada: los pagos no están abiertos, esto solo mide si el experimento merece existir.", w1: "Vale 1 €", w3: "Vale 3 €", w5: "Vale 5 €", no: "No vale 1 €", thanks: "<b>Gracias.</b> Queda registrado como intención, no como dinero. Los pagos reales siguen cerrados hasta que suficiente gente diga que esto vale la pena.", tell: "¿Quieres que te avisen cuando se pueda apoyar? (Solo para eso, nada más.)", tellbtn: "Avísame", or: "O la forma gratis de ayudar: ", send1: "envíaselo a una persona", noted: "<p><b>Anotado.</b> Te escribirá una persona, una sola vez, si se abren los pagos. Gracias por ser de los primeros.</p>", fair: "Justo. Gracias por la sinceridad. El experimento elimina lo que no vale la pena.", bademail: "Ese email no parece correcto", found: "Herramienta gratis que he encontrado: " }
    : { share: "Share receipt", copy: "Copy link", copied: "Copied. Paste it anywhere.", dl: "Image downloaded + link copied", q: "Was this worth at least €1 to you?", qsub: "Honest answer. Nothing is charged: payments are not open yet, this only measures whether the experiment deserves to exist.", w1: "Worth €1", w3: "Worth €3", w5: "Worth €5", no: "Not worth €1", thanks: "<b>Thank you.</b> That is recorded as intention, not money. Real payments stay closed until enough people say this is worth it.", tell: "Want to be told when supporting becomes possible? (Only for that, nothing else.)", tellbtn: "Tell me", or: "Or the free way to help: ", send1: "send it to one person", noted: "<p><b>Noted.</b> You will hear from a human, once, if payments open. Thank you for being one of the first.</p>", fair: "Fair. Thanks for the honesty. The experiment kills what is not worth it.", bademail: "That email does not look right", found: "Free little tool I found: " };

  function send(t, meta, extra) {
    if (!API) return Promise.resolve();
    const body = Object.assign({ t, d: drop, sid, src: store("wo_src") || "", c: store("wo_c") || "", ref: store("wo_ref") || "", m: meta || {} }, extra || {});
    try {
      return fetch(API + "/v1/e", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), keepalive: true }).catch(() => {});
    } catch (e) { return Promise.resolve(); }
  }
  function toast(msg) { let t = document.querySelector(".toast"); if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); } t.textContent = msg; t.classList.add("on"); setTimeout(() => t.classList.remove("on"), 2400); }
  function shareUrl(extra) { const u = new URL(location.href.split("?")[0]); u.searchParams.set("r", sid); if (extra) Object.keys(extra).forEach(k => u.searchParams.set(k, extra[k])); return u.toString(); }
  async function share(opts) {
    opts = opts || {};
    const url = shareUrl(opts.params); const text = opts.text || document.title;
    send("share", { how: "start", via: opts.via || "native" });
    if (navigator.share) {
      try {
        const data = { title: document.title, text, url };
        if (opts.file && navigator.canShare && navigator.canShare({ files: [opts.file] })) { data.files = [opts.file]; }
        await navigator.share(data); send("share", { how: "native" }); return true;
      } catch (e) { if (e && e.name === "AbortError") return false; }
    }
    return copy(text + " " + url);
  }
  async function copy(s) { try { await navigator.clipboard.writeText(s); toast(T.copied); send("share", { how: "copy" }); return true; } catch (e) { prompt("Copy this:", s); send("share", { how: "prompt" }); return true; } }
  function via(net, opts) {
    const url = shareUrl(opts.params); const text = (opts.text || document.title);
    const enc = encodeURIComponent;
    const links = {
      whatsapp: "https://wa.me/?text=" + enc(text + " " + url),
      telegram: "https://t.me/share/url?url=" + enc(url) + "&text=" + enc(text),
      email: "mailto:?subject=" + enc(document.title) + "&body=" + enc(text + "\n\n" + url),
    };
    send("share", { how: net });
    window.open(links[net], net === "email" ? "_self" : "_blank", "noopener");
  }
  const ICON = {
    img: '<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M6 16l4-5 3 4 2-2 3 3z"/></svg>',
    wa: '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5.1-1.3A10 10 0 1 0 12 2zm0 18a8 8 0 0 1-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8 8 0 1 1 12 20zm4.4-6c-.2-.1-1.4-.7-1.6-.8s-.4-.1-.5.1-.6.8-.8 1-.3.2-.5.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.3-.4.7-1.3.1-.2 0-.3 0-.4l-.7-1.8c-.2-.5-.4-.4-.5-.4h-.5a1 1 0 0 0-.7.3 2.9 2.9 0 0 0-.9 2.2 5 5 0 0 0 1.1 2.7 11.4 11.4 0 0 0 4.4 3.9c1.6.7 2.3.7 3.1.6a2.6 2.6 0 0 0 1.7-1.2 2 2 0 0 0 .2-1.2c-.1-.1-.3-.2-.5-.3z"/></svg>',
    tg: '<svg viewBox="0 0 24 24"><path d="M21.9 4.6 18.9 19c-.2 1-.8 1.2-1.6.8l-4.5-3.3-2.2 2.1c-.2.2-.4.4-.9.4l.3-4.6 8.4-7.6c.4-.3-.1-.5-.6-.2L7.4 13.2 2.9 11.8c-1-.3-1-1 .2-1.4l17.5-6.8c.8-.3 1.5.2 1.3 1z"/></svg>',
    mail: '<svg viewBox="0 0 24 24"><path d="M3 5h18v14H3z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 7l9 6 9-6" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    link: '<svg viewBox="0 0 24 24"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  };
  function mountShare(el, get) {
    if (!el) return;
    el.innerHTML = '<button class="primary" data-s="img">' + ICON.img + T.share + '</button><button data-s="whatsapp">' + ICON.wa + 'WhatsApp</button><button data-s="telegram">' + ICON.tg + 'Telegram</button><a data-s="email" href="#">' + ICON.mail + 'Email</a><button data-s="link">' + ICON.link + T.copy + '</button>';
    el.querySelectorAll("[data-s]").forEach(b => b.addEventListener("click", async e => {
      e.preventDefault(); const o = get() || {}; const s = b.dataset.s;
      if (s === "img") { if (o.makeFile) { const file = await o.makeFile(); send("share_card", o.meta || {}); const ok = await share({ text: o.text, params: o.params, file }); if (!(navigator.canShare && navigator.canShare({ files: [file] }))) { const a = document.createElement("a"); a.href = URL.createObjectURL(file); a.download = file.name; a.click(); toast(T.dl); } } else share({ text: o.text, params: o.params }); }
      else if (s === "link") copy(shareUrl(o.params));
      else via(s, o);
    }));
  }
  function support(amount, email, onlyEmail) {
    if (!API) return Promise.resolve({ ok: false });
    return fetch(API + "/v1/support", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ sid, d: drop, amount, email: email || null, only_email: !!onlyEmail, src: store("wo_src") || "", c: store("wo_c") || "" }) }).then(r => r.json()).catch(() => ({ ok: false }));
  }
  function mountSupport(el) {
    if (!el) return;
    el.innerHTML = '<h3>' + T.q + '</h3><p class="small muted">' + T.qsub + '</p>' +
      '<div class="opts"><button data-a="1">' + T.w1 + '</button><button data-a="3">' + T.w3 + '</button><button data-a="5">' + T.w5 + '</button><button class="no" data-a="0">' + T.no + '</button></div><div class="after" hidden></div>';
    el.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
      const a = +b.dataset.a; el.querySelectorAll("button").forEach(x => x.disabled = true); b.style.background = "var(--ink)"; b.style.color = "var(--bg)";
      support(a);
      const after = el.querySelector(".after"); after.hidden = false;
      if (a > 0) {
        after.innerHTML = '<p>' + T.thanks + '</p>' +
          '<p class="small">' + T.tell + '</p><div class="row"><input type="email" placeholder="tu@email" style="max-width:260px"><button class="btn sm">' + T.tellbtn + '</button></div><p class="small muted">' + T.or + '<a href="#" class="share-after">' + T.send1 + '</a>.</p>';
        const inp = after.querySelector("input"), btn = after.querySelector(".btn");
        btn.addEventListener("click", async () => { const v = inp.value.trim(); if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { toast(T.bademail); return; } btn.disabled = true; await support(a, v, true); after.innerHTML = T.noted; });
        after.querySelector(".share-after").addEventListener("click", e => { e.preventDefault(); share({ text: T.found + document.title }); });
      } else {
        after.innerHTML = '<p class="small muted">' + T.fair + '</p>';
      }
    }));
  }
  async function fund(el) {
    let s = null;
    if (API) { try { s = await (await fetch(API + "/v1/stats")).json(); } catch (e) {} }
    const f = s ? s.fund : { car_target: 30000, real: 0, real_pct: 0, people_worth_1plus: 0, intended_value: 0, payments_enabled: false };
    if (el && el.querySelector(".bar i")) {
      el.querySelector(".bar i").style.width = Math.max(0.5, f.real_pct) + "%";
      const q = k => el.querySelector(k);
      if (q(".real")) q(".real").textContent = "€" + f.real.toFixed(0) + " / €" + f.car_target.toLocaleString("en");
      if (q(".people")) q(".people").textContent = f.people_worth_1plus.toLocaleString("en");
      if (q(".intended")) q(".intended").textContent = "€" + f.intended_value.toLocaleString("en");
    }
    // v3: small honest numbers on the home "experiment" block; hidden unless real data exists
    const st = document.getElementById("expStats");
    if (s && st && s.users >= 5) {
      const u = st.querySelector("[data-stat=users]"); if (u) u.textContent = s.users.toLocaleString("en");
      const c = st.querySelector("[data-stat=countries]"); if (c) c.textContent = s.countries;
      const r = st.querySelector("[data-stat=real]"); if (r) r.textContent = "€" + f.real.toFixed(0);
      st.hidden = false;
    }
  }
  function mountSubscribe(form) {
    if (!form) return;
    const msg = document.getElementById("subscribeMsg");
    form.addEventListener("submit", async e => {
      e.preventDefault(); const inp = form.querySelector("input"); const v = inp.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { toast(T.bademail); return; }
      form.querySelector("button").disabled = true;
      if (API) { try { await fetch(API + "/v1/subscribe", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ sid, email: v, lang: LANG }) }); } catch (x) {} }
      form.hidden = true; if (msg) msg.textContent = ES ? "Hecho. Solo el próximo drop, nada más." : "Done. Just the next drop, nothing else.";
    });
  }
  async function compare(d, v) { if (!API) return null; try { return await (await fetch(API + "/v1/compare?d=" + d + "&v=" + v)).json(); } catch (e) { return null; } }
  window.WO = { sid, send, share, shareUrl, support, mountSupport, mountShare, fund, toast, compare, copy, param: k => P.get(k), site: SITE };
  if (inFrame && document.body.dataset.embed) { let host = ""; try { host = new URL(document.referrer).hostname; } catch (e) {} send("embed_view", { host, path: location.pathname }); }
  else send("page_view", { path: location.pathname, ref: ref ? 1 : 0 });
  function langBanner() {
    try {
      if (inFrame || store("wo_lang")) return;
      const nav = (navigator.language || "").toLowerCase();
      const path = location.pathname.replace(/^.*\/worth-one/, "");
      const onEs = /^\/es(\/|$)/.test(path);
      if (nav.startsWith("es") && !onEs && !ES) {
        const b = document.createElement("div"); b.className = "note"; b.style.cssText = "margin:8px auto 0;max-width:720px;display:flex;justify-content:space-between;gap:10px;align-items:center";
        b.innerHTML = '<span>Esta página también está en español.</span><span><a href="' + SITE + "/es" + path + '" style="font-weight:700">Ver en español →</a> <a href="#" style="margin-left:10px;color:inherit" class="x">✕</a></span>';
        b.querySelector(".x").addEventListener("click", e => { e.preventDefault(); store("wo_lang", "en"); b.remove(); });
        document.body.prepend(b);
      } else if (ES) { store("wo_lang", "es"); }
    } catch (e) {}
  }
  document.addEventListener("DOMContentLoaded", () => {
    langBanner(); fund(document.querySelector(".fund")); mountSupport(document.querySelector(".support")); mountSubscribe(document.getElementById("subscribe"));
    document.querySelectorAll("[data-share]").forEach(b => b.addEventListener("click", e => { e.preventDefault(); share({ text: b.dataset.share }); }));
    document.querySelectorAll("[data-nav]").forEach(a => a.addEventListener("click", () => send("drop_nav", { to: a.dataset.nav })));
  });
})();
