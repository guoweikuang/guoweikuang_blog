# coding: utf-8
import pymysql
from datetime import datetime
import os

print(os.path.dirname(os.path.abspath(__file__)))


def use_mysql():
    conn = pymysql.connect(host='localhost',
                           user='root',
                           passwd='gwk2014081029',
                           db='mysql',
                           charset='utf8')
    cur = conn.cursor()
    cur.execute('use weibo')
    return conn, cur


def especial_using(time_end, day=5, database='content'):
    """
     函数目的:为提取近期微博文本进行热点话题发现提供元数据
     start_time: 提取从某段时间开始的文本
     end_time: 提取到某段时间结束的文本，和start_time设置一个时间段
    """
    conn, cur = use_mysql()
    sql = 'select * from {};'.format(database)
    cur.execute(sql)
    rows = cur.fetchall()
    contents = []       # day时间内所有微博文本的内容
    all_times = []      # day时间内所有微博文本的时间
    all_comment = []    # day时间内所有微博文本的评论数
    all_zan = []        # day时间内所有微博文本的点赞数
    
    for row in rows:
        times = row[2].encode('utf-8')
        times = times.split()
        start_time = times[0].decode('utf-8').split('-')
        now_time = time_end.split('-')
        start_time = datetime(int(start_time[0]), int(start_time[1]), int(start_time[2]))
        end_time = datetime(int(now_time[0]), int(now_time[1]), int(now_time[2]))
        time_sub = (end_time - start_time).days
        if 0 <= time_sub <= day and len(row[1]) >= 10:
            contents.append(row[1])
            all_times.append(row[2])
            all_comment.append(row[4])
            all_zan.append(row[5])
    print(len(contents))
    return contents, all_times, all_comment, all_zan


def especial_using1(time_end, day=5, database='content'):
    conn, cur = use_mysql()
    sql = 'select * from {};'.format(database)
    cur.execute(sql)
    rows = cur.fetchall()
    content = []

    for row in rows:
        times = row[2].encode('utf-8')
        times = times.split()
        start_time = times[0].decode('utf-8').split('-')
        now_time = time_end.split('-')
        start_time = datetime(int(start_time[0]), int(start_time[1]), int(start_time[2]))
        end_time = datetime(int(now_time[0]), int(now_time[1]), int(now_time[2]))
        time_sub = (end_time - start_time).days

        if 0 <= time_sub <= int(day) and len(row[1]) >= 10:
            content.append(row)
    return content

