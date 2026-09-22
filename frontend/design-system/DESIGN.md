# LMS Infinity Learn — Design System

Read this before building or changing any screen in the LMS (saleslms.infinitylearn.com).
It is written for people and AI agents alike: every rule is explicit, and every value has a name.

| What | Where |
|---|---|
| Tokens (source of truth, W3C DTCG JSON) | `frontend/design-system/tokens.json` |
| Tokens in code (CSS variables) | `frontend/src/styles/sales-theme.css` (`--il-*`) |
| Figma library (variables, text styles, components) | Figma file **LMS Infinity Learn — Design System** |
| Every screen, desktop + mobile | Figma file **LMS Infinity Learn** |
| Report colours and band logic | `frontend/src/pages/Reports/reportUtils.js` |

Token names are identical in all three places: `color/semantic/brand` in Figma is `color.semantic.brand` in
`tokens.json` and `var(--il-primary-50)` in CSS. Figma variables carry the CSS variable as their code syntax.

---

## 1. Principles

1. **One brand colour.** Blue `#027BFF` means "act here" or "you are here". Don't use it for decoration.
2. **White panel on blue chrome.** Desktop: a 240px transparent sidebar on the blue gradient, and content in a
   white panel with 24px radius. Mobile: white page, bottom-sheet modals, no floating panel.
3. **Pills everywhere.** Every button, chip, status and badge is fully rounded (999px). Cards are 24px.
4. **Say what happens next.** Each screen has one obvious next step: "Continue learning", "Add person".
5. **Plain words.** Say "Day 3", not "CRT 3"; "Team admin", not "Moderator"; "Done", not "Evaluation Completed".
6. **Only real data states.** Design for empty, locked, in-progress and done. The journey is locked step by step.

## 2. Colour

Use **semantic** tokens in components; primitives exist only to define them.

| Token | Hex | Use |
|---|---|---|
| `brand` | #027BFF | Primary button, active chip, "Today" pill, progress bar |
| `brand-strong` | #0062CC | Links, active sidebar item text |
| `brand-navy` | #00254C | Hero banner, selected filter chip, Super Admin badge |
| `brand-soft` | #E6F2FF | Team chips, avatar circles, tinted rows |
| `brand-strip` | #F4F9FF | Card header strips, the current journey row (with 1px #CFE5FF border) |
| `accent` | #FCDE5A | Progress ring and streak only. Never as text on white (fails contrast) |
| `text` / `text-muted` / `text-subtle` | #080E14 / #52565C / #85878A | Headings+body / captions+emails / placeholders |
| `surface` / `surface-muted` / `border` | #FFFFFF / #F2F2F2 / #E6E7E8 | Cards / neutral pills+inputs / dividers |
| `success` + `success-soft` | #04742D + #D6F4DE | "Done" pill, completed steps |
| `warning` + `warning-soft` | #B36E00 + #FFEECC | Team admin badge, lock notices |
| `danger` + `danger-soft` | #F03E3E + #FEF0F0 | Errors and destructive actions only |

**Score bands** (all reports): Excellent ≥90%, Good 80–90%, Average 60–80%, Needs improvement <60%.
Each band has `bg`, `soft`, `text`, `solid` colours in `color.band.*`. Always show the band label next to the colour,
never colour alone.

## 3. Type

Poppins only, weights 400/500/600. Letter-spacing +0.02em.

| Style | Size/Line | Weight | Use |
|---|---|---|---|
| `page-title` | 28/36 | 600 | One per page, top left |
| `hero-title` | 28/34 | 600 | White, on the navy hero |
| `section-title` | 18/24 | 600 | Card headings |
| `row-title` | 15/22 | 500 | List rows, journey steps, tabs |
| `body` / `body-strong` | 14/21 | 400 / 500 | Paragraphs / names in tables, sidebar |
| `button` | 14/20 | 600 | Button labels |
| `caption` | 12/16 | 400 | Sub-lines, emails, meta |
| `label` | 12/18 | 600 | Pills, badges, counters |
| `overline` | 12/14 | 600, uppercase, +0.08em | Sidebar group headings |

## 4. Space, radius, elevation

- 4px grid: 4, 8, 12, 16, 20, 24, 28, 32, 40, 48. Card padding 24 (desktop) / 16 (mobile). Gap between cards 24.
- Radius: 8 icon buttons · 12 tiles · 16 list rows · 20 report header card · 24 cards and hero · 999 pills.
- Shadows: `soft` (0 1 12 / 12% black) on cards; `chip` (0 1 4 / 16%) on the active sidebar item and floating pills;
  `hover` (0 4 20 / 16%) plus a 2px lift on clickable cards. There are no other shadows.

## 5. Components

Figma component names match the headings. Vue files are the implementation.

### Button — `Button / {Primary|Secondary|Ghost|Danger} / {Default|Disabled}`
Height 44, padding 0 24, radius pill, `button` type. Primary: `brand` bg, white text. Secondary: white bg, 1px
`border`, `brand-strong` text. On the navy hero the primary action is white with navy text ("Continue learning").
One primary button per screen area. Icon (16px, Lucide) sits left of the label with an 8px gap.

### Status pill — `Pill / {Done|Today|Up next|Locked|After}`
Height 24, padding 3 10, `label` type. Done = `success-soft`/`success`. Today = `brand`/white. Up next and Locked =
`surface-muted`/`text-muted`. Journey rows use exactly one of these.

### Role badge — `Badge / {Learner|Instructor|Manager|Team admin|Super Admin}`
Fixed width 112, height 24, `label` type. Learner `surface-muted`/`text-muted`; Instructor `brand-soft`/`brand-strong`;
Manager #EFEBFF/#5B3FD6; Team admin `warning-soft`/#8A5A00; Super Admin `brand-navy`/white.

### Filter chip — `Chip / {Default|Selected}` (with counter)
Height 40, padding 0 8 0 16, radius pill, 1px `border`, `body` type, and a 24px round counter on the right.
Selected: `brand-navy` bg and border, white text, the counter white at 20%.

### Team tag — `Tag / Team`
`brand-soft` bg, `brand-strong` text, 11.5/600, radius 6, padding 2 8. Primary team first; others neutral.

### Journey step — `Journey step / {Done|Current|Next|Locked}`
Row height 64 (current 73 with a 4px progress bar), radius 16, padding 11 12. Left: 40px circle (tick on
`success-soft`; number on `brand` for current; lock on `surface-muted`). Middle: `row-title` + `caption`
("3 of 5 sessions"). Right: status pill + chevron. Current row: `brand-strip` bg and 1px #CFE5FF border.

### Hero banner — `Hero / Learner`
Navy (#00254C → #013166) card, radius 24, padding 28. Greeting in `caption` white 75%, `hero-title`, meta line,
white pill button. Progress ring on the right: 136px, `accent` arc on a navy 30% track, "52% DONE" centred.

### Card — `Card / Section`
`surface`, radius 24, `soft` shadow, header row with `section-title` and optional right-hand meta or a
"View details →" pill. Report sections add a `brand-strip` header strip (`ReportSection.vue`).

### Person row — `Row / Person`
Avatar 36 (initials on `brand-soft`, or navy for admins), name `body-strong`, email `caption`, role badge,
team tags, manager ("Neha Kapoor · TM"), edit icon button (28, radius 8).

### Sheet — `Sheet / Desktop modal` and `Sheet / Mobile bottom`
Desktop: centred, max width 560, radius 24. Mobile (<768): bottom sheet, top radius 24, drag handle, sticky footer
with the primary button full width (`frontend/src/pages/Team/Sheet.vue`).

### Report blocks
`ReportSection`, `InsightsCard` (lavender gradient, bullet insights, tone chip good/warn/bad), `QuadrantChart`
(75% threshold lines, four labelled corners), `ScoreTrend` (bars with a star on the best), `BandAccordion`
(subject rows coloured by band). All under `frontend/src/pages/Reports/`.

## 6. Layout

- Desktop 1440: sidebar 240 (logo + user switcher on top, nav items 40 high, pill-shaped, active = white pill with
  `chip` shadow and `brand-strong` text), content column max 1112 inside the white panel, 28px page padding.
- Mobile 390: 16px side gutters, no sidebar (bottom navigation / hamburger), cards full width, tables become
  stacked rows, modals become bottom sheets. No horizontal page scroll; wide tables scroll inside their card.
- Page skeleton: `page-title` (+ one-line description in `caption`) → primary action top right → filters/tabs →
  content cards.

## 7. Content and naming

- The journey is: Hello ILians → Day 1 … Day 5 → Final review → Go live · OJT → Certificate.
  Day titles: 1 Welcome to Infinity Learn · 2 CBSE Foundation & Math Champ · 3 Test Prep: JEE & NEET ·
  4 LeadSquared & your leads · 5 Mock calls & demo.
- Roles shown to people: Learner, Instructor, Manager, Team admin, Super Admin. Teams: Retail Sales, Retail Sales
  Training, CS, B2B IL Schools, SCA Sales, Genius, AcadOps, Delivery, HR.
- Sentence case everywhere. Numbers as digits. Dates as "22 Sep 2026".

## 8. Accessibility

- Text contrast ≥ 4.5:1 (yellow is never text on white; `text-subtle` only for placeholders).
- Touch targets ≥ 40px (chips 40, buttons 44). Focus ring: 2px `brand` at 40% outside the control.
- Status is never colour-only: pills carry words, bands carry labels, charts carry a legend.

## 9. Rules for AI agents

1. Use tokens by name from `tokens.json`; never invent hex values. If a colour is missing, stop and ask.
2. Reuse the components in §5 (and the Vue files named there) before creating new ones.
3. Every new screen needs desktop 1440 and mobile 390 states, plus empty, loading and locked/no-access states.
4. Use `__()` for every user-facing string; it does not support format arguments, so use template literals.
5. Match the naming in §7 exactly: never show "CRT", "Moderator", "System Manager" or raw doctype names to learners.
6. When adding a token: add it to `tokens.json`, `sales-theme.css`, and the Figma variables, with the same name.
