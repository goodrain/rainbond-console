import hashlib
import platform
import socket
import uuid


def get_system_info():
    # 获取CPU信息
    cpu_info = platform.processor()

    # 获取IP地址
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip_address = "N/A"

    # 获取MAC地址
    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(5, -1, -1)])

    return f"CPU: {cpu_info}\nIP: {ip_address}\nMAC: {mac_address}"


def calculate_md5(data):
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode('utf-8'))
    return md5_hash.hexdigest()


def get_hash_mac():
    system_info = get_system_info()
    return calculate_md5(system_info)
