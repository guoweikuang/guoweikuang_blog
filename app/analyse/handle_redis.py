# coding=utf-8
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
    new_contents = []
    for content in contents:
        # print(content.decode('utf-8'))
        new_contents.append(content.decode('utf-8'))
    return new_contents