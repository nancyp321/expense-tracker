import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db, init_db, seed_db,
    create_user, get_user_by_email, get_user_by_id, get_expense_summary,
    get_user_expenses, update_user_profile, update_user_password,
    get_expenses_by_category,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

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


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
