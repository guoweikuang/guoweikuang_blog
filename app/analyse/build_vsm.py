# coding: utf-8
import math
import jieba
from collections import Counter
from itertools import combinations
import nltk
from weibo_text_from_database import especial_using
import os
from handle_redis import save_to_redis, remove_to_redis, r


abs_filename = os.path.dirname(os.path.abspath(__file__))


# 加载自己定义的字典
jieba.load_userdict(abs_filename + '\\dict\\dict.txt')
user_stop_word = []
with open(abs_filename + '\\dict\\user_stop_word.txt', 'rb') as f:
    for line in f.readlines():
        user_stop_word.append(line.decode('utf-8').strip('\n'))


class Tf_IDf(object):
    def __init__(self, rows, all_comment=None, all_zan=None, all_time=None):
        self.rows = rows
        self.all_time = all_time
        self.all_comment = all_comment
        self.all_zan = all_zan
        self.temp_contents = []
        self.total_seglist = []
        self.tf_dict = {}
        self.tf_idf_dict = {}
        self.score = []

    @staticmethod
    def get_seg_content(rows):
        temp_seglist = []
        for row in rows:
            if len(row) < 10:
                continue
            seg_list = jieba.cut(row, cut_all=False)
            temp_seglist.append(' '.join(set(seg_list) - set(user_stop_word)))   # 集合差，去除停用词
        return temp_seglist

    def get_total_keywords(self):
        """
        统计分词去除停用词和长度小于2后的关键词数量
        contents: 数据源，即所有的文本
        return: 返回统计后所有关键字的字典
        """
        temp_seglist = self.get_seg_content(self.rows)
        total = ' '.join(temp_seglist)
        # 把所有关键字集合在一起，再统计每个关键词出现次数
        self.total_seglist = [word for word in total.split() if len(word) >= 2]
        # 使用collections库来统计关键字个数
        # print repr(self.total_seglist[:100]).decode('raw_unicode_escape')
        count = Counter()
        for seg in self.total_seglist:
            count[seg] = count.get(seg, 0) + 1
        # print(sorted(count.items(), key=lambda d: d[1], reverse=True)[:50])
        content_count = sorted(count.items(), key=lambda d: d[1], reverse=True)[:50]
        print repr(content_count).decode('raw_unicode_escape')
        # save_to_logging(content_count)
        return count

    def get_tf(self):
        """
        计算所有关键字的tf值
        return： 所有关键字的tf字典
        """
        count = self.get_total_keywords()
        max_number = len(count)

        for name, value in count.items():
            if value > 1:
                self.tf_dict[name] = float(float(value) / max_number)
        # print self.tf_dict

    def tf_idf(self):
        """
        计算所有关键字的tf-idf权重
        :return: 所有关键字的tf-idf权重字典
        """
        self.get_tf()
        for name, value in self.tf_dict.items():
            self.tf_idf_dict[name] = float(value * float(math.log(len(self.tf_dict) / (value + 1))))
        return self.tf_idf_dict

    @staticmethod
    def get_distance(two_vector, content):
        """
        实现文本相似度比较算法
        :param two_vector: 两组需要进行比较的文本向量化的列表
        :return:
        """
        total_number = sum([i * j for i, j in zip(two_vector[0], two_vector[1])])
        number1 = math.sqrt(sum([i ** 2 for i in two_vector[0]]))
        number2 = math.sqrt(sum([i ** 2 for i in two_vector[1]]))
        if number1 * number2 == 0:
            result = 0.0
        else:
            result = total_number / number1 * number2
        # print('余弦相似度算法 :  {}'.format(result))
        return result

    def similarity_two_text(self, weights, contents):
        # print repr(contents[:100]).decode('raw_unicode_escape')
        two_content = combinations(weights[:200], 2)
        text = combinations(contents[:200], 2)
        all_results = []
        all_contents = []
        for words, content in zip(two_content, text):
            # print(content)
            # number = cosine_similarity(words[0], words[1])
            # result = nltk.cluster.cosine_distance(words[0], words[1])
            # print('nltk相似度算法 :  {}'.format(number))
            result = self.get_distance(words, content)
            all_results.append(result)
            all_contents.append(content)
        # print(all_results)
        top = sorted(all_results, reverse=True)[:10]
        top_contents = [all_results.index(text) for text in top]
        top_contents = [all_contents[index] for index in top_contents]
        top_resulst = set()
        for i, j in zip(top_contents, top):
            for text in i:
                top_resulst.add(text)
            print repr(i).decode('raw_unicode_escape')
            print repr(j).decode('raw_unicode_escape')
        print repr(top_resulst).decode('raw_unicode_escape')

    @staticmethod
    def handle_filename(filename):
        name = filename + '.txt'
        abs_filename = os.path.dirname(os.path.abspath(__file__)) + '\\%s\\' % filename + name
        print(abs_filename)
        if not os.path.exists(filename):
            os.mkdir(filename)
        if os.path.exists(abs_filename):
            os.remove(abs_filename)
        return abs_filename

    def build_vsm(self, filename):
        """
        构建向量化空间模型，一、进行特征提取，目的是减少向量化维度
        二、进行文本相似度比较，两种实现方法。
        :param contents:
        :return:
        """
        if r.lrange(filename, 0, -1):
            remove_to_redis(filename)
        tf_idf_dict = self.tf_idf()
        print(u'总关键字个数: %s' % str(len(tf_idf_dict)))
        if len(tf_idf_dict) < 100:
            tf_idf_list = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)[:50]
        else:
            tf_idf_list = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)[:100]
        keyword_list = [word for (word, value) in tf_idf_list]
        removed_words = []
        contents = self.rows
        for row in contents:
            seg_list = jieba.cut(row, cut_all=False)
            seg_list = [seg for seg in seg_list if len(seg) >= 2]
            removed_words.append(' '.join(set(seg_list) - set(user_stop_word)))
        two_score = []
        for words in removed_words:
            score = [0.0 for _ in tf_idf_list]
            for word in words.split():
                if word in keyword_list:
                    number = tf_idf_dict.get(word, 0.0)
                    index = keyword_list.index(word)
                    score.pop(index)
                    score.insert(index, number)
            number = [str(i) for i in score]
            guo = '\t'.join(number)
            save_to_redis(filename, guo.encode('utf-8'))
            two_score.append(score)
        # self.similarity_two_text(two_score, contents)


if __name__ == '__main__':
    start_time = input(u"请输入你要抓取的起始日期（2016-11-1）：")
    day = raw_input(u"请输入你要抓取的天数（从起始日期起)：")
    database_name = input(u'请输入你要获取数据的数据库：')
    rows, all_time, all_comment, all_zan = especial_using(start_time, int(day), database_name)
    tf = Tf_IDf(rows, all_comment, all_zan, all_time)
    tf_idf_dict = tf.tf_idf()
    print(tf_idf_dict)
    tf.build_vsm('test')
