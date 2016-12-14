# coding=utf-8
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user
from .. import db
from . import auth
from ..models import User
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, \
    PasswordResetForm, PasswordResetRequestForm, ChangeEmailForm
from ..email import send_mail
from flask_login import current_user


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash(u'无效的用户名或密码')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('your have log out!')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        # 提交数据库之后才能赋予新用户 id 值，
        # 而确认令牌需要用到 id ，所以不能延后提交
        db.session.commit()
        token = user.generate_confirmation_token()
        send_mail(user.email, u'确认你的账号！',
                  'auth/email/confirm', user=user, token=token)
        flash(u'一封确认邮件已经发送到你的邮箱里！')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash(u'你已经验证过账号了，谢谢！')
    else:
        flash(u'这个验证链接已经无效或者不期待！')

    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, u'验证你的账号',
              'auth/email/confirm', user=current_user, token=token)
    flash(u'一封验证邮件已经发送到你的邮箱里了！')
    return redirect(url_for('main.index'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash(u'你的密码已经更新！')
            return redirect(url_for('main.index'))
        else:
            flash(u'无效的密码！')
    return render_template('auth/change_password.html', form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_confirmation_token()
            send_mail(user.email, u'重设你的密码',
                      'auth/email/reset_password',
                      user=user, token=token,
                      next=request.args.get('next'))
        flash(u'一封重置密码的邮件已经发送到你的邮箱！')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_annoymous:
        return redirect(url_for('main.index'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash(u'你的密码已经更新！')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_mail(new_email, u'验证你的邮箱',
                      'auth/email/change_email',
                      user=current_user, token=token)
            flash(u'一封验证邮件发送到你的邮箱里的，请你去确认！')
            return redirect(url_for('main.index'))
        else:
            flash(u'无效的邮箱或密码！')

    return render_template('auth/change_email.html', form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash(u'你的邮箱地址已经更新！')
    else:
        flash(u'无效的请求！')
    return redirect(url_for('main.index'))







