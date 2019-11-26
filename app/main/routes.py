from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app, send_from_directory
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, PostForm, MessageForm, \
    Edit_PostForm, Rename_CategoryForm, AddCategoryForm, Delete_CategoryForm, CommentForm, \
        ReplyForm
from app.models import User, Post, Message, Notification, Category, Category_by_date, Tag, Comment
from app.main import bp
from config import Config
import os
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from app.utils import get_years
from werkzeug import abort
from config import COMMENT_COLORS


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    g.locale = str(get_locale())


@bp.route('/static/photos/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'],
                               filename)


@bp.route('/', methods=['GET'])
@bp.route('/index', methods=['GET'])
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/categories', methods=['GET', 'POST'])
def categories():
    categories = Category.query.all()
    return render_template('category.html', categories=categories)

@bp.route('/tags', methods=['GET'])
def tags():
    tags = Tag.query.all()
    return render_template('tag.html', tags=tags)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/other_user/<username>')
def other_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.other_user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.other_user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    return render_template('other_user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_popup.html', user=user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s!', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))



@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/send_comment/<int:id>', methods=['GET', 'POST'])
@login_required
def send_comment(id, form):
    post = Post.query.get_or_404(id)
    if form.validate_on_submit():
        comment = Comment(post=current_user, posts=post, body=form.comment.data)
        db.session.add(comment)
        db.session.commit()
        flash('评论成功')
        return redirect(url_for('main.show_post', id=post.id))
    return redirect(url_for('main.show_post', id=post.id, form=form))

@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


@bp.route('/category/<string:category_name>')
def get_posts_by_category_name(category_name):
    page = request.args.get('page', 1, type=int)
    category = Category.query.filter_by(category_name=category_name).first()
    if category is not None:
        pagination = category.posts.filter_by(is_draft=False).order_by(Post.timestamp.desc()).paginate(
                page, int(current_app.config['POSTS_PER_PAGE']), error_out=False)
        posts = pagination.items
        if (len(posts) == 0):
            flash("当前分类下没有文章哦")
            return render_template('index.html', posts=None)
        return render_template('index.html', posts=posts, pagination=pagination)


@bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    user = current_user._get_current_object()
    form = PostForm()
    form.categories.choices = [(cate.id, cate.category_name) for cate in Category.query.order_by('category_name')]
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        post_description = form.post_description.data
        if form.publish.data:
            f = form.image.data
            if f:
                filename = secure_filename(f.filename)
                url = os.path.join(
                    current_app.root_path, 'static', 'photos', filename
                )
                f.save(url)
                image_url = filename
            else:
                image_url = ''
            category = Category.query.get(form.categories.data)
            if category is not None:
                category.post_count += 1
            tags = form.tags.data
            # 序列化tags
            tag_list = []
            if tags is not None:
                for tag in tags.split(','):
                    tag_in = Tag.query.filter_by(tag_name=tag).first()
                    if tag_in:
                        tag_in.post_count += 1
                        tag_list.append(tag_in)
                    else:
                        new_tag = Tag(tag_name=tag, post_count=1)
                        db.session.add(new_tag)
                        tag_list.append(new_tag)
            post = Post(title=title, body=body, author=user, post_description=post_description,
                    category=category, tags=tag_list, years=get_years(), image_url=image_url)
        else:
            post = Post(title=title, body_draft=body, body=body, author=user, post_description=post_description, is_draft=True)
        db.session.add(post)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('发布失败')
            return redirect(url_for('main.new_post'))
        flash('发布成功')
        return redirect(url_for('main.index', id=post.id))
    return render_template('new_post.html', form=form)


@bp.route('/post/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    user = current_user._get_current_object()
    post = Post.query.get(id)
    if post is None:
        abort(403)
    form = Edit_PostForm()
    old_cate = post.category
    old_tags = post.tags
    form.categories.choices = [(cate.id, cate.category_name) for cate in Category.query.order_by('category_name')]
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        post_description = form.post_description.data
        if form.publish.data:
            f = form.image.data
            if f:
                filename = secure_filename(f.filename)
                url = os.path.join(
                    current_app.root_path, 'static', 'photos', filename
                )
                f.save(url)
                image_url = filename
            else:
                image_url = ''
            category = Category.query.get(form.categories.data)
            if category is not None:
                category.post_count += 1
            tags = form.tags.data
            # 序列化tags
            tag_list = []
            if tags is not None:
                for tag in tags.split(','):
                    tag_in = Tag.query.filter_by(tag_name=tag).first()
                    if tag_in:
                        tag_in.post_count += 1
                        tag_list.append(tag_in)
                    else:
                        new_tag = Tag(tag_name=tag, post_count=1)
                        db.session.add(new_tag)
                        tag_list.append(new_tag)
            post.title = title
            post.body = body
            post.author = user
            post.post_description = post_description
            post.is_draft = False
            post.category = category
            post.tags = tag_list
            post.years = get_years()
            image_url = image_url
            if old_cate and old_cate.post_count != 0:
                old_cate.post_count -= 1
            for tag in old_tags:
                if tag.post_count:
                    tag.post_count -= 1
                if tag.post_count == 0:
                    db.session.delete(tag)
        else:
            post.author = user
            post.title = title
            post.body = body
            post.body_draft = body
            post.post_description = post_description
            post.is_draft = True
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('发布失败')
            return redirect(url_for('main.new_post'))
        flash('发布成功')
        return redirect(url_for('bp.show_post', id=post.id))
    
    form.title.data = post.title
    form.post_description.data = post.post_description
    if post.is_draft:
        form.body.data = post.body_draft
    else:
        form.body.data = post.body
    return render_template('edit_post.html', form=form)

@bp.route('/post/<int:id>', methods=['GET', 'POST'])
def show_post(id):
    post = Post.query.get_or_404(id)
    comments = Comment.query.filter_by(post_id=id, is_reply=False)
    if not current_user.is_anonymous:
        form = CommentForm()
        if form.validate_on_submit():
            comment = Comment(user=current_user, post=post, body=form.comment.data)
            db.session.add(comment)
            db.session.commit()
            flash('评论成功')
        return render_template('show_post.html', post=post, form=form, comments=comments, COMMENT_COLORS=COMMENT_COLORS)
    flash("登录后可评论文章")
    return render_template('show_post.html', post=post, comments=comments, COMMENT_COLORS=COMMENT_COLORS)


@bp.route('/post/reply/<int:id>', methods=('GET', 'POST'))
@login_required
def reply(id):
    comment = Comment.query.get_or_404(id)
    form = ReplyForm()
    if form.validate_on_submit():
        reply = Comment(user=current_user, post=comment.post, body=form.reply.data, is_reply=True)
        db.session.add(reply)
        db.session.commit()
        comment.reply = reply.id
        comment.has_reply = True
        db.session.commit()
        flash('回复成功')
        print(reply.id)
        return redirect(url_for('main.show_post', id=comment.post.id))
    return render_template('reply.html', form=form, comment_user=comment.user.username)
    



@bp.route('/post/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_post(id):
    post = Post.query.get(id)
    if post:
        cate = post.category
        if cate.post_count:
            cate.post_count -= 1
        if cate.post_count == 0:
            db.session.delete(cate)
        for tag in post.tags:
            if tag.post_count:
                tag.post_count -= 1
            if tag.post_count == 0:
                db.session.delete(tag)
        db.session.delete(post)
        db.session.commit()
        flash("删除成功")
    else:
        flash('删除失败')
    return redirect(url_for('main.index'))


@bp.route('/post/manage')
@login_required
def manage_post():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('manage_post.html', posts=posts)


@bp.route('/category/manage')
@login_required
def manage_category():
    add_category_form = AddCategoryForm()
    rename_category_form = Rename_CategoryForm()
    delete_category_form = Delete_CategoryForm()
    choices = [(cate.id, cate.category_name) for cate in Category.query.order_by('category_name')]
    rename_category_form.old_category_name.choices = choices
    delete_category_form.category_name.choices = choices

    return render_template('manage_cate.html',
                            add_category_form=add_category_form,
                            rename_category_form=rename_category_form,
                            delete_category_form=delete_category_form)


@bp.route('/category/delete', methods=['POST'])
@login_required
def delete_category():
    delete_category_form = Delete_CategoryForm()
    delete_category_form.category_name.choices = [(cate.id, cate.category_name) for cate in Category.query.order_by('category_name')]
    if delete_category_form.validate_on_submit():
        category = Category.query.get(delete_category_form.category_name.data)
        if category.delete_category():
            flash("删除成功")
            return redirect(url_for('main.index'))
        else:
            flash('删除失败')
            return redirect(url_for('main.manage_category'))


@bp.route('/category/rename', methods=['POST'])
@login_required
def rename_category():
    rename_category_form = Rename_CategoryForm()
    rename_category_form.old_category_name.choices = [(cate.id, cate.category_name) for cate in Category.query.order_by('category_name')]
    if rename_category_form.validate_on_submit():
        category = Category.query.get(rename_category_form.old_category_name.data)
        category.category_name = rename_category_form.new_category_name.data
        db.session.commit()
        flash("修改分类成功")
        return redirect(url_for('main.categories'))
    return redirect(url_for('main.manage_category'))


@bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    add_category_form = AddCategoryForm()
    if add_category_form.validate_on_submit():
        category_name = add_category_form.category_name.data
        if Category.add_category(category_name):
            flash("添加分类成功")
            return redirect(url_for('main.index'))
        else:
            flash("添加分类失败")
            return redirect(url_for('main.manage_category'))


@bp.route('/tag/<string:name>')
def get_post_by_tag(name):
    page = request.args.get('page', 1, type=int)
    tag = Tag.query.filter_by(tag_name=name).first_or_404()
    pagination = tag.posts.filter_by(is_draft=False).order_by(Post.timestamp.desc()).paginate(
                page, int(current_app.config['POSTS_PER_PAGE']), error_out=False)
    posts = pagination.items
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('index.html', posts=posts, pagination=pagination)

