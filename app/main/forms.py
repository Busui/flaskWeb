from flask import request, flash
from wtforms import PasswordField, SubmitField, StringField, BooleanField, SelectField, TextAreaField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Email, Length, regexp, ValidationError
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.utils import secure_filename
from flask_pagedown.fields import PageDownField
from app.models import User, Category





class EditProfileForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    image = FileField('头像', validators=[FileRequired(), FileAllowed(['png'], 'png Images only!')])
    about_me = TextAreaField('关于我',
                             validators=[Length(min=0, max=140)])
    submit = SubmitField('确认')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('请使用不同的用户名')

class MessageForm(FlaskForm):
    message = TextAreaField('私信', validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('提交')


class CommentForm(FlaskForm):
    comment = TextAreaField('评论', validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('提交')


class ReplyForm(FlaskForm):
    reply = TextAreaField('回复', validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('提交')

class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(1, 64)])
    image = FileField('文章插图', validators=[FileRequired(), FileAllowed(['jpg', 'png', 'gif'], 'Images only!')])
    post_description = TextAreaField('文章描述')
    body = PageDownField('内容')
    tags = StringField('标签')
    categories = SelectField(u'选择分类', coerce=int)
    publish = SubmitField('发布')
    save = SubmitField('存为草稿')


class AddCategoryForm(FlaskForm):
    category_name = StringField('分类名称', validators=[DataRequired(), Length(1, 16)])
    submit = SubmitField('增加')


class Rename_CategoryForm(FlaskForm):
    old_category_name = SelectField(u'旧分类', coerce=int)
    new_category_name = StringField('新分类', validators=[DataRequired(), Length(1, 16)])
    submit = SubmitField('重命名')

    def validate_new_category_name(self, field):
            if Category.query.filter_by(category_name=field.data).first():
                flash("用户名已经存在，请重试")
                raise ValidationError('这个分类名称已被注册')


class Delete_CategoryForm(FlaskForm):
    category_name = SelectField(u'选择分类', coerce=int)
    submit = SubmitField('删除')


class Delete_PostForm(FlaskForm):
    submit = SubmitField('删除')


class Edit_PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(1, 64)])
    image = FileField('文章插图', validators=[FileAllowed(['jpg', 'png', 'gif'], 'Images only!')])
    post_description = TextAreaField('文章描述')
    body = PageDownField('内容')
    tags = StringField('标签')
    categories = SelectField(u'选择分类', coerce=int)
    publish = SubmitField('发布')
    save = SubmitField('存为草稿')
