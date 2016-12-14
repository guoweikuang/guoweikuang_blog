# coding: utf-8
from flask import Flask, render_template,\
                session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_script import Manager
from flask_moment import Moment
from datetime import datetime
from flask_wtf import Form
from wtforms import StringField, SubmitField
from wtforms.validators import Required
from flask_sqlalchemy import SQLAlchemy
import os
from flask_script import Shell
from flask_migrate import Migrate, MigrateCommand
from flask_mail import Mail, Message
from threading import Thread
from celery import Celery


basedir = os.path.abspath(os.path.dirname(__file__))
"""
app = Flask(__name__)
为什么这里要传入__name__参数呢？？？
Flask用这个参数来决定程序的根目录，
以便找到根目录的资源文件
"""
app = Flask(__name__)
app.config['SECRET_KEY'] = 'guo wei kuang'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# 发送邮件需要的配置
app.config['MAIL_SERVER'] = 'smtp.163.com'
app.config['MAIL_PORT'] = 465
# 这里需要注意的是，使用SSL还是TSL，需要根据使用的邮件服务提供商里面的说明为主
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = '15602200534@163.com'
app.config['MAIL_PASSWORD'] = 'gwk2014081029'
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Guoweikuang]'
app.config['FLASKY_MAIL_SENDER'] = '郭伟匡<15602200534@163.com>'
app.config['FLASKY_ADMIN'] = '673411814@qq.com'

# celery任务调度使用的redis
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
manager = Manager(app)
bootstrap = Bootstrap(app)
# 时间日期渲染
moment = Moment(app)
db = SQLAlchemy(app)
mail = Mail(app)

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
"""
url_for() 函数最简单的用法是以视图函数名（或者 app.add_url_route() 定义路由时使用的端点名）
作为参数，返回对应的 URL,调用 url_for('index', _external=True) 返回的则是绝对地址
"""


class NameForm(Form):
    """
    StringField 构造函数中的可选参数 validators 指定一个由验证函数组成的列表，
    在接受用户提交的数据之前验证数据
    """
    name = StringField('your name:', validators=[Required()])
    submit = SubmitField('submit'.encode('utf-8'))


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    """
    db.relationship() 中的 backref 参数向 User 模型中添加一个 role 属性，
    从而定义反向关系。这一属性可替代 role_id 访问 Role 模型，
    此时获取的是模型对象，而不是外键的值
    """
    users = db.relationship('User', backref='role', lazy='dynamic')

    # 返回一个具有可读性的字符串表示模型，可在调试和测试时使用
    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)
manager.add_command('shell', Shell(make_context=make_shell_context))

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


# @celery.task
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_mail(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    # msg.body = u'郭伟匡的个人博客'
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
    # send_async_email.delay(msg)


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        print user
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if app.config['FLASKY_ADMIN']:
                send_mail(app.config['FLASKY_ADMIN'], '新用户',
                          'mail/new_user', user=user)
        else:
            session['known'] = True

        # 把数据存储在用户会话中，在请求之间“记住”数据
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False),
                           current_time=datetime.utcnow())


@app.route('/user/<name>', methods=['POST', 'GET'])
def user(name):
    return render_template('user.html', name=name)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    manager.run()
