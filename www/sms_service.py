# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from utils.mnssdk.mns.account import Account
from utils.mnssdk.mns.topic import DirectSMSInfo, TopicMessage
from utils.mnssdk.mns.mns_exception import MNSExceptionBase

logger = logging.getLogger('default')


def send_phone_message(phone, phonecode):
    # AccessKeyId、AccessKeySecret、Endpoint、SecurityToken
    # 从https://account.console.aliyun.com/#/secure获取$YourAccountid
    # 从https://ak-console.aliyun.com/#/accesskey获取$YourAccessId和$YourAccessKey
    # 从http://$YourAccountId.mns.cn-hangzhou.aliyuncs.com获取$YourMNSEndpoint,
    #  eg. http://1234567890123456.mns.cn-hangzhou.aliyuncs.com
    account_id = settings.ALIYUN_MNS['ACCOUNTID']
    if account_id is None:
        return False, None
    access_id = settings.ALIYUN_MNS['ACCESSKEYID']
    access_key = settings.ALIYUN_MNS['ACCESSKEYSECRET']
    end_point = settings.ALIYUN_MNS['ENDPOINT']
    # security_token = ''
    # YourTopic，发送短信使用的主题
    topic_name = settings.ALIYUN_MNS['TOPICNAME']
    # $YourSignName，发送短信使用的签名，
    sign_name = settings.ALIYUN_MNS['SIGNNAME']
    # YourSMSTemplateCode 发送短信使用的模板Code
    template_code = settings.ALIYUN_MNS['TEMPLATECODE']
    # YourSMSTemplateParamKey1，所指定短信模板中定义的参数名（“{}”中的内容），没有可不指定
    # YourReceiverPhoneNumber1，接收短信的手机号码
    receiver_phone_number = phone

    # Step 1. 获取主题引用
    my_account = Account(end_point, access_id, access_key)
    my_topic = my_account.get_topic(topic_name)
    # Step 2. 设置SMS消息体（必须）
    msg_body = str("[注册码]")
    # Step 3. 生成SMS消息属性，single=False表示每个接收者参数不一样，
    # 3.1 设置SMSSignName和SMSTempateCode
    direct_sms_attr = DirectSMSInfo(free_sign_name=sign_name, template_code=template_code, single=False)
    # 3.2 指定接收短信的手机号并指定发送给该接收人的短信中的参数值（在短信模板中定义的）
    direct_sms_attr.add_receiver(receiver=receiver_phone_number, params={"code": str(phonecode)})
    # Step 4. 生成SMS消息属性，single=True表示每个接收者参数一样
    # direct_sms_attr2 = DirectSMSInfo(free_sign_name="$YourSignName", template_code="$YourSMSTemplateCode", single=True)
    # direct_sms_attr2.add_receiver(receiver="$YourReceiverPhoneNumber1")
    # direct_sms_attr2.add_receiver(receiver="$YourReceiverPhoneNumber2")
    # direct_sms_attr2.set_params({"$YourSMSTemplateParamKey1": "$Value"})
    # Step 5. 生成SMS消息对象
    msg1 = TopicMessage(msg_body, direct_sms=direct_sms_attr)
    try:
        # Step 6. 发布SMS消息
        re_msg = my_topic.publish_message(msg1)
        logger.debug("Publish Message Succeed. MessageID:{0}".format(re_msg.message_id))
        return True, re_msg.message_id
    except MNSExceptionBase, e:
        if e.type == "TopicNotExist":
            logger.error('ali yun mns topic not exist, please create it!')
        logger.error("Publish Message Fail. Exception:%s" % e)
    return False, None


# if __name__ == '__main__':
#     phone = '15901415902'
#     phonecode = '123123'
#     send_phone_message(phone, phonecode)
