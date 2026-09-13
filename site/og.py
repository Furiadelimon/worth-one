#!/usr/bin/env python3
"""Generates the Open Graph cards and the press-kit visuals from the product itself (stylised receipts).
Runs on the LXC (Pillow + DejaVu fonts). Output: docs/assets/*.png
  og.png / og-doomscroll.png / og-subscriptions.png            1200x630
  square-doomscroll.png / square-subscriptions.png            1080x1080
  vertical-doomscroll.png / vertical-subscriptions.png        1080x1920
  og-es-doomscroll.png / og-es-subscriptions.png / og-es.png  1200x630 (Spanish)
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "assets")
os.makedirs(OUT, exist_ok=True)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO_R = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
PAPER, INK, MUT, ACC, MONEY, BG = "#ffffff", "#141311", "#6f6a62", "#ff4a1c", "#178a52", "#f4f1ea"


def F(path, size):
    return ImageFont.truetype(path, size)


def center(d, xy, text, font, fill):
    w = d.textlength(text, font=font)
    d.text((xy[0] - w / 2, xy[1]), text, font=font, fill=fill)


def dashed(d, y, x0, x1, color="#9a9a9a"):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + 12, x1), y)], fill=color, width=2)
        x += 22


def receipt_card(size, title, small, big, em, rows, color, foot, tilt=True):
    """A receipt drawn on paper, scaled to the canvas."""
    W, H = size
    im = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(im)
    # receipt geometry
    rw = int(min(W * 0.62, H * 0.78)) if W >= H else int(W * 0.78)   # landscape: bound by height so the receipt never overflows
    rh = int(H * 0.86) if W >= H else min(int(H * 0.86), int(rw * 1.12))   # portrait: receipt height follows content, not the canvas
    x0 = (W - rw) // 2
    y0 = (H - rh) // 2
    rec = Image.new("RGB", (rw, rh), PAPER)
    rd = ImageDraw.Draw(rec)
    pad = int(rw * 0.08)
    sc = rw / 640  # scale factor relative to a 640px-wide receipt
    y = int(40 * sc)
    center(rd, (rw / 2, y), title, F(MONO, int(30 * sc)), INK); y += int(46 * sc)
    center(rd, (rw / 2, y), "worth one?", F(MONO_R, int(20 * sc)), MUT); y += int(40 * sc)
    dashed(rd, y, pad, rw - pad); y += int(34 * sc)
    center(rd, (rw / 2, y), small, F(MONO_R, int(26 * sc)), "#555"); y += int(46 * sc)
    bigf = F(MONO, int(92 * sc))
    while rd.textlength(big, font=bigf) > rw - 2 * pad and bigf.size > 30:
        bigf = F(MONO, bigf.size - 4)
    center(rd, (rw / 2, y), big, bigf, color); y += int(bigf.size * 1.15)
    center(rd, (rw / 2, y), em, F(MONO_R, int(26 * sc)), "#333"); y += int(50 * sc)
    dashed(rd, y, pad, rw - pad); y += int(30 * sc)
    for l, r in rows:
        rd.text((pad, y), l, font=F(MONO_R, int(24 * sc)), fill=INK)
        w = rd.textlength(r, font=F(MONO, int(24 * sc)))
        rd.text((rw - pad - w, y), r, font=F(MONO, int(24 * sc)), fill=INK)
        y += int(38 * sc)
    dashed(rd, y + int(8 * sc), pad, rw - pad); y += int(44 * sc)
    # barcode
    bx = pad + int(rw * 0.08); bw = rw - 2 * bx; xx = bx
    while xx < bx + bw:
        for wdt, gap in ((2, 2), (1, 4), (3, 2)):
            if xx + wdt > bx + bw: break
            rd.rectangle([xx, y, xx + wdt * max(1, int(sc)), y + int(34 * sc)], fill=INK); xx += (wdt + gap) * max(1, int(sc))
    y += int(50 * sc)
    center(rd, (rw / 2, min(y, rh - int(40 * sc))), foot, F(MONO_R, int(18 * sc)), "#888")
    # zigzag edges
    tooth = max(6, int(10 * sc))
    for i in range(0, rw, tooth * 2):
        rd.polygon([(i, 0), (i + tooth, tooth), (i + tooth * 2, 0)], fill=BG)
        rd.polygon([(i, rh), (i + tooth, rh - tooth), (i + tooth * 2, rh)], fill=BG)
    if tilt:
        rec = rec.rotate(1.6, expand=True, fillcolor=BG, resample=Image.BICUBIC)
        x0 = (W - rec.width) // 2; y0 = (H - rec.height) // 2
    # shadow
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rectangle([x0 + 10, y0 + 18, x0 + rec.width + 10, y0 + rec.height + 18], fill=(0, 0, 0, 60))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    im = Image.alpha_composite(im.convert("RGBA"), sh).convert("RGB")
    im.paste(rec, (x0, y0))
    return im


def brand(im, text):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([28, 28, 74, 74], radius=12, fill=INK)
    center(d, (51, 40), "€1", F(MONO, 22), BG)
    d.text((88, 36), "WORTH ONE?", font=F(SANS, 26), fill=INK)
    w = d.textlength(text, font=F(SANS_R, 20))
    d.text((im.width - w - 30, 44), text, font=F(SANS_R, 20), fill=MUT)
    return im


DOOM = dict(title="YOUR LIFE RECEIPT", small="2 hours a day", big="= 304 days", em="of your next 10 years",
            rows=[("Per year", "30 days"), ("Next 20 years", "1.7 years"), ("Your tier", "Casual scroller")], color=ACC, foot="get yours · free · no account")
DOOM_ES = dict(title="TICKET DE TU VIDA", small="2 horas al día", big="= 304 días", em="de tus próximos 10 años",
               rows=[("Al año", "30 días"), ("Próximos 20 años", "1,7 años"), ("Tu nivel", "Scroll casual")], color=ACC, foot="el tuyo · gratis · sin cuenta")
SUBS = dict(title="SUBSCRIPTION RECEIPT", small="€14.99 a month doesn't look like much", big="€1,799", em="over 10 years. That was one of them.",
            rows=[("Netflix", "€13.99"), ("Spotify", "€10.99"), ("Gym", "€35.00"), ("10 YEARS", "€8,278")], color=MONEY, foot="print yours · free · no account")
SUBS_ES = dict(title="TICKET DE SUSCRIPCIONES", small="14,99 € al mes no parece mucho", big="1.799 €", em="en 10 años. Y eso era solo una.",
               rows=[("Netflix", "13,99 €"), ("Spotify", "10,99 €"), ("Gimnasio", "35,00 €"), ("10 AÑOS", "8.278 €")], color=MONEY, foot="el tuyo · gratis · sin cuenta")


def home_card(size, lang="en"):
    W, H = size
    im = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(im)
    left = receipt_card((int(W * 0.5), H), **DOOM if lang == "en" else DOOM_ES)
    im.paste(left.crop((int(W * 0.5) // 2 - 260, 0, int(W * 0.5) // 2 + 260, H)), (W - 560, 0))
    d = ImageDraw.Draw(im)
    x = 70
    d.text((x, 150), "Small things", font=F(SANS, 78), fill=INK)
    d.text((x, 240), "worth trying." if lang == "en" else "que merecen", font=F(SANS, 78), fill=ACC)
    if lang == "es":
        d.text((x, 330), "un minuto.", font=F(SANS, 78), fill=ACC)
    sub = ("Free little tools for your time,\nyour money and your curiosity." if lang == "en" else "Herramientas gratis para tu tiempo,\ntu dinero y tu curiosidad.")
    d.multiline_text((x, 360 if lang == "en" else 440), sub, font=F(SANS_R, 30), fill=MUT, spacing=10)
    d.text((x, 520), "free · no account · no ads" if lang == "en" else "gratis · sin cuenta · sin anuncios", font=F(MONO_R, 24), fill=MONEY)
    return brand(im, "worth-one" if lang == "en" else "worth-one/es")


def main():
    home_card((1200, 630)).save(os.path.join(OUT, "og.png"), optimize=True)
    home_card((1200, 630), "es").save(os.path.join(OUT, "og-es.png"), optimize=True)
    for name, spec, spec_es in (("doomscroll", DOOM, DOOM_ES), ("subscriptions", SUBS, SUBS_ES)):
        brand(receipt_card((1200, 630), **spec), "get yours in 10 seconds").save(os.path.join(OUT, f"og-{name}.png"), optimize=True)
        brand(receipt_card((1200, 630), **spec_es), "el tuyo en 10 segundos").save(os.path.join(OUT, f"og-es-{name}.png"), optimize=True)
        brand(receipt_card((1080, 1080), **spec), "").save(os.path.join(OUT, f"square-{name}.png"), optimize=True)
        brand(receipt_card((1080, 1920), **spec), "").save(os.path.join(OUT, f"vertical-{name}.png"), optimize=True)
    print("assets:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
