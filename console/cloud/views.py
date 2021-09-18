# -*- coding: utf8 -*-
import logging
import re

import requests
from django.http import HttpResponse, QueryDict

try:
    from urllib.parse import urlparse
except Exception:
    from urllib.parse import urlparse

import os

from console.views.base import JWTAuthApiView

logger = logging.getLogger("default")


# proxy api to enterprise api
class ProxyView(JWTAuthApiView):
    def dispatch(self, request, path, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers
        try:
            self.initial(request, *args, **kwargs)
            remoteurl = "http://{0}:{1}/{2}".format(os.getenv("ADAPTOR_HOST", "127.0.0.1"), os.getenv("ADAPTOR_PORT", "8080"),
                                                    path)
            response = self.proxy_view(request, remoteurl)
        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def proxy_view(self, request, url, requests_args=None):
        """
        Forward as close to an exact copy of the request as possible along to the
        given url.  Respond with as close to an exact copy of the resulting
        response as possible.
        If there are any additional arguments you wish to send to requests, put
        them in the requests_args dictionary.
        """
        requests_args = (requests_args or {}).copy()
        headers = self.get_headers(request.META)
        params = request.GET.copy()

        if 'headers' not in requests_args:
            requests_args['headers'] = {}
        if 'data' not in requests_args:
            requests_args['data'] = request.body
        if 'params' not in requests_args:
            requests_args['params'] = QueryDict('', mutable=True)

        # Overwrite any headers and params from the incoming request with explicitly
        # specified values for the requests library.
        headers.update(requests_args['headers'])
        params.update(requests_args['params'])

        # If there's a content-length header from Django, it's probably in all-caps
        # and requests might not notice it, so just remove it.
        for key in list(headers.keys()):
            if key.lower() == 'content-length':
                del headers[key]

        requests_args['headers'] = headers
        requests_args['params'] = params
        if requests_args['headers'].get("AUTHORIZATION"):
            requests_args['headers'].pop("AUTHORIZATION")
        response = requests.request(request.method, url, **requests_args)

        proxy_response = HttpResponse(response.content, status=response.status_code)

        excluded_headers = set([
            # Hop-by-hop headers
            # ------------------
            # Certain response headers should NOT be just tunneled through.  These
            # are they.  For more info, see:
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
            'connection',
            'keep-alive',
            'proxy-authenticate',
            'proxy-authorization',
            'te',
            'trailers',
            'transfer-encoding',
            'upgrade',

            # Although content-encoding is not listed among the hop-by-hop headers,
            # it can cause trouble as well.  Just let the server set the value as
            # it should be.
            'content-encoding',

            # Since the remote server may or may not have sent the content in the
            # same encoding as Django will, let Django worry about what the length
            # should be.
            'content-length',
        ])
        for key, value in list(response.headers.items()):
            if key.lower() in excluded_headers:
                continue
            elif key.lower() == 'location':
                # If the location is relative at all, we want it to be absolute to
                # the upstream server.
                proxy_response[key] = self.make_absolute_location(response.url, value)
            else:
                proxy_response[key] = value

        return proxy_response

    def make_absolute_location(self, base_url, location):
        """
        Convert a location header into an absolute URL.
        """
        absolute_pattern = re.compile(r'^[a-zA-Z]+://.*$')
        if absolute_pattern.match(location):
            return location

        parsed_url = urlparse(base_url)

        if location.startswith('//'):
            # scheme relative
            return parsed_url.scheme + ':' + location

        elif location.startswith('/'):
            # host relative
            return parsed_url.scheme + '://' + parsed_url.netloc + location

        else:
            # path relative
            return parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path.rsplit('/', 1)[0] + '/' + location

    def get_headers(self, environ):
        """
        Retrieve the HTTP headers from a WSGI environment dictionary.  See
        https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.META
        """
        headers = {}
        for key, value in list(environ.items()):
            # Sometimes, things don't like when you send the requesting host through.
            if key.startswith('HTTP_') and key != 'HTTP_HOST':
                headers[key[5:].replace('_', '-')] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                headers[key.replace('_', '-')] = value

        return headers
