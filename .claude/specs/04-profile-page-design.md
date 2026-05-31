# Spec: Profile Page Design

## Overview
Step 4 implements the user profile page — the first authenticated, data-rich page in Spendly. After logging in, a user lands on `/profile` to see their account details (name, email, member since) alongside a personal expense summary (total spend, number of expenses, and a per-category breakdown). This step converts the placeholder `/profile` route in `app.py` into a fully working view, adds a `get_user_by_id()` and `get_expense_summary()` helper to `database/db.py`, and creates the `profile.html` template styled with the existing Spendly design system.

## Depends on
- Step 1: Database setup (`get_db()`, `users` and `expenses` tables)
- Step 2: Registration (`users` rows exist)
- Step 3: Login / logout / sessions (`session["user_id"]` is set on login)

## Routes
- `GET /profile` — render the profile page for the logged-in user — logged-in only (redirect to `/login` if no session)

## Database changes
No new tables or columns. Two new query functions are needed in `database/db.py`:
- `get_user_by_id(user_id)` — `SELECT * FROM users WHERE id = ?`; returns a `sqlite3.Row` or `None`
- `get_expense_summary(user_id)` — returns a dict with:
  - `total` — sum of all expense amounts for the user (float, 0.0 if none)
  - `count` — total number of expense rows for the user (int)
  - `by_category` — list of `(category, subtotal)` tuples ordered by subtotal descending

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; displays:
  - User info card: name, email, member-since date (formatted as "May 2026")
  - Expense summary card: total spend (formatted with ₹ symbol), number of expenses
  - Category breakdown table or list: category name + subtotal, ordered highest first
  - An "Add Expense" call-to-action button linking to `/expenses/add`
- **Modify:** none

## Files to change
- `app.py` — implement the `profile()` view: check session, call `get_user_by_id` and `get_expense_summary`, pass data to template; import new db helpers
- `database/db.py` — add `get_user_by_id(user_id)` and `get_expense_summary(user_id)`

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug (no change needed here; passwords are never rendered)
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- If `session.get("user_id")` is not set, redirect to `url_for("login")` immediately — do not render anything
- If `get_user_by_id` returns `None` (user deleted mid-session), clear the session and redirect to `/login`
- Format currency as `₹{amount:,.2f}` in the template using a Jinja2 filter or inline expression
- Format `created_at` date for display — parse the ISO string and render as "Month YYYY" (e.g. "May 2026")
- `get_expense_summary` must return safe defaults (`total=0.0`, `count=0`, `by_category=[]`) when the user has no expenses
- The "Add Expense" button links to `/expenses/add` (placeholder route — button is present but page is not yet implemented)

## Definition of done
- [ ] Visiting `/profile` when not logged in redirects to `/login`
- [ ] Visiting `/profile` when logged in renders the profile page without errors
- [ ] The page displays the logged-in user's name and email
- [ ] The page displays the member-since date in a human-readable format
- [ ] The page displays the correct total spend amount
- [ ] The page displays the correct number of expenses
- [ ] The category breakdown lists every category with its subtotal, ordered highest first
- [ ] A user with zero expenses sees 0.0 total and an empty category list (no crash)
- [ ] The "Add Expense" button is present and links to `/expenses/add`
- [ ] The page is styled using only CSS variables — no hardcoded colour values
