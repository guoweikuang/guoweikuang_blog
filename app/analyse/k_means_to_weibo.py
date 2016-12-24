# coding: utf-8
from sklearn.cluster import KMeans
from collections import Counter
from functools import wraps
import time
import os
import shutil
import math
from build_vsm import Tf_IDf
from classify_topic import Classify
from redis import Redis
from set_logging import save_to_logging
from classify_topic import word_tag
from handle_redis import save_to_redis, remove_to_redis, show_redis_data, r
from numpy import *
import operator


# 加载数据集文件，没有返回类标号的函数
def loadDataSet(file_name):
    data_mat = []
    openfile = open(file_name)
    for line in openfile.readlines():
        cur_line = line.strip().split('\t')
        float_line = list(map(float, cur_line))
        # if sum(floatLine) != 0:
        data_mat.append(float_line)
    return data_mat


def run_time(func):
    @wraps(func)
    def wrpper(*args, **kwargs):
        start_time = time.time()
        func(*args, **kwargs)
        print(u'花费时间:{}'.format(time.time() - start_time))
    return wrpper


def classify_file(labels, filename, rows, zans, comments, times):
    for i in set(labels):
        # print u'删除'
        if r.lrange(filename + str(i + 1), 0, -1):
            remove_to_redis(filename + str(i + 1))

    for i, text, zan, comment, pub_time in zip(labels, rows, zans, comments, times):
        text = text.encode('utf-8')
        if not zan:
            zan = '0'
        if not comment:
            comment = '0'
        zan = zan.encode('utf-8')
        comment = comment.encode('utf-8')
        pub_time = pub_time.encode('utf-8')

        weibo_text = text + '\t'.encode('utf-8') + zan + '\t'.encode('utf-8') \
                     + comment + '\t'.encode('utf-8') + pub_time
        save_to_redis(filename + str(i+1), weibo_text)


class K_Means(object):
    def __init__(self, content, comments, zans, times=None, name=u'聚类结果1'):
        self.filename = os.path.dirname(os.path.abspath(__file__)) + "\\" + name
        self.rows = content
        self.all_time = times
        self.all_comment = comments
        self.all_zan = zans
        self.file_name = name

    @staticmethod
    def load_data_set(vsm_name):
        data_mat = []
        for line in r.lrange(vsm_name, 0, -1):
            cur_line = line.strip().split('\t')
            float_line = list(map(float, cur_line))
            data_mat.append(float_line)
        return data_mat

    @staticmethod
    def rand_cent(data_set, k):
        """
        data_set: 数据源，特征提取后的各文本特征权重集合
        k: 人工设定的聚类算法中心
        """
        n = shape(data_set)[1]  # 计算列数
        centroids = mat(zeros((k, n)))

        for j in range(n):
            min_j = min(data_set[:, j])  # 找出矩阵data_set每列最小值
            # print(min(data_set[:, j]))

            range_J = float(max(data_set[:, j]) - min_j)  # 计算第j列最大值和最小值的差
            # 赋予一个随机质心， 它的值在整个数据集的边界之内
            # random.rand(k,1)构建k行一列，每行代表二维的质心坐标
            centroids[:, j] = min_j + range_J * random.rand(k, 1)
        return centroids  # 返回一个随机的质心矩阵

    def person(self, vector1, vector2):
        sum1 = sum(vector1)
        sum2 = sum(vector2)

        sum1_sq = sum([pow(v, 2) for v in vector1])
        sum2_sq = sum([pow(v, 2) for v in vector2])

        p_sum = sum([vector1[i] * vector2[i] for i in range(vector1)])

        num = p_sum - sum1 * sum2 / len(vector1)
        den = sqrt((sum1_sq - pow(sum1, 2) / len(vector1)) * (sum2_sq - pow(sum2, 2)
                                                        / len(vector1)))
        if den == 0:
            return 0

        return 1.0 - num / den

    def distEclud(self, vector1, vector2):
        """
        返回两个文本之间的距离
        """
        return sqrt(sum(power(vector1 - vector2, 2)))

    # @run_time
    def k_means(self, data_set, k, distE=person, createCent=rand_cent):
        """
        data_set: 数据集
        data_set = [[1.658985, 4.285136], [-3.453687, 3.424321],
                [4.838138, -1.151539],[-5.379713, -3.362104],
                [0.972564, 2.924086]]
        k: 设置聚类簇数K值
        distE：函数, 计算数据点的欧式距离
        例如：vector1 = [[ 1.658985  4.285136]]
          vector2 = [[-3.453687  3.424321]]
        欧氏距离：distance = distE(vector1, vector2)
        createCent: 函数， 返回一个随机的质点矩阵
        """
        m = shape(data_set)[0]  # 获取行数
        cluster_assent = mat(zeros((m, 2)))  # 初始化一个矩阵， 用来记录簇索引和存储误差平方和(指当前点到簇质点的距离）
        centroids = self.rand_cent(data_set, k)  # 随机生成一个质心矩阵蔟
        # print(centroids)
        cluster_changed = True
        print(u'开始')
        while cluster_changed:
            cluster_changed = False
            for i in range(m):  # 对每个数据点寻找最近的质心
                min_dist = inf  # 设置最小距离为正无穷大
                min_index = -1
                for j in range(k):  # 遍历质心簇，寻找最近质心
                    dist__j = self.distEclud(centroids[j, :], data_set[i, :])
                    if dist__j < min_dist:
                        min_dist = dist__j
                        min_index = j
                if cluster_assent[i, 0] != min_index:
                    cluster_changed = True
                cluster_assent[i, :] = min_index, min_dist ** 2    # 平方的意义在于判断聚类结果的好坏
            # print(centroids)
            for cent in range(k):  # 更新质心，将每个簇中的点的均值作为质心
                index_all = cluster_assent[:, 0].A  # 取出样本所属簇的索引值
                value = nonzero(index_all == cent)  # 取出所有属于第cent个簇的索引值
                sample_in_clust = data_set[value[0]]  # 取出属于第I个簇的所有样本点
                centroids[cent, :] = mean(sample_in_clust, axis=0)
        return centroids, cluster_assent

    def produce_every_type_contents(self, labels):
        """
        对聚类结果里的几类文本分别进行汇集，为后面的tf-idf算法实现提供数据源
        :return:
        """

        save_to_logging(self.filename)
        labels = set(labels)
        for index in labels:
            contents = []
            contents_only = []
            for line in r.lrange(self.file_name + str(index + 1), 0, -1):
                contents.append(line.decode('utf-8'))
                content, zan, comment, pub_time = line.decode('utf-8').split('\t')
                contents_only.append(content)
            self.get_every_tf_idf(contents, contents_only)

    def get_every_tf_idf(self, contents, contents_only):
        """
        对聚类结果中的每一类分别进行tf-idf计算，并截取前15的特征词，然后进行文本热度计算
        :param contents: 每一类中所有的文本集合
        :return:
        """
        print(u'===============热点话题热度计算两种公式结果对比============================')
        tf = Tf_IDf(contents_only)
        tf_idf_dict = tf.tf_idf()
        count = Counter()
        comment_count = Counter()
        total = 0
        no_similar_count = Counter()
        for content in contents:
            content, zan, comment, pub_time = content.split('\t')
            zan = float(zan)
            comment = float(comment)
            total += float(math.sqrt(zan) + comment)
        print(total)
        tf_idf_dict = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)[:15]
        sum = 0
        for name, value in tf_idf_dict:
            for content in contents:
                content, zan, comment, pub_time = content.split('\t')
                zan = float(zan)
                comment = float(comment)
                if name in content:
                    count[name] += float(comment * value)
                    comment_count[name] += float(comment + math.sqrt(zan))
                    sum += float(comment + math.sqrt(zan))

        print(sum)
        count = sorted(dict(count).items(), key=lambda d: d[1], reverse=True)
        comment_count = sorted(dict(comment_count).items(), key=lambda d: d[1], reverse=True)
        print repr(count).decode('raw_unicode_escape')
        print repr(comment_count).decode('raw_unicode_escape')


def get_content(basedir_name, file_name):
    rows = []
    zans = []
    comments = []
    times = []
    for text in r.lrange(basedir_name + ":" + file_name, 0, -1):
        text, zan, comment, pub_time = text.decode('utf-8').split('\t')
        rows.append(text)
        zans.append(zan)
        comments.append(comment)
        times.append(pub_time)

    return rows, zans, comments, times


def second_cluster(file_name, label, k_num=3):
    second_file_name = file_name + u'结果'
    size_list = {}
    for index in set(label):
        size = len(r.lrange(second_file_name + str(index + 1), 0, -1))
        size_list[second_file_name + str(index+1)] = size
    print repr(size_list).decode('raw_unicode_escape')
    max_size_name = max(size_list.iteritems(), key=operator.itemgetter(1))[0]
    if size_list[max_size_name] > 40:
        rows = []
        zans = []
        comments = []
        times = []

        for line in r.lrange(max_size_name, 0, -1):
            text, zan, comment, pub_time = line.decode('utf-8').split('\t')
            rows.append(text)
            zans.append(zan)
            comments.append(comment)
            times.append(pub_time)

        tf = Tf_IDf(rows)
        tf_idf_dict = tf.tf_idf()
        tf_idf_dict = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)
        print repr(tf_idf_dict).decode('raw_unicode_escape')
        second_vsm_file = file_name + u'二次vsm'
        tf.build_vsm(second_vsm_file)

        k = K_Means(rows, comments, zans, times, name=u'聚类结果1')
        data_set = mat(k.load_data_set(second_vsm_file))
        centroid, clusterAssment = k.k_means(data_set, k_num)
        labels = clusterAssment[:, 0]
        get_labels = [int(i[0]) for i in labels.tolist()]

        cluster = KMeans(init='k-means++', n_clusters=k_num)
        matrix1 = cluster.fit_predict(data_set)
        print list(matrix1)
        classify_file(get_labels, file_name + u'二次聚类结果', rows, zans, comments, times)
        save_to_logging(get_labels)
    else:
        print u'不需要进行二次聚类'


def main(time_end, day):
    classify_topic = Classify(u'分类结果', time_end, day)
    classify_topic.classify_to_file()
    basedir_name = u'分类结果'
    for keyword in word_tag:
        contents, zans, comments, times = get_content(basedir_name, keyword)
        tf = Tf_IDf(contents, comments, zans, times)
        tf_idf_dict = tf.tf_idf()
        tf_idf_dict = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)

        vsm_file = keyword + 'vsm'
        tf.build_vsm(vsm_file)
        # vsm_file = u'{}/{}.txt'.format(vsm_file, vsm_file)
        k_cluster = K_Means(contents, comments, zans, times, name=keyword + u'结果')
        data_set1 = mat(k_cluster.load_data_set(vsm_file))
        # print data_set1
        get_centroid, cluster_assments = k_cluster.k_means(data_set1, 4)
        label = cluster_assments[:, 0]
        get_label = [int(i[0]) for i in label.tolist()]
        classify_file(get_label, keyword + u'结果', contents, zans, comments, times)

        k_cluster.produce_every_type_contents(get_label)

        print(u'=============二次聚类=====================')
        second_cluster(keyword, get_label)

    # for file_name in file_list:
    #     contents, zans, comments, times = get_content(basedir_name, file_name)
    #     tf = Tf_IDf(contents, comments, zans, times)
    #     tf_idf_dict = tf.tf_idf()
    #     tf_idf_dict = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)
    #     # print repr(tf_idf_dict).decode('raw_unicode_escape')
    #     vsm_file = file_name[:-4] + 'vsm'
    #     tf.build_vsm(vsm_file)
    #     file_vsm_name = u'{}/{}.txt'.format(vsm_file, vsm_file)
    #     k_cluster = K_Means(contents, comments, zans, times, name=file_name[:-4] + u'结果')
    #     data_set1 = mat(k_cluster.loadDataSet(file_vsm_name))
    #     get_centroid, cluster_assments = k_cluster.k_means(data_set1, 4)
    #     label = cluster_assments[:, 0]
    #     get_label = [int(i[0]) for i in label.tolist()]
    #     classify_file(get_label, file_name[:-4] + u'结果', contents, zans, comments, times)
    #
    #     k_cluster.produce_every_type_contents()
    #
    #     second_cluster(file_name)
        # second_file_name = file_name[:-4] + u'结果'
        # file_list = os.listdir(second_file_name)
        # file_size = [os.path.getsize(second_file_name + '/' + file) for file in file_list]
        # name = file_list[file_size.index(max(file_size))]
        # rows = []
        # zans = []
        # comments = []
        # times = []
        # # print(second_file_name+'/' + name)
        # save_to_logging(second_file_name + '/' + name)
        # with open(second_file_name + '/' + name, 'rb') as fp:
        #     for line in fp.readlines():
        #         text, zan, comment, pub_time = line.decode('utf-8').replace('\n', '').split('\t')
        #         rows.append(text)
        #         zans.append(zan)
        #         comments.append(comment)
        #         times.append(pub_time)
        #
        # tf = Tf_IDf(rows)
        # tf_idf_dict = tf.tf_idf()
        # second_vsm_file = file_name[:-4] + u'二次vsm'
        # tf.build_vsm(second_vsm_file)
        # filename = u'{}/{}.txt'.format(second_vsm_file, second_vsm_file)
        # k = K_Means(rows, comments, zans, times, name=u'聚类结果1')
        # data_set = mat(k.loadDataSet(filename))
        # centroid, clusterAssment = k.k_means(data_set, 4)
        # labels = clusterAssment[:, 0]
        # get_labels = [int(i[0]) for i in labels.tolist()]
        #
        # cluster = KMeans(init='k-means++', n_clusters=4)
        # matrix1 = cluster.fit_predict(data_set)
        # classify_file(get_labels, file_name[:-4] + u'二次聚类结果', rows, zans, comments, times)
        # # k.circulate_build_vsm()
        # print(get_labels)


def main1(time_end, day):
    # classify_topic = Classify(u'分类结果', time_end, day)
    # classify_topic.classify_to_file()
    main(time_end, day)
    # print(u'=============开始=====================')
    # type_name = u'学校新闻二次聚类结果'
    # file_list = os.listdir(type_name)
    # file_size = [os.path.getsize(type_name + '/' + file) for file in file_list]
    # name = file_list[file_size.index(max(file_size))]
    # show_redis_data(type_name + name[1])

if __name__ == '__main__':
    """
    使用说明：通过设定时间获取某个时间段的微博文本信息，
    通过tf.tf_idf()获取文本TF_IDF值，再通过tf.build_vsm()建立vsm空间向量模型并存储
    通过K_Means()类的k_means函数实现k_means聚类算法，
    """
    start = raw_input(u'请输入你要抓取的起始日期（2016-11-1）：')
    day = input(u'请输入你要抓取的天数（从起始日期起)：')
    main(start, day)
    print(u'=============开始=====================')
    type_name = u'学校新闻二次聚类结果'
    size_list = {}
    for index in range(4):
        size = len(r.lrange(type_name + str(index + 1), 0, -1))
        # print type_name + str(index)
        size_list[type_name + str(index+1)] = size
    print repr(size_list).decode('raw_unicode_escape')
    max_size_name = max(size_list.iteritems(), key=operator.itemgetter(1))[0]
    print max_size_name
    show_redis_data(max_size_name)


    # rows, all_time, all_comment, all_zan = main()
    # print('================所有文本内容====================')
    # k = K_Means(rows, all_comment, all_zan, all_time)
    #
    # filename = 'school1\\school1.txt'
    # data_set = mat(k.loadDataSet(filename))
    #
    # print('===========聚类前的vsm=================')
    # centroid, cluster_assment = k.k_means(data_set, 5, k.person)
    # print(sum(cluster_assment))
    # labels = cluster_assment[:, 0]
    # get_labels = [int(i[0]) for i in labels.tolist()]
    # print('=================对聚类结果进行分类存入文档=====================')
    # files = '聚类结果分类'
    # classify_file(get_labels, files, rows, all_zan, all_comment, all_time)
    #
    # print('===================对聚类的几种类型分别重新进行tf_idf计算==========================')
    # # k.produce_every_type_contents()
    # # k.circulate_build_vsm()
    # # k.show_result(data_set)
    #
    # print('===================第二次对最大的聚类结果重新聚类=============================')
    # # second_cluster('聚类结果1', True)
    #
    # filelist = os.listdir('分类结果')
    # for files in filelist:
    #     second_cluster('分类结果', True)

    # basedir_name = '聚类结果1'
    # file_list = os.listdir(basedir_name)
    # file_size = [os.path.getsize(basedir_name + '/' + file) for file in file_list]
    # file_name = file_list[file_size.index(max(file_size))]
    # rows = []
    # zans = []
    # comments = []
    #
    # times = []
    # print(basedir_name+'/'+file_name)
    # with open(basedir_name + '/' + file_name, 'rb') as fp:
    #     for line in fp.readlines():
    #         text, zan, comment, pub_time = line.decode('utf-8').replace('\n', '').split('\t')
    #         rows.append(text)
    #         zans.append(zan)
    #         comments.append(comment)
    #         times.append(pub_time)
    #
    # tf = Tf_IDf(rows)
    # tf_idf_dict = tf.tf_idf()
    # tf.build_vsm('number1')
    # filename = 'number1/number1.txt'
    # k = K_Means(rows, comments, zans, times, name='聚类结果1')
    # data_set = mat(k.loadDataSet(filename))
    # centroid, clusterAssment = k.k_means(data_set, 4)
    # labels = clusterAssment[:, 0]
    # get_labels = [int(i[0]) for i in labels.tolist()]
    #
    # cluster = KMeans(init='k-means++', n_clusters=4)
    # matrix1 = cluster.fit_predict(data_set)
    # classify_file(get_labels, '二次聚类', rows, zans, comments, times)
    # # k.circulate_build_vsm()
    # print(get_labels)
