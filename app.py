import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db, init_db, seed_db,
    create_user, get_user_by_email, get_user_by_id, get_expense_summary,
    get_user_expenses, update_user_profile, update_user_password,
    get_expenses_by_category, add_expense as db_add_expense,
    get_expense_by_id, update_expense,
    delete_expense as db_delete_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

ALLOWED_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, generate_password_hash(password))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))
    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    member_since = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    summary = get_expense_summary(user_id)
    return render_template("profile.html", user=user, summary=summary, member_since=member_since)


# ------------------------------------------------------------------ #
# History Routes                                                      #
# ------------------------------------------------------------------ #

def _parse_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except (ValueError, TypeError):
        return None


@app.route("/profile/history")
def profile_history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    raw_start  = request.args.get("start_date", "").strip()
    raw_end    = request.args.get("end_date", "").strip()
    start_date = _parse_date(raw_start)
    end_date   = _parse_date(raw_end)
    if (raw_start and start_date is None) or (raw_end and end_date is None):
        start_date = None
        end_date = None
    expenses = get_user_expenses(user_id, start_date=start_date, end_date=end_date)
    return render_template(
        "history.html",
        expenses=expenses,
        start_date=start_date or "",
        end_date=end_date or "",
    )


# ------------------------------------------------------------------ #
# Summary Stats / Profile Edit Routes                                 #
# ------------------------------------------------------------------ #

@app.route("/profile/edit", methods=["POST"])
def profile_edit():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    name  = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if not name or not email:
        flash("Name and email are required.", "error")
        return redirect(url_for("profile"))
    try:
        update_user_profile(user_id, name, email)
        session["user_name"] = name
        flash("Profile updated successfully.", "success")
    except sqlite3.IntegrityError:
        flash("That email is already in use by another account.", "error")
    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["POST"])
def profile_password():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    current = request.form.get("current_password", "")
    new_pw  = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if new_pw != confirm:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))
    user = get_user_by_id(user_id)
    if user is None or not check_password_hash(user["password_hash"], current):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))
    update_user_password(user_id, generate_password_hash(new_pw))
    flash("Password changed successfully.", "success")
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Category Breakdown Routes                                           #
# ------------------------------------------------------------------ #

@app.route("/profile/categories/<category>")
def profile_category(category):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    expenses = get_expenses_by_category(user_id, category)
    summary  = get_expense_summary(user_id)
    category_total = sum(e["amount"] for e in expenses)
    return render_template(
        "category.html",
        category=category,
        expenses=expenses,
        category_total=category_total,
        grand_total=summary["total"],
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    today = datetime.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        raw_amount  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        raw_date    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Amount must be a positive number.", "error")
            return render_template("add_expense.html", categories=ALLOWED_CATEGORIES, today=today)

        if category not in ALLOWED_CATEGORIES:
            flash("Please select a valid category.", "error")
            return render_template("add_expense.html", categories=ALLOWED_CATEGORIES, today=today)

        date = _parse_date(raw_date)
        if not date:
            flash("Please enter a valid date.", "error")
            return render_template("add_expense.html", categories=ALLOWED_CATEGORIES, today=today)

        db_add_expense(user_id, amount, category, date, description)
        flash("Expense added successfully.", "success")
        return redirect(url_for("profile_history"))

    return render_template("add_expense.html", categories=ALLOWED_CATEGORIES, today=today)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != user_id:
        abort(403)

    if request.method == "POST":
        raw_amount  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        raw_date    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Amount must be a positive number.", "error")
            return render_template("edit_expense.html", expense=expense, categories=ALLOWED_CATEGORIES)

        if category not in ALLOWED_CATEGORIES:
            flash("Please select a valid category.", "error")
            return render_template("edit_expense.html", expense=expense, categories=ALLOWED_CATEGORIES)

        date = _parse_date(raw_date)
        if not date:
            flash("Please enter a valid date.", "error")
            return render_template("edit_expense.html", expense=expense, categories=ALLOWED_CATEGORIES)

        update_expense(id, amount, category, date, description)
        flash("Expense updated successfully.", "success")
        return redirect(url_for("profile_history"))

    return render_template("edit_expense.html", expense=expense, categories=ALLOWED_CATEGORIES)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != user_id:
        abort(403)
    db_delete_expense(id)
    flash("Expense deleted.", "success")
    return redirect(url_for("profile_history"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
