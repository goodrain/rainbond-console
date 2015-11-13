#import re
from django.utils.six.moves.urllib.parse import urlparse

REDIRECT_SSL_HOST = ('user.goodrain.com', 'zyq-debug.goodrain.com', 'dev.goodrain.com')


def get_redirect_url(path, request=None, scheme=None, host=None):
    parsed_url = urlparse(path)
    if parsed_url.scheme != '' and parsed_url.netloc != '':
        scheme = parsed_url.scheme
        host = parsed_url.netloc
        path = parsed_url.path + '?' + parsed_url.query
    elif request is not None:
        scheme = request.scheme
        host = request.get_host()
    else:
        if scheme is None or host is None:
            raise ValueError("scheme and host can't be none")

    if scheme == 'https':
        pass
    else:
        if host in REDIRECT_SSL_HOST:
            scheme = 'https'

    return "{0}://{1}{2}".format(scheme, host, path)
