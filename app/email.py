# coding: utf-8
from flask_mail import Message
from flask import current_app, render_template
from threading import Thread
from . import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_mail(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    # msg.body = u'郭伟匡的个人博客'
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
