# -*- coding: utf8 -*-
import logging.handlers
import collections
import os
import sys
reload(sys)
sys.setdefaultencoding('UTF-8')


loggerOld = logging.getLogger('default')


class WebLog:
    WebLogs = collections.defaultdict(logging.getLogger)
    WebLogsKey = collections.defaultdict(int)
    def __init__(self):
        pass
            
    def createLogObject(self, tenantName, logName):
        try:
            log_dir = "/tmp/logs/" + tenantName + "/"
            if(os.path.exists(log_dir)):
                pass
            else:
                os.makedirs(log_dir)            
            log_file = log_dir + logName + ".log"
            handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)  # 实例化handler 
            fmt = '%(asctime)s  %(message)s'        
            formatter = logging.Formatter(fmt)  # 实例化formatter
            handler.setFormatter(formatter)  # 为handler添加formatter  
            logger = logging.getLogger(logName)  # 获取名为tst的logger
            logger.addHandler(handler)  # 为logger添加handler
            logger.setLevel(logging.INFO)
            self.WebLogs[tenantName + "-" + logName] = logger
            self.WebLogsKey[tenantName + "-" + logName] = 1
        except Exception:
            pass
        
        
    def info(self, tenantName, logName, msg):
        try:
            if(logName != ""):
                key = tenantName + "-" + logName
                if(self.WebLogsKey[key] == 0):
                    self.createLogObject(tenantName, logName)
                logger = self.WebLogs[key]
                newMsg = "[" + logName + "] : " + unicode(msg)
                logger.info(newMsg)
        except Exception as e:
            loggerOld.info("%s" % e)
            pass
        
    def getLog(self, tenantName, logName):
        data = {}       
        num = 0
        msg = ""
        try:
            logfile="/tmp/logs/" + tenantName + "/" + logName + ".log"
            f = open(logfile)
            line = f.readline()
            while line:
                num = num + 1
                msg = msg + line + "</br>" 
                line = f.readline()
            f.close()
        except Exception as e:
            loggerOld.info("%s" % e)
            pass
        data["num"] = num
        data["log"] = msg
        return data
