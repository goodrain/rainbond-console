# -*- coding: utf8 -*-
import re
import ipaddress
import validators

from console.exception.main import ServiceHandleException


def validate_endpoint_address(address):
    def parse_ip():
        domain_ip = False
        format_address = address
        try:
            for item in address:
                if item == ".":
                    format_address = ipaddress.IPv4Address(address)
                    break
                elif item == ":":
                    format_address = ipaddress.IPv6Address(address)
                    break
        except ipaddress.AddressValueError:
            if validators.domain(address):
                domain_ip = True
            else:
                return None, False
        return format_address, domain_ip

    errs = []
    ip, domain_ip = parse_ip()
    if not domain_ip:
        if not ip:
            errs.append("{} must be a valid IP address".format(address))
            return errs, None
        if ip.is_unspecified:
            errs.append("{} may not be unspecified (0.0.0.0)".format(address))
        if ip.is_loopback:
            errs.append("{} may not be in the loopback range (127.0.0.0/8)".format(address))
        # if ip.is_link_local:
        #     errs.append("{} may not be in the link-local range (169.254.0.0/16)".format(address))
        # if ip.is_link_local:
        #     errs.append("{} may not be in the link-local multicast range (224.0.0.0/24)".format(address))
    return errs, domain_ip


def validate_endpoints_info(endpoints_info):
    total_domain = 0
    exist_address = dict()
    for address in endpoints_info:
        if exist_address.get(address):
            raise ServiceHandleException(msg="Multiple instances of the same address are not allowed", msg_show="不允许多实例地址相同")
        exist_address[address] = address
        if "https://" in address:
            address = address.partition("https://")[2]
        if "http://" in address:
            address = address.partition("http://")[2]
        if ":" in address:
            address = address.rpartition(":")[0]
        errs, domain_ip = validate_endpoint_address(address)
        if domain_ip:
            total_domain += 1
        if errs:
            if len(errs) > 0:
                raise ServiceHandleException(msg=errs, msg_show="ip地址不合法")
    if total_domain > 1:
        raise ServiceHandleException(msg="do not support multi domain endpoint", msg_show="不允许多实例域名地址")
    elif total_domain > 0 and len(endpoints_info) > 1:
        raise ServiceHandleException(msg="do not support multi domain endpoint", msg_show="不允许多实例域名、ip混合地址")


def validate_name(name):
    # 只支持中文、字母、数字和-_组合,并且必须以中文、字母、数字开始和结束
    if re.match(r'^[a-z0-9A-Z\u4e00-\u9fa5]([a-zA-Z0-9_\-\u4e00-\u9fa5]*[a-z0-9A-Z\u4e00-\u9fa5])?$', name):
        return True
    return False


# Verification k8s resource name, refer to:
# https://github.com/kubernetes/kubernetes/blob/b0bc8adbc2178e15872f9ef040355c51c45d04bb/staging/src/k8s.io/apimachinery/pkg/util/validation/validation.go#L43
def is_qualified_name(name):
    # 只支持字母、数字和-组合,并且必须以字母开始、以数字或字母结尾
    if re.match(r'^[a-z]([-a-z0-9]*[a-z0-9])?$', name):
        return True
    return False


def normalize_name_for_k8s_namespace(name):
    """
    将用户名转换为符合k8s命名空间规范的名称
    k8s命名空间规范:
    - 只能包含小写字母、数字和连字符(-)
    - 必须以小写字母开头
    - 不能以连字符结尾
    - 长度限制为63个字符以内
    - 不能包含连续的连字符
    """
    if not name:
        return "user"
    
    # 转换为小写
    name = name.lower()
    
    # 移除或替换不允许的字符，只保留字母、数字和连字符
    name = re.sub(r'[^a-z0-9\-]', '-', name)
    
    # 移除连续的连字符
    name = re.sub(r'-+', '-', name)
    
    # 确保以字母开头
    if not re.match(r'^[a-z]', name):
        name = 'user-' + name
    
    # 移除开头的连字符（如果有）
    name = name.lstrip('-')
    
    # 移除结尾的连字符
    name = name.rstrip('-')
    
    # 如果为空或只包含连字符，使用默认值
    if not name or name == '-':
        name = 'user'
    
    # 限制长度为63个字符
    if len(name) > 63:
        name = name[:63].rstrip('-')
    
    # 最终验证
    if not is_qualified_name(name):
        # 如果仍然不符合规范，使用默认值加随机后缀
        import time
        name = 'user-{}'.format(int(time.time()) % 100000)
    
    return name
