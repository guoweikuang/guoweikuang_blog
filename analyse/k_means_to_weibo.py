# coding: utf-8
from numpy import *
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from collections import Counter
from functools import wraps
import time
import os
import shutil
import math
from build_vsm import Tf_IDf
from weibo_text_from_database import especial_using
from sklearn.metrics.pairwise import cosine_similarity
# from classify_to_rand_cent import classify
from redis import Redis


r = Redis(host='localhost', port=6379, db=0)


def save_to_redis(i, text):
    r.lpush(i, text)


def remove_to_redis(name):
    number = len(r.lrange(name, 0, -1))
    for i in range(number):
        r.lpop(name)


def show_redis_data(type_name):
    contents = r.lrange(type_name, 0, -1)
    for content in contents:
        print(content.decode('utf-8'))


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
        print('花费时间:{}'.format(time.time() - start_time))
    return wrpper


def classify_file(labels, filename, rows, zans, comments, times):
    if os.path.exists(filename):
        shutil.rmtree(filename, True)

    os.makedirs(filename)
    for i in set(labels):
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
        name = filename + "\\" + '第%d类.txt' % (i + 1)

        with open(name, 'ab') as f:
            f.write(text + '\t'.encode('utf-8') + zan + '\t'.encode('utf-8')
                    + comment + '\t'.encode('utf-8') + pub_time + '\n'.encode('utf-8'))
            weibo_text = text + '\t'.encode('utf-8') + zan + '\t'.encode('utf-8') \
                         + comment + '\t'.encode('utf-8') + pub_time
            save_to_redis(filename + str(i+1), weibo_text)


class K_Means(object):
    def __init__(self, content, comments, zans, times=None, name='聚类结果1'):
        self.filename = os.path.dirname(os.path.abspath(__file__)) + "\\" + name
        self.rows = content
        self.all_time = times
        self.all_comment = comments
        self.all_zan = zans

    def madir_file(self):
        if not os.path.exists(self.filename):
            os.makedirs(self.filename)

    # 加载数据集文件，没有返回类标号的函数
    def loadDataSet(self, file_name):
        data_mat = []
        openfile = open(file_name)
        for line in openfile.readlines():
            cur_line = line.strip().split('\t')
            float_line = list(map(float, cur_line))
            # if sum(floatLine) != 0:
            data_mat.append(float_line)
        return data_mat

    # def set_rand_cent(self, data_set, k_num):
    #     n = shape(data_set)[1]  # 计算列数
    #     centroids = mat(zeros((k_num, n)))
    #     # all_lines = classify()
    #     for index, value in enumerate(all_lines):
    #         centroids[index, :] = value
    #     print(centroids)

    def rand_cent(self, data_set, k):
        """
        data_set: 数据源，特征提取后的各文本特征权重集合
        k: 人工设定的聚类算法中心
        """
        n = shape(data_set)[1]  # 计算列数
        centroids = mat(zeros((k, n)))

        for j in range(n):
            min_j = min(data_set[:, j])  # 找出矩阵data_set每列最小值
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
        print('开始')
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

    def produce_every_type_contents(self):
        """
        对聚类结果里的几类文本分别进行汇集，为后面的tf-idf算法实现提供数据源
        :return:
        """
        print(self.filename)
        self.madir_file()
        all_type_list = os.listdir(self.filename)
        for every in all_type_list:
            contents = []
            contents_only = []
            every = self.filename + '\\' + every
            with open(every, 'rb') as fp:
                for line in fp.readlines():
                    contents.append(line.decode('utf-8').replace('\n', ''))
                    content, zan, comment, pub_time = line.decode('utf-8').split('\t')
                    contents_only.append(content)
                    # contents.append(content)
            self.get_every_tf_idf(contents, contents_only)

    def get_every_tf_idf(self, contents, contents_only):
        """
        对聚类结果中的每一类分别进行tf-idf计算，并截取前15的特征词，然后进行文本热度计算
        :param contents: 每一类中所有的文本集合
        :return:
        """
        print('===============热点话题热度计算两种公式结果对比============================')
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
        print(count)
        print(comment_count)


def build_every_cluster(basedir_name, file_name):
    rows = []
    zans = []
    comments = []
    times = []
    with open(basedir_name + '\\' + file_name, 'rb') as fp:
        for line in fp.readlines():
            text, zan, comment, pub_time = line.decode('utf-8').replace('\n', '').split('\t')
            rows.append(text)
            zans.append(zan)
            comments.append(comment)
            times.append(pub_time)

    tf = Tf_IDf(rows)
    tf_idf_dict = tf.tf_idf()
    vsm_file = file_name[:-4] + 'vsm'
    tf.build_vsm(vsm_file)

    filename = '{}/{}.txt'.format(vsm_file, vsm_file)
    k = K_Means(rows, comments, zans, times, name=file_name[:-4] + '结果')
    data_set = mat(k.loadDataSet(filename))
    get_centroid, cluster_assment = k.k_means(data_set, 4)
    labels = cluster_assment[:, 0]
    get_labels = [int(i[0]) for i in labels.tolist()]

    # k.classify_file(get_labels, rows)
    # k.produce_every_type_contents()
    # 使用sklearn库实现k-means算法
    cluster = KMeans(init='k-means++', n_clusters=4)
    matrix1 = cluster.fit_predict(data_set)
    classify_file(get_labels, file_name[:-4] + '结果')
    # k.circulate_build_vsm()
    print(get_labels)
    print(matrix1)


def second_cluster(basedir_name='聚类结果1', cluster_one_max=True):
    """ 利用第一次聚类结果，再获取第二次"""
    # basedir_name = '分类结果'
    print(basedir_name)
    file_list = os.listdir(basedir_name)
    if cluster_one_max:
        file_size = [os.path.getsize(basedir_name + '/' + file) for file in file_list]
        file_name = file_list[file_size.index(max(file_size))]
        build_every_cluster(basedir_name, file_name)
    else:
        for file in file_list:
            build_every_cluster(basedir_name, file)


# def main():
#     # time = input('请输入你要抓取的起始日期（2016-11-1）：')
#     # day = input('请输入你要抓取的天数（从起始日期起)：')
#     # rows, all_time, all_comment, all_zan = especial_using(time, int(day))
#     # tf = Tf_IDf(rows, all_comment, all_zan, all_time)
#     # tf_idf_dict = tf.tf_idf()
#     # tf.build_vsm('school1')
#     # print(sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)[:100])
#     # return rows, all_time, all_comment, all_zan

def get_content(basedir_name, file_name):
    rows = []
    zans = []
    comments = []
    times = []
    with open(basedir_name + '\\' + file_name, 'rb') as fp:
        for line in fp.readlines():
            text, zan, comment, pub_time = line.decode('utf-8').replace('\n', '').split('\t')
            rows.append(text)
            zans.append(zan)
            comments.append(comment)
            times.append(pub_time)
    return rows, zans, comments, times


def main():
    file_list = os.listdir('分类结果')
    basedir_name = '分类结果'
    for file_name in file_list:
        contents, zans, comments, times = get_content(basedir_name, file_name)
        tf = Tf_IDf(contents, comments, zans, times)
        tf_idf_dict = tf.tf_idf()
        vsm_file = file_name[:-4] + 'vsm'
        tf.build_vsm(vsm_file)
        file_vsm_name = '{}/{}.txt'.format(vsm_file, vsm_file)
        k_cluster = K_Means(contents, comments, zans, times, name=file_name[:-4] + '结果')
        data_set1 = mat(k_cluster.loadDataSet(file_vsm_name))
        get_centroid, cluster_assments = k_cluster.k_means(data_set1, 4)
        label = cluster_assments[:, 0]
        get_label = [int(i[0]) for i in label.tolist()]
        classify_file(get_label, file_name[:-4] + '结果', contents, zans, comments, times)

        k_cluster.produce_every_type_contents()

        second_file_name = file_name[:-4] + '结果'
        file_list = os.listdir(second_file_name)
        file_size = [os.path.getsize(second_file_name + '/' + file) for file in file_list]
        name = file_list[file_size.index(max(file_size))]
        rows = []
        zans = []
        comments = []
        times = []
        print(second_file_name+'/' + name)
        with open(second_file_name + '/' + name, 'rb') as fp:
            for line in fp.readlines():
                text, zan, comment, pub_time = line.decode('utf-8').replace('\n', '').split('\t')
                rows.append(text)
                zans.append(zan)
                comments.append(comment)
                times.append(pub_time)

        tf = Tf_IDf(rows)
        tf_idf_dict = tf.tf_idf()
        second_vsm_file = file_name[:-4] + '二次vsm'
        tf.build_vsm(second_vsm_file)
        filename = '{}/{}.txt'.format(second_vsm_file, second_vsm_file)
        k = K_Means(rows, comments, zans, times, name='聚类结果1')
        data_set = mat(k.loadDataSet(filename))
        centroid, clusterAssment = k.k_means(data_set, 4)
        labels = clusterAssment[:, 0]
        get_labels = [int(i[0]) for i in labels.tolist()]

        cluster = KMeans(init='k-means++', n_clusters=4)
        matrix1 = cluster.fit_predict(data_set)
        classify_file(get_labels, file_name[:-4] + '二次聚类结果', rows, zans, comments, times)
        # k.circulate_build_vsm()
        print(get_labels)


if __name__ == '__main__':
    """
    使用说明：通过设定时间获取某个时间段的微博文本信息，
    通过tf.tf_idf()获取文本TF_IDF值，再通过tf.build_vsm()建立vsm空间向量模型并存储
    通过K_Means()类的k_means函数实现k_means聚类算法，
    """
    # main()
    print('=============开始=====================')
    type_name = '学校新闻二次聚类结果'
    file_list = os.listdir(type_name)
    file_size = [os.path.getsize(type_name + '/' + file) for file in file_list]
    name = file_list[file_size.index(max(file_size))]
    show_redis_data(type_name + name[1])
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
