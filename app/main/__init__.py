# coding=utf-8
from flask import Blueprint

"""
实例化一个Blueprint类对象来创建蓝本，
构造函数需要传入两个参数，蓝本的名字和蓝本所在的包或模块
"""
main = Blueprint('main', __name__)

# 在这里导入为了避免循环导入依赖
from . import views, errors
from ..models import Permission


@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)