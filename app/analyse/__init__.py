# coding=utf-8
from k_means_to_weibo import show_redis_data

# 设置默认日志处理方式，避免“未找到处理方法”的警告。
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())