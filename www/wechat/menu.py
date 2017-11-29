# -*- coding: utf8 -*-

import time
import requests
from www.models import WeChatConfig


class MenuApi:

    def __init__(self, access_token):
        self.access_token = access_token
        self.url = "https://api.weixin.qq.com/cgi-bin/menu/"

    def create_menu(self, menustr):
        url = self.url + "create?access_token={0}".format(self.access_token)
        return requests.post(url, data=menustr)

    def query_menu(self):
        url = self.url + "get?access_token={0}".format(self.access_token)
        return requests.get(url)

    def delete_menu(self):
        url = self.url + "delete?access_token={0}".format(self.access_token)
        return requests.get(url)


class AccessTokenApi:

    def __init__(self):
        pass

    def check_token(self, token):
        pass

    @staticmethod
    def auth_access_token(app_id, app_secret):
        payload = {'grant_type': 'client_credential',
                   'appid': app_id,
                   'secret': app_secret}
        url = "https://api.weixin.qq.com/cgi-bin/token"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                jd = res.json()
                return jd.access_token
            except Exception as e:
                print e
        return None


# if __name__ == "__main__":
    # 从数据库中获取access_token
#     wechat_config = WeChatConfig.objects.get(config="goodrain")
#     access_token = wechat_config.access_token
#     access_token_expires_at = wechat_config.access_token_expires_at
#     now = int(time.time())
#     if (access_token is None) or (now - access_token_expires_at < 60):
#         # 获取access_token
#         access_token = AccessTokenApi.auth_access_token(wechat_config.app_id,
#                                                         wechat_config.app_secret)
#         wechat_config.access_token = access_token
#         wechat_config.access_token_expires_at = now + 7200
#         wechat_config.save()
#
#     # 重新生成menu
#     menustr = """
# {
#     "button": [
#         {
#             "name": "云帮",
#             "sub_button": [
#                 {
#                     "type": "view",
#                     "name": "云帮2.0",
#                     "url": "http://www.goodrain.com/product/"
#                 },
#                 {
#                     "type": "view",
#                     "name": "免费体验",
#                     "url": "http://www.goodrain.com/product/goodrain.html"
#                 }
#             ]
#         },
#         {
#             "name": "云市",
#             "type": "view",
#             "url": "https://app.goodrain.com/"
#         },
#         {
#             "name": "我们",
#             "type": "view",
#             "url": "http://mp.weixin.qq.com/s?__biz=MzIwMDA2OTI0Mw==&mid=505965013&idx=1&sn=fe9dba9dd56f5b6aa5792a2a75fb4cfc&scene=18#wechat_redirect"
#         }
#     ]
# }
#     """
#     menuapi = MenuApi(access_token)
#     result = menuapi.create_menu(menustr)
#     print result



