# Spec: Registration

## Overview
Step 2 adds the user registration flow to Spendly. A visitor fills in their name, email, and password; the server validates the input, hashes the password with werkzeug, inserts a new row into the `users` table, and redirects to the login page. This is the first route that writes to the database and introduces form handling, flash messages, and Flask sessions (via `secret_key`) — all patterns that every subsequent authenticated feature builds on.

## Depends on
- Step 1: Database setup (`database/db.py` with `get_db()`, `init_db()`, `users` table)

## Routes
- `GET  /register` — render the registration form — public (already exists, no change needed)
- `POST /register` — validate form data, insert user, redirect to `/login` — public

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already exists from Step 1.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — add an HTML form (`method="POST"`) with fields: `name`, `email`, `password`, `confirm_password`; display flashed error/success messages
  - `templates/base.html` — add a flash messages block (renders flashed messages from any route) so error/success feedback works site-wide

## Files to change
- `app.py` — add `secret_key`; import `request`, `redirect`, `url_for`, `flash`; convert `register()` to handle both GET and POST; add a `create_user()` helper call or inline the INSERT
- `templates/register.html` — add form and flash message display
- `templates/base.html` — add flash messages block
- `database/db.py` — add `create_user(name, email, password_hash)` function that executes the INSERT and returns the new row id

## Files to create
None.

## New dependencies
No new dependencies. `flask` and `werkzeug` are already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` before inserting
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- `app.secret_key` must be set for flash messages and sessions to work; use a hard-coded dev string for now (e.g. `"dev-secret-key"`)
- Duplicate email must be caught and surfaced as a flashed error message, not an unhandled 500
- On success: flash a success message and redirect to `url_for("login")`
- On validation failure: re-render `register.html` with the flashed error (do not redirect)
- Validate that `password == confirm_password` before touching the database
- All form fields are required; show a clear message if any are blank

## Definition of done
- [ ] `GET /register` renders a form with name, email, password, and confirm-password fields
- [ ] Submitting the form with valid data inserts a new row in `users` with a hashed password (not plaintext)
- [ ] After successful registration the browser is redirected to `/login`
- [ ] Submitting with a duplicate email shows an error message on the page (no 500 error)
- [ ] Submitting with mismatched passwords shows an error message on the page
- [ ] Submitting with any blank field shows an error message on the page
- [ ] Flash messages are visible in the browser on both success and error paths
- [ ] Plaintext password is never stored — `SELECT password_hash FROM users` shows a werkzeug hash string
