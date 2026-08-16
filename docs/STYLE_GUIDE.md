# Debrief Golf — Style Guide

Status: living document. Governs `apps/web`'s visual design system —
tokens, typography, components, and UI copy tone. Reference: an editorial
private-club membership brand (ordrhealth.com) — think *member's handbook*
or *caddie's field notes*, not a fitness tracker.

## 1. Aesthetic direction

**Quiet confidence, not gamification.** Debrief Golf reports on your game
the way a good caddie would: plainly, a little dry, without exclamation
points. The visual language is closer to a golf club's weekly newsletter
than a sports app — warm paper, restrained color, serif headlines, small
tracked labels. No neon greens, no badge/streak UI, no heavy shadows or
pill-shaped buttons.

If a screen looks like it belongs in a members-only clubhouse binder,
it's right. If it looks like a fitness-tracker dashboard, it's wrong.

## 2. Color

All colors are CSS custom properties in `apps/web/src/app/globals.css`,
exposed to Tailwind via `@theme inline` (so `bg-primary`, `text-muted-foreground`,
`border-border`, etc. all resolve to these). Light values below; a
parallel `.dark` palette exists for completeness but isn't the focus of
this brief — paper-and-ink is a light-mode-first aesthetic.

The **Safe as** column says what a token may be used for, measured against
`--card` (`#FBF8F0`): **Text** clears the 4.5:1 WCAG AA floor for normal
text; **Fill only** clears 3:1 for non-text (borders, meter fills, chart
marks) but must never carry body text.

| Token | Hex | Safe as | Use |
|---|---|---|---|
| `--background` | `#F3EEE1` | — | Page background — warm aged paper, never stark white |
| `--card` | `#FBF8F0` | — | Card/surface — a hair lighter than the page, distinguished by a hairline border, not elevation |
| `--foreground` | `#211D17` | Text | Body text ("ink") — warm near-black, never pure `#000` |
| `--muted-foreground` | `#726A5A` | Text | Secondary text, captions, kickers |
| `--muted` | `#EAE2CE` | Fill only | Subtle fill — hover states, quiet backgrounds |
| `--border` | `#DED2B4` | Fill only | Hairline rules — the primary way this system shows structure |
| `--primary` | `#28402F` | Text | The one accent — deep fairway green. CTAs, active states, small emphasis only |
| `--accent-hover` | `#1D3123` | Text | Primary button/link hover — a deliberately darker green, not a lighter tint |
| `--secondary` | `#E7DFCB` | Fill only | Secondary button surface |
| `--destructive` | `#9C4530` | Text | Errors — a muted clay/rust, not a stock red |
| `--status-good` | `#3F6B4A` | Text | Positive status (distinct from `--primary` so CTAs and status don't compete) |
| `--status-warning` | `#8A5E1B` | Text | Caution — muted ochre |
| `--status-serious` | `#A4502E` | Text | Between warning and critical. Currently unused — wire it up or delete it, don't let it rot |
| `--status-critical` | `#9C4530` | Text | Same rust as `--destructive` — one "something's wrong" color, not two |

**Rules:**
- **One accent.** Fairway green is it. Don't introduce a second bright
  color for "variety" — everything else is ink, paper, or grey.
- **Never pure black or white.** `--foreground` and `--background` both
  carry a warm undertone. If you're tempted to write `text-black` or
  `bg-white`, use the tokens instead.
- Status colors (`--status-*`) were retinted from their original vivid
  defaults to sit inside this palette — this is a deliberate, considered
  override for brand coherence, not an oversight of the "fixed" comment
  that used to guard them.
- **Check contrast before retinting.** The palette is muted by design,
  which puts warm mid-tones close to the AA floor: `--status-warning`
  shipped at `#B9812C` for several phases at 3.17:1 against `--card`,
  used as the text for "Needs audit" — the least legible text in the app
  was the text saying something needed attention. Muted is the aesthetic;
  illegible isn't.

## 3. Typography

**Pairing:** Fraunces (editorial serif) for headlines and stat callouts,
Geist Sans (clean neo-grotesque) for UI, body copy, and data. Loaded via
`next/font/google` in `src/app/layout.tsx`; use `font-serif` / `font-sans`
Tailwind utilities (or `--font-heading`, which aliases to the serif).

**Overline labels** — small-caps-style section kickers ("ROUND SUMMARY",
"TODAY'S DEBRIEF"): uppercase, `0.14em` letter-spacing, `text-xs`,
`text-muted-foreground` by default. Use the `<Overline>` component or the
`.kicker` utility class directly. True OpenType small-caps aren't
reliable across this font pairing, so this is an uppercase+tracking
approximation — good enough, and more portable.

> **The class is `.kicker`, not `.overline`.** Tailwind ships a built-in
> `overline` utility for `text-decoration-line: overline`, and the
> utilities layer outranks `@layer components` — so while the class was
> named `.overline`, every kicker, nav link, and stat caption in the app
> silently drew a stray rule above itself. Don't rename it back, and don't
> write `class="overline"` expecting this style.

| Role | Class / component | Notes |
|---|---|---|
| Overline | `<Overline>` / `.kicker` | Section kickers, stat captions |
| H1 | `font-serif text-3xl md:text-4xl font-medium` | Page titles |
| H2 | `font-serif text-2xl font-medium` | Section headings |
| H3 / Card title | `font-serif text-xl font-medium` | `<CardTitle>` |
| Body | `font-sans text-sm` (default) | UI copy, paragraphs |
| Small / caption | `text-xs text-muted-foreground` | Helper text, detail lines |
| Stat numeral | `.stat-numeral` (`font-serif text-4xl tabular-nums`) | Scores, Strokes Gained, handicap — always tabular so a column lines up |

## 4. Spacing, radius, shadow

- **Radius:** `--radius: 0.1875rem` (3px) — small, not zero. Derived
  radii (`rounded-sm/md/lg/xl`) scale proportionally from this one token;
  change it there, not per-component.
- **Shadows: avoid them.** Elevation is a hairline border
  (`border border-border`), not `box-shadow`. None of the base components
  use a drop shadow. If a floating element (a menu, a tooltip) genuinely
  needs to separate from the page, use a small, near-invisible shadow —
  never the default Tailwind `shadow-lg`/`shadow-xl` scale.
- **Spacing:** standard Tailwind scale, no custom tokens. Prefer generous
  whitespace over dense stacking — cards use `p-6`, not `p-3`.
- **Content measure.** Pick from these three; don't invent a fourth, or
  the content column visibly jumps as a reader moves between pages:
  | Width | For |
  |---|---|
  | `max-w-5xl` | Analytics and dashboard pages — multi-column, side-by-side cards (`/`, `/practice`, hole replay, manual shot entry) |
  | `max-w-3xl` | Reading pages and single-flow forms (`/rounds`, `/rounds/new`, settings, the audit wizard) |
  | `max-w-md` | Auth only (`/login`) |

**Icons.** Typographic glyphs — `✦ • ↑ ↓ ✓ ⚠ ←` — are in. Icon *sets* are
out: no Lucide, no Heroicons, no glyph fonts, and no icon-only buttons. A
control that needs a label gets a word ("Menu", "Close", "Edit geometry"),
not a hamburger. This rule was being cited from memory in code comments
before it was ever written down here, which is how conventions get lost.

**Focus.** A crisp `outline-2 outline-offset-2 outline-ring`, not the
shadcn-default blurred `ring` — a soft halo is the same kind of glow the
"avoid shadows" rule above already rejects for surfaces, and it's the one
place the `destructive` button used to look pink instead of rust.
`Input`/`Select` thicken their bottom rule to 2px on focus (`-mb-px`
cancels the added height so nothing shifts) and add a faint `bg-muted/40`
tint — a 1px color-only change undershoots WCAG 2.4.13's indicator-size
floor, and next to a `.kicker` label in the same muted palette it was easy
to miss which field actually had focus.

## 5. Imagery & texture

Not yet implemented (no imagery in the app today), but the intended
treatment for whenever course/lifestyle photography is added:
- Black-and-white or heavily desaturated — never full-color stock photos.
- A subtle paper-grain texture on large flat backgrounds rather than flat
  fill, if/when a texture asset is sourced.
- Section breaks use `<Divider>` (a hairline rule broken by a small ✦ or
  •), not photography or heavy icon dividers.

## 6. Components

All in `apps/web/src/components/ui/` unless noted.

- **`Button`** (`button.tsx`) — variants `default` (fairway green fill,
  `--accent-hover` on hover) / `outline` / `secondary` / `ghost` /
  `destructive` / `link`. New `label="overline"` prop renders the button
  label uppercase and tracked — use it for a primary, formal CTA ("SAVE
  COURSE," "SUBMIT ROUND"); leave secondary/ghost actions in sentence case
  (`label="sentence"`, the default) so they read quieter.
- **`Card`** (`card.tsx`) — `Card` / `CardHeader` / `CardTitle` /
  `CardDescription` / `CardContent` / `CardFooter`. Hairline border, warm
  surface, no shadow, generous padding (`p-6`).
- **`Input`** (`input.tsx`) — underline style: a single bottom hairline,
  no box, focuses to the fairway-green border color. Pair with an
  `<Overline>` as the field label placed above.
- **`StatTile`** (`src/components/stat-tile.tsx`, not `ui/`) — **this is
  the project's stat-display component** (named `StatTile` for historical
  reasons — it predates this design system and is already threaded
  through `RoundSnapshot`, `TigerFiveMeter`, and Smart Bag). Large serif
  numeral on top, an `<Overline>` caption beneath, optional detail line.
  `tone` (`good`/`bad`/`neutral`) drives color; `indicator`
  (`delta`/`status`) picks ↑/↓ vs. ✓/⚠.
- **`Overline`** (`overline.tsx`) — the small-caps-style label described
  above. `as` prop for inline use; `accent` prop switches it to fairway
  green for a kicker that should read as emphasized, not routine.
- **`Divider`** (`divider.tsx`) — hairline + centered glyph (`✦` default,
  `•` for a quieter break). Use between major sections of a page instead
  of stacking cards edge-to-edge.
- **`MembershipCard`** (`membership-card.tsx`) — the player-profile/
  handicap-card pattern: double hairline rule top and bottom, a monogram
  instead of an avatar photo, handicap index as the one large serif
  numeral. Reuse this pattern anywhere a player's identity needs a
  formal, "membership card" treatment rather than a generic profile
  widget.
- **`Select`** (`select.tsx`) — the `Input` treatment for dropdowns, so a
  `<select>` doesn't read as a leftover browser default beside one. Same
  underline, same focus color. Pair with an `<Overline>` label above.
- **`NavBar`** (`src/components/nav-bar.tsx`, not `ui/`) — a masthead, not
  a toolbar: serif wordmark, uppercase text links (via `.kicker`), an
  understated underline (not a pill or tab background) for the active
  page. Collapses behind a text "Menu"/"Close" toggle below `md`.

## 7. Tone of voice in UI copy

Confident, dry, a little witty. Short and declarative over exclamatory
SaaS-speak.

| Instead of | Write |
|---|---|
| "Your round has been successfully saved!" | "Round logged." |
| "Oops! Something went wrong." | "Couldn't save that. Try again." |
| "You're doing great! Keep it up!" | (say nothing, or state the number) |
| "Please enter a valid user ID" | "Enter a user ID." |
| "Successfully connected to Garmin!" | "Garmin connected." |

Rules of thumb:
- Past tense, done deal: "Course saved," not "Course has been saved."
- No exclamation points unless something is actually alarming.
- State the fact; let the number or the fact carry the weight, not
  adjectives around it.
- Error messages say what happened and, if useful, what to do — no
  apology theater ("Oops," "Whoops," "Uh-oh").

## 8. What's actually applied where

Tokens (color, radius, border) are CSS variables read by every existing
screen already, so the palette and radius change is effectively global —
every page in the app inherited the new look the moment `globals.css`
changed, without needing a per-file pass. The component-level rebuild
(serif stat numerals, overlines, dividers, underline inputs, the
masthead nav) is fully realized on:

- The dashboard / round debrief screen (`src/app/page.tsx`,
  `round-snapshot.tsx`, `tiger-five-meter.tsx`) — the flagship proof
  screen for this system.
- `NavBar`, `Button`, `Card`, `Input`, `StatTile` — used across the rest
  of the app, so every screen that already uses these shared primitives
  picked up the new treatment for free.

Screens built before this design system (course builder, manual shot
entry, hole replay, the audit wizard) inherited the palette/radius but
still use hand-written Tailwind classes for their layout rather than the
new `Card`/`Overline`/`Divider` components — a natural next pass, not
done in this session. `git grep -rL "components/ui/card"
apps/web/src/app` is a reasonable way to find what's left.
