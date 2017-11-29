import hmac
import hashlib
import urllib
import base64
from urlparse import parse_qs


class SSO_AuthHandle(object):

    def __init__(self, secret_key):
        self.secret_key = secret_key

    def sig(self, string_to_sig):
        _hmac = hmac.new(self.secret_key, digestmod=hashlib.sha256)
        _hmac.update(string_to_sig)
        return _hmac.hexdigest()

    def extra_payload(self, sso, sig):
        encoded_sso = str(urllib.unquote(sso))
        sig_sso = self.sig(encoded_sso)
        if sig_sso != sig:
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
        encoded_payload = base64.standard_b64encode(unsign_payload)
        url_encoded_payload = urllib.quote(encoded_payload)
        sig = self.sig(encoded_payload)
        return url_encoded_payload, sig
