# Spec: Add Expense

## Overview
Step 7 implements the add-expense flow — the first route that lets a logged-in user write new records to the `expenses` table. A user visits `/expenses/add`, fills in amount, category, date, and an optional description, and submits the form. The server validates the input, inserts the row via a new `add_expense()` DB helper, and redirects to the history page with a success flash. This converts the existing Step 7 placeholder route and is the foundation for the edit and delete steps that follow.

## Depends on
- Step 1 — database setup (`expenses` table must exist)
- Step 3 — login / sessions (route is logged-in only)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, redirect to `/profile/history` — logged-in only

## Database changes
No new tables or columns. A new helper function is added to `database/db.py`:

```python
def add_expense(user_id, amount, category, date, description):
    # INSERT INTO expenses (user_id, amount, category, date, description)
```

The `expenses` table already has all required columns.

## Templates
- **Create:** `templates/add_expense.html` — form with fields: amount (number), category (select), date (date input, defaults to today), description (textarea, optional); submit button; extends `base.html`
- **Modify:** none

## Files to change
- `app.py` — replace the Step 7 placeholder `add_expense` route with GET + POST handlers; import `add_expense` from `database.db`
- `database/db.py` — add `add_expense()` helper

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not applicable here, but do not introduce plain-text storage)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Redirect unauthenticated users to `/login`
- Amount must be a positive number; reject zero or negative values with a flash error
- Category must be one of the fixed allowed values: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Date must be a valid `YYYY-MM-DD` string; reuse `_parse_date()` already in `app.py`
- On validation error, re-render the form (do not redirect) so the user's input is preserved
- After successful insert, flash a success message and redirect to `url_for("profile_history")`

## Definition of done
- [ ] `GET /expenses/add` returns 200 for a logged-in user and renders a form
- [ ] `GET /expenses/add` redirects to `/login` for an unauthenticated user
- [ ] Submitting the form with valid data inserts a row into `expenses` and redirects to `/profile/history`
- [ ] The new expense appears on the history page immediately after submission
- [ ] Submitting with a missing or zero amount shows a flash error and re-renders the form
- [ ] Submitting with an invalid date shows a flash error and re-renders the form
- [ ] Submitting with an invalid category shows a flash error and re-renders the form
- [ ] The category select contains exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- [ ] The date field defaults to today's date when the form first loads
