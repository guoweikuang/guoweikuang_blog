# coding=utf-8
from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User


class LoginForm(Form):
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField(u'密码', validators=[DataRequired()])
    remember_me = BooleanField(u'保持登录状态')
    submit = SubmitField(u'登录')


class RegistrationForm(Form):
    email = StringField(u'邮箱', validators=[
        DataRequired(), Length(6, 64, message=u'邮箱长度要在6和64之间'), Email()])
    username = StringField(u'用户名', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              u'用户名必须为字母，数字，小数点或者下划线')])
    password = PasswordField(u'密码', validators=[
        DataRequired(), EqualTo('password2', message=u'密码必须匹配！')])
    password2 = PasswordField(u'确认密码', validators=[DataRequired()])
    submit = SubmitField(u'注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经被注册了！')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已经被使用了！')


class ChangePasswordForm(Form):
    old_password = PasswordField(u'旧密码', validators=[DataRequired()])
    password = PasswordField(u'新密码', validators=[
        DataRequired(), EqualTo('password2', message=u'密码必须一致！')])
    password2 = PasswordField(u'确认密码', validators=[DataRequired()])
    submit = SubmitField(u'更新密码')


class PasswordResetRequestForm(Form):
    email = StringField(u'邮箱', validators=[
                                            DataRequired(),
                                            Length(6, 64, message=u'邮箱长度要在6和64之间'),
                                            Email(message=u'邮箱格式不正确')])
    submit = SubmitField(u'重置密码')


class PasswordResetForm(Form):
    email = StringField(u'邮箱', validators=[
                                    DataRequired(),
                                    Length(6, 64, message=u'邮件长度要在6和64之间'),
                                    Email(message=u'邮件格式不正确！')])
    password = PasswordField(u'密码', validators=[
                                                DataRequired(),
                                                EqualTo(u'password2', message=u'密码必须一致！')])
    password2 = PasswordField(u'重输密码', validators=[DataRequired()])
    submit = SubmitField(u'确认')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError(u'邮箱未注册！')


class ChangeEmailForm(Form):
    email = StringField(u'新邮箱', validators=[
                                            DataRequired(),
                                            Length(6, 64, message=u'邮件长度要在6和64之间'),
                                            Email(message=u'邮箱格式不正确')])
    password = PasswordField(u'密码', validators=[DataRequired()])
    submit = SubmitField(u'更新邮箱')





