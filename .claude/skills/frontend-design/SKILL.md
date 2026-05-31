---
name: spendly-ui-designer
description: >
  Generates modern, production-ready UI components and pages for Spendly — a Flask + SQLite
  expense tracker (github.com/nancyp321/expense-tracker). Outputs clean HTML (Jinja2-compatible),
  well-structured CSS, and minimal JS consistent with the existing Spendly design system.

  Use this skill whenever the user says things like:
  - "Design the ___ page"
  - "Create UI for ___"
  - "Build a component for ___"
  - "Redesign / improve ___"
  - "Make a [dashboard / form / modal / card / table] for Spendly"
  - Any UI or frontend task related to the Spendly expense tracker

  Trigger even if the user doesn't say "Spendly" explicitly — if they're working on this
  expense tracker project and ask for any page, component, or visual improvement, use this skill.
---

# Spendly UI Designer

You generate polished, production-ready UI for the **Spendly** expense tracker.
Output: structured UI brief → clean code (HTML + CSS, optionally JS).

---

## Project Overview

**Spendly** is a Flask + SQLite expense tracker, built step-by-step as a learning project.

- **Backend**: Python / Flask, Jinja2 templates, SQLite
- **Template structure**: All pages extend `templates/base.html`
- **CSS**: Single file at `static/css/style.css` — CSS custom properties in `:root`
- **JS**: `static/js/main.js` (minimal; add only what's needed)
- **Icon library**: Use **Lucide Icons** (SVG-based, aesthetic, consistent)
- **Routes / pages so far**: landing, register, login, logout, profile, add_expense, edit_expense, delete_expense

Read `references/design-system.md` before writing any code — it has all tokens, color palette, font names, and conventions.

---

## Response Structure

For every UI request, respond in **three parts**:

### Part 1 — UI Structure (brief)
In 4–8 bullet points, describe:
- Layout type (e.g. centered card, sidebar + main, full-width)
- Key sections / zones
- Notable interactions or states
- Whether 3D elements would enhance this component (and which ones)
- Any assumptions made about data or context

### Part 2 — 3D Design Check (when applicable)
Before writing code, assess whether 3D elements would meaningfully enhance the component.

**Prompt the user for approval if any of these apply:**
- Hero sections / landing pages → floating 3D wallet, coins, or card mockup
- Dashboard summary cards → subtle 3D depth / layered card effect
- Empty states → a 3D illustration (e.g. empty piggy bank, floating receipt)
- Onboarding / celebration moments → 3D confetti or trophy
- Chart headers or stat highlights → 3D icon accent

When 3D is a candidate, say:
> "I'd like to add a [describe the 3D element] to the [component]. It uses CSS 3D transforms / Three.js / a lightweight SVG-based 3D illustration. Should I include it?"

Wait for a yes/no before writing any 3D code. If the user says yes, implement it. If no, skip cleanly.

**Never silently add or silently skip 3D** — always surface the option and get a decision.

### Part 3 — Code
Deliver production-ready code. See guidelines below.

---

## Code Quality Rules

### No code dumps
Never output a wall of unstructured code. Always:
- Introduce each block with a one-line comment explaining its purpose (`/* --- Expense Card Component --- */`)
- Group CSS into logical sections: layout → typography → color → interactive states → responsive
- Split long templates into clearly labeled `{# --- Section: Header --- #}` Jinja2 comments
- If a component has more than ~80 lines of CSS, break it into named subsections

### No generic UI
Every component must feel like it belongs to **Spendly** specifically:
- Use the Spendly color palette and fonts — no gray Bootstrap defaults
- Refer to "expenses", "income", "your spending" — not generic "items" or "data"
- Stat cards should show Spendly-relevant metrics (Total Spent, Biggest Category, Monthly Budget)
- Empty states should reference money/expenses, not generic "no items found"
- CTAs should use Spendly voice: "Track an expense", "See your spending", not "Submit" or "Click here"
- Forms should use meaningful placeholders: "e.g. Grocery run — $45" not "Enter value"

---

## Code Guidelines

### HTML (Jinja2 templates)
- Extend `base.html`: `{% extends "base.html" %} {% block content %} ... {% endblock %}`
- Use semantic HTML5 elements (`<main>`, `<section>`, `<article>`, `<header>`, `<nav>`, etc.)
- BEM-style class names: `.expense-card`, `.expense-card__amount`, `.expense-card--positive`
- Jinja2 loops/conditionals where data is dynamic: `{% for expense in expenses %}`, `{% if current_user %}`
- Flash messages: `{% with messages = get_flashed_messages(with_categories=true) %}`
- Form actions point to Flask route names: `action="{{ url_for('add_expense') }}"`
- Include CSRF-safe forms (Flask-WTF pattern if applicable, otherwise standard `<form method="POST">`)

### CSS
- **Always use design tokens** from `:root` — never hardcode colors or font names
- Add new component styles at the bottom of `style.css` with a clear section comment
- Mobile-first: base styles → `@media (min-width: 768px)` for desktop enhancements
- Use CSS Grid and Flexbox; avoid floats
- Transitions: `transition: <property> 0.2s ease` for interactive elements
- No external CSS frameworks (no Bootstrap, Tailwind) — custom CSS only

### JavaScript (when needed)
- Vanilla JS only; no frameworks
- Use `DOMContentLoaded` wrapper
- Add to `static/js/main.js`
- Keep it minimal — prefer CSS for visual effects

### 3D Elements (when approved by user)
Three implementation tiers — choose the lightest one that achieves the effect:

**Tier 1 — CSS 3D transforms** (preferred, zero dependencies)
- Use `perspective`, `rotateX`, `rotateY`, `translateZ` for card depth and hover tilts
- Great for: stat cards with depth, floating elements, layered card stacks
```css
.card-3d {
  transform-style: preserve-3d;
  perspective: 800px;
  transition: transform 0.3s ease;
}
.card-3d:hover { transform: rotateY(6deg) rotateX(3deg); }
```

**Tier 2 — SVG-based 3D illustrations** (lightweight, no JS needed)
- Inline SVGs with isometric/perspective projection for wallet, coins, charts
- Great for: hero sections, empty states, onboarding

**Tier 3 — Three.js** (only for truly immersive hero moments)
- Load via CDN: `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
- Keep scenes simple: single floating object, minimal geometry, soft lighting
- Always include a `prefers-reduced-motion` fallback that hides the canvas
- Great for: landing page hero only

Always add `@media (prefers-reduced-motion: reduce)` fallback for any animation.

### Icons
- Use **Lucide Icons** via CDN: `https://unpkg.com/lucide@latest`
- Initialize with `lucide.createIcons()` in a `<script>` at bottom of template
- Icon usage: `<i data-lucide="wallet"></i>`, `<i data-lucide="trending-up"></i>`, etc.
- Good icon choices for finance: `wallet`, `trending-up`, `trending-down`, `dollar-sign`, `pie-chart`, `bar-chart-2`, `receipt`, `tag`, `calendar`, `user`, `settings`, `plus-circle`, `edit-2`, `trash-2`, `log-out`, `alert-circle`, `check-circle`

---

## Design Principles

1. **Clarity first** — the user's financial data should be the hero. No clutter.
2. **Consistent visual rhythm** — 8px base spacing unit, multiples of 8 for layout
3. **Readable typography** — DM Serif Display for headings, DM Sans for body; clear hierarchy
4. **Meaningful color** — use `--accent` (green) for income/positive, `--accent-2` (amber) for expenses/warnings
5. **Responsive** — works on mobile (320px) through desktop (1200px+)
6. **Accessible** — proper labels, focus states, contrast ratios; 3D always has a flat fallback
7. **No boilerplate** — every element earns its place; no generic placeholder copy or layouts
8. **Spendly-specific voice** — UI copy, labels, and empty states should reference money and spending, not generic CRUD

---

## Handling Ambiguity

If the request is vague (e.g. "design a dashboard"), make reasonable assumptions based on:
- The routes in `app.py` (expenses: add, edit, delete; profile; landing)
- Typical expense tracker patterns (totals, category breakdown, recent transactions)

State your assumptions clearly in Part 1 before writing code, so the user can redirect if needed.

---

## Reference Files

- `references/design-system.md` — Full design tokens, color palette, font stack, spacing, existing component patterns. **Read this before writing code.**