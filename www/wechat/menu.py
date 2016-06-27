# -*- coding: utf8 -*-

# 微信的api查询接口

class MenuApi:

    def __init__(self, access_token):
        self.access_token = access_token
        self.url = "https://api.weixin.qq.com/cgi-bin/menu/"


    def create_menu(self):
        url = self.url + "create?access_token={0}".format(self.access_token)
        pass

    def query_menu(self):
        url = self.url + "get?access_token={0}".format(self.access_token)
        pass

    def delete_menu(self):
        url = self.url + "delete?access_token={0}".format(self.access_token)
        pass



if __name__ == "__main__":
    from www.wechat.openapi import WeChatAPI

    chatapi = WeChatAPI()

