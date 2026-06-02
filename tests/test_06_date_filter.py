"""
tests/test_06_date_filter.py

Step 06 — Date Filter for Profile Page
Covers both the database helper (get_user_expenses) and the
GET /profile/history route.

Fixture strategy
----------------
The `app` fixture points the app at a fresh in-memory SQLite database so no
real expense_tracker.db is touched.  `db_conn` gives raw access to that same
database inside a test so we can seed deterministic rows without going through
the HTTP layer.  `auth_client` performs register + login for a test user and
returns an already-authenticated test client.

Seeded expenses (user = "filteruser@test.com")
-----------------------------------------------
  id  date        amount   category
  --  ----------  -------  -----------
  1   2026-04-15  100.00   Food         ← before May
  2   2026-05-01  200.00   Transport    ← start of May
  3   2026-05-15  300.00   Bills        ← mid May
  4   2026-05-31  400.00   Health       ← end of May
  5   2026-06-10  500.00   Shopping     ← after May

A second user's expense is also seeded to verify cross-user isolation.
"""

import sqlite3
import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import init_db, get_user_expenses


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """Flask app wired to a temp-file SQLite DB (not in-memory so that both
    the app connection and our fixture connection share the same file)."""
    db_file = tmp_path / "test_spendly.db"

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })

    # Monkey-patch DB_PATH so every get_db() call inside the app uses our file
    import database.db as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = str(db_file)

    with flask_app.app_context():
        init_db()

    yield flask_app

    # Restore original path after test
    db_module.DB_PATH = original_path


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_conn(app):
    """Direct SQLite connection to the test database for seeding."""
    import database.db as db_module
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


@pytest.fixture
def seeded_user(db_conn):
    """Insert the primary test user; return their id."""
    cursor = db_conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Filter User", "filteruser@test.com", generate_password_hash("password123")),
    )
    db_conn.commit()
    return cursor.lastrowid


@pytest.fixture
def seeded_expenses(db_conn, seeded_user):
    """Insert a known set of expenses for seeded_user plus one for a
    different user.  Returns (user_id, list_of_expense_dicts)."""
    user_id = seeded_user

    # A second user — used to verify cross-user isolation
    cursor2 = db_conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@test.com", generate_password_hash("password456")),
    )
    other_user_id = cursor2.lastrowid

    rows = [
        (user_id,       100.0, "Food",      "2026-04-15", "Before May"),
        (user_id,       200.0, "Transport", "2026-05-01", "Start of May"),
        (user_id,       300.0, "Bills",     "2026-05-15", "Mid May"),
        (user_id,       400.0, "Health",    "2026-05-31", "End of May"),
        (user_id,       500.0, "Shopping",  "2026-06-10", "After May"),
        (other_user_id, 999.0, "Other",     "2026-05-10", "Other user expense"),
    ]
    db_conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    db_conn.commit()
    return user_id


@pytest.fixture
def auth_client(client, seeded_expenses):
    """Logged-in test client for filteruser@test.com."""
    client.post(
        "/login",
        data={"email": "filteruser@test.com", "password": "password123"},
        follow_redirects=False,
    )
    return client


# ---------------------------------------------------------------------------
# Unit tests — get_user_expenses (database layer)
# ---------------------------------------------------------------------------

class TestGetUserExpensesUnit:
    """Direct unit tests for the get_user_expenses() helper."""

    def test_no_filter_returns_all_user_expenses(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id)
        assert len(results) == 5, "Expected all 5 expenses for the test user"

    def test_no_filter_excludes_other_user_expenses(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id)
        amounts = [r["amount"] for r in results]
        assert 999.0 not in amounts, "Other user's expense must not appear"

    def test_no_filter_ordered_newest_first(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id)
        dates = [r["date"] for r in results]
        assert dates == sorted(dates, reverse=True), \
            "Expenses must be returned newest-first"

    def test_both_dates_returns_only_range(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id, start_date="2026-05-01", end_date="2026-05-31")
        dates = [r["date"] for r in results]
        assert "2026-04-15" not in dates, "Expense before range must be excluded"
        assert "2026-06-10" not in dates, "Expense after range must be excluded"
        assert "2026-05-01" in dates, "Inclusive start date must be included"
        assert "2026-05-15" in dates, "Mid-range expense must be included"
        assert "2026-05-31" in dates, "Inclusive end date must be included"
        assert len(results) == 3, "Exactly 3 expenses fall in May 2026"

    def test_start_date_only_returns_on_or_after(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id, start_date="2026-05-15")
        dates = [r["date"] for r in results]
        assert "2026-04-15" not in dates, "Pre-start expense must be excluded"
        assert "2026-05-01" not in dates, "Expense before start_date must be excluded"
        assert "2026-05-15" in dates, "Expense on start_date must be included"
        assert "2026-05-31" in dates, "Expense after start_date must be included"
        assert "2026-06-10" in dates, "Expense well after start_date must be included"
        assert len(results) == 3

    def test_end_date_only_returns_on_or_before(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id, end_date="2026-05-15")
        dates = [r["date"] for r in results]
        assert "2026-06-10" not in dates, "Post-end expense must be excluded"
        assert "2026-05-31" not in dates, "Expense after end_date must be excluded"
        assert "2026-05-15" in dates, "Expense on end_date must be included"
        assert "2026-05-01" in dates, "Expense before end_date must be included"
        assert "2026-04-15" in dates, "Expense well before end_date must be included"
        assert len(results) == 3

    def test_empty_range_returns_no_results(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(
                user_id, start_date="2026-01-01", end_date="2026-01-31"
            )
        assert results == [], "No expenses in January 2026 — expect empty list"

    def test_none_start_date_does_not_filter(self, app, seeded_expenses):
        """Passing start_date=None must behave identically to omitting it."""
        user_id = seeded_expenses
        with app.app_context():
            all_results = get_user_expenses(user_id)
            none_results = get_user_expenses(user_id, start_date=None)
        assert len(all_results) == len(none_results), \
            "start_date=None must return all expenses"

    def test_none_end_date_does_not_filter(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            all_results = get_user_expenses(user_id)
            none_results = get_user_expenses(user_id, end_date=None)
        assert len(all_results) == len(none_results), \
            "end_date=None must return all expenses"

    def test_returns_list_of_dicts(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id)
        assert isinstance(results, list), "Return value must be a list"
        assert isinstance(results[0], dict), "Each element must be a dict"

    def test_returned_dict_has_expected_keys(self, app, seeded_expenses):
        user_id = seeded_expenses
        with app.app_context():
            results = get_user_expenses(user_id)
        required_keys = {"id", "amount", "category", "date", "description"}
        assert required_keys.issubset(results[0].keys()), \
            f"Row is missing keys. Got: {set(results[0].keys())}"


# ---------------------------------------------------------------------------
# Route tests — GET /profile/history
# ---------------------------------------------------------------------------

class TestProfileHistoryRoute:
    """Integration tests for the /profile/history endpoint."""

    # -- Auth guard ----------------------------------------------------------

    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/profile/history")
        assert response.status_code == 302, \
            "Unauthenticated request must be redirected"
        assert "/login" in response.headers["Location"], \
            "Redirect must point to /login"

    def test_unauthenticated_does_not_serve_page(self, client):
        response = client.get("/profile/history", follow_redirects=True)
        assert b"Login" in response.data or b"login" in response.data, \
            "Following the redirect must land on the login page"

    # -- No filter (baseline) ------------------------------------------------

    def test_no_filter_returns_200(self, auth_client):
        response = auth_client.get("/profile/history")
        assert response.status_code == 200

    def test_no_filter_shows_all_expenses(self, auth_client):
        response = auth_client.get("/profile/history")
        data = response.data
        # All five description strings seeded for filteruser must appear
        assert b"Before May" in data, "April expense must appear with no filter"
        assert b"Start of May" in data, "May 1 expense must appear"
        assert b"Mid May" in data, "May 15 expense must appear"
        assert b"End of May" in data, "May 31 expense must appear"
        assert b"After May" in data, "June expense must appear"

    def test_no_filter_excludes_other_user_expenses(self, auth_client):
        response = auth_client.get("/profile/history")
        assert b"Other user expense" not in response.data, \
            "Another user's expense must never appear in the response"

    def test_no_filter_no_clear_filter_link(self, auth_client):
        response = auth_client.get("/profile/history")
        assert b"Clear filter" not in response.data and b"clear filter" not in response.data, \
            "'Clear filter' must not appear when no filter is active"

    # -- Valid date range ----------------------------------------------------

    def test_valid_range_returns_200(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        assert response.status_code == 200

    def test_valid_range_shows_matching_expenses(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        data = response.data
        assert b"Start of May" in data, "May 1 expense must appear in May filter"
        assert b"Mid May" in data, "May 15 expense must appear in May filter"
        assert b"End of May" in data, "May 31 expense must appear in May filter"

    def test_valid_range_excludes_out_of_range_expenses(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        data = response.data
        assert b"Before May" not in data, \
            "April expense must be excluded from May filter"
        assert b"After May" not in data, \
            "June expense must be excluded from May filter"

    # -- start_date only (open-ended upper bound) ----------------------------

    def test_start_date_only_returns_200(self, auth_client):
        response = auth_client.get("/profile/history?start_date=2026-05-15")
        assert response.status_code == 200

    def test_start_date_only_includes_on_and_after(self, auth_client):
        response = auth_client.get("/profile/history?start_date=2026-05-15")
        data = response.data
        assert b"Mid May" in data, "Expense on start_date must appear"
        assert b"End of May" in data, "Expense after start_date must appear"
        assert b"After May" in data, "Expense well after start_date must appear"

    def test_start_date_only_excludes_before(self, auth_client):
        response = auth_client.get("/profile/history?start_date=2026-05-15")
        data = response.data
        assert b"Before May" not in data, \
            "April expense must be excluded when start_date=2026-05-15"
        assert b"Start of May" not in data, \
            "May 1 expense must be excluded when start_date=2026-05-15"

    # -- end_date only (open-ended lower bound) ------------------------------

    def test_end_date_only_returns_200(self, auth_client):
        response = auth_client.get("/profile/history?end_date=2026-05-15")
        assert response.status_code == 200

    def test_end_date_only_includes_on_and_before(self, auth_client):
        response = auth_client.get("/profile/history?end_date=2026-05-15")
        data = response.data
        assert b"Before May" in data, "April expense must appear"
        assert b"Start of May" in data, "May 1 expense must appear"
        assert b"Mid May" in data, "Expense on end_date must appear"

    def test_end_date_only_excludes_after(self, auth_client):
        response = auth_client.get("/profile/history?end_date=2026-05-15")
        data = response.data
        assert b"End of May" not in data, \
            "May 31 expense must be excluded when end_date=2026-05-15"
        assert b"After May" not in data, \
            "June expense must be excluded when end_date=2026-05-15"

    # -- Empty result set ----------------------------------------------------

    def test_no_matches_returns_200(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-01-01&end_date=2026-01-31"
        )
        assert response.status_code == 200

    def test_no_matches_shows_empty_state_message(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-01-01&end_date=2026-01-31"
        )
        data = response.data
        assert b"No expenses found" in data, \
            "Empty-state message must appear when no expenses match the filter"

    def test_no_matches_does_not_show_expenses(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-01-01&end_date=2026-01-31"
        )
        data = response.data
        # None of the seeded descriptions should be present
        assert b"Before May" not in data
        assert b"Start of May" not in data

    # -- Malformed dates -----------------------------------------------------

    @pytest.mark.parametrize("bad_date", [
        "abc",
        "2026/05/01",
        "01-05-2026",
        "not-a-date",
        "99999",
        "2026-13-01",   # invalid month
        "2026-05-32",   # invalid day
        "",
        "null",
    ])
    def test_malformed_start_date_shows_all_expenses(self, auth_client, bad_date):
        response = auth_client.get(f"/profile/history?start_date={bad_date}")
        assert response.status_code == 200, \
            f"Malformed start_date={bad_date!r} must not crash the route"
        data = response.data
        assert b"Before May" in data, \
            f"All expenses must show when start_date={bad_date!r} is malformed"
        assert b"After May" in data, \
            f"All expenses must show when start_date={bad_date!r} is malformed"

    @pytest.mark.parametrize("bad_date", [
        "abc",
        "2026/05/31",
        "31-05-2026",
        "not-a-date",
    ])
    def test_malformed_end_date_shows_all_expenses(self, auth_client, bad_date):
        response = auth_client.get(f"/profile/history?end_date={bad_date}")
        assert response.status_code == 200, \
            f"Malformed end_date={bad_date!r} must not crash the route"
        data = response.data
        assert b"Before May" in data
        assert b"After May" in data

    def test_both_dates_malformed_shows_all_expenses(self, auth_client):
        """When both bounds are malformed the page must still show all expenses."""
        response = auth_client.get(
            "/profile/history?start_date=bad&end_date=also-bad"
        )
        assert response.status_code == 200
        data = response.data
        assert b"Before May" in data
        assert b"After May" in data

    def test_one_valid_one_malformed_shows_all_expenses(self, auth_client):
        """Per spec: if either value is malformed, ignore both and show all."""
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=not-a-date"
        )
        assert response.status_code == 200
        data = response.data
        # All expenses must appear — the valid start_date must also be ignored
        assert b"Before May" in data, \
            "April expense must appear — both bounds must be ignored when one is malformed"
        assert b"After May" in data

    # -- Pre-populated inputs (active filter reflected in form) --------------

    def test_active_filter_prepopulates_start_date(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        assert b"2026-05-01" in response.data, \
            "start_date value must appear in the response (pre-populated input)"

    def test_active_filter_prepopulates_end_date(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        assert b"2026-05-31" in response.data, \
            "end_date value must appear in the response (pre-populated input)"

    def test_start_date_only_prepopulated(self, auth_client):
        response = auth_client.get("/profile/history?start_date=2026-05-15")
        assert b"2026-05-15" in response.data, \
            "start_date value must appear in response when only start_date is supplied"

    def test_end_date_only_prepopulated(self, auth_client):
        response = auth_client.get("/profile/history?end_date=2026-05-15")
        assert b"2026-05-15" in response.data, \
            "end_date value must appear in response when only end_date is supplied"

    # -- Clear filter link ---------------------------------------------------

    def test_active_filter_shows_clear_filter_link(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        data = response.data
        assert b"Clear filter" in data or b"clear filter" in data or b"Clear Filter" in data, \
            "'Clear filter' link must be present when a filter is active"

    def test_clear_filter_link_points_to_unfiltered_history(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        # The unfiltered history URL must appear as a link target
        assert b"/profile/history" in response.data, \
            "Clear filter link must href to /profile/history (no query string)"

    def test_start_date_only_shows_clear_filter(self, auth_client):
        response = auth_client.get("/profile/history?start_date=2026-05-01")
        data = response.data
        assert b"Clear filter" in data or b"clear filter" in data or b"Clear Filter" in data, \
            "'Clear filter' must appear when start_date filter is active"

    def test_end_date_only_shows_clear_filter(self, auth_client):
        response = auth_client.get("/profile/history?end_date=2026-05-31")
        data = response.data
        assert b"Clear filter" in data or b"clear filter" in data or b"Clear Filter" in data, \
            "'Clear filter' must appear when end_date filter is active"

    # -- Ordering ------------------------------------------------------------

    def test_no_filter_newest_first_ordering(self, auth_client):
        """Expense dates in the rendered HTML must appear in descending order."""
        response = auth_client.get("/profile/history")
        data = response.data.decode("utf-8")
        pos_june  = data.find("2026-06-10")
        pos_may31 = data.find("2026-05-31")
        pos_may15 = data.find("2026-05-15")
        pos_may1  = data.find("2026-05-01")
        pos_april = data.find("2026-04-15")

        assert pos_june < pos_may31, "June expense must appear before May 31"
        assert pos_may31 < pos_may15, "May 31 must appear before May 15"
        assert pos_may15 < pos_may1, "May 15 must appear before May 1"
        assert pos_may1 < pos_april, "May 1 must appear before April"

    def test_filtered_results_still_ordered_newest_first(self, auth_client):
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        data = response.data.decode("utf-8")
        pos_may31 = data.find("2026-05-31")
        pos_may15 = data.find("2026-05-15")
        pos_may1  = data.find("2026-05-01")

        assert pos_may31 < pos_may15, "May 31 must appear before May 15 in filtered view"
        assert pos_may15 < pos_may1,  "May 15 must appear before May 1 in filtered view"

    # -- Template extends base.html ------------------------------------------

    def test_response_contains_html_structure(self, auth_client):
        """Page must be a complete HTML document rendered from a template."""
        response = auth_client.get("/profile/history")
        data = response.data
        assert b"<!DOCTYPE html>" in data or b"<html" in data, \
            "Response must be a full HTML page, not a plain-text stub"

    # -- Active filter summary line ------------------------------------------

    def test_active_filter_shows_summary_line(self, auth_client):
        """When a filter is applied a summary / 'Showing expenses from ...' line
        must appear.  We check for key date fragments inside the summary area."""
        response = auth_client.get(
            "/profile/history?start_date=2026-05-01&end_date=2026-05-31"
        )
        data = response.data
        # The summary line must mention both bounds in some form
        assert b"2026-05-01" in data and b"2026-05-31" in data, \
            "Active filter summary must show both the start and end date values"

    def test_no_filter_no_summary_line(self, auth_client):
        """When no filter is active the 'Showing expenses from … to …'
        summary line must not appear."""
        response = auth_client.get("/profile/history")
        data = response.data
        # No date literals from our seed should appear as filter summaries.
        # We confirm by checking that no filter-summary-specific phrasing exists.
        assert b"Showing expenses from" not in data, \
            "Filter summary must not appear when no filter is active"
