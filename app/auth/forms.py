from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登入')


class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    image = FileField('头像', validators=[FileRequired(), FileAllowed(['png'], 'png Images only!')])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    password2 = PasswordField(
        '重复输入密码', validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('该用户名已被注册')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('该邮箱已被注册')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('邮箱地址', validators=[DataRequired(), Email()])
    submit = SubmitField('请求密码重置')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('密码', validators=[DataRequired()])
    password2 = PasswordField(
        '重复输入密码', validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField('修改密码')
