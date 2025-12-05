from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, UserList

bp = Blueprint("auth", __name__, template_folder="../templates/auth")

@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("feed.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not email or not password:
            flash("Tüm alanları doldurmalısınız.", "danger")
            return render_template("auth/register.html")

        if password != password2:
            flash("Şifreler uyuşmuyor.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Bu e-posta zaten kayıtlı.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten alınmış.", "danger")
            return render_template("auth/register.html")
        

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()  # user.id burada oluşsun

        # Varsayılan listeler
        default_lists = [
            UserList(user_id=user.id, name="İzlenecek Filmler", list_type="watch", is_default=True),
            UserList(user_id=user.id, name="İzlenen Filmler", list_type="watch", is_default=True),
            UserList(user_id=user.id, name="Okunacak Kitaplar", list_type="read", is_default=True),
            UserList(user_id=user.id, name="Okunan Kitaplar", list_type="read", is_default=True),
        ]
        db.session.add_all(default_lists)
        db.session.commit()

        flash("Kayıt başarılı, giriş yapabilirsiniz.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("feed.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Hoş geldiniz, " + user.username, "success")
            return redirect(url_for("feed.index"))
        else:
            flash("E-posta veya şifre hatalı.", "danger")

    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("auth.login"))
