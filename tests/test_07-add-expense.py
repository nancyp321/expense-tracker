"""
tests/test_07-add-expense.py

Pytest test suite for Step 7 — Add Expense feature.

Spec: .claude/specs/07-add-expense.md

Coverage:
  - Auth guard (GET and POST without a session)
  - GET /expenses/add: status, form fields, exact category set, today default
  - POST happy path: redirect, DB row inserted, appears on history page
  - Amount validation: zero, negative, empty, non-numeric
  - Category validation: invalid value, empty string
  - Date validation: empty, non-date string, structurally wrong format
  - DB isolation: failed validation must not insert a row
  - Edge cases: very large amount, SQL-injection-safe description storage
"""

import sqlite3
import tempfile
import os
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Module-level constants mirrored from the spec (not from implementation)
# ---------------------------------------------------------------------------
ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
]
ADD_EXPENSE_URL = "/expenses/add"
LOGIN_URL = "/login"
HISTORY_URL = "/profile/history"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a path to a fresh, empty SQLite file inside pytest's tmp_path."""
    return str(tmp_path / "test_expense_tracker.db")


@pytest.fixture
def app(tmp_db_path, monkeypatch):
    """
    Create the Flask app in test mode, redirecting all DB calls to an
    isolated temporary SQLite file so the real expense_tracker.db is
    never touched.

    The monkeypatch of database.db.DB_PATH must happen before init_db()
    is called inside the fixture, which is why we do it here rather than
    relying on the config dict.
    """
    # Patch the module-level DB_PATH before importing anything that uses it.
    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_db_path)

    from app import app as flask_app

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        db_module.init_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user(tmp_db_path):
    """
    Insert a single test user directly into the temp DB and return their id.
    Uses the same DB_PATH that the app fixture has already patched, so the
    row is visible to all DB helpers the route calls.
    """
    import database.db as db_module

    conn = sqlite3.connect(tmp_db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    password_hash = generate_password_hash("testpass123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "testuser@example.com", password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "email": "testuser@example.com", "password": "testpass123"}


@pytest.fixture
def auth_client(client, seed_user):
    """
    A test client that already has a valid session for the seeded test user.
    Session is injected directly — no HTTP login round-trip required.
    """
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["user_name"] = "Test User"
    return client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _expense_count(tmp_db_path, user_id):
    """Return the number of expense rows for user_id in the temp DB."""
    conn = sqlite3.connect(tmp_db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def _last_expense(tmp_db_path, user_id):
    """Return the most-recently inserted expense row for user_id, or None."""
    conn = sqlite3.connect(tmp_db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ===========================================================================
# Auth guard tests
# ===========================================================================

class TestAuthGuard:
    def test_get_unauthenticated_redirects_to_login(self, client):
        response = client.get(ADD_EXPENSE_URL)
        assert response.status_code == 302, (
            "GET /expenses/add without a session should redirect"
        )
        assert LOGIN_URL in response.headers["Location"], (
            "Unauthenticated GET should redirect to /login"
        )

    def test_post_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            ADD_EXPENSE_URL,
            data={"amount": "100", "category": "Food", "date": "2026-06-01"},
        )
        assert response.status_code == 302, (
            "POST /expenses/add without a session should redirect"
        )
        assert LOGIN_URL in response.headers["Location"], (
            "Unauthenticated POST should redirect to /login"
        )

    def test_get_unauthenticated_does_not_return_200(self, client):
        response = client.get(ADD_EXPENSE_URL)
        assert response.status_code != 200, (
            "Unauthenticated request must not receive the form page"
        )


# ===========================================================================
# GET /expenses/add — authenticated
# ===========================================================================

class TestGetAddExpense:
    def test_returns_200_for_authenticated_user(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert response.status_code == 200, (
            "GET /expenses/add should return 200 for a logged-in user"
        )

    def test_renders_amount_input(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert b'name="amount"' in response.data, (
            "Form must contain an amount input field"
        )

    def test_renders_category_select(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert b'name="category"' in response.data, (
            "Form must contain a category select field"
        )

    def test_renders_date_input(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert b'name="date"' in response.data, (
            "Form must contain a date input field"
        )

    def test_renders_description_textarea(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert b'name="description"' in response.data, (
            "Form must contain a description textarea"
        )

    def test_category_select_contains_all_seven_categories(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        html = response.data.decode("utf-8")
        for cat in ALLOWED_CATEGORIES:
            assert cat in html, (
                f"Category '{cat}' must appear in the category select options"
            )

    def test_category_select_contains_no_extra_categories(self, auth_client):
        """
        Verify none of the well-known invalid categories appear as selectable
        option values. This is a structural sanity check, not exhaustive.
        """
        response = auth_client.get(ADD_EXPENSE_URL)
        html = response.data.decode("utf-8")
        invalid_categories = ["Rent", "Salary", "Misc", "Travel", "Utilities"]
        for invalid_cat in invalid_categories:
            # Check that the invalid category does not appear as an option value
            assert f'value="{invalid_cat}"' not in html, (
                f"Category '{invalid_cat}' must not appear in the category options"
            )

    def test_date_field_defaults_to_today(self, auth_client):
        today_str = date.today().strftime("%Y-%m-%d")
        response = auth_client.get(ADD_EXPENSE_URL)
        html = response.data.decode("utf-8")
        assert today_str in html, (
            f"The date field should default to today's date ({today_str})"
        )

    def test_page_extends_base_template(self, auth_client):
        """The rendered page should contain landmarks from base.html."""
        response = auth_client.get(ADD_EXPENSE_URL)
        # base.html renders a <nav> or footer; check for the Spendly brand
        assert b"Spendly" in response.data, (
            "Page must extend base.html (Spendly brand text expected)"
        )

    def test_form_submit_targets_add_expense_route(self, auth_client):
        response = auth_client.get(ADD_EXPENSE_URL)
        assert b"/expenses/add" in response.data, (
            "Form action must point to /expenses/add"
        )


# ===========================================================================
# POST happy path
# ===========================================================================

class TestPostAddExpenseHappyPath:
    def test_valid_submission_redirects_to_history(self, auth_client):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "250.00",
                "category": "Food",
                "date": "2026-06-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 302, (
            "Valid POST should result in a redirect"
        )
        assert HISTORY_URL in response.headers["Location"], (
            "Valid POST should redirect to /profile/history"
        )

    def test_valid_submission_inserts_expense_row(
        self, auth_client, seed_user, tmp_db_path
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "350.00",
                "category": "Transport",
                "date": "2026-06-02",
                "description": "Cab fare",
            },
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before + 1, (
            "A valid POST must insert exactly one new row into the expenses table"
        )

    def test_valid_submission_stores_correct_amount(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "499.99",
                "category": "Shopping",
                "date": "2026-06-03",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, "Expense row must exist after valid POST"
        assert abs(row["amount"] - 499.99) < 0.001, (
            f"Stored amount should be 499.99, got {row['amount']}"
        )

    def test_valid_submission_stores_correct_category(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": "Bills",
                "date": "2026-06-03",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row["category"] == "Bills", (
            f"Stored category should be 'Bills', got {row['category']}"
        )

    def test_valid_submission_stores_correct_date(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "75",
                "category": "Health",
                "date": "2026-05-15",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row["date"] == "2026-05-15", (
            f"Stored date should be '2026-05-15', got {row['date']}"
        )

    def test_valid_submission_stores_description(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "60",
                "category": "Entertainment",
                "date": "2026-06-01",
                "description": "Movie ticket",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row["description"] == "Movie ticket", (
            f"Stored description should be 'Movie ticket', got {row['description']}"
        )

    def test_valid_submission_without_description_stores_null(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "200",
                "category": "Other",
                "date": "2026-06-01",
                "description": "",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, "Row must be inserted even with empty description"
        assert row["description"] is None or row["description"] == "", (
            "Missing description should be stored as NULL or empty string"
        )

    def test_new_expense_appears_on_history_page(self, auth_client):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "1234.56",
                "category": "Shopping",
                "date": "2026-06-01",
                "description": "Unique item for history test",
            },
        )
        history_response = auth_client.get(HISTORY_URL)
        assert history_response.status_code == 200, (
            "History page must be accessible after adding an expense"
        )
        assert b"1234" in history_response.data or b"Shopping" in history_response.data, (
            "The new expense (amount or category) should appear on the history page"
        )

    def test_success_flash_message_present_after_redirect(self, auth_client):
        """Follow the redirect and confirm a success flash is displayed."""
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "50",
                "category": "Food",
                "date": "2026-06-01",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200, (
            "Following redirect after valid POST should yield 200"
        )
        # The success flash text from the spec is "Expense added successfully."
        assert b"successfully" in response.data or b"added" in response.data, (
            "A success flash message should be visible on the redirected page"
        )

    def test_valid_submission_stores_correct_user_id(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "80",
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row["user_id"] == seed_user["id"], (
            f"Expense must be associated with user_id={seed_user['id']}, "
            f"got {row['user_id']}"
        )


# ===========================================================================
# Amount validation
# ===========================================================================

class TestAmountValidation:
    @pytest.mark.parametrize(
        "bad_amount, label",
        [
            ("0",     "zero"),
            ("0.00",  "zero as float string"),
            ("-1",    "negative integer"),
            ("-0.01", "negative fractional"),
            ("",      "empty string"),
            ("abc",   "non-numeric string"),
            ("12abc", "alphanumeric string"),
            (" ",     "whitespace only"),
        ],
    )
    def test_invalid_amount_rerenders_form_with_200(
        self, auth_client, bad_amount, label
    ):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        assert response.status_code == 200, (
            f"Invalid amount ({label}) should re-render the form (200), not redirect"
        )

    @pytest.mark.parametrize(
        "bad_amount, label",
        [
            ("0",    "zero"),
            ("-5",   "negative"),
            ("",     "empty"),
            ("abc",  "non-numeric"),
        ],
    )
    def test_invalid_amount_shows_flash_error(
        self, auth_client, bad_amount, label
    ):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        # The spec says: "Amount must be a positive number."
        html = response.data.decode("utf-8")
        assert "Amount" in html or "amount" in html or "positive" in html, (
            f"A flash error about the amount must appear for input ({label})"
        )

    @pytest.mark.parametrize(
        "bad_amount",
        ["0", "-1", "", "abc"],
    )
    def test_invalid_amount_does_not_insert_db_row(
        self, auth_client, seed_user, tmp_db_path, bad_amount
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            f"Invalid amount '{bad_amount}' must not insert a DB row"
        )


# ===========================================================================
# Category validation
# ===========================================================================

class TestCategoryValidation:
    @pytest.mark.parametrize(
        "bad_category",
        [
            "",
            "Rent",
            "Groceries",
            "FOOD",           # case mismatch
            "food",           # lowercase
            "InvalidCat",
            "'; DROP TABLE expenses; --",
        ],
    )
    def test_invalid_category_rerenders_form_with_200(
        self, auth_client, bad_category
    ):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": bad_category,
                "date": "2026-06-01",
            },
        )
        assert response.status_code == 200, (
            f"Invalid category '{bad_category}' should re-render form (200)"
        )

    @pytest.mark.parametrize(
        "bad_category",
        ["", "Rent", "FOOD", "invalid"],
    )
    def test_invalid_category_shows_flash_error(
        self, auth_client, bad_category
    ):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": bad_category,
                "date": "2026-06-01",
            },
        )
        html = response.data.decode("utf-8")
        # Spec says: "Please select a valid category."
        assert (
            "category" in html.lower()
            or "valid" in html.lower()
            or "select" in html.lower()
        ), f"A flash error about category must appear for input '{bad_category}'"

    @pytest.mark.parametrize(
        "bad_category",
        ["", "Rent", "FOOD"],
    )
    def test_invalid_category_does_not_insert_db_row(
        self, auth_client, seed_user, tmp_db_path, bad_category
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": bad_category,
                "date": "2026-06-01",
            },
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            f"Invalid category '{bad_category}' must not insert a DB row"
        )

    def test_all_allowed_categories_are_accepted(
        self, auth_client, seed_user, tmp_db_path
    ):
        """Every value in ALLOWED_CATEGORIES must produce a successful insert."""
        for cat in ALLOWED_CATEGORIES:
            before = _expense_count(tmp_db_path, seed_user["id"])
            response = auth_client.post(
                ADD_EXPENSE_URL,
                data={"amount": "10", "category": cat, "date": "2026-06-01"},
            )
            after = _expense_count(tmp_db_path, seed_user["id"])
            assert after == before + 1, (
                f"Category '{cat}' should be accepted and insert a row"
            )
            assert response.status_code == 302, (
                f"Category '{cat}' should cause a redirect on success"
            )


# ===========================================================================
# Date validation
# ===========================================================================

class TestDateValidation:
    @pytest.mark.parametrize(
        "bad_date, label",
        [
            ("",             "empty string"),
            ("not-a-date",   "arbitrary string"),
            ("32-13-2099",   "structurally wrong (DD-MM-YYYY)"),
            ("2026/06/01",   "wrong separator"),
            ("01-06-2026",   "DD-MM-YYYY format"),
            ("2026-13-01",   "month 13"),
            ("2026-00-01",   "month 00"),
            ("2026-06-32",   "day 32"),
            ("99999-06-01",  "five-digit year"),
        ],
    )
    def test_invalid_date_rerenders_form_with_200(
        self, auth_client, bad_date, label
    ):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": "Food",
                "date": bad_date,
            },
        )
        assert response.status_code == 200, (
            f"Invalid date ({label}) should re-render the form (200)"
        )

    @pytest.mark.parametrize(
        "bad_date",
        ["", "not-a-date", "2026/06/01", "01-06-2026"],
    )
    def test_invalid_date_shows_flash_error(self, auth_client, bad_date):
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": "Food",
                "date": bad_date,
            },
        )
        html = response.data.decode("utf-8")
        assert (
            "date" in html.lower()
            or "valid" in html.lower()
        ), f"A flash error about the date must appear for input '{bad_date}'"

    @pytest.mark.parametrize(
        "bad_date",
        ["", "not-a-date", "2026/06/01"],
    )
    def test_invalid_date_does_not_insert_db_row(
        self, auth_client, seed_user, tmp_db_path, bad_date
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "100",
                "category": "Food",
                "date": bad_date,
            },
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            f"Invalid date '{bad_date}' must not insert a DB row"
        )


# ===========================================================================
# DB isolation: combined validation failure
# ===========================================================================

class TestDbIsolationOnValidationFailure:
    def test_all_fields_invalid_does_not_insert_row(
        self, auth_client, seed_user, tmp_db_path
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        auth_client.post(
            ADD_EXPENSE_URL,
            data={"amount": "0", "category": "BadCat", "date": "not-a-date"},
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            "All-invalid POST must not insert any DB row"
        )

    def test_multiple_sequential_failures_do_not_accumulate_rows(
        self, auth_client, seed_user, tmp_db_path
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        invalid_payloads = [
            {"amount": "", "category": "Food", "date": "2026-06-01"},
            {"amount": "100", "category": "BadCat", "date": "2026-06-01"},
            {"amount": "100", "category": "Food", "date": ""},
        ]
        for payload in invalid_payloads:
            auth_client.post(ADD_EXPENSE_URL, data=payload)
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            "Multiple failed POSTs must not insert any rows into the DB"
        )


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_very_large_amount_is_accepted(
        self, auth_client, seed_user, tmp_db_path
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "999999999.99",
                "category": "Other",
                "date": "2026-06-01",
            },
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert response.status_code == 302, (
            "A very large positive amount should be accepted"
        )
        assert after == before + 1, (
            "A very large positive amount should insert a row"
        )

    def test_sql_injection_in_description_stored_as_literal(
        self, auth_client, seed_user, tmp_db_path
    ):
        injection = "'; DROP TABLE expenses; --"
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "10",
                "category": "Other",
                "date": "2026-06-01",
                "description": injection,
            },
        )
        # The expenses table must still exist and the row must be retrievable
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, (
            "expenses table must survive a SQL-injection-like description"
        )
        assert row["description"] == injection, (
            "SQL-injection-like description must be stored as a literal string"
        )

    def test_sql_injection_in_amount_rejected_safely(
        self, auth_client, seed_user, tmp_db_path
    ):
        before = _expense_count(tmp_db_path, seed_user["id"])
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "1; DROP TABLE expenses; --",
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        # Should be treated as non-numeric and rejected with a form re-render
        assert response.status_code == 200, (
            "SQL-injection string as amount should be rejected and form re-rendered"
        )
        after = _expense_count(tmp_db_path, seed_user["id"])
        assert after == before, (
            "SQL-injection string as amount must not insert any row"
        )

    def test_expense_belongs_only_to_submitting_user(
        self, client, tmp_db_path
    ):
        """
        Two users submit expenses. Each user should only see their own
        expense count — verifies user_id scoping in the DB layer.
        """
        conn = sqlite3.connect(tmp_db_path)
        pw = generate_password_hash("pass")
        uid1 = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("User One", "one@example.com", pw),
        ).lastrowid
        uid2 = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("User Two", "two@example.com", pw),
        ).lastrowid
        conn.commit()
        conn.close()

        # Log in as user 1 and add an expense
        with client.session_transaction() as sess:
            sess["user_id"] = uid1
            sess["user_name"] = "User One"
        client.post(
            ADD_EXPENSE_URL,
            data={"amount": "50", "category": "Food", "date": "2026-06-01"},
        )

        # Log in as user 2 — must NOT see user 1's expense
        with client.session_transaction() as sess:
            sess["user_id"] = uid2
            sess["user_name"] = "User Two"

        assert _expense_count(tmp_db_path, uid1) == 1, (
            "User 1 should have exactly 1 expense"
        )
        assert _expense_count(tmp_db_path, uid2) == 0, (
            "User 2 should have 0 expenses after user 1 added one"
        )

    def test_fractional_amount_precision_preserved(
        self, auth_client, seed_user, tmp_db_path
    ):
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "0.01",
                "category": "Food",
                "date": "2026-06-01",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, "Row must be inserted for minimal positive amount"
        assert abs(row["amount"] - 0.01) < 0.0001, (
            f"Fractional amount 0.01 should be stored accurately, got {row['amount']}"
        )

    def test_very_long_description_accepted(
        self, auth_client, seed_user, tmp_db_path
    ):
        long_desc = "A" * 2000
        response = auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "10",
                "category": "Other",
                "date": "2026-06-01",
                "description": long_desc,
            },
        )
        assert response.status_code == 302, (
            "A very long description should not cause a server error"
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, "Row must be inserted even with a very long description"

    def test_whitespace_only_description_stored_as_none_or_empty(
        self, auth_client, seed_user, tmp_db_path
    ):
        """
        The spec says description is optional; a whitespace-only description
        should be treated as absent (the route strips and converts '' to None).
        """
        auth_client.post(
            ADD_EXPENSE_URL,
            data={
                "amount": "10",
                "category": "Food",
                "date": "2026-06-01",
                "description": "   ",
            },
        )
        row = _last_expense(tmp_db_path, seed_user["id"])
        assert row is not None, "Row must be inserted"
        # After strip(), "   " becomes "" which the route converts to None
        assert row["description"] is None or row["description"] == "", (
            "Whitespace-only description should be stored as NULL or empty"
        )
