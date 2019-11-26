from datetime import datetime
from hashlib import md5
import json
from time import time
from flask import current_app,flash
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import markdown
import bleach
from .bleach_whitelist import all_styles, markdown_attrs, markdown_tags
from app import db, login



followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    commemts = db.relationship('Comment', backref='user', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self):
        return self.username + ".png"

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

tags_posts = db.Table('tags_posts',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True)
)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, index=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    body_draft = db.Column(db.Text)
    is_draft = db.Column(db.Boolean, default=False)
    topping = db.Column(db.Boolean, default=False)
    reading_volume = db.Column(db.Integer, default=0, index=True)
    post_description = db.Column(db.Text)
    image_url = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    category_by_date_id = db.Column(db.Integer, db.ForeignKey('category_by_date.id'))
    category = db.relationship('Category', backref=db.backref('posts', lazy='dynamic'))
    tags = db.relationship('Tag', secondary=tags_posts, lazy='subquery',
                                 backref=db.backref('posts', lazy='dynamic'))
    commemts = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        target.body_html = bleach.linkify(bleach.clean(markdown.markdown(value, output_format='html', extensions=['extra']),
                                          markdown_tags, markdown_attrs, all_styles, strip=True))

    def __repr__(self):
        return '<Post %r>' % self.title

db.event.listen(Post.body, 'set', Post.on_changed_body)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    is_reply = db.Column(db.Boolean, default=False)
    has_reply = db.Column(db.Boolean, default=False)
    reply = db.Column(db.Integer, default=0)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def get_reply(self):
        return Comment.query.get_or_404(self.reply)

    def __repr__(self):
        return '<Comment {}>'.format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


# post count
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(16))
    post_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Tag %r>' % self.tag_name


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(64), nullable=False)
    post_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Category %r>' % self.category_name

    def delete_category(self):
        if self.id == 1:
            return False
        default_category = Category.query.get(1)
        for post in self.posts:
            post.category = default_category
            default_category.post_count += 1
        db.session.delete(self)
        db.session.commit()
        return True

    @classmethod
    def add_category(cls, category_name):
        if cls.query.filter_by(category_name=category_name).first() is not None:
            flash('这个分类已经存在，请重试')
            return False
        else:
            db.session.add(cls(category_name=category_name))
            db.session.commit()
            return True

class Category_by_date(db.Model):
    __tablename__ = "category_by_date"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    posts = db.relationship('Post', backref='years', lazy=True)

    def __repr__(self):
        return '<Category by date: %r>' % self.date
