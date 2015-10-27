import hmac
import hashlib
import urllib
import base64
from www.utils.json_tool import json_load


class SSO_AuthHandle(object):

    def __init__(self, secret_key):
        self.secret_key = secret_key
        self._hmac = hmac.new(self.secret_key, digestmod=hashlib.sha256)

    def sig(self, string_to_sig):
        self._hmac.update(string_to_sig)
        return self._hmac.hexdigest()

    def extra_payload(self, sso, sig):
        if self.sig(sso) != sig:
            return None

        raw_payload = base64.standard_b64decode(sso)
        return json_load(raw_payload)

    def create_auth(self, params):
        pairs = []
        for k, v in params.items():
            q = k + '=' + urllib.quote(str(v))
            pairs.append(q)

        unsign_payload = '&'.join(pairs)
        encoded_paylaod = base64.standard_b64encode(unsign_payload)

        sig = self.sig(encoded_paylaod)
        return encoded_paylaod, sig
