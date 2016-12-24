# coding=utf-8
# coding: utf-8
from datetime import datetime
from flask import render_template, session, redirect, \
    url_for, current_app, abort, flash, request, make_response
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, ShowDataForm
from .. import db
from ..models import User, Role, Post, Permission, Comment
from ..email import send_mail
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required
from ..analyse.k_means_to_weibo import main1
from ..analyse.handle_redis import r, show_redis_data
import operator
import os


@main.route('/show_data', methods=['GET', 'POST'])
def show_data():
    form = ShowDataForm()
    word_tag = [u'买卖交易', u'求助', u'校园生活', u'学校新闻', u'网络', u'情感']
    word_tag = [name + u'二次聚类结果' for name in word_tag]
    type_name = u'学校新闻二次聚类结果'
    category = request.values.get("category")

    if category:
        new_word_tag = []
        type_name = category
        new_word_tag.append(category)
        for word in word_tag:
            if word != category:
                new_word_tag.append(word)
    else:
        new_word_tag = word_tag

    size_list = {}
    for index in range(10):
        size = len(r.lrange(type_name + str(index + 1), 0, -1))
        if size > 0:
            size_list[type_name + str(index+1)] = size
    max_size_name = max(size_list.iteritems(), key=operator.itemgetter(1))[0]
    all_second_cluster = sorted(size_list.iteritems(), key=operator.itemgetter(1), reverse=True)
    category_list = sorted(size_list.keys())

    cate = request.values.get("name")
    if cate:
        new_category_list = []
        contents = show_redis_data(cate)
        new_category_list.append(cate)
        for i in category_list:
            if i != cate:
                new_category_list.append(i)
    else:

        contents = show_redis_data(max_size_name)
        new_category_list = category_list
    print repr(category_list).decode('raw_unicode_escape')
    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        main1(start_time, end_time)
        return redirect(url_for('.show_data'))

    sub_content = []
    for index, content in enumerate(contents):
        text, zans, comments, pub_time = content.split('\t')
        sub_content.append([index, text, zans, comments, pub_time])
    contents = sub_content
    # category_list = []
    return render_template('show_data.html', form=form, contents=contents,
                           category_list=new_category_list, word_tag=new_word_tag)


@main.route('/show_data/<int:id>', methods=['GET', 'POST'])
def show_every_data(id):
    form = ShowDataForm()
    type_name = u'学校新闻二次聚类结果'
    file_name = type_name + str(id)

    contents = show_redis_data(file_name)
    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        main1(start_time, end_time)
        return redirect(url_for('.show_every_data', id=id))

    sub_content = []
    for index, content in enumerate(contents):
        text, zans, comments, pub_time = content.split('\t')
        sub_content.append([index, text, zans, comments, pub_time])
    contents = sub_content
    return render_template('show_data.html', form=form, contents=contents)


@main.route('/show_picture')
def show_picture():
    basedir_name = os.path.dirname(os.path.abspath(__file__))
    print(basedir_name)
    basedir_name = 'D:\\project\\weibo_showing\\app\\static\\images'
    images_list = os.listdir(basedir_name)
    word_tag = [u'买卖交易', u'求助', u'校园生活', u'学校新闻', u'网络', u'情感']
    category = request.values.get("category")
    if category:
        new_category_list = []
        index = word_tag.index(category)
        new_category_list.append(category)
        for word in word_tag:
            if word != category:
                new_category_list.append(word)
    else:
        new_category_list = word_tag
        index = 3

    return render_template('show_picture.html', images=images_list, categorys=new_category_list, categorys_flag=index)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash(u'你的个人主页被更新了.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        flash(u'个人主页已经更新！')
        return redirect(url_for('.user', username=current_user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination)


@main.route('/user/<username>', methods=['GET', 'POST'])
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash(u'你的评论已经被发布！')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) / \
               current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False
    )
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash(u'你的文章已经更新！')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form, post=post)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'无效的用户！')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash(u'你已经关注了该用户！')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash(u'你现在关注了%s' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'无效的用户！')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash(u'你已经取消关注了该用户！')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash(u'你现在取消关注了 %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'无效的用户！')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'无效的用户！')
        redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title='Followed by',
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=24 * 60 * 60 * 30)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=24 * 60 * 60 * 30)
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))





