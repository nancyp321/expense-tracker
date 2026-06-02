# Spec: Date Filter for Profile Page

## Overview
Step 6 adds date-range filtering to the expense history page (`/profile/history`).
Currently the history page fetches every expense for the logged-in user with no
way to narrow the list. This step introduces a `start_date` / `end_date` query-
string filter so users can view expenses within a specific period. The filter
form sits above the expense table; submitting it reloads the page with the chosen
dates in the URL, keeping all state in the query string (no sessions or hidden
fields). If no dates are supplied the page behaves exactly as before, showing
all expenses.

## Depends on
- Step 1: Database setup (`expenses` table with a `date` column exists)
- Step 3: Login / logout (`session["user_id"]` set on login)
- Step 5: Backend routes for profile page (`/profile/history` route and
  `get_user_expenses()` already exist)

## Routes
- `GET /profile/history` — modified to accept optional `start_date` and
  `end_date` query-string parameters — logged-in only

No new routes.

## Database changes
No new tables or columns. The existing `expenses.date` column (stored as
`TEXT` in `YYYY-MM-DD` format) supports ISO string comparison directly in SQL.

## Templates
- **Modify:** `templates/history.html`
  - Add a date-filter form above the expense table with two `<input type="date">`
    fields (`start_date`, `end_date`) and a Submit button.
  - Pre-populate both inputs with the values currently in the query string so
    the form reflects the active filter after a reload.
  - Display the active filter range as a short summary line beneath the form
    (e.g. "Showing expenses from 01 May 2026 to 31 May 2026") when a filter
    is applied; hide this line when no filter is active.
  - If the filtered result set is empty, show a friendly "No expenses found
    for this period." message in place of the table.
  - Add a "Clear filter" link that navigates to `/profile/history` (no query
    string) whenever a filter is active.

## Files to change
- `database/db.py` — extend `get_user_expenses(user_id)` to accept optional
  `start_date=None` and `end_date=None` keyword arguments; narrow the WHERE
  clause when either is provided
- `app.py` — read `start_date` and `end_date` from `request.args` in
  `profile_history()` and pass them to `get_user_expenses()`; pass the active
  filter values back to the template so the form can be pre-populated
- `templates/history.html` — add filter form, active-filter summary, empty-
  state message, and clear-filter link as described above

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Date values from query strings must be validated as `YYYY-MM-DD` before use;
  if either value is malformed, ignore both and show all expenses (no crash)
- If `start_date` is provided but `end_date` is not (or vice-versa), apply
  only the supplied bound (open-ended range)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Filter state must live entirely in the URL query string — do not store it in
  `session` or hidden form fields
- The expense list must remain ordered newest-first (date DESC, id DESC)

## Definition of done
- [ ] Visiting `/profile/history` with no query params shows all expenses,
      ordered newest-first — behaviour unchanged from Step 5
- [ ] Submitting the filter form with a valid date range reloads the page and
      shows only expenses whose `date` falls within that range (inclusive)
- [ ] Both date inputs are pre-populated with the active filter values after
      the form is submitted
- [ ] The active-filter summary line appears when a filter is applied and is
      absent when no filter is active
- [ ] Filtering to a range with no matching expenses shows the empty-state
      message instead of the table
- [ ] The "Clear filter" link appears when a filter is active and navigates
      back to the unfiltered history page
- [ ] Supplying only `start_date` returns all expenses on or after that date
- [ ] Supplying only `end_date` returns all expenses on or before that date
- [ ] Supplying a malformed date (e.g. `?start_date=abc`) shows all expenses
      without raising an error
- [ ] Unauthenticated access to `/profile/history` redirects to `/login`
