# coding=utf-8
import os
import shutil
import jieba
import time
import jieba.analyse
from functools import wraps
from weibo_text_from_database import especial_using1
from handle_redis import remove_to_redis, save_to_redis, r


word_tag = [u'买卖交易', u'求助', u'校园生活', u'学校新闻', u'网络', u'情感']
market_tag = [u'评论', u'私聊', u'价格', u'小刀', u'有意', u'有意者', u'出售']
help_tag = [u'请问', u'有人', u'谢谢', u'求问']
campus_tag = [u'同学', u'宿舍', u'毕业', u'师兄', u'图书馆', u'考研', u'考试', u'宿友', u'一卡通', u'空调']
college_tag = [u'学院', u'老师', u'校区', u'学校', u'领导', u'管理', u'奖学金', u'助学金']
network_tag = [u'锐捷', u'网卡', u'报修', u'二次认证', u'断网', u'网络中心']
emotion_list = [u'喜欢', u'女朋友', u'男朋友', u'女生', u'男生', u'男票', u'分手']
all_tag = [market_tag, help_tag, campus_tag, college_tag, network_tag, emotion_list]

abs_filename = os.path.dirname(os.path.abspath(__file__))
# 加载自己定义的字典
jieba.load_userdict(abs_filename + '\\dict\\dict.txt')
user_stop_word = []
with open(abs_filename + '\\dict\\user_stop_word.txt', 'rb') as f:
    for line in f.readlines():
        user_stop_word.append(line.decode('utf-8').strip('\n'))


def get_rows(time_end, day):
    # input_time = raw_input(u'请输入你要抓取的起始日期（2016-11-1）：')
    # input_day = input(u'请输入你要抓取的天数（从起始日期起)：')
    rows = especial_using1(time_end, day)
    return rows


def run_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func(*args, **kwargs)
        print(u'花费时间为:{}'.format(time.time() - start_time))

    return wrapper


def save_to_file(path, name, contents):
    if not os.path.exists(path):
        path = path + '/' + '{}.txt'.format(name)
        os.mkdir(path)
        with open(path, 'wb') as fp:
            fp.write(contents)
            fp.close()
    else:
        path = path + "/" + '{}.txt'.format(name)
        with open(path, 'wb') as fp:
            fp.write(contents)
            fp.close()


class Classify(object):
    def __init__(self, filename, time_end="2016-11-1", day=10):
        self.rows = get_rows(time_end, day)
        self.seg = []
        self.filename = filename

    def save_to_one_file(self, name, contents, comment_num, zan_num, public_time):
        # print(self.filename + u'\\{}.txt'.format(name))
        with open(self.filename + u'\\{}.txt'.format(name), 'ab') as f:
            f.write(contents.encode('utf-8') + '\t'.encode('utf-8') + comment_num.encode('utf-8')
                    + '\t'.encode('utf-8') + zan_num.encode('utf-8') + '\t'.encode('utf-8')
                    + public_time.encode('utf-8') + '\r\n'.encode('utf-8'))

    @run_time
    def classify_to_file(self):
        """
        根据给定的几种类别对文本进行分类
        """
        for tag in word_tag:
            file_name = self.filename + ":" + tag
            if r.lrange(file_name, 0, -1):
                remove_to_redis(file_name)

        for row in self.rows:
            comment_num = row[4]
            zan_num = row[5]
            public_time = row[2]
            seg_list = jieba.cut(row[1], cut_all=False)
            self.seg = [word.encode('utf-8').decode('utf-8') for word in seg_list if word not in user_stop_word]
            # print repr(self.seg).decode('raw_unicode_escape')
            seg_copy = jieba.cut(row[1], cut_all=False)
            content = ' '.join(seg_copy).encode('utf-8')
            for tag, name in zip(all_tag, word_tag):
                if len(set(tag) & set(self.seg)) != 0:
                    content = row[1] + '\t' + comment_num + '\t' + zan_num + '\t' + public_time
                    # print(content)
                    save_to_redis(self.filename + ":" + name, content)
                    # print u'存入{}'.format(self.filename + ':' + name)
                    # r.lpush(self.filename + ':' + name, content)
                    # self.save_to_one_file(name, row[1], comment_num, zan_num, public_time)


if __name__ == '__main__':
    classify_topic = Classify(u'分类结果')
    classify_topic.classify_to_file()
    print(abs_filename)
