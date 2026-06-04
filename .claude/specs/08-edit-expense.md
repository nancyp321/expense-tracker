# Spec: Edit Expense

## Overview
Step 8 implements the edit-expense flow, letting a logged-in user fix an existing record in the `expenses` table. A user clicks an edit link on the history page, lands on `/expenses/<id>/edit`, sees a pre-filled form, makes changes, and submits. The server validates the input, verifies that the expense belongs to the current user (ownership check), updates the row via a new `update_expense()` DB helper, and redirects to the history page with a success flash. This step converts the existing Step 8 placeholder route and is a direct complement to Step 7 (add expense) and the upcoming Step 9 (delete expense).

## Depends on
- Step 1 — database setup (`expenses` table must exist)
- Step 3 — login / sessions (route is logged-in only)
- Step 7 — add expense (establishes the expense form pattern and `ALLOWED_CATEGORIES` constant)

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the expense's current values — logged-in only
- `POST /expenses/<int:id>/edit` — validate input, verify ownership, update the row, redirect to `/profile/history` — logged-in only

## Database changes
No new tables or columns. Two new helper functions are added to `database/db.py`:

```python
def get_expense_by_id(expense_id):
    # SELECT * FROM expenses WHERE id = ?
    # Returns a dict or None

def update_expense(expense_id, amount, category, date, description):
    # UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=?
```

The `expenses` table already has all required columns.

## Templates
- **Create:** `templates/edit_expense.html` — form with pre-filled fields: amount (number), category (select with current category selected), date (date input pre-set to existing date), description (textarea, optional); submit button; extends `base.html`
- **Modify:** `templates/history.html` — add an "Edit" link next to each expense row pointing to `url_for("edit_expense", id=expense.id)`

## Files to change
- `app.py` — replace the Step 8 placeholder `edit_expense` route with GET + POST handlers; add ownership check; import `get_expense_by_id` and `update_expense` from `database.db`
- `database/db.py` — add `get_expense_by_id()` and `update_expense()` helpers
- `templates/history.html` — add Edit link per expense row

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not applicable here, but do not introduce plain-text storage)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Redirect unauthenticated users to `/login`
- **Ownership check:** if the fetched expense's `user_id` does not match `session["user_id"]`, return a 403 or redirect to history with a flash error — never let a user edit another user's expense
- If the expense `id` does not exist, return 404 (use `abort(404)`)
- Amount must be a positive number; reject zero or negative values with a flash error
- Category must be one of the `ALLOWED_CATEGORIES` constant values already defined in `app.py`
- Date must be a valid `YYYY-MM-DD` string; reuse `_parse_date()` already in `app.py`
- On validation error, re-render the edit form (do not redirect) so the user's input is visible
- After a successful update, flash a success message and redirect to `url_for("profile_history")`
- The edit form must pre-fill all fields with the expense's current values on GET

## Definition of done
- [ ] `GET /expenses/<id>/edit` returns 200 and a pre-filled form for the expense owner
- [ ] `GET /expenses/<id>/edit` redirects to `/login` for an unauthenticated user
- [ ] `GET /expenses/<id>/edit` returns 404 for a non-existent expense id
- [ ] `GET /expenses/<id>/edit` returns 403 (or redirects with flash error) when the expense belongs to a different user
- [ ] Submitting the form with valid data updates the row in `expenses` and redirects to `/profile/history`
- [ ] The updated values appear on the history page immediately after submission
- [ ] Submitting with a missing or zero/negative amount shows a flash error and re-renders the form
- [ ] Submitting with an invalid date shows a flash error and re-renders the form
- [ ] Submitting with an invalid category shows a flash error and re-renders the form
- [ ] The history page shows an "Edit" link for each expense that links to the correct edit URL
