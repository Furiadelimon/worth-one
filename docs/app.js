/* Worth One - shared site script: anonymous session id, event beacons, share helpers, support intent, car fund. */
(function () {
  const API = (window.WO_API || "").replace(/\/$/, "");
  const P = new URLSearchParams(location.search);
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
  const rnd = () => { const a = new Uint8Array(12); (crypto.getRandomValues ? crypto.getRandomValues(a) : a.map(() => Math.random() * 256)); return Array.from(a, b => b.toString(16).padStart(2, "0")).join(""); };
  let sid = store("wo_sid"); if (!sid) { sid = rnd(); store("wo_sid", sid); }
  // attribution: keep the first source we ever saw for this browser
  const src = P.get("src") || P.get("utm_source") || store("wo_src") || (document.referrer ? (new URL(document.referrer).hostname.replace(/^www\./, "")) : "");
  if (src && !store("wo_src")) store("wo_src", src.slice(0, 40));
  const camp = P.get("c") || P.get("utm_campaign") || store("wo_c") || ""; if (camp && !store("wo_c")) store("wo_c", camp.slice(0, 40));
  const ref = P.get("r") || store("wo_ref") || ""; if (ref && !store("wo_ref") && ref !== sid) store("wo_ref", ref.slice(0, 64));
  const drop = document.body.dataset.drop || "";

  function send(t, meta, extra) {
    if (!API) return Promise.resolve();
    const body = Object.assign({ t, d: drop, sid, src: store("wo_src") || "", c: store("wo_c") || "", ref: store("wo_ref") || "", m: meta || {} }, extra || {});
    try {
      return fetch(API + "/v1/e", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), keepalive: true }).catch(() => {});
    } catch (e) { return Promise.resolve(); }
  }
  function toast(msg) { let t = document.querySelector(".toast"); if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); } t.textContent = msg; t.classList.add("on"); setTimeout(() => t.classList.remove("on"), 2200); }
  function shareUrl(extra) { const u = new URL(location.href.split("?")[0]); u.searchParams.set("r", sid); if (extra) Object.keys(extra).forEach(k => u.searchParams.set(k, extra[k])); return u.toString(); }
  async function share(opts) {
    const url = shareUrl(opts.params); const text = opts.text || document.title;
    send("share", { how: "start" });
    if (navigator.share) {
      try {
        const data = { title: document.title, text, url };
        if (opts.file && navigator.canShare && navigator.canShare({ files: [opts.file] })) { data.files = [opts.file]; }
        await navigator.share(data); send("share", { how: "native" }); return true;
      } catch (e) { if (e && e.name === "AbortError") return false; }
    }
    try { await navigator.clipboard.writeText(text + " " + url); toast("Link copied. Paste it anywhere."); send("share", { how: "copy" }); return true; } catch (e) { prompt("Copy this link:", url); send("share", { how: "prompt" }); return true; }
  }
  function support(amount, email, onlyEmail) {
    if (!API) return Promise.resolve({ ok: false });
    return fetch(API + "/v1/support", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ sid, d: drop, amount, email: email || null, only_email: !!onlyEmail, src: store("wo_src") || "", c: store("wo_c") || "" }) }).then(r => r.json()).catch(() => ({ ok: false }));
  }
  function mountSupport(el) {
    if (!el) return;
    el.innerHTML = '<h3>Was this worth at least €1 to you?</h3><p class="small muted">Honest answer. Nothing is charged: payments are not open yet, this only measures whether the experiment deserves to exist.</p>' +
      '<div class="opts"><button data-a="1">Worth €1</button><button data-a="3">Worth €3</button><button data-a="5">Worth €5</button><button class="no" data-a="0">Not worth €1</button></div><div class="after" hidden></div>';
    el.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
      const a = +b.dataset.a; el.querySelectorAll("button").forEach(x => x.disabled = true); b.style.background = "#151515"; b.style.color = "#fff";
      support(a);
      const after = el.querySelector(".after"); after.hidden = false;
      if (a > 0) {
        after.innerHTML = '<p><b>Thank you.</b> That is recorded as intention, not money. Real payments stay closed until enough people say this is worth it.</p>' +
          '<p class="small">Want to be told when supporting becomes possible? (Only for that, nothing else.)</p><div class="row"><input type="email" placeholder="your@email" style="max-width:260px"><button class="btn sm">Tell me</button></div><p class="small muted">Or the free way to help: <a href="#" class="share-after">share it</a>.</p>';
        const inp = after.querySelector("input"), btn = after.querySelector(".btn");
        btn.addEventListener("click", async () => { const v = inp.value.trim(); if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { toast("That email does not look right"); return; } btn.disabled = true; await support(a, v, true); after.innerHTML = "<p><b>Noted.</b> You will hear from a human, once, if payments open. Thank you for being one of the first.</p>"; });
        after.querySelector(".share-after").addEventListener("click", e => { e.preventDefault(); share({ text: "Free little tool I found: " + document.title }); });
      } else {
        after.innerHTML = '<p class="small muted">Fair. Thanks for the honesty. The experiment kills what is not worth it.</p>';
      }
    }));
  }
  async function fund(el) {
    if (!el) return;
    let s = null;
    if (API) { try { s = await (await fetch(API + "/v1/stats")).json(); } catch (e) {} }
    const f = s ? s.fund : { car_target: 15000, real: 0, real_pct: 0, people_worth_1plus: 0, intended_value: 0, payments_enabled: false };
    el.querySelector(".bar i").style.width = Math.max(0.5, f.real_pct) + "%";
    el.querySelector(".real").textContent = "€" + f.real.toFixed(0) + " / €" + f.car_target.toLocaleString("en");
    el.querySelector(".people").textContent = f.people_worth_1plus.toLocaleString("en");
    el.querySelector(".intended").textContent = "€" + f.intended_value.toLocaleString("en");
    if (s) { const u = document.querySelector("[data-stat=users]"); if (u) u.textContent = s.users.toLocaleString("en"); const c = document.querySelector("[data-stat=countries]"); if (c) c.textContent = s.countries; }
  }
  window.WO = { sid, send, share, shareUrl, support, mountSupport, fund, toast, param: k => P.get(k) };
  send("page_view", { path: location.pathname, ref: ref ? 1 : 0 });
  document.addEventListener("DOMContentLoaded", () => { fund(document.querySelector(".fund")); mountSupport(document.querySelector(".support")); document.querySelectorAll("[data-share]").forEach(b => b.addEventListener("click", e => { e.preventDefault(); share({ text: b.dataset.share }); })); });
})();
