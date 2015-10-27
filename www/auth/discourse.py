import hmac
import hashlib
import urllib
import base64
from urlparse import parse_qs
from www.utils.json_tool import json_load


class SSO_AuthHandle(object):

    def __init__(self, secret_key):
        self.secret_key = secret_key
        self._hmac = hmac.new(self.secret_key, digestmod=hashlib.sha256)

    def sig(self, string_to_sig):
        self._hmac.update(string_to_sig)
        return self._hmac.hexdigest()

    def extra_payload(self, sso, sig):
        encoded_sso = urllib.unquote(sso)
        if self.sig(encoded_sso) != sig:
            return None

        raw_payload = base64.urlsafe_b64decode(encoded_sso)
        params_form = parse_qs(raw_payload)
        payload = {}
        for key, values in params_form.items():
            payload[key] = values[0]
        return payload

    def create_auth(self, params):
        pairs = []
        for k, v in params.items():
            q = k + '=' + urllib.quote(str(v))
            pairs.append(q)

        unsign_payload = '&'.join(pairs)
        encoded_payload = base64.urlsafe_b64encode(unsign_payload)
        sig = self.sig(encoded_payload)
        url_encoded_payload = urllib.quote(encoded_payload)
        return url_encoded_payload, sig
