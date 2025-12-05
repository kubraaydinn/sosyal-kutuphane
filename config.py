import os

class Config:
    # Güvenlik için istersen çevre değişkeninden okursun
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Proje kökünde sosyal_kutuphane.db dosyası oluşturur
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "sosyal_kutuphane.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
