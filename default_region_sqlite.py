# -*- coding: UTF-8 -*-
import datetime
import os
import uuid

import sqlite3


def create_db_client():
    db = sqlite3.connect('/app/data/db.sqlite3')
    return db


def make_uuid(key=None):
    random_uuid = str(uuid.uuid4()).replace('-', '')
    return random_uuid


def get_region_id():
    return make_uuid()


def get_url():
    return os.environ.get('REGION_URL')


def get_wsurl():
    return os.environ.get('REGION_WS_URL')


def get_http_domain():
    return os.environ.get('REGION_HTTP_DOMAIN')


def get_tcp_domain():
    return os.environ.get('REGION_TCP_DOMAIN')


# 获取文件的内容
def get_contends(path):
    with open(path) as file_object:
        contends = file_object.read()
    return contends


def get_ssl_ca_cert():
    content = get_contends("/app/region/ssl/ca.pem")
    print(content)
    return content


def get_cert_file():
    content = get_contends("/app/region/ssl/client.pem")
    print(content)
    return content


def get_key_file():
    content = get_contends("/app/region/ssl/client.key.pem")
    print(content)
    return content


def get_current_time():
    create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(create_time)
    return create_time


def get_sql():
    sql = 'INSERT INTO region_info (`region_id`,`region_name`,`region_alias`,`url`,`status`,`desc`,`wsurl`, \
    `httpdomain`,`tcpdomain`,`scope`,`ssl_ca_cert`,`cert_file`,`key_file`,`create_time`) VALUES ("{0}", "rainbond", \
    "default cluster", "{1}", "1", "The current cluster is the default built-in cluster", "{2}", "{3}", "{4}", "default", \
        "{5}", "{6}", "{7}", "{8}" )'.format(get_region_id(), get_url(), get_wsurl(), get_http_domain(), get_tcp_domain(),
                                             get_ssl_ca_cert(), get_cert_file(), get_key_file(), get_current_time())
    print(sql)
    return sql


def insert_default_region_info():
    sql = get_sql()
    db = create_db_client()
    cursor = db.cursor()
    cursor.execute(sql)
    cursor.close()
    db.commit()
    db.close()


def get_region_info():
    print("get region info")
    db = create_db_client()
    cursor = db.cursor()
    cursor.execute("select * from region_info")
    data = cursor.fetchone()
    cursor.close()
    db.commit()
    db.close()
    return data


if __name__ == '__main__':
    print("Initialize default region info ")
    region_info = get_region_info()
    if region_info:
        print("default region info already exists, skip it")
    else:
        print("default region info do not exists, init it")
        insert_default_region_info()
    print("init default region info success")
