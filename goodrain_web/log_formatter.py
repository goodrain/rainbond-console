import logging
import socket
import time

class IPFormatter(logging.Formatter):
    def format(self, record):
        # 获取服务器IP地址
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = 'unknown'
        
        # 格式化时间
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S')
        
        # 获取模块名
        module = record.module if hasattr(record, 'module') else 'unknown'
        
        # 构建日志消息
        log_message = f"INFO[{timestamp}] ip={ip} module={module} {record.getMessage()}"
        
        return log_message