# -*- coding: utf8 -*-

import requests


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
        payload = {'grant_type': 'client_credential', 'appid': app_id, 'secret': app_secret}
        url = "https://api.weixin.qq.com/cgi-bin/token"
        res = requests.get(url, params=payload)
        if res.status_code == 200:
            try:
                jd = res.json()
                return jd.access_token
            except Exception as e:
                print(e)
        return None
