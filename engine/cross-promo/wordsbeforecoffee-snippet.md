# Words Before Coffee → Worth One cross-promotion (ready to paste)

One discreet, tracked, reversible link. It does not merge the brands: Words Before Coffee lends the audience,
Worth One stays a separate project. Spanish, because that audience is Spanish.

**File:** `app/templates/_games_sheet.html` (the "Más juegos" sheet shared by the four games)
**Where:** immediately after the `</div>` that closes `.ws-games`, before the existing `<p class="sheet__tip">`.

```html
  <p class="sheet__tip">
    Otro descanso mental, de la misma cocina:
    <a href="https://furiadelimon.github.io/worth-one/es/?src=wordsbeforecoffee" target="_blank" rel="noopener" id="link-worth-one">Worth One?</a>
  </p>
```

That is the whole change. To remove it, delete those four lines.

## Why this placement
The sheet is opened deliberately by someone already looking for "what else is there", which is the only moment a
link to another site is welcome rather than an interruption. It sits below the games, visually separated, and it is
never the first thing anyone sees.

## Tracking
The `?src=wordsbeforecoffee` tag makes every visit attributable in the Worth One control center: visitors, drop
results, shares and "worth €1" answers coming from this link are counted separately from every other source.
If it produces nothing in two weeks, delete it.

## Optional second placement (only if the first one works)
The Coffee Score page (`coffee_score.html`), under the score, same one-line format. Do not add more than these two.
