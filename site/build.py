#!/usr/bin/env python3
"""Static generator for the programmatic / content parts of the Worth One site.

Generates (into docs/):
  drops/index.html                       catalogue from engine/drops.json
  screen-time/index.html + /<slug>/      one substantial page per daily scrolling amount (search intent: "2 hours a day screen time")
  subscriptions/index.html + /<slug>/    one page per subscription service (search intent: "netflix cost over 10 years")
  notes/index.html + /<slug>.html        lab notes (content hub), from site/notes/*.md (very small markdown subset)
  embed/index.html, embed/doomscroll.html, embed/subscriptions.html, embed.js
  sitemap.xml

Every generated page has real content, not filler. Run: python site/build.py  (then commit docs/).
"""
import html
import json
import os
import re
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SITE = "https://furiadelimon.github.io/worth-one"
TODAY = dt.date.today().isoformat()
ICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23151515'/%3E%3Ctext x='32' y='44' font-size='34' text-anchor='middle' fill='%23fff' font-family='Arial' font-weight='bold'%3E€1%3C/text%3E%3C/svg%3E"
urls = []


def esc(s):
    return html.escape(str(s), quote=True)


def layout(path, title, desc, body, depth, og_image=None, ld=None, drop="", extra_head="", noindex=False):
    rel = "../" * depth
    canonical = f"{SITE}/{path}"
    if not noindex:
        urls.append(canonical)
    og = og_image or f"{SITE}/assets/og.png"
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">{robots}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{ICON}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{rel}style.css"><script src="{rel}config.js"></script><script defer src="{rel}app.js"></script>
{ldj}{extra_head}
</head>
<body data-drop="{drop}">
<div class="wrap">
<nav class="nav"><a class="brand" href="{rel}"><i>€1</i>WORTH ONE?</a><span class="links"><a href="{rel}drops/">Drops</a><a href="{rel}notes/">Lab notes</a><a href="{rel}embed/">Embed</a><a href="{rel}about.html">About</a></span></nav>
{body}
<footer><a class="brand" href="{rel}">WORTH ONE?</a><br><a href="{rel}">Home</a><a href="{rel}drops/">Drops</a><a href="{rel}notes/">Lab notes</a><a href="{rel}embed/">Embed</a><a href="{rel}about.html">About</a><a href="{rel}privacy.html">Privacy</a><a href="https://github.com/Furiadelimon/worth-one">Source</a><br><span class="tiny">An independent project by one person. Free things for strangers. One car.</span></footer>
</div>
</body>
</html>
"""


def write(path, content):
    full = os.path.join(DOCS, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def fmt_days(d):
    if d < 1:
        return f"{round(d * 24)} hours"
    if d < 60:
        return f"{round(d, 1):g} days"
    if d < 365:
        return f"{round(d)} days"
    return f"{round(d / 365.25, 2):g} years"


def fmt_h(x):
    H = int(x); M = round((x - H) * 60)
    return (f"{H}h {M}m" if M else f"{H}h") if H else f"{M}m"


# ---------------- drops catalogue ----------------
def build_drops():
    drops = json.load(open(os.path.join(ROOT, "engine", "drops.json"), encoding="utf-8"))
    order = {"LIVE": 0, "GROWING": 0, "VIRAL": 0, "TESTING": 1, "BUILDING": 2, "IDEA": 3, "PAUSED": 4, "KILLED": 5}
    drops.sort(key=lambda d: (order.get(d["status"], 9), d["drop_id"]))
    cards = []
    for d in drops:
        if d["status"] == "KILLED":
            continue
        live = d["status"] in ("LIVE", "GROWING", "VIRAL")
        num = d["drop_id"].replace("DROP-", "#")
        if live:
            cards.append(f'<a class="drop" href="{d["slug"]}/" data-nav="{d["drop_id"]}"><span class="num">{num}</span><span class="tag live">live</span><b>{esc(d["name"])}</b><p>{esc(d["concept"][:140])}</p></a>')
        else:
            tag = "soon" if d["status"] in ("BUILDING", "TESTING") or d["drop_id"] == "DROP-003" else ""
            cards.append(f'<div class="drop soon"><span class="num">{num}</span><span class="tag {tag}">{"next" if tag else "idea"}</span><b>{esc(d["name"])}</b><p>{esc(d["concept"][:140])}</p></div>')
    body = f"""<section class="hero"><span class="eyebrow">Catalogue</span><h1>All <em>drops</em></h1><p class="lead">Small web experiences you can use right now, free, no account. Live ones are ranked by use; ideas become drops when the data says so, and drops that nobody shares get killed.</p></section>
<div class="drops">{''.join(cards)}</div>
<section class="card"><h2>Suggest one</h2><p>Have a small, useful, slightly absurd idea? <a href="https://github.com/Furiadelimon/worth-one/issues">Open an issue</a>. Good ideas get built and credited.</p></section>"""
    write("drops/index.html", layout("drops/", "All drops · Worth One?", "Every free drop: doomscroll receipt, subscription lifetime receipt, and what is coming next.", body, 1))


# ---------------- screen-time programmatic pages ----------------
SCREEN = [(0.5, "30-minutes", "30 minutes"), (1, "1-hour", "1 hour"), (1.5, "90-minutes", "1.5 hours"), (2, "2-hours", "2 hours"), (2.5, "2-5-hours", "2.5 hours"),
          (3, "3-hours", "3 hours"), (4, "4-hours", "4 hours"), (5, "5-hours", "5 hours"), (6, "6-hours", "6 hours"), (8, "8-hours", "8 hours")]
AVG = 2.33


def screen_page(hours, slug, label):
    year_h = hours * 365.25; year_d = year_h / 24
    d10 = year_d * 10; d20 = year_d * 20; h10 = year_h * 10
    dif = round((hours - AVG) / AVG * 100)
    rec30 = 0.5 * 365.25 / 24
    tier = next(t for lim, t in [(1, "Light thumb"), (2, "Casual scroller"), (3, "Regular"), (4, "Committed"), (6, "Heavy rotation"), (99, "Professional thumb athlete")] if hours < lim)
    others = " · ".join(f'<a href="../{s}/">{l}</a>' for h, s, l in SCREEN if s != slug)
    title = f"{label} of screen time a day: what it adds up to in a year, a decade, a life"
    desc = f"{label} a day on your phone is {fmt_days(year_d)} a year and {fmt_days(d10)} over ten years. The full receipt, what that time could be, and what cutting 30 minutes gives back."
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": title, "datePublished": TODAY, "dateModified": TODAY, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "mainEntityOfPage": f"{SITE}/screen-time/{slug}/"}
    body = f"""<section class="hero"><span class="eyebrow">Screen time, by the hour</span><h1>{label} a day is <em>{fmt_days(year_d)} a year.</em></h1>
<p class="lead">If you scroll for about {label} every day, that is {fmt_days(d10)} over the next ten years, and {fmt_days(d20)} over twenty. Here is the receipt, line by line, and what the same time could be.</p>
<div class="row"><a class="btn acc" href="../../drops/doomscroll-receipt/?v={hours}" data-nav="DROP-001">Make it your own receipt →</a></div></section>
<div class="receipt"><h3>LIFE RECEIPT · {esc(label).upper()}/DAY</h3><div class="c">worth-one · fixed-price edition</div><hr>
<div class="ln"><span>Scrolling / day</span><b>{fmt_h(hours)}</b></div><div class="ln"><span>Per week</span><b>{fmt_h(hours*7)}</b></div><div class="ln"><span>Per year</span><b>{fmt_days(year_d)}</b></div><hr>
<div class="ln"><span>Next 5 years</span><b>{fmt_days(year_d*5)}</b></div><div class="ln"><span>Next 10 years</span><b>{fmt_days(d10)}</b></div><div class="ln"><span>Next 20 years</span><b>{fmt_days(d20)}</b></div><hr>
<div class="ln"><span>Your tier</span><b>{tier}</b></div><div class="ln"><span>vs world average</span><b>{'+' if dif>=0 else ''}{dif}%</b></div><hr>
<div class="ln tot"><span>TOTAL, 10 YEARS</span><b>{fmt_days(d10)}</b></div><div class="barcode"></div></div>
<section class="card prose">
<h2>What {label} a day means in practice</h2>
<p>{label.capitalize()} of scrolling a day is {round(year_h):,} hours a year. Expressed in full 24-hour days it is {fmt_days(year_d)}, which is easier to feel: it is the length of a long holiday, spent in roughly {int(hours*60)}-minute pieces you will not remember individually.</p>
<p>Over ten years the same habit is {round(h10):,} hours. That is enough time to read about {round(h10/6):,} books at six hours each, {"to learn " + str(int(h10/500)) + (" language" if int(h10/500)==1 else " languages") + " to a conversational level (roughly 500 hours each), " if h10 >= 500 else ""}or to watch every episode of Friends {round(h10/87,1):g} times.</p>
<h2>Compared with everyone else</h2>
<p>The world average for social media is about 2 hours 20 minutes a day (DataReportal, Digital 2025). {label.capitalize()} a day is {abs(dif)}% {'above' if dif>=0 else 'below'} that average, which puts you in the "{tier}" tier on the receipt. The tier names are a joke; the numbers are not.</p>
<h2>The refund department</h2>
<p>Cutting just 30 minutes a day from {label} gives back {fmt_days(rec30)} a year and {fmt_days(rec30*10)} over ten years, without changing anything else. Cutting it to one hour a day would return {fmt_days(max(0,(hours-1))*365.25/24)} a year. None of this is advice; it is arithmetic you can act on or ignore.</p>
<h2>How to check your real number</h2>
<p>iPhone: Settings → Screen Time → See All App &amp; Website Activity, weekly view, add up social and entertainment apps and divide by seven. Android: Settings → Digital Wellbeing → Dashboard. Then <a href="../../drops/doomscroll-receipt/">print your own receipt</a> and send it to the friend who claims they "barely use their phone".</p>
<p class="small muted">Other amounts: {others}.</p>
</section>
<section class="card support"></section>
<section class="card"><h2>Related</h2><div class="next"><a class="drop" href="../../drops/doomscroll-receipt/" data-nav="DROP-001"><span class="num">#001</span><b>Doomscroll Receipt</b><p>Your own number, your own receipt, shareable.</p></a><a class="drop" href="../../drops/subscription-receipt/" data-nav="DROP-002"><span class="num">#002</span><b>Subscription Lifetime Receipt</b><p>The same trick, applied to money.</p></a></div></section>"""
    write(f"screen-time/{slug}/index.html", layout(f"screen-time/{slug}/", title, desc, body, 2, og_image=f"{SITE}/assets/og-doomscroll.png", ld=ld, drop="DROP-001"))


def build_screen():
    for h, s, l in SCREEN:
        screen_page(h, s, l)
    rows = "".join(f'<tr><td><a href="{s}/">{l}</a></td><td>{fmt_days(h*365.25/24)}</td><td>{fmt_days(h*365.25/24*10)}</td><td>{fmt_days(h*365.25/24*20)}</td></tr>' for h, s, l in SCREEN)
    body = f"""<section class="hero"><span class="eyebrow">Reference</span><h1>Screen time, <em>by the hour</em></h1><p class="lead">How much a daily scrolling habit adds up to over a year, a decade and two decades. Pick your number, or <a href="../drops/doomscroll-receipt/">print your own receipt</a>.</p></section>
<section class="card prose"><table><tr><th>Per day</th><th>Per year</th><th>10 years</th><th>20 years</th></tr>{rows}</table>
<p class="small muted">Method: daily time × 365.25, expressed in full 24-hour days. World average on social media is about 2h20/day (DataReportal, Digital 2025). Arithmetic, not health advice.</p></section>"""
    write("screen-time/index.html", layout("screen-time/", "Screen time by the hour: 1, 2, 3… hours a day over a year and a decade", "A table of what 30 minutes to 8 hours of daily scrolling adds up to per year, per decade and over twenty years, with a page for each.", body, 1, og_image=f"{SITE}/assets/og-doomscroll.png", drop="DROP-001"))


# ---------------- subscriptions programmatic pages ----------------
SUBS = [("netflix", "Netflix", 13.99, "streaming"), ("spotify", "Spotify", 10.99, "music"), ("youtube-premium", "YouTube Premium", 12.99, "streaming"), ("disney-plus", "Disney+", 9.99, "streaming"),
        ("amazon-prime", "Amazon Prime", 4.99, "delivery and streaming"), ("apple-music", "Apple Music", 10.99, "music"), ("icloud", "iCloud+ / Google One (200 GB)", 2.99, "cloud storage"),
        ("chatgpt", "ChatGPT Plus / an AI assistant", 20, "AI"), ("gym", "a gym membership", 35, "fitness"), ("playstation-plus", "PlayStation Plus / Xbox Game Pass", 9.99, "gaming"), ("dating-app", "a dating app", 20, "dating")]


def sub_page(slug, name, price, kind):
    y = price * 12; y5 = y * 5; y10 = y * 10; y20 = y * 20
    others = " · ".join(f'<a href="../{s}/">{n}</a>' for s, n, p, k in SUBS if s != slug)
    title = f"How much does {name} cost over 10 years? {round(y10):,} EUR, and what that buys"
    desc = f"{name} at about {price:.2f} a month is {round(y):,} a year, {round(y10):,} over ten years and {round(y20):,} over twenty. The receipt, the comparisons, and the cancel maths."
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": title, "datePublished": TODAY, "dateModified": TODAY, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "mainEntityOfPage": f"{SITE}/subscriptions/{slug}/"}
    body = f"""<section class="hero"><span class="eyebrow">Subscriptions, one by one</span><h1>{esc(name)} costs <em>{round(y10):,} over ten years.</em></h1>
<p class="lead">At roughly {price:.2f} a month, {esc(name)} is {round(y):,} a year, {round(y10):,} over a decade and {round(y20):,} over twenty years, at today's price and before increases. Here is the receipt and what the same money is in real things.</p>
<div class="row"><a class="btn acc" href="../../drops/subscription-receipt/" data-nav="DROP-002">Build your full receipt →</a></div></section>
<div class="receipt"><h3>SUBSCRIPTION RECEIPT</h3><div class="c">worth-one · single item</div><hr>
<div class="ln"><span>{esc(name)}</span><b>{price:.2f}/mo</b></div><hr>
<div class="ln"><span>Per year</span><b>{round(y):,}</b></div><div class="ln"><span>5 years</span><b>{round(y5):,}</b></div><div class="ln"><span>10 years</span><b>{round(y10):,}</b></div><div class="ln"><span>20 years</span><b>{round(y20):,}</b></div><hr>
<div class="ln"><span>10 years buys ≈</span></div><div style="font-size:13px;color:#333">• {round(y10/30000*100):g}% of a 30,000 car<br>• {round(y10/3):,} coffees at 3<br>• {round(y10/80):,} weeks of groceries at 80<br>• {round(y10/1200,1):g} return flights at 1,200</div><hr>
<div class="ln tot"><span>TOTAL, 10 YEARS</span><b>{round(y10):,}</b></div><div class="barcode"></div></div>
<section class="card prose">
<h2>Is {esc(name)} worth {round(y10):,}?</h2>
<p>Maybe. That is not the point of the page. The point is that {kind} subscriptions are priced to feel small per month, and {price:.2f} feels small. {round(y10):,} over a decade does not. Both numbers are the same purchase; only the framing changes. If you use {esc(name)} every week, the decade price may be one of the best deals you have. If you opened it twice last month, you now know what "I'll cancel it eventually" costs per year: {round(y):,}.</p>
<h2>What the 10-year figure assumes</h2>
<p>Today's price, no increases, no annual-plan discount, no shared family plan, no free months. Real ten-year cost is usually higher because prices rise; this is the floor. Currency is left generic on purpose: the figures are close enough in EUR, USD and GBP to use as they are, and you can edit any price in the <a href="../../drops/subscription-receipt/">full calculator</a>.</p>
<h2>The cancel maths</h2>
<p>Cancelling {esc(name)} for six months a year (most people binge in bursts) saves about {round(y/2):,} a year and {round(y10/2):,} over ten years. Downgrading to a cheaper tier, sharing legitimately with a household, or rotating between services are all cheaper than the default of paying every month forever.</p>
<p class="small muted">Other services: {others}.</p>
</section>
<section class="card support"></section>
<section class="card"><h2>Related</h2><div class="next"><a class="drop" href="../../drops/subscription-receipt/" data-nav="DROP-002"><span class="num">#002</span><b>Subscription Lifetime Receipt</b><p>All your subscriptions, one receipt, shareable.</p></a><a class="drop" href="../../drops/doomscroll-receipt/" data-nav="DROP-001"><span class="num">#001</span><b>Doomscroll Receipt</b><p>The same trick, applied to time.</p></a></div></section>"""
    write(f"subscriptions/{slug}/index.html", layout(f"subscriptions/{slug}/", title, desc, body, 2, ld=ld, drop="DROP-002"))


def build_subs():
    for s, n, p, k in SUBS:
        sub_page(s, n, p, k)
    rows = "".join(f'<tr><td><a href="{s}/">{esc(n)}</a></td><td>{p:.2f}</td><td>{round(p*12):,}</td><td>{round(p*120):,}</td><td>{round(p*240):,}</td></tr>' for s, n, p, k in SUBS)
    total = sum(p for s, n, p, k in SUBS)
    body = f"""<section class="hero"><span class="eyebrow">Reference</span><h1>Subscriptions, <em>one by one</em></h1><p class="lead">What each common subscription costs per year, per decade and over twenty years at today's list price. All of them together: {round(total*120):,} over ten years. Pick yours in the <a href="../drops/subscription-receipt/">calculator</a>.</p></section>
<section class="card prose"><table><tr><th>Service</th><th>Per month</th><th>Per year</th><th>10 years</th><th>20 years</th></tr>{rows}</table>
<p class="small muted">Typical 2026 list prices, no increases, no discounts. Figures are close enough in EUR, USD and GBP to read as-is.</p></section>"""
    write("subscriptions/index.html", layout("subscriptions/", "Subscription costs over 10 years: Netflix, Spotify, gym, cloud and more", "A table of what common subscriptions cost per year, per decade and over twenty years, with one page per service.", body, 1, drop="DROP-002"))


# ---------------- notes (content hub) ----------------
def md(text):
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        b = block.strip()
        if b.startswith("## "):
            out.append(f"<h2>{esc(b[3:])}</h2>")
        elif b.startswith("### "):
            out.append(f"<h3>{esc(b[4:])}</h3>")
        elif all(l.startswith("- ") for l in b.splitlines()):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in b.splitlines()) + "</ul>")
        else:
            out.append(f"<p>{inline(b)}</p>")
    return "\n".join(out)


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    return s


def build_notes():
    ndir = os.path.join(ROOT, "site", "notes")
    posts = []
    for fn in sorted(os.listdir(ndir)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(ndir, fn), encoding="utf-8").read()
        meta, _, body = raw.partition("\n---\n")
        m = dict(l.split(":", 1) for l in meta.strip().splitlines())
        m = {k.strip(): v.strip() for k, v in m.items()}
        slug = fn[:-3]
        posts.append((m.get("date", TODAY), slug, m["title"], m["summary"], body))
    posts.sort(reverse=True)
    for date, slug, title, summary, body in posts:
        ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": title, "datePublished": date, "dateModified": date, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "description": summary}
        html_body = f"""<section class="hero"><span class="eyebrow">Lab notes · {date}</span><h1>{esc(title)}</h1><p class="lead">{esc(summary)}</p></section><section class="card prose">{md(body)}</section>
<section class="card"><h2>Try a drop</h2><div class="next"><a class="drop" href="../drops/doomscroll-receipt/" data-nav="DROP-001"><span class="num">#001</span><b>Doomscroll Receipt</b><p>Your scrolling, itemised.</p></a><a class="drop" href="../drops/subscription-receipt/" data-nav="DROP-002"><span class="num">#002</span><b>Subscription Lifetime Receipt</b><p>Your subscriptions, over a decade.</p></a></div></section>"""
        write(f"notes/{slug}.html", layout(f"notes/{slug}.html", f"{title} · Worth One? lab notes", summary, html_body, 1, ld=ld))
    items = "".join(f'<a class="drop" href="{slug}.html"><span class="num">{date}</span><b>{esc(title)}</b><p>{esc(summary)}</p></a>' for date, slug, title, summary, body in posts)
    body = f"""<section class="hero"><span class="eyebrow">Content hub</span><h1>Lab <em>notes</em></h1><p class="lead">How the tools are calculated, what the numbers say in aggregate, and milestones. Published only when there is something worth reading.</p></section><div class="drops">{items}</div>"""
    write("notes/index.html", layout("notes/", "Lab notes · Worth One?", "Method, findings and milestones of the Worth One experiment. Published only when there is something to say.", body, 1))


# ---------------- embeds ----------------
def build_embed():
    embed_js = """/* Worth One? embed loader. Usage: <div data-worthone="doomscroll"></div><script src="%s/embed.js" async></script> */
(function(){var S="%s";document.querySelectorAll("[data-worthone]").forEach(function(el){if(el.dataset.done)return;el.dataset.done=1;var which=el.dataset.worthone||"doomscroll";var f=document.createElement("iframe");f.src=S+"/embed/"+(which==="subscriptions"?"subscriptions":"doomscroll")+".html?src=embed&c="+encodeURIComponent(location.hostname);f.style.cssText="width:100%%;max-width:560px;height:"+(which==="subscriptions"?"820":"640")+"px;border:0;border-radius:16px;display:block;margin:0 auto";f.loading="lazy";f.title="Worth One? "+which+" widget";el.appendChild(f)})})();
""" % (SITE, SITE)
    write("embed.js", embed_js)
    for which, src, height in (("doomscroll", "drops/doomscroll-receipt/", 640), ("subscriptions", "drops/subscription-receipt/", 820)):
        page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Worth One? widget</title><meta name="robots" content="noindex"><link rel="stylesheet" href="../style.css"><script src="../config.js"></script><script defer src="../app.js"></script><style>body{{padding:10px}}.wrap{{max-width:560px}}.receipt{{transform:none;box-shadow:0 2px 12px rgba(0,0,0,.1)}}.pow{{text-align:center;font-size:12px;margin:8px 0 0}}.pow a{{color:var(--mut)}}</style></head>
<body data-drop="{'DROP-001' if which=='doomscroll' else 'DROP-002'}" data-embed="1"><div class="wrap"><iframe src="../{src}?src=embed" style="width:100%;height:{height-40}px;border:0" title="Worth One? {which}"></iframe><p class="pow">Powered by <a href="{SITE}/?src=embed" target="_blank" rel="noopener">Worth One?</a> · free tools for strangers</p></div></body></html>"""
        write(f"embed/{which}.html", page)
    snippet_d = esc(f'<div data-worthone="doomscroll"></div>\n<script src="{SITE}/embed.js" async></script>')
    snippet_s = esc(f'<div data-worthone="subscriptions"></div>\n<script src="{SITE}/embed.js" async></script>')
    iframe_d = esc(f'<iframe src="{SITE}/embed/doomscroll.html" style="width:100%;max-width:560px;height:640px;border:0;border-radius:16px" loading="lazy" title="Doomscroll Receipt"></iframe>')
    body = f"""<section class="hero"><span class="eyebrow">Free widgets</span><h1>Put a drop <em>on your site.</em></h1><p class="lead">Any drop can live on your blog, resource page or newsletter site for free. One line of HTML, no account, no tracking of your readers beyond an anonymous count of widget views. Each widget carries a small "Powered by Worth One?" line.</p></section>
<section class="card prose"><h2>Doomscroll Receipt widget</h2><p>Script (recommended, responsive):</p><pre style="white-space:pre-wrap;background:var(--bg2);padding:12px;border-radius:12px;font-size:13px">{snippet_d}</pre><p>Plain iframe (WordPress, Ghost, Substack-style editors that allow iframes):</p><pre style="white-space:pre-wrap;background:var(--bg2);padding:12px;border-radius:12px;font-size:13px">{iframe_d}</pre>
<div data-worthone="doomscroll"></div></section>
<section class="card prose"><h2>Subscription Lifetime Receipt widget</h2><pre style="white-space:pre-wrap;background:var(--bg2);padding:12px;border-radius:12px;font-size:13px">{snippet_s}</pre></section>
<section class="card prose"><h2>Terms for embedding</h2><p>Free for any site, commercial or not. Keep the "Powered by Worth One?" line. Do not present the widget as your own tool. Widget views are counted anonymously (hostname and count only) so the experiment can see where it is useful. That is all.</p><p class="small muted">Want a different size, a language, or a widget for another drop? <a href="https://github.com/Furiadelimon/worth-one/issues">Open an issue</a>.</p></section>
<script src="../embed.js" async></script>"""
    write("embed/index.html", layout("embed/", "Embed a free calculator widget · Worth One?", "Put the Doomscroll Receipt or Subscription Lifetime Receipt on your own site with one line of HTML. Free, no account.", body, 1))


def build_sitemap():
    fixed = ["", "about.html", "drops/doomscroll-receipt/", "drops/subscription-receipt/"]
    all_urls = [f"{SITE}/{u}" for u in fixed] + [u for u in urls if u not in [f"{SITE}/{x}" for x in fixed]]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in all_urls) + "</urlset>\n"
    write("sitemap.xml", xml)
    json.dump(all_urls, open(os.path.join(ROOT, "site", "urls.json"), "w"), indent=1)
    print(f"{len(all_urls)} urls")


if __name__ == "__main__":
    build_drops(); build_screen(); build_subs(); build_notes(); build_embed(); build_sitemap()
    print("built")
