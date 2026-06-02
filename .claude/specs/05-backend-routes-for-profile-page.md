# Spec: Backend Routes For Profile Page

## Overview
Step 5 adds write-capable backend routes to the profile page. Step 4 delivered a read-only profile — users can see their name, email, member-since date, and expense summary, but there is no way to change anything. This step wires up two POST routes — one to update a user's name and email, one to change their password — and extends `profile.html` with the corresponding forms. After this step, the profile page is fully interactive and the authenticated section of Spendly is complete before expense CRUD begins in Step 6.

## Depends on
- Step 1: Database setup (`get_db()`, `users` table)
- Step 2: Registration (`create_user()`, `users` rows exist)
- Step 3: Login / logout / sessions (`session["user_id"]` populated on login)
- Step 4: Profile page design (`profile.html` template, `get_user_by_id()`, `get_expense_summary()` already in place)

## Routes
- `POST /profile/edit` — update the logged-in user's name and email — logged-in only
- `POST /profile/password` — change the logged-in user's password — logged-in only

Both routes redirect back to `GET /profile` on both success and validation failure (POST-Redirect-GET pattern). Flash messages communicate the outcome.

## Database changes
No new tables or columns. Two new functions are needed in `database/db.py`:

- `update_user_profile(user_id, name, email)` — executes `UPDATE users SET name = ?, email = ? WHERE id = ?`; raises `sqlite3.IntegrityError` if the email is already in use by another account
- `update_user_password(user_id, password_hash)` — executes `UPDATE users SET password_hash = ? WHERE id = ?`

`get_user_by_id` and `get_expense_summary` already exist from Step 4.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — append a "Account Settings" section below the existing CTA. It contains two sub-forms:
  1. **Edit Profile form** — fields `name` (pre-filled) and `email` (pre-filled), submits `POST /profile/edit`
  2. **Change Password form** — fields `current_password`, `new_password`, `confirm_password`, submits `POST /profile/password`
  Each form has its own submit button. Both forms use `method="POST"`. Flash messages are already rendered by `base.html` and will appear at the top of the page.

## Files to change
- `app.py` — add `profile_edit()` view for `POST /profile/edit` and `profile_password()` view for `POST /profile/password`; update import of db helpers to include `update_user_profile` and `update_user_password`
- `database/db.py` — add `update_user_profile(user_id, name, email)` and `update_user_password(user_id, password_hash)`
- `templates/profile.html` — add the Account Settings section with both forms

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — store the hash, never plaintext
- Verify the current password with `werkzeug.security.check_password_hash` before accepting a password change
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- Both POST routes must check `session.get("user_id")` first; if missing, redirect to `url_for("login")`
- Use the POST-Redirect-GET pattern: always redirect to `url_for("profile")` after handling the POST (whether success or error), and communicate outcomes via `flash()`
- On a successful profile update, refresh `session["user_name"]` to reflect the new name so the navbar stays current
- On a duplicate email error (`sqlite3.IntegrityError`), flash a user-friendly message — do not expose the raw exception
- Validate that name and email are non-empty before hitting the database
- For password change: validate that `new_password == confirm_password` before hashing; validate that `current_password` is correct before updating

## Definition of done
- [ ] `POST /profile/edit` with a new name updates `users.name` in the database
- [ ] `POST /profile/edit` with a new email updates `users.email` in the database
- [ ] After a successful name change, the profile page and navbar display the updated name
- [ ] `POST /profile/edit` with an email already used by another account flashes an error and does not change anything
- [ ] `POST /profile/edit` with empty name or email flashes a validation error and does not change anything
- [ ] `POST /profile/password` with the correct current password and matching new/confirm fields updates the password hash
- [ ] After a password change, the user can log out and log back in with the new password
- [ ] `POST /profile/password` with an incorrect current password flashes an error and does not update anything
- [ ] `POST /profile/password` where `new_password != confirm_password` flashes an error and does not update anything
- [ ] Both routes redirect unauthenticated requests to `/login`
- [ ] The Account Settings section is visible on the profile page and styled using only CSS variables
