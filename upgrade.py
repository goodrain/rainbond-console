# -*- coding: UTF-8 -*-
import os

import MySQLdb


class RainbondVersion(object):

    max_version = 5

    min_version = 1

    median_version = 5

    def __str__(self):
        return "{0}.{1}.{2}".format(self.max_version, self.median_version, self.min_version)

    def __init__(self, version_str):
        info = version_str.split(".")
        if len(info) == 3:
            self.max_version = int(info[0])
            self.median_version = int(info[1])
            self.min_version = int(info[2])
        else:
            raise Exception("Illegal version")

    def next_min_version(self):
        return "{0}.{1}.{2}".format(self.max_version, self.median_version, self.min_version + 1)

    def next_median_version(self):
        return "{0}.{1}.{2}".format(self.max_version, self.median_version + 1, 0)

    def next_max_version(self):
        return "{0}.{1}.{2}".format(self.max_version + 1, 0, 0)

    def equal(self, new_version):
        return self.max_version == new_version.max_version and \
            self.median_version == new_version.median_version and \
            self.min_version == new_version.min_version


def create_db_client():
    host = os.environ.get('MYSQL_HOST')
    user = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASS')
    database = os.environ.get('MYSQL_DB')
    db = MySQLdb.connect(host, user, password, database)
    return db


def get_upgrade_sql(current_version, new_version):
    sql_file_name = "/app/ui/sql/{0}-{1}.sql".format(current_version, new_version)
    if not os.path.exists(sql_file_name):
        return None
    with open(sql_file_name) as f:
        sql_list = f.read().split(';')[:-1]  # sql文件最后一行加上;
        # sql_list = [x.replace('\n', ' ') if '\n' in x else x for x in sql_list]  # 将每段sql里的换行符改成空格
        return sql_list
    return None


def upgrade(current_version, new_version):
    try:
        print("current console db version is {}".format(current_version))
        print("update  console db version to {}".format(new_version))
        sql_list = get_upgrade_sql(current_version, new_version)
        if sql_list:
            db = create_db_client()
            cursor = db.cursor()
            for sql_item in sql_list:
                print "exec sql: {0}".format(sql_item)
                cursor.execute(sql_item)
            cursor.close()
            db.commit()
            db.close()
            print("update console db version to {} success".format(new_version))
        else:
            print("no sql file, do not update")
            db = create_db_client()
            cursor = db.cursor()
            cursor.execute('update console_sys_config set `value`="{0}" where `key`="RAINBOND_VERSION";'.format(new_version))
            cursor.close()
            db.commit()
            db.close()
    except Exception as e:
        print(e)


def get_version():
    db = create_db_client()
    cursor = db.cursor()
    cursor.execute('select value from console_sys_config where `key`="RAINBOND_VERSION"')
    data = cursor.fetchone()
    cursor.close()
    db.close()
    if data:
        return RainbondVersion(data[0])
    return ""


def get_current_version():
    return RainbondVersion("5.2.0")


def should_upgrade(current_version, new_version):
    if new_version.max_version != current_version.max_version:
        return False
    if new_version.median_version != current_version.median_version:
        return False
    if new_version.min_version > current_version.min_version:
        return True
    return False


if __name__ == '__main__':
    print "Initialize rainbond console"
    new_version = get_current_version()
    current_version = get_version()
    if should_upgrade(current_version, new_version):
        print "Start upgrade console db from {0} to {1}".format(current_version, new_version)
        while True:
            if current_version.equal(new_version):
                break
            upgrade(current_version, current_version.next_min_version())
            current_version = RainbondVersion(current_version.next_min_version())
        print "upgrade console db from {0} to {1} success".format(current_version, new_version)
    else:
        print "{0} no need upgrade to {1}".format(current_version, new_version)
