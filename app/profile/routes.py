from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..models import db, User, UserList, Activity, Follow, ListItem

bp = Blueprint("profile", __name__, template_folder="../templates/profile")

@bp.route("/<string:username>")
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Kullanıcının listeleri ve aktiviteleri (soldaki aktiviteler için)
    lists = (
        UserList.query
        .filter_by(user_id=user.id)
        .order_by(UserList.is_default.desc(), UserList.id)
        .all()
    )

    activities = (
        Activity.query
        .filter_by(user_id=user.id)
        .order_by(Activity.created_at.desc())
        .limit(20)
        .all()
    )

    is_owner = (current_user.id == user.id)

    # Takipçi / takip edilen
    followers_rel = user.followers.order_by(Follow.created_at.desc()).all()
    following_rel = user.following.order_by(Follow.created_at.desc()).all()
    followers = [f.follower for f in followers_rel]
    following = [f.followed for f in following_rel]

    followers_count = len(followers)
    following_count = len(following)

    is_following = False
    if not is_owner:
        is_following = current_user.is_following(user)

    # ----- KÜTÜPHANE RAF VERİLERİ -----
    # Amaç: listelerin ismine güvenmeden, list_type + is_default üzerinden
    # "izlenen / izlenecek / okunan / okunacak" raflarını doldurmak.

    def _default_lists(list_type: str):
        return (
            UserList.query
            .filter_by(user_id=user.id, list_type=list_type, is_default=True)
            .order_by(UserList.id)
            .all()
        )

    def _items_for_list(lst: UserList):
        if not lst:
            return []
        return (
            ListItem.query
            .filter_by(list_id=lst.id)
            .order_by(ListItem.added_at.desc())
            .all()
        )

    watch_defaults = _default_lists("watch")  # film listeleri
    read_defaults = _default_lists("read")    # kitap listeleri

    watched_items = []
    watchlist_items = []
    read_items = []
    toread_items = []

    # --- Film listelerini isim + fallback ile paylaştır ---
    for lst in watch_defaults:
        name = (lst.name or "").lower()
        if "izlenecek" in name or "to watch" in name or "watchlist" in name:
            watchlist_items = _items_for_list(lst)
        elif "izlenen" in name or "izlediklerim" in name or "watched" in name:
            watched_items = _items_for_list(lst)

    # Eğer isimlerden yakalayamadıysak, sırayla ver:
    # 1. default liste = izlenecek, 2. default liste = izlenen
    if not watchlist_items and watch_defaults:
        watchlist_items = _items_for_list(watch_defaults[0])
    if not watched_items and len(watch_defaults) > 1:
        watched_items = _items_for_list(watch_defaults[1])

    # --- Kitap listelerini isim + fallback ile paylaştır ---
    for lst in read_defaults:
        name = (lst.name or "").lower()
        if "okunacak" in name or "to read" in name:
            toread_items = _items_for_list(lst)
        elif "okunan" in name or "okuduklarım" in name or "read" in name:
            read_items = _items_for_list(lst)

    # fallback: 1. liste = okunacak, 2. liste = okunan
    if not toread_items and read_defaults:
        toread_items = _items_for_list(read_defaults[0])
    if not read_items and len(read_defaults) > 1:
        read_items = _items_for_list(read_defaults[1])

    return render_template(
        "profile/profile.html",
        profile_user=user,
        lists=lists,
        activities=activities,
        is_owner=is_owner,
        followers=followers,
        following=following,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        watched_items=watched_items,
        watchlist_items=watchlist_items,
        read_items=read_items,
        toread_items=toread_items,
    )



@bp.route("/<string:username>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(username):
    # Sadece kendi profilini düzenleyebilsin
    if username != current_user.username:
        flash("Sadece kendi profilinizi düzenleyebilirsiniz.", "warning")
        return redirect(url_for("profile.view_profile", username=username))

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        avatar_url = request.form.get("avatar_url", "").strip() or None
        bio = request.form.get("bio", "").strip() or None

        if not new_username:
            flash("Kullanıcı adı boş olamaz.", "danger")
        else:
            # kullanıcı adını değiştiriyorsa benzersiz olsun
            if new_username != current_user.username:
                existing = User.query.filter_by(username=new_username).first()
                if existing:
                    flash("Bu kullanıcı adı zaten kullanımda.", "danger")
                    return redirect(url_for("profile.edit_profile", username=username))

            current_user.username = new_username
            current_user.avatar_url = avatar_url
            current_user.bio = bio
            db.session.commit()
            flash("Profiliniz güncellendi.", "success")
            return redirect(url_for("profile.view_profile", username=current_user.username))

    return render_template(
        "profile/edit_profile.html",
        user=current_user,
    )


@bp.route("/<string:username>/<string:list_type>")
@login_required
def view_follow_list(username, list_type):
    """
    /profil/kübra/followers veya /profil/kübra/following gibi
    takipçi / takip edilen listelerini gösteren sayfa.
    """
    user = User.query.filter_by(username=username).first_or_404()

    if list_type == "followers":
        rels = user.followers.order_by(Follow.created_at.desc()).all()
        title = "Takipçiler"
        users = [f.follower for f in rels]
    elif list_type == "following":
        rels = user.following.order_by(Follow.created_at.desc()).all()
        title = "Takip Edilenler"
        users = [f.followed for f in rels]
    else:
        flash("Geçersiz liste türü.", "danger")
        return redirect(url_for("profile.view_profile", username=username))

    return render_template(
        "profile/follow_list.html",
        profile_user=user,
        users=users,
        list_type=list_type,
        title=title,
    )



@bp.route("/<string:username>/follow", methods=["POST"])
@login_required
def follow_user(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user.id == current_user.id:
        flash("Kendinizi takip edemezsiniz.", "warning")
        return redirect(url_for("profile.view_profile", username=username))

    current_user.follow(user)
    db.session.commit()
    flash(f"{user.username} kullanıcısını takip etmeye başladınız.", "success")
    return redirect(url_for("profile.view_profile", username=username))


@bp.route("/<string:username>/unfollow", methods=["POST"])
@login_required
def unfollow_user(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user.id == current_user.id:
        flash("Kendinizden takip kaldıramazsınız.", "warning")
        return redirect(url_for("profile.view_profile", username=username))

    current_user.unfollow(user)
    db.session.commit()
    flash(f"{user.username} kullanıcısını takip etmeyi bıraktınız.", "info")
    return redirect(url_for("profile.view_profile", username=username))