import base64
import hashlib
import hmac
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs


class SSO_AuthHandle(object):
    def __init__(self, secret_key: Any) -> None:
        self.secret_key = secret_key

    def sig(self, string_to_sig: Any) -> str:
        _hmac = hmac.new(self.secret_key, digestmod=hashlib.sha256)
        _hmac.update(string_to_sig)
        return _hmac.hexdigest()

    def extra_payload(self, sso: str, sig: str) -> Optional[Dict[str, Any]]:
        encoded_sso = str(urllib.parse.unquote(sso))
        sig_sso = self.sig(encoded_sso)
        if sig_sso != sig:
            return None

        raw_payload = base64.urlsafe_b64decode(encoded_sso)
        params_form = parse_qs(raw_payload)
        payload: Dict[str, Any] = {}
        for key, values in list(params_form.items()):
            payload[key] = values[0]  # type: ignore[index]  # NOTE: parse_qs on bytes input yields dict[bytes, list[bytes]]; key is bytes but payload typed as dict[str,Any]; existing Python2/3 compat code
        return payload

    def create_auth(self, params: Dict[str, Any]) -> Tuple[str, str]:
        pairs = []
        for k, v in list(params.items()):
            q = k + '=' + urllib.parse.quote(str(v))
            pairs.append(q)

        unsign_payload = '&'.join(pairs)
        encoded_payload = base64.standard_b64encode(unsign_payload)  # type: ignore[arg-type]  # NOTE: unsign_payload is str but b64encode expects bytes; existing code relies on runtime implicit encoding
        url_encoded_payload = urllib.parse.quote(encoded_payload)
        sig = self.sig(encoded_payload)
        return url_encoded_payload, sig
