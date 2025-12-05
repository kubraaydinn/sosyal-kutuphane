from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from ..models import (
    db,
    Activity,
    Content,
    User,
    Follow,
    Rating,
    Review,
    ListItem,
    ActivityLike,
    ActivityComment,
)
from ..external_api import search_tmdb_movies, search_openlibrary_books

bp = Blueprint("feed", __name__, template_folder="../templates/feed")

PER_PAGE = 16


def _get_followed_ids(user):
    """Kullanıcının kendisi + takip ettikleri."""
    ids = [user.id]
    # user.following ilişkini Follow modeli ile kurmuştuk
    for f in user.following.all():
        ids.append(f.followed_id)
    return ids


def _build_activity_cards(activities):
    """Her Activity için rating / review / list_item + like/comment verilerini hazırla."""
    cards = []
    for act in activities:
        rating = review = list_item = None

        if act.activity_type == "rating" and act.ref_id:
            rating = Rating.query.get(act.ref_id)
        elif act.activity_type == "review" and act.ref_id:
            review = Review.query.get(act.ref_id)
        elif act.activity_type == "list_add" and act.ref_id:
            list_item = ListItem.query.get(act.ref_id)

        likes_count = ActivityLike.query.filter_by(activity_id=act.id).count()
        comments = (
            ActivityComment.query
            .filter_by(activity_id=act.id)
            .order_by(ActivityComment.created_at.asc())
            .all()
        )

        cards.append(
            {
                "activity": act,
                "rating": rating,
                "review": review,
                "list_item": list_item,
                "likes_count": likes_count,
                "comments": comments,
            }
        )
    return cards





# ------------------ AKIŞ (FEED) ------------------

def _build_discovery_base_query(content_type: str):
    """
    Film/kitap için ortak sorgu.
    Dönen:
      base_q, rating_subq, list_subq, review_subq
    """

    # Ortalama puanlar
    rating_subq = (
        db.session.query(
            Rating.content_id.label("content_id"),
            func.avg(Rating.score).label("avg_score"),
            func.count(Rating.id).label("rating_count"),
        )
        .group_by(Rating.content_id)
        .subquery()
    )

    # Kaç kişinin listesinde?
    list_subq = (
        db.session.query(
            ListItem.content_id.label("content_id"),
            func.count(ListItem.id).label("list_count"),
        )
        .group_by(ListItem.content_id)
        .subquery()
    )

    # Kaç yorum almış?
    review_subq = (
        db.session.query(
            Review.content_id.label("content_id"),
            func.count(Review.id).label("review_count"),
        )
        .group_by(Review.content_id)
        .subquery()
    )

    base_q = (
        db.session.query(
            Content,
            func.coalesce(rating_subq.c.avg_score, 0).label("avg_score"),
            func.coalesce(rating_subq.c.rating_count, 0).label("rating_count"),
            func.coalesce(list_subq.c.list_count, 0).label("list_count"),
            func.coalesce(review_subq.c.review_count, 0).label("review_count"),
        )
        .outerjoin(rating_subq, rating_subq.c.content_id == Content.id)
        .outerjoin(list_subq, list_subq.c.content_id == Content.id)
        .outerjoin(review_subq, review_subq.c.content_id == Content.id)
        .filter(Content.type == content_type)
    )

    return base_q, rating_subq, list_subq, review_subq


def get_discovery_lists(content_type: str, limit: int = 15):
    """
    Anasayfadaki vitrinler için sınırlı liste
    """
    base_q, rating_subq, list_subq, review_subq = _build_discovery_base_query(
        content_type
    )

    # En yüksek puanlılar
    top_rated = (
        base_q.order_by(func.coalesce(rating_subq.c.avg_score, 0).desc())
        .limit(limit)
        .all()
    )

    # En popüler (liste + yorum sayısı)
    popularity_score = (
        func.coalesce(list_subq.c.list_count, 0)
        + func.coalesce(review_subq.c.review_count, 0)
    )
    most_popular = (
        base_q.order_by(popularity_score.desc()).limit(limit).all()
    )

    return top_rated, most_popular




from flask_login import login_required
from flask import render_template


@bp.route("/movies/top-rated")
@login_required
def movies_top_rated():
    base_q, rating_subq, list_subq, review_subq = _build_discovery_base_query(
        "movie"
    )
    items = (
        base_q.order_by(func.coalesce(rating_subq.c.avg_score, 0).desc())
        .all()
    )

    return render_template(
        "search/movies_list.html",
        page_title="En Yüksek Puanlı Filmler",
        items=items,
    )


@bp.route("/movies/popular")
@login_required
def movies_popular():
    base_q, rating_subq, list_subq, review_subq = _build_discovery_base_query(
        "movie"
    )
    popularity_score = (
        func.coalesce(list_subq.c.list_count, 0)
        + func.coalesce(review_subq.c.review_count, 0)
    )
    items = base_q.order_by(popularity_score.desc()).all()

    return render_template(
        "search/movies_list.html",
        page_title="En Popüler Filmler",
        items=items,
    )


@bp.route("/books/top-rated")
@login_required
def books_top_rated():
    base_q, rating_subq, list_subq, review_subq = _build_discovery_base_query(
        "book"
    )
    items = (
        base_q.order_by(func.coalesce(rating_subq.c.avg_score, 0).desc())
        .all()
    )

    return render_template(
        "search/books_list.html",
        page_title="En Yüksek Puanlı Kitaplar",
        items=items,
    )


@bp.route("/books/popular")
@login_required
def books_popular():
    base_q, rating_subq, list_subq, review_subq = _build_discovery_base_query(
        "book"
    )
    popularity_score = (
        func.coalesce(list_subq.c.list_count, 0)
        + func.coalesce(review_subq.c.review_count, 0)
    )
    items = base_q.order_by(popularity_score.desc()).all()

    return render_template(
        "search/books_list.html",
        page_title="En Popüler Kitaplar",
        items=items,
    )





@bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    user_q = request.args.get("user_q", "", type=str).strip()

    followed_ids = _get_followed_ids(current_user)

    base_query = (
        Activity.query.filter(Activity.user_id.in_(followed_ids))
        .order_by(Activity.created_at.desc())
    )

    pagination = base_query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    activities = pagination.items
    activity_cards = _build_activity_cards(activities)

    # Popüler kullanıcılar + kullanıcı arama
    user_query = User.query
    if user_q:
        user_query = user_query.filter(User.username.ilike(f"%{user_q}%"))

    all_users = user_query.all()
    popular_sorted = sorted(all_users, key=lambda u: u.followers.count(), reverse=True)
    popular_users = [(u, u.followers.count()) for u in popular_sorted[:10]]

    return render_template(
        "feed/index.html",
        activity_cards=activity_cards,
        popular_users=popular_users,
        user_q=user_q,
        has_next=pagination.has_next,
        next_page=page + 1,
    )


@bp.route("/more")
@login_required
def more():
    """Daha Fazla Yükle butonu için JSON dönen endpoint."""
    page = request.args.get("page", 2, type=int)

    followed_ids = _get_followed_ids(current_user)

    base_query = (
        Activity.query.filter(Activity.user_id.in_(followed_ids))
        .order_by(Activity.created_at.desc())
    )

    pagination = base_query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    activities = pagination.items
    activity_cards = _build_activity_cards(activities)

    html = render_template("feed/_activity_cards.html", activity_cards=activity_cards)

    return jsonify(
        {
            "html": html,
            "has_next": pagination.has_next,
            "next_page": page + 1,
        }
    )


@bp.route("/activities/<int:activity_id>/like", methods=["POST"])
@login_required
def like_activity(activity_id):
    act = Activity.query.get_or_404(activity_id)

    like = ActivityLike.query.filter_by(
        activity_id=activity_id,
        user_id=current_user.id
    ).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        like = ActivityLike(activity_id=activity_id, user_id=current_user.id)
        db.session.add(like)
        liked = True

    db.session.commit()
    like_count = ActivityLike.query.filter_by(activity_id=activity_id).count()

    return jsonify({"liked": liked, "like_count": like_count})


@bp.route("/activities/<int:activity_id>/comment", methods=["POST"])
@login_required
def comment_activity(activity_id):
    act = Activity.query.get_or_404(activity_id)

    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Boş yorum gönderilemez."}), 400

    comment = ActivityComment(
        activity_id=activity_id,
        user_id=current_user.id,
        text=text,
    )
    db.session.add(comment)
    db.session.commit()

    comments = (
        ActivityComment.query
        .filter_by(activity_id=activity_id)
        .order_by(ActivityComment.created_at.asc())
        .all()
    )

    html = render_template("feed/_activity_comments.html", comments=comments, activity=act)

    return jsonify(
        {
            "ok": True,
            "html": html,
            "comment_count": len(comments),
        }
    )


# ------------------ İÇERİK ARAMA (ESKİ ROUTE'LARIN DEVAMI) ------------------


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = []

    if q:
        # Başlığa göre basit LIKE araması (case-insensitive)
        results = Content.query.filter(Content.title.ilike(f"%{q}%")).all()

    return render_template("search/search.html", q=q, results=results)


@bp.route("/search/movies")
@login_required
def search_movies():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        results = search_tmdb_movies(q)  # TMDb’den film arama (senin mevcut fonksiyonun)

    top_rated, most_popular = get_discovery_lists("movie")

    return render_template(
        "search/movies.html",
        query=q,
        results=results,
        top_rated=top_rated,
        most_popular=most_popular,
    )



@bp.route("/search/books")
@login_required
def search_books():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        results = search_openlibrary_books(q)

    top_rated, most_popular = get_discovery_lists("book")

    return render_template(
        "search/books.html",
        query=q,
        results=results,
        top_rated=top_rated,
        most_popular=most_popular,
    )
