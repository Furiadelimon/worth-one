title: How the receipts are calculated
date: 2026-09-12
summary: The exact arithmetic behind the Doomscroll Receipt and the Subscription Lifetime Receipt, so you can check it, argue with it, or reuse it.
---
Both receipts are deliberately dumb. No models, no predictions, no personalisation. One input, multiplied out. This page shows every step so nobody has to trust us.

## Doomscroll Receipt

- **Per week** = hours per day × 7.
- **Per year** = hours per day × 365.25 (the quarter accounts for leap years), then ÷ 24 to express the result in full 24-hour days. Two hours a day gives 730.5 hours, which is 30.4 days.
- **Next 5 / 10 / 20 years** = the yearly figure × 5, × 10, × 20. No compounding, no ageing, no assumptions about you living to a certain age.
- **Equivalents** use round, public figures: a book at 6 hours, the extended Lord of the Rings trilogy at 11.4 hours, every episode of Friends at about 87 hours, a language to conversational level at roughly 500 hours of study. They are illustrations, not measurements.
- **World average** is 2 hours 20 minutes a day on social media for internet users aged 16 to 64, from DataReportal's Digital 2025 report. The receipt shows your percentage distance from that figure.
- **Tier names** are jokes with fixed thresholds: under 1h "Light thumb", under 2h "Casual scroller", under 3h "Regular", under 4h "Committed", under 6h "Heavy rotation", above that "Professional thumb athlete".
- **Refund department** = minutes reclaimed per day ÷ 60 × 365.25 ÷ 24, in days per year, then × 10.

## Subscription Lifetime Receipt

- **Per month** = sum of the selected monthly prices. Default prices are typical 2026 list prices and are only starting points; every price is editable.
- **Per year** = monthly × 12. **5 / 10 / 20 years** = yearly × 5, × 10, × 20.
- No inflation, no price increases, no investment returns. The decade figure is therefore a floor: real costs are usually higher.
- **Comparisons** are fixed reference prices: a car at 30,000 (the target of this experiment), a coffee at 3, a week of groceries at 80, a return flight at 1,200. The currency symbol is cosmetic; the arithmetic is identical.
- **Tiers** by monthly total: under 25 "Minimalist", under 60 "Streaming citizen", under 120 "Bundle enjoyer", under 200 "Recurring revenue hero", above that "The landlord's favourite tenant".

## What is not calculated

Nothing about health, attention, addiction or wellbeing. The receipts only convert one unit into another (hours into days, months into decades) because the second unit is the one people remember. What you do with the number is yours.

## Reuse

The pages are plain HTML and JavaScript, MIT licensed, in the [public repository](https://github.com/Furiadelimon/worth-one). You can also [embed either receipt](../embed/) on your own site.
