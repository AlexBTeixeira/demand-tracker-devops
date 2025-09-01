# blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required
import MySQLdb.cursors

from extensions import mysql, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(
            "SELECT id, username, name, password_hash FROM users WHERE username = %s",
            (username,),
        )
        user_data = cur.fetchone()
        cur.close()

        if user_data and password == user_data["password_hash"]:
            user = User(
                user_data["id"],
                user_data["username"],
                user_data["name"],
                user_data["password_hash"],
            )
            # login_user(user)
            flash("Login bem-sucedido!", "success")
            return redirect(url_for("demands.dashboard"))
        else:
            flash("Usuário ou senha inválidos.", "danger")

    return render_template("pages/login.html")


@auth_bp.route("/logout")
# @login_required
def logout():
    # logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("auth.login"))
