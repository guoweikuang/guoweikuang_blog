# coding=utf-8
import os
import jieba
from build_vsm import Tf_IDf

file_list = os.listdir(u'分类结果')
print(file_list)


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


for file in file_list:
    badir_name = u'分类结果'
    contents, zans, comments, times = get_content(badir_name, file)
    tf = Tf_IDf(contents, comments, zans, times)
    tf_idf_dict = tf.tf_idf()
    show = sorted(tf_idf_dict.items(), key=lambda d: d[1], reverse=True)
    # for i in show[:10]:
    #     print i
    for content in contents:
        seg_list = jieba.cut(content, cut_all=False)

