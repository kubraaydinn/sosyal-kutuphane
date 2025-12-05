from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Kullanıcı
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ratings = db.relationship("Rating", backref="user", lazy="dynamic")
    reviews = db.relationship("Review", backref="user", lazy="dynamic")
    lists = db.relationship("UserList", backref="owner", lazy="dynamic")
    activities = db.relationship("Activity", backref="user", lazy="dynamic")

        # Takip ilişkileri
    followers = db.relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        backref="followed",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    following = db.relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        backref="follower",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def follower_count(self):
        return self.followers.count()

    def following_count(self):
        return self.following.count()

    def is_following(self, user):
        if not user or not getattr(user, "id", None):
            return False
        return (
            self.following.filter(Follow.followed_id == user.id).count() > 0
        )

    def follow(self, user):
        if not self.is_following(user) and self.id != user.id:
            f = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(f)

    def unfollow(self, user):
        if self.id == user.id:
            return
        f = self.following.filter(Follow.followed_id == user.id).first()
        if f:
            db.session.delete(f)

    def __repr__(self):
        return f"<User {self.username}>"
    
class Follow(db.Model):
    __tablename__ = "follow"

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("follower_id", "followed_id", name="uq_follow"),
    )


# Kitap / film içeriği
class Content(db.Model):
    __tablename__ = "contents"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), nullable=False)  # TMDb, Google Books vs. id
    source = db.Column(db.String(50), nullable=False)        # "tmdb" / "google_books" / "open_library"
    type = db.Column(db.String(10), nullable=False)          # "movie" / "book"
    title = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer)
    poster_url = db.Column(db.String(255))
    meta_json = db.Column(db.Text)  # Diğer meta bilgiler (JSON string)

    ratings = db.relationship("Rating", backref="content", lazy="dynamic")
    reviews = db.relationship("Review", backref="content", lazy="dynamic")
    list_items = db.relationship("ListItem", backref="content", lazy="dynamic")
    activities = db.relationship("Activity", backref="content", lazy="dynamic")

# Puanlama
class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # 1-10 arası
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "content_id", name="uix_user_content_rating"),
    )

# Yorum
class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

# Kullanıcı listeleri (okunacak, izlenecek vs.)
class UserList(db.Model):
    __tablename__ = "user_lists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    list_type = db.Column(db.String(20), nullable=False)  # "watch", "read", "custom"

    items = db.relationship("ListItem", backref="user_list", lazy="dynamic")

class ListItem(db.Model):
    __tablename__ = "list_items"

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("user_lists.id"), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("list_id", "content_id", name="uix_list_content"),
    )

# Aktivite (feed için)
class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"))
    activity_type = db.Column(db.String(20), nullable=False)  # "rating", "review", "list_add" ...
    ref_id = db.Column(db.Integer)  # ilgili rating/review/list_item id’si
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    likes = db.relationship("ActivityLike", backref="activity", lazy="dynamic", cascade="all, delete-orphan"
)
    comments = db.relationship("ActivityComment", backref="activity", lazy="dynamic", cascade="all, delete-orphan"
)

class ActivityLike(db.Model):
    __tablename__ = "activity_likes"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("activity_likes", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("activity_id", "user_id", name="uq_activity_like"),
    )


class ActivityComment(db.Model):
    __tablename__ = "activity_comments"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("activity_comments", lazy="dynamic"))
