from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.get_by_username(username)

        if user is None or not user.check_password(password):
            flash("用户名或密码错误", "error")
            return render_template("auth/login.html")

        login_user(user, remember=request.form.get("remember"))
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.index"))

    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            flash("请填写所有字段", "error")
            return render_template("auth/register.html")

        if password != password2:
            flash("两次密码输入不一致", "error")
            return render_template("auth/register.html")

        if len(password) < 4:
            flash("密码至少需要4个字符", "error")
            return render_template("auth/register.html")

        existing = User.get_by_username(username)
        if existing:
            flash("用户名已存在", "error")
            return render_template("auth/register.html")

        User.create(username, password)
        flash("注册成功，请登录", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("auth.login"))
