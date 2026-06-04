# Spec: Delete Expense

## Overview
Step 9 lets a logged-in user permanently remove an expense record from the `expenses` table. A user clicks a Delete button on the history page, a browser confirmation dialog asks them to confirm, and on confirmation a POST request is sent to `/expenses/<id>/delete`. The server verifies ownership, deletes the row via a new `delete_expense()` DB helper, then redirects to the history page with a success flash. This converts the existing Step 9 GET placeholder route into a proper POST handler and is a direct complement to Step 8 (edit expense).

## Depends on
- Step 1 — database setup (`expenses` table must exist)
- Step 3 — login / sessions (route is logged-in only)
- Step 6 — history page (the Delete button lives there)
- Step 8 — edit expense (establishes the ownership-check and 404/403 pattern)

## Routes
- `POST /expenses/<int:id>/delete` — verify ownership, delete the row, redirect to `/profile/history` — logged-in only

> The existing placeholder uses GET. Change it to POST-only to prevent accidental deletion via URL navigation.

## Database changes
No new tables or columns. One new helper function added to `database/db.py`:

```python
def delete_expense(expense_id):
    # DELETE FROM expenses WHERE id = ?
```

The `expenses` table already has all required columns.

## Templates
- **Create:** none
- **Modify:** `templates/history.html` — add a Delete `<form method="post">` button next to each expense row, pointing to `url_for("delete_expense", id=expense.id)`; add a `onclick="return confirm('Delete this expense?')"` on the submit button for a lightweight browser confirmation

## Files to change
- `app.py` — replace the Step 9 placeholder `delete_expense` route with a POST-only handler; add `@login_required`-style guard, 404 on missing expense, 403 on ownership mismatch; import `delete_expense` from `database.db`
- `database/db.py` — add `delete_expense()` helper using a parameterised DELETE query
- `templates/history.html` — add Delete form/button per expense row

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not applicable here, but do not introduce plain-text storage)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The route must only accept POST; a GET request to `/expenses/<id>/delete` should return 405
- Redirect unauthenticated users to `/login`
- **Ownership check:** if the fetched expense's `user_id` does not match `session["user_id"]`, return 403 — never let a user delete another user's expense
- If the expense `id` does not exist, return 404 (use `abort(404)`)
- After a successful delete, flash a success message and redirect to `url_for("profile_history")`
- Use `get_expense_by_id()` (already in `database/db.py`) to fetch before deleting — do not query inline in the route
- The Delete button in `history.html` should use a `<form>` with `method="post"` and include an `onclick` confirmation; do not rely on a separate confirmation page

## Definition of done
- [ ] `POST /expenses/<id>/delete` deletes the row and redirects to `/profile/history` with a success flash for the expense owner
- [ ] The deleted expense no longer appears on the history page after deletion
- [ ] `POST /expenses/<id>/delete` redirects to `/login` for an unauthenticated user
- [ ] `POST /expenses/<id>/delete` returns 404 for a non-existent expense id
- [ ] `POST /expenses/<id>/delete` returns 403 when the expense belongs to a different user
- [ ] `GET /expenses/<id>/delete` returns 405 (method not allowed)
- [ ] The history page shows a Delete button for each expense
- [ ] Clicking Delete triggers a browser confirmation dialog before submitting
