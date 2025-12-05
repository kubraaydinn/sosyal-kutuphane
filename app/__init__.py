from flask import Flask
from flask_login import LoginManager
from datetime import datetime

from config import Config
from .models import db, User

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # login lazım olduğunda buraya yönlendir


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---- Akış sayfası için "x saat önce" filtresi ----
def timesince(value):
    if not value:
        return ""
    now = datetime.utcnow()
    diff = now - value
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "az önce"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} dakika"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} saat"
    days = hours // 24
    if days < 7:
        return f"{days} gün"
    weeks = days // 7
    if weeks < 4:
        return f"{weeks} hafta"
    months = days // 30
    if months < 12:
        return f"{months} ay"
    years = days // 365
    return f"{years} yıl"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Veritabanı ve login
    db.init_app(app)
    login_manager.init_app(app)

    # Jinja filtresi kaydı
    app.jinja_env.filters["timesince"] = timesince

    # Blueprint'ler
    from .auth.routes import bp as auth_bp
    from .feed.routes import bp as feed_bp
    from .content.routes import bp as content_bp
    from .profile.routes import bp as profile_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(feed_bp)  # ana sayfa
    app.register_blueprint(content_bp, url_prefix="/content")
    app.register_blueprint(profile_bp, url_prefix="/profile")

    # Basit bir CLI komutu: veritabanı tablolarını oluştur
    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()
        print("Database initialized.")

    # *** ÖNEMLİ: Artık app'i gerçekten döndürüyoruz ***
    return app
