# Spec: Login and Logout

## Overview
Step 3 adds session-based authentication to Spendly. A registered user submits their email and password; the server looks up the user by email, verifies the password with werkzeug, and stores the user's `id` and `name` in `flask.session`. Logging out clears the session and redirects to the landing page. This is the first step that uses Flask sessions and introduces the concept of "logged-in vs. public" access — a pattern every subsequent authenticated route depends on.

## Depends on
- Step 1: Database setup (`get_db()`, `users` table)
- Step 2: Registration (`create_user()`, `users` rows exist with hashed passwords)

## Routes
- `GET  /login`  — render the login form — public (already exists as stub, needs POST added)
- `POST /login`  — validate credentials, set session, redirect to `/profile` — public
- `GET  /logout` — clear session, redirect to `/` — logged-in (currently returns placeholder string)

## Database changes
No new tables or columns. One new query function is needed in `database/db.py`:
- `get_user_by_email(email)` — SELECT a single row from `users` WHERE `email = ?`; returns a `sqlite3.Row` or `None`

## Templates
- **Create:**
  - `templates/login.html` — login form (it already exists as a rendered template per `app.py`, so verify content; add the POST form with `email` and `password` fields and flash message display if not already present)
- **Modify:**
  - `templates/base.html` — update the navbar "Login" link to show a "Logout" link when `session.user_id` is set, and hide it when not logged in

## Files to change
- `app.py` — convert `login()` to handle both GET and POST; implement `logout()` (remove placeholder string); import `session` from flask; import `check_password_hash` from werkzeug; import `get_user_by_email` from `database.db`
- `database/db.py` — add `get_user_by_email(email)` function
- `templates/login.html` — ensure form has `method="POST"`, fields `email` and `password`, and flash message display
- `templates/base.html` — conditional navbar links based on session state

## Files to create
None.

## New dependencies
No new dependencies. `flask` and `werkzeug` are already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` and `user_name` in `flask.session` — never store the password hash in the session
- On successful login: set `session["user_id"]` and `session["user_name"]`, then redirect to `url_for("profile")`
- On failed login (wrong email or wrong password): show the same generic error message for both cases — do not reveal which field was wrong (security best practice)
- On logout: call `session.clear()`, then redirect to `url_for("landing")`
- Flash messages must be visible — the `base.html` flash block from Step 2 already handles this
- `app.secret_key` is already set in `app.py` from Step 2 — do not change it

## Definition of done
- [ ] `GET /login` renders a form with `email` and `password` fields
- [ ] Submitting valid credentials sets the session and redirects to `/profile`
- [ ] Submitting a non-existent email shows a generic "Invalid email or password" error (no 500)
- [ ] Submitting the correct email with the wrong password shows the same generic error
- [ ] After login, `session["user_id"]` contains the correct integer user id
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout, `session.get("user_id")` is `None`
- [ ] The navbar shows a "Logout" link when logged in and a "Login" link when logged out
- [ ] Password hash is never exposed — the session and any template variables never contain `password_hash`
