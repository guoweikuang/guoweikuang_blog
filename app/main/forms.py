# coding=utf-8
from flask_wtf import Form
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Regexp, Email, ValidationError
from ..models import Role, User
from flask_pagedown.fields import PageDownField


class NameForm(Form):
    """
    StringField 构造函数中的可选参数 validators
    指定一个由验证函数组成的列表，
    在接受用户提交的数据之前验证数据
    """
    name = StringField(u'your name:', validators=[DataRequired()])
    submit = SubmitField('submit'.encode('utf-8'))


class EditProfileForm(Form):
    name = StringField(u'名字', validators=[Length(0, 64)])
    location = StringField(u'所在地', validators=[Length(0, 64)])
    about_me = TextAreaField(u'关于自己')
    submit = SubmitField(u'提交')


class EditProfileAdminForm(Form):
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField(u'用户名', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          'Usernames must have only letters, '
                                          'numbers, dots or underscores')])
    confirmed = BooleanField(u'验证')
    role = SelectField(u'角色', coerce=int)
    name = StringField(u'真实名字', validators=[Length(0, 64)])
    location = StringField(u'所在地', validators=[Length(0, 64)])
    about_me = TextAreaField(u'关于我')
    submit = SubmitField(u'提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经被注册了.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已经被使用了.')


class PostForm(Form):
    body = PageDownField(u'写下你想说的话', validators=[DataRequired()])
    submit = SubmitField(u'提交')


class CommentForm(Form):
    body = StringField(u'', validators=[DataRequired()])
    submit = SubmitField(u'提交')

