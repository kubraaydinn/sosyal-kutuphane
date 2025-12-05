import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import db, Content, Rating, Review, Activity, UserList, ListItem
from ..external_api import get_tmdb_movie_details

# Blueprint burada tanımlanıyor
bp = Blueprint("content", __name__, template_folder="../templates/content")


@bp.route("/import", methods=["POST"])
@login_required
def import_external():
    external_id = request.form.get("external_id", "").strip()
    source = request.form.get("source", "").strip()
    ctype = request.form.get("type", "").strip()   # "movie" / "book"
    title = request.form.get("title", "").strip()
    year_str = request.form.get("year", "").strip()
    poster_url = request.form.get("poster_url", "").strip() or None

    if not (external_id and source and ctype and title):
        flash("Eksik veri alındı, içerik eklenemedi.", "danger")
        return redirect(url_for("feed.index"))

    # Yıl integer'a çevrilmeye çalışılır
    year = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None

    # Zaten varsa tekrar oluşturma
    existing = Content.query.filter_by(
        external_id=external_id,
        source=source
    ).first()

    if existing:
        flash("Bu içerik zaten sistemde var, detay sayfasına yönlendirildiniz.", "info")
        return redirect(url_for("content.detail", content_id=existing.id))

    # --- meta bilgiyi hazırlayalım ---
    meta = {}

    # Kaynak TMDb ve tür film ise ekstra verileri çek
    if source == "tmdb" and ctype == "movie":
        details = get_tmdb_movie_details(external_id)
        if details:
            meta.update(details)

    content = Content(
        external_id=external_id,
        source=source,
        type=ctype,
        title=title,
        year=year,
        poster_url=poster_url,
        meta_json=json.dumps(meta, ensure_ascii=False)
    )
    db.session.add(content)
    db.session.commit()

    flash("İçerik başarıyla sisteme eklendi.", "success")
    return redirect(url_for("content.detail", content_id=content.id))


@bp.route("/<int:content_id>", methods=["GET", "POST"])
@login_required
def detail(content_id):
    content = Content.query.get_or_404(content_id)

    # TMDb/OpenLibrary meta verisini çöz
    meta = {}
    if content.meta_json:
        try:
            meta = json.loads(content.meta_json)
        except json.JSONDecodeError:
            meta = {}

    # Kullanıcının kendi puanı
    user_rating = Rating.query.filter_by(
        user_id=current_user.id,
        content_id=content.id
    ).first()

    # Ortalama puan
    ratings = Rating.query.filter_by(content_id=content.id).all()
    avg_rating = None
    if ratings:
        avg_rating = sum(r.score for r in ratings) / len(ratings)

    # Yorumlar (yeniden eskiye)
    reviews = (
        Review.query.filter_by(content_id=content.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    # Kullanıcının bu içerik türü için listeleri
    list_type = "watch" if content.type == "movie" else "read"
    user_lists = UserList.query.filter_by(
        user_id=current_user.id,
        list_type=list_type
    ).all()

    if request.method == "POST":
        # ----------------- LİSTEYE EKLE / ÇIKAR -----------------
        if "list_id" in request.form:
            try:
                list_id = int(request.form["list_id"])
            except ValueError:
                flash("Geçersiz liste.", "danger")
                return redirect(url_for("content.detail", content_id=content.id))

            user_list = UserList.query.filter_by(
                id=list_id,
                user_id=current_user.id
            ).first()

            if not user_list:
                flash("Liste bulunamadı.", "danger")
                return redirect(url_for("content.detail", content_id=content.id))

            existing = ListItem.query.filter_by(
                list_id=list_id,
                content_id=content.id
            ).first()

            if existing:
                # Listeden çıkarma
                db.session.delete(existing)
                db.session.commit()
                flash("İçerik listeden çıkarıldı.", "info")
            else:
                # Listeye ekleme
                item = ListItem(list_id=list_id, content_id=content.id)
                db.session.add(item)
                db.session.flush()  # item.id için

                act = Activity(
                    user_id=current_user.id,
                    content_id=content.id,
                    activity_type="list_add",
                    ref_id=item.id,   # ÖNEMLİ: ListItem.id
                )
                db.session.add(act)
                db.session.commit()

                flash("İçerik listeye eklendi.", "success")

            return redirect(url_for("content.detail", content_id=content.id))

        # ----------------- PUAN GÖNDERME -----------------
        if "score" in request.form:
            try:
                score = int(request.form["score"])
            except ValueError:
                flash("Puan sayısal olmalı.", "danger")
                return redirect(url_for("content.detail", content_id=content.id))

            if score < 1 or score > 10:
                flash("Puan 1 ile 10 arasında olmalı.", "danger")
                return redirect(url_for("content.detail", content_id=content.id))

            if user_rating:
                user_rating.score = score
                # mevcut rating'in id'si zaten var
            else:
                user_rating = Rating(
                    user_id=current_user.id,
                    content_id=content.id,
                    score=score
                )
                db.session.add(user_rating)
                db.session.flush()  # user_rating.id üretildi

            # Her puan vermede bir Activity kaydı
            act = Activity(
                user_id=current_user.id,
                content_id=content.id,
                activity_type="rating",
                ref_id=user_rating.id,  # ÖNEMLİ: Rating.id
            )
            db.session.add(act)

            db.session.commit()
            flash("Puanınız kaydedildi.", "success")
            return redirect(url_for("content.detail", content_id=content.id))

        # ----------------- YORUM GÖNDERME -----------------
        if "review_text" in request.form:
            text = request.form["review_text"].strip()
            if not text:
                flash("Boş yorum kaydedilmedi.", "warning")
                return redirect(url_for("content.detail", content_id=content.id))

            review = Review(
                user_id=current_user.id,
                content_id=content.id,
                text=text
            )
            db.session.add(review)
            db.session.flush()  # review.id için

            act = Activity(
                user_id=current_user.id,
                content_id=content.id,
                activity_type="review",
                ref_id=review.id,  # ÖNEMLİ: Review.id
            )
            db.session.add(act)
            db.session.commit()

            flash("Yorumunuz kaydedildi.", "success")
            return redirect(url_for("content.detail", content_id=content.id))

    return render_template(
        "content/detail.html",
        content=content,
        user_rating=user_rating,
        avg_rating=avg_rating,
        reviews=reviews,
        user_lists=user_lists,
        meta=meta
    )