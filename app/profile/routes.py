from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from app.models import (
    db,
    User,
    Activity,
    UserListItem,
    Follow,
)

from sqlalchemy.orm import joinedload

bp = Blueprint("profile", __name__, url_prefix="/profile")


# ---------------------------------------------------------------------------
# PROFİL GÖRÜNTÜLE
# ---------------------------------------------------------------------------
@bp.route("/<username>")
@login_required
def view_profile(username):
    """
    Kullanıcı profil sayfası.
    Sol kolon: sadece bu kullanıcının aktiviteleri (10'ar 10'ar sayfalandırılmış)
    Sağ kolon: kütüphane rafları (izlenen / izlenecek filmler, okunan / okunacak kitaplar)
    """
    profile_user = User.query.filter_by(username=username).first_or_404()

    # --- Aktivite sayfalandırma ---
    page = request.args.get("page", 1, type=int)
    per_page = 10

    activities_query = (
        Activity.query.options(
            joinedload(Activity.user),
            joinedload(Activity.content),
        )
        .filter(Activity.user_id == profile_user.id)
        .order_by(Activity.created_at.desc())
    )

    activities_page = activities_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    # --- Kütüphane listeleri ---
    watched_items = (
        UserListItem.query.options(joinedload(UserListItem.content))
        .filter_by(user_id=profile_user.id, list_type="watched")
        .order_by(UserListItem.created_at.desc())
        .limit(20)
        .all()
    )

    watchlist_items = (
        UserListItem.query.options(joinedload(UserListItem.content))
        .filter_by(user_id=profile_user.id, list_type="watchlist")
        .order_by(UserListItem.created_at.desc())
        .limit(20)
        .all()
    )

    read_items = (
        UserListItem.query.options(joinedload(UserListItem.content))
        .filter_by(user_id=profile_user.id, list_type="read")
        .order_by(UserListItem.created_at.desc())
        .limit(20)
        .all()
    )

    toread_items = (
        UserListItem.query.options(joinedload(UserListItem.content))
        .filter_by(user_id=profile_user.id, list_type="toread")
        .order_by(UserListItem.created_at.desc())
        .limit(20)
        .all()
    )

    # Takipçi / takip edilen sayıları
    followers_count = Follow.query.filter_by(followed_id=profile_user.id).count()
    following_count = Follow.query.filter_by(follower_id=profile_user.id).count()

    is_owner = current_user.id == profile_user.id
    is_following = False
    if not is_owner:
        is_following = (
            Follow.query.filter_by(
                follower_id=current_user.id,
                followed_id=profile_user.id,
            ).first()
            is not None
        )

    return render_template(
        "profile/profile.html",
        profile_user=profile_user,
        activities=activities_page,  # template'de activities.items diye kullanıyoruz
        page=page,
        per_page=per_page,
        watched_items=watched_items,
        watchlist_items=watchlist_items,
        read_items=read_items,
        toread_items=toread_items,
        followers_count=followers_count,
        following_count=following_count,
        is_owner=is_owner,
        is_following=is_following,
    )


# ---------------------------------------------------------------------------
# PROFİL DÜZENLE
# ---------------------------------------------------------------------------
@bp.route("/<username>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user.id != current_user.id:
        flash("Sadece kendi profilinizi düzenleyebilirsiniz.", "warning")
        return redirect(url_for("profile.view_profile", username=username))

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        bio = request.form.get("bio", "").strip()
        avatar_url = request.form.get("avatar_url", "").strip() or None

        if not new_username:
            flash("Kullanıcı adı boş olamaz.", "danger")
            return redirect(url_for("profile.edit_profile", username=username))

        # başka kullanıcı ile çakışma kontrolü
        existing = (
            User.query.filter(User.username == new_username, User.id != user.id)
            .first()
        )
        if existing:
            flash("Bu kullanıcı adı zaten kullanımda.", "danger")
            return redirect(url_for("profile.edit_profile", username=username))

        user.username = new_username
        user.bio = bio
        user.avatar_url = avatar_url

        db.session.commit()
        flash("Profil güncellendi.", "success")
        return redirect(url_for("profile.view_profile", username=user.username))

    return render_template("profile/edit_profile.html", profile_user=user)


# ---------------------------------------------------------------------------
# TAKİP / TAKİPTEN ÇIK
# ---------------------------------------------------------------------------
@bp.route("/<username>/follow", methods=["POST"])
@login_required
def follow_user(username):
    target = User.query.filter_by(username=username).first_or_404()

    if target.id == current_user.id:
        flash("Kendinizi takip edemezsiniz.", "warning")
        return redirect(url_for("profile.view_profile", username=username))

    exists = Follow.query.filter_by(
        follower_id=current_user.id, followed_id=target.id
    ).first()
    if exists:
        flash("Zaten takip ediyorsunuz.", "info")
    else:
        f = Follow(follower_id=current_user.id, followed_id=target.id)
        db.session.add(f)
        db.session.commit()
        flash("Kullanıcıyı takip etmeye başladınız.", "success")

    return redirect(url_for("profile.view_profile", username=username))


@bp.route("/<username>/unfollow", methods=["POST"])
@login_required
def unfollow_user(username):
    target = User.query.filter_by(username=username).first_or_404()

    rel = Follow.query.filter_by(
        follower_id=current_user.id, followed_id=target.id
    ).first()

    if rel:
        db.session.delete(rel)
        db.session.commit()
        flash("Takipten çıktınız.", "info")
    else:
        flash("Bu kullanıcıyı takip etmiyorsunuz.", "warning")

    return redirect(url_for("profile.view_profile", username=username))


# ---------------------------------------------------------------------------
# TAKİPÇİ / TAKİP EDİLEN LİSTESİ
# ---------------------------------------------------------------------------
@bp.route("/<username>/follows/<list_type>")
@login_required
def view_follow_list(username, list_type):
    user = User.query.filter_by(username=username).first_or_404()

    if list_type == "followers":
        rels = Follow.query.filter_by(followed_id=user.id).all()
        users = [User.query.get(r.follower_id) for r in rels]
        title = "Takipçiler"
    else:
        rels = Follow.query.filter_by(follower_id=user.id).all()
        users = [User.query.get(r.followed_id) for r in rels]
        title = "Takip edilenler"

    return render_template(
        "profile/follow_list.html",
        profile_user=user,
        users=users,
        list_type=list_type,
        title=title,
    )
