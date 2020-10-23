import platform

if platform.system() == "Darwin":
    import pymysql
    pymysql.install_as_MySQLdb()
