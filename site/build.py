#!/usr/bin/env python3
"""Static generator for the programmatic / content parts of the Worth One site, in English and Spanish.

Generates (into docs/ and docs/es/):
  drops/index.html                       catalogue from engine/drops.json (+ Words Before Coffee, a friend site)
  screen-time/index.html + /<slug>/      one substantial page per daily scrolling amount
  subscriptions/index.html + /<slug>/    one page per subscription service
  notes/index.html + /<slug>.html        lab notes (English only for now), from site/notes/*.md
  embed/index.html, embed/doomscroll.html, embed/subscriptions.html, embed.js
  sitemap.xml (both languages, hreflang alternates)

Every generated page has real content, not filler. Run: python site/build.py && python site/i18n_es.py
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
WBC = "https://wordsbeforecoffee.com/?src=worthone"
urls = {"en": [], "es": []}

S = {
    "en": dict(drops="Drops", notes="Lab notes", embed="Embed", about="About", home="Home", privacy="Privacy", source="Source", other="English", other_lang="es", other_label="Español",
               foot="An independent project by one person. Free things for strangers. One car.",
               try_drop="Try a drop", related="Related", more="More", live="live", next="next", idea="idea",
               wbc_num="FRIEND", wbc_tag="games", wbc_p="Three words to wake up. Daily word games, no registration, no ads. From the same kitchen (in Spanish).",
               d1="Doomscroll Receipt", d1p="Your scrolling, itemised.", d2="Subscription Lifetime Receipt", d2p="Your subscriptions, over a decade."),
    "es": dict(drops="Drops", notes="Notas", embed="Insertar", about="Acerca de", home="Inicio", privacy="Privacidad", source="Código", other="English", other_lang="en", other_label="English",
               foot="Un proyecto independiente de una sola persona. Cosas gratis para desconocidos. Un coche.",
               try_drop="Prueba un drop", related="Relacionado", more="Más", live="activo", next="próximo", idea="idea",
               wbc_num="AMIGO", wbc_tag="juegos", wbc_p="Tres palabras para despertar. Juegos de palabras diarios, sin registro, sin anuncios. De la misma cocina.",
               d1="Ticket de Doomscroll", d1p="Tu scroll, detallado.", d2="Ticket de Suscripciones", d2p="Tus suscripciones, en una década."),
}


def esc(s):
    return html.escape(str(s), quote=True)


def layout(lang, path, title, desc, body, depth, og_image=None, ld=None, drop="", noindex=False, alt=True):
    """path is relative to the language root (e.g. 'screen-time/2-hours/'). depth = folders under the language root."""
    t = S[lang]
    pre = "" if lang == "en" else "es/"
    rel = "../" * depth            # to language root
    root = rel + ("../" if lang == "es" else "")  # to site root (assets)
    canonical = f"{SITE}/{pre}{path}"
    en_url, es_url = f"{SITE}/{path}", f"{SITE}/es/{path}"
    if not noindex:
        urls[lang].append(canonical)
    og = og_image or f"{SITE}/assets/og.png"
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    hreflang = f'<link rel="alternate" hreflang="en" href="{en_url}"><link rel="alternate" hreflang="es" href="{es_url}"><link rel="alternate" hreflang="x-default" href="{en_url}">' if alt else ""
    other_href = (rel + "../" + path) if lang == "es" else (rel + "es/" + path)
    notes_link = f'<a href="{rel}notes/">{t["notes"]}</a>' if lang == "en" else ""
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">{hreflang}{robots}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{ICON}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{root}style.css"><script src="{root}config.js"></script><script defer src="{root}app.js"></script>
{ldj}
</head>
<body data-lang="{lang}" data-drop="{drop}">
<div class="wrap">
<nav class="nav"><a class="brand" href="{rel}"><i>€1</i>WORTH ONE?</a><span class="links"><a href="{rel}drops/">{t["drops"]}</a>{notes_link}<a href="{rel}embed/">{t["embed"]}</a><a href="{rel}about.html">{t["about"]}</a>{'<a href="' + other_href + '" hreflang="' + t["other_lang"] + '">' + t["other_label"] + '</a>' if alt else ''}</span></nav>
{body}
<footer><a class="brand" href="{rel}">WORTH ONE?</a><br><a href="{rel}">{t["home"]}</a><a href="{rel}drops/">{t["drops"]}</a>{notes_link}<a href="{rel}embed/">{t["embed"]}</a><a href="{rel}about.html">{t["about"]}</a><a href="{rel}privacy.html">{t["privacy"]}</a><a href="https://github.com/Furiadelimon/worth-one">{t["source"]}</a><br><span class="tiny">{t["foot"]}</span></footer>
</div>
</body>
</html>
"""


def write(lang, path, content):
    full = os.path.join(DOCS, "" if lang == "en" else "es", path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def fmt_days(d, lang="en"):
    h, dd, y = ("hours", "days", "years") if lang == "en" else ("horas", "días", "años")
    if d < 1:
        return f"{round(d * 24)} {h}"
    if d < 60:
        return f"{round(d, 1):g} {dd}"
    if d < 365:
        return f"{round(d)} {dd}"
    return f"{round(d / 365.25, 2):g} {y}"


def fmt_h(x):
    H = int(x); M = round((x - H) * 60)
    return (f"{H}h {M}m" if M else f"{H}h") if H else f"{M}m"


def related(lang, rel):
    t = S[lang]
    return f"""<section class="card"><h2>{t["related"]}</h2><div class="next"><a class="drop" href="{rel}drops/doomscroll-receipt/" data-nav="DROP-001"><span class="num">#001</span><b>{t["d1"]}</b><p>{t["d1p"]}</p></a><a class="drop" href="{rel}drops/subscription-receipt/" data-nav="DROP-002"><span class="num">#002</span><b>{t["d2"]}</b><p>{t["d2p"]}</p></a><a class="drop" href="{WBC}" data-nav="WBC" rel="noopener"><span class="num">{t["wbc_num"]}</span><b>Words Before Coffee</b><p>{t["wbc_p"]}</p></a></div></section>"""


# ---------------- drops catalogue ----------------
DROP_ES = {
    "DROP-001": ("Ticket de Doomscroll", "Di cuánto haces scroll al día. Recibe un ticket: al año, por década, días de tu vida y lo que recuperas quitando 30 minutos. Hecho para hacer captura."),
    "DROP-002": ("Ticket de Suscripciones", "Marca tus suscripciones (streaming, música, nube, gimnasio, apps). Mira el coste real a 1/5/10 años y qué es ese dinero en cosas concretas."),
    "DROP-003": ("Fines de semana que te quedan", "Di tu edad. Mira los fines de semana que estadísticamente te quedan, en una cuadrícula para hacer captura."),
    "DROP-004": ("La tarjeta de cumpleaños de tu móvil", "¿Cuántas veces has desbloqueado el móvil desde que lo tienes? Una tarjeta con comparaciones absurdas."),
    "DROP-005": ("Café vs coche", "Un gasto diario pequeño, compuesto a 1/5/10/30 años, y qué compra."),
    "DROP-006": ("Deuda de notificaciones", "Notificaciones al día por años con móvil: interrupciones totales presentadas como una factura que nunca aceptaste."),
}


def build_drops(lang):
    t = S[lang]
    drops = json.load(open(os.path.join(ROOT, "engine", "drops.json"), encoding="utf-8"))
    order = {"LIVE": 0, "GROWING": 0, "VIRAL": 0, "TESTING": 1, "BUILDING": 2, "IDEA": 3, "PAUSED": 4, "KILLED": 5}
    drops.sort(key=lambda d: (order.get(d["status"], 9), d["drop_id"]))
    cards = []
    for d in drops:
        if d["status"] == "KILLED":
            continue
        name, concept = (d["name"], d["concept"]) if lang == "en" else DROP_ES.get(d["drop_id"], (d["name"], d["concept"]))
        live = d["status"] in ("LIVE", "GROWING", "VIRAL")
        num = d["drop_id"].replace("DROP-", "#")
        if live:
            cards.append(f'<a class="drop" href="{d["slug"]}/" data-nav="{d["drop_id"]}"><span class="num">{num}</span><span class="tag live">{t["live"]}</span><b>{esc(name)}</b><p>{esc(concept[:140])}</p></a>')
        else:
            soon = d["status"] in ("BUILDING", "TESTING") or d["drop_id"] == "DROP-003"
            cards.append(f'<div class="drop soon"><span class="num">{num}</span><span class="tag {"soon" if soon else ""}">{t["next"] if soon else t["idea"]}</span><b>{esc(name)}</b><p>{esc(concept[:140])}</p></div>')
    cards.append(f'<a class="drop" href="{WBC}" data-nav="WBC" rel="noopener"><span class="num">{t["wbc_num"]}</span><span class="tag">{t["wbc_tag"]}</span><b>Words Before Coffee</b><p>{t["wbc_p"]}</p></a>')
    if lang == "en":
        body = f"""<section class="hero"><span class="eyebrow">Catalogue</span><h1>All <em>drops</em></h1><p class="lead">Small web experiences you can use right now, free, no account. New ones appear when they are ready; the ones nobody shares are removed.</p></section>
<div class="drops">{''.join(cards)}</div>
<section class="card"><h2>Suggest one</h2><p>Have a small, useful, slightly absurd idea? <a href="https://github.com/Furiadelimon/worth-one/issues">Open an issue</a>. Good ideas get built and credited.</p></section>"""
        write(lang, "drops/index.html", layout(lang, "drops/", "All drops · Worth One?", "Every free drop: doomscroll receipt, subscription lifetime receipt, and what is coming next.", body, 1))
    else:
        body = f"""<section class="hero"><span class="eyebrow">Catálogo</span><h1>Todos los <em>drops</em></h1><p class="lead">Pequeñas experiencias web para usar ahora mismo, gratis, sin cuenta. Los nuevos aparecen cuando están listos; los que nadie comparte se eliminan.</p></section>
<div class="drops">{''.join(cards)}</div>
<section class="card"><h2>Propón uno</h2><p>¿Tienes una idea pequeña, útil y un poco absurda? <a href="https://github.com/Furiadelimon/worth-one/issues">Abre un issue</a>. Las buenas ideas se construyen y se acreditan.</p></section>"""
        write(lang, "drops/index.html", layout(lang, "drops/", "Todos los drops · Worth One?", "Todos los drops gratis: ticket de doomscroll, ticket de suscripciones y lo que viene.", body, 1))


# ---------------- screen-time programmatic pages ----------------
SCREEN = [(0.5, "30-minutes", "30 minutes", "30 minutos"), (1, "1-hour", "1 hour", "1 hora"), (1.5, "90-minutes", "1.5 hours", "1,5 horas"), (2, "2-hours", "2 hours", "2 horas"), (2.5, "2-5-hours", "2.5 hours", "2,5 horas"),
          (3, "3-hours", "3 hours", "3 horas"), (4, "4-hours", "4 hours", "4 horas"), (5, "5-hours", "5 hours", "5 horas"), (6, "6-hours", "6 hours", "6 horas"), (8, "8-hours", "8 hours", "8 horas")]
AVG = 2.33
TIERS = {"en": [(1, "Light thumb"), (2, "Casual scroller"), (3, "Regular"), (4, "Committed"), (6, "Heavy rotation"), (99, "Professional thumb athlete")],
         "es": [(1, "Pulgar ligero"), (2, "Scroll casual"), (3, "Habitual"), (4, "Comprometido"), (6, "Alta rotación"), (99, "Atleta profesional del pulgar")]}


def screen_page(lang, hours, slug, label):
    L = lang
    year_h = hours * 365.25; year_d = year_h / 24
    d10 = year_d * 10; d20 = year_d * 20; h10 = year_h * 10
    dif = round((hours - AVG) / AVG * 100)
    rec30 = 0.5 * 365.25 / 24
    tier = next(t for lim, t in TIERS[L] if hours < lim)
    others = " · ".join(f'<a href="../{s}/">{(l if L == "en" else le)}</a>' for h, s, l, le in SCREEN if s != slug)
    fd = lambda d: fmt_days(d, L)
    art = lambda title, path: {"@context": "https://schema.org", "@type": "Article", "headline": title, "datePublished": TODAY, "dateModified": TODAY, "inLanguage": L, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "mainEntityOfPage": path}
    receipt = lambda hdr, rows, tot: f'<div class="receipt"><h3>{hdr}</h3><div class="c">worth-one</div><hr>' + "".join(f'<div class="ln"><span>{a}</span><b>{b}</b></div>' if a != "hr" else "<hr>" for a, b in rows) + f'<hr><div class="ln tot"><span>{tot[0]}</span><b>{tot[1]}</b></div><div class="barcode"></div></div>'
    if L == "en":
        title = f"{label} of screen time a day: what it adds up to in a year, a decade, a life"
        desc = f"{label} a day on your phone is {fd(year_d)} a year and {fd(d10)} over ten years. The full receipt, what that time could be, and what cutting 30 minutes gives back."
        rows = [("Scrolling / day", fmt_h(hours)), ("Per week", fmt_h(hours * 7)), ("Per year", fd(year_d)), ("hr", ""), ("Next 5 years", fd(year_d * 5)), ("Next 10 years", fd(d10)), ("Next 20 years", fd(d20)), ("hr", ""), ("Your tier", tier), ("vs world average", f"{'+' if dif >= 0 else ''}{dif}%")]
        body = f"""<section class="hero"><span class="eyebrow">Screen time, by the hour</span><h1>{label} a day is <em>{fd(year_d)} a year.</em></h1>
<p class="lead">If you scroll for about {label} every day, that is {fd(d10)} over the next ten years, and {fd(d20)} over twenty. Here is the receipt, line by line, and what the same time could be.</p>
<div class="row"><a class="btn acc" href="../../drops/doomscroll-receipt/?v={hours}" data-nav="DROP-001">Make it your own receipt →</a></div></section>
{receipt(f"LIFE RECEIPT · {esc(label).upper()}/DAY", rows, ("TOTAL, 10 YEARS", fd(d10)))}
<section class="card prose">
<h2>What {label} a day means in practice</h2>
<p>{label.capitalize()} of scrolling a day is {round(year_h):,} hours a year. Expressed in full 24-hour days it is {fd(year_d)}, which is easier to feel: it is the length of a long holiday, spent in roughly {int(hours*60)}-minute pieces you will not remember individually.</p>
<p>Over ten years the same habit is {round(h10):,} hours. That is enough time to read about {round(h10/6):,} books at six hours each, {"to learn " + str(int(h10/500)) + (" language" if int(h10/500)==1 else " languages") + " to a conversational level (roughly 500 hours each), " if h10 >= 500 else ""}or to watch every episode of Friends {round(h10/87,1):g} times.</p>
<h2>Compared with everyone else</h2>
<p>The world average for social media is about 2 hours 20 minutes a day (DataReportal, Digital 2025). {label.capitalize()} a day is {abs(dif)}% {'above' if dif>=0 else 'below'} that average, which puts you in the "{tier}" tier on the receipt. The tier names are a joke; the numbers are not.</p>
<h2>The refund department</h2>
<p>Cutting just 30 minutes a day from {label} gives back {fd(rec30)} a year and {fd(rec30*10)} over ten years, without changing anything else. Cutting it to one hour a day would return {fd(max(0,(hours-1))*365.25/24)} a year. None of this is advice; it is arithmetic you can act on or ignore.</p>
<h2>How to check your real number</h2>
<p>iPhone: Settings → Screen Time → See All App &amp; Website Activity, weekly view, add up social and entertainment apps and divide by seven. Android: Settings → Digital Wellbeing → Dashboard. Then <a href="../../drops/doomscroll-receipt/">print your own receipt</a> and send it to the friend who claims they "barely use their phone".</p>
<p class="small muted">Other amounts: {others}.</p>
</section>
<section class="card support"></section>
{related(L, "../../")}"""
    else:
        title = f"{label} de pantalla al día: cuánto suma en un año, una década, una vida"
        desc = f"{label} al día en el móvil son {fd(year_d)} al año y {fd(d10)} en diez años. El ticket completo, qué podría ser ese tiempo y qué recuperas quitando 30 minutos."
        rows = [("Scroll / día", fmt_h(hours)), ("A la semana", fmt_h(hours * 7)), ("Al año", fd(year_d)), ("hr", ""), ("Próximos 5 años", fd(year_d * 5)), ("Próximos 10 años", fd(d10)), ("Próximos 20 años", fd(d20)), ("hr", ""), ("Tu nivel", tier), ("vs media mundial", f"{'+' if dif >= 0 else ''}{dif}%")]
        body = f"""<section class="hero"><span class="eyebrow">Tiempo de pantalla, hora a hora</span><h1>{label} al día son <em>{fd(year_d)} al año.</em></h1>
<p class="lead">Si haces scroll unas {label} cada día, eso son {fd(d10)} en los próximos diez años y {fd(d20)} en veinte. Aquí está el ticket, línea a línea, y qué podría ser ese mismo tiempo.</p>
<div class="row"><a class="btn acc" href="../../drops/doomscroll-receipt/?v={hours}" data-nav="DROP-001">Hazlo tu propio ticket →</a></div></section>
{receipt(f"TICKET DE VIDA · {esc(label).upper()}/DÍA", rows, ("TOTAL, 10 AÑOS", fd(d10)))}
<section class="card prose">
<h2>Qué significan {label} al día en la práctica</h2>
<p>{label.capitalize()} de scroll al día son {round(year_h):,} horas al año. En días completos de 24 horas son {fd(year_d)}, que es más fácil de sentir: es la duración de unas vacaciones largas, gastadas en trozos de unos {int(hours*60)} minutos que no recordarás uno a uno.</p>
<p>En diez años el mismo hábito son {round(h10):,} horas. Da para leer unos {round(h10/6):,} libros de seis horas, {"aprender " + str(int(h10/500)) + (" idioma" if int(h10/500)==1 else " idiomas") + " a nivel conversacional (unas 500 horas cada uno), " if h10 >= 500 else ""}o ver todos los episodios de Friends {round(h10/87,1):g} veces.</p>
<h2>Comparado con el resto</h2>
<p>La media mundial en redes sociales ronda las 2 horas y 20 minutos al día (DataReportal, Digital 2025). {label.capitalize()} al día están un {abs(dif)}% {'por encima' if dif>=0 else 'por debajo'} de esa media, lo que te sitúa en el nivel "{tier}" del ticket. Los nombres de los niveles son una broma; los números no.</p>
<h2>Departamento de devoluciones</h2>
<p>Quitar solo 30 minutos al día de {label} devuelve {fd(rec30)} al año y {fd(rec30*10)} en diez años, sin cambiar nada más. Bajar a una hora al día devolvería {fd(max(0,(hours-1))*365.25/24)} al año. Nada de esto es un consejo; es aritmética que puedes usar o ignorar.</p>
<h2>Cómo comprobar tu número real</h2>
<p>iPhone: Ajustes → Tiempo de uso → Ver toda la actividad, vista semanal, suma las apps sociales y de entretenimiento y divide entre siete. Android: Ajustes → Bienestar digital → Panel. Luego <a href="../../drops/doomscroll-receipt/">imprime tu propio ticket</a> y envíaselo al amigo que dice que "casi no usa el móvil".</p>
<p class="small muted">Otras cantidades: {others}.</p>
</section>
<section class="card support"></section>
{related(L, "../../")}"""
    write(L, f"screen-time/{slug}/index.html", layout(L, f"screen-time/{slug}/", title, desc, body, 2, og_image=f"{SITE}/assets/og-doomscroll.png", ld=art(title, f"{SITE}/{'' if L == 'en' else 'es/'}screen-time/{slug}/"), drop="DROP-001"))


AGE_ROWS = [("16-24", 3.0, "3h 00m"), ("25-34", 2.6, "2h 35m"), ("35-44", 2.2, "2h 10m"), ("45-54", 1.8, "1h 50m"), ("55-64", 1.4, "1h 25m")]


def build_age_page(lang):
    """Benchmark page: 'average screen time by age' (social media time per day, approximate, GWI via DataReportal)."""
    fd = lambda d: fmt_days(d, lang)
    if lang == "en":
        rows = "".join(f'<tr><td>{a}</td><td>{lbl}</td><td>{fd(h*365.25/24)}</td><td>{fd(h*365.25/24*10)}</td></tr>' for a, h, lbl in AGE_ROWS)
        title = "Average screen time by age: social media hours per day, and what they add up to"
        desc = "Approximate daily social media time by age group (16 to 64), per year and per decade, with the world average of about 2h20. Compare yourself with a free receipt."
        body = f"""<section class="hero"><span class="eyebrow">Benchmark</span><h1>Average screen time <em>by age</em></h1><p class="lead">How much time people spend on social media per day, by age group, and what each figure adds up to over a year and a decade. Approximate, from public surveys. Then print <a href="../../drops/doomscroll-receipt/">your own receipt</a> and see where you land.</p></section>
<section class="card prose"><table><tr><th>Age</th><th>Per day (approx.)</th><th>Per year</th><th>10 years</th></tr>{rows}<tr><td><b>World average</b></td><td>2h 20m</td><td>{fd(2.33*365.25/24)}</td><td>{fd(2.33*365.25/24*10)}</td></tr></table>
<h2>Where the numbers come from</h2><p>The world average (about 2 hours 20 minutes a day on social media, internet users aged 16 to 64) is from DataReportal's Digital 2025 report, built on GWI survey data. The age rows are rounded from the same family of surveys and vary by country and year by around 20 minutes either way; treat them as a ladder, not a ruler. Younger groups sit near or above three hours, and each decade of age removes roughly 20 to 30 minutes.</p>
<h2>Why the decade column matters</h2><p>A difference of 40 minutes a day between two age groups looks small. Over ten years it is {fd(40/60*365.25/24*10)}. That is the whole point of the receipt format: the same number, framed so it can be felt.</p>
<h2>Compare yourself</h2><p>Set your own daily figure in the <a href="../../drops/doomscroll-receipt/">Doomscroll Receipt</a>. It shows your distance from the world average and, once enough receipts exist, how you compare with everyone else who used it. Nothing you type is uploaded.</p>
<p class="small muted">Not health advice. Time on social media is not the same as total screen time, which is typically 2 to 3 times higher.</p></section>
<section class="card support"></section>
{related(lang, "../../")}"""
        write(lang, "screen-time/average-by-age/index.html", layout(lang, "screen-time/average-by-age/", title, desc, body, 2, og_image=f"{SITE}/assets/og-doomscroll.png", drop="DROP-001"))
    else:
        rows = "".join(f'<tr><td>{a}</td><td>{lbl}</td><td>{fd(h*365.25/24)}</td><td>{fd(h*365.25/24*10)}</td></tr>' for a, h, lbl in AGE_ROWS)
        title = "Tiempo de pantalla medio por edad: horas de redes sociales al día y cuánto suman"
        desc = "Tiempo diario aproximado en redes sociales por grupo de edad (16 a 64), al año y por década, con la media mundial de unas 2h20. Compárate con un ticket gratis."
        body = f"""<section class="hero"><span class="eyebrow">Referencia</span><h1>Tiempo de pantalla medio <em>por edad</em></h1><p class="lead">Cuánto tiempo pasa la gente en redes sociales al día según su edad, y cuánto suma cada cifra en un año y en una década. Aproximado, de encuestas públicas. Luego imprime <a href="../../drops/doomscroll-receipt/">tu propio ticket</a> y mira dónde caes.</p></section>
<section class="card prose"><table><tr><th>Edad</th><th>Al día (aprox.)</th><th>Al año</th><th>10 años</th></tr>{rows}<tr><td><b>Media mundial</b></td><td>2h 20m</td><td>{fd(2.33*365.25/24)}</td><td>{fd(2.33*365.25/24*10)}</td></tr></table>
<h2>De dónde salen los números</h2><p>La media mundial (unas 2 horas y 20 minutos al día en redes sociales, usuarios de internet de 16 a 64 años) es del informe Digital 2025 de DataReportal, basado en encuestas de GWI. Las filas por edad están redondeadas de esa misma familia de encuestas y varían según país y año unos 20 minutos arriba o abajo; tómalas como una escalera, no como una regla. Los grupos jóvenes rondan o superan las tres horas, y cada década de edad quita entre 20 y 30 minutos.</p>
<h2>Por qué importa la columna de la década</h2><p>Una diferencia de 40 minutos al día entre dos grupos de edad parece pequeña. En diez años son {fd(40/60*365.25/24*10)}. Ese es el sentido del formato ticket: el mismo número, enmarcado para que se sienta.</p>
<h2>Compárate</h2><p>Pon tu cifra diaria en el <a href="../../drops/doomscroll-receipt/">Ticket de Doomscroll</a>. Muestra tu distancia a la media mundial y, cuando haya suficientes tickets, cómo te comparas con el resto de personas que lo han usado. Nada de lo que escribes se envía.</p>
<p class="small muted">No es consejo de salud. El tiempo en redes sociales no es el tiempo total de pantalla, que suele ser 2 o 3 veces mayor.</p></section>
<section class="card support"></section>
{related(lang, "../../")}"""
        write(lang, "screen-time/average-by-age/index.html", layout(lang, "screen-time/average-by-age/", title, desc, body, 2, og_image=f"{SITE}/assets/og-doomscroll.png", drop="DROP-001"))


def build_screen(lang):
    build_age_page(lang)
    for h, s, l, le in SCREEN:
        screen_page(lang, h, s, l if lang == "en" else le)
    fd = lambda d: fmt_days(d, lang)
    rows = "".join(f'<tr><td><a href="{s}/">{(l if lang == "en" else le)}</a></td><td>{fd(h*365.25/24)}</td><td>{fd(h*365.25/24*10)}</td><td>{fd(h*365.25/24*20)}</td></tr>' for h, s, l, le in SCREEN)
    if lang == "en":
        body = f"""<section class="hero"><span class="eyebrow">Reference</span><h1>Screen time, <em>by the hour</em></h1><p class="lead">How much a daily scrolling habit adds up to over a year, a decade and two decades. Pick your number, or <a href="../drops/doomscroll-receipt/">print your own receipt</a>.</p></section>
<section class="card prose"><table><tr><th>Per day</th><th>Per year</th><th>10 years</th><th>20 years</th></tr>{rows}</table>
<p class="small muted">Method: daily time × 365.25, expressed in full 24-hour days. World average on social media is about 2h20/day (DataReportal, Digital 2025). Arithmetic, not health advice.</p></section>{related(lang, "../")}"""
        write(lang, "screen-time/index.html", layout(lang, "screen-time/", "Screen time by the hour: 1, 2, 3… hours a day over a year and a decade", "A table of what 30 minutes to 8 hours of daily scrolling adds up to per year, per decade and over twenty years, with a page for each.", body, 1, og_image=f"{SITE}/assets/og-doomscroll.png", drop="DROP-001"))
    else:
        body = f"""<section class="hero"><span class="eyebrow">Referencia</span><h1>Tiempo de pantalla, <em>hora a hora</em></h1><p class="lead">Cuánto suma un hábito diario de scroll en un año, una década y dos décadas. Elige tu número o <a href="../drops/doomscroll-receipt/">imprime tu propio ticket</a>.</p></section>
<section class="card prose"><table><tr><th>Al día</th><th>Al año</th><th>10 años</th><th>20 años</th></tr>{rows}</table>
<p class="small muted">Método: tiempo diario × 365,25, expresado en días completos de 24 horas. La media mundial en redes sociales ronda las 2h20/día (DataReportal, Digital 2025). Aritmética, no consejo de salud.</p></section>{related(lang, "../")}"""
        write(lang, "screen-time/index.html", layout(lang, "screen-time/", "Tiempo de pantalla hora a hora: 1, 2, 3… horas al día en un año y una década", "Tabla de lo que suman de 30 minutos a 8 horas de scroll diario al año, por década y en veinte años, con una página para cada cantidad.", body, 1, og_image=f"{SITE}/assets/og-doomscroll.png", drop="DROP-001"))


# ---------------- subscriptions programmatic pages ----------------
SUBS = [("netflix", "Netflix", 13.99, "streaming", "streaming"), ("spotify", "Spotify", 10.99, "music", "música"), ("youtube-premium", "YouTube Premium", 12.99, "streaming", "streaming"), ("disney-plus", "Disney+", 9.99, "streaming", "streaming"),
        ("amazon-prime", "Amazon Prime", 4.99, "delivery and streaming", "envíos y streaming"), ("apple-music", "Apple Music", 10.99, "music", "música"), ("icloud", "iCloud+ / Google One (200 GB)", 2.99, "cloud storage", "almacenamiento en la nube"),
        ("chatgpt", "ChatGPT Plus / an AI assistant", 20, "AI", "IA"), ("gym", "a gym membership", 35, "fitness", "gimnasio"), ("playstation-plus", "PlayStation Plus / Xbox Game Pass", 9.99, "gaming", "videojuegos"), ("dating-app", "a dating app", 20, "dating", "citas")]
SUB_NAME_ES = {"chatgpt": "ChatGPT Plus / un asistente de IA", "gym": "el gimnasio", "dating-app": "una app de citas"}


def sub_page(lang, slug, name, price, kind, kind_es):
    L = lang
    y = price * 12; y5 = y * 5; y10 = y * 10; y20 = y * 20
    n_es = SUB_NAME_ES.get(slug, name)
    others = " · ".join(f'<a href="../{s}/">{esc(n if L == "en" else SUB_NAME_ES.get(s, n))}</a>' for s, n, p, k, ke in SUBS if s != slug)
    art = lambda title, path: {"@context": "https://schema.org", "@type": "Article", "headline": title, "datePublished": TODAY, "dateModified": TODAY, "inLanguage": L, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "mainEntityOfPage": path}
    fm = (lambda v: f"{round(v):,}") if L == "en" else (lambda v: f"{round(v):,}".replace(",", "."))
    if L == "en":
        title = f"How much does {name} cost over 10 years? {fm(y10)} EUR, and what that buys"
        desc = f"{name} at about {price:.2f} a month is {fm(y)} a year, {fm(y10)} over ten years and {fm(y20)} over twenty. The receipt, the comparisons, and the cancel maths."
        body = f"""<section class="hero"><span class="eyebrow">Subscriptions, one by one</span><h1>{esc(name)} costs <em>{fm(y10)} over ten years.</em></h1>
<p class="lead">At roughly {price:.2f} a month, {esc(name)} is {fm(y)} a year, {fm(y10)} over a decade and {fm(y20)} over twenty years, at today's price and before increases. Here is the receipt and what the same money is in real things.</p>
<div class="row"><a class="btn acc" href="../../drops/subscription-receipt/" data-nav="DROP-002">Build your full receipt →</a></div></section>
<div class="receipt"><h3>SUBSCRIPTION RECEIPT</h3><div class="c">worth-one · single item</div><hr>
<div class="ln"><span>{esc(name)}</span><b>{price:.2f}/mo</b></div><hr>
<div class="ln"><span>Per year</span><b>{fm(y)}</b></div><div class="ln"><span>5 years</span><b>{fm(y5)}</b></div><div class="ln"><span>10 years</span><b>{fm(y10)}</b></div><div class="ln"><span>20 years</span><b>{fm(y20)}</b></div><hr>
<div class="ln"><span>10 years buys ≈</span></div><div style="font-size:13px;color:#333">• {round(y10/30000*100):g}% of a 30,000 car<br>• {fm(y10/3)} coffees at 3<br>• {fm(y10/80)} weeks of groceries at 80<br>• {round(y10/1200,1):g} return flights at 1,200</div><hr>
<div class="ln tot"><span>TOTAL, 10 YEARS</span><b>{fm(y10)}</b></div><div class="barcode"></div></div>
<section class="card prose">
<h2>Is {esc(name)} worth {fm(y10)}?</h2>
<p>Maybe. That is not the point of the page. The point is that {kind} subscriptions are priced to feel small per month, and {price:.2f} feels small. {fm(y10)} over a decade does not. Both numbers are the same purchase; only the framing changes. If you use {esc(name)} every week, the decade price may be one of the best deals you have. If you opened it twice last month, you now know what "I'll cancel it eventually" costs per year: {fm(y)}.</p>
<h2>What the 10-year figure assumes</h2>
<p>Today's price, no increases, no annual-plan discount, no shared family plan, no free months. Real ten-year cost is usually higher because prices rise; this is the floor. Currency is left generic on purpose: the figures are close enough in EUR, USD and GBP to use as they are, and you can edit any price in the <a href="../../drops/subscription-receipt/">full calculator</a>.</p>
<h2>The cancel maths</h2>
<p>Cancelling {esc(name)} for six months a year (most people binge in bursts) saves about {fm(y/2)} a year and {fm(y10/2)} over ten years. Downgrading to a cheaper tier, sharing legitimately with a household, or rotating between services are all cheaper than the default of paying every month forever.</p>
<p class="small muted">Other services: {others}.</p>
</section>
<section class="card support"></section>
{related(L, "../../")}"""
    else:
        title = f"¿Cuánto cuesta {n_es} en 10 años? {fm(y10)} €, y qué compra ese dinero"
        desc = f"{n_es.capitalize()} a unos {price:.2f} al mes son {fm(y)} al año, {fm(y10)} en diez años y {fm(y20)} en veinte. El ticket, las comparaciones y las cuentas de la baja."
        body = f"""<section class="hero"><span class="eyebrow">Suscripciones, una a una</span><h1>{esc(n_es.capitalize())} cuesta <em>{fm(y10)} en diez años.</em></h1>
<p class="lead">A unos {price:.2f} al mes, {esc(n_es)} son {fm(y)} al año, {fm(y10)} en una década y {fm(y20)} en veinte años, al precio de hoy y antes de subidas. Aquí está el ticket y qué es ese mismo dinero en cosas reales.</p>
<div class="row"><a class="btn acc" href="../../drops/subscription-receipt/" data-nav="DROP-002">Haz tu ticket completo →</a></div></section>
<div class="receipt"><h3>TICKET DE SUSCRIPCIONES</h3><div class="c">worth-one · un solo artículo</div><hr>
<div class="ln"><span>{esc(n_es)}</span><b>{price:.2f}/mes</b></div><hr>
<div class="ln"><span>Al año</span><b>{fm(y)}</b></div><div class="ln"><span>5 años</span><b>{fm(y5)}</b></div><div class="ln"><span>10 años</span><b>{fm(y10)}</b></div><div class="ln"><span>20 años</span><b>{fm(y20)}</b></div><hr>
<div class="ln"><span>10 años compran ≈</span></div><div style="font-size:13px;color:#333">• {round(y10/30000*100):g}% de un coche de 30.000<br>• {fm(y10/3)} cafés a 3<br>• {fm(y10/80)} semanas de compra a 80<br>• {round(y10/1200,1):g} vuelos ida y vuelta a 1.200</div><hr>
<div class="ln tot"><span>TOTAL, 10 AÑOS</span><b>{fm(y10)}</b></div><div class="barcode"></div></div>
<section class="card prose">
<h2>¿Vale {esc(n_es)} {fm(y10)}?</h2>
<p>Quizá. No es el objetivo de esta página. El objetivo es que las suscripciones de {kind_es} están pensadas para parecer pequeñas al mes, y {price:.2f} parece poco. {fm(y10)} en una década no. Los dos números son la misma compra; solo cambia el marco. Si usas {esc(n_es)} cada semana, el precio de la década puede ser de lo mejor que pagas. Si lo abriste dos veces el mes pasado, ya sabes lo que cuesta al año el "ya lo daré de baja": {fm(y)}.</p>
<h2>Qué asume la cifra de 10 años</h2>
<p>Precio de hoy, sin subidas, sin descuento anual, sin plan familiar compartido, sin meses gratis. El coste real a diez años suele ser mayor porque los precios suben; esto es el suelo. La moneda se deja genérica a propósito: las cifras son lo bastante parecidas en EUR, USD y GBP para usarlas tal cual, y puedes editar cualquier precio en la <a href="../../drops/subscription-receipt/">calculadora completa</a>.</p>
<h2>Las cuentas de la baja</h2>
<p>Dar de baja {esc(n_es)} seis meses al año (la mayoría consume a rachas) ahorra unos {fm(y/2)} al año y {fm(y10/2)} en diez años. Bajar a un plan más barato, compartir legítimamente en casa o rotar entre servicios sale más barato que pagar todos los meses para siempre.</p>
<p class="small muted">Otros servicios: {others}.</p>
</section>
<section class="card support"></section>
{related(L, "../../")}"""
    write(L, f"subscriptions/{slug}/index.html", layout(L, f"subscriptions/{slug}/", title, desc, body, 2, ld=art(title, f"{SITE}/{'' if L == 'en' else 'es/'}subscriptions/{slug}/"), drop="DROP-002"))


def build_subs(lang):
    for s, n, p, k, ke in SUBS:
        sub_page(lang, s, n, p, k, ke)
    fm = (lambda v: f"{round(v):,}") if lang == "en" else (lambda v: f"{round(v):,}".replace(",", "."))
    rows = "".join(f'<tr><td><a href="{s}/">{esc(n if lang == "en" else SUB_NAME_ES.get(s, n))}</a></td><td>{p:.2f}</td><td>{fm(p*12)}</td><td>{fm(p*120)}</td><td>{fm(p*240)}</td></tr>' for s, n, p, k, ke in SUBS)
    total = sum(p for s, n, p, k, ke in SUBS)
    if lang == "en":
        body = f"""<section class="hero"><span class="eyebrow">Reference</span><h1>Subscriptions, <em>one by one</em></h1><p class="lead">What each common subscription costs per year, per decade and over twenty years at today's list price. All of them together: {fm(total*120)} over ten years. Pick yours in the <a href="../drops/subscription-receipt/">calculator</a>.</p></section>
<section class="card prose"><table><tr><th>Service</th><th>Per month</th><th>Per year</th><th>10 years</th><th>20 years</th></tr>{rows}</table>
<p class="small muted">Typical 2026 list prices, no increases, no discounts. Figures are close enough in EUR, USD and GBP to read as-is.</p></section>{related(lang, "../")}"""
        write(lang, "subscriptions/index.html", layout(lang, "subscriptions/", "Subscription costs over 10 years: Netflix, Spotify, gym, cloud and more", "A table of what common subscriptions cost per year, per decade and over twenty years, with one page per service.", body, 1, drop="DROP-002"))
    else:
        body = f"""<section class="hero"><span class="eyebrow">Referencia</span><h1>Suscripciones, <em>una a una</em></h1><p class="lead">Lo que cuesta cada suscripción habitual al año, por década y en veinte años al precio de lista de hoy. Todas juntas: {fm(total*120)} en diez años. Elige las tuyas en la <a href="../drops/subscription-receipt/">calculadora</a>.</p></section>
<section class="card prose"><table><tr><th>Servicio</th><th>Al mes</th><th>Al año</th><th>10 años</th><th>20 años</th></tr>{rows}</table>
<p class="small muted">Precios de lista típicos de 2026, sin subidas ni descuentos. Las cifras son lo bastante parecidas en EUR, USD y GBP para leerlas tal cual.</p></section>{related(lang, "../")}"""
        write(lang, "subscriptions/index.html", layout(lang, "subscriptions/", "Coste de las suscripciones en 10 años: Netflix, Spotify, gimnasio, nube y más", "Tabla de lo que cuestan las suscripciones habituales al año, por década y en veinte años, con una página por servicio.", body, 1, drop="DROP-002"))


# ---------------- notes (content hub, English) ----------------
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
        m = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in meta.strip().splitlines())}
        posts.append((m.get("date", TODAY), fn[:-3], m["title"], m["summary"], body))
    posts.sort(reverse=True)
    for date, slug, title, summary, body in posts:
        ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": title, "datePublished": date, "dateModified": date, "author": {"@type": "Organization", "name": "Worth One?"}, "publisher": {"@type": "Organization", "name": "Worth One?"}, "description": summary}
        html_body = f"""<section class="hero"><span class="eyebrow">Lab notes · {date}</span><h1>{esc(title)}</h1><p class="lead">{esc(summary)}</p></section><section class="card prose">{md(body)}</section>{related("en", "../")}"""
        write("en", f"notes/{slug}.html", layout("en", f"notes/{slug}.html", f"{title} · Worth One? lab notes", summary, html_body, 1, ld=ld, alt=False))
    items = "".join(f'<a class="drop" href="{slug}.html"><span class="num">{date}</span><b>{esc(title)}</b><p>{esc(summary)}</p></a>' for date, slug, title, summary, body in posts)
    body = f"""<section class="hero"><span class="eyebrow">Notes</span><h1>Lab <em>notes</em></h1><p class="lead">How the tools are calculated, what the numbers say in aggregate, and milestones. Published only when there is something worth reading.</p></section><div class="drops">{items}</div>"""
    write("en", "notes/index.html", layout("en", "notes/", "Lab notes · Worth One?", "Method, findings and milestones of the Worth One experiment. Published only when there is something to say.", body, 1, alt=False))


# ---------------- embeds ----------------
def build_embed(lang):
    if lang == "en":
        embed_js = """/* Worth One? embed loader. Usage: <div data-worthone="doomscroll"></div><script src="%s/embed.js" async></script>  (add data-lang="es" for Spanish) */
(function(){var S="%s";document.querySelectorAll("[data-worthone]").forEach(function(el){if(el.dataset.done)return;el.dataset.done=1;var which=el.dataset.worthone||"doomscroll";var lang=el.dataset.lang==="es"?"es/":"";var f=document.createElement("iframe");f.src=S+"/"+lang+"embed/"+(which==="subscriptions"?"subscriptions":"doomscroll")+".html?src=embed&c="+encodeURIComponent(location.hostname);f.style.cssText="width:100%%;max-width:560px;height:"+(which==="subscriptions"?"820":"640")+"px;border:0;border-radius:16px;display:block;margin:0 auto";f.loading="lazy";f.title="Worth One? "+which+" widget";el.appendChild(f)})})();
""" % (SITE, SITE)
        write("en", "embed.js", embed_js)
    pre = "" if lang == "en" else "es/"
    pow_txt = "Powered by" if lang == "en" else "Con tecnología de"
    tail = "free tools for strangers" if lang == "en" else "herramientas gratis para desconocidos"
    for which, src, height in (("doomscroll", "drops/doomscroll-receipt/", 640), ("subscriptions", "drops/subscription-receipt/", 820)):
        root = "../" if lang == "en" else "../../"
        page = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Worth One? widget</title><meta name="robots" content="noindex"><link rel="stylesheet" href="{root}style.css"><script src="{root}config.js"></script><script defer src="{root}app.js"></script><style>body{{padding:10px}}.wrap{{max-width:560px}}.pow{{text-align:center;font-size:12px;margin:8px 0 0}}.pow a{{color:var(--mut)}}</style></head>
<body data-lang="{lang}" data-drop="{'DROP-001' if which=='doomscroll' else 'DROP-002'}" data-embed="1"><div class="wrap"><iframe src="../{src}?src=embed" style="width:100%;height:{height-40}px;border:0" title="Worth One? {which}"></iframe><p class="pow">{pow_txt} <a href="{SITE}/{pre}?src=embed" target="_blank" rel="noopener">Worth One?</a> · {tail}</p></div></body></html>"""
        write(lang, f"embed/{which}.html", page)
    d_attr = "" if lang == "en" else ' data-lang="es"'
    snippet_d = esc(f'<div data-worthone="doomscroll"{d_attr}></div>\n<script src="{SITE}/embed.js" async></script>')
    snippet_s = esc(f'<div data-worthone="subscriptions"{d_attr}></div>\n<script src="{SITE}/embed.js" async></script>')
    iframe_d = esc(f'<iframe src="{SITE}/{pre}embed/doomscroll.html" style="width:100%;max-width:560px;height:640px;border:0;border-radius:16px" loading="lazy" title="Doomscroll Receipt"></iframe>')
    pre_css = 'style="white-space:pre-wrap;background:var(--bg2);padding:12px;border-radius:12px;font-size:13px"'
    if lang == "en":
        body = f"""<section class="hero"><span class="eyebrow">Free widgets</span><h1>Put a drop <em>on your site.</em></h1><p class="lead">Any drop can live on your blog, resource page or newsletter site for free. One line of HTML, no account, no tracking of your readers beyond an anonymous count of widget views. Each widget carries a small "Powered by Worth One?" line.</p></section>
<section class="card prose"><h2>Doomscroll Receipt widget</h2><p>Script (recommended, responsive):</p><pre {pre_css}>{snippet_d}</pre><p>Plain iframe (WordPress, Ghost, Substack-style editors that allow iframes):</p><pre {pre_css}>{iframe_d}</pre>
<div data-worthone="doomscroll"></div></section>
<section class="card prose"><h2>Subscription Lifetime Receipt widget</h2><pre {pre_css}>{snippet_s}</pre></section>
<section class="card prose"><h2>Terms for embedding</h2><p>Free for any site, commercial or not. Keep the "Powered by Worth One?" line. Do not present the widget as your own tool. Widget views are counted anonymously (hostname and count only). That is all.</p><p class="small muted">Want a different size, a language, or a widget for another drop? <a href="https://github.com/Furiadelimon/worth-one/issues">Open an issue</a>.</p></section>
<script src="../embed.js" async></script>"""
        write(lang, "embed/index.html", layout(lang, "embed/", "Embed a free calculator widget · Worth One?", "Put the Doomscroll Receipt or Subscription Lifetime Receipt on your own site with one line of HTML. Free, no account.", body, 1))
    else:
        body = f"""<section class="hero"><span class="eyebrow">Widgets gratis</span><h1>Pon un drop <em>en tu web.</em></h1><p class="lead">Cualquier drop puede vivir en tu blog, página de recursos o newsletter gratis. Una línea de HTML, sin cuenta, sin rastrear a tus lectores más allá de un recuento anónimo de vistas del widget. Cada widget lleva una pequeña línea "Con tecnología de Worth One?".</p></section>
<section class="card prose"><h2>Widget del Ticket de Doomscroll</h2><p>Script (recomendado, adaptable):</p><pre {pre_css}>{snippet_d}</pre><p>Iframe simple (WordPress, Ghost y editores que permiten iframes):</p><pre {pre_css}>{iframe_d}</pre>
<div data-worthone="doomscroll" data-lang="es"></div></section>
<section class="card prose"><h2>Widget del Ticket de Suscripciones</h2><pre {pre_css}>{snippet_s}</pre></section>
<section class="card prose"><h2>Condiciones para insertar</h2><p>Gratis para cualquier web, comercial o no. Mantén la línea "Con tecnología de Worth One?". No presentes el widget como herramienta propia. Las vistas se cuentan de forma anónima (solo dominio y recuento). Nada más.</p><p class="small muted">¿Quieres otro tamaño, otro idioma o un widget de otro drop? <a href="https://github.com/Furiadelimon/worth-one/issues">Abre un issue</a>.</p></section>
<script src="../../embed.js" async></script>"""
        write(lang, "embed/index.html", layout(lang, "embed/", "Inserta una calculadora gratis en tu web · Worth One?", "Pon el Ticket de Doomscroll o el Ticket de Suscripciones en tu propia web con una línea de HTML. Gratis, sin cuenta.", body, 1))


def build_guide(lang):
    """Subscription-audit guide: the link target publishers can point at, and a real search-intent page."""
    ld_faq = lambda qs: {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qs]}
    if lang == "en":
        title = "How to audit your subscriptions in 20 minutes (and what they cost over 10 years)"
        desc = "A short, honest subscription audit: find everything you pay for, see the 10-year cost, and decide what to keep. Free calculator, no signup, no app."
        faq = ld_faq([("How often should I audit my subscriptions?", "Twice a year, and after any move, job change or new device. Most forgotten subscriptions are found within six months of starting them."),
                      ("What is the fastest way to find hidden subscriptions?", "Search your bank and card statements for the last 12 months, then check the subscription lists inside your phone's app store and PayPal. Those three cover almost everything."),
                      ("How much do subscriptions really cost?", "Multiply your monthly total by 120 for a decade. A typical bundle of about 68 a month is roughly 8,200 over ten years at today's prices.")])
        body = """<section class="hero"><span class="eyebrow">Guide</span><h1>Audit your subscriptions <em>in 20 minutes.</em></h1>
<p class="lead">No app, no account, no spreadsheet. Five steps, then one number that makes the decision for you: what each thing costs over ten years.</p>
<div class="row"><a class="btn acc" href="../drops/subscription-receipt/" data-nav="DROP-002">Open the free calculator &rarr;</a></div></section>
<section class="card prose">
<h2>1. Find everything (8 minutes)</h2>
<p>Three places cover almost every recurring charge. Your bank and card statements for the last twelve months, searched for the same amount appearing monthly. Your phone's subscription list: on iPhone, Settings &rarr; your name &rarr; Subscriptions; on Android, Play Store &rarr; Payments and subscriptions. And PayPal, under Automatic payments, which is where the forgotten ones hide.</p>
<p>Write each one down with its price and billing date. Annual plans count: divide by twelve so everything is comparable.</p>
<h2>2. Get the ten-year number (2 minutes)</h2>
<p>This is the step most guides skip, and it is the one that decides things. Monthly prices are designed to feel small. Put your list into the <a href="../drops/subscription-receipt/">Subscription Lifetime Receipt</a> and it prints the yearly, five-year, ten-year and twenty-year totals as a receipt, plus what that money is in concrete things. Nothing you type is uploaded; the calculation runs in your browser.</p>
<h2>3. Give each one a verdict (5 minutes)</h2>
<p>Four options, not two. <b>Keep</b> if you used it in the last month and would miss it. <b>Downgrade</b> if you use it but not at the tier you pay for, which covers most music, cloud and streaming plans. <b>Switch to annual</b> only for things you are certain about, since annual saves 15 to 20 percent but locks you in. <b>Cancel</b> if you cannot remember the last time you opened it. Untick it in the calculator first and watch the ten-year line drop; that is usually enough.</p>
<h2>4. Cancel immediately, not later (4 minutes)</h2>
<p>"I will cancel it this weekend" is what the pricing model counts on. Cancel from the same list you used to find them. Most services keep your access until the end of the period already paid, so there is nothing to gain by waiting.</p>
<h2>5. Put the next audit in the calendar (1 minute)</h2>
<p>Six months from today, plus a reminder three days before any free trial ends. That single habit is worth more than the audit itself.</p>
<h2>What this is not</h2>
<p>Not financial advice, and not an argument that subscriptions are bad. A service you use every week may be the best money you spend. The point is to decide with the ten-year figure in view instead of the monthly one, because they are the same purchase described two different ways.</p>
</section>
<section class="card support"></section>
"""
        write(lang, "guides/subscription-audit/index.html", layout(lang, "guides/subscription-audit/", title, desc, body + related(lang, "../../"), 2, ld=faq, drop="DROP-002"))
    else:
        title = "Cómo auditar tus suscripciones en 20 minutos (y lo que cuestan en 10 años)"
        desc = "Auditoría de suscripciones corta y honesta: encuentra todo lo que pagas, mira el coste a 10 años y decide qué conservar. Calculadora gratis, sin registro, sin app."
        faq = ld_faq([("¿Cada cuánto debo revisar mis suscripciones?", "Dos veces al año, y después de una mudanza, un cambio de trabajo o un móvil nuevo. Casi todas las suscripciones olvidadas se detectan en los seis meses siguientes a contratarlas."),
                      ("¿Cuál es la forma más rápida de encontrar suscripciones ocultas?", "Busca en los extractos del banco y la tarjeta de los últimos 12 meses, y luego revisa la lista de suscripciones de la tienda de apps del móvil y de PayPal. Esas tres fuentes cubren casi todo."),
                      ("¿Cuánto cuestan realmente las suscripciones?", "Multiplica el total mensual por 120 para una década. Un paquete típico de unos 68 € al mes son unos 8.200 € en diez años a precios de hoy.")])
        body = """<section class="hero"><span class="eyebrow">Guía</span><h1>Audita tus suscripciones <em>en 20 minutos.</em></h1>
<p class="lead">Sin app, sin cuenta, sin hoja de cálculo. Cinco pasos y un número que decide por ti: lo que cuesta cada cosa en diez años.</p>
<div class="row"><a class="btn acc" href="../drops/subscription-receipt/" data-nav="DROP-002">Abrir la calculadora gratis &rarr;</a></div></section>
<section class="card prose">
<h2>1. Encuéntralo todo (8 minutos)</h2>
<p>Tres sitios cubren casi cualquier cargo recurrente. Los extractos del banco y la tarjeta de los últimos doce meses, buscando el mismo importe cada mes. La lista de suscripciones del móvil: en iPhone, Ajustes &rarr; tu nombre &rarr; Suscripciones; en Android, Play Store &rarr; Pagos y suscripciones. Y PayPal, en Pagos automáticos, que es donde se esconden las olvidadas.</p>
<p>Apunta cada una con su precio y su fecha de cobro. Los planes anuales cuentan: divide entre doce para poder comparar.</p>
<h2>2. Consigue el número de los diez años (2 minutos)</h2>
<p>Es el paso que casi ninguna guía incluye y el que de verdad decide. Los precios mensuales están diseñados para parecer pequeños. Mete tu lista en el <a href="../drops/subscription-receipt/">Ticket de Suscripciones</a> y te imprime los totales al año, a cinco, a diez y a veinte años, además de qué es ese dinero en cosas concretas. Nada de lo que escribes se envía: el cálculo ocurre en tu navegador.</p>
<h2>3. Dale un veredicto a cada una (5 minutos)</h2>
<p>Cuatro opciones, no dos. <b>Conservar</b> si la usaste el último mes y la echarías de menos. <b>Bajar de plan</b> si la usas pero no al nivel que pagas, que es el caso de casi toda la música, la nube y el streaming. <b>Pasar a anual</b> solo con lo que tengas clarísimo, porque ahorra un 15-20 % pero te ata. <b>Dar de baja</b> si no recuerdas cuándo la abriste por última vez. Desmárcala primero en la calculadora y mira cómo cae la línea de diez años; suele bastar.</p>
<h2>4. Cancela ahora, no luego (4 minutos)</h2>
<p>"Lo doy de baja el fin de semana" es justo con lo que cuenta el modelo de precios. Cancela desde la misma lista que usaste para encontrarlas. Casi todos los servicios mantienen el acceso hasta el final del periodo ya pagado, así que no se gana nada esperando.</p>
<h2>5. Pon la próxima revisión en el calendario (1 minuto)</h2>
<p>Dentro de seis meses, más un aviso tres días antes de que acabe cualquier prueba gratuita. Ese hábito vale más que la propia auditoría.</p>
<h2>Lo que esto no es</h2>
<p>No es asesoramiento financiero ni un argumento contra las suscripciones. Un servicio que usas cada semana puede ser el mejor dinero que gastas. La idea es decidir con la cifra de diez años delante en vez de con la mensual, porque son la misma compra contada de dos maneras.</p>
</section>
<section class="card support"></section>
"""
        write(lang, "guides/subscription-audit/index.html", layout(lang, "guides/subscription-audit/", title, desc, body + related(lang, "../../"), 2, ld=faq, drop="DROP-002"))


def build_sitemap():
    fixed = ["", "about.html", "drops/doomscroll-receipt/", "drops/subscription-receipt/"]
    all_urls = [f"{SITE}/{u}" for u in fixed] + [f"{SITE}/es/{u}" for u in fixed] + urls["en"] + urls["es"]
    all_urls = list(dict.fromkeys(all_urls))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in all_urls) + "</urlset>\n"
    write("en", "sitemap.xml", xml)
    json.dump(all_urls, open(os.path.join(ROOT, "site", "urls.json"), "w"), indent=1)
    print(f"{len(all_urls)} urls")


if __name__ == "__main__":
    for lang in ("en", "es"):
        build_drops(lang); build_screen(lang); build_subs(lang); build_embed(lang); build_guide(lang)
    build_notes(); build_sitemap()
    print("built")
