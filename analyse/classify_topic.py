# coding=utf-8
import os
import shutil
import jieba
import time
import jieba.analyse
from functools import wraps
from weibo_text_from_database import especial_using1


word_tag = ['买卖交易', '求助', '校园生活', '学校新闻', '网络', '情感']
market_tag = ['评论', '私聊', '价格', '小刀', '有意', '有意者', '出售']
help_tag = ['请问', '有人', '谢谢', '求问']
campus_tag = ['同学', '宿舍', '毕业', '师兄', '图书馆', '考研', '考试', '宿友', '一卡通', '空调']
college_tag = ['学院', '老师', '校区', '学校', '领导', '管理', '奖学金', '助学金']
network_tag = ['锐捷', '网卡', '报修', '二次认证', '断网', '网络中心']
emotion_list = ['喜欢', '女朋友', '男朋友', '女生', '男生', '男票', '分手']
all_tag = [market_tag, help_tag, campus_tag, college_tag, network_tag, emotion_list]

abs_filename = os.path.dirname(os.path.abspath(__file__))
# 加载自己定义的字典
jieba.load_userdict(abs_filename + '\\dict\\dict.txt')
user_stop_word = []
with open(abs_filename + '\\dict\\user_stop_word.txt', 'rb') as f:
    for line in f.readlines():
        user_stop_word.append(line.decode('utf-8').strip('\n'))


def get_rows():
    input_time = input('请输入你要抓取的起始日期（2016-11-1）：')
    input_day = input('请输入你要抓取的天数（从起始日期起)：')
    rows = especial_using1(input_time, input_day)
    return rows


def run_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func(*args, **kwargs)
        print('花费时间为:{}'.format(time.time() - start_time))
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
    def __init__(self, filename):
        self.rows = get_rows()
        self.seg = []
        self.filename = filename

    def save_to_one_file(self, name, contents, comment_num, zan_num, public_time):
        with open(self.filename + '/{}.txt'.format(name), 'ab') as f:
            f.write(contents.encode('utf-8') + '\t'.encode('utf-8') + comment_num.encode('utf-8')
                    + '\t'.encode('utf-8') + zan_num.encode('utf-8') + '\t'.encode('utf-8')
                    + public_time.encode('utf-8') + '\r\n'.encode('utf-8'))

    @run_time
    def classify_to_file(self):
        """
        根据给定的几种类别对文本进行分类
        """
        keyword_path = os.path.dirname(__file__) + '/' + self.filename
        if not os.path.exists(keyword_path):
            os.mkdir(keyword_path)
        else:
            shutil.rmtree(keyword_path)
            # os.remove(keyword_path)
            os.mkdir(keyword_path)
        print('start')
        for row in self.rows:
            comment_num = row[4]
            zan_num = row[5]
            public_time = row[2]
            seg_list = jieba.cut(row[1], cut_all=False)
            self.seg = [word for word in seg_list if word not in user_stop_word]
            seg_copy = jieba.cut(row[1], cut_all=False)
            content = ' '.join(seg_copy).encode('utf-8')
            for tag, name in zip(all_tag, word_tag):
                if len(set(tag) & set(self.seg)) != 0:
                    self.save_to_one_file(name, row[1], comment_num, zan_num, public_time)


if __name__ == '__main__':
    classify_topic = Classify('分类结果')
    classify_topic.classify_to_file()
